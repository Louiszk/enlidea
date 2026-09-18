import os

from decouple import config

# Deterministic settings resolution:
# 1. Respect explicit DJANGO_SETTINGS_MODULE if specified.
# 2. Otherwise, select based on DEBUG with a safe, fail-closed default (DEBUG=False -> production).
_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
if _module.endswith(".production"):
    from .production import *
elif _module.endswith(".development") or config("DEBUG", default=False, cast=bool):
    from .development import *
else:
    from .production import *
