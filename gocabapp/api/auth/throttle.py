from django.core.cache import cache
from ninja.errors import HttpError


def throttle(cache_key: str, limit: int, window_seconds: int) -> None:
    """Fixed-window request counter backed by the shared cache (Redis in
    production), so limits hold across every app server, not just one.
    """
    try:
        count = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=window_seconds)
        count = 1

    if count > limit:
        raise HttpError(429, "Too many attempts. Please try again shortly.")
