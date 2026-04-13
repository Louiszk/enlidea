from rest_framework import status
from django.urls import reverse
from accounts.models import Agent, Account
from .test_agent_auth import EnlideaBaseTestCase

class PublicAgentTests(EnlideaBaseTestCase):
    def test_request_public_key(self):
        url = reverse('public_key')
        
        # First call
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        key1 = response1.data['api_key']
        
        # Second call
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        key2 = response2.data['api_key']
        
        # Assert keys are different
        self.assertNotEqual(key1, key2)
        
        # Verify DB records
        self.assertTrue(Account.objects.filter(username='Public_Pool').exists())
        # Two distinct agents should exist for Public_Pool
        self.assertEqual(Agent.objects.filter(maintainer__username='Public_Pool').count(), 2)

    def test_public_agent_read_only_access(self):
        # 1. Get public key
        url_pk = reverse('public_key')
        resp_pk = self.client.get(url_pk)
        public_key = resp_pk.data['api_key']
        
        # 2. Create a node for testing
        node = self.create_node(self.agent1)
        
        # 3. Test Read (Allowed)
        url_list = reverse('researchnode-list')
        response = self.client.get(url_list, HTTP_X_AGENT_API_KEY=public_key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 4. Test Write (Blocked)
        url_bid = reverse('researchnode-bid', kwargs={'pk': node.pk})
        response = self.client.post(url_bid, HTTP_X_AGENT_API_KEY=public_key)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
