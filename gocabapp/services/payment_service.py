"""
Payment orchestration: fare estimation, Paystack checkout, and callback verification.
All Paystack HTTP logic lives here alongside the Django service functions.
"""
from __future__ import annotations

import logging
import random
import time

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from ..models import RideRequest, Rider
from ..utils.fare_pricing import calculate_ride_fare, DRIVER_EARNINGS_RATE
from ..utils.distance_utils import google_distance
from ..services.ride_events import notify_rider, notify_driver_pool

logger = logging.getLogger(__name__)

# ── Paystack constants ────────────────────────────────────────────────────────

_INIT_URL   = "https://api.paystack.co/transaction/initialize"
_VERIFY_URL = "https://api.paystack.co/transaction/verify/{}"
_TIMEOUT    = 30
_REF_PREFIX = "RIDE"


class PaymentError(Exception):
    """Paystack or transport-level failure."""


# ── Internal Paystack helpers ─────────────────────────────────────────────────

def _passenger_email(ride: RideRequest) -> str:
    email = ride.passenger.email
    if not email:
        try:
            email = Rider.objects.get(user=ride.passenger).email
        except Rider.DoesNotExist:
            pass
    if not email:
        raise PaymentError(f"No email found for passenger on ride {ride.id}")
    return email


def _reference(ride: RideRequest) -> str:
    return f"{_REF_PREFIX}_{ride.id}_{int(time.time())}_{random.randint(1000, 9999)}"


def _auth_header() -> dict:
    return {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}


def _create_payment_link(ride: RideRequest) -> str:
    """Call Paystack initialize; return authorization_url. Raises PaymentError on failure."""
    if not ride.total_fare or ride.total_fare <= 0:
        raise PaymentError(f"Invalid fare ₦{ride.total_fare} for ride {ride.id}")

    email     = _passenger_email(ride)
    reference = _reference(ride)

    payload = {
        "email":        email,
        "amount":       int(ride.total_fare * 100),  # kobo
        "reference":    reference,
        "callback_url": f"{settings.BASE_URL}/payment/success/{ride.id}/",
        "metadata": {
            "ride_id":      ride.id,
            "passenger_id": ride.passenger.id,
            "driver_id":    ride.driver.id if ride.driver else None,
        },
    }

    try:
        response = requests.post(_INIT_URL, headers=_auth_header(), json=payload, timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise PaymentError(f"Paystack request failed: {e}") from e

    if response.status_code != 200:
        raise PaymentError(f"Paystack returned HTTP {response.status_code}")

    data = response.json()
    url  = data.get("data", {}).get("authorization_url")
    if not (data.get("status") and url):
        raise PaymentError(f"Paystack init failed: {data}")

    ride.payment_reference = reference
    ride.save(update_fields=["payment_reference"])
    return url


# ── Public service functions ──────────────────────────────────────────────────

def estimate_fare_from_locations(pickup: str, destination: str) -> tuple[dict, int]:
    if not pickup or not destination:
        return {"error": "Both pickup and destination are required"}, 400
    distance_km, duration_min = google_distance(pickup, destination)
    if distance_km is None:
        return {"error": "Could not calculate route — check addresses"}, 400
    return calculate_ride_fare(distance_km, duration_min), 200


def initiate_checkout_for_ride(passenger: User, ride_id: int) -> tuple[dict, int]:
    try:
        ride = RideRequest.objects.get(id=ride_id, passenger=passenger)
    except RideRequest.DoesNotExist:
        return {"status": "error", "error": "Ride not found"}, 404

    if ride.status != "completed":
        return {"status": "error", "error": f"Ride must be completed before payment (status: {ride.status})"}, 400
    if ride.payment_status == "paid":
        return {"status": "error", "error": "Payment already completed"}, 400

    try:
        url = _create_payment_link(ride)
        logger.info("Payment link created ride_id=%s", ride.id)
        return {"status": "success", "payment_url": url, "ride_id": ride.id}, 200
    except PaymentError as e:
        logger.error("Payment link failed ride_id=%s: %s", ride_id, e)
        return {"status": "error", "error": str(e)}, 500


def handle_payment_callback(ride_id: int, query_params) -> str:
    """
    Verify Paystack callback, mark ride paid, notify via WebSocket.
    Returns a redirect path string.
    """
    fail = "/rider-dashboard/?payment=failed"

    try:
        ride      = RideRequest.objects.get(id=ride_id)
        reference = query_params.get("reference") or ride.payment_reference

        if not reference:
            return f"{fail}&error=no_reference"

        try:
            response = requests.get(
                _VERIFY_URL.format(reference),
                headers=_auth_header(),
                timeout=_TIMEOUT,
            )
        except requests.RequestException as e:
            logger.error("Paystack verify request failed: %s", e)
            return f"{fail}&error=request_failed"

        if response.status_code != 200:
            return f"{fail}&error=http_{response.status_code}"

        data            = response.json()
        paystack_status = data.get("data", {}).get("status")

        if not (data.get("status") and paystack_status == "success"):
            logger.error("Paystack verification failed status=%s", paystack_status)
            return f"{fail}&error=paystack_{paystack_status}"

        applied = False
        with transaction.atomic():
            locked = RideRequest.objects.select_for_update().get(id=ride_id)
            if locked.payment_status != "paid":
                locked.payment_reference = reference
                locked.payment_status    = "paid"
                locked.paid_at           = timezone.now()
                locked.save()
                applied = True
                logger.info("Ride %s marked paid", ride_id)

        if applied:
            ride.refresh_from_db()
            earnings = float(ride.total_fare) * DRIVER_EARNINGS_RATE

            notify_rider(ride.id, {
                "type":    "ride_update",
                "event":   "payment_completed",
                "ride_id": ride.id,
                "message": "Payment completed! Thank you for your ride.",
            })

            if ride.driver:
                notify_driver_pool({
                    "type":     "ride_update",
                    "event":    "payment_received",
                    "ride_id":  ride.id,
                    "message":  "Rider payment completed!",
                    "earnings": earnings,
                })

        return f"/rider-dashboard/?payment=success&amount={ride.total_fare}&ride_id={ride.id}"

    except RideRequest.DoesNotExist:
        logger.error("handle_payment_callback: ride %s not found", ride_id)
        return f"{fail}&error=ride_not_found"
    except Exception:
        logger.exception("handle_payment_callback unexpected error ride_id=%s", ride_id)
        return f"{fail}&error=unexpected"