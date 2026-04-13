from django.contrib import admin
from accounts.models import Account, Agent
from django.contrib.auth.admin import UserAdmin

class UserAdminConfig(UserAdmin):
    search_fields = ('email', 'username')
    list_filter = ('is_admin', 'is_staff', 'is_superuser', 'is_active')
    ordering = ('-username',)
    list_display = ('email', 'username', 'is_admin',
                    'rank', 'score', 'is_active')
    fieldsets = (
        ('Personal', {'fields': ('email', 'username', 'biography')}),
        ('Permissions', {'fields': ('is_admin',
                                    'is_staff', 'is_superuser', 'is_active')}),
        ('Balance', {'fields': ('balance_blue_stars', 'balance_orange_stars')}),
        ('Nodes', {'fields': ('saved_nodes',)})
    )

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('name', 'maintainer', 'orange_stars', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'maintainer__username', 'api_key')

admin.site.register(Account, UserAdminConfig)
