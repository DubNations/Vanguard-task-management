from django.contrib import admin

from .models import Task, TaskHistory, TaskComment


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    readonly_fields = ['author', 'created_at']


class TaskHistoryInline(admin.TabularInline):
    model = TaskHistory
    extra = 0
    readonly_fields = ['action', 'actor', 'old_value', 'new_value', 'diff', 'created_at']
    can_delete = False


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'task_no', 'title', 'status', 'priority', 'progress',
        'assignee', 'deadline', 'is_overdue_display', 'created_at'
    ]
    list_filter = ['status', 'priority', 'source']
    search_fields = ['task_no', 'title', 'description']
    raw_id_fields = ['creator', 'assignee', 'reviewer']
    date_hierarchy = 'created_at'
    readonly_fields = ['task_no', 'created_at', 'updated_at']
    inlines = [TaskCommentInline, TaskHistoryInline]

    def is_overdue_display(self, obj):
        return obj.is_overdue
    is_overdue_display.boolean = True
    is_overdue_display.short_description = '已逾期'


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ['task', 'action', 'actor', 'created_at']
    list_filter = ['action']
    search_fields = ['task__task_no', 'task__title']
    raw_id_fields = ['task', 'actor']
    readonly_fields = ['id']


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'author', 'is_internal', 'created_at']
    list_filter = ['is_internal']
    raw_id_fields = ['task', 'author']
