from typing import cast, Any
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
import hashlib
from main_api.models import Capability, ResearchNode, NodeType
from accounts.models import Agent
from decimal import Decimal

User = get_user_model()


class EnlideaBaseTestCase(APITestCase):
    def setUp(self):
        # Create common NodeType
        self.node_type, _ = NodeType.objects.get_or_create(name="Research Node")

        # Create Capabilities
        self.cap_python = Capability.objects.create(title="Python", slug="python")
        self.cap_ai = Capability.objects.create(title="AI", slug="ai")

        # Create Maintainers
        self.maintainer1 = User.objects.create_user(
            email="m1@enlidea.com", username="maintainer1", password="password123", is_active=True
        )
        self.maintainer1.balance_blue_stars = 1000
        self.maintainer1.save()

        self.maintainer2 = User.objects.create_user(
            email="m2@enlidea.com", username="maintainer2", password="password123", is_active=True
        )
        self.maintainer2.balance_blue_stars = 1000
        self.maintainer2.save()

        # Initialize System Treasury
        from main_api.tasks import TREASURY_USERNAME

        self.treasury = User.objects.create_user(
            email="treasury@enlidea.com", username=TREASURY_USERNAME, password="password123", is_active=True
        )
        self.treasury.balance_blue_stars = Decimal("10000.0000")
        self.treasury.save()

        # Create Agents
        self.agent1_raw_key = "key-alpha"
        self.agent1 = Agent.objects.create(
            name="Agent Alpha",
            maintainer=self.maintainer1,
            api_key_hash=hashlib.sha256(self.agent1_raw_key.encode()).hexdigest(),
            orange_stars=Decimal("10.0000"),
        )
        self.agent1.capabilities.add(self.cap_python)

        self.agent2_raw_key = "key-beta"
        self.agent2 = Agent.objects.create(
            name="Agent Beta",
            maintainer=self.maintainer2,
            api_key_hash=hashlib.sha256(self.agent2_raw_key.encode()).hexdigest(),
            orange_stars=Decimal("10.0000"),
        )
        self.agent2.capabilities.add(self.cap_python, self.cap_ai)

    def create_node(self, coordinator, bounty=100, collaborators=1, caps=None, required_reviews=3):
        node = ResearchNode.objects.create(
            title="Test Research Node",
            description="Test Description",
            body="Test Body",
            type=self.node_type,
            coordinating_agent=coordinator,
            bounty_amount=bounty,
            required_collaborators=collaborators,
            required_reviews=required_reviews,
            status="open",
        )
        if caps:
            node.required_capabilities.add(*caps)
        return node


class AgentAuthTests(EnlideaBaseTestCase):
    def test_bid_requires_agent_api_key(self):
        node = self.create_node(self.agent1)
        url = reverse("researchnode-bid", kwargs={"pk": node.pk})

        # Test without API key
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test with standard session auth (should fail for agent-only endpoint)
        self.client.force_authenticate(user=self.maintainer2)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test with valid Agent API Key
        self.client.force_authenticate(user=None)  # Clear session auth
        response = self.client.post(url, {"interview_response": "hello"}, HTTP_X_AGENT_API_KEY=self.agent2_raw_key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bid_missing_capabilities(self):
        # Node requires AI, Agent 1 only has Python
        node = self.create_node(self.agent2, caps=[self.cap_ai])
        url = reverse("researchnode-bid", kwargs={"pk": node.pk})

        response = self.client.post(url, HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Missing required capabilities", cast(Any, response.data)["detail"])
