import logging

from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate

from enlidea.constants import TREASURY_USERNAME

logger = logging.getLogger(__name__)


def check_system_identities(sender, **kwargs):
    User = get_user_model()
    try:
        if not User.objects.filter(username=TREASURY_USERNAME).exists():
            logger.warning(
                "System Treasury account missing! Please run 'python manage.py setup_system' to initialize system accounts."
            )
    except Exception as e:
        logger.debug("System identity check skipped: %s", e)


class MainApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "main_api"

    def ready(self):
        post_migrate.connect(check_system_identities, sender=self)
