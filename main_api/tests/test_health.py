from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient


class HealthProbeTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_healthz_endpoint(self):
        # Test liveness probe with and without trailing slash
        res_slash = self.client.get("/healthz/")
        self.assertEqual(res_slash.status_code, status.HTTP_200_OK)
        self.assertEqual(res_slash.json().get("status"), "healthy")

        res_no_slash = self.client.get("/healthz")
        self.assertEqual(res_no_slash.status_code, status.HTTP_200_OK)
        self.assertEqual(res_no_slash.json().get("status"), "healthy")

    @patch("django.db.connection.ensure_connection")
    @patch("django.db.connection.is_usable", return_value=True)
    @patch("django.core.cache.cache.set", return_value=True)
    @patch("django.core.cache.cache.get", return_value="1")
    def test_readyz_endpoint_healthy(self, mock_cache_get, mock_cache_set, mock_db_usable, mock_db_ensure):
        # Normal state should report ready and ok for both database and cache
        res = self.client.get("/readyz/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data.get("status"), "ready")
        self.assertEqual(data.get("database"), "ok")
        self.assertEqual(data.get("cache"), "ok")

    @patch("django.core.cache.cache.set", return_value=True)
    @patch("django.core.cache.cache.get", return_value="1")
    @patch("django.db.connection.ensure_connection", side_effect=Exception("Database unreachable"))
    def test_readyz_database_failure(self, mock_db, mock_cache_get, mock_cache_set):
        res = self.client.get("/readyz/")
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        data = res.json()
        self.assertEqual(data.get("status"), "degraded")
        self.assertEqual(data.get("database"), "unreachable")
        self.assertEqual(data.get("cache"), "ok")

    @patch("django.db.connection.ensure_connection")
    @patch("django.db.connection.is_usable", return_value=True)
    @patch("django.core.cache.cache.get", side_effect=Exception("Redis connection error"))
    def test_readyz_cache_failure(self, mock_cache, mock_db_usable, mock_db_ensure):
        res = self.client.get("/readyz/")
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        data = res.json()
        self.assertEqual(data.get("status"), "degraded")
        self.assertEqual(data.get("database"), "ok")
        self.assertEqual(data.get("cache"), "unreachable")
