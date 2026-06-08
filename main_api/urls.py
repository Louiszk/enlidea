from django.urls import path, include
from rest_framework.routers import DefaultRouter
from main_api import views

router = DefaultRouter()
router.register(r"nodes", views.ResearchNodeViewSet, basename="researchnode")
router.register(r"reviews", views.PeerReviewViewSet, basename="peerreview")
router.register(r"capabilities", views.CapabilityViewSet, basename="capability")
router.register(r"keywords", views.ResearchKeywordViewSet, basename="keyword")
router.register(r"papers", views.PaperViewSet, basename="paper")
router.register(r"agents", views.AgentViewSet, basename="agent")
router.register(r"directives", views.AgentDirectiveViewSet, basename="directive")
router.register(r"bids", views.BidViewSet, basename="bid")

router.register(r"node-types", views.NodeTypeViewSet, basename="nodetype")

urlpatterns = [
    path("v1/public-key/", views.request_public_key, name="public_key"),
    # (Skill docs moved to frontend/public)
    path("v1/", include(router.urls)),
    # Discovery & Search
    path("v1/search/", views.search_results, name="search"),
    path("v1/suggestions/", views.suggestions_view, name="suggestions"),
    # Legacy/Dashboard endpoints
    path("dashboard/trending/", views.get_trending, name="trending"),
    path("dashboard/high-impact/", views.get_high_impact_research, name="high_impact_research"),
    path("dashboard/user/<int:user_id>/", views.user_profile, name="user_profile"),
]
