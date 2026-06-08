from django.db import models
from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("new_follower", "New Follower"),
        ("node_saved", "Node Saved"),
        ("peer_review_received", "Peer Review Received"),
        ("high_views", "High Views"),
        ("assignment_received", "Research Assignment"),
        ("payout_received", "Bounty Payout Received"),
        ("custom", "Custom Notification"),
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    research_node = models.ForeignKey("main_api.ResearchNode", on_delete=models.CASCADE, null=True, blank=True)
    verb = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient.username} - {self.get_notification_type_display()}"


class Appreciation(models.Model):
    VOTE_CHOICES = [
        (-2, "-2"),
        (-1, "-1"),
        (1, "+1"),
        (2, "+2"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    paper = models.ForeignKey("main_api.Paper", on_delete=models.CASCADE, related_name="appreciations")
    vote = models.IntegerField(choices=VOTE_CHOICES)
    impact = models.DecimalField(max_digits=12, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "paper")

    def __str__(self):
        return f"Appreciation for {self.paper.title} by {self.user.username}"


class Report(models.Model):
    REASON_CHOICES = [
        ("spam", "Spam"),
        ("harassment", "Harassment"),
        ("inappropriate", "Inappropriate Content"),
        ("plagiarism_or_copyright", "Plagiarism or Copyright"),
        ("malicious_activity", "Malicious Activity"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("action_taken", "Action Taken"),
        ("dismissed", "Dismissed"),
        ("dismissed_as_abuse", "Dismissed as Abuse"),
    ]

    reporter_account = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports_submitted"
    )
    reporter_agent = models.ForeignKey(
        "accounts.Agent", on_delete=models.SET_NULL, null=True, blank=True, related_name="reports_submitted"
    )

    # Generic Foreign Key to target ResearchNode, Agent, or Account
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    description = models.TextField(validators=[MaxLengthValidator(5000)])
    node_id = models.PositiveIntegerField(null=True, blank=True, help_text="Contextual ResearchNode ID")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report by {self.reporter_account or self.reporter_agent} - {self.reason}"


class Complaint(models.Model):
    CATEGORY_CHOICES = [
        ("auto_kick_dispute", "Auto-Kick Dispute"),
        ("platform_issue", "Platform Issue"),
        ("transaction_issue", "Transaction Issue"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("reviewing", "Reviewing"),
        ("resolved", "Resolved"),
        ("rejected", "Rejected"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaints")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    description = models.TextField(validators=[MaxLengthValidator(5000)])
    reference_id = models.CharField(max_length=100, null=True, blank=True, help_text="Related Node ID or Report ID")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Complaint by {self.user.username} - {self.category}"
