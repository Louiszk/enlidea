from decouple import config

# If DEBUG is True, load development settings. Otherwise, load production.
if config("DEBUG", default=True, cast=bool):
    from .development import *
else:
    from .production import *
