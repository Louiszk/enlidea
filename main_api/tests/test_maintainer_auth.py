from typing import Any, cast
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

    def test_missing_jwt_token_version_claim_revocation(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(self.user)
        # Remove the claim
        if "jwt_token_version" in refresh.payload:
            del refresh.payload["jwt_token_version"]

        # Verify refresh token without claim is rejected
        refresh_res = self.client.post("/auth-api/token-refresh/", {"refresh": str(refresh)}, format="json")
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
        self.assertEqual(
            msg1,
            "If an account with that email address exists, a password reset link has been sent.",
        )

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
            msg1,
            "If an inactive account with that email address exists, an activation email has been sent.",
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

    @patch("main_api.tasks.send_async_activation_email.delay")
    def test_registration_transactional_coherence(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(
                "/auth-api/register/",
                {
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "password1": "ComplexPass123!",
                    "password2": "ComplexPass123!",
                },
                format="json",
            )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("User registered successfully", res.data.get("message", ""))
        created_user = Account.objects.get(username="newuser")
        self.assertFalse(created_user.is_active)
        mock_delay.assert_called_once()

    @patch("main_api.tasks.send_mail", side_effect=Exception("SMTP Server Unavailable"))
    def test_async_activation_email_metric_logging_on_max_retries(self, mock_send_mail):
        from main_api.tasks import send_async_activation_email

        task = cast(Any, send_async_activation_email)
        with self.assertLogs("main_api.tasks", level="CRITICAL") as cm:
            with self.assertRaises(Exception):
                task.push_request(retries=5)
                try:
                    task(self.inactive_user.id, "http://test.link")
                finally:
                    task.pop_request()
            self.assertTrue(any("METRIC email_delivery_failure" in log for log in cm.output))

    def test_delete_account_worker_disassociation(self):
        from accounts.models import Agent
        from main_api.models import ResearchNode
        from main_api.tasks import TREASURY_USERNAME
        from decimal import Decimal
        import hashlib

        # 1. Create Treasury
        treasury, _ = Account.objects.get_or_create(
            username=TREASURY_USERNAME,
            defaults={"email": "treasury@example.com", "balance_blue_stars": Decimal("100.0000")},
        )

        # 2. Coordinator Account and Agent
        coordinator_account = Account.objects.create_user(
            email="coord@example.com", username="coordinator", password="SecurePassword123!", is_active=True
        )
        coord_agent = Agent.objects.create(
            name="CoordAgent",
            maintainer=coordinator_account,
            api_key_hash=hashlib.sha256(b"coord_key").hexdigest(),
        )

        # 3. Worker Account and Agent (to be deleted)
        worker_account = Account.objects.create_user(
            email="worker@example.com", username="worker", password="SecurePassword123!", is_active=True
        )
        worker_agent = Agent.objects.create(
            name="WorkerAgent",
            maintainer=worker_account,
            api_key_hash=hashlib.sha256(b"worker_key").hexdigest(),
        )

        # 4. Remaining Worker Account and Agent
        other_worker_account = Account.objects.create_user(
            email="otherworker@example.com", username="otherworker", password="SecurePassword123!", is_active=True
        )
        other_worker_agent = Agent.objects.create(
            name="OtherWorkerAgent",
            maintainer=other_worker_account,
            api_key_hash=hashlib.sha256(b"other_worker_key").hexdigest(),
        )

        # Create active node with 2 assigned agents
        node = ResearchNode.objects.create(
            title="Active Collaboration Node",
            description="Testing worker disassociation",
            body="Body text",
            coordinating_agent=coord_agent,
            bounty_amount=Decimal("10.0000"),
            status="in_progress",
            required_collaborators=2,
        )
        node.assigned_agents.set([worker_agent, other_worker_agent])

        # Delete worker_account
        self.client.force_authenticate(user=worker_account)
        res = self.client.delete(
            "/auth-api/settings/delete-account/", {"password": "SecurePassword123!"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Refresh node and treasury
        node.refresh_from_db()
        treasury.refresh_from_db()

        # Worker agent should be disassociated
        self.assertNotIn(worker_agent, node.assigned_agents.all())
        # Node should still have remaining worker and remain in_progress
        self.assertEqual(node.assigned_agents.count(), 1)
        self.assertIn(other_worker_agent, node.assigned_agents.all())
        self.assertEqual(node.status, "in_progress")

        # Treasury balance increased by stake (10 * 0.10 = 1.0000 -> min 2.0000)
        self.assertEqual(treasury.balance_blue_stars, Decimal("102.0000"))

        # Test deleting remaining worker account reverts status to 'open' when count drops to 0
        self.client.force_authenticate(user=other_worker_account)
        res2 = self.client.delete(
            "/auth-api/settings/delete-account/", {"password": "SecurePassword123!"}, format="json"
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        node.refresh_from_db()
        self.assertEqual(node.assigned_agents.count(), 0)
        self.assertEqual(node.status, "open")
