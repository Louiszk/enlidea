from django.core.management.base import BaseCommand
from .helpers.trending_service import update_trending_cache


class Command(BaseCommand):
    help = "Updates the trending cache"

    def handle(self, *args, **options):
        update_trending_cache()
        self.stdout.write(self.style.SUCCESS("Successfully updated trending cache"))
