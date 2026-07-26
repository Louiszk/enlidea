from typing import cast, Any
from rest_framework import status
from django.urls import reverse
from accounts.models import Agent
from .test_agent_auth import EnlideaBaseTestCase
from decimal import Decimal


class AgentManagementTests(EnlideaBaseTestCase):
    def test_agent_limit_per_maintainer(self):
        url = reverse("agent-list")
        self.client.force_authenticate(user=self.maintainer1)

        # Maintainer needs 5.0 OS to deploy agents now
        self.maintainer1.balance_orange_stars = Decimal("10.0000")
        self.maintainer1.save()

        for i in range(3):
            response = self.client.post(url, {"name": f"Extra Agent {i}"})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify count is 4
        self.assertEqual(Agent.objects.filter(maintainer=self.maintainer1).count(), 4)

        # Attempt to create the 5th agent
        response = self.client.post(url, {"name": "Illegal 5th Agent"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            cast(Any, response.data)["detail"], "Agent limit reached. You can only deploy a maximum of 4 agents."
        )

    def test_agent_revoke_and_destroy_disassociation(self):
        from main_api.models import ResearchNode
        from main_api.tasks import TREASURY_USERNAME
        from accounts.models import Account

        treasury, _ = Account.objects.get_or_create(
            username=TREASURY_USERNAME,
            defaults={"email": "treasury2@example.com", "balance_blue_stars": Decimal("100.0000")},
        )

        node = ResearchNode.objects.create(
            title="Node For Agent Revocation Test",
            description="Testing agent revocation disassociation",
            body="Body text",
            coordinating_agent=self.agent1,
            bounty_amount=Decimal("10.0000"),
            status="in_progress",
            required_collaborators=1,
        )
        node.assigned_agents.set([self.agent2])

        # Maintainer 2 revokes agent 2 via POST /api/v1/agents/{id}/revoke/
        self.client.force_authenticate(user=self.maintainer2)
        revoke_url = reverse("agent-revoke", kwargs={"pk": self.agent2.pk})
        res = self.client.post(revoke_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.agent2.refresh_from_db()
        self.assertFalse(self.agent2.is_active)

        # Agent 2 should be disassociated and node status reverted to open
        node.refresh_from_db()
        self.assertNotIn(self.agent2, node.assigned_agents.all())
        self.assertEqual(node.status, "open")

    def test_agent_both_coordinator_and_worker_disassociation(self):
        from main_api.models import ResearchNode
        from main_api.tasks import TREASURY_USERNAME
        from accounts.models import Account

        treasury, _ = Account.objects.get_or_create(
            username=TREASURY_USERNAME,
            defaults={"email": "treasury3@example.com", "balance_blue_stars": Decimal("100.0000")},
        )

        initial_worker_balance = self.maintainer2.balance_blue_stars

        # Create active node where agent1 is BOTH coordinator and assigned worker, and agent2 is also a worker
        node = ResearchNode.objects.create(
            title="Dual Role Node",
            description="Testing dual role agent revocation",
            body="Body text",
            coordinating_agent=self.agent1,
            bounty_amount=Decimal("10.0000"),
            status="in_progress",
            required_collaborators=2,
        )
        node.assigned_agents.set([self.agent1, self.agent2])

        # Revoke agent1 (the coordinator & worker)
        self.client.force_authenticate(user=self.maintainer1)
        revoke_url = reverse("agent-revoke", kwargs={"pk": self.agent1.pk})
        res = self.client.post(revoke_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        node.refresh_from_db()
        # Node coordinated by revoked agent should be set to failed
        self.assertEqual(node.status, "failed")

        # Worker agent2 from maintainer2 should have their stake refunded (10 * 0.10 = 1.0000 -> min 2.0000)
        self.maintainer2.refresh_from_db()
        self.assertEqual(self.maintainer2.balance_blue_stars, initial_worker_balance + Decimal("2.0000"))
