from decimal import Decimal
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, inline_serializer
from django.utils.timezone import localtime
from django.utils.text import slugify
from .models import (
    Capability,
    ResearchNode,
    Comment,
    SubComment,
    ProfaneWord,
    PeerReview,
    ResearchKeyword,
    Paper,
    AgentDirective,
    NodeType,
    Bid,
    Attachment,
    AgentMessage,
)
from django.contrib.auth import get_user_model
from accounts.models import Agent
from .sanitization import sanitize_agent_input, sanitize_json_payload

User = get_user_model()


class AgentMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.ReadOnlyField(source="sender.name")
    sender_id = serializers.ReadOnlyField(source="sender.id")

    class Meta:
        model = AgentMessage
        fields = ["id", "node", "sender", "sender_name", "sender_id", "content", "created_at"]
        read_only_fields = ["id", "node", "sender", "created_at"]

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")

        # Apply sanitization (loose for message body)
        value = sanitize_agent_input(value, apply_nfkc=False)
        if len(value) > 4000:
            raise serializers.ValidationError("Message content must be under 4000 characters.")
        from .models import ProfaneWord

        profane_words = ProfaneWord.objects.values_list("word", flat=True)
        for word in profane_words:
            if word.lower() in value.lower():
                raise serializers.ValidationError(f"The text contains profane language: '{word}'")
        return value


class UserSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "avatar"]


class UserSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField(source="average_trust_score", read_only=True)
    average_soundness = serializers.FloatField(read_only=True)
    average_novelty = serializers.FloatField(read_only=True)
    average_significance = serializers.FloatField(read_only=True)
    average_clarity = serializers.FloatField(read_only=True)
    total_ratings = serializers.IntegerField(source="total_peer_reviews", read_only=True)
    total_fulfillments = serializers.IntegerField(read_only=True)
    total_research_nodes = serializers.IntegerField(read_only=True)
    total_saves = serializers.IntegerField(source="total_node_saves", read_only=True)
    total_visits = serializers.IntegerField(source="total_node_visits", read_only=True)
    total_appreciation_score = serializers.FloatField(read_only=True)
    rank = serializers.IntegerField(read_only=True)
    score = serializers.IntegerField(read_only=True)
    follower_count = serializers.IntegerField(read_only=True)
    joined_date = serializers.SerializerMethodField()
    active_agents = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "rank",
            "score",
            "avatar",
            "average_rating",
            "average_soundness",
            "average_novelty",
            "average_significance",
            "average_clarity",
            "total_ratings",
            "total_fulfillments",
            "total_research_nodes",
            "total_saves",
            "follower_count",
            "total_visits",
            "biography",
            "joined_date",
            "total_appreciation_score",
            "saved_papers",
            "active_agents",
        ]

    @extend_schema_field(serializers.CharField())
    def get_joined_date(self, obj):
        return localtime(obj.date_joined).strftime("%B %Y")

    @extend_schema_field(
        serializers.ListField(
            child=inline_serializer(
                name="ActiveAgent",
                fields={
                    "id": serializers.IntegerField(),
                    "name": serializers.CharField(),
                    "orange_stars": serializers.DecimalField(max_digits=12, decimal_places=4),
                },
            )
        )
    )
    def get_active_agents(self, obj):
        agents = obj.agents.filter(is_active=True).order_by("-created_at")
        return [{"id": a.id, "name": a.name, "orange_stars": a.orange_stars} for a in agents]


class CapabilitySerializer(serializers.ModelSerializer):
    parent_capabilities = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    child_capabilities = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    has_children = serializers.SerializerMethodField()

    class Meta:
        model = Capability
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "icon",
            "parent_capabilities",
            "child_capabilities",
            "has_children",
        ]

    @extend_schema_field(serializers.BooleanField())
    def get_has_children(self, obj):
        return obj.child_capabilities.exists()


class CapabilitySearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Capability
        fields = ["id", "title", "slug"]


class NodeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeType
        fields = ["name"]


class AgentListSerializer(serializers.ListSerializer):
    def to_representation(self, instance):
        from django.core.cache import cache

        # Force evaluation into a list once
        iterable = list(instance.all() if hasattr(instance, "all") else instance)

        # Bulk fetch cache for the evaluated list
        agent_ids = [agent.id for agent in iterable]
        cache_keys = [f"agent_active_{aid}" for aid in agent_ids]
        cache_values = cache.get_many(cache_keys)
        self.context["agent_active_cache"] = cache_values

        # Pass the evaluated list to parent
        return super().to_representation(iterable)


class AgentSerializer(serializers.ModelSerializer):
    maintainer = serializers.ReadOnlyField(source="maintainer.username")
    maintainer_id = serializers.ReadOnlyField(source="maintainer.id")
    capabilities = serializers.SlugRelatedField(many=True, slug_field="slug", queryset=Capability.objects.all())
    capabilities_detail = CapabilitySerializer(source="capabilities", many=True, read_only=True)
    is_online = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        list_serializer_class = AgentListSerializer
        fields = [
            "id",
            "name",
            "maintainer",
            "maintainer_id",
            "orange_stars",
            "is_active",
            "is_online",
            "capabilities",
            "capabilities_detail",
            "created_at",
        ]
        read_only_fields = ["is_online", "orange_stars", "is_active"]

    def validate_name(self, value):
        # Strict sanitization for agent names to prevent spoofing/UI breakage
        value = sanitize_agent_input(value, apply_nfkc=True)
        if len(value) > 100:
            raise serializers.ValidationError("Agent name must be under 100 characters.")
        if not value.strip():
            raise serializers.ValidationError("Agent name cannot be empty.")

        # Profanity check for agent names with cache & regex word boundaries
        import re
        from django.core.cache import cache
        from .models import ProfaneWord

        profane_words = cache.get("profane_words")
        if profane_words is None:
            profane_words = list(ProfaneWord.objects.values_list("word", flat=True))
            cache.set("profane_words", profane_words, 3600)

        value_lower = value.lower()
        for word in profane_words:
            if re.search(r"\b" + re.escape(word.lower()) + r"\b", value_lower):
                raise serializers.ValidationError(f"The name contains profane language: '{word}'")
        return value

    @extend_schema_field(serializers.BooleanField())
    def get_is_online(self, obj):
        from django.core.cache import cache

        if "agent_active_cache" in self.context:
            return bool(self.context["agent_active_cache"].get(f"agent_active_{obj.id}"))
        return bool(cache.get(f"agent_active_{obj.id}"))


class ResearchKeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchKeyword
        fields = ["id", "name", "slug"]


class ResearchNodeSerializer(serializers.ModelSerializer):
    coordinating_agent = AgentSerializer(read_only=True)
    required_capabilities = CapabilitySerializer(many=True, read_only=True)
    keywords = ResearchKeywordSerializer(many=True, read_only=True)
    saves = serializers.IntegerField(read_only=True)
    average_rating = serializers.SerializerMethodField()
    average_soundness = serializers.FloatField(read_only=True)
    average_novelty = serializers.FloatField(read_only=True)
    average_significance = serializers.FloatField(read_only=True)
    average_clarity = serializers.FloatField(read_only=True)
    total_ratings = serializers.SerializerMethodField()
    total_assigned = serializers.SerializerMethodField()

    class Meta:
        model = ResearchNode
        fields = [
            "id",
            "title",
            "description",
            "body",
            "required_capabilities",
            "keywords",
            "type",
            "status",
            "bounty_amount",
            "required_reviews",
            "required_collaborators",
            "min_trust_required",
            "research_duration_days",
            "deadline",
            "coordinating_agent",
            "updated",
            "visits",
            "saves",
            "average_rating",
            "average_soundness",
            "average_novelty",
            "average_significance",
            "average_clarity",
            "total_ratings",
            "total_assigned",
            "orchestrator_verdict",
            "verdict_strength",
            "revision_count",
            "escalated_to_counsel",
            "decision_deadline",
            "interview_prompt",
            "coordination_plan",
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Only show body if published, or if the requester is the coordinator, assigned agent, or assigned reviewer.
        request = self.context.get("request")
        user = getattr(request, "user", None)

        show_body = False
        if instance.status == "published" or instance.status == "open":
            # Always show body for 'open' nodes so agents can bid, and for 'published' for the public
            show_body = True
        elif user:
            from accounts.models import Agent

            if isinstance(user, Agent):
                if (
                    instance.coordinating_agent == user
                    or instance.assigned_agents.filter(id=user.id).exists()
                    or instance.reviews.filter(assigned_reviewer=user).exists()
                ):
                    show_body = True
            elif user.is_authenticated:
                if (
                    (instance.coordinating_agent and instance.coordinating_agent.maintainer == user)
                    or instance.assigned_agents.filter(maintainer=user).exists()
                    or instance.reviews.filter(assigned_reviewer__maintainer=user).exists()
                ):
                    show_body = True

        if not show_body:
            representation["body"] = "Content restricted to assigned actors until publication."
            representation["coordination_plan"] = "Content restricted to assigned actors until publication."

        return representation

    @extend_schema_field(serializers.FloatField())
    def get_average_rating(self, obj):
        return getattr(obj, "calculated_average_rating", obj.average_rating)

    @extend_schema_field(serializers.IntegerField())
    def get_total_ratings(self, obj):
        return getattr(obj, "calculated_total_ratings", obj.reviews.count())

    @extend_schema_field(serializers.IntegerField())
    def get_total_assigned(self, obj):
        return getattr(obj, "calculated_total_assigned", obj.total_assigned)


class ResearchNodeCardSerializer(serializers.ModelSerializer):
    coordinating_agent = serializers.SerializerMethodField()
    required_capabilities = serializers.SerializerMethodField()
    keywords = ResearchKeywordSerializer(many=True, read_only=True)
    saves = serializers.IntegerField(read_only=True)
    average_rating = serializers.SerializerMethodField()
    total_ratings = serializers.SerializerMethodField()
    total_assigned = serializers.SerializerMethodField()

    class Meta:
        model = ResearchNode
        fields = [
            "id",
            "title",
            "description",
            "required_capabilities",
            "keywords",
            "type",
            "status",
            "bounty_amount",
            "min_trust_required",
            "required_collaborators",
            "deadline",
            "coordinating_agent",
            "saves",
            "average_rating",
            "total_ratings",
            "total_assigned",
        ]

    @extend_schema_field(
        inline_serializer(
            name="CardAgent",
            fields={"name": serializers.CharField(), "id": serializers.IntegerField()},
            allow_null=True,
        )
    )
    def get_coordinating_agent(self, obj):
        return (
            {"name": obj.coordinating_agent.name, "id": obj.coordinating_agent.id} if obj.coordinating_agent else None
        )

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_required_capabilities(self, obj):
        return [cap.slug for cap in obj.required_capabilities.all()]

    @extend_schema_field(serializers.FloatField())
    def get_average_rating(self, obj):
        return getattr(obj, "calculated_average_rating", obj.average_rating)

    @extend_schema_field(serializers.IntegerField())
    def get_total_ratings(self, obj):
        return getattr(obj, "calculated_total_ratings", obj.reviews.count())

    @extend_schema_field(serializers.IntegerField())
    def get_total_assigned(self, obj):
        return getattr(obj, "calculated_total_assigned", obj.total_assigned)


class PaperSerializer(serializers.ModelSerializer):
    authors = AgentSerializer(many=True, read_only=True)
    research_node_title = serializers.CharField(source="research_node.title", read_only=True)
    user_vote = serializers.SerializerMethodField()

    class Meta:
        model = Paper
        fields = [
            "id",
            "research_node",
            "research_node_title",
            "title",
            "abstract",
            "content",
            "published_date",
            "authors",
            "appreciation_score",
            "user_vote",
            "saves",
        ]

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_user_vote(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # Prevent autonomous Agents from triggering this DB query
            if isinstance(request.user, User):
                from social.models import Appreciation

                try:
                    appreciation = Appreciation.objects.get(user=request.user, paper=obj)
                    return appreciation.vote
                except Appreciation.DoesNotExist:
                    return None
        return None


class AgentDirectiveSerializer(serializers.ModelSerializer):
    agent_detail = AgentSerializer(source="agent", read_only=True)
    agent = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.all(), write_only=True, required=False, allow_null=True
    )
    maintainer_username = serializers.ReadOnlyField(source="maintainer.username")

    class Meta:
        model = AgentDirective
        fields = [
            "id",
            "maintainer",
            "maintainer_username",
            "agent",
            "agent_detail",
            "content",
            "agent_response",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "maintainer", "agent_response", "status", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            user = request.user
            if hasattr(user, "agents"):
                self.fields["agent"].queryset = user.agents.all()

    def validate_agent(self, value):
        if value is None:
            return value
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            user = request.user
            if hasattr(user, "agents"):
                if value.maintainer_id != user.id:
                    raise serializers.ValidationError("Selected agent does not belong to you.")
            elif hasattr(user, "maintainer_id"):
                if value.maintainer_id != user.maintainer_id:
                    raise serializers.ValidationError("Agent does not belong to the same maintainer.")
        return value

    def validate_content(self, value):
        # Apply strict normalization (NFKC) for directives
        value = sanitize_agent_input(value, apply_nfkc=True)
        if len(value) > 10000:
            raise serializers.ValidationError("Directive content must be under 10000 characters.")
        from .models import ProfaneWord

        profane_words = ProfaneWord.objects.values_list("word", flat=True)
        for word in profane_words:
            if word.lower() in value.lower():
                raise serializers.ValidationError(f"The text contains profane language: '{word}'")
        return value


class CommentSerializer(serializers.ModelSerializer):
    creator = AgentSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "created", "creator", "updated", "body", "research_node"]

    def validate_body(self, value):
        # Apply loose sanitization
        value = sanitize_agent_input(value, apply_nfkc=False)
        from .models import ProfaneWord

        profane_words = ProfaneWord.objects.values_list("word", flat=True)
        for word in profane_words:
            if word.lower() in value.lower():
                raise serializers.ValidationError(f"The text contains profane language: '{word}'")
        return value


class SubCommentSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)

    class Meta:
        model = SubComment
        fields = ["id", "created", "creator", "updated", "body", "comment"]

    def validate_body(self, value):
        # Sub-comments are usually from maintainers (humans), but we sanitize anyway
        value = sanitize_agent_input(value, apply_nfkc=True)
        if len(value) > 5000:
            raise serializers.ValidationError("Sub-comment body must be under 5000 characters.")
        from .models import ProfaneWord

        profane_words = ProfaneWord.objects.values_list("word", flat=True)
        for word in profane_words:
            if word.lower() in value.lower():
                raise serializers.ValidationError(f"The text contains profane language: '{word}'")
        return value


class ProfaneWordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfaneWord
        fields = ["id", "word"]


class PeerReviewSerializer(serializers.ModelSerializer):
    assigned_reviewer_detail = AgentSerializer(source="assigned_reviewer", read_only=True)
    research_node_detail = ResearchNodeSerializer(source="research_node", read_only=True)
    structured_data = serializers.DictField(allow_null=True, required=False)

    class Meta:
        model = PeerReview
        fields = [
            "id",
            "assigned_reviewer",
            "assigned_reviewer_detail",
            "research_node",
            "research_node_detail",
            "value",
            "soundness",
            "significance",
            "novelty",
            "clarity",
            "confidence",
            "detailed_comments",
            "recommendation",
            "is_approved",
            "structured_data",
            "status",
            "claimed_at",
            "round_number",
        ]
        read_only_fields = [
            "id",
            "assigned_reviewer",
            "research_node",
            "created",
            "value",
            "is_approved",
            "claimed_at",
            "round_number",
        ]

    def validate_detailed_comments(self, value):
        # Apply loose sanitization to preserve scientific notation in reviews
        value = sanitize_agent_input(value, apply_nfkc=False)
        if len(value) > 10000:
            raise serializers.ValidationError("Detailed comments must be under 10000 characters.")
        from .models import ProfaneWord

        profane_words = ProfaneWord.objects.values_list("word", flat=True)
        for word in profane_words:
            if word.lower() in value.lower():
                raise serializers.ValidationError(f"The text contains profane language: '{word}'")
        return value

    def validate_structured_data(self, value):
        if value:
            # Apply loose sanitization recursively to the JSON payload
            return sanitize_json_payload(value, apply_nfkc=False)
        return value


class CreateResearchNodeSerializer(serializers.ModelSerializer):
    required_capabilities = serializers.PrimaryKeyRelatedField(queryset=Capability.objects.all(), many=True)
    # Change to ListField accepting strings
    keywords = serializers.ListField(child=serializers.CharField(max_length=100), required=False, write_only=True)

    class Meta:
        model = ResearchNode
        fields = [
            "id",
            "title",
            "description",
            "body",
            "required_capabilities",
            "keywords",
            "type",
            "status",
            "bounty_amount",
            "required_reviews",
            "required_collaborators",
            "min_trust_required",
            "research_duration_days",
            "deadline",
            "interview_prompt",
        ]
        read_only_fields = ["status", "deadline"]

    def validate_profanity(self, text):
        from .models import ProfaneWord

        profane_words = ProfaneWord.objects.values_list("word", flat=True)
        for word in profane_words:
            if word.lower() in text.lower():
                raise serializers.ValidationError(f"The text contains profane language: '{word}'")

    def validate_title(self, value):
        value = sanitize_agent_input(value, apply_nfkc=True)
        if len(value) <= 10:
            raise serializers.ValidationError("Title must be over 10 characters")
        if len(value) > 80:
            raise serializers.ValidationError("Title must be under 80 characters")
        self.validate_profanity(value)
        return value

    def validate_description(self, value):
        value = sanitize_agent_input(value, apply_nfkc=True)
        if len(value) > 5000:
            raise serializers.ValidationError("Description must be under 5000 characters.")
        self.validate_profanity(value)
        return value

    def validate_body(self, value):
        value = sanitize_agent_input(value, apply_nfkc=False)
        if len(value) <= 140:
            raise serializers.ValidationError("Content must be over 140 characters")
        if len(value) > 50000:
            raise serializers.ValidationError("Content must be under 50000 characters")
        self.validate_profanity(value)
        return value

    def validate_interview_prompt(self, value):
        value = sanitize_agent_input(value, apply_nfkc=True)
        if len(value) > 2000:
            raise serializers.ValidationError("Interview prompt must be under 2000 characters.")
        self.validate_profanity(value)
        return value

    def validate_keywords(self, value):
        if value:
            value = [sanitize_agent_input(k, apply_nfkc=True) for k in value]
            for k in value:
                if len(k) > 100:
                    raise serializers.ValidationError("Keyword must be under 100 characters.")
        return value

    def validate(self, attrs):
        required_capabilities = attrs.get("required_capabilities")
        if required_capabilities is not None and len(required_capabilities) == 0:
            raise serializers.ValidationError(
                {"required_capabilities": "At least one required capability must be selected."}
            )

        required_reviews = attrs.get("required_reviews")
        if required_reviews is not None:
            if required_reviews < 3:
                raise serializers.ValidationError({"required_reviews": "Minimum of 3 peer reviews required."})
            if required_reviews > 20:
                raise serializers.ValidationError({"required_reviews": "Maximum of 20 peer reviews allowed."})

        required_collaborators = attrs.get("required_collaborators")
        if required_collaborators is not None:
            if required_collaborators < 1:
                raise serializers.ValidationError({"required_collaborators": "At least 1 collaborator is required."})
            if required_collaborators > 20:
                raise serializers.ValidationError({"required_collaborators": "Maximum of 20 collaborators allowed."})

        research_duration_days = attrs.get("research_duration_days")
        if research_duration_days is not None:
            if research_duration_days < 1:
                raise serializers.ValidationError(
                    {"research_duration_days": "Research duration must be at least 1 day."}
                )
            if research_duration_days > 365:
                raise serializers.ValidationError(
                    {"research_duration_days": "Research duration cannot exceed 365 days."}
                )

        min_trust = attrs.get("min_trust_required")
        if min_trust is not None:
            if min_trust < Decimal("-20.0000") or min_trust > Decimal("1000.0000"):
                raise serializers.ValidationError(
                    {"min_trust_required": "Min trust required must be between -20.0 and 1000.0."}
                )

        bounty = attrs.get("bounty_amount")
        if bounty is not None:
            if bounty < Decimal("0.0000") or bounty > Decimal("1000000.0000"):
                raise serializers.ValidationError(
                    {"bounty_amount": "Bounty amount must be between 0 and 1,000,000 Blue Stars."}
                )

        return attrs

    def create(self, validated_data):
        keywords_data = validated_data.pop("keywords", [])
        capabilities_data = validated_data.pop("required_capabilities", [])

        node = ResearchNode.objects.create(**validated_data)
        node.required_capabilities.set(capabilities_data)

        # Handle dynamic keyword creation
        for kw_name in keywords_data:
            kw_slug = slugify(kw_name)
            if not kw_slug:
                continue

            kw_obj, _ = ResearchKeyword.objects.get_or_create(slug=kw_slug, defaults={"name": kw_name})
            node.keywords.add(kw_obj)

        from django.db import transaction
        from .tasks import task_handle_node_deadline

        if node.deadline:
            transaction.on_commit(
                lambda n_id=node.id, n_eta=node.deadline: task_handle_node_deadline.apply_async(args=(n_id,), eta=n_eta)
            )

        return node


class EditResearchNodeSerializer(serializers.ModelSerializer):
    required_capabilities = serializers.PrimaryKeyRelatedField(queryset=Capability.objects.all(), many=True)
    # Change to ListField accepting strings
    keywords = serializers.ListField(child=serializers.CharField(max_length=100), required=False, write_only=True)

    class Meta:
        model = ResearchNode
        # Added 'body' so that agents can patch technical typos or rephrase hypotheses
        fields = [
            "title",
            "description",
            "body",
            "required_capabilities",
            "keywords",
            "type",
            "required_reviews",
            "required_collaborators",
            "min_trust_required",
            "interview_prompt",
        ]

    def validate_profanity(self, text):
        from .models import ProfaneWord

        profane_words = ProfaneWord.objects.values_list("word", flat=True)
        for word in profane_words:
            if word.lower() in text.lower():
                raise serializers.ValidationError(f"The text contains profane language: '{word}'")

    def validate_title(self, value):
        value = sanitize_agent_input(value, apply_nfkc=True)
        if len(value) <= 10:
            raise serializers.ValidationError("Title must be over 10 characters")
        if len(value) > 80:
            raise serializers.ValidationError("Title must be under 80 characters")
        self.validate_profanity(value)
        return value

    def validate_description(self, value):
        value = sanitize_agent_input(value, apply_nfkc=True)
        if len(value) > 5000:
            raise serializers.ValidationError("Description must be under 5000 characters.")
        self.validate_profanity(value)
        return value

    def validate_body(self, value):
        value = sanitize_agent_input(value, apply_nfkc=False)
        if len(value) <= 140:
            raise serializers.ValidationError("Content must be over 140 characters")
        if len(value) > 50000:
            raise serializers.ValidationError("Content must be under 50000 characters")
        self.validate_profanity(value)
        return value

    def validate_interview_prompt(self, value):
        value = sanitize_agent_input(value, apply_nfkc=True)
        if len(value) > 2000:
            raise serializers.ValidationError("Interview prompt must be under 2000 characters.")
        self.validate_profanity(value)
        return value

    def validate_keywords(self, value):
        if value:
            value = [sanitize_agent_input(k, apply_nfkc=True) for k in value]
            for k in value:
                if len(k) > 100:
                    raise serializers.ValidationError("Keyword must be under 100 characters.")
        return value

    def validate(self, attrs):
        # Capability validation
        if "required_capabilities" in attrs:
            if not attrs["required_capabilities"]:
                raise serializers.ValidationError({"required_capabilities": "At least one capability is required."})

        # Integer enforcement for trust
        min_trust = attrs.get("min_trust_required")
        if min_trust is not None:
            if min_trust % 1 != 0:
                raise serializers.ValidationError(
                    {"min_trust_required": "Minimum trust required must be a whole number."}
                )
            if min_trust < Decimal("-20.0000") or min_trust > Decimal("1000.0000"):
                raise serializers.ValidationError(
                    {"min_trust_required": "Min trust required must be between -20.0 and 1000.0."}
                )

        required_collaborators = attrs.get("required_collaborators")
        if required_collaborators is not None:
            if required_collaborators < 1:
                raise serializers.ValidationError({"required_collaborators": "At least 1 collaborator is required."})
            if required_collaborators > 20:
                raise serializers.ValidationError({"required_collaborators": "Maximum of 20 collaborators allowed."})

        # Reviewer cap validation
        required_reviews = attrs.get("required_reviews")
        if required_reviews:
            if required_reviews < 3:
                raise serializers.ValidationError({"required_reviews": "Minimum of 3 peer reviews required."})
            if required_reviews > 20:
                raise serializers.ValidationError({"required_reviews": "Maximum of 20 peer reviews allowed."})

        return attrs

    def update(self, instance, validated_data):
        keywords_data = validated_data.pop("keywords", None)
        capabilities_data = validated_data.pop("required_capabilities", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if capabilities_data is not None:
            instance.required_capabilities.set(capabilities_data)

        if keywords_data is not None:
            instance.keywords.clear()
            for kw_name in keywords_data:
                kw_slug = slugify(kw_name)
                if not kw_slug:
                    continue

                kw_obj, _ = ResearchKeyword.objects.get_or_create(slug=kw_slug, defaults={"name": kw_name})
                instance.keywords.add(kw_obj)

        return instance


class AgentSyncNodeSerializer(serializers.ModelSerializer):
    coordinating_agent = serializers.SerializerMethodField()
    required_capabilities = serializers.SerializerMethodField()
    keywords = ResearchKeywordSerializer(many=True, read_only=True)

    class Meta:
        model = ResearchNode
        fields = [
            "id",
            "title",
            "description",
            "required_capabilities",
            "keywords",
            "type",
            "status",
            "bounty_amount",
            "required_collaborators",
            "deadline",
            "coordinating_agent",
            "research_duration_days",
            "interview_prompt",
            "coordination_plan",
        ]

    @extend_schema_field(
        inline_serializer(
            name="SyncNodeAgent",
            fields={"name": serializers.CharField(), "id": serializers.IntegerField()},
            allow_null=True,
        )
    )
    def get_coordinating_agent(self, obj):
        return (
            {"name": obj.coordinating_agent.name, "id": obj.coordinating_agent.id} if obj.coordinating_agent else None
        )

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_required_capabilities(self, obj):
        return [cap.slug for cap in obj.required_capabilities.all()]


class ResearchNodePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchNode
        fields = ["coordination_plan"]

    def validate_coordination_plan(self, value):
        # Apply strict normalization (NFKC)
        value = sanitize_agent_input(value, apply_nfkc=True)
        if len(value) > 10000:
            raise serializers.ValidationError("Coordination plan must be under 10000 characters.")
        from .models import ProfaneWord

        profane_words = ProfaneWord.objects.values_list("word", flat=True)
        for word in profane_words:
            if word.lower() in value.lower():
                raise serializers.ValidationError(f"The text contains profane language: '{word}'")
        return value


class BidSerializer(serializers.ModelSerializer):
    agent_detail = AgentSerializer(source="agent", read_only=True)

    class Meta:
        model = Bid
        fields = ["id", "node", "agent", "agent_detail", "interview_response", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at", "agent"]

    def validate_interview_response(self, value):
        # Apply loose sanitization
        value = sanitize_agent_input(value, apply_nfkc=False)
        if len(value) > 2000:
            raise serializers.ValidationError("Interview response must be under 2000 characters.")

        profane_words = ProfaneWord.objects.values_list("word", flat=True)
        for word in profane_words:
            if word.lower() in value.lower():
                raise serializers.ValidationError(f"The response contains profane language: '{word}'")
        return value


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.ReadOnlyField(source="uploaded_by.name")
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "node", "file", "url", "uploaded_by", "uploaded_by_name", "created_at"]
        read_only_fields = ["id", "node", "uploaded_by", "created_at", "file"]

    def validate_file(self, value):
        from .services import process_and_validate_attachment_image

        try:
            return process_and_validate_attachment_image(value)
        except Exception as e:
            msg = e.messages[0] if hasattr(e, "messages") else str(e)
            raise serializers.ValidationError(msg)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_url(self, obj):
        if not obj.file:
            return None
        # Ensure we return a relative path starting with /media/
        url = obj.file.url
        if url.startswith("http"):
            from urllib.parse import urlparse

            return urlparse(url).path
        return url


class ResearchNodeBodySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchNode
        fields = ["body"]

    def validate_body(self, value):
        # Apply loose sanitization
        value = sanitize_agent_input(value, apply_nfkc=False)
        from .models import ProfaneWord

        if len(value) <= 140:
            raise serializers.ValidationError("Content must be over 140 characters")
        if len(value) > 10000:
            raise serializers.ValidationError("Content must be under 10000 characters")

        profane_words = ProfaneWord.objects.values_list("word", flat=True)
        for word in profane_words:
            if word.lower() in value.lower():
                raise serializers.ValidationError(f"The text contains profane language: '{word}'")
        return value
