from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, SimpleRateThrottle

from accounts.models import Agent
from enlidea.constants import PUBLIC_POOL_USERNAME


class PublicKeyRateThrottle(AnonRateThrottle):
    scope = "public_key_request"


class StandardAgentScopedThrottle(ScopedRateThrottle):
    """
    Standard scoped throttle for non-public agents.
    If the agent belongs to the Public_Pool, we skip this throttle.
    """

    def get_cache_key(self, request, view):
        if isinstance(request.user, Agent) and request.user.maintainer.username == PUBLIC_POOL_USERNAME:
            return None
        return super().get_cache_key(request, view)


class PublicAgentIndividualThrottle(SimpleRateThrottle):
    """
    Throttles individual public agents based on their primary key.
    """

    scope = "public_agent_individual"

    def get_cache_key(self, request, view):
        if isinstance(request.user, Agent) and request.user.maintainer.username == PUBLIC_POOL_USERNAME:
            return self.cache_format % {"scope": self.scope, "ident": request.user.pk}
        return None


class PublicAgentGlobalThrottle(SimpleRateThrottle):
    """
    Throttles the entire public pool globally.
    """

    scope = "public_agent_global"

    def get_cache_key(self, request, view):
        if isinstance(request.user, Agent) and request.user.maintainer.username == PUBLIC_POOL_USERNAME:
            return self.cache_format % {"scope": self.scope, "ident": "public_pool_global"}
        return None
