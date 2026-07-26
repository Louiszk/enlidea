from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from decimal import Decimal

Account = get_user_model()


class Command(BaseCommand):
    help = "Calculate and update user (maintainer) ranks based on their agents performance"

    def handle(self, *args, **options):
        with transaction.atomic():
            # Exclude inactive accounts, Public_Pool, and System_Treasury
            excluded_usernames = ["Public_Pool", "System_Treasury"]

            # Single annotated query to eliminate N+1 database queries
            users = (
                Account.objects.filter(is_active=True)
                .exclude(username__in=excluded_usernames)
                .annotate(
                    agent_os_sum=Coalesce(
                        Sum("agents__orange_stars", filter=Q(agents__is_active=True)),
                        Decimal("0.0000"),
                    )
                )
            )

            users_list = []
            for user in users:
                agent_os_sum = user.agent_os_sum
                user.balance_orange_stars = agent_os_sum
                user.score = round(float(agent_os_sum + (user.balance_blue_stars / Decimal("10"))))
                users_list.append(user)

            # Sort maintainers by score descending
            users_list.sort(key=lambda x: x.score, reverse=True)

            # Assign rank 1..200 for top maintainers, set rank=None (Unranked) for rank 201+ while preserving score & balance
            for rank, user in enumerate(users_list, start=1):
                user.rank = rank if rank <= 200 else None

            # Bulk update balance_orange_stars, score, and rank for ALL active maintainers
            Account.objects.bulk_update(users_list, ["balance_orange_stars", "score", "rank"])

        self.stdout.write(self.style.SUCCESS("Successfully updated ranks and scores."))
