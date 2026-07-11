from .base import *
import dj_database_url
import redis

DEBUG = True
WHITENOISE_AUTOREFRESH = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"), conn_max_age=0, ssl_require=False
    )
}


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
        "TIMEOUT": 300,
        "OPTIONS": {"MAX_ENTRIES": 1000},
    }
}
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = "gocab"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "gocabapp": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}