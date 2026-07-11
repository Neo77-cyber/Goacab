"""
Ride event broadcasting and payload construction.
All channel-layer sends go through _send(); all JSON shapes come from build_* functions.
"""
from __future__ import annotations

from decimal import Decimal


import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User

from ..models import RideRequest

logger = logging.getLogger(__name__)


# ── Payload builders ──────────────────────────────────────────────────────────

def _driver_fields(user: User) -> dict:
    p = user.driver
    return {
        "id":            user.id,
        "name":          user.get_full_name() or user.username,
        "car_model":     getattr(p, "vehicle_model",  None) or "Unknown",
        "license_plate": getattr(p, "license_plate",  None) or "N/A",
        "rating":        float(p.rating) if getattr(p, "rating", None) is not None else 4.5,
        "phone":         str(getattr(p, "phone_number", None) or ""),
    }


def _passenger_fields(ride: RideRequest) -> dict:
    return {
        "id":   ride.passenger.id,
        "name": ride.passenger.get_full_name() or ride.passenger.username,
    }


def build_trip_payload(ride: RideRequest, driver_user: User) -> dict:
    """Single shape used for active and completed trip responses."""
    return {
        "id":           ride.id,
        "status":       ride.status,
        "pickup":       ride.current_location or "",
        "dropoff":      ride.destination or "",
        "distance_km":  float(ride.distance_km)  if ride.distance_km  is not None else 0.0,
        "duration_min": float(ride.duration_min) if ride.duration_min is not None else 0.0,
        "fare":         float(ride.total_fare)   if ride.total_fare   is not None else 0.0,
        "started_at":   ride.started_at.isoformat() if ride.started_at else None,
        "driver":       _driver_fields(driver_user),
        "passenger":    _passenger_fields(ride),
    }

def _make_json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_json_safe(v) for v in value]
    return value


# ── Channel broadcasts ────────────────────────────────────────────────────────

def _send(group: str, message: dict) -> None:
    safe_message = _make_json_safe(message)
    async_to_sync(get_channel_layer().group_send)(group, safe_message)


def notify_drivers_new_ride(ride_id: int) -> None:
    _send("driver_updates", {"type": "new_ride_request", "ride_id": ride_id})
    logger.info("notify_drivers_new_ride ride_id=%s", ride_id)


def notify_drivers_ride_cancelled(ride_id: int, had_driver: bool = False) -> None:
    _send("driver_updates", {
        "type": "ride_cancelled",
        "ride_id": ride_id,
        "message": "Ride was cancelled by passenger",
    })
    logger.info("notify_drivers_ride_cancelled ride_id=%s had_driver=%s", ride_id, had_driver)


def notify_rider(ride_id: int, message: dict) -> None:
    """Send any typed event to the rider watching this ride."""
    _send(f"ride_{ride_id}", message)


def notify_driver_pool(message: dict) -> None:
    """Broadcast an arbitrary event to all connected drivers."""
    _send("driver_updates", message)