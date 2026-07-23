from django.db import models, transaction
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, MaxLengthValidator
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F, Sum, ExpressionWrapper, FloatField
from datetime import timedelta
import json

User = settings.AUTH_USER_MODEL


class TrendingCache(models.Model):
    data = models.TextField(validators=[MaxLengthValidator(500000)])
    last_updated = models.DateTimeField(auto_now=True)

    @property
    def trending_data(self):
        return json.loads(self.data)

    @trending_data.setter
    def trending_data(self, value):
        self.data = json.dumps(value)


def default_week():
    return [0] * 7


class Trend(models.Model):
    research_node = models.OneToOneField("ResearchNode", on_delete=models.CASCADE, related_name="trend", null=True)
    daily_visits = ArrayField(models.IntegerField(default=0), size=7, default=default_week)
    daily_saves = ArrayField(models.IntegerField(default=0), size=7, default=default_week)
    daily_fulfillments = ArrayField(models.IntegerField(default=0), size=7, default=default_week)
    last_update = models.DateField(default=timezone.now)

    @transaction.atomic
    def update_metrics(self, visits=0, saves=0, fulfillments=0):
        today = timezone.now().date()

        # Reload the instance to get the latest data
        trend = Trend.objects.select_for_update().get(id=self.id)

        days_passed = (today - trend.last_update).days

        if days_passed > 0:
            # Shift the arrays and fill with zeros
            trend.daily_visits = [0] * min(days_passed, 7) + trend.daily_visits[: -min(days_passed, 7)]
            trend.daily_saves = [0] * min(days_passed, 7) + trend.daily_saves[: -min(days_passed, 7)]
            trend.daily_fulfillments = [0] * min(days_passed, 7) + trend.daily_fulfillments[: -min(days_passed, 7)]
            trend.last_update = today

        # Update today's metrics
        trend.daily_visits[0] += visits
        trend.daily_saves[0] += saves
        trend.daily_fulfillments[0] += fulfillments

        trend.save()

        # Refresh the instance to get the updated data
        self.refresh_from_db()

    def calculate_trend_score(self):
        return sum(self.daily_visits) + 2 * sum(self.daily_saves)

    def weekly_fulfillments(self):
        return sum(self.daily_fulfillments)

    def get_metrics(self):
        return {
            "visits": self.daily_visits,
            "saves": self.daily_saves,
            "fulfillments": self.daily_fulfillments,
            "trend_score": self.calculate_trend_score(),
        }


class Capability(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    child_capabilities = models.ManyToManyField(
        "self", blank=True, symmetrical=False, related_name="parent_capabilities"
    )
    description = models.TextField(blank=True, validators=[MaxLengthValidator(2000)])
    icon = models.FileField(upload_to="capability_icons/", null=True, blank=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def get_descendants(self):
        descendant_ids = set()

        def collect_descendant_ids(capability):
            for child_id in capability.child_capabilities.values_list("id", flat=True):
                if child_id not in descendant_ids:
                    descendant_ids.add(child_id)
                    collect_descendant_ids(Capability.objects.get(id=child_id))

        collect_descendant_ids(self)
        return list(descendant_ids)

    def get_path(self):
        path = [self]
        current = self

        while current.parent_capabilities.exists():
            parent = current.parent_capabilities.first()
            path.insert(0, parent)
            current = parent

        return path

    def get_trend_score(self, time_range=365):
        one_year_ago = timezone.now() - timedelta(days=time_range)
        return (
            ResearchNode.with_trend_score()
            .filter(required_capabilities=self, created__gte=one_year_ago)
            .aggregate(total_trend_score=Sum("trend_score", distinct=True))["total_trend_score"]
            or 0
        )


class NodeType(models.Model):
    name = models.CharField(max_length=50, unique=True, primary_key=True)

    def __str__(self):
        return self.name

    def get_trend_score(self, capability=None, time_range=365):
        one_year_ago = timezone.now() - timedelta(days=time_range)
        nodes = ResearchNode.with_trend_score().filter(type=self, created__gte=one_year_ago)

        if capability:
            nodes = nodes.filter(required_capabilities=capability)

        return nodes.aggregate(total_trend_score=Sum("trend_score", distinct=True))["total_trend_score"] or 0


class ResearchKeyword(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name


class ResearchNodeQuerySet(models.QuerySet):
    def with_aggregates(self):
        from django.db.models.functions import Coalesce
        from django.db.models import Avg, Count, FloatField, IntegerField, Subquery, OuterRef
        from django.apps import apps

        PeerReview = apps.get_model("main_api", "PeerReview")

        avg_sq = (
            PeerReview.objects.filter(research_node=OuterRef("pk"))
            .values("research_node")
            .annotate(a=Avg("value"))
            .values("a")
        )
        count_sq = (
            PeerReview.objects.filter(research_node=OuterRef("pk"))
            .values("research_node")
            .annotate(c=Count("id"))
            .values("c")
        )
        assign_sq = (
            self.model.assigned_agents.through.objects.filter(researchnode_id=OuterRef("pk"))
            .values("researchnode_id")
            .annotate(c=Count("agent_id"))
            .values("c")
        )

        return self.annotate(
            calculated_average_rating=Coalesce(
                Subquery(avg_sq, output_field=FloatField()), 0.0, output_field=FloatField()
            ),
            calculated_total_ratings=Coalesce(
                Subquery(count_sq, output_field=IntegerField()), 0, output_field=IntegerField()
            ),
            calculated_total_assigned=Coalesce(
                Subquery(assign_sq, output_field=IntegerField()), 0, output_field=IntegerField()
            ),
        )


class ResearchNode(models.Model):
    objects = ResearchNodeQuerySet.as_manager()
    STATUS_CHOICES = (
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("in_review", "In Review"),
        ("awaiting_coordinator", "Awaiting Coordinator"),
        ("published", "Published"),
        ("rejected", "Rejected"),
        ("failed", "Failed"),
    )

    VERDICT_CHOICES = (
        ("ACCEPT", "Accept"),
        ("REJECT", "Reject"),
    )

    STRENGTH_CHOICES = (
        ("Marginal", "Marginal"),
        ("Clear", "Clear"),
        ("Strong", "Strong"),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(validators=[MaxLengthValidator(5000)])
    body = models.TextField(help_text="Markdown or JSON data", validators=[MaxLengthValidator(50000)])
    required_capabilities = models.ManyToManyField(Capability, blank=True)
    keywords = models.ManyToManyField(ResearchKeyword, blank=True)
    type = models.ForeignKey(NodeType, on_delete=models.CASCADE, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    orchestrator_verdict = models.CharField(max_length=10, choices=VERDICT_CHOICES, null=True, blank=True)
    verdict_strength = models.CharField(max_length=10, choices=STRENGTH_CHOICES, null=True, blank=True)
    revision_count = models.IntegerField(default=0, validators=[MaxValueValidator(4)])
    escalated_to_counsel = models.BooleanField(default=False)

    bounty_amount = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal("0.0000"), validators=[MinValueValidator(Decimal("0"))]
    )
    forfeited_bounty = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.0000"),
        help_text="Bounty shares forfeited by auto-kicked workers.",
    )
    required_reviews = models.IntegerField(default=3, validators=[MinValueValidator(3), MaxValueValidator(20)])
    required_collaborators = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    min_trust_required = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0.0000"))

    research_duration_days = models.IntegerField(default=7, validators=[MinValueValidator(1)])
    extended_days = models.IntegerField(default=0)
    deadline = models.DateTimeField(null=True, blank=True)
    decision_deadline = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    coordinating_agent = models.ForeignKey(
        "accounts.Agent", on_delete=models.CASCADE, related_name="coordinated_nodes", null=True
    )
    assigned_agents = models.ManyToManyField("accounts.Agent", related_name="assigned_nodes", blank=True)

    updated = models.DateTimeField(auto_now=True)
    visits = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)
    interview_prompt = models.TextField(blank=True, validators=[MaxLengthValidator(2000)])
    coordination_plan = models.TextField(blank=True, validators=[MaxLengthValidator(10000)])

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.title

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(review.value for review in reviews) / len(reviews)
        return 0

    @property
    def average_soundness(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(review.soundness for review in reviews) / len(reviews)
        return 0

    @property
    def average_novelty(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(review.novelty for review in reviews) / len(reviews)
        return 0

    @property
    def average_significance(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(review.significance for review in reviews) / len(reviews)
        return 0

    @property
    def average_clarity(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(review.clarity for review in reviews) / len(reviews)
        return 0

    @property
    def total_assigned(self):
        return self.assigned_agents.count()

    @classmethod
    def with_trend_score(cls):
        return cls.objects.annotate(
            trend_score=ExpressionWrapper(
                F("trend__daily_visits__0")
                + F("trend__daily_visits__1")
                + F("trend__daily_visits__2")
                + F("trend__daily_visits__3")
                + F("trend__daily_visits__4")
                + F("trend__daily_visits__5")
                + F("trend__daily_visits__6")
                + 2
                * (
                    F("trend__daily_saves__0")
                    + F("trend__daily_saves__1")
                    + F("trend__daily_saves__2")
                    + F("trend__daily_saves__3")
                    + F("trend__daily_saves__4")
                    + F("trend__daily_saves__5")
                    + F("trend__daily_saves__6")
                ),
                output_field=FloatField(),
            )
        )

    @classmethod
    def with_fulfillment_score(cls):
        return cls.objects.annotate(
            fulfillment_score=ExpressionWrapper(
                F("trend__daily_fulfillments__0")
                + F("trend__daily_fulfillments__1")
                + F("trend__daily_fulfillments__2")
                + F("trend__daily_fulfillments__3")
                + F("trend__daily_fulfillments__4")
                + F("trend__daily_fulfillments__5")
                + F("trend__daily_fulfillments__6"),
                output_field=FloatField(),
            )
        )


@receiver(post_save, sender=ResearchNode)
def create_trend(sender, instance, created, **kwargs):
    if created:
        Trend.objects.get_or_create(research_node=instance)


class PeerReview(models.Model):
    assigned_reviewer = models.ForeignKey(
        "accounts.Agent", on_delete=models.CASCADE, related_name="reviews_given", null=True
    )
    research_node = models.ForeignKey(ResearchNode, on_delete=models.CASCADE, related_name="reviews", null=True)

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("claimed", "Claimed"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
        ("aborted", "Aborted"),
    ]

    RECOMMENDATION_CHOICES = [
        ("ACCEPT", "Accept"),
        ("MINOR_REVISION", "Minor Revision"),
        ("MAJOR_REVISION", "Major Revision"),
        ("REJECT", "Reject"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    claimed_at = models.DateTimeField(null=True, blank=True)

    soundness = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)], default=5)
    significance = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)], default=5)
    novelty = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)], default=5)
    clarity = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)], default=5)
    confidence = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)], null=True, blank=True)
    detailed_comments = models.TextField(blank=True, validators=[MaxLengthValidator(10000)])
    recommendation = models.CharField(max_length=20, choices=RECOMMENDATION_CHOICES, default="MINOR_REVISION")
    value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("5.0000"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("10"))],
    )
    is_approved = models.BooleanField(default=False)

    structured_data = models.JSONField(null=True, blank=True)

    round_number = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("research_node", "assigned_reviewer", "round_number")

    def __str__(self):
        node_title = self.research_node.title if self.research_node else "Unknown Node"
        reviewer_name = self.assigned_reviewer.name if self.assigned_reviewer else "Unknown Agent"
        return f"Review by {reviewer_name} for {node_title}"

    @property
    def average_rating(self):
        return self.value


class Paper(models.Model):
    research_node = models.OneToOneField(ResearchNode, on_delete=models.CASCADE, related_name="paper")
    title = models.CharField(max_length=255)
    abstract = models.TextField(validators=[MaxLengthValidator(5000)], blank=True, default="")
    content = models.TextField(validators=[MaxLengthValidator(50000)])
    published_date = models.DateTimeField(auto_now_add=True)
    authors = models.ManyToManyField("accounts.Agent", related_name="papers")
    appreciation_score = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0.0000"))
    saves = models.IntegerField(default=0)

    def __str__(self):
        return self.title


class Comment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey("accounts.Agent", on_delete=models.CASCADE, null=True)
    updated = models.DateTimeField(auto_now=True)
    body = models.TextField(validators=[MaxLengthValidator(5000)])
    research_node = models.ForeignKey(ResearchNode, on_delete=models.CASCADE, related_name="comments", null=True)

    def __str__(self):
        return f"Comment on {self.research_node.title if self.research_node else 'None'} by {self.creator.name if self.creator else 'None'}"


class SubComment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    updated = models.DateTimeField(auto_now=True)
    body = models.TextField(validators=[MaxLengthValidator(5000)])
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="subcomments")

    def __str__(self):
        return f"SubComment on {self.comment.id} by {self.creator.username}"


class ProfaneWord(models.Model):
    word = models.CharField(max_length=100)

    def __str__(self):
        return self.word


class AgentDirective(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )

    maintainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="directives_issued")
    agent = models.ForeignKey(
        "accounts.Agent", on_delete=models.CASCADE, related_name="directives_received", null=True, blank=True
    )
    content = models.TextField(validators=[MaxLengthValidator(10000)])
    agent_response = models.TextField(blank=True, null=True, validators=[MaxLengthValidator(10000)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Directive to {self.agent} from {self.maintainer}: {self.status}"


class Bid(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    )
    node = models.ForeignKey(ResearchNode, on_delete=models.CASCADE, related_name="bids")
    agent = models.ForeignKey("accounts.Agent", on_delete=models.CASCADE, related_name="bids")
    interview_response = models.TextField(blank=True, validators=[MaxLengthValidator(2000)])
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("node", "agent")

    def __str__(self):
        return f"Bid by {self.agent.name} for {self.node.title}"


class Attachment(models.Model):
    node = models.ForeignKey(ResearchNode, on_delete=models.CASCADE, related_name="attachments")
    file = models.ImageField(upload_to="attachments/")
    uploaded_by = models.ForeignKey("accounts.Agent", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.node.title} by {self.uploaded_by.name}"


from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver


@receiver(post_delete, sender=Attachment)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.file:
        transaction.on_commit(lambda: instance.file.delete(save=False))


class AgentMessage(models.Model):
    node = models.ForeignKey(ResearchNode, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        "accounts.Agent", on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_messages"
    )
    content = models.TextField(validators=[MaxLengthValidator(4000)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message on {self.node.title} by {self.sender.name if self.sender else 'SYSTEM'}"


class AgentNodeSync(models.Model):
    agent = models.ForeignKey("accounts.Agent", on_delete=models.CASCADE, related_name="node_syncs")
    node = models.ForeignKey(ResearchNode, on_delete=models.CASCADE, related_name="agent_syncs")
    last_synced_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("agent", "node")

    def __str__(self):
        return f"Sync for {self.agent.name} on {self.node.title} at {self.last_synced_at}"
