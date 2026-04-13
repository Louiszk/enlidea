from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from main_api.models import ResearchNode, PeerReview
from accounts.models import Agent
from django.utils import timezone
from datetime import timedelta
from main_api.tasks import task_matchmake_node
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

class TestMatchmaking(TestCase):
    def setUp(self):
        self.maintainer = User.objects.create_user(username='test_maintainer', email='test@test.com', password='password')
        
        # Create some agents
        self.agents = []
        for i in range(15):
            agent = Agent.objects.create(
                name=f'Agent_{i}',
                maintainer=self.maintainer,
                orange_stars=Decimal('5.0000'),
                last_active_at=timezone.now(),
                api_key_hash=f'hash_{i}'
            )
            self.agents.append(agent)

        self.other_user = User.objects.create_user(username='other', email='other@test.com', password='p')
        self.coordinator = Agent.objects.create(name='Coordinator', maintainer=self.other_user, api_key_hash='coord_hash')

        self.node = ResearchNode.objects.create(
            title='Test Broadcast Node',
            description='Test Description',
            body='Test Body' * 50,
            status='in_review',
            required_reviews=3,
            bounty_amount=Decimal('10.0000'),
            coordinating_agent=self.coordinator
        )

    def test_over_provisioning(self):
        """Test that task_matchmake_node creates N*3 pending reviews."""
        task_matchmake_node(self.node.id)
        
        # Required is 3, so should have 9 pending reviews
        pending_count = PeerReview.objects.filter(research_node=self.node, status='pending').count()
        self.assertEqual(pending_count, 9)

    def test_claim_protocol(self):
        """Test that claiming a review works and cleans up when quota met."""
        task_matchmake_node(self.node.id)
        pending_reviews = list(PeerReview.objects.filter(research_node=self.node, status='pending'))
        
        # Agent 1 claims
        review1 = pending_reviews[0]
        agent_client = APIClient()
        agent_client.force_authenticate(user=review1.assigned_reviewer)
        
        url = reverse('peerreview-respond', kwargs={'pk': review1.id})
        response = agent_client.post(url, {'action': 'claim'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        review1.refresh_from_db()
        self.assertEqual(review1.status, 'claimed')
        self.assertIsNotNone(review1.claimed_at)

        # Quota is 3. We have 1 claimed. 8 still pending.
        self.assertEqual(PeerReview.objects.filter(research_node=self.node, status='pending').count(), 8)
        
        # Agent 2 claims
        review2 = pending_reviews[1]
        agent_client.force_authenticate(user=review2.assigned_reviewer)
        agent_client.post(reverse('peerreview-respond', kwargs={'pk': review2.id}), {'action': 'claim'})
        
        # Agent 3 claims - this should hit the quota of 3
        review3 = pending_reviews[2]
        agent_client.force_authenticate(user=review3.assigned_reviewer)
        response = agent_client.post(reverse('peerreview-respond', kwargs={'pk': review3.id}), {'action': 'claim'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Now quota (3) is met. All other pending (6) should be deleted.
        self.assertEqual(PeerReview.objects.filter(research_node=self.node, status='pending').count(), 0)
        self.assertEqual(PeerReview.objects.filter(research_node=self.node, status='claimed').count(), 3)

    def test_reject_and_refill(self):
        """Test that rejecting a review triggers a refill if below quota."""
        # Initial matchmaking
        task_matchmake_node(self.node.id)
        self.assertEqual(PeerReview.objects.filter(research_node=self.node, status='pending').count(), 9)
        
        # Reject one
        review = PeerReview.objects.filter(research_node=self.node, status='pending').first()
        agent_client = APIClient()
        agent_client.force_authenticate(user=review.assigned_reviewer)
        
        url = reverse('peerreview-respond', kwargs={'pk': review.id})
        agent_client.post(url, {'action': 'reject'})
        
        # Reject enough to trigger refill
        remaining = list(PeerReview.objects.filter(research_node=self.node, status='pending'))
        # Currently 8 pending. We need to reject 6 more to reach 2 pending.
        for r in remaining[:6]:
             agent_client.force_authenticate(user=r.assigned_reviewer)
             agent_client.post(reverse('peerreview-respond', kwargs={'pk': r.id}), {'action': 'reject'})
        
        # Now we have 2 pending. 2 < 3. Refill should have been triggered (but it's .delay())
        self.assertEqual(PeerReview.objects.filter(research_node=self.node, status='pending').count(), 2)
