from rest_framework import authentication
from rest_framework import exceptions
from accounts.models import Agent
import hashlib
from django.core.cache import cache

class AgentApiKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_AGENT_API_KEY')
        if not api_key:
            return None

        # Use fast SHA-256 for high-entropy API keys to allow O(1) lookups
        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

        try:
            agent = Agent.objects.get(api_key_hash=hashed_key, is_active=True)
            # Update the agent's "online" status with a 10-minute TTL (600 seconds)
            cache.set(f'agent_active_{agent.id}', True, timeout=600)
            return (agent, None)
        except Agent.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid or inactive Agent API Key')
