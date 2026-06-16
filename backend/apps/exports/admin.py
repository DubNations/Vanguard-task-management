from django.contrib import admin
from .models import ExportJob


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'requester', 'format', 'status', 'row_count', 'created_at']
    list_filter = ['format', 'status']
    raw_id_fields = ['requester']
