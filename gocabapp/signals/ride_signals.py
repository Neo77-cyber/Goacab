from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from ..models import Notification, RideRequest
from ..services.ride_events import notify_driver_pool, notify_rider

logger = logging.getLogger(__name__)


def _driver_info(instance: RideRequest) -> dict:
    u = instance.driver
    d = u.driver
    return {
        "name":          u.get_full_name() or u.username,
        "rating":        float(d.rating) if getattr(d, "rating", None) else 4.5,
        "car_model":     getattr(d, "vehicle_model",  None) or "Unknown",
        "license_plate": getattr(d, "license_plate",  None) or "N/A",
    }


@receiver(post_save, sender=RideRequest)
def ride_request_update(sender, instance: RideRequest, created: bool, **kwargs):
    if created:
        notify_driver_pool({"type": "new_ride_request", "ride_id": instance.id})
        return

    status = instance.status

    if status == "accepted":
        Notification.objects.filter(user=instance.passenger, is_active=True).delete()
        Notification.objects.create(
            user=instance.passenger,
            message=f"Driver {instance.driver.get_full_name()} accepted your ride",
            is_active=True,
        )
        notify_rider(instance.id, {
            "type":    "ride_update",
            "event":   "accepted",
            "ride_id": instance.id,
            "driver":  _driver_info(instance),
            "eta":     max(5, int(instance.distance_km * 2)) if instance.distance_km else 10,
            "distance": f"{instance.distance_km:.1f} km" if instance.distance_km else None,
            "fare":    instance.total_fare,
        })
        

    elif status == "completed":
        Notification.objects.filter(user=instance.passenger, is_active=True).update(is_active=False)
        notify_rider(instance.id, {
            "type": "ride_update", "event": "completed",
            "ride_id": instance.id, "message": "Ride completed",
        })

    elif status in ("started", "cancelled"):
        notify_rider(instance.id, {
            "type": "ride_update", "event": status,
            "ride_id": instance.id, "message": f"Ride {status}",
        })
        if status == "cancelled" and instance.driver:
            notify_driver_pool({
                "type": "ride_cancelled", "ride_id": instance.id,
                "message": "Ride cancelled by passenger",
            })