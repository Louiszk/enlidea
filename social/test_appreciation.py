from typing import cast, Any
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from main_api.models import ResearchNode, Paper, NodeType
from accounts.models import Agent
from decimal import Decimal

User = get_user_model()


class AppreciationTests(APITestCase):
    def setUp(self):
        # Setup basic data
        self.node_type, _ = NodeType.objects.get_or_create(name="Research")
        self.maintainer1 = User.objects.create_user(
            email="m1@enlidea.com", username="maintainer1", password="password123", is_active=True
        )
        self.maintainer2 = User.objects.create_user(
            email="m2@enlidea.com", username="maintainer2", password="password123", is_active=True
        )

        # Agent for Maintainer 1 (to be author of the paper)
        self.agent1 = Agent.objects.create(
            name="Author Agent", maintainer=self.maintainer1, api_key_hash="hash1", orange_stars=100
        )

        # Agent for Maintainer 2 (to test reputation impact)
        self.agent2 = Agent.objects.create(
            name="Voter Agent", maintainer=self.maintainer2, api_key_hash="hash2", orange_stars=90
        )

        # Create a Paper
        self.node = ResearchNode.objects.create(
            title="Test Paper Node",
            description="Test Abstract",
            body="Test Content",
            type=self.node_type,
            coordinating_agent=self.agent1,
            status="published",
        )
        self.paper = Paper.objects.create(
            research_node=self.node, title=self.node.title, abstract=self.node.description, content=self.node.body
        )
        self.paper.authors.add(self.agent1)

    def test_appreciation_impact_calculation(self):
        """Test that the vote impact is calculated correctly based on reputation."""
        self.client.force_authenticate(user=self.maintainer2)
        url = reverse("appreciate_paper", kwargs={"paper_id": self.paper.id})

        # Vote +2
        response = self.client.post(url, {"vote": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # total_reputation = 90 (from agent2)
        # impact = 2 * max(1.0, log10(90 + 10)) = 2 * log10(100) = 2 * 2.0 = 4.0

        self.paper.refresh_from_db()
        self.assertEqual(self.paper.appreciation_score, Decimal("4.0000"))

        # Change vote to -1
        response = self.client.post(url, {"vote": -1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # impact = -1 * log10(100) = -2.0
        self.paper.refresh_from_db()
        self.assertEqual(self.paper.appreciation_score, Decimal("-2.0000"))

    def test_maintainer_total_appreciation_score(self):
        """Test that the maintainer's total appreciation score aggregates correctly."""
        # Setup: Paper 1 has score -2.0
        self.client.force_authenticate(user=self.maintainer2)
        url = reverse("appreciate_paper", kwargs={"paper_id": self.paper.id})
        self.client.post(url, {"vote": 1})

        # Create Paper 2 for same maintainer
        node2 = ResearchNode.objects.create(
            title="Paper 2",
            description="Abs",
            body="Content",
            type=self.node_type,
            coordinating_agent=self.agent1,
            status="published",
        )
        paper2 = Paper.objects.create(research_node=node2, title="Paper 2", abstract="Abs", content="Content")
        paper2.authors.add(self.agent1)

        url2 = reverse("appreciate_paper", kwargs={"paper_id": paper2.id})
        self.client.post(url2, {"vote": 2})

        self.maintainer1.refresh_from_db()
        # Total should be 2.0 + 4.0 = 6.0
        self.assertEqual(self.maintainer1.total_appreciation_score, Decimal("6.0000"))

    def test_paper_serializer_user_vote(self):
        """Test that PaperSerializer correctly returns user_vote for humans and None for agents."""
        # 1. Human User Vote
        self.client.force_authenticate(user=self.maintainer2)
        reverse("appreciate_paper", kwargs={"paper_id": self.paper.id})
        self.client.post(reverse("appreciate_paper", kwargs={"paper_id": self.paper.id}), {"vote": 2})

        url = reverse("paper-detail", kwargs={"research_node": self.paper.research_node.id})
        response = self.client.get(url)
        self.assertEqual(cast(Any, response.data)["user_vote"], 2)
        self.assertEqual(cast(Any, response.data)["appreciation_score"], "4.0000")

        # 2. Agent (should get None for user_vote and not crash)
        self.client.force_authenticate(user=self.agent2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(cast(Any, response.data)["user_vote"])

        # 3. Unauthenticated (should get None)
        self.client.force_authenticate(user=None)
        response = self.client.get(url)
        self.assertIsNone(cast(Any, response.data)["user_vote"])

    def test_invalid_vote_values(self):
        """Test that only valid votes are accepted."""
        self.client.force_authenticate(user=self.maintainer2)
        url = reverse("appreciate_paper", kwargs={"paper_id": self.paper.id})

        for invalid_vote in [0, 3, -3, 5]:
            response = self.client.post(url, {"vote": invalid_vote})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
