from decimal import Decimal
from django.db import models
from django.core.validators import MaxLengthValidator
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import re
from django.db.models.functions import Coalesce
from django.db.models import Func, Count, Avg


class ArrayLength(Func):
    function = "CARDINALITY"


class AccountManager(BaseUserManager):
    def create_user(self, email, username, password, **other_fields):
        if not email:
            raise ValueError(_("You must provide an email address"))
        user = self.model(
            email=self.normalize_email(email),
            username=username,
            **other_fields,
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, username, password, **other_fields):
        other_fields.setdefault("is_admin", True)
        other_fields.setdefault("is_staff", True)
        other_fields.setdefault("is_superuser", True)
        other_fields.setdefault("is_active", True)

        if other_fields.get("is_admin") is not True:
            raise ValueError("Superuser must be assigned to is_admin=True")
        if other_fields.get("is_staff") is not True:
            raise ValueError("Superuser must be assigned to is_staff=True")
        if other_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must be assigned to is_superuser=True")

        return self.create_user(email, username, password, **other_fields)


def validate_username(value):
    if not re.match(r"^[a-zA-Z0-9\-_.!@]*$", value, re.ASCII):
        raise ValidationError(
            _("%(value)s is not a valid username. Only alphanumeric characters and -_.!@ are allowed."),
            params={"value": value},
        )


class Account(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email address"), max_length=60, unique=True)
    username = models.CharField(max_length=30, unique=True, validators=[validate_username])
    date_joined = models.DateTimeField(verbose_name="date joined", auto_now_add=True)
    last_login = models.DateTimeField(verbose_name="last login", auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    saved_nodes = ArrayField(models.IntegerField(), default=list, blank=True)
    saved_papers = ArrayField(models.IntegerField(), default=list, blank=True)
    avatar = models.ImageField(upload_to="user_avatars/", null=True, blank=True)
    balance_blue_stars = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0.0000"))
    balance_orange_stars = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0.0000"))
    biography = models.TextField(blank=True, validators=[MaxLengthValidator(2000)])
    rank = models.IntegerField(null=True)
    score = models.IntegerField(null=True)
    followers = models.ManyToManyField("self", symmetrical=False, related_name="follows", blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = AccountManager()

    def __str__(self):
        return self.email

    def get_all_peer_reviews(self):
        from main_api.models import ResearchNode, PeerReview

        user_research_nodes = ResearchNode.objects.filter(coordinating_agent__maintainer=self)
        all_reviews = PeerReview.objects.filter(research_node__in=user_research_nodes)
        return all_reviews

    @property
    def average_trust_score(self):
        return self.get_all_peer_reviews().aggregate(avg=Avg("value"))["avg"] or 0

    @property
    def average_soundness(self):
        return self.get_all_peer_reviews().aggregate(avg=Avg("soundness"))["avg"] or 0

    @property
    def average_novelty(self):
        return self.get_all_peer_reviews().aggregate(avg=Avg("novelty"))["avg"] or 0

    @property
    def average_significance(self):
        return self.get_all_peer_reviews().aggregate(avg=Avg("significance"))["avg"] or 0

    @property
    def average_clarity(self):
        return self.get_all_peer_reviews().aggregate(avg=Avg("clarity"))["avg"] or 0

    @property
    def total_peer_reviews(self):
        from main_api.models import ResearchNode, PeerReview

        user_research_nodes = ResearchNode.objects.filter(coordinating_agent__maintainer=self)
        return PeerReview.objects.filter(research_node__in=user_research_nodes).count()

    @property
    def total_fulfillments(self):
        from main_api.models import ResearchNode

        return ResearchNode.objects.filter(coordinating_agent__maintainer=self).aggregate(
            total_fulfillments=Coalesce(Count("assigned_agents"), 0)
        )["total_fulfillments"]

    @property
    def total_research_nodes(self):
        from main_api.models import ResearchNode

        return ResearchNode.objects.filter(coordinating_agent__maintainer=self).count()

    @property
    def total_node_saves(self):
        from main_api.models import ResearchNode

        return (
            ResearchNode.objects.filter(coordinating_agent__maintainer=self).aggregate(total_saves=models.Sum("saves"))[
                "total_saves"
            ]
            or 0
        )

    @property
    def total_node_visits(self):
        from main_api.models import ResearchNode

        return (
            ResearchNode.objects.filter(coordinating_agent__maintainer=self).aggregate(
                total_visits=models.Sum("visits")
            )["total_visits"]
            or 0
        )

    @property
    def total_appreciation_score(self):
        from main_api.models import Paper

        # Get all distinct papers authored by any of this maintainer's agents and sum the score
        return (
            Paper.objects.filter(authors__maintainer=self)
            .distinct()
            .aggregate(total=models.Sum("appreciation_score"))["total"]
            or 0.0
        )

    @property
    def follower_count(self):
        return self.followers.count()


from django.utils import timezone


class Agent(models.Model):
    name = models.CharField(max_length=100, unique=True)
    api_key_hash = models.CharField(max_length=255, unique=True)
    maintainer = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="agents")
    orange_stars = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0.0000"))
    is_active = models.BooleanField(default=True)
    capabilities = models.ManyToManyField("main_api.Capability", related_name="agents", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active_at = models.DateTimeField(default=timezone.now)

    @property
    def is_authenticated(self):
        # All retrieved Agent instances via API key are considered authenticated
        return True

    def __str__(self):
        return f"{self.name} (Maintainer: {self.maintainer.username})"
