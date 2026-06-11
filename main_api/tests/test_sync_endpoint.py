from typing import cast, Any
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from accounts.models import Account, Agent
from main_api.models import ResearchNode, AgentDirective, NodeType
import hashlib
import time


class SyncEndpointTest(APITestCase):
    def setUp(self):
        # Create maintainer
        self.maintainer = Account.objects.create_user(
            email="maintainer@test.com", username="maintainer", password="password123"
        )
        self.maintainer.balance_blue_stars = 1000
        self.maintainer.is_active = True
        self.maintainer.save()

        # Create agent
        self.raw_api_key = "test-api-key"
        self.hashed_key = hashlib.sha256(self.raw_api_key.encode()).hexdigest()
        self.agent = Agent.objects.create(
            name="Test Agent", maintainer=self.maintainer, api_key_hash=self.hashed_key, orange_stars=50
        )

        self.client.credentials(HTTP_X_AGENT_API_KEY=self.raw_api_key)
        self.url = reverse("agent-sync")

    def test_sync_full_response_no_timestamp(self):
        # Create a directive
        AgentDirective.objects.create(
            maintainer=self.maintainer, agent=self.agent, content="Do something", status="pending"
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(cast(Any, response.data)["agent_meta"]["name"], "Test Agent")
        self.assertEqual(len(cast(Any, response.data)["directives"]), 1)
        self.assertTrue(cast(Any, response.data)["timestamp"] > 0)

    def test_sync_304_when_up_to_date(self):
        # Create initial state
        AgentDirective.objects.create(
            maintainer=self.maintainer, agent=self.agent, content="Initial Task", status="pending"
        )

        response = self.client.get(self.url)
        timestamp = cast(Any, response.data)["timestamp"]

        # Sync with current timestamp -> 304
        response = self.client.get(self.url, {"since_timestamp": timestamp})
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_sync_200_with_all_data_when_state_changes(self):
        # 1. Initial sync
        directive1 = AgentDirective.objects.create(
            maintainer=self.maintainer, agent=self.agent, content="Task 1", status="pending"
        )

        response = self.client.get(self.url)
        ts1 = cast(Any, response.data)["timestamp"]
        self.assertEqual(len(cast(Any, response.data)["directives"]), 1)

        # Small delay to ensure timestamp difference
        time.sleep(0.1)

        # 2. Add second directive
        AgentDirective.objects.create(maintainer=self.maintainer, agent=self.agent, content="Task 2", status="pending")

        # 3. Sync with old timestamp -> 200 with BOTH directives (State-Based)
        response = self.client.get(self.url, {"since_timestamp": ts1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cast(Any, response.data)["directives"]), 2)
        self.assertTrue(cast(Any, response.data)["timestamp"] > ts1)

    def test_sync_state_recovery_after_crash(self):
        # Simulate state with multiple objects
        node_type = NodeType.objects.create(name="Research")
        node = ResearchNode.objects.create(title="Test Node", status="in_progress", type=node_type)
        node.assigned_agents.add(self.agent)

        response = self.client.get(self.url)
        ts_initial = cast(Any, response.data)["timestamp"]

        # New activity
        time.sleep(0.1)
        AgentDirective.objects.create(maintainer=self.maintainer, agent=self.agent, content="New Task")

        # Agent "crashed" and lost its state, but has an old timestamp
        response = self.client.get(self.url, {"since_timestamp": ts_initial})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # It gets everything back, not just the new directive
        self.assertEqual(len(cast(Any, response.data)["assignments"]), 1)
        self.assertEqual(len(cast(Any, response.data)["directives"]), 1)

    def test_sync_200_when_state_shrinks(self):
        # 1. Initial state with a task
        directive = AgentDirective.objects.create(
            maintainer=self.maintainer, agent=self.agent, content="Temp Task", status="pending"
        )
        response = self.client.get(self.url)
        ts_with_task = cast(Any, response.data)["timestamp"]
        self.assertEqual(len(cast(Any, response.data)["directives"]), 1)

        # 2. State Shrinkage: Task is deleted/completed
        directive.delete()

        # 3. Sync with old timestamp -> 200 OK (because ts_with_task != current 0)
        response = self.client.get(self.url, {"since_timestamp": ts_with_task})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cast(Any, response.data)["directives"]), 0)
        self.assertEqual(cast(Any, response.data)["timestamp"], 0)
