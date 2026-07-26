from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient
from decimal import Decimal
from main_api.models import ResearchNode, TrendingCache, Trend, NodeType
from accounts.models import Agent
import hashlib

User = get_user_model()


class TrendingAndRankerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.maintainer = User.objects.create_user(
            username="test_maintainer",
            email="maintainer@example.com",
            password="Password123!",
            balance_blue_stars=Decimal("100.0000"),
            is_active=True,
        )
        self.public_pool = User.objects.create_user(
            username="Public_Pool",
            email="public_pool@example.com",
            password="Password123!",
            is_active=True,
        )
        self.agent1 = Agent.objects.create(
            name="Agent_Alpha",
            maintainer=self.maintainer,
            api_key_hash=hashlib.sha256(b"key1").hexdigest(),
            orange_stars=Decimal("25.5000"),
            is_active=True,
        )
        self.agent2 = Agent.objects.create(
            name="Agent_Beta",
            maintainer=self.maintainer,
            api_key_hash=hashlib.sha256(b"key2").hexdigest(),
            orange_stars=Decimal("14.5000"),
            is_active=True,
        )
        self.anon_agent = Agent.objects.create(
            name="Anon_PublicAgent",
            maintainer=self.public_pool,
            api_key_hash=hashlib.sha256(b"anon_key").hexdigest(),
            orange_stars=Decimal("100.0000"),
            is_active=True,
        )
        self.node_type = NodeType.objects.create(name="Research Node")
        self.node = ResearchNode.objects.create(
            title="Test Node",
            body="Node Body",
            coordinating_agent=self.agent1,
            type=self.node_type,
            status="open",
        )

    def test_get_trending_fallback(self):
        # Delete any existing trending cache
        TrendingCache.objects.all().delete()
        response = self.client.get("/api/dashboard/trending/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("trendingCombinations", response.data)
        self.assertIn("trendingCategories", response.data)
        self.assertTrue(TrendingCache.objects.exists())

    def test_node_retrieve_increments_visits(self):
        response = self.client.get(f"/api/v1/nodes/{self.node.id}/")
        self.assertEqual(response.status_code, 200)
        trend = Trend.objects.get(research_node=self.node)
        self.assertGreaterEqual(trend.daily_visits[0], 1)

    def test_node_save_increments_saves(self):
        self.client.force_authenticate(user=self.maintainer)
        response = self.client.post(f"/social-api/nodes/{self.node.id}/save/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get("saved"))
        trend = Trend.objects.get(research_node=self.node)
        self.assertGreaterEqual(trend.daily_saves[0], 1)

    def test_ranker_command_syncs_maintainer_trust(self):
        call_command("ranker")
        self.maintainer.refresh_from_db()
        self.public_pool.refresh_from_db()

        # agent1 (25.5) + agent2 (14.5) = 40.0
        self.assertEqual(self.maintainer.balance_orange_stars, Decimal("40.0000"))
        # score = round(40.0 + 100.0 / 10) = 50
        self.assertEqual(self.maintainer.score, 50)
        self.assertEqual(self.maintainer.rank, 1)

        # Public_Pool should be excluded from ranking
        self.assertIsNone(self.public_pool.rank)
        self.assertIsNone(self.public_pool.score)

    def test_realtime_maintainer_trust_signal(self):
        # 1. Check initial balance synced via setUp Agent creation (25.5 + 14.5 = 40.0)
        self.maintainer.refresh_from_db()
        self.assertEqual(self.maintainer.balance_orange_stars, Decimal("40.0000"))

        # 2. Update agent1 trust score directly via save()
        self.agent1.orange_stars += Decimal("10.0000")
        self.agent1.save(update_fields=["orange_stars"])
        self.maintainer.refresh_from_db()
        self.assertEqual(self.maintainer.balance_orange_stars, Decimal("50.0000"))

        # 3. Create new agent for maintainer
        new_agent = Agent.objects.create(
            name="Agent_Gamma",
            maintainer=self.maintainer,
            api_key_hash=hashlib.sha256(b"key3").hexdigest(),
            orange_stars=Decimal("15.0000"),
            is_active=True,
        )
        self.maintainer.refresh_from_db()
        self.assertEqual(self.maintainer.balance_orange_stars, Decimal("65.0000"))

        # 4. Delete new agent
        new_agent.delete()
        self.maintainer.refresh_from_db()
        self.assertEqual(self.maintainer.balance_orange_stars, Decimal("50.0000"))
