import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from starlette.testclient import TestClient
from mcp_server.server import app, make_request, get_agent_key, require_full_agent
from fastmcp.exceptions import ToolError, ResourceError


class MCPServerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("service"), "mcp-server")

    @patch("mcp_server.server.get_http_headers")
    def test_get_agent_key_validation(self, mock_get_headers):
        # 1. Missing header
        mock_get_headers.return_value = {}
        with self.assertRaises(ToolError) as cm:
            get_agent_key()
        self.assertIn("Missing or invalid Authorization header", str(cm.exception))

        # 2. Valid Bearer token
        mock_get_headers.return_value = {"authorization": "Bearer valid_key_123"}
        self.assertEqual(get_agent_key(), "valid_key_123")

    def test_require_full_agent_restriction(self):
        # 1. Public key rejected
        with self.assertRaises(ToolError) as cm:
            require_full_agent("pub_enlidea_testkey")
        self.assertIn("read-only access", str(cm.exception))

        # 2. Full agent key accepted
        self.assertEqual(require_full_agent("agent_secret_key"), "agent_secret_key")

    @patch("mcp_server.server.http_client")
    async def test_make_request_status_differentiation(self, mock_http_client):
        # 1. Test HTTP 401 (raises ToolError / ResourceError)
        mock_res_401 = MagicMock()
        mock_res_401.status_code = 401
        mock_http_client.request = AsyncMock(return_value=mock_res_401)

        with self.assertRaises(ToolError) as cm:
            await make_request("GET", "nodes/", is_tool=True)
        self.assertIn("Authentication failed", str(cm.exception))

        with self.assertRaises(ResourceError) as cm_res:
            await make_request("GET", "nodes/", is_tool=False)
        self.assertIn("Authentication failed", str(cm_res.exception))

        # 2. Test HTTP 403
        mock_res_403 = MagicMock()
        mock_res_403.status_code = 403
        mock_res_403.json.return_value = {"detail": "You do not have permission."}
        mock_http_client.request = AsyncMock(return_value=mock_res_403)

        with self.assertRaises(ToolError) as cm:
            await make_request("GET", "nodes/")
        self.assertIn("Permission denied", str(cm.exception))

        # 3. Test HTTP 429 with Retry-After
        mock_res_429 = MagicMock()
        mock_res_429.status_code = 429
        mock_res_429.headers = {"Retry-After": "60"}
        mock_http_client.request = AsyncMock(return_value=mock_res_429)

        with self.assertRaises(ToolError) as cm:
            await make_request("GET", "nodes/")
        self.assertIn("Rate limit exceeded", str(cm.exception))
        self.assertIn("60 seconds", str(cm.exception))

        # 4. Test HTTP 500 (Sanitized)
        mock_res_500 = MagicMock()
        mock_res_500.status_code = 500
        mock_res_500.text = "Traceback: File 'C:/Users/secret/file.py', line 12, in error..."
        mock_http_client.request = AsyncMock(return_value=mock_res_500)

        with self.assertRaises(ToolError) as cm:
            await make_request("GET", "nodes/")
        self.assertNotIn("Traceback", str(cm.exception))
        self.assertNotIn("C:/Users", str(cm.exception))
        self.assertIn("Internal server error on backend", str(cm.exception))
