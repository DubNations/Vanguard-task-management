from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'leader', 'member_count', 'created_at']
    search_fields = ['name']
    raw_id_fields = ['leader']

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = '成员数'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'team', 'is_active', 'last_login']
    list_filter = ['role', 'team', 'is_active', 'is_staff']
    search_fields = ['username', 'email', 'phone']
    ordering = ['-date_joined']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('扩展信息', {
            'fields': ('phone', 'role', 'team', 'avatar', 'last_login_ip'),
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('扩展信息', {
            'fields': ('email', 'phone', 'role', 'team'),
        }),
    )
