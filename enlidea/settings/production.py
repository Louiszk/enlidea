from typing import cast
from urllib.parse import quote_plus

from decouple import Csv, config

from .base import *

SECRET_KEY = config("SECRET_KEY")
DEBUG = False

# Allow production domain(s) plus local loopback and internal docker network hostnames
configured_hosts = cast(list, config("ALLOWED_HOSTS", cast=Csv()))
ALLOWED_HOSTS = configured_hosts + ["127.0.0.1", "backend"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASS"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
        "CONN_MAX_AGE": 60,
        # Keep readiness checks and requests bounded when PostgreSQL is unavailable.
        "OPTIONS": {
            "connect_timeout": 5,
            "options": "-c statement_timeout=5000",
        },
    }
}

REDIS_PASSWORD: str = str(config("REDIS_PASSWORD"))
SAFE_REDIS_PASSWORD = quote_plus(REDIS_PASSWORD)


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://:{SAFE_REDIS_PASSWORD}@redis:6379/1",
        "OPTIONS": {
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
        },
    }
}


# --- TLS / Reverse Proxy Security ---
# Tell Django to trust the X-Forwarded-Proto header sent by Nginx / TLS load balancer
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Production Security Flags (configurable via .env for local HTTP testing if needed)
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_REDIRECT_EXEMPT = [r"^healthz/?$", r"^readyz/?$"]
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)
