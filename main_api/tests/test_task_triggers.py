from rest_framework import status
from django.urls import reverse
import hashlib
from main_api.models import PeerReview
from accounts.models import Agent
from unittest.mock import patch
from main_api.tests.test_agent_auth import EnlideaBaseTestCase
from decimal import Decimal


class TaskTriggersTest(EnlideaBaseTestCase):
    def setUp(self):
        super().setUp()
        # Mock transaction.on_commit to execute immediately for testing in Django 3.1
        self.on_commit_patcher = patch("django.db.transaction.on_commit", side_effect=lambda f: f())
        self.mock_on_commit = self.on_commit_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.on_commit_patcher.stop()

    @patch("main_api.tasks.task_handle_node_deadline.apply_async")
    def test_bid_triggers_deadline_task(self, mock_apply_async):
        node = self.create_node(self.agent1, collaborators=2, caps=[self.cap_python])
        bid_url = reverse("researchnode-bid", kwargs={"pk": node.pk})
        eval_url_template = reverse("bid-evaluate", kwargs={"pk": 0})

        # Agent 2 bids
        self.client.post(bid_url, {"interview_response": "test"}, HTTP_X_AGENT_API_KEY=self.agent2_raw_key)

        # Accept bid
        bid2 = node.bids.get(agent=self.agent2)
        self.client.post(
            eval_url_template.replace("0/", f"{bid2.pk}/"),
            {"action": "accept"},
            HTTP_X_AGENT_API_KEY=self.agent1_raw_key,
        )

        # Check node.required_collaborators logic.
        node.refresh_from_db()
        if node.status == "in_progress":
            mock_apply_async.assert_called_once()
        else:
            mock_apply_async.assert_not_called()

            # Agent 3 bids
            agent3_raw_key = "key-gamma"
            agent3 = Agent.objects.create(
                name="Agent Gamma",
                maintainer=self.maintainer1,
                api_key_hash=hashlib.sha256(agent3_raw_key.encode()).hexdigest(),
                orange_stars=Decimal("10.0000"),
            )
            agent3.capabilities.add(self.cap_python)

            self.client.post(bid_url, {"interview_response": "test"}, HTTP_X_AGENT_API_KEY=agent3_raw_key)
            bid3 = node.bids.get(agent=agent3)
            self.client.post(
                eval_url_template.replace("0/", f"{bid3.pk}/"),
                {"action": "accept"},
                HTTP_X_AGENT_API_KEY=self.agent1_raw_key,
            )

            # Now it must be in_progress, should trigger deadline
            node.refresh_from_db()
            self.assertEqual(node.status, "in_progress")
            mock_apply_async.assert_called_once_with(args=(node.id,), eta=node.deadline)

    @patch("main_api.tasks.task_matchmake_node.delay")
    def test_finalize_triggers_matchmake_task(self, mock_delay):
        from django.core.files.uploadedfile import SimpleUploadedFile

        node = self.create_node(self.agent1, caps=[self.cap_python])
        node.status = "in_progress"
        node.save()

        url = reverse("researchnode-finalize", kwargs={"pk": node.pk})
        long_content = (
            b"Research Paper Content that is significantly longer to pass the one hundred and forty character minimum constraint required by the new validation rule in the serializer. "
            * 5
        )
        md_file = SimpleUploadedFile("final.md", long_content, content_type="text/markdown")

        response = self.client.post(
            url, {"file": md_file}, format="multipart", HTTP_X_AGENT_API_KEY=self.agent1_raw_key
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        node.refresh_from_db()
        self.assertEqual(node.status, "in_review")
        mock_delay.assert_called_once_with(node.id)

    @patch("main_api.tasks.task_resolve_node.delay")
    def test_peer_review_triggers_resolve_task(self, mock_delay):
        node = self.create_node(self.agent1, bounty=100, required_reviews=1)
        node.status = "in_review"
        node.save()

        reviewer = Agent.objects.create(
            name="Reviewer Bot",
            maintainer=self.maintainer1,
            api_key_hash=hashlib.sha256("key-rev".encode()).hexdigest(),
        )
        reviewer_raw_key = "key-rev"

        review = PeerReview.objects.create(
            research_node=node,
            assigned_reviewer=reviewer,
            status="claimed",
            soundness=0,
            significance=0,
            novelty=0,
            clarity=0,
            value=0.0,
        )

        url = reverse("peerreview-detail", kwargs={"pk": review.pk})

        # Complete the review
        data = {
            "soundness": 8,
            "significance": 8,
            "novelty": 8,
            "clarity": 8,
            "recommendation": "ACCEPT",
            "detailed_comments": "Looks great",
            "structured_data": {"comment": "Looks great"},
        }

        response = self.client.put(url, data, format="json", HTTP_X_AGENT_API_KEY=reviewer_raw_key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_delay.assert_called_once_with(node.id)
