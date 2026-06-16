from django.contrib import admin
from .models import TaskFile


@admin.register(TaskFile)
class TaskFileAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'task', 'uploader', 'file_type', 'file_size', 'created_at']
    list_filter = ['file_type']
    search_fields = ['original_name', 'task__task_no']
    raw_id_fields = ['task', 'uploader']
