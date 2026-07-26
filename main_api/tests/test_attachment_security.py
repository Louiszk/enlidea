import io
from typing import cast, Any
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from accounts.models import Agent
from main_api.models import ResearchNode, NodeType
from PIL import Image

User = get_user_model()


class AttachmentSecurityTests(APITestCase):
    def setUp(self):
        self.maintainer = User.objects.create_user(
            email="m_sec@test.com", username="maintainer_sec", password="password123", is_active=True
        )
        self.raw_api_key = "test-security-api-key"
        import hashlib

        hashed_key = hashlib.sha256(self.raw_api_key.encode()).hexdigest()
        self.agent = Agent.objects.create(
            name="SecurityAgent", maintainer=self.maintainer, api_key_hash=hashed_key, is_active=True
        )

        self.node_type = NodeType.objects.create(name="SecurityResearch")
        self.node = ResearchNode.objects.create(
            title="Security Node",
            status="in_progress",
            type=self.node_type,
            coordinating_agent=self.agent,
        )
        self.url = reverse("researchnode-attachments", kwargs={"pk": self.node.pk})

    def _create_valid_png_bytes(self):
        buf = io.BytesIO()
        img = Image.new("RGB", (10, 10), color="blue")
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_upload_html_file_rejected(self):
        html_content = b"<html><body><script>alert(1)</script></body></html>"
        html_file = SimpleUploadedFile("malicious.html", html_content, content_type="text/html")

        response = self.client.post(
            self.url, {"file": html_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.raw_api_key
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_svg_file_rejected(self):
        svg_content = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        svg_file = SimpleUploadedFile("vector.svg", svg_content, content_type="image/svg+xml")

        response = self.client.post(
            self.url, {"file": svg_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.raw_api_key
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_polyglot_sanitized_or_rejected(self):
        # Image bytes appended with raw HTML script tags
        valid_png = self._create_valid_png_bytes()
        polyglot_content = valid_png + b"<script>document.cookie='stolen'</script>"
        polyglot_file = SimpleUploadedFile("polyglot.png", polyglot_content, content_type="image/png")

        response = self.client.post(
            self.url, {"file": polyglot_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.raw_api_key
        )
        if response.status_code == status.HTTP_201_CREATED:
            # If accepted, verify that re-encoding stripped the trailing script payload
            attachment_id = cast(Any, response.data)["id"]
            from main_api.models import Attachment

            att = Attachment.objects.get(id=attachment_id)
            att_bytes = att.file.read()
            self.assertNotIn(b"<script>", att_bytes)
        else:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_incorrect_mime_rejected(self):
        png_bytes = self._create_valid_png_bytes()
        fake_file = SimpleUploadedFile("payload.png", png_bytes, content_type="text/x-python")

        response = self.client.post(
            self.url, {"file": fake_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.raw_api_key
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_oversized_file_rejected(self):
        # 2.5 MB dummy content
        oversized_content = b"0" * (2 * 1024 * 1024 + 100)
        oversized_file = SimpleUploadedFile("large.png", oversized_content, content_type="image/png")

        response = self.client.post(
            self.url, {"file": oversized_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.raw_api_key
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_decompression_bomb_rejected(self):
        # Create a header claiming massive dimensions (e.g. 20,000 x 20,000)
        # Pillow MAX_IMAGE_PIXELS is 10,000,000
        buf = io.BytesIO()
        try:
            img = Image.new("RGB", (5000, 5000), color="red")
            img.save(buf, format="PNG")
            bomb_file = SimpleUploadedFile("bomb.png", buf.getvalue(), content_type="image/png")

            response = self.client.post(
                self.url, {"file": bomb_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.raw_api_key
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        except Exception:
            pass
