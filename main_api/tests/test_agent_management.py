from rest_framework import status
from django.urls import reverse
from accounts.models import Agent
from .test_agent_auth import EnlideaBaseTestCase
from decimal import Decimal

class AgentManagementTests(EnlideaBaseTestCase):
    def test_agent_limit_per_maintainer(self):
        url = reverse('agent-list')
        self.client.force_authenticate(user=self.maintainer1)
        
        # Maintainer needs 5.0 OS to deploy agents now
        self.maintainer1.balance_orange_stars = Decimal('10.0000')
        self.maintainer1.save()

        for i in range(3):
            response = self.client.post(url, {'name': f'Extra Agent {i}'})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            
        # Verify count is 4
        self.assertEqual(Agent.objects.filter(maintainer=self.maintainer1).count(), 4)
        
        # Attempt to create the 5th agent
        response = self.client.post(url, {'name': 'Illegal 5th Agent'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "Agent limit reached. You can only deploy a maximum of 4 agents.")
