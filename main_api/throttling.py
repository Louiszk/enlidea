from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle
from accounts.models import Agent

class StandardAgentScopedThrottle(ScopedRateThrottle):
    """
    Standard scoped throttle for non-public agents.
    If the agent belongs to the Public_Pool, we skip this throttle.
    """
    def get_cache_key(self, request, view):
        if isinstance(request.user, Agent) and request.user.maintainer.username == 'Public_Pool':
            return None
        return super().get_cache_key(request, view)

class PublicAgentIndividualThrottle(SimpleRateThrottle):
    """
    Throttles individual public agents based on their primary key.
    """
    scope = 'public_agent_individual'

    def get_cache_key(self, request, view):
        if isinstance(request.user, Agent) and request.user.maintainer.username == 'Public_Pool':
            return self.cache_format % {
                'scope': self.scope,
                'ident': request.user.pk
            }
        return None

class PublicAgentGlobalThrottle(SimpleRateThrottle):
    """
    Throttles the entire public pool globally.
    """
    scope = 'public_agent_global'

    def get_cache_key(self, request, view):
        if isinstance(request.user, Agent) and request.user.maintainer.username == 'Public_Pool':
            return self.cache_format % {
                'scope': self.scope,
                'ident': 'public_pool_global'
            }
        return None
