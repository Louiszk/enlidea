from typing import cast, Any
from rest_framework import status
from django.urls import reverse
from main_api.models import ResearchKeyword
from .test_agent_auth import EnlideaBaseTestCase


class NodeEditingTests(EnlideaBaseTestCase):
    def setUp(self):
        super().setUp()
        self.node = self.create_node(self.agent1, bounty=100, caps=[self.cap_python])
        self.url = reverse("researchnode-detail", kwargs={"pk": self.node.pk})

    def test_successful_edit_by_coordinator(self):
        """Coordinating agent should be able to edit allowed fields and add keywords."""
        payload = {
            "title": "Updated Research Node Title",
            "body": "Updated detailed body of the research hypothesis. This needs to be a little bit longer so that it exceeds the one hundred and forty character minimum limit that we have on bodies.",
            "description": "Updated description",
            "required_capabilities": [self.cap_ai.id],
            "keywords": ["Machine Learning", "Data Science"],
        }
        response = self.client.patch(self.url, payload, format="json", HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.node.refresh_from_db()
        self.assertEqual(self.node.title, "Updated Research Node Title")
        self.assertEqual(
            self.node.body,
            "Updated detailed body of the research hypothesis. This needs to be a little bit longer so that it exceeds the one hundred and forty character minimum limit that we have on bodies.",
        )
        self.assertIn(self.cap_ai, self.node.required_capabilities.all())

        # Verify Keywords were dynamically created
        keywords = self.node.keywords.values_list("slug", flat=True)
        self.assertIn("machine-learning", keywords)
        self.assertIn("data-science", keywords)

    def test_permission_denied_for_other_agent(self):
        """Another agent should not be able to edit."""
        payload = {"title": "Hacked Title"}
        response = self.client.patch(self.url, payload, format="json", HTTP_X_AGENT_API_KEY=self.agent2_raw_key)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_edit_if_bids_exist(self):
        """Should block edits if an agent has already bid on it."""
        self.node.assigned_agents.add(self.agent2)

        payload = {"title": "Tried to bait and switch"}
        response = self.client.patch(self.url, payload, format="json", HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot edit a node that has active external bids or is no longer open.", cast(Any, response.data)["detail"]
        )

    def test_cannot_edit_if_not_open(self):
        """Should block edits if status is anything other than open."""
        self.node.status = "in_review"
        self.node.save()

        payload = {"title": "Late edit"}
        response = self.client.patch(self.url, payload, format="json", HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bounty_and_status_are_read_only(self):
        """Security check: Agents cannot alter bounty_amount or status via the edit endpoint."""
        original_bounty = self.node.bounty_amount
        original_status = self.node.status

        payload = {"bounty_amount": 10000, "status": "published"}

        response = self.client.patch(self.url, payload, format="json", HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.node.refresh_from_db()
        self.assertEqual(self.node.bounty_amount, original_bounty)
        self.assertEqual(self.node.status, original_status)

    def test_keyword_collision_and_empty_slugs_handled(self):
        """Test that different casing maps to the same slug without throwing IntegrityError and empty slugs are ignored."""
        # Create initial keyword
        kw_obj = ResearchKeyword.objects.create(name="Deep Learning", slug="deep-learning")

        payload = {"keywords": ["deep-learning", "DEEP learning", "😎"]}

        response = self.client.patch(self.url, payload, format="json", HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.node.refresh_from_db()
        keywords = list(self.node.keywords.all())

        self.assertEqual(len(keywords), 1)
        self.assertEqual(keywords[0].slug, "deep-learning")

    def test_cannot_edit_if_pending_bids_exist(self):
        """Should block edits if an agent has a pending bid to prevent bait-and-switch."""
        from main_api.models import Bid

        Bid.objects.create(node=self.node, agent=self.agent2, status="pending", interview_response="My bid")

        payload = {"title": "Impossible new conditions"}
        response = self.client.patch(self.url, payload, format="json", HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot edit a node that has pending bids. Reject or accept pending bids first to avoid bait-and-switch exploits.",
            cast(Any, response.data)["detail"],
        )

    def test_create_node_ignores_custom_deadline(self):
        """Initial deadline must be server-controlled (7 days) and ignore client deadline."""
        from django.utils import timezone
        from datetime import timedelta
        from main_api.models import ResearchNode

        past_deadline = (timezone.now() - timedelta(days=10)).isoformat()
        payload = {
            "title": "Quantum Computing Validation",
            "description": "Validation of quantum computing algorithms for security.",
            "body": "Detailed body of the research hypothesis. This needs to be long enough to pass body validation requirements exceeding 140 characters in total length.",
            "required_capabilities": [self.cap_python.id],
            "type": self.node_type.pk,
            "bounty_amount": "50.0000",
            "deadline": past_deadline,
        }
        res = self.client.post(
            reverse("researchnode-list"),
            payload,
            format="json",
            HTTP_X_AGENT_API_KEY=self.agent1_raw_key,
        )
        if res.status_code != status.HTTP_201_CREATED:
            self.assertEqual(res.status_code, status.HTTP_201_CREATED, msg=f"Error response: {res.data}")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        node_data = cast(dict[str, Any], res.data)
        node_id = node_data["id"]
        created_node = ResearchNode.objects.get(id=node_id)
        # Verify deadline is set in future (~7 days from now), not past
        self.assertIsNotNone(created_node.deadline)
        if created_node.deadline is not None:
            self.assertTrue(created_node.deadline > timezone.now())

    def test_lifecycle_input_bounds_validation(self):
        """Out of bound research_duration_days and required_collaborators should fail validation."""
        base_payload = {
            "title": "Quantum Computing Validation",
            "description": "Validation of quantum computing algorithms for security.",
            "body": "Detailed body of the research hypothesis. This needs to be long enough to pass body validation requirements exceeding 140 characters in total length.",
            "required_capabilities": [self.cap_python.id],
            "type": self.node_type.pk,
            "bounty_amount": "50.0000",
        }

        # Overflow / extreme research_duration_days
        payload_duration = {**base_payload, "research_duration_days": 99999}
        res = self.client.post(
            reverse("researchnode-list"),
            payload_duration,
            format="json",
            HTTP_X_AGENT_API_KEY=self.agent1_raw_key,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Negative / zero collaborators
        payload_collab = {**base_payload, "required_collaborators": 0}
        res = self.client.post(
            reverse("researchnode-list"),
            payload_collab,
            format="json",
            HTTP_X_AGENT_API_KEY=self.agent1_raw_key,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_extend_deadline_bounds(self):
        """Extending deadline with extreme values should fail."""
        extend_url = reverse("researchnode-extend-deadline", kwargs={"pk": self.node.pk})

        # Out of bounds extension
        res = self.client.post(
            extend_url,
            {"days": 999999999999999},
            format="json",
            HTTP_X_AGENT_API_KEY=self.agent1_raw_key,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
