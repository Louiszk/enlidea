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

        # 3. Sync with old timestamp -> 200 OK (because ts_with_task != current agent timestamp)
        response = self.client.get(self.url, {"since_timestamp": ts_with_task})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cast(Any, response.data)["directives"]), 0)
        self.assertGreater(cast(Any, response.data)["timestamp"], 0)

    def test_sync_privacy(self):
        """Ensure directives with agent=None are only broadcasted to agents of the same maintainer."""
        # Create another maintainer and agent
        other_maintainer = Account.objects.create_user(email="other@test.com", username="other", password="password123")
        other_agent = Agent.objects.create(
            name="Other Agent", maintainer=other_maintainer, api_key_hash="hash2", orange_stars=50
        )

        # Other maintainer broadcasts a directive
        AgentDirective.objects.create(
            maintainer=other_maintainer, agent=None, content="Secret broadcast", status="pending"
        )

        # Our maintainer broadcasts a directive
        AgentDirective.objects.create(maintainer=self.maintainer, agent=None, content="Our broadcast", status="pending")

        # Our agent syncs
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        directives = cast(Any, response.data)["directives"]
        self.assertEqual(len(directives), 1)
        self.assertEqual(directives[0]["content"], "Our broadcast")

    def test_sync_200_when_review_claimed(self):
        """Ensure claiming a review updates updated_at and triggers 200 OK on sync."""
        from main_api.models import PeerReview

        node_type = NodeType.objects.create(name="Paper")
        node = ResearchNode.objects.create(title="Review Node", status="in_review", type=node_type)
        review = PeerReview.objects.create(assigned_reviewer=self.agent, research_node=node, status="pending")

        response = self.client.get(self.url)
        data = cast(Any, response.data)
        ts_initial = data["timestamp"]
        self.assertEqual(data["pending_reviews"][0]["status"], "pending")

        time.sleep(0.05)
        # Agent claims review
        from django.utils import timezone

        review.status = "claimed"
        review.claimed_at = timezone.now()
        review.save(update_fields=["status", "claimed_at", "updated_at"])

        response = self.client.get(self.url, {"since_timestamp": ts_initial})
        data2 = cast(Any, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data2["pending_reviews"][0]["status"], "claimed")
        self.assertGreater(data2["timestamp"], ts_initial)

    def test_sync_200_when_directive_completed(self):
        """Ensure completing a directive advances timestamp and returns 200 with updated list."""
        d1 = AgentDirective.objects.create(maintainer=self.maintainer, agent=self.agent, content="D1", status="pending")
        d2 = AgentDirective.objects.create(maintainer=self.maintainer, agent=self.agent, content="D2", status="pending")

        response = self.client.get(self.url)
        data = cast(Any, response.data)
        ts_initial = data["timestamp"]
        self.assertEqual(len(data["directives"]), 2)

        time.sleep(0.05)
        d2.status = "completed"
        d2.save(update_fields=["status", "updated_at"])

        response = self.client.get(self.url, {"since_timestamp": ts_initial})
        data2 = cast(Any, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data2["directives"]), 1)
        self.assertEqual(data2["directives"][0]["content"], "D1")
        self.assertGreater(data2["timestamp"], ts_initial)

    def test_sync_200_when_agent_capabilities_changed(self):
        """Ensure adding capabilities updates Agent.updated_at via signal and returns 200 on sync."""
        from main_api.models import Capability

        cap = Capability.objects.create(title="Python", slug="python")

        response = self.client.get(self.url)
        data = cast(Any, response.data)
        ts_initial = data["timestamp"]

        time.sleep(0.05)
        self.agent.capabilities.add(cap)

        response = self.client.get(self.url, {"since_timestamp": ts_initial})
        data2 = cast(Any, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("python", data2["agent_meta"]["capabilities"])
        self.assertGreater(data2["timestamp"], ts_initial)

    def test_sync_200_when_worker_bid_rejected(self):
        """Ensure worker agent gets 200 OK sync when its submitted bid status is updated."""
        from main_api.models import Bid

        node_type = NodeType.objects.create(name="Research")
        node = ResearchNode.objects.create(title="Bid Node", status="open", type=node_type)
        bid = Bid.objects.create(node=node, agent=self.agent, status="pending")

        response = self.client.get(self.url)
        data = cast(Any, response.data)
        ts_initial = data["timestamp"]

        time.sleep(0.05)
        bid.status = "rejected"
        bid.save(update_fields=["status", "updated_at"])

        response = self.client.get(self.url, {"since_timestamp": ts_initial})
        data2 = cast(Any, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(data2["timestamp"], ts_initial)

    def test_sync_200_when_maintainer_balance_changed(self):
        """Ensure agent gets 200 OK sync when maintainer Blue Star balance changes."""
        from accounts.models import Account
        from decimal import Decimal
        from django.db.models import F
        from django.utils import timezone

        response = self.client.get(self.url)
        data = cast(Any, response.data)
        ts_initial = data["timestamp"]

        time.sleep(0.05)
        Account.objects.filter(id=self.maintainer.id).update(
            balance_blue_stars=F("balance_blue_stars") + Decimal("50.0000"),
            updated_at=timezone.now(),
        )

        response = self.client.get(self.url, {"since_timestamp": ts_initial})
        data2 = cast(Any, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(data2["timestamp"], ts_initial)

    def test_sync_200_when_m2m_cleared(self):
        """Ensure clearing M2M relationships (pre_clear) bumps timestamp and triggers 200 OK sync."""
        from main_api.models import Capability

        cap = Capability.objects.create(title="GPU", slug="gpu")
        self.agent.capabilities.add(cap)

        response = self.client.get(self.url)
        data = cast(Any, response.data)
        ts_initial = data["timestamp"]

        time.sleep(0.05)
        cap.agents.clear()

        response = self.client.get(self.url, {"since_timestamp": ts_initial})
        data2 = cast(Any, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("gpu", data2["agent_meta"]["capabilities"])
        self.assertGreater(data2["timestamp"], ts_initial)

    def test_sync_200_when_assigned_agents_removed_and_cleared(self):
        """Ensure removing or clearing assigned_agents triggers 200 OK sync for workers."""
        node_type = NodeType.objects.create(name="Paper")
        node = ResearchNode.objects.create(title="Assigned Node", status="in_progress", type=node_type)
        node.assigned_agents.add(self.agent)

        response = self.client.get(self.url)
        data = cast(Any, response.data)
        ts_initial = data["timestamp"]

        time.sleep(0.05)
        # 1. Remove agent from assigned_agents
        node.assigned_agents.remove(self.agent)

        response = self.client.get(self.url, {"since_timestamp": ts_initial})
        data2 = cast(Any, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(data2["timestamp"], ts_initial)
        ts_second = data2["timestamp"]

        time.sleep(0.05)
        # 2. Add back and clear via node.assigned_agents.clear() (pre_clear)
        node.assigned_agents.add(self.agent)
        node.assigned_agents.clear()

        response = self.client.get(self.url, {"since_timestamp": ts_second})
        data3 = cast(Any, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(data3["timestamp"], ts_second)

    def test_sync_two_agents_under_one_maintainer_balance_mutation(self):
        """Ensure Agent B gets 200 OK sync and updated balance when Agent A mutates maintainer balance."""
        from decimal import Decimal
        from main_api.tasks import TREASURY_USERNAME

        Account.objects.get_or_create(
            username=TREASURY_USERNAME,
            defaults={"email": "treasury@test.com", "balance_blue_stars": Decimal("1000.0000"), "is_active": True},
        )

        raw_key_b = "test-api-key-b"
        hashed_key_b = hashlib.sha256(raw_key_b.encode()).hexdigest()
        agent_b = Agent.objects.create(
            name="Agent B", maintainer=self.maintainer, api_key_hash=hashed_key_b, is_active=True
        )

        # Sync Agent B initially
        self.client.credentials(HTTP_X_AGENT_API_KEY=raw_key_b)
        res_b = self.client.get(self.url)
        data_b = cast(Any, res_b.data)
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)
        ts_b_initial = data_b["timestamp"]
        initial_balance = data_b["balances"]["blue_stars"]

        # Agent A creates a node (deducting creation fee from shared maintainer)
        from main_api.services import create_research_node

        time.sleep(0.05)
        node_type = NodeType.objects.create(name="Code")
        create_research_node(
            agent=self.agent,
            validated_data={
                "title": "Node by Agent A",
                "body": "Content",
                "type": node_type,
                "bounty_amount": Decimal("10.0000"),
            },
        )

        # Sync Agent B with its old timestamp
        res_b_after = self.client.get(self.url, {"since_timestamp": ts_b_initial})
        data_b2 = cast(Any, res_b_after.data)
        self.assertEqual(res_b_after.status_code, status.HTTP_200_OK)
        self.assertGreater(data_b2["timestamp"], ts_b_initial)
        self.assertNotEqual(data_b2["balances"]["blue_stars"], initial_balance)

    def test_sync_200_after_review_claim_endpoint(self):
        """Ensure claiming a review via endpoint response triggers 200 OK on sync."""
        from main_api.models import PeerReview

        node_type = NodeType.objects.create(name="Paper")
        node = ResearchNode.objects.create(title="Review Claim Node", status="in_review", type=node_type)
        review = PeerReview.objects.create(assigned_reviewer=self.agent, research_node=node, status="pending")

        response = self.client.get(self.url)
        data = cast(Any, response.data)
        ts_initial = data["timestamp"]

        time.sleep(0.05)
        # Agent claims review via DRF ViewSet action
        url_respond = reverse("peerreview-respond", kwargs={"pk": review.id})
        response_claim = self.client.post(url_respond, {"action": "claim"}, format="json")
        self.assertEqual(response_claim.status_code, status.HTTP_200_OK)

        response_sync = self.client.get(self.url, {"since_timestamp": ts_initial})
        data2 = cast(Any, response_sync.data)
        self.assertEqual(response_sync.status_code, status.HTTP_200_OK)
        self.assertEqual(data2["pending_reviews"][0]["status"], "claimed")
        self.assertGreater(data2["timestamp"], ts_initial)
