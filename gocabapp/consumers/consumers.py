from __future__ import annotations

import json
import logging

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder

from ..models import Notification, RideRequest
from ..utils import DjangoSafeJSONEncoder

logger = logging.getLogger(__name__)


class RideUpdatesConsumer(AsyncWebsocketConsumer):
    """Rider-side WebSocket: subscribes to a single ride group."""

    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return
        self.user = self.scope["user"]
        self.ride_group: str | None = None
        await self.accept()
        logger.info("RideUpdates connected user=%s", self.user.id)

    async def disconnect(self, close_code):
        if self.ride_group:
            await self.channel_layer.group_discard(self.ride_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = data.get("action")
        ride_id = data.get("ride_id")

        if action == "subscribe" and ride_id:
            # Leave previous group if re-subscribing
            if self.ride_group:
                await self.channel_layer.group_discard(
                    self.ride_group, self.channel_name
                )
            self.ride_group = f"ride_{ride_id}"
            await self.channel_layer.group_add(self.ride_group, self.channel_name)
            logger.info("User %s subscribed to %s", self.user.id, self.ride_group)

        elif action == "unsubscribe" and self.ride_group:
            await self.channel_layer.group_discard(self.ride_group, self.channel_name)
            self.ride_group = None

    async def ride_update(self, event):
        """Relay a ride_update group message to the WebSocket client."""
        payload = {
            "type": "ride_update",
            "event": event.get("event"),
            "ride_id": event.get("ride_id"),
            "data": {
                "status": event.get("event"),
                "driver": event.get("driver"),
                "eta": event.get("eta"),
                "fare": _to_float(event.get("fare")),
                "distance": _to_float(event.get("distance")),
            },
        }
        await self.send(text_data=json.dumps(payload, cls=DjangoJSONEncoder))


class DriverUpdatesConsumer(AsyncWebsocketConsumer):
    """Driver-side WebSocket: joins the shared driver_updates pool."""

    DRIVER_GROUP = "driver_updates"

    async def connect(self):
        user = self.scope["user"]

        if user.is_anonymous:
            await self.close()
            return
        
        await self.accept()
    
        if not await self._is_driver(user):
            logger.warning("DriverUpdates rejected non-driver: user=%s", user.id)
            await self.close()
            return
        self.user = user
        self.personal_group = f"driver_{user.id}"
        await self.channel_layer.group_add(self.DRIVER_GROUP, self.channel_name)
        await self.channel_layer.group_add(self.personal_group, self.channel_name)
        logger.info("Driver %s joined %s", self.user.id, self.DRIVER_GROUP)

    async def disconnect(self, close_code):
        if hasattr(self, "user"):
            await self.channel_layer.group_discard(self.DRIVER_GROUP, self.channel_name)
            if hasattr(self, "personal_group"):
                await self.channel_layer.group_discard(self.personal_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        if data.get("type") == "heartbeat":
            await self.send(text_data=json.dumps({"type": "heartbeat_ack"}))

    # ---- channel-layer event handlers ----

    async def new_ride_request(self, event):
        await self._send(
            {
                "type": "new_ride_request",
                "event": "new_ride_request",
                "ride_id": event.get("ride_id"),
                "message": event.get("message", "New ride request available"),
            }
        )

    async def ride_accepted(self, event):
        await self._send(
            {
                "type": "ride_accepted",
                "event": "ride_accepted",
                "ride": event.get("ride"),
                "message": "Ride accepted successfully",
            }
        )

    async def ride_update(self, event):
        await self._send(
            {
                "type": "ride_update",
                "event": event.get("event"),
                "ride_id": event.get("ride_id"),
                "message": event.get("message"),
                "data": event.get("data"),
            }
        )

    async def ride_accepted_by_other(self, event):
        await self._send(
            {
                "type": "ride_accepted_by_other",
                "ride_id": event.get("ride_id"),
                "message": "This ride was accepted by another driver",
            }
        )

    async def ride_cancelled(self, event):
        await self._send(
            {
                "type": "ride_update",
                "event": "ride_cancelled",
                "ride_id": event.get("ride_id"),
                "message": "Ride was cancelled by passenger",
            }
        )

    async def driver_update(self, event):
        await self._send(dict(event))

    # ---- helpers ----

    async def _send(self, payload: dict):
        """Serialise and send; log on failure instead of silently swallowing."""
        try:
            await self.send(text_data=json.dumps(payload, cls=DjangoSafeJSONEncoder))
        except Exception:
            logger.exception(
                "DriverUpdatesConsumer._send failed for driver %s payload=%s",
                getattr(self, "user", {}).id if hasattr(self, "user") else "?",
                payload.get("type"),
            )

    @database_sync_to_async
    def _is_driver(self, user) -> bool:
        return hasattr(user, "driver")


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return
        self.user = user
        self.group = f"notifications_{user.id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        count = await self._notification_count()
        await self.accept()
        await self.send(text_data=json.dumps({"type": "counter", "count": count}))
    
    
    async def notification_update(self, event):
        """Forward notification count update to rider client."""
        await self.send(text_data=json.dumps({
            "type": "notification_update",
            "count": event.get("count", 0),
        }, cls=DjangoJSONEncoder))

    async def disconnect(self, close_code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def notification_update(self, event):
        await self.send(
            text_data=json.dumps({"type": "counter", "count": event["count"]})
        )

    @database_sync_to_async
    def _notification_count(self) -> int:
        return Notification.objects.filter(user=self.user, is_active=True).count()


# ---- module-level util ----

def _to_float(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None