from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
import hashlib
from accounts.models import Agent, Account
from main_api.models import ResearchNode, PeerReview
from main_api.tasks import task_handle_node_deadline, task_sweep_stale_reviews


class CeleryTasksTest(TestCase):
    def setUp(self):
        self.maintainer = Account.objects.create(
            username="maintainer_test", email="test@enlidea.com", balance_blue_stars=1000
        )
        self.coordinator_acc = Account.objects.create(
            username="coordinator", email="coord@enlidea.com", balance_blue_stars=1000
        )
        self.coordinator = Agent.objects.create(
            name="CoordAgent",
            maintainer=self.coordinator_acc,
            api_key_hash=hashlib.sha256("coordhash".encode()).hexdigest(),
        )
        self.worker1 = Agent.objects.create(
            name="Worker1",
            maintainer=self.maintainer,
            api_key_hash=hashlib.sha256("worker1".encode()).hexdigest(),
            orange_stars=10,
        )
        self.worker2 = Agent.objects.create(
            name="Worker2",
            maintainer=self.maintainer,
            api_key_hash=hashlib.sha256("worker2".encode()).hexdigest(),
            orange_stars=10,
        )

        self.node = ResearchNode.objects.create(
            title="Test Deadline Node",
            description="Test Description",
            body="Test Body",
            coordinating_agent=self.coordinator,
            bounty_amount=100,
            required_reviews=3,
            status="open",
            deadline=timezone.now() - timedelta(hours=1),
        )

    def test_handle_node_deadline_open_refunds_stakes(self):
        # Assign an agent who placed a stake
        self.node.assigned_agents.add(self.worker1)
        # Deduct stake
        self.maintainer.balance_blue_stars -= 10
        self.maintainer.save()

        self.assertEqual(self.maintainer.balance_blue_stars, 990)
        self.assertEqual(self.coordinator_acc.balance_blue_stars, 1000)

        task_handle_node_deadline(self.node.id)

        self.node.refresh_from_db()
        self.assertEqual(self.node.status, "failed")

        # Coordinator gets bounty back
        self.coordinator_acc.refresh_from_db()
        self.assertEqual(self.coordinator_acc.balance_blue_stars, 1100)

        # Worker gets stake back
        self.maintainer.refresh_from_db()
        self.assertEqual(self.maintainer.balance_blue_stars, 1000)

    def test_handle_node_deadline_in_progress_slashes_trust(self):
        self.node.status = "in_progress"
        self.node.assigned_agents.add(self.worker1)
        self.node.save()

        # Deduct stake (simulated)
        self.maintainer.balance_blue_stars -= 10
        self.maintainer.save()

        task_handle_node_deadline(self.node.id)

        self.node.refresh_from_db()
        self.assertEqual(self.node.status, "failed")

        # Coordinator gets bounty back
        self.coordinator_acc.refresh_from_db()
        self.assertEqual(self.coordinator_acc.balance_blue_stars, 1100)

        # Worker does NOT get stake back (burns stake)
        self.maintainer.refresh_from_db()
        self.assertEqual(self.maintainer.balance_blue_stars, 990)

        # Worker trust is slashed
        self.worker1.refresh_from_db()
        self.assertEqual(self.worker1.orange_stars, 5)

    def test_sweep_stale_reviews(self):
        # Create a stale review (older than 4 hours, no structured data)
        stale_review = PeerReview.objects.create(
            research_node=self.node,
            assigned_reviewer=self.worker1,
            soundness=0,
            significance=0,
            novelty=0,
            clarity=0,
            value=0.0,
        )
        stale_review.created = timezone.now() - timedelta(hours=5)
        stale_review.save()

        # Create a fresh review
        fresh_review = PeerReview.objects.create(
            research_node=self.node,
            assigned_reviewer=self.worker2,
            soundness=0,
            significance=0,
            novelty=0,
            clarity=0,
            value=0.0,
        )

        # Create a completed review (older than 48 hours, but status is 'completed')
        completed_review = PeerReview.objects.create(
            research_node=self.node,
            assigned_reviewer=self.coordinator,
            status="completed",
            soundness=8,
            significance=8,
            novelty=8,
            clarity=8,
            value=8.0,
            structured_data={"comment": "Done"},
        )
        completed_review.created = timezone.now() - timedelta(days=3)
        completed_review.save()

        # Initial count is 3
        self.assertEqual(PeerReview.objects.count(), 3)

        task_sweep_stale_reviews()

        # Should only delete the stale one
        self.assertEqual(PeerReview.objects.count(), 2)
        self.assertTrue(PeerReview.objects.filter(id=fresh_review.id).exists())
        self.assertTrue(PeerReview.objects.filter(id=completed_review.id).exists())
        self.assertFalse(PeerReview.objects.filter(id=stale_review.id).exists())
