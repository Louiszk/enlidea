from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from main_api.models import ResearchNode, AgentMessage
from accounts.models import Agent
from django.utils import timezone
from datetime import timedelta
import time
from django.contrib.auth import get_user_model

User = get_user_model()

class CollaborationWorkspaceTests(TestCase):
    def setUp(self):
        self.maintainer = User.objects.create_user(username='maintainer', email='m@e.com', password='password')
        self.maintainer.balance_blue_stars = Decimal('100.0000')
        self.maintainer.save()
        
        self.coordinator = Agent.objects.create(name='Coordinator', maintainer=self.maintainer, api_key_hash='key1')
        self.worker = Agent.objects.create(name='Worker', maintainer=self.maintainer, api_key_hash='key2')
        self.other_agent = Agent.objects.create(name='Other', maintainer=self.maintainer, api_key_hash='key3')
        
        self.node = ResearchNode.objects.create(
            title='Test Node',
            description='Test Description',
            coordinating_agent=self.coordinator,
            status='in_progress',
            bounty_amount=Decimal('10.0000'),
            deadline=timezone.now() + timedelta(days=7)
        )
        self.node.assigned_agents.add(self.coordinator)
        self.node.assigned_agents.add(self.worker)
        
        self.client = Client()

    def test_get_messages_assigned_agent(self):
        # Authenticate as agent (using the authentication class in views)
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=self.worker)
        
        url = reverse('researchnode-messages', kwargs={'pk': self.node.pk})
        
        # Post a message first
        AgentMessage.objects.create(node=self.node, sender=self.coordinator, content='Hello team!')
        
        response = api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['content'], 'Hello team!')
        self.assertEqual(response.data[0]['sender_name'], 'Coordinator')

    def test_post_message_assigned_agent(self):
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=self.worker)
        
        url = reverse('researchnode-messages', kwargs={'pk': self.node.pk})
        
        response = api_client.post(url, {'content': 'I am working on it.'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AgentMessage.objects.filter(node=self.node, sender=self.worker, content='I am working on it.').exists())

    def test_message_access_denied(self):
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=self.other_agent)
        
        url = reverse('researchnode-messages', kwargs={'pk': self.node.pk})
        
        response = api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = api_client.post(url, {'content': 'Spam'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_messages_since_timestamp(self):
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=self.worker)
        
        url = reverse('researchnode-messages', kwargs={'pk': self.node.pk})
        
        m1 = AgentMessage.objects.create(node=self.node, sender=self.coordinator, content='Old message')
        time.sleep(0.1)
        ts = timezone.now().timestamp()
        time.sleep(0.1)
        m2 = AgentMessage.objects.create(node=self.node, sender=self.worker, content='New message')
        
        response = api_client.get(url, {'since_timestamp': ts})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['content'], 'New message')

    def test_patch_plan_coordinator_only(self):
        from rest_framework.test import APIClient
        api_client = APIClient()
        url = reverse('researchnode-plan', kwargs={'pk': self.node.pk})
        
        # Worker tries to update plan
        api_client.force_authenticate(user=self.worker)
        response = api_client.patch(url, {'coordination_plan': 'New plan'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Coordinator updates plan
        api_client.force_authenticate(user=self.coordinator)
        response = api_client.patch(url, {'coordination_plan': 'Phase 1: Research. Phase 2: Code.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.node.refresh_from_db()
        self.assertEqual(self.node.coordination_plan, 'Phase 1: Research. Phase 2: Code.')
        
        # Check audit trail
        self.assertTrue(AgentMessage.objects.filter(node=self.node, sender=None, content__icontains='SYSTEM').exists())

    def test_sync_timestamp_updates_on_message(self):
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=self.worker)
        url_sync = reverse('agent-sync')
        
        # Initial sync
        response = api_client.get(url_sync)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ts1 = response.data['timestamp']
        
        # New message posted by coordinator
        time.sleep(0.1)
        AgentMessage.objects.create(node=self.node, sender=self.coordinator, content='Update!')
        
        # Second sync
        response = api_client.get(url_sync)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ts2 = response.data['timestamp']
        
        self.assertGreater(ts2, ts1)

    def test_extend_deadline_success(self):
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=self.worker)
        url = reverse('researchnode-extend-deadline', kwargs={'pk': self.node.pk})
        
        initial_deadline = self.node.deadline
        initial_balance = self.maintainer.balance_blue_stars
        
        # Extend by 3 days
        response = api_client.post(url, {'days': 3})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.node.refresh_from_db()
        self.maintainer.refresh_from_db()
        
        # Verify 3 days extension (72 hours)
        self.assertAlmostEqual((self.node.deadline - initial_deadline).total_seconds(), 3 * 86400, places=1)
        self.assertEqual(self.node.extended_days, 3)
        
        # Verify cost: 2.0 per day * 3 = 6.0 Blue Stars
        self.assertEqual(self.maintainer.balance_blue_stars, initial_balance - Decimal('6.0000'))
        
        # Verify audit trail
        self.assertTrue(AgentMessage.objects.filter(node=self.node, content__icontains='SYSTEM: Project deadline has been extended by 3 days').exists())

    def test_read_before_write_constraint(self):
        from rest_framework.test import APIClient
        api_client = APIClient()
        url = reverse('researchnode-messages', kwargs={'pk': self.node.pk})
        
        # 1. Initially worker can post a message because there are no messages at all
        api_client.force_authenticate(user=self.worker)
        response = api_client.post(url, {'content': 'First message'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 2. Coordinator posts a message
        api_client.force_authenticate(user=self.coordinator)
        # Coordinator must read first!
        api_client.get(url)
        response = api_client.post(url, {'content': 'Hello worker'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 3. Worker tries to post without reading the coordinator's message
        api_client.force_authenticate(user=self.worker)
        response = api_client.post(url, {'content': 'Interrupting...'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('You must fetch the latest messages', response.data['detail'])
        
        # 4. Worker reads messages
        response = api_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify sync record was updated
        from main_api.models import AgentNodeSync
        sync = AgentNodeSync.objects.get(agent=self.worker, node=self.node)
        self.assertIsNotNone(sync.last_synced_at)
        
        # 5. Worker tries to post again after reading
        response = api_client.post(url, {'content': 'Now I can talk'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_read_before_write_system_message(self):
        from rest_framework.test import APIClient
        api_client = APIClient()
        url = reverse('researchnode-messages', kwargs={'pk': self.node.pk})
        
        # 1. System posts a message (e.g. via coordination plan update)
        AgentMessage.objects.create(node=self.node, sender=None, content='SYSTEM: Plan updated')
        
        # 2. Worker tries to post without reading system message
        api_client.force_authenticate(user=self.worker)
        response = api_client.post(url, {'content': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # 3. Worker reads messages
        api_client.get(url)
        
        # 4. Worker can post now
        response = api_client.post(url, {'content': 'Acknowledged'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_extend_deadline_exceeds_max(self):
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=self.coordinator)
        url = reverse('researchnode-extend-deadline', kwargs={'pk': self.node.pk})
        
        response = api_client.post(url, {'days': 15})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Maximum allowed total extension is 14 days', response.data['detail'])

    def test_extend_deadline_unauthorized(self):
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=self.other_agent)
        url = reverse('researchnode-extend-deadline', kwargs={'pk': self.node.pk})
        
        response = api_client.post(url, {'days': 2})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'Only assigned workers or the coordinator can extend the deadline.')

