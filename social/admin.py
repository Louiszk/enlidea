from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Notification, Appreciation, Report, Complaint

User = get_user_model()


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "notification_type", "actor", "verb", "created_at", "is_read")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("recipient__username", "actor__username", "verb")
    date_hierarchy = "created_at"
    actions = ["mark_as_read", "mark_as_unread"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("recipient", "actor", "research_node")

    @admin.action(description="Mark selected notifications as read")
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description="Mark selected notifications as unread")
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)


@admin.register(Appreciation)
class AppreciationAdmin(admin.ModelAdmin):
    list_display = ("user", "paper", "vote", "impact", "created_at")
    list_filter = ("vote", "created_at")
    search_fields = ("user__username", "paper__title")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reporter_account",
        "reporter_agent",
        "reason",
        "status",
        "content_type",
        "object_id",
        "created_at",
    )
    list_filter = ("reason", "status", "created_at", "content_type")
    search_fields = ("description", "reporter_account__username", "reporter_agent__name", "object_id")
    date_hierarchy = "created_at"


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "status", "reference_id", "created_at")
    list_filter = ("category", "status", "created_at")
    search_fields = ("description", "user__username", "reference_id")
    date_hierarchy = "created_at"
