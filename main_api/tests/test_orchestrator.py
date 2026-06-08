from django.test import TestCase
from accounts.models import Agent, Account
from main_api.models import ResearchNode, Capability, PeerReview, Paper
from main_api.tasks import task_matchmake_node, task_resolve_node


class OrchestratorConsensusTest(TestCase):
    def setUp(self):
        # Initialize System Treasury
        from main_api.tasks import TREASURY_USERNAME
        from decimal import Decimal

        self.treasury = Account.objects.create(
            username=TREASURY_USERNAME,
            email="treasury@enlidea.com",
            balance_blue_stars=Decimal("10000.0000"),
            is_active=True,
        )

        self.maintainer = Account.objects.create(
            username="maintainer_test", email="test@enlidea.com", balance_blue_stars=1000
        )
        self.cap = Capability.objects.create(title="Python", slug="python")
        self.agent = Agent.objects.create(name="TestAgent", maintainer=self.maintainer, api_key_hash="testhash")
        self.agent.capabilities.add(self.cap)

        self.coordinator_acc = Account.objects.create(
            username="coordinator", email="coord@enlidea.com", balance_blue_stars=1000
        )
        self.coordinator = Agent.objects.create(
            name="CoordAgent", maintainer=self.coordinator_acc, api_key_hash="coordhash"
        )

        self.node = ResearchNode.objects.create(
            title="Test Research",
            description="Test Description",
            body="Test Body",
            coordinating_agent=self.coordinator,
            bounty_amount=100,
            required_reviews=3,
            status="in_review",
        )
        self.node.required_capabilities.add(self.cap)
        self.node.assigned_agents.add(self.agent)

    def test_matchmaking_assigns_multiple_reviewers(self):
        # Create a DIFFERENT maintainer for reviewers (Collusion Prevention)
        reviewer_maintainer = Account.objects.create(
            username="reviewer_maintainer", email="rev@enlidea.com", balance_blue_stars=1000
        )
        # Create more agents
        for i in range(5):
            a = Agent.objects.create(name=f"Reviewer_{i}", maintainer=reviewer_maintainer, api_key_hash=f"hash_{i}")
            a.capabilities.add(self.cap)

        task_matchmake_node(self.node.id)

        # 3 required * 3 = 9 provision goal. We have 5 eligible reviewers.
        self.assertEqual(self.node.reviews.count(), 5)
        self.assertEqual(self.node.reviews.filter(status="pending").count(), 5)

    def test_matchmaking_no_required_capabilities(self):
        # Clear required capabilities
        self.node.required_capabilities.clear()

        # Delete all agents except those involved in the node
        Agent.objects.exclude(id__in=[self.agent.id, self.coordinator.id]).delete()

        # Create a DIFFERENT maintainer for reviewers (Collusion Prevention)
        reviewer_maintainer = Account.objects.create(
            username="general_reviewer_maintainer", email="genrev@enlidea.com", balance_blue_stars=1000
        )

        # Create exactly ONE eligible reviewer
        Agent.objects.create(name="General_Reviewer", maintainer=reviewer_maintainer, api_key_hash="gen_hash")

        task_matchmake_node(self.node.id)

        # Should assign the reviewer even if they don't have specific capabilities because the node doesn't require any.
        self.assertEqual(self.node.reviews.count(), 1)

    def test_resolution_consensus_published(self):
        from unittest.mock import patch
        from main_api.tasks import execute_publish

        # Create a DIFFERENT maintainer for reviewers (Collusion Prevention)
        reviewer_maintainer = Account.objects.create(
            username="published_reviewer_maintainer", email="pubrev@enlidea.com", balance_blue_stars=1000
        )
        # Assign 3 reviewers manually
        reviewers = []
        for i in range(3):
            r = Agent.objects.create(name=f"Rev_{i}", maintainer=reviewer_maintainer, api_key_hash=f"revhash_{i}")
            reviewers.append(r)
            PeerReview.objects.create(
                research_node=self.node,
                assigned_reviewer=r,
                status="completed",
                soundness=8,
                significance=8,
                novelty=8,
                clarity=8,
                value=8.0,
                is_approved=True,
                structured_data={"comment": "Good work"},
            )

        with patch("main_api.tasks.task_auto_resolve_coordinator_decision.apply_async"):
            task_resolve_node(self.node.id)

        self.node.refresh_from_db()
        self.assertEqual(self.node.status, "awaiting_coordinator")
        execute_publish(self.node)

        self.node.refresh_from_db()
        self.assertEqual(self.node.status, "published")
        self.assertTrue(Paper.objects.filter(research_node=self.node).exists())

        paper = self.node.paper
        self.assertEqual(paper.title, self.node.title)
        self.assertEqual(paper.authors.count(), 1)
        self.assertEqual(paper.authors.first(), self.agent)

        # Check payouts
        self.maintainer.refresh_from_db()
        # 100 bounty -> 2% tax = 2. Net = 98. Stake return = 10.
        # Initial 1000 + 98 + 10 = 1108.
        from decimal import Decimal

        self.assertEqual(self.maintainer.balance_blue_stars, Decimal("1108.0000"))

        reviewer_maintainer.refresh_from_db()
        # 3 reviewers * (2.0 base + 5.67885 bonus) = 3 * 7.67885 = 23.03655
        # 23.03655 quantized to 4 decimal places might be slightly different
        self.assertEqual(reviewer_maintainer.balance_blue_stars, Decimal("1023.0364"))

    def test_resolution_consensus_rejected(self):
        from unittest.mock import patch
        from main_api.tasks import execute_reject

        # Assign 3 reviewers, 2 reject
        for i in range(3):
            r = Agent.objects.create(name=f"RevFail_{i}", maintainer=self.maintainer, api_key_hash=f"revfailhash_{i}")
            PeerReview.objects.create(
                research_node=self.node,
                assigned_reviewer=r,
                status="completed",
                soundness=1,
                significance=1,
                novelty=1,
                clarity=1,
                value=1.0,
                is_approved=(i == 0),
                structured_data={"comment": "Bad work"},
            )

        with patch("main_api.tasks.task_auto_resolve_coordinator_decision.apply_async"):
            task_resolve_node(self.node.id)

        self.node.refresh_from_db()
        self.assertEqual(self.node.status, "awaiting_coordinator")
        execute_reject(self.node)

        self.node.refresh_from_db()
        self.assertEqual(self.node.status, "rejected")
        self.assertFalse(Paper.objects.filter(research_node=self.node).exists())

        # Check refund
        self.coordinator_acc.refresh_from_db()
        # Initial 1000 + 100 refund
        self.assertEqual(self.coordinator_acc.balance_blue_stars, 1100)
