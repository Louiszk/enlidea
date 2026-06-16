from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import CSRFCheck
from rest_framework import exceptions


class CookieJWTAuthentication(JWTAuthentication):
    def enforce_csrf(self, request):
        """
        Enforce CSRF validation when using cookies for authentication.
        """

        def dummy_get_response(request):  # pragma: no cover
            return None

        check = CSRFCheck(dummy_get_response)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied("CSRF Failed: %s" % reason)

    def authenticate(self, request):
        header = self.get_header(request)

        from_cookie = False
        if header is None:
            # Try to get token from cookies
            raw_token = request.COOKIES.get("access")
            from_cookie = True
        else:
            raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        if isinstance(raw_token, str):
            raw_token = raw_token.encode("utf-8")

        validated_token = self.get_validated_token(raw_token)

        if from_cookie:
            self.enforce_csrf(request)

        return self.get_user(validated_token), validated_token
