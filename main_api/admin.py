from django.contrib import admin

from .models import (
    AgentDirective,
    Capability,
    NodeType,
    Paper,
    PeerReview,
    ResearchKeyword,
    ResearchNode,
)


@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "created", "updated")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "description")
    filter_horizontal = ("child_capabilities",)


@admin.register(ResearchKeyword)
class ResearchKeywordAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


class PeerReviewInline(admin.TabularInline):
    model = PeerReview
    extra = 1


@admin.register(NodeType)
class NodeTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(ResearchNode)
class ResearchNodeAdmin(admin.ModelAdmin):
    list_display = ("title", "coordinating_agent", "created", "updated", "status", "bounty_amount")
    list_filter = ("status",)
    search_fields = ("title", "description", "body")
    inlines = [PeerReviewInline]
    readonly_fields = ("created", "updated", "visits")
    filter_horizontal = ("required_capabilities", "keywords", "assigned_agents")


@admin.register(PeerReview)
class PeerReviewAdmin(admin.ModelAdmin):
    list_display = (
        "research_node",
        "assigned_reviewer",
        "soundness",
        "significance",
        "novelty",
        "clarity",
        "recommendation",
        "is_approved",
        "created",
    )
    list_filter = ("soundness", "significance", "novelty", "clarity", "recommendation", "is_approved")


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ("title", "research_node", "published_date")
    search_fields = ("title", "abstract", "content")
    filter_horizontal = ("authors",)


@admin.register(AgentDirective)
class AgentDirectiveAdmin(admin.ModelAdmin):
    list_display = ("agent", "maintainer", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("content", "agent__name", "maintainer__username")
    readonly_fields = ("created_at", "updated_at")
