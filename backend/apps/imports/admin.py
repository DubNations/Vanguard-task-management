from django.contrib import admin
from .models import ImportSession


@admin.register(ImportSession)
class ImportSessionAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'uploader', 'file_format', 'status', 'total_rows', 'valid_rows', 'created_at']
    list_filter = ['status', 'file_format']
    search_fields = ['original_name']
    raw_id_fields = ['uploader']
    readonly_fields = ['preview_data', 'errors', 'imported_task_ids']
