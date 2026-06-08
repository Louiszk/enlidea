from rest_framework.throttling import SimpleRateThrottle
from .auth_helpers import get_client_ip


class UsernameCheckThrottle(SimpleRateThrottle):
    """
    Throttles username availability checks to prevent user enumeration and DoS.
    Applies to both anonymous (by IP) and authenticated users (by ID).
    """

    scope = "username_check"

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = get_client_ip(request)

        return self.cache_format % {"scope": self.scope, "ident": ident}
