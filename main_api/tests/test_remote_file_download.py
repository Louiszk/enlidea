from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.exceptions import ValidationError
from main_api.services import download_remote_file


class RemoteFileDownloadTest(TestCase):
    @patch("requests.get")
    def test_ssrf_protection_domain_allowlist(self, mock_get):
        # Test that arbitrary domains are rejected
        with self.assertRaises(ValidationError) as cm:
            download_remote_file("https://malicious-site.com/payload.md", max_size_bytes=1024)
        self.assertIn("is not in the approved allowlist", str(cm.exception))

    @patch("requests.get")
    def test_ssrf_protection_http_auth_bypass(self, mock_get):
        # Test the SSRF exploit mentioned in changes.md
        # urlparse('https://raw.githubusercontent.com:password@10.0.0.1/my-payload.md').hostname is '10.0.0.1'
        exploit_url = "https://raw.githubusercontent.com:password@10.0.0.1/my-payload.md"
        with self.assertRaises(ValidationError) as cm:
            download_remote_file(exploit_url, max_size_bytes=1024)

        self.assertIn("Domain '10.0.0.1' is not in the approved allowlist", str(cm.exception))

    @patch("requests.get")
    def test_https_only(self, mock_get):
        with self.assertRaises(ValidationError) as cm:
            download_remote_file("http://raw.githubusercontent.com/user/repo/main/file.md", max_size_bytes=1024)
        self.assertIn("Only HTTPS is allowed", str(cm.exception))

    @patch("requests.get")
    def test_no_redirects(self, mock_get):
        mock_response = MagicMock()
        mock_response.is_redirect = True
        mock_response.status_code = 302
        # Mocking context manager
        mock_get.return_value.__enter__.return_value = mock_response

        with self.assertRaises(ValidationError) as cm:
            download_remote_file("https://raw.githubusercontent.com/user/repo/main/file.md", max_size_bytes=1024)
        self.assertIn("Redirects are not allowed", str(cm.exception))

    @patch("requests.get")
    def test_imgur_extension_bypass(self, mock_get):
        # Imgur URLs often don't have extensions in the path
        url = "https://i.imgur.com/aBcDeF"

        mock_response = MagicMock()
        mock_response.is_redirect = False
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/png", "Content-Length": "100"}
        mock_response.iter_content.return_value = [b"fake-image-data"]
        # Mocking context manager
        mock_get.return_value.__enter__.return_value = mock_response

        # Should NOT raise ValidationError for missing extension
        file_obj = download_remote_file(url, max_size_bytes=1024, allowed_extensions=[".png"])
        # Our implementation appends .png if no dot in filename
        self.assertEqual(file_obj.name, "downloaded_attachment.png")

    @patch("requests.get")
    def test_github_extension_enforced(self, mock_get):
        url = "https://raw.githubusercontent.com/user/repo/main/no-extension"
        with self.assertRaises(ValidationError) as cm:
            download_remote_file(url, max_size_bytes=1024, allowed_extensions=[".md"])
        self.assertIn("Invalid file extension", str(cm.exception))

    @patch("requests.get")
    def test_mime_type_validation(self, mock_get):
        url = "https://raw.githubusercontent.com/user/repo/main/file.md"

        mock_response = MagicMock()
        mock_response.is_redirect = False
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/exe"}
        # Mocking context manager
        mock_get.return_value.__enter__.return_value = mock_response

        with self.assertRaises(ValidationError) as cm:
            download_remote_file(url, max_size_bytes=1024)
        self.assertIn("Must be image/* or text/*", str(cm.exception))

    @patch("requests.get")
    def test_size_limit_header(self, mock_get):
        url = "https://raw.githubusercontent.com/user/repo/main/file.md"

        mock_response = MagicMock()
        mock_response.is_redirect = False
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/plain", "Content-Length": "2000"}
        # Mocking context manager
        mock_get.return_value.__enter__.return_value = mock_response

        with self.assertRaises(ValidationError) as cm:
            download_remote_file(url, max_size_bytes=1000)
        self.assertIn("File size exceeds the limit", str(cm.exception))

    @patch("requests.get")
    def test_size_limit_streaming(self, mock_get):
        url = "https://raw.githubusercontent.com/user/repo/main/file.md"

        mock_response = MagicMock()
        mock_response.is_redirect = False
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/plain"}
        # No content-length header, but stream exceeds limit
        mock_response.iter_content.return_value = [b"a" * 500, b"b" * 600]
        # Mocking context manager
        mock_get.return_value.__enter__.return_value = mock_response

        with self.assertRaises(ValidationError) as cm:
            download_remote_file(url, max_size_bytes=1000)
        self.assertIn("File size exceeds the limit", str(cm.exception))
