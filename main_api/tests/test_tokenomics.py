from .test_agent_auth import EnlideaBaseTestCase
from accounts.models import Agent, Account
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from main_api.models import ResearchNode
from main_api.models import ResearchNode, PeerReview, Paper
from main_api.tasks import task_resolve_node, task_handle_node_deadline
from main_api.tests.test_agent_auth import EnlideaBaseTestCase
from rest_framework import status
import hashlib
import math

User = get_user_model()

class TokenomicsTests(EnlideaBaseTestCase):
    
    def test_agent_deployment_fee(self):
        url = reverse('agent-list')
        self.client.force_authenticate(user=self.maintainer1)
        
        # Maintainer needs 5.0 OS to deploy agents now
        self.maintainer1.balance_orange_stars = Decimal('10.0000')
        self.maintainer1.save()

        # Initial balance is 1000 (from setUp)
        initial_balance = self.maintainer1.balance_blue_stars
        
        # Deploy agent
        response = self.client.post(url, {'name': 'Paid Agent'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check balance deduction (50 stars)
        self.maintainer1.refresh_from_db()
        self.assertEqual(self.maintainer1.balance_blue_stars, initial_balance - 50)

    def test_agent_deployment_insufficient_funds(self):
        url = reverse('agent-list')
        self.maintainer1.balance_blue_stars = 10
        self.maintainer1.save()
        
        self.client.force_authenticate(user=self.maintainer1)
        response = self.client.post(url, {'name': 'Broke Agent'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient Blue Stars", response.data['detail'])

    def test_bidding_stake_deduction(self):
        node = self.create_node(self.agent2, bounty=500)
        bid_url = reverse('researchnode-bid', kwargs={'pk': node.pk})
        eval_url_template = reverse('bid-evaluate', kwargs={'pk': 0})
        
        initial_balance = self.maintainer1.balance_blue_stars
        stake_amount = (Decimal('500') * Decimal('0.10')).quantize(Decimal('0.0001'))
        
        # Bid first
        response = self.client.post(bid_url, {'interview_response': 'test'}, HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Balance should NOT be deducted yet
        self.maintainer1.refresh_from_db()
        self.assertEqual(self.maintainer1.balance_blue_stars, initial_balance)

        # Coordinator accepts bid
        bid = node.bids.get(agent=self.agent1)
        eval_url = eval_url_template.replace('0/', f'{bid.pk}/')
        response = self.client.post(eval_url, {'action': 'accept'}, HTTP_X_AGENT_API_KEY=self.agent2_raw_key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # NOW balance should be deducted
        self.maintainer1.refresh_from_db()
        self.assertEqual(self.maintainer1.balance_blue_stars, initial_balance - stake_amount)

    def test_bidding_insufficient_stake(self):
        node = self.create_node(self.agent2, bounty=1000)
        url = reverse('researchnode-bid', kwargs={'pk': node.pk})
        
        self.maintainer1.balance_blue_stars = Decimal('50.0000')
        self.maintainer1.save()
        
        response = self.client.post(url, {'interview_response': 'test'}, HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Insufficient Blue Stars to cover potential stake", response.data['detail'])

    def test_proportional_bounty_split(self):
        from unittest.mock import patch
        from main_api.tasks import execute_publish
        
        # Create a node with 2 collaborators
        node = self.create_node(self.agent1, bounty=1000, collaborators=2)
        
        node.assigned_agents.add(self.agent1, self.agent2)
        node.status = 'in_review'
        node.save()
        
        # Set individual trust
        self.agent1.orange_stars = Decimal('100.0000')
        self.agent1.save()
        self.agent2.orange_stars = Decimal('300.0000')
        self.agent2.save()
        
        # Add reviews to pass consensus
        for i in range(3):
            reviewer = Agent.objects.create(name=f'Rev{i}', maintainer=self.maintainer1, api_key_hash=f'h{i}')
            PeerReview.objects.create(
                research_node=node, assigned_reviewer=reviewer,
                status='completed',
                is_approved=True, structured_data={'ok': True},
                soundness=8, significance=8, novelty=8, clarity=8, value=8.0
            )
            
        b1 = self.maintainer1.balance_blue_stars
        b2 = self.maintainer2.balance_blue_stars
        
        with patch('main_api.tasks.task_auto_resolve_coordinator_decision.apply_async'):
            task_resolve_node(node.id)

        node.refresh_from_db()
        self.assertEqual(node.status, 'awaiting_coordinator')
        execute_publish(node)
        
        self.maintainer1.refresh_from_db()
        self.maintainer2.refresh_from_db()
        
        stake_return = Decimal('1000') * Decimal('0.10')
        
        self.assertEqual(self.maintainer1.balance_blue_stars, b1 + Decimal('441.0') + stake_return + Decimal('31.5552'))
        self.assertEqual(self.maintainer2.balance_blue_stars, b2 + Decimal('539.0') + stake_return)

    def test_reviewer_slashing(self):
        from unittest.mock import patch
        
        node = self.create_node(self.agent1, bounty=100)
        node.status = 'in_review'
        node.save()
        
        reviewers = []
        for i in range(3):
            r = Agent.objects.create(name=f'RevSlash{i}', maintainer=self.maintainer1, api_key_hash=f'hs{i}', orange_stars=Decimal('100.0000'))
            reviewers.append(r)
            PeerReview.objects.create(
                research_node=node, assigned_reviewer=r,
                status='completed',
                is_approved=(i < 2),
                structured_data={'ok': True},
                soundness=5, significance=5, novelty=5, clarity=5, value=5.0
            )
        
        # Coordinator is also the worker here to test refund/payout
        node.assigned_agents.add(self.agent1)
        self.maintainer1.balance_blue_stars -= Decimal('10.0000') # 10% stake
        self.maintainer1.save()
            
        b1_initial = self.maintainer1.balance_blue_stars
        with patch('main_api.tasks.task_auto_resolve_coordinator_decision.apply_async'):
            task_resolve_node(node.id)

        node.refresh_from_db()
        self.assertEqual(node.status, 'awaiting_coordinator')
        from main_api.tasks import execute_publish
        execute_publish(node)
        
        # Reviewer 3 should be slashed (Reviewer 2 in index)
        reviewers[2].refresh_from_db()
        self.assertEqual(reviewers[2].orange_stars, Decimal('90.0000')) # 100 - MAX(5.0, 100 * 0.10)
        
        self.maintainer1.refresh_from_db()
        self.assertEqual(self.maintainer1.balance_blue_stars, b1_initial + Decimal('125.3576')) 

    def test_node_deadline_expiration_open(self):
        node = self.create_node(self.agent1, bounty=1000)
        node.deadline = timezone.now() - timezone.timedelta(hours=1)
        node.save()
        
        # Agent 2 bids (to test stake refund)
        node.assigned_agents.add(self.agent2)
        self.maintainer2.balance_blue_stars -= Decimal('100.0000')
        self.maintainer2.save()
        
        task_handle_node_deadline(node.id)
        
        node.refresh_from_db()
        self.assertEqual(node.status, 'failed')
        
        # Stake should be refunded for 'open' node
        self.maintainer2.refresh_from_db()
        self.assertEqual(self.maintainer2.balance_blue_stars, Decimal('1000.0000'))

    def test_node_deadline_expiration_in_progress(self):
        node = self.create_node(self.agent1, bounty=1000)
        node.status = 'in_progress'
        node.deadline = timezone.now() - timezone.timedelta(hours=1)
        node.assigned_agents.add(self.agent2)
        self.agent2.orange_stars = Decimal('100.0000')
        self.agent2.save()
        node.save()
        
        task_handle_node_deadline(node.id)
        
        # Agent 2 (worker) should be slashed by 10%
        self.agent2.refresh_from_db()
        self.assertEqual(self.agent2.orange_stars, Decimal('90.0000'))
        
        # Stake is NOT refunded
        node.refresh_from_db()
        self.assertEqual(node.status, 'failed')
        
        # Stake is NOT refunded
        node.refresh_from_db()
        self.assertEqual(node.status, 'failed')

class AdvancedTokenomicsTests(EnlideaBaseTestCase):
    def setUp(self):
        super().setUp()
        # Ensure Treasury exists
        from main_api.tasks import TREASURY_USERNAME
        self.treasury, _ = User.objects.get_or_create(
            username=TREASURY_USERNAME,
            defaults={'email': 'treasury@enlidea.system', 'balance_blue_stars': Decimal('10000.0000')}
        )
        
        # Setup agent with negative trust for testing 0-bounty access
        self.neg_agent = Agent.objects.create(
            name='NegativeAgent',
            maintainer=self.maintainer2,
            api_key_hash=hashlib.sha256('neg_hash'.encode()).hexdigest(),
            orange_stars=Decimal('-10.0000')
        )
        self.neg_agent.capabilities.add(self.cap_python)

        # Setup agent keys properly for HTTP headers
        self.agent2.api_key_hash = hashlib.sha256('agent2_key'.encode()).hexdigest()
        self.agent2.save()

        self.agent1.api_key_hash = hashlib.sha256('agent1_key'.encode()).hexdigest()
        self.agent1.save()

        self.maintainer2.balance_blue_stars = Decimal('1000.0000')
        self.maintainer2.save()

    def test_node_creation_fee(self):
        """Test that creating a node costs 5.0 BS regardless of bounty."""
        url = reverse('researchnode-list')
        initial_balance = self.maintainer1.balance_blue_stars
        initial_treasury = self.treasury.balance_blue_stars
        
        # 1. Create 0-bounty node
        data = {
            'title': 'Zero Bounty Node Test Title (Longer than 10 chars)',
            'description': 'Anti-spam test description',
            'body': 'A' * 150,
            'bounty_amount': '0.0000',
            'type': self.node_type.pk,
            'required_capabilities': [self.cap_python.pk],
            'required_reviews': 3,
            'required_collaborators': 1
        }
        self.client.credentials(HTTP_X_AGENT_API_KEY='agent1_key')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.maintainer1.refresh_from_db()
        self.treasury.refresh_from_db()
        
        # Costs 5.0 BS fee
        self.assertEqual(self.maintainer1.balance_blue_stars, initial_balance - Decimal('5.0000'))
        self.assertEqual(self.treasury.balance_blue_stars, initial_treasury + Decimal('5.0000'))

    def test_minimum_bidding_stake(self):
        """Test MAX(2.0, bounty * 0.1) stake logic."""
        # 1. 0-bounty node (should stake 2.0)
        node_zero = ResearchNode.objects.create(
            title='Zero Node', coordinating_agent=self.agent1, 
            bounty_amount=Decimal('0.0000'), status='open', type=self.node_type,
            required_collaborators=2
        )
        node_zero.required_capabilities.add(self.cap_python)
        
        bid_url = reverse('researchnode-bid', kwargs={'pk': node_zero.id})
        eval_url_template = reverse('bid-evaluate', kwargs={'pk': 0})
        self.client.credentials(HTTP_X_AGENT_API_KEY='agent2_key')
        
        initial_m2_balance = self.maintainer2.balance_blue_stars
        # Bid
        response = self.client.post(bid_url, {'interview_response': 'test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Accept
        self.client.credentials(HTTP_X_AGENT_API_KEY='agent1_key')
        bid = node_zero.bids.get(agent=self.agent2)
        response = self.client.post(eval_url_template.replace('0/', f'{bid.pk}/'), {'action': 'accept'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.maintainer2.refresh_from_db()
        self.assertEqual(self.maintainer2.balance_blue_stars, initial_m2_balance - Decimal('2.0000'))

        # 2. 100-bounty node (should stake 10.0, because 10.0 > 2.0)
        node_paid = ResearchNode.objects.create(
            title='Paid Node', coordinating_agent=self.agent1, 
            bounty_amount=Decimal('100.0000'), status='open', type=self.node_type,
            required_collaborators=2
        )
        node_paid.required_capabilities.add(self.cap_python)
        
        bid_url_paid = reverse('researchnode-bid', kwargs={'pk': node_paid.id})
        self.client.credentials(HTTP_X_AGENT_API_KEY='agent2_key')
        initial_m2_balance = self.maintainer2.balance_blue_stars
        
        # Bid
        response = self.client.post(bid_url_paid, {'interview_response': 'test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Accept
        self.client.credentials(HTTP_X_AGENT_API_KEY='agent1_key')
        bid_paid = node_paid.bids.get(agent=self.agent2)
        response = self.client.post(eval_url_template.replace('0/', f'{bid_paid.pk}/'), {'action': 'accept'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.maintainer2.refresh_from_db()
        self.assertEqual(self.maintainer2.balance_blue_stars, initial_m2_balance - Decimal('10.0000'))

    def test_trust_requirements_paid_vs_zero(self):
        """Test that paid nodes enforce trust, 0-bounty nodes allow recovery."""
        # 1. Paid node with 0 min_trust (default)
        node_paid = ResearchNode.objects.create(
            title='Paid Node', coordinating_agent=self.agent1, 
            bounty_amount=Decimal('10.0000'), status='open', type=self.node_type,
            required_collaborators=2
        )
        node_paid.required_capabilities.add(self.cap_python)
        
        # Negative trust agent tries to bid on paid node -> Forbidden
        url = reverse('researchnode-bid', kwargs={'pk': node_paid.id})
        self.client.credentials(HTTP_X_AGENT_API_KEY='neg_hash')
        response = self.client.post(url, {'interview_response': 'test'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Insufficient trust score', response.data['detail'])

        # 2. 0-bounty node
        node_zero = ResearchNode.objects.create(
            title='Zero Node', coordinating_agent=self.agent1, 
            bounty_amount=Decimal('0.0000'), status='open', type=self.node_type,
            required_collaborators=2
        )
        node_zero.required_capabilities.add(self.cap_python)
        
        # Negative trust agent tries to bid on 0-bounty node -> Success
        url_zero = reverse('researchnode-bid', kwargs={'pk': node_zero.id})
        response = self.client.post(url_zero, {'interview_response': 'test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_force_zero_trust_on_zero_bounty(self):
        """Test that min_trust_required is forced to 0 for 0-bounty nodes."""
        url = reverse('researchnode-list')
        
        data = {
            'title': 'Zero Bounty Spam Prevention Title (Over 10 chars)',
            'description': 'Test description for anti-spam logic',
            'body': 'B' * 150,
            'bounty_amount': '0.0000',
            'min_trust_required': '50.0000',
            'type': self.node_type.pk,
            'required_capabilities': [self.cap_python.pk],
            'required_reviews': 3,
            'required_collaborators': 1
        }
        self.client.credentials(HTTP_X_AGENT_API_KEY='agent1_key')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        node = ResearchNode.objects.get(id=response.data['id'])
        # Must be forced to 0.0
        self.assertEqual(node.min_trust_required, Decimal('0.0000'))

    def test_reviewer_cap_validation(self):
        """Test that required_reviews is capped between 3 and 20."""
        url = reverse('researchnode-list')
        self.client.credentials(HTTP_X_AGENT_API_KEY='agent1_key')
        
        base_data = {
            'title': 'Reviewer Cap Test Title (Long enough)',
            'description': 'Test description',
            'body': 'C' * 150,
            'bounty_amount': '10.0000',
            'type': self.node_type.pk,
            'required_capabilities': [self.cap_python.pk],
            'required_collaborators': 1
        }

        # 1. Too low (2)
        data_low = base_data.copy()
        data_low['required_reviews'] = 2
        response = self.client.post(url, data_low)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Django's MinValueValidator message
        self.assertIn('greater than or equal to 3', str(response.data['required_reviews']))

        # 2. Too high (21)
        data_high = base_data.copy()
        data_high['required_reviews'] = 21
        response = self.client.post(url, data_high)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Django's MaxValueValidator message
        self.assertIn('less than or equal to 20', str(response.data['required_reviews']))

        # 3. Valid (5)
        data_valid = base_data.copy()
        data_valid['required_reviews'] = 5
        response = self.client.post(url, data_valid)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_reviewer_trust_requirement(self):
        """Test that task_matchmake_node enforces trust floor for reviewers on paid nodes."""
        from main_api.tasks import task_matchmake_node
        from main_api.models import PeerReview

        # Paid node with 5.0 min_trust
        node_paid = ResearchNode.objects.create(
            title='Paid Node for Reviewer Trust', coordinating_agent=self.agent1, 
            bounty_amount=Decimal('100.0000'), status='in_review', type=self.node_type,
            required_collaborators=1, required_reviews=3, min_trust_required=Decimal('5.0000')
        )
        node_paid.required_capabilities.add(self.cap_python)
        
        # Agent 2 has 10 OS (from base setup), so it should be eligible
        self.agent2.orange_stars = Decimal('10.0000')
        self.agent2.capabilities.add(self.cap_python)
        self.agent2.save()

        # Negative trust agent should NOT be eligible
        self.neg_agent.orange_stars = Decimal('-10.0000')
        self.neg_agent.save()

        # Run matchmaking
        task_matchmake_node(node_paid.id)

        # Agent 2 should have a review created
        self.assertTrue(PeerReview.objects.filter(research_node=node_paid, assigned_reviewer=self.agent2).exists())
        # Negative agent should NOT
        self.assertFalse(PeerReview.objects.filter(research_node=node_paid, assigned_reviewer=self.neg_agent).exists())

    def test_trust_weighted_voting_consensus(self):
        """Test the trust-weighted voting formula."""
        from unittest.mock import patch
        from main_api.tasks import task_resolve_node, execute_publish, LAMBDA
        from main_api.models import PeerReview

        # Node requires 2 reviews (Even number to test tie-breaking/weighted gap)
        node = ResearchNode.objects.create(
            title='Weighted Voting Test', coordinating_agent=self.agent1,
            bounty_amount=Decimal('100.0000'), status='in_review', type=self.node_type,
            required_collaborators=1, required_reviews=2 
        )
        node.assigned_agents.add(self.agent2)

        # 1. Veteran Agent (High Trust: 100 OS) - Votes ACCEPT
        # Weight = 80 + 20*(1 - e^-2) approx 97.3
        veteran = Agent.objects.create(name='Veteran', maintainer=self.maintainer1, orange_stars=Decimal('100.0000'), api_key_hash='vh')
        PeerReview.objects.create(
            research_node=node, assigned_reviewer=veteran, is_approved=True, status='completed',
            soundness=8, significance=8, novelty=8, clarity=8, value=8.0,
            structured_data={'ok': True}
        )

        # 2. Novice Agent (Low Trust: 0 OS) - Votes REJECT
        # Weight = 80 + 20*(1 - e^0) = 80
        novice = Agent.objects.create(name='Novice', maintainer=self.maintainer1, orange_stars=Decimal('0.0000'), api_key_hash='nh')
        PeerReview.objects.create(
            research_node=node, assigned_reviewer=novice, is_approved=False, status='completed',
            soundness=2, significance=2, novelty=2, clarity=2, value=2.0,
            structured_data={'bad': True}
        )

        # Decision = sgn(1.0 * 97.3 + -1.0 * 80) = sgn(17.3) = Positive -> PUBLISHED
        # Veteran overrules Novice in a 1-vs-1 tie!
        
        with patch('main_api.tasks.task_auto_resolve_coordinator_decision.apply_async'):
            task_resolve_node(node.id)

        node.refresh_from_db()
        self.assertEqual(node.status, 'awaiting_coordinator')
        execute_publish(node)

        node.refresh_from_db()
        self.assertEqual(node.status, 'published')
