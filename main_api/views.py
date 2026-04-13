from rest_framework import viewsets, status, permissions, mixins, authentication, throttling
from accounts.authentication import CookieJWTAuthentication
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes, authentication_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction, models, IntegrityError
from django.db.models import Q, F, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta, timezone as dt_timezone
from .models import Capability, ResearchNode, PeerReview, TrendingCache, NodeType, ResearchKeyword, Paper, AgentDirective, Bid, Attachment, AgentMessage
from accounts.models import Agent
import logging
import hashlib
import uuid
import secrets
import string

logger = logging.getLogger(__name__)
from .serializer import (
    CapabilitySerializer, ResearchNodeSerializer, ResearchNodeCardSerializer,
    PeerReviewSerializer, AgentSerializer, UserSerializer,
    CreateResearchNodeSerializer, EditResearchNodeSerializer, ResearchNodeBodySerializer,
    CommentSerializer, SubCommentSerializer, ResearchKeywordSerializer, PaperSerializer,
    AgentDirectiveSerializer, NodeTypeSerializer, BidSerializer, AgentSyncNodeSerializer,
    AgentMessageSerializer, ResearchNodePlanSerializer, CapabilitySearchSerializer
)
from .authentication import AgentApiKeyAuthentication
from .permissions import IsAgent, IsMaintainer, IsNotPublicAgent
from .services import (
    download_remote_file, create_research_node, update_research_node, delete_research_node,
    submit_bid, evaluate_bid_service, finalize_research_service, handle_coordinator_decision
)
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError, PermissionDenied
import json
from decimal import Decimal

User = get_user_model()

from rest_framework.pagination import PageNumberPagination

class ResearchNodePagination(PageNumberPagination):
    page_size = 9
    
    def get_paginated_response(self, data):
        return Response({
            'nodes': data,
            'total_pages': self.page.paginator.num_pages,
            'count': self.page.paginator.count
        })

class PaperPagination(PageNumberPagination):
    page_size = 9
    
    def get_paginated_response(self, data):
        return Response({
            'papers': data,
            'nextPage': self.page.next_page_number() if self.page.has_next() else None,
            'previousPage': self.page.previous_page_number() if self.page.has_previous() else None,
            'total_pages': self.page.paginator.num_pages,
            'count': self.page.paginator.count
        })

class NodeTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NodeType.objects.all()
    serializer_class = NodeTypeSerializer
    authentication_classes = []

class CapabilityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Capability.objects.all()
    serializer_class = CapabilitySerializer
    lookup_field = 'slug'
    authentication_classes = []

    def get_queryset(self):
        queryset = Capability.objects.all()
        parent = self.request.query_params.get('parent')
        if parent == 'top':
            queryset = queryset.filter(parent_capabilities__isnull=True)
        elif parent:
            queryset = queryset.filter(parent_capabilities__slug=parent)
        return queryset

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.GET.get('q', '').lower()
        if len(query) < 2:
            return Response([])
        capabilities = Capability.objects.filter(title__icontains=query)[:10]
        serializer = CapabilitySerializer(capabilities, many=True)
        return Response(serializer.data)

class ResearchKeywordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ResearchKeyword.objects.all()
    serializer_class = ResearchKeywordSerializer
    lookup_field = 'slug'
    authentication_classes = []

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.GET.get('q', '').lower()
        if len(query) < 2:
            return Response([])
        keywords = ResearchKeyword.objects.filter(name__icontains=query)[:10]
        serializer = ResearchKeywordSerializer(keywords, many=True)
        return Response(serializer.data)

class AgentViewSet(viewsets.ModelViewSet):
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Agent.objects.filter(maintainer=self.request.user)

    def create(self, request, *args, **kwargs):
        if Agent.objects.filter(maintainer=self.request.user).count() >= 4:
            raise ValidationError({"detail": "Agent limit reached. You can only deploy a maximum of 4 agents."})
            
        # Move the check inside the atomic block with a lock
        with transaction.atomic():
            maintainer = User.objects.select_for_update().get(id=self.request.user.id)
            
            if maintainer.balance_blue_stars < Decimal('50.0000'):
                raise ValidationError({"detail": "Insufficient Blue Stars. Deploying an agent costs 50 Blue Stars."})

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            raw_key = str(uuid.uuid4())
            # Use fast SHA-256 for O(1) database lookups
            hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
            
            maintainer.balance_blue_stars -= Decimal('50.0000')
            maintainer.save()

            # Transfer fee to System Treasury
            from main_api.tasks import TREASURY_USERNAME
            from accounts.models import Account
            updated_count = Account.objects.filter(
                username=TREASURY_USERNAME
            ).update(
                balance_blue_stars=F('balance_blue_stars') + Decimal('50.0000')
            )
            if updated_count == 0:
                logger.error("Treasury account not found during agent deployment!")
            agent = serializer.save(maintainer=maintainer, api_key_hash=hashed_key)
        
        # Return the original agent data plus the raw API key
        data = serializer.data
        data['api_key'] = raw_key
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def rotate_api_key(self, request, pk=None):
        agent = self.get_object()
        raw_key = str(uuid.uuid4())
        # Use fast SHA-256 for O(1) database lookups
        agent.api_key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        agent.save()
        return Response({'api_key': raw_key})

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        agent = self.get_object()
        agent.is_active = False
        agent.save()
        return Response({'status': 'revoked'})

    @action(detail=False, methods=['get'])
    def check_name(self, request):
        name = request.query_params.get('name', '').strip()
        if not name:
            return Response({'available': False, 'detail': 'Name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        exists = Agent.objects.filter(name__iexact=name).exists()
        return Response({'available': not exists})

    @action(detail=False, methods=['get'], authentication_classes=[AgentApiKeyAuthentication], permission_classes=[IsAgent, IsNotPublicAgent])
    def sync(self, request):
        agent = request.user
        # Only update the DB if it's been more than 5 minutes since the last ping
        if not agent.last_active_at or (timezone.now() - agent.last_active_at).total_seconds() > 300:
            Agent.objects.filter(pk=agent.pk).update(last_active_at=timezone.now())
        
        since_timestamp = request.query_params.get('since_timestamp')
        
        # Removed maintainer filter to allow global broadcasts (e.g. from Public_Pool)
        directives_qs = AgentDirective.objects.filter(
            Q(agent=agent) | Q(agent__isnull=True),
            status='pending'
        )
        
        nodes_qs = ResearchNode.objects.filter(
            Q(assigned_agents=agent) | Q(coordinating_agent=agent),
            status__in=['open', 'in_progress', 'in_review', 'awaiting_coordinator']
        ).select_related(
            'coordinating_agent', 'coordinating_agent__maintainer', 'type'
        ).prefetch_related(
            'required_capabilities', 'keywords', 'assigned_agents'
        ).distinct()

        reviews_qs = PeerReview.objects.filter(
            assigned_reviewer=agent,
            status__in=['pending', 'claimed']
        )
        
        bids_to_evaluate_qs = Bid.objects.filter(
            node__coordinating_agent=agent,
            status='pending'
        ).select_related('node', 'agent')

        # Calculate latest update timestamp
        timestamps = []
        
        max_directive = directives_qs.aggregate(max_ts=models.Max('updated_at'))['max_ts']
        if max_directive: timestamps.append(max_directive.timestamp())
        
        max_node = nodes_qs.aggregate(max_ts=models.Max('updated'))['max_ts']
        if max_node: timestamps.append(max_node.timestamp())
        
        max_review = reviews_qs.aggregate(max_ts=models.Max('created'))['max_ts']
        if max_review: timestamps.append(max_review.timestamp())
        
        max_bid = bids_to_evaluate_qs.aggregate(max_ts=models.Max('created_at'))['max_ts']
        if max_bid: timestamps.append(max_bid.timestamp())

        max_message = AgentMessage.objects.filter(node__in=nodes_qs).aggregate(max_ts=models.Max('created_at'))['max_ts']
        if max_message: timestamps.append(max_message.timestamp())

        latest_update = max(timestamps) if timestamps else 0
        
        # Logic: If since_timestamp matches latest_update, return 304
        if since_timestamp:
            try:
                if abs(float(since_timestamp) - latest_update) < 0.001:
                    return Response({}, status=status.HTTP_304_NOT_MODIFIED)
            except (ValueError, TypeError):
                pass

        return Response({
            'timestamp': latest_update,
            'agent_meta': {
                'id': agent.id,
                'name': agent.name,
                'capabilities': list(agent.capabilities.values_list('slug', flat=True))
            },
            'balances': {
                'blue_stars': agent.maintainer.balance_blue_stars,
                'orange_stars': agent.orange_stars
            },
            'directives': AgentDirectiveSerializer(directives_qs, many=True, context={'request': request}).data,
            'assignments': AgentSyncNodeSerializer(nodes_qs, many=True, context={'request': request}).data,
            'pending_reviews': PeerReviewSerializer(reviews_qs, many=True, context={'request': request}).data,
            'bids_to_evaluate': BidSerializer(bids_to_evaluate_qs, many=True, context={'request': request}).data
        })

class ResearchNodeViewSet(viewsets.ModelViewSet):
    queryset = ResearchNode.objects.all()
    authentication_classes = [AgentApiKeyAuthentication, CookieJWTAuthentication, authentication.SessionAuthentication]
    pagination_class = ResearchNodePagination
    throttle_scope = 'agent_read'

    def get_throttles(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'bid', 'attachments', 'finalize', 'plan', 'coordinator_decision', 'extend_deadline']:
            self.throttle_scope = 'agent_action'
        elif self.action == 'messages' and self.request and self.request.method.lower() == 'post':
            self.throttle_scope = 'agent_action'
        else:
            self.throttle_scope = 'agent_read'
        return super().get_throttles()

    def get_queryset(self):
        queryset = ResearchNode.objects.all()
        capability_slug = self.request.query_params.get('capability')
        keyword_slug = self.request.query_params.get('keyword')
        maintainer_id = self.request.query_params.get('maintainer')
        search_query = self.request.query_params.get('search')
        sort_by = self.request.query_params.get('sort')
        filters_param = self.request.query_params.get('filters')

        if filters_param:
            try:
                filters = json.loads(filters_param)
                status_filter = filters.get('status')
                if status_filter:
                    queryset = queryset.filter(status__in=status_filter.split(','))
                
                types_filter = filters.get('types')
                if types_filter:
                    queryset = queryset.filter(type__name__in=types_filter.split(','))
                
                tags_filter = filters.get('tags')
                if tags_filter:
                    # Try capabilities first
                    queryset = queryset.filter(Q(required_capabilities__slug__in=tags_filter.split(',')) | Q(keywords__slug__in=tags_filter.split(',')))
            except json.JSONDecodeError:
                pass

        # Legacy direct status param support
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status__in=status_param.split(','))
        
        if capability_slug and capability_slug != 'undefined':
            queryset = queryset.filter(required_capabilities__slug=capability_slug)

        if keyword_slug:
            queryset = queryset.filter(keywords__slug=keyword_slug)
            
        if maintainer_id:
            queryset = queryset.filter(coordinating_agent__maintainer_id=maintainer_id)

        if self.request.query_params.get('saved') == 'true' and self.request.user.is_authenticated:
            queryset = queryset.filter(id__in=self.request.user.saved_nodes)
            
        if search_query:
            queryset = queryset.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))
            
        if sort_by == 'bounty_amount':
            queryset = queryset.order_by('-bounty_amount')
        elif sort_by == 'collaborative':
            queryset = queryset.annotate(agent_count=Count('assigned_agents')).order_by('-agent_count')
        elif sort_by == 'rating':
            queryset = queryset.annotate(avg_rating=Avg('reviews__value')).order_by('-avg_rating')
        elif sort_by == 'created_desc':
            queryset = queryset.order_by('-created')
        elif sort_by == 'trending':
            queryset = ResearchNode.with_trend_score().order_by('-trend_score')
        else:
            queryset = queryset.order_by('-created')
            
        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            
            capability_slug = self.request.query_params.get('capability')
            if capability_slug:
                try:
                    cap = Capability.objects.get(slug=capability_slug)
                    path = cap.get_path()
                    response.data['category_path'] = [{'title': c.title, 'slug': c.slug} for c in path]
                except Capability.DoesNotExist:
                    pass
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.instance = update_research_node(self.get_object(), self.request.user, serializer.validated_data)

    def perform_destroy(self, instance):
        delete_research_node(instance, self.request.user)
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateResearchNodeSerializer
        if self.action in ['update', 'partial_update']:
            return EditResearchNodeSerializer
        if self.action == 'list':
            return ResearchNodeCardSerializer
        return ResearchNodeSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAgent(), IsNotPublicAgent()]
        if self.action in ['update', 'partial_update', 'destroy']:
            # Allow both Agents and Maintainers through the front door
            return [permissions.IsAuthenticated(), IsNotPublicAgent()]
        if self.action in ['active', 'bid', 'attachments', 'finalize', 'messages', 'plan', 'coordinator_decision', 'extend_deadline']:
            return [permissions.IsAuthenticated(), IsNotPublicAgent()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.instance = create_research_node(self.request.user, serializer.validated_data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def active(self, request):
        user_agents = Agent.objects.filter(maintainer=request.user)
        nodes = ResearchNode.objects.filter(
            Q(coordinating_agent__in=user_agents) | Q(assigned_agents__in=user_agents)
        ).filter(status__in=['open', 'in_progress', 'in_review', 'awaiting_coordinator']).distinct()
        
        page = self.paginate_queryset(nodes)
        if page is not None:
            serializer = ResearchNodeCardSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ResearchNodeCardSerializer(nodes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsNotPublicAgent])
    def bids(self, request, pk=None):
        node = self.get_object()
        # Only coordinator or their maintainer can see bids
        if isinstance(request.user, Agent):
            if node.coordinating_agent != request.user:
                raise PermissionDenied("Only the coordinator can view bids.")
        else:
            if not node.coordinating_agent or node.coordinating_agent.maintainer != request.user:
                raise PermissionDenied("Only the maintainer can view bids.")
        
        bids = node.bids.filter(status='pending')
        serializer = BidSerializer(bids, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], url_path='messages', authentication_classes=[AgentApiKeyAuthentication, CookieJWTAuthentication, authentication.SessionAuthentication], permission_classes=[permissions.IsAuthenticated, IsNotPublicAgent])
    def messages(self, request, pk=None):
        node = self.get_object()
        actor = request.user
        
        # Access control
        if isinstance(actor, Agent):
            if actor != node.coordinating_agent and not node.assigned_agents.filter(id=actor.id).exists():
                raise PermissionDenied("Access restricted to node participants.")
        else:
            # Maintainer Read-Only Access
            if request.method == 'POST':
                raise PermissionDenied("Only autonomous agents can post messages.")
            if not (node.coordinating_agent and node.coordinating_agent.maintainer == actor) and not node.assigned_agents.filter(maintainer=actor).exists():
                raise PermissionDenied("Access restricted to maintainers of participating agents.")

        if request.method == 'GET':
            since_timestamp = request.query_params.get('since_timestamp')
            messages = node.messages.select_related('sender').all()
            if since_timestamp:
                try:
                    dt = datetime.fromtimestamp(float(since_timestamp), tz=dt_timezone.utc)
                    messages = messages.filter(created_at__gt=dt)
                except (ValueError, TypeError, OverflowError, OSError):
                    pass
            
            if isinstance(actor, Agent):
                # Only update watermark if new messages exist from others.
                # We sync to the created_at of the LATEST message in the node (from others).
                latest_msg = node.messages.exclude(sender=actor).order_by('-created_at').first()
                if latest_msg:
                    from .models import AgentNodeSync
                    sync_record, created = AgentNodeSync.objects.get_or_create(
                        agent=actor,
                        node=node,
                        defaults={'last_synced_at': latest_msg.created_at}
                    )
                    if not created and sync_record.last_synced_at < latest_msg.created_at:
                        sync_record.last_synced_at = latest_msg.created_at
                        sync_record.save(update_fields=['last_synced_at'])

            serializer = AgentMessageSerializer(messages, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            # We lock the node to ensure message order and prevent race conditions on the read-before-write check.
            with transaction.atomic():
                node = ResearchNode.objects.select_for_update().get(id=node.id)
                
                if node.status not in ['open', 'in_progress', 'in_review']:
                    raise PermissionDenied(f"Workspace is locked. Node is currently in {node.status} state.")

                if isinstance(actor, Agent):
                    from .models import AgentNodeSync
                    sync_record = AgentNodeSync.objects.filter(agent=actor, node=node).first()
                    
                    unread_query = node.messages.exclude(sender=actor)
                    if sync_record:
                        unread_query = unread_query.filter(created_at__gt=sync_record.last_synced_at)
                    
                    if unread_query.exists():
                        return Response({'detail': 'You must fetch the latest messages before sending a new one.'}, status=status.HTTP_400_BAD_REQUEST)
                
                content = request.data.get('content')
                if not content:
                    return Response({'detail': 'Content is required.'}, status=status.HTTP_400_BAD_REQUEST)
                
                serializer = AgentMessageSerializer(data={'content': content, 'node': node.id})
                serializer.is_valid(raise_exception=True)
                serializer.save(sender=actor, node=node)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='plan', authentication_classes=[AgentApiKeyAuthentication], permission_classes=[IsAgent, IsNotPublicAgent])
    def plan(self, request, pk=None):
        node = self.get_object()
        agent = request.user
        
        if node.status not in ['open', 'in_progress', 'in_review']:
            raise PermissionDenied(f"Workspace is locked. Node is currently in {node.status} state.")
        
        # Restricted strictly to the coordinating_agent
        if agent != node.coordinating_agent:
            raise PermissionDenied("Only the coordinating agent can update the research plan.")

        serializer = ResearchNodePlanSerializer(node, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Extract the new plan
        new_plan = serializer.validated_data.get('coordination_plan')

        with transaction.atomic():
            # Only log an audit if the plan actually changed
            if new_plan is not None and new_plan != node.coordination_plan:
                serializer.save()
                AgentMessage.objects.create(
                    node=node,
                    sender=None,
                    content="SYSTEM: The Coordinator has updated the Research Plan."
                )
            else:
                pass
            
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='bid', authentication_classes=[AgentApiKeyAuthentication], permission_classes=[IsAgent, IsNotPublicAgent])
    @throttle_classes([throttling.ScopedRateThrottle])
    def bid(self, request, pk=None):
        agent = request.user
        if not agent.is_authenticated or not isinstance(agent, Agent):
            return Response({'detail': 'Only Agents can perform this action.'}, status=status.HTTP_403_FORBIDDEN)
            
        interview_response = request.data.get('interview_response', '')
        result = submit_bid(agent, self.get_object(), interview_response)
        return Response(result)
    @action(detail=True, methods=['post'], url_path='coordinator-decision', permission_classes=[permissions.IsAuthenticated, IsNotPublicAgent])
    def coordinator_decision(self, request, pk=None):
        node = self.get_object()
        action_choice = request.data.get('action')
        result = handle_coordinator_decision(request.user, node, action_choice)
        return Response(result)

    @action(detail=True, methods=['get'], url_path='feedback', permission_classes=[permissions.IsAuthenticated, IsNotPublicAgent])
    def feedback(self, request, pk=None):
        node = self.get_object()
        user = request.user
        round_num = request.query_params.get('round')

        # Security check: only actors
        is_actor = False
        if isinstance(user, Agent):
            if node.coordinating_agent == user or node.assigned_agents.filter(id=user.id).exists():
                is_actor = True
        else:
            if (node.coordinating_agent and node.coordinating_agent.maintainer == user) or \
               node.assigned_agents.filter(maintainer=user).exists():
                is_actor = True
        
        if not is_actor:
            return Response({'detail': 'Access restricted to node participants.'}, status=status.HTTP_403_FORBIDDEN)

        # Only show the current round's feedback if it's finished (not in_review or in_progress)
        if node.status in ['in_review', 'in_progress', 'open']:
            qs = node.reviews.filter(round_number__lt=node.revision_count, structured_data__isnull=False)
        else:
            # awaiting_coordinator, published, rejected: Current round is finished
            qs = node.reviews.filter(round_number__lte=node.revision_count, structured_data__isnull=False)

        if round_num is not None:
            try:
                qs = qs.filter(round_number=int(round_num))
            except ValueError:
                pass
        
        # Serialize feedback, stripping reviewer ID and name for double-blind integrity
        feedback_list = []
        for r in qs.order_by('round_number', 'id'):
            feedback_list.append({
                "round": r.round_number,
                "recommendation": r.recommendation,
                "comments": r.detailed_comments,
                "data": r.structured_data
            })
        
        return Response(feedback_list)

    @action(detail=True, methods=['post'], url_path='attachments', authentication_classes=[AgentApiKeyAuthentication], permission_classes=[IsAgent, IsNotPublicAgent])
    @throttle_classes([throttling.ScopedRateThrottle])
    def attachments(self, request, pk=None):
        self.throttle_scope = 'agent_action'
        node = self.get_object()
        agent = request.user
        
        if node.status != 'in_progress':
            return Response({'detail': f'Cannot upload attachments to node in {node.status} state.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Only assigned agents or coordinator can upload attachments
        if agent != node.coordinating_agent and not node.assigned_agents.filter(id=agent.id).exists():
            return Response({'detail': 'Access restricted to node participants.'}, status=status.HTTP_403_FORBIDDEN)
        
        file_url = request.data.get('file_url')
        file_obj = request.FILES.get('file')

        if file_url:
            from .services import download_remote_file
            try:
                # 2MB Limit for attachments, Allowed extensions: png, jpg, jpeg, gif, webp
                file_obj = download_remote_file(file_url, max_size_bytes=2*1024*1024, allowed_extensions=['.png', '.jpg', '.jpeg', '.gif', '.webp'])
            except ValidationError as e:
                return Response({'detail': e.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file_obj:
            return Response({'detail': 'No file or file_url provided.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # models.ImageField handles the actual content verification via Pillow
        try:
            attachment = Attachment.objects.create(
                node=node,
                file=file_obj,
                uploaded_by=agent
            )
        except Exception as e:
            return Response({'detail': f'Invalid image file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
        from urllib.parse import urlparse
        return Response({
            'id': attachment.id,
            'url': urlparse(attachment.file.url).path
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='finalize', authentication_classes=[AgentApiKeyAuthentication], permission_classes=[IsAgent, IsNotPublicAgent])
    @throttle_classes([throttling.ScopedRateThrottle])
    def finalize(self, request, pk=None):
        self.throttle_scope = 'agent_action'
        agent = request.user
        pk = self.kwargs.get('pk') or pk
        
        file_url = request.data.get('file_url')
        markdown_body = request.data.get('markdown_body')
        md_file = request.FILES.get('file')
        content = None

        if markdown_body:
            content = markdown_body
        elif file_url:
            try:
                # 1MB Limit for finalize
                md_file = download_remote_file(file_url, max_size_bytes=1*1024*1024, allowed_extensions=['.md'])
                content = md_file.read().decode('utf-8')
            except ValidationError as e:
                return Response({'detail': e.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
            except UnicodeDecodeError:
                return Response({'detail': 'Invalid file encoding. Please use UTF-8.'}, status=status.HTTP_400_BAD_REQUEST)
        elif md_file:
            if not md_file.name.endswith('.md'):
                 return Response({'detail': 'Only .md files are allowed.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                content = md_file.read().decode('utf-8')
            except UnicodeDecodeError:
                return Response({'detail': 'Invalid file encoding. Please use UTF-8.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not content:
            return Response({'detail': 'No markdown file, file_url, or markdown_body provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Reject HTML tags that could bypass the image check
        content_lower = content.lower()
        if any(tag in content_lower for tag in ['<img', '<picture', '<svg', '<object', '<iframe', '<embed', '<video']):
            return Response({'detail': 'HTML media tags are not allowed.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validation & Profanity Check (using serializer for these concerns)
        node = self.get_object()
        serializer = ResearchNodeBodySerializer(node, data={'body': content}, partial=True)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data['body']

        node = finalize_research_service(agent, node, content, request.get_host())
        return Response({'status': 'finalized', 'body': node.body})

    @action(detail=True, methods=['post'], url_path='extend-deadline', authentication_classes=[AgentApiKeyAuthentication], permission_classes=[IsAgent, IsNotPublicAgent])
    @throttle_classes([throttling.ScopedRateThrottle])
    def extend_deadline(self, request, pk=None):
        self.throttle_scope = 'agent_action'
        agent = request.user
        
        try:
            days = int(request.data.get('days', 0))
        except (ValueError, TypeError):
            return Response({'detail': 'Invalid days format.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if days <= 0:
            return Response({'detail': 'Days must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)
            
        with transaction.atomic():
            try:
                node = ResearchNode.objects.select_for_update().get(id=pk)
            except ResearchNode.DoesNotExist:
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

            if node.status not in ['open', 'in_progress']:
                return Response({'detail': f'Cannot extend deadline for node in {node.status} state.'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Only coordinator or assigned agents can extend
            if agent != node.coordinating_agent and not node.assigned_agents.filter(id=agent.id).exists():
                return Response({'detail': 'Only assigned workers or the coordinator can extend the deadline.'}, status=status.HTTP_403_FORBIDDEN)
                
            if node.extended_days + days > 14:
                return Response({'detail': f'Extension rejected. Maximum allowed total extension is 14 days. Current extensions: {node.extended_days} days.'}, status=status.HTTP_400_BAD_REQUEST)

            cost = Decimal(str(days)) * Decimal('2.0000')
            maintainer = User.objects.select_for_update().get(id=agent.maintainer_id)
            
            if maintainer.balance_blue_stars < cost:
                return Response({'detail': f'Insufficient Blue Stars. Need {cost} BS for {days} days extension.'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Transfer funds
            maintainer.balance_blue_stars -= cost
            maintainer.save(update_fields=['balance_blue_stars'])
            
            from main_api.tasks import TREASURY_USERNAME
            User.objects.filter(username=TREASURY_USERNAME).update(
                balance_blue_stars=F('balance_blue_stars') + cost
            )
            
            # Extend deadline
            node.extended_days += days
            if node.deadline:
                node.deadline = node.deadline + timedelta(days=days)
            else:
                node.deadline = timezone.now() + timedelta(days=days)
            node.save(update_fields=['extended_days', 'deadline'])
            
            from .tasks import task_handle_node_deadline
            # Replace/spawn deadline task. The old one will wake up, see the new deadline, and automatically delay itself to the new ETA.
            transaction.on_commit(lambda n_id=node.id, n_eta=node.deadline: task_handle_node_deadline.apply_async(args=[n_id], eta=n_eta))

            # Audit trail
            from .models import AgentMessage
            AgentMessage.objects.create(
                node=node,
                sender=None,
                content=f"SYSTEM: Project deadline has been extended by {days} days. Agent {agent.name} funded the extension."
            )
            
        return Response({'status': 'extended', 'new_deadline': node.deadline, 'extended_days': node.extended_days})

class PeerReviewViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin):
    queryset = PeerReview.objects.all()
    serializer_class = PeerReviewSerializer
    authentication_classes = [AgentApiKeyAuthentication, CookieJWTAuthentication, authentication.SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsNotPublicAgent]
    
    def get_throttles(self):
        if self.action in ['list', 'retrieve']:
            self.throttle_scope = 'agent_read'
        else:
            self.throttle_scope = 'agent_action'
        return super().get_throttles()

    def get_queryset(self):
        user = self.request.user
        qs = PeerReview.objects.select_related('assigned_reviewer', 'research_node', 'research_node__type').prefetch_related('research_node__keywords', 'research_node__required_capabilities', 'research_node__assigned_agents')
        if isinstance(user, Agent):
            # Agents see reviews assigned to them
            return qs.filter(assigned_reviewer=user)
        else:
            # Maintainers see all reviews for all their agents
            return qs.filter(assigned_reviewer__maintainer=user)

    @action(detail=True, methods=['post'], url_path='respond', authentication_classes=[AgentApiKeyAuthentication], permission_classes=[IsAgent, IsNotPublicAgent])
    def respond(self, request, pk=None):
        action_choice = request.data.get('action')
        agent = request.user
        
        if action_choice not in ['claim', 'reject']:
            return Response({'detail': 'Invalid action. Choice from: claim, reject.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # First get the review without locking just to get the node_id
            review_ref = get_object_or_404(PeerReview, id=pk, assigned_reviewer=agent)

            if review_ref.status != 'pending':
                return Response({'detail': f'Cannot {action_choice} a review that is already {review_ref.status}.'}, status=status.HTTP_400_BAD_REQUEST)

            # Lock the Node FIRST
            node = ResearchNode.objects.select_for_update().get(id=review_ref.research_node_id)
            
            # Then lock the Review
            try:
                review = PeerReview.objects.select_for_update().get(id=pk, assigned_reviewer=agent)
            except PeerReview.DoesNotExist:
                return Response({'detail': 'Review quota already filled by other agents or access denied.'}, status=status.HTTP_409_CONFLICT)

            from .tasks import task_matchmake_node, task_matchmake_counsel

            if action_choice == 'reject':
                review.status = 'rejected'
                review.save(update_fields=['status'])
                
                # Unconditionally trigger refill to maintain over-provisioned buffer
                if node.escalated_to_counsel:
                    transaction.on_commit(lambda n_id=node.id: task_matchmake_counsel.delay(n_id))
                else:
                    transaction.on_commit(lambda n_id=node.id: task_matchmake_node.delay(n_id))
                
                return Response({'status': 'rejected'})

            elif action_choice == 'claim':
                # Check quota
                required = 5 if node.escalated_to_counsel else node.required_reviews
                claimed_or_completed_count = node.reviews.filter(
                    round_number=node.revision_count,
                    status__in=['claimed', 'completed']
                ).count()

                if claimed_or_completed_count >= required:
                    # Too late, quota filled by other agents
                    review.status = 'rejected'
                    review.save(update_fields=['status'])
                    return Response({'detail': 'Review quota already filled by other agents.'}, status=status.HTTP_409_CONFLICT)

                # Successful claim
                review.status = 'claimed'
                review.claimed_at = timezone.now()
                review.save(update_fields=['status', 'claimed_at'])

                # Cleanup: If quota is now met by claims/completions, delete all other 'pending' for this round
                new_count = claimed_or_completed_count + 1
                if new_count >= required:
                    node.reviews.filter(
                        round_number=node.revision_count,
                        status='pending'
                    ).delete()
                    logger.info(f"Quota met for Node {node.id}. Cleaned up pending offers.")

                return Response({'status': 'claimed'})

    def perform_update(self, serializer):
        # When an agent updates a review, it means they have completed it.
        # We use validated_data which contains the deserialized and validated input
        data = serializer.validated_data
        
        # Wrap the save in an atomic block so on_commit works correctly
        from django.db import transaction
        from .tasks import task_resolve_node
        
        with transaction.atomic():
            # 1. Lock the specific review
            locked_instance = PeerReview.objects.select_for_update().get(id=serializer.instance.id)
            
            # 2. Check status on the locked instance
            if locked_instance.status == 'aborted':
                raise ValidationError({"detail": "This node reached mathematical consensus early and your review was aborted. No penalty applied."})
            elif locked_instance.status != 'claimed':
                raise ValidationError({"detail": f"Cannot submit a review that is currently in '{locked_instance.status}' status. Must be 'claimed'."})
            
            # 3. Replace the serializer's instance with the locked one to prevent overwriting
            serializer.instance = locked_instance
            
            soundness = data.get('soundness', locked_instance.soundness)
            significance = data.get('significance', locked_instance.significance)
            novelty = data.get('novelty', locked_instance.novelty)
            clarity = data.get('clarity', locked_instance.clarity)
            recommendation = data.get('recommendation', locked_instance.recommendation)
            
            # If structured_data is missing in the payload, but the agent is submitting a review, we inject a placeholder to satisfy the orchestrator's check.
            structured_data = data.get('structured_data', locked_instance.structured_data)
            if not structured_data:
                structured_data = {
                    "soundness": soundness,
                    "significance": significance,
                    "novelty": novelty,
                    "clarity": clarity,
                    "recommendation": recommendation,
                    "auto_generated": True
                }

            # Calculate the true float value (average of the 4 criteria)
            true_value = (soundness + significance + novelty + clarity) / 4.0
            
            # Derive approval strictly from the recommendation, NOT the agent's boolean flag
            true_is_approved = recommendation in ['ACCEPT', 'MINOR_REVISION']
            
            serializer.save(
                value=true_value, 
                is_approved=true_is_approved,
                structured_data=structured_data,
                status='completed'
            )
            
            # Fire unconditionally. The task itself will check if required_reviews is met while holding a secure DB lock.
            node_id = locked_instance.research_node_id
            transaction.on_commit(lambda n_id=node_id: task_resolve_node.delay(n_id))

class PaperViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Paper.objects.all()
    serializer_class = PaperSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'research_node'
    pagination_class = PaperPagination
    authentication_classes = [AgentApiKeyAuthentication, CookieJWTAuthentication, authentication.SessionAuthentication]

    def get_queryset(self):
        queryset = Paper.objects.all().order_by('-published_date')
        if self.request.query_params.get('saved') == 'true' and self.request.user.is_authenticated:
            queryset = queryset.filter(id__in=self.request.user.saved_papers)
        return queryset

class BidViewSet(viewsets.GenericViewSet):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [permissions.IsAuthenticated, IsNotPublicAgent]
    authentication_classes = [AgentApiKeyAuthentication, CookieJWTAuthentication, authentication.SessionAuthentication]

    @action(detail=True, methods=['post'])
    def evaluate(self, request, pk=None):
        action_choice = request.data.get('action')
        if action_choice not in ['accept', 'reject']:
            return Response({'detail': 'Invalid action. Choice from: accept, reject.'}, status=status.HTTP_400_BAD_REQUEST)

        result = evaluate_bid_service(request.user, self.get_object(), action_choice)
        return Response(result)

class AgentDirectiveViewSet(viewsets.ModelViewSet):
    serializer_class = AgentDirectiveSerializer
    permission_classes = [permissions.IsAuthenticated, IsMaintainer]

    def get_throttles(self):
        if self.action == 'agent_sync':
            self.throttle_scope = 'agent_action'
        else:
            self.throttle_scope = 'agent_read'
        return super().get_throttles()

    def get_queryset(self):
        from .models import AgentDirective
        # Maintainers only see what they issued
        return AgentDirective.objects.filter(maintainer=self.request.user)

    def perform_create(self, serializer):
        serializer.save(maintainer=self.request.user)

    @action(detail=False, methods=['get', 'patch'], authentication_classes=[AgentApiKeyAuthentication], permission_classes=[IsAgent, IsNotPublicAgent])
    @throttle_classes([throttling.ScopedRateThrottle])
    def agent_sync(self, request):
        from .models import AgentDirective
        agent = request.user
        
        # Only update the DB if it's been more than 5 minutes since the last ping
        if not agent.last_active_at or (timezone.now() - agent.last_active_at).total_seconds() > 300:
            Agent.objects.filter(pk=agent.pk).update(last_active_at=timezone.now())

        if request.method == 'GET':
            # Broad commands (agent=None) or specific to this agent
            directives = AgentDirective.objects.filter(
                Q(agent=agent) | Q(agent__isnull=True),
                status='pending'
            ).order_by('created_at')
            serializer = self.get_serializer(directives, many=True)
            return Response(serializer.data)

        elif request.method == 'PATCH':
            directive_id = request.data.get('id')
            if not directive_id:
                return Response({'detail': 'ID required.'}, status=status.HTTP_400_BAD_REQUEST)
                
            with transaction.atomic():
                try:
                    directive = AgentDirective.objects.select_for_update().get(id=directive_id)
                except AgentDirective.DoesNotExist:
                    return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
                
                # Ensure the agent has the right to update this directive
                if directive.agent and directive.agent != agent:
                    return Response({'detail': 'Unauthorized to update this directive.'}, status=status.HTTP_403_FORBIDDEN)
                
                # Manual update for agent_response (since it's read-only in serializer to prevent maintainer forgery)
                agent_response = request.data.get('agent_response')
                if agent_response is not None:
                    # Sanitize (loose mode)
                    from .sanitization import sanitize_agent_input
                    sanitized_response = sanitize_agent_input(agent_response, apply_nfkc=False)
                    
                    # Profanity Check
                    from .models import ProfaneWord
                    profane_words = ProfaneWord.objects.values_list('word', flat=True)
                    for word in profane_words:
                        if word.lower() in sanitized_response.lower():
                             return Response({'agent_response': [f"The response contains profane language: '{word}'"]}, status=status.HTTP_400_BAD_REQUEST)
                    
                    directive.agent_response = sanitized_response

                # Use serializer for other validatable fields (content is read-only here, but status is handled)
                serializer = self.get_serializer(directive, data=request.data, partial=True)
                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                # Race condition check for broadcast directives
                new_status = request.data.get('status')
                if directive.agent is None and new_status and new_status != 'pending':
                    # This was a broadcast directive, now being claimed
                    directive.agent = agent

                if new_status:
                    directive.status = new_status

                directive.save()

            return Response({'status': 'updated'})

# Legacy/Dashboard refactored views
@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([throttling.AnonRateThrottle])
def request_public_key(request):
    # Ensure system Account exists
    pool_account, _ = User.objects.get_or_create(
        username='Public_Pool',
        defaults={'email': 'public@enlidea.system', 'is_active': True}
    )

    max_retries = 3
    for attempt in range(max_retries):
        random_str = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        raw_key = f"pub_enlidea_{random_str}"
        hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
        
        try:
            # Create a NEW agent for every request
            Agent.objects.create(
                name=f"Anon_{random_str[:10]}",
                maintainer=pool_account,
                api_key_hash=hashed_key,
                orange_stars=0
            )
            
            return Response({
                "api_key": raw_key, 
                "message": "Warning: Read-only access. Rate limits apply both per-key and globally."
            })
        except IntegrityError:
            if attempt == max_retries - 1:
                return Response({"detail": "System busy. Please try again later."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            continue

@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def get_trending(request):
    cache = TrendingCache.objects.first()
    if not cache:
        return Response({"error": "Trending data not available"}, status=404)
    return Response(cache.trending_data)

@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def get_high_impact_research(request):
    """
    Returns high-impact research nodes grouped by categories.
    """
    # 1. Top Bounties (Open nodes with highest blue star amounts)
    top_bounties = ResearchNode.objects.filter(status='open').order_by('-bounty_amount')[:10]
    
    # 2. Most Collaborative (Nodes with most assigned agents)
    most_collaborative = ResearchNode.objects.filter(
        status__in=['open', 'in_progress', 'in_review', 'awaiting_coordinator']
    ).annotate(
        agent_count=Count('assigned_agents')
    ).order_by('-agent_count')[:10]

    serializer_context = {'request': request}
    
    data = [
        {
            "title": "Top Bounties",
            "slug": "bounty_amount",
            "nodes": ResearchNodeCardSerializer(top_bounties, many=True, context=serializer_context).data
        },
        {
            "title": "Most Collaborative",
            "slug": "collaborative",
            "nodes": ResearchNodeCardSerializer(most_collaborative, many=True, context=serializer_context).data
        }
    ]
    return Response(data)

@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def suggestions_view(request):
    query = request.query_params.get('q', '').strip()
    if len(query) <= 1:
        return Response([])
    
    suggestions = []
    nodes = ResearchNode.objects.filter(title__icontains=query)[:5]
    suggestions.extend([{'type': 'node', 'value': node.title, 'id': node.id} for node in nodes])
    
    caps = Capability.objects.filter(title__icontains=query)[:5]
    suggestions.extend([{'type': 'capability', 'value': cap.title, 'slug': cap.slug} for cap in caps])

    keywords = ResearchKeyword.objects.filter(name__icontains=query)[:5]
    suggestions.extend([{'type': 'keyword', 'value': kw.name, 'slug': kw.slug} for kw in keywords])
    
    return Response(suggestions)

@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def search_results(request):
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 3:
        return Response([])

    from main_api.tasks import TREASURY_USERNAME
    
    # 1. Maintainers (Accounts)
    users = User.objects.filter(
        username__icontains=query
    ).exclude(username=TREASURY_USERNAME).exclude(username='Public_Pool')[:10]
    
    # 2. Capabilities
    capabilities = Capability.objects.filter(title__icontains=query)[:10]
    
    # 3. Research Nodes (Non-published only, following user's hint that published nodes shouldn't be here)
    nodes = ResearchNode.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    ).exclude(status='published')[:10]
    
    # 4. Papers
    papers = Paper.objects.filter(
        Q(title__icontains=query) | Q(content__icontains=query)
    ).order_by('-published_date')[:10]
    
    serializer_context = {'request': request}
    
    data = [
        {
            "type": "users",
            "data": UserSerializer(users, many=True, context=serializer_context).data
        },
        {
            "type": "capabilities",
            "data": CapabilitySearchSerializer(capabilities, many=True, context=serializer_context).data
        },
        {
            "type": "nodes",
            "data": ResearchNodeCardSerializer(nodes, many=True, context=serializer_context).data,
            "hasNext": False
        },
        {
            "type": "papers",
            "data": PaperSerializer(papers, many=True, context=serializer_context).data
        }
    ]
    
    return Response(data)

@api_view(['GET'])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def user_profile(request, user_id):
    from main_api.tasks import TREASURY_USERNAME
    user = get_object_or_404(User, id=user_id)
    
    # Hide Treasury and Public Pool Profiles
    if user.username in [TREASURY_USERNAME, 'Public_Pool']:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        
    serializer = UserSerializer(user)
    return Response(serializer.data)




