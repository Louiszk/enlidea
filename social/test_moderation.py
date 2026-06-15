from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache
import hashlib
from main_api.models import ResearchNode, NodeType
from accounts.models import Agent
from social.models import Report, Complaint, Notification

User = get_user_model()


class ModerationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.node_type, _ = NodeType.objects.get_or_create(name="Research Node")

        self.user = User.objects.create_user(
            email="user@test.com", username="testuser", password="password123", is_active=True
        )
        self.other_user = User.objects.create_user(
            email="other@test.com", username="otheruser", password="password123", is_active=True
        )
        self.third_user = User.objects.create_user(
            email="third@test.com", username="thirduser", password="password123", is_active=True
        )

        self.agent1_raw_key = "agent1-key"
        self.agent1 = Agent.objects.create(
            name="Agent1",
            maintainer=self.user,
            api_key_hash=hashlib.sha256(self.agent1_raw_key.encode()).hexdigest(),
            orange_stars=100,
        )

        self.agent2_raw_key = "agent2-key"
        self.agent2 = Agent.objects.create(
            name="Agent2",
            maintainer=self.other_user,
            api_key_hash=hashlib.sha256(self.agent2_raw_key.encode()).hexdigest(),
            orange_stars=100,
        )

        self.agent3_raw_key = "agent3-key"
        self.agent3 = Agent.objects.create(
            name="Agent3",
            maintainer=self.third_user,
            api_key_hash=hashlib.sha256(self.agent3_raw_key.encode()).hexdigest(),
            orange_stars=100,
        )

        self.node = ResearchNode.objects.create(
            title="Test Node",
            description="Test Description",
            body="Test Body",
            type=self.node_type,
            coordinating_agent=self.agent1,
            status="open",
        )
        self.node.assigned_agents.add(self.agent1, self.agent2, self.agent3)

    def test_report_node_by_user(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("report_content")
        data = {"target_type": "node", "target_id": self.node.id, "reason": "spam", "description": "This is spam"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Report.objects.count(), 1)

    def test_report_account_by_agent_proxy(self):
        url = reverse("report_content")
        data = {
            "target_type": "account",
            "target_id": self.other_user.id,
            "reason": "harassment",
            "description": "He is mean",
        }
        response = self.client.post(url, data, HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.count(), 1)

    def test_auto_kick_consensus(self):
        url = reverse("report_content")

        # Agent 1 reports Agent 2
        data1 = {
            "target_type": "agent",
            "target_id": self.agent2.id,
            "reason": "malicious_activity",
            "description": "He is sabotaging",
            "node_id": self.node.id,
        }
        self.client.post(url, data1, HTTP_X_AGENT_API_KEY=self.agent1_raw_key)

        # Clear rate limit for testing (or use different agent)
        cache.clear()

        # Agent 3 reports Agent 2
        data2 = {
            "target_type": "agent",
            "target_id": self.agent2.id,
            "reason": "malicious_activity",
            "description": "I agree, he is bad",
            "node_id": self.node.id,
        }
        response = self.client.post(url, data2, HTTP_X_AGENT_API_KEY=self.agent3_raw_key)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check if Agent 2 was kicked
        self.assertNotIn(self.agent2, self.node.assigned_agents.all())

        # Check Orange Stars slash (100 -> 85)
        self.agent2.refresh_from_db()
        self.assertEqual(self.agent2.orange_stars, 85)

        # Check Notification for Agent 2's maintainer
        self.assertEqual(Notification.objects.filter(recipient=self.other_user).count(), 1)

    def test_no_auto_kick_on_finalized_node(self):
        # Finalize the node
        self.node.status = "published"
        self.node.save()

        url = reverse("report_content")
        # Two reports would normally trigger a kick
        data1 = {
            "target_type": "agent",
            "target_id": self.agent2.id,
            "reason": "malicious_activity",
            "description": "He is bad",
            "node_id": self.node.id,
        }
        self.client.post(url, data1, HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        cache.clear()

        data2 = {
            "target_type": "agent",
            "target_id": self.agent2.id,
            "reason": "malicious_activity",
            "description": "I agree",
            "node_id": self.node.id,
        }
        self.client.post(url, data2, HTTP_X_AGENT_API_KEY=self.agent3_raw_key)

        # Check if Agent 2 was NOT kicked
        self.assertIn(self.agent2, self.node.assigned_agents.all())
        # Status should still be published
        self.node.refresh_from_db()
        self.assertEqual(self.node.status, "published")

    def test_auto_kick_deadlock_coordinator_in_workers(self):
        """When the coordinator is one of the two deadlocked workers, it requires admin intervention."""
        # 2 workers only (agent1 is coordinator and a worker)
        self.node.assigned_agents.remove(self.agent3)

        url = reverse("report_content")
        data = {
            "target_type": "agent",
            "target_id": self.agent2.id,
            "reason": "malicious_activity",
            "description": "1v1 deadlock test",
            "node_id": self.node.id,
        }

        admin = User.objects.create_superuser(username="admin_test", email="admin@enlidea.com", password="password")

        response = self.client.post(url, data, HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Agent 2 should NOT be kicked
        self.assertIn(self.agent2, self.node.assigned_agents.all())

        # Should notify all superusers
        self.assertTrue(Notification.objects.filter(recipient=admin).exists())

    def test_auto_kick_deadlock_coordinator_external_gets_directive(self):
        """When coordinator is external to the deadlock, they receive a directive to break the tie."""
        from main_api.models import AgentDirective

        # 2 workers only (agent2 and agent3). Coordinator (agent1) is NOT a worker.
        self.node.assigned_agents.remove(self.agent1)

        url = reverse("report_content")
        data = {
            "target_type": "agent",
            "target_id": self.agent3.id,
            "reason": "malicious_activity",
            "description": "I think agent3 is bad",
            "node_id": self.node.id,
        }

        response = self.client.post(url, data, HTTP_X_AGENT_API_KEY=self.agent2_raw_key)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Agent 3 should NOT be kicked yet
        self.assertIn(self.agent3, self.node.assigned_agents.all())

        # Coordinator should get an AgentDirective
        self.assertTrue(AgentDirective.objects.filter(agent=self.agent1, status="pending").exists())

    def test_auto_kick_deadlock_coordinator_external_breaks_tie(self):
        """When coordinator is external and reports a worker, the tie is instantly broken."""
        # 2 workers only (agent2 and agent3). Coordinator (agent1) is NOT a worker.
        self.node.assigned_agents.remove(self.agent1)

        url = reverse("report_content")

        # Coordinator (agent1) reports agent3 first
        coord_data = {
            "target_type": "agent",
            "target_id": self.agent3.id,
            "reason": "malicious_activity",
            "description": "I agree with agent2",
            "node_id": self.node.id,
        }
        self.client.post(url, coord_data, HTTP_X_AGENT_API_KEY=self.agent1_raw_key)

        # Agent2 reports agent3, triggering the deadlock check
        worker_data = {
            "target_type": "agent",
            "target_id": self.agent3.id,
            "reason": "malicious_activity",
            "description": "Agent3 is bad",
            "node_id": self.node.id,
        }
        response = self.client.post(url, worker_data, HTTP_X_AGENT_API_KEY=self.agent2_raw_key)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Agent 3 SHOULD be kicked because the coordinator broke the tie
        self.assertNotIn(self.agent3, self.node.assigned_agents.all())

    def test_submit_complaint_by_user(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("submit_complaint")
        data = {"category": "platform_issue", "description": "The site is slow", "reference_id": "123"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Complaint.objects.count(), 1)
