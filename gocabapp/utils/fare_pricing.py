from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

VEHICLE_RATES: dict[str, dict] = {
    "standard": {"base": 1000.0, "per_km": 200.0, "per_min": 10.0, "min_fare": 800.0},
    "premium":  {"base": 1600.0, "per_km": 300.0, "per_min": 16.0, "min_fare": 1200.0},
    "xl":       {"base": 1400.0, "per_km": 240.0, "per_min": 12.0, "min_fare": 1000.0},
}

# Average city speeds in km/h — used for pickup-time estimates
CITY_SPEEDS: dict[str, int] = {
    "lagos": 20, "benin": 30, "ibadan": 25,
    "abuja": 35, "port harcourt": 25, "default": 25,
}

MAX_FARE = 30_000


DRIVER_EARNINGS_RATE = 0.8  


def _surge_multiplier() -> float:
    now = datetime.now()
    weekday = now.weekday() < 5
    hour = now.hour
    if weekday and (7 <= hour <= 9 or 17 <= hour <= 19):
        return 1.3
    if not weekday and 12 <= hour <= 22:
        return 1.2
    return 1.0


def calculate_ride_fare(
    distance_km: float,
    duration_min: float,
    vehicle_type: str = "standard",
) -> dict | None:
    if not distance_km or not duration_min or distance_km <= 0 or duration_min <= 0:
        logger.warning("calculate_ride_fare: invalid inputs distance=%s duration=%s", distance_km, duration_min)
        return None

    rates = VEHICLE_RATES.get(vehicle_type) or VEHICLE_RATES["standard"]
    surge = _surge_multiplier()

    subtotal = (rates["base"] + distance_km * rates["per_km"] + duration_min * rates["per_min"]) * surge
    total = max(subtotal, rates["min_fare"])
    if distance_km > 50:
        total = min(total, MAX_FARE)

    result = {
        "base_fare":        rates["base"],
        "distance_km":      round(distance_km, 2),
        "duration_min":     round(duration_min, 2),
        "distance_fare":    round(distance_km * rates["per_km"], 2),
        "time_fare":        round(duration_min * rates["per_min"], 2),
        "surge_multiplier": surge,
        "total_fare":       round(total, 2),
        "vehicle_type":     vehicle_type if vehicle_type in VEHICLE_RATES else "standard",
        "currency":         "NGN",
    }
    logger.info("Fare: ₦%s for %.1fkm (%s)", result["total_fare"], distance_km, vehicle_type)
    return result


def estimate_pickup_time(distance_km: float, city: str) -> int:
    """
    Estimate pickup time in minutes.
    Formula: travel time at city avg speed + 1.5 min/km traffic buffer.
    """
    speed = CITY_SPEEDS.get(city.lower(), CITY_SPEEDS["default"])
    travel_min = (distance_km / speed) * 60
    buffer_min = distance_km * 1.5   # ~1.5 extra min per km for traffic/stops
    return round(travel_min + buffer_min)