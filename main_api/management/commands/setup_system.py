import hashlib
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from accounts.models import Agent
from main_api.models import NodeType, Capability
from decouple import config
from django.conf import settings
from django.utils.text import slugify

User = get_user_model()


class Command(BaseCommand):
    help = "Bootstraps the Enlidea system with necessary identities, treasury, and public pool."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("--- Enlidea System Bootstrap ---"))

        # 1. System Treasury
        self.stdout.write("\n1. Configuring System Treasury...")
        treasury_email = (
            config("TREASURY_EMAIL", default="treasury@enlidea.com") if settings.DEBUG else config("TREASURY_EMAIL")
        )
        treasury_username = "System_Treasury"

        treasury_acc, created = User.objects.get_or_create(
            username=treasury_username,
            defaults={
                "email": treasury_email,
                "balance_blue_stars": Decimal("10000.0000"),
                "is_active": True,
                "is_staff": True,
                "is_admin": True,
                "is_superuser": True,
            },
        )

        if created:
            # Set a random password for system accounts
            treasury_acc.set_password(get_random_string(32))
            treasury_acc.save()
            self.stdout.write(self.style.SUCCESS(f"Successfully created {treasury_username} account."))
        else:
            self.stdout.write(f"{treasury_username} account already exists.")

        # 2. Treasury Orchestrator Agent
        treasury_key = (
            config("TREASURY_AGENT_KEY", default=get_random_string(32))
            if settings.DEBUG
            else config("TREASURY_AGENT_KEY")
        )
        hashed_key = hashlib.sha256(treasury_key.encode()).hexdigest()

        agent, created = Agent.objects.get_or_create(
            name="Treasury_Orchestrator",
            defaults={
                "maintainer": treasury_acc,
                "api_key_hash": hashed_key,
                "orange_stars": Decimal("1000.0000"),
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS("Successfully created Treasury_Orchestrator agent."))
            if config("TREASURY_AGENT_KEY", default=None) is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"WARNING: TREASURY_AGENT_KEY was not found in .env. Generated a random one: {treasury_key}"
                    )
                )
        else:
            self.stdout.write("Treasury_Orchestrator agent already exists.")

        # 3. Public Pool Account
        self.stdout.write("\n2. Configuring Public Pool...")
        public_pool_username = "Public_Pool"
        public_pool_email = (
            config("PUBLIC_POOL_EMAIL", default="public_pool@enlidea.com")
            if settings.DEBUG
            else config("PUBLIC_POOL_EMAIL")
        )

        public_acc, created = User.objects.get_or_create(
            username=public_pool_username,
            defaults={
                "email": public_pool_email,
                "balance_blue_stars": Decimal("0.0000"),
                "is_active": True,
                "is_staff": False,
            },
        )

        if created:
            public_acc.set_password(get_random_string(32))
            public_acc.save()
            self.stdout.write(self.style.SUCCESS(f"Successfully created {public_pool_username} account."))
        else:
            self.stdout.write(f"{public_pool_username} account already exists.")

        # 4. Node Types
        self.stdout.write("\n3. Populating Node Types...")
        node_types = ["Research Node", "Hypothesis", "Algorithm", "Dataset"]
        for nt_name in node_types:
            nt, created = NodeType.objects.get_or_create(name=nt_name)
            if created:
                self.stdout.write(f"Created NodeType: {nt_name}")

        # 5. Capabilities
        self.stdout.write("\n4. Populating Base Capabilities...")
        capabilities = [
            "Code Execution",
            "Web Search",
            "Image Generation",
            "Image Analysis",
            "GPU Access",
            "OpenAI API",
            "Anthropic API",
        ]
        for cap_name in capabilities:
            cap, created = Capability.objects.get_or_create(title=cap_name, defaults={"slug": slugify(cap_name)})
            if created:
                self.stdout.write(f"Created Capability: {cap_name}")

        self.stdout.write(self.style.SUCCESS("\n--- System Bootstrap Complete ---"))
