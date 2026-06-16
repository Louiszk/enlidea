from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from accounts.models import Agent, Account
from accounts.authentication import CookieJWTAuthentication
from main_api.models import ResearchNode, Paper
from main_api.authentication import AgentApiKeyAuthentication
from main_api.permissions import IsNotPublicAgent
from .models import Notification, Appreciation, Report, Complaint
from .serializers import NotificationSerializer, FollowSerializer
from main_api.serializer import ResearchNodeCardSerializer, AgentSerializer
from django.db.models import F, Sum
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
import math
import logging

from .services import evaluate_auto_kick
from decimal import Decimal

User = get_user_model()
logger = logging.getLogger(__name__)

# Constants for Tokenomics
TREASURY_USERNAME = "System_Treasury"
APPRECIATION_BS_REWARD = Decimal("2.0000")


@extend_schema(
    request=inline_serializer(
        name="AppreciatePaperRequest",
        fields={
            "vote": serializers.IntegerField(),
        },
    ),
    responses={
        200: inline_serializer(
            name="AppreciatePaperResponse",
            fields={
                "appreciation_score": serializers.FloatField(),
                "user_vote": serializers.IntegerField(),
            },
        ),
        400: inline_serializer(
            name="AppreciatePaperBadRequest",
            fields={
                "error": serializers.CharField(),
            },
        ),
        403: inline_serializer(
            name="AppreciatePaperForbidden",
            fields={
                "error": serializers.CharField(),
            },
        ),
        404: inline_serializer(
            name="AppreciatePaperNotFound",
            fields={
                "detail": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def appreciate_paper(request, paper_id):
    vote = request.data.get("vote")
    try:
        vote = int(vote)
    except (ValueError, TypeError):
        return Response({"error": "Invalid vote value. Must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

    if vote not in [-2, -1, 1, 2]:
        return Response({"error": "Invalid vote value. Must be -2, -1, 1, or 2."}, status=status.HTTP_400_BAD_REQUEST)

    paper = get_object_or_404(Paper, id=paper_id)

    # Anti-Collusion: Prevent maintainers from appreciating their own agents' papers
    if paper.authors.filter(maintainer=request.user).exists():
        return Response(
            {"error": "You cannot appreciate a paper authored by your own agents."}, status=status.HTTP_403_FORBIDDEN
        )

    total_reputation = (
        Agent.objects.filter(maintainer=request.user, is_active=True).aggregate(total=Sum("orange_stars"))["total"] or 0
    )
    safe_reputation = max(0.0, float(total_reputation))
    impact_raw = int(vote) * max(1.0, math.log10(safe_reputation + 10.0))
    impact = Decimal(str(impact_raw)).quantize(Decimal("0.0001"))

    with transaction.atomic():
        obj, created = Appreciation.objects.update_or_create(
            user=request.user, paper=paper, defaults={"vote": vote, "impact": impact}
        )
        total_score = paper.appreciations.aggregate(total=Sum("impact"))["total"] or 0.0
        Paper.objects.filter(id=paper_id).update(appreciation_score=total_score)

        # Tokenomics: Reward human maintainers for curation (max 5/day)
        if created:
            cache_key = f"appreciation_reward_count_{request.user.id}_{timezone.now().date()}"
            # Atomic initialization of cache key
            cache.add(cache_key, 0, 86400)
            reward_count = cache.incr(cache_key)

            if reward_count <= 5:
                # 1. Deduct from Treasury (Lock-free atomic deduction)
                try:
                    updated_rows = Account.objects.filter(
                        username=TREASURY_USERNAME, balance_blue_stars__gte=APPRECIATION_BS_REWARD
                    ).update(balance_blue_stars=F("balance_blue_stars") - APPRECIATION_BS_REWARD)

                    if updated_rows > 0:
                        # 2. Reward Maintainer
                        Account.objects.filter(id=request.user.id).update(
                            balance_blue_stars=F("balance_blue_stars") + APPRECIATION_BS_REWARD
                        )

                        Notification.objects.create(
                            recipient=request.user,
                            notification_type="payout_received",
                            verb=f"You earned {APPRECIATION_BS_REWARD} Blue Stars for rating: {paper.title}",
                        )
                    else:
                        logger.warning(f"Treasury dry! Could not reward curation for user {request.user.id}")
                except Exception as e:
                    logger.error(f"Error rewarding curation: {str(e)}")

    return Response({"appreciation_score": total_score, "user_vote": vote}, status=status.HTTP_200_OK)


@extend_schema(
    request=None,
    responses={
        200: inline_serializer(
            name="FollowUserResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        400: inline_serializer(
            name="FollowUserBadRequest",
            fields={
                "error": serializers.CharField(),
            },
        ),
        404: inline_serializer(
            name="FollowUserNotFound",
            fields={
                "error": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def follow_user(request, user_id):
    try:
        user_to_follow = User.objects.get(id=user_id)

        # Hide Treasury and Public Pool
        if user_to_follow.username in [TREASURY_USERNAME, "Public_Pool"]:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.user == user_to_follow:
            return Response({"error": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.follows.add(user_to_follow)
        return Response({"message": f"You are now following {user_to_follow.username}"}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    request=None,
    responses={
        200: inline_serializer(
            name="UnfollowUserResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        404: inline_serializer(
            name="UnfollowUserNotFound",
            fields={
                "error": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unfollow_user(request, user_id):
    try:
        user_to_unfollow = User.objects.get(id=user_id)
        request.user.follows.remove(user_to_unfollow)
        return Response({"message": f"You have unfollowed {user_to_unfollow.username}"}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(request=None, responses=FollowSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_follows(request):
    user = request.user
    follows = user.follows.all()
    serializer = FollowSerializer(follows, many=True)
    return Response(serializer.data)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="page",
            description="Page number",
            required=False,
            type=int,
        )
    ],
    responses=inline_serializer(
        name="HomeFeedResponse",
        fields={
            "nodes": ResearchNodeCardSerializer(many=True),
            "nextPage": serializers.IntegerField(allow_null=True),
        },
    ),
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def home_feed(request, user_id):
    items_per_page = 10
    page = request.GET.get("page", 1)

    if user_id != 0:
        followed_users = [user_id]
    else:
        followed_users = request.user.follows.values_list("id", flat=True)

    nodes = (
        ResearchNode.objects.with_aggregates()
        .filter(coordinating_agent__maintainer_id__in=followed_users)
        .order_by("-created")
    )

    from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

    paginator = Paginator(nodes, items_per_page)
    try:
        current_page = paginator.page(page)
    except PageNotAnInteger:
        current_page = paginator.page(1)
    except EmptyPage:
        current_page = paginator.page(paginator.num_pages)

    serializer = ResearchNodeCardSerializer(current_page, many=True)
    next_page = current_page.next_page_number() if current_page.has_next() else None

    return Response({"nodes": serializer.data, "nextPage": next_page}, status=status.HTTP_200_OK)


@extend_schema(request=None, responses=NotificationSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by("-created_at")[:20]
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@extend_schema(
    request=None,
    responses={
        200: inline_serializer(
            name="MarkNotificationsAsReadResponse",
            fields={
                "message": serializers.CharField(),
            },
        )
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notifications_as_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return Response({"message": "All notifications marked as read"}, status=status.HTTP_200_OK)


@extend_schema(
    request=None,
    responses={
        200: inline_serializer(
            name="SaveNodeResponse",
            fields={
                "message": serializers.CharField(),
                "saved": serializers.BooleanField(),
            },
        ),
        404: inline_serializer(
            name="SaveNodeNotFound",
            fields={
                "detail": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_node(request, node_id):
    with transaction.atomic():
        user = User.objects.select_for_update().get(id=request.user.id)
        if not ResearchNode.objects.filter(id=node_id).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if node_id in user.saved_nodes:
            user.saved_nodes.remove(node_id)
            ResearchNode.objects.filter(id=node_id).update(saves=F("saves") - 1)
            message = "Node removed from saved collection"
            is_saved = False
        else:
            user.saved_nodes.append(node_id)
            ResearchNode.objects.filter(id=node_id).update(saves=F("saves") + 1)
            message = "Node saved to collection"
            is_saved = True

        user.save(update_fields=["saved_nodes"])

    return Response({"message": message, "saved": is_saved}, status=status.HTTP_200_OK)


@extend_schema(
    request=None,
    responses={
        200: inline_serializer(
            name="SavePaperResponse",
            fields={
                "message": serializers.CharField(),
                "saved": serializers.BooleanField(),
            },
        ),
        404: inline_serializer(
            name="SavePaperNotFound",
            fields={
                "detail": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_paper(request, paper_id):
    with transaction.atomic():
        user = User.objects.select_for_update().get(id=request.user.id)
        if not Paper.objects.filter(id=paper_id).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if paper_id in user.saved_papers:
            user.saved_papers.remove(paper_id)
            Paper.objects.filter(id=paper_id).update(saves=F("saves") - 1)
            message = "Paper removed from saved collection"
            is_saved = False
        else:
            user.saved_papers.append(paper_id)
            Paper.objects.filter(id=paper_id).update(saves=F("saves") + 1)
            message = "Paper saved to collection"
            is_saved = True

        user.save(update_fields=["saved_papers"])

    return Response({"message": message, "saved": is_saved}, status=status.HTTP_200_OK)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="page",
            description="Page number",
            required=False,
            type=int,
        )
    ],
    responses=inline_serializer(
        name="LeaderboardResponse",
        fields={
            "agents": AgentSerializer(many=True),
        },
    ),
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def leaderboard(request):
    from django.core.paginator import Paginator
    from main_api.tasks import TREASURY_USERNAME

    page = request.GET.get("page", 1)
    items_per_page = 10
    top_agents = (
        Agent.objects.filter(is_active=True)
        .exclude(maintainer__username="Public_Pool")
        .exclude(maintainer__username=TREASURY_USERNAME)
        .order_by("-orange_stars")
    )
    paginator = Paginator(top_agents, items_per_page)
    try:
        current_page = paginator.page(page)
    except:
        current_page = paginator.page(1)

    serializer = AgentSerializer(current_page, many=True)
    return Response({"agents": serializer.data}, status=status.HTTP_200_OK)


@extend_schema(
    request=inline_serializer(
        name="ReportContentRequest",
        fields={
            "target_type": serializers.ChoiceField(choices=["node", "agent", "account"]),
            "target_id": serializers.IntegerField(),
            "reason": serializers.CharField(),
            "description": serializers.CharField(),
            "node_id": serializers.IntegerField(required=False, allow_null=True),
        },
    ),
    responses={
        201: inline_serializer(
            name="ReportContentCreatedResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        200: inline_serializer(
            name="ReportContentOKResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        400: inline_serializer(
            name="ReportContentBadRequestResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
        404: inline_serializer(
            name="ReportContentNotFoundResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
        429: inline_serializer(
            name="ReportContentRateLimitedResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@authentication_classes([AgentApiKeyAuthentication, CookieJWTAuthentication])
@permission_classes([IsAuthenticated, IsNotPublicAgent])
def report_content(request):
    target_type_str = request.data.get("target_type")
    target_id = request.data.get("target_id")
    reason = request.data.get("reason")
    description = request.data.get("description")
    node_id_context = request.data.get("node_id")  # New field for context

    if not all([target_type_str, target_id, reason, description]):
        return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

    # Map target type to ContentType
    type_map = {"node": ResearchNode, "agent": Agent, "account": User}

    target_model = type_map.get(target_type_str)
    if not target_model:
        return Response({"error": "Invalid target type."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        content_type = ContentType.objects.get_for_model(target_model)
        if not target_model.objects.filter(id=target_id).exists():
            return Response({"error": "Target object not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception:
        return Response({"error": "Error resolving target."}, status=status.HTTP_400_BAD_REQUEST)

    # Rate Limiting
    user_id = request.user.id
    is_agent = isinstance(request.user, Agent)
    cache_id = f"agent_{user_id}" if is_agent else f"user_{user_id}"

    last_report_key = f"report_last_5min_{cache_id}"
    daily_count_key = f"report_daily_count_{cache_id}"

    # Atomic rate limiting checks
    if not cache.add(last_report_key, True, 300):
        return Response(
            {"error": "You can only report once every 5 minutes."}, status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    try:
        daily_count = cache.incr(daily_count_key)
    except ValueError:
        # The key didn't exist, so set it initially
        cache.set(daily_count_key, 1, 86400)
        daily_count = 1

    if daily_count > 10:
        return Response({"error": "Daily report limit reached (10)."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    # Proxy Logic
    if is_agent and target_type_str == "account":
        Notification.objects.create(
            recipient=request.user.maintainer,
            notification_type="custom",
            verb=f"Your agent {request.user.name} flagged Maintainer ID {target_id} for {reason}. Please review and submit a formal report.",
        )
        return Response({"message": "Report flagged for maintainer review."}, status=status.HTTP_200_OK)

    # Create Report
    with transaction.atomic():
        Report.objects.create(
            reporter_account=request.user.maintainer if is_agent else request.user,
            reporter_agent=request.user if is_agent else None,
            content_type=content_type,
            object_id=target_id,
            node_id=node_id_context,
            reason=reason,
            description=description,
        )

        # Trigger Auto-Kick Evaluation if applicable
        if target_type_str == "agent" and node_id_context and reason in ["malicious_activity", "inappropriate"]:
            try:
                evaluate_auto_kick(int(target_id), node_id_context)
            except (ValueError, TypeError):
                pass

    return Response({"message": "Report submitted successfully"}, status=status.HTTP_201_CREATED)


@extend_schema(
    request=inline_serializer(
        name="SubmitComplaintRequest",
        fields={
            "category": serializers.CharField(),
            "description": serializers.CharField(),
            "reference_id": serializers.IntegerField(required=False, allow_null=True),
        },
    ),
    responses={
        201: inline_serializer(
            name="SubmitComplaintCreatedResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        400: inline_serializer(
            name="SubmitComplaintBadRequestResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
        403: inline_serializer(
            name="SubmitComplaintForbiddenResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
        429: inline_serializer(
            name="SubmitComplaintRateLimitedResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@authentication_classes([AgentApiKeyAuthentication, CookieJWTAuthentication])
@permission_classes([IsAuthenticated])
def submit_complaint(request):
    if isinstance(request.user, Agent):
        return Response({"error": "Only human accounts can submit complaints."}, status=status.HTTP_403_FORBIDDEN)

    category = request.data.get("category")
    description = request.data.get("description")
    reference_id = request.data.get("reference_id")

    if not all([category, description]):
        return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

    # Rate Limiting
    user_id = request.user.id
    daily_count_key = f"complaint_daily_count_user_{user_id}"

    try:
        daily_count = cache.incr(daily_count_key)
    except ValueError:
        # The key didn't exist, so set it initially
        cache.set(daily_count_key, 1, 86400)
        daily_count = 1

    if daily_count > 4:
        return Response({"error": "Daily complaint limit reached (4)."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    Complaint.objects.create(user=request.user, category=category, description=description, reference_id=reference_id)

    return Response({"message": "Complaint submitted successfully"}, status=status.HTTP_201_CREATED)
