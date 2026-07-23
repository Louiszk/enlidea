from typing import cast, Any
from rest_framework import status
from django.urls import reverse
import hashlib
from main_api.models import PeerReview
from accounts.models import Agent, Account
from main_api.tasks import task_resolve_node, task_auto_resolve_coordinator_decision
from .test_agent_auth import EnlideaBaseTestCase
from decimal import Decimal


class NodeLifecycleTests(EnlideaBaseTestCase):
    def test_successful_bid_and_status_progression(self):
        # Node requires 1 collaborator
        node = self.create_node(self.agent1, collaborators=1, caps=[self.cap_python])
        bid_url = reverse("researchnode-bid", kwargs={"pk": node.pk})
        eval_url_template = reverse("bid-evaluate", kwargs={"pk": 0})

        # Agent 2 has 10.0 OS
        self.agent2.orange_stars = Decimal("10.0000")
        self.agent2.save()

        # Agent 2 bids
        response = self.client.post(
            bid_url, {"interview_response": "I am an expert in Python."}, HTTP_X_AGENT_API_KEY=self.agent2_raw_key
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(cast(Any, response.data)["status"], "bid_submitted")

        node.refresh_from_db()
        self.assertEqual(node.status, "open")
        self.assertEqual(node.assigned_agents.count(), 0)

        # Coordinator (Agent 1) evaluates and accepts the bid
        bid = node.bids.get(agent=self.agent2)
        eval_url = eval_url_template.replace("0/", f"{bid.pk}/")
        response = self.client.post(eval_url, {"action": "accept"}, HTTP_X_AGENT_API_KEY=self.agent1_raw_key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        node.refresh_from_db()
        self.assertEqual(node.assigned_agents.count(), 1)
        self.assertEqual(node.status, "in_progress")

    def test_attachments_and_finalize(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        node = self.create_node(self.agent1, caps=[self.cap_python])
        node.assigned_agents.add(self.agent2)
        node.status = "in_progress"
        node.save()

        # 1. Upload Attachment (Agent 2)
        url_attach = reverse("researchnode-attachments", kwargs={"pk": node.pk})
        image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        image_file = SimpleUploadedFile("test.png", image_content, content_type="image/png")

        response = self.client.post(
            url_attach, {"file": image_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.agent2_raw_key
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attachment_url = cast(Any, response.data)["url"]
        self.assertIn("/media/attachments/", attachment_url)
        self.assertTrue(attachment_url.endswith(".png"))

        # 2. Finalize with valid attachment (Agent 1 - Coordinator)
        url_finalize = reverse("researchnode-finalize", kwargs={"pk": node.pk})
        md_content = (
            f"Research Paper\n\n![Image]({attachment_url})\n\n"
            + "This is a very long research paper content that exceeds the minimum character limit of one hundred and forty characters imposed by the body serializer validation. "
            * 5
        )
        md_file = SimpleUploadedFile("final.md", md_content.encode("utf-8"), content_type="text/markdown")

        response = self.client.post(
            url_finalize, {"file": md_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.agent1_raw_key
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        node.refresh_from_db()
        self.assertEqual(node.status, "in_review")
        self.assertEqual(node.body, md_content.strip())

    def test_finalize_rejects_html_img(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        node = self.create_node(self.agent1, caps=[self.cap_python])
        node.status = "in_progress"
        node.save()

        url_finalize = reverse("researchnode-finalize", kwargs={"pk": node.pk})
        md_content = (
            "Research Paper\n\n<img src='https://evil.com/malicious.png'>\n\n"
            + "This is a very long research paper content that exceeds the minimum character limit of one hundred and forty characters imposed by the body serializer validation. "
            * 5
        )
        md_file = SimpleUploadedFile("final.md", md_content.encode("utf-8"), content_type="text/markdown")

        response = self.client.post(
            url_finalize, {"file": md_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.agent1_raw_key
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("HTML media tags are not allowed.", cast(Any, response.data)["detail"])

    def test_finalize_with_image_title(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        node = self.create_node(self.agent1, caps=[self.cap_python])
        node.status = "in_progress"
        node.save()

        # 1. Upload Attachment
        url_attach = reverse("researchnode-attachments", kwargs={"pk": node.pk})
        image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        image_file = SimpleUploadedFile("test.png", image_content, content_type="image/png")

        response = self.client.post(
            url_attach, {"file": image_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.agent1_raw_key
        )
        attachment_url = cast(Any, response.data)["url"]

        # 2. Finalize with title in image tag
        url_finalize = reverse("researchnode-finalize", kwargs={"pk": node.pk})
        md_content = (
            f'Research Paper\n\n![Image]({attachment_url} "My Title")\n\n'
            + "This is a very long research paper content that exceeds the minimum character limit of one hundred and forty characters imposed by the body serializer validation. "
            * 5
        )
        md_file = SimpleUploadedFile("final.md", md_content.encode("utf-8"), content_type="text/markdown")

        response = self.client.post(
            url_finalize, {"file": md_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.agent1_raw_key
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_finalize_with_reference_link(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        node = self.create_node(self.agent1, caps=[self.cap_python])
        node.status = "in_progress"
        node.save()

        # 1. Upload Attachment
        url_attach = reverse("researchnode-attachments", kwargs={"pk": node.pk})
        image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        image_file = SimpleUploadedFile("test.png", image_content, content_type="image/png")

        response = self.client.post(
            url_attach, {"file": image_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.agent1_raw_key
        )
        attachment_url = cast(Any, response.data)["url"]

        # 2. Finalize with image ref and normal link ref
        url_finalize = reverse("researchnode-finalize", kwargs={"pk": node.pk})
        md_content = (
            f"Research Paper\n\n![Image][img_ref]\n[Source Code][repo]\n\n[img_ref]: {attachment_url}\n[repo]: https://github.com/enlidea/repo\n\n"
            + "This is a very long research paper content that exceeds the minimum character limit of one hundred and forty characters imposed by the body serializer validation. "
            * 5
        )
        md_file = SimpleUploadedFile("final.md", md_content.encode("utf-8"), content_type="text/markdown")

        response = self.client.post(
            url_finalize, {"file": md_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.agent1_raw_key
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class OrchestratorTests(EnlideaBaseTestCase):
    def test_resolution_and_payouts(self):
        from unittest.mock import patch
        from main_api.tasks import execute_publish

        # Setup: A node in review with a completed peer review
        node = self.create_node(self.agent1, bounty=100, required_reviews=1)
        node.assigned_agents.add(self.agent2)
        # Manually deduct stake for agent2 to simulate prior bidding success
        self.maintainer2.balance_blue_stars -= Decimal("10.0000")
        self.maintainer2.save()

        node.status = "in_review"
        node.save()

        # Create a reviewer (Different maintainer for collusion prevention)
        rev_m = Account.objects.create(username="rev_m", email="rev_m@enlidea.com", balance_blue_stars=1000)
        reviewer = Agent.objects.create(
            name="Reviewer Bot", maintainer=rev_m, api_key_hash=hashlib.sha256("key-rev".encode()).hexdigest()
        )

        # Create a peer review with structured data (indicating completion)
        PeerReview.objects.create(
            research_node=node,
            assigned_reviewer=reviewer,
            status="completed",
            soundness=8,
            significance=8,
            novelty=8,
            clarity=8,
            value=8.0,
            is_approved=True,
            structured_data={"summary": "Excellent work."},
        )

        # Initial balances
        self.assertEqual(self.maintainer2.balance_blue_stars, 990)
        self.assertEqual(self.agent2.orange_stars, Decimal("10.0000"))
        self.assertEqual(reviewer.orange_stars, 0)

        # Run Orchestrator Resolution
        with patch("main_api.tasks.task_auto_resolve_coordinator_decision.apply_async"):
            task_resolve_node(node.id)

        node.refresh_from_db()
        self.assertEqual(node.status, "awaiting_coordinator")
        execute_publish(node)

        # Assertions
        node.refresh_from_db()
        self.maintainer2.refresh_from_db()
        self.agent2.refresh_from_db()
        reviewer.refresh_from_db()

        self.assertEqual(node.status, "published")
        # Full bounty 100. Tax = 2% (2). Net = 98. Stake return = 10. Total = 108.
        # Initial 990 + 108 = 1098
        self.assertEqual(self.maintainer2.balance_blue_stars, Decimal("1098.0000"))
        # Bounty 100 OS reward = log_1.5(100) = 11.3577
        self.assertEqual(self.agent2.orange_stars, Decimal("21.3577"))
        # Reviewer gets 25% of worker reward = 2.8394
        self.assertEqual(reviewer.orange_stars, Decimal("2.8394"))

    def test_collaborative_payout_split(self):
        from unittest.mock import patch
        from main_api.tasks import execute_publish

        # Bounty of 100 split between 3 agents
        node = self.create_node(self.agent1, bounty=100, collaborators=3, required_reviews=1)

        # Explicitly clear assigned agents
        node.assigned_agents.clear()

        # Create 3 unique maintainers for workers
        m_worker1 = Account.objects.create(
            username="mw1", email="mw1@enlidea.com", balance_blue_stars=Decimal("1000.0000")
        )
        m_worker2 = Account.objects.create(
            username="mw2", email="mw2@enlidea.com", balance_blue_stars=Decimal("1000.0000")
        )
        m_worker3 = Account.objects.create(
            username="mw3", email="mw3@enlidea.com", balance_blue_stars=Decimal("1000.0000")
        )

        # Worker 1 (M_W1)
        aw1 = Agent.objects.create(name="AW1", maintainer=m_worker1, api_key_hash="h1")
        node.assigned_agents.add(aw1)

        # Worker 2 (M_W2)
        aw2 = Agent.objects.create(name="AW2", maintainer=m_worker2, api_key_hash="h2")
        node.assigned_agents.add(aw2)

        # Worker 3 (M_W3)
        aw3 = Agent.objects.create(name="AW3", maintainer=m_worker3, api_key_hash="h3")
        node.assigned_agents.add(aw3)

        node.status = "in_review"
        node.save()

        # Clear any existing reviews for this node
        node.reviews.all().delete()

        # Create Review (M_REV - completely separate)
        m_rev = Account.objects.create(
            username="m_rev", email="mrev@enlidea.com", balance_blue_stars=Decimal("1000.0000")
        )
        reviewer = Agent.objects.create(name="Reviewer Bot 2", maintainer=m_rev, api_key_hash="hrev")

        PeerReview.objects.create(
            research_node=node,
            assigned_reviewer=reviewer,
            status="completed",
            soundness=8,
            significance=8,
            novelty=8,
            clarity=8,
            value=8.0,
            is_approved=True,
            structured_data={"ok": True},
        )

        with patch("main_api.tasks.task_auto_resolve_coordinator_decision.apply_async"):
            task_resolve_node(node.id)

        node.refresh_from_db()
        self.assertEqual(node.status, "awaiting_coordinator")
        execute_publish(node)

        m_worker1.refresh_from_db()
        m_worker2.refresh_from_db()
        m_worker3.refresh_from_db()

        self.assertEqual(m_worker1.balance_blue_stars, Decimal("1042.6667"))
        self.assertEqual(m_worker2.balance_blue_stars, Decimal("1042.6667"))
        self.assertEqual(m_worker3.balance_blue_stars, Decimal("1042.6667"))

    def test_auto_resolve_coordinator_decision(self):
        from unittest.mock import patch
        from django.utils import timezone
        from datetime import timedelta

        node = self.create_node(self.agent1, collaborators=1, caps=[self.cap_python])
        node.status = "awaiting_coordinator"
        node.orchestrator_verdict = "ACCEPT"
        node.decision_deadline = timezone.now() - timedelta(minutes=5)
        node.save()

        with patch("main_api.tasks.execute_publish") as mock_publish:
            task_auto_resolve_coordinator_decision(node.id)
            mock_publish.assert_called_once_with(node)

        # Test rejection path
        node.orchestrator_verdict = "REJECT"
        node.save()
        with patch("main_api.tasks.execute_reject") as mock_reject:
            task_auto_resolve_coordinator_decision(node.id)
            mock_reject.assert_called_once_with(node)
