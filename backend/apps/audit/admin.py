from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'resource_type', 'description', 'ip_address', 'created_at']
    list_filter = ['action', 'resource_type']
    search_fields = ['user__username', 'description']
    raw_id_fields = ['user']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
