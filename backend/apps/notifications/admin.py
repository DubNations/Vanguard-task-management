from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'type', 'is_read', 'email_sent', 'created_at']
    list_filter = ['type', 'is_read', 'email_sent']
    search_fields = ['title', 'content', 'recipient__username']
    raw_id_fields = ['recipient', 'task', 'actor']
