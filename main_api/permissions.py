from rest_framework import permissions
from accounts.models import Agent


class IsAgent(permissions.BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, Agent)


class IsMaintainer(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Assumes obj has a maintainer field or similar
        if hasattr(obj, "maintainer"):
            return obj.maintainer == request.user
        if hasattr(obj, "coordinating_agent"):
            return obj.coordinating_agent.maintainer == request.user
        return False


class IsNotPublicAgent(permissions.BasePermission):
    message = (
        "Public API keys (pub_enlidea_...) have read-only access. Please use a full Agent API key for write operations."
    )

    def has_permission(self, request, view):
        if isinstance(request.user, Agent) and request.user.maintainer.username == "Public_Pool":
            return False
        return True
