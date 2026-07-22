from .base import *
from decouple import config
from urllib.parse import quote_plus


SECRET_KEY = config("SECRET_KEY")
DEBUG = True

ALLOWED_HOSTS = ["*"]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

import sys

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASS"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
    }
}

if "test" in sys.argv:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_STORE_EAGER_RESULT = True
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }
else:
    DEV_REDIS_PASSWORD = quote_plus(str(config("REDIS_PASSWORD", default="")))

    DEV_REDIS_AUTH = f":{DEV_REDIS_PASSWORD}@" if DEV_REDIS_PASSWORD else ""
    DEV_REDIS_HOST = config("REDIS_HOST", default="localhost")
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": f"redis://{DEV_REDIS_AUTH}{DEV_REDIS_HOST}:6379/1",
        }
    }
