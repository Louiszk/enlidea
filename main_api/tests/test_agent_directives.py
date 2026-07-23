from typing import cast, Any
import hashlib
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from accounts.models import Agent
from main_api.models import AgentDirective

User = get_user_model()


class AgentDirectiveTests(APITestCase):
    def setUp(self):
        # Create a maintainer
        self.maintainer = User.objects.create_user(
            email="m@test.com", username="maintainer", password="password123", is_active=True
        )

        # Create an agent for the maintainer
        self.raw_api_key = "test-api-key"
        self.hashed_key = hashlib.sha256(self.raw_api_key.encode()).hexdigest()
        self.agent = Agent.objects.create(
            name="TestAgent", maintainer=self.maintainer, api_key_hash=self.hashed_key, is_active=True
        )

        # URL for directives
        self.list_url = reverse("directive-list")
        self.sync_url = reverse("directive-agent-sync")

    def test_maintainer_can_issue_directive(self):
        self.client.force_authenticate(user=self.maintainer)
        data = {"agent": self.agent.id, "content": "Check the research node 123"}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AgentDirective.objects.count(), 1)
        directive = AgentDirective.objects.first()
        assert directive is not None
        self.assertEqual(directive.maintainer, self.maintainer)
        self.assertEqual(directive.agent, self.agent)
        self.assertEqual(directive.status, "pending")

    def test_maintainer_only_sees_own_directives(self):
        # Create another maintainer and directive
        other_user = User.objects.create_user(email="o@test.com", username="other", password="password", is_active=True)
        AgentDirective.objects.create(maintainer=other_user, content="Other content")

        # Issuing own directive
        AgentDirective.objects.create(maintainer=self.maintainer, content="My content")

        self.client.force_authenticate(user=self.maintainer)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cast(Any, response.data)), 1)
        self.assertEqual(cast(Any, response.data)[0]["content"], "My content")

    def test_agent_can_sync_pending_directives(self):
        # Issue a directive
        directive = AgentDirective.objects.create(
            maintainer=self.maintainer, agent=self.agent, content="Test task", status="pending"
        )

        # Issue another one that is already in progress
        AgentDirective.objects.create(
            maintainer=self.maintainer, agent=self.agent, content="Already started", status="in_progress"
        )

        # Sync with API Key
        self.client.credentials(HTTP_X_AGENT_API_KEY=self.raw_api_key)
        response = self.client.get(self.sync_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cast(Any, response.data)), 1)
        self.assertEqual(cast(Any, response.data)[0]["content"], "Test task")

    def test_agent_can_sync_broadcast_directives(self):
        # Broadcast directive (agent is null)
        AgentDirective.objects.create(
            maintainer=self.maintainer, agent=None, content="Global broadcast", status="pending"
        )

        self.client.credentials(HTTP_X_AGENT_API_KEY=self.raw_api_key)
        response = self.client.get(self.sync_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cast(Any, response.data)), 1)
        self.assertEqual(cast(Any, response.data)[0]["content"], "Global broadcast")

    def test_agent_can_update_directive_status(self):
        directive = AgentDirective.objects.create(
            maintainer=self.maintainer, agent=self.agent, content="Update me", status="pending"
        )

        self.client.credentials(HTTP_X_AGENT_API_KEY=self.raw_api_key)
        data = {"id": directive.id, "status": "in_progress"}
        response = self.client.patch(self.sync_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        directive.refresh_from_db()
        self.assertEqual(directive.status, "in_progress")

    def test_agent_cannot_update_others_directive(self):
        # Other agent
        other_agent = Agent.objects.create(name="OtherAgent", maintainer=self.maintainer, api_key_hash="other-hash")
        directive = AgentDirective.objects.create(
            maintainer=self.maintainer, agent=other_agent, content="Not yours", status="pending"
        )

        self.client.credentials(HTTP_X_AGENT_API_KEY=self.raw_api_key)
        data = {"id": directive.id, "status": "completed"}
        response = self.client.patch(self.sync_url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        directive.refresh_from_db()
        self.assertEqual(directive.status, "pending")

    def test_agent_can_update_directive_with_response(self):
        directive = AgentDirective.objects.create(
            maintainer=self.maintainer, agent=self.agent, content="Update me with response", status="pending"
        )

        self.client.credentials(HTTP_X_AGENT_API_KEY=self.raw_api_key)
        data = {"id": directive.id, "status": "completed", "agent_response": "Terminal Output Test"}
        response = self.client.patch(self.sync_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        directive.refresh_from_db()
        self.assertEqual(directive.status, "completed")
        self.assertEqual(directive.agent_response, "Terminal Output Test")

    def test_agent_claiming_broadcast_directive(self):
        # Broadcast directive (agent is null)
        directive = AgentDirective.objects.create(
            maintainer=self.maintainer, agent=None, content="Global broadcast", status="pending"
        )

        self.client.credentials(HTTP_X_AGENT_API_KEY=self.raw_api_key)
        data = {"id": directive.id, "status": "in_progress"}
        response = self.client.patch(self.sync_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        directive.refresh_from_db()
        self.assertEqual(directive.status, "in_progress")
        self.assertEqual(directive.agent, self.agent)

    def test_maintainer_cannot_issue_directive_to_other_maintainers_agent(self):
        other_user = User.objects.create_user(
            email="other@test.com", username="other_maintainer", password="password123"
        )
        other_agent = Agent.objects.create(name="OtherAgent", maintainer=other_user, api_key_hash="hash_other")

        self.client.force_authenticate(user=self.maintainer)
        data = {"agent": other_agent.id, "content": "Unauthorized cross-tenant directive"}
        response = self.client.post(self.list_url, data)
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])
        self.assertEqual(AgentDirective.objects.filter(content="Unauthorized cross-tenant directive").count(), 0)

    def test_agent_cannot_claim_other_maintainers_broadcast_directive(self):
        other_user = User.objects.create_user(
            email="other2@test.com", username="other_maintainer2", password="password123"
        )
        other_broadcast = AgentDirective.objects.create(
            maintainer=other_user, agent=None, content="Other tenant broadcast", status="pending"
        )

        self.client.credentials(HTTP_X_AGENT_API_KEY=self.raw_api_key)
        data = {"id": other_broadcast.id, "status": "completed", "agent_response": "Malicious claim"}
        response = self.client.patch(self.sync_url, data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        other_broadcast.refresh_from_db()
        self.assertEqual(other_broadcast.status, "pending")
        self.assertIsNone(other_broadcast.agent)

    def test_agent_cannot_sync_other_maintainers_targeted_directive(self):
        other_user = User.objects.create_user(
            email="other3@test.com", username="other_maintainer3", password="password123"
        )
        AgentDirective.objects.create(
            maintainer=other_user, agent=self.agent, content="Forged cross-tenant target", status="pending"
        )

        self.client.credentials(HTTP_X_AGENT_API_KEY=self.raw_api_key)
        response = self.client.get(self.sync_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cast(Any, response.data)), 0)
