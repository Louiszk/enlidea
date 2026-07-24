from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.cache import cache

Account = get_user_model()


class MaintainerAuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = Account.objects.create_user(
            email="victim@example.com",
            username="victim",
            password="SecurePassword123!",
            is_active=True,
        )
        self.inactive_user = Account.objects.create_user(
            email="inactive@example.com",
            username="inactive",
            password="SecurePassword123!",
            is_active=False,
        )

    def test_token_revocation_on_password_reset(self):
        # 1. Login and get cookies
        login_res = self.client.post(
            "/auth-api/login/",
            {"email": "victim@example.com", "password": "SecurePassword123!"},
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        access_morsel = login_res.cookies.get("access")
        refresh_morsel = login_res.cookies.get("refresh")
        self.assertIsNotNone(access_morsel)
        self.assertIsNotNone(refresh_morsel)
        assert access_morsel is not None and refresh_morsel is not None
        access_cookie = access_morsel.value
        refresh_cookie = refresh_morsel.value

        # Verify access token works
        self.client.cookies["access"] = access_cookie
        user_res = self.client.get("/auth-api/current-user/")
        self.assertEqual(user_res.status_code, status.HTTP_200_OK)

        # 2. Reset password
        token = default_token_generator.make_token(self.user)
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        reset_res = self.client.post(
            f"/auth-api/password-reset-confirm/{uidb64}/{token}/",
            {"new_password1": "NewSecurePassword456!", "new_password2": "NewSecurePassword456!"},
            format="json",
        )
        self.assertEqual(reset_res.status_code, status.HTTP_200_OK)

        # 3. Verify old access token is revoked
        self.client.cookies["access"] = access_cookie
        revoked_res = self.client.get("/auth-api/current-user/")
        self.assertEqual(revoked_res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 4. Verify old refresh token is revoked
        self.client.cookies["refresh"] = refresh_cookie
        refresh_res = self.client.post("/auth-api/token-refresh/")
        self.assertEqual(refresh_res.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("accounts.auth_views.send_password_reset_email", return_value=True)
    def test_password_reset_anti_enumeration(self, mock_send_email):
        # Existing email
        res1 = self.client.post("/auth-api/password-reset/", {"email": "victim@example.com"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        msg1 = res1.data.get("message")

        # Non-existing email
        res2 = self.client.post("/auth-api/password-reset/", {"email": "nonexistent@example.com"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        msg2 = res2.data.get("message")

        self.assertEqual(msg1, msg2)
        self.assertEqual(msg1, "If an account with that email address exists, a password reset link has been sent.")

    @patch("accounts.auth_views.send_activation_email", return_value=True)
    def test_resend_activation_anti_enumeration(self, mock_send_email):
        # Inactive email
        res1 = self.client.post("/auth-api/resend-activation/", {"email": "inactive@example.com"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        msg1 = res1.data.get("message")

        # Non-existing email
        res2 = self.client.post("/auth-api/resend-activation/", {"email": "nonexistent@example.com"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        msg2 = res2.data.get("message")

        self.assertEqual(msg1, msg2)
        self.assertEqual(
            msg1, "If an inactive account with that email address exists, an activation email has been sent."
        )

    def test_per_account_ip_login_lockout(self):
        Account.objects.create_user(
            email="lockout_victim@example.com",
            username="lockout_victim",
            password="SecurePassword123!",
            is_active=True,
        )

        # Fail 5 times for lockout_victim@example.com
        for _ in range(5):
            self.client.post(
                "/auth-api/login/",
                {"email": "lockout_victim@example.com", "password": "WrongPassword!"},
                format="json",
            )

        # 6th attempt for victim should be throttled (429)
        throttled_res = self.client.post(
            "/auth-api/login/",
            {"email": "lockout_victim@example.com", "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(throttled_res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Other user from SAME IP should NOT be locked out
        Account.objects.create_user(
            email="other@example.com",
            username="other",
            password="SecurePassword123!",
            is_active=True,
        )
        success_res = self.client.post(
            "/auth-api/login/",
            {"email": "other@example.com", "password": "SecurePassword123!"},
            format="json",
        )
        self.assertEqual(success_res.status_code, status.HTTP_200_OK)

        # Successful login of other_user should NOT clear victim's lockout
        victim_retry = self.client.post(
            "/auth-api/login/",
            {"email": "lockout_victim@example.com", "password": "SecurePassword123!"},
            format="json",
        )
        self.assertEqual(victim_retry.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_csrf_enforcement_on_cookie_logout(self):
        csrf_client = APIClient(enforce_csrf_checks=True)
        login_res = csrf_client.post(
            "/auth-api/login/",
            {"email": "victim@example.com", "password": "SecurePassword123!"},
            format="json",
        )
        refresh_morsel = login_res.cookies.get("refresh")
        self.assertIsNotNone(refresh_morsel)
        assert refresh_morsel is not None
        csrf_client.cookies["refresh"] = refresh_morsel.value

        # POST to logout without CSRF token header should fail with 403
        logout_res = csrf_client.post("/auth-api/logout/")
        self.assertEqual(logout_res.status_code, status.HTTP_403_FORBIDDEN)
