from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
import math

Account = get_user_model()

class Command(BaseCommand):
    help = 'Calculate and update user (maintainer) ranks based on their agents performance'

    def calculate_score(self, user):
        # Placeholder score calculation for maintainers
        return user.balance_orange_stars + user.balance_blue_stars / 10

    def handle(self, *args, **options):
        with transaction.atomic():
            users = Account.objects.filter(is_active=True)
            users_with_scores = [(user, self.calculate_score(user)) for user in users]
            users_with_scores.sort(key=lambda x: x[1], reverse=True)

            user_updates = []
            for rank, (user, score) in enumerate(users_with_scores[:200], start=1):
                user.rank = rank
                user.score = round(score)
                user_updates.append(user)

            Account.objects.bulk_update(user_updates, ['rank', 'score'])
            Account.objects.filter(is_active=True).exclude(id__in=[user.id for user in user_updates]).update(rank=None, score=None)

        self.stdout.write(self.style.SUCCESS(f'Successfully updated ranks and scores.'))
