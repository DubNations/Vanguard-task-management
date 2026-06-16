from rest_framework import serializers
from .models import Task, TaskHistory, TaskComment


class TaskListSerializer(serializers.ModelSerializer):
    assignee_name = serializers.CharField(source='assignee.username', read_only=True, default='')
    creator_name = serializers.CharField(source='creator.username', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True, default=0)
    files_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Task
        fields = [
            'id', 'task_no', 'title', 'status', 'status_display',
            'priority', 'priority_display', 'progress',
            'assignee', 'assignee_name', 'creator_name',
            'deadline', 'is_overdue', 'tags',
            'comments_count', 'files_count',
            'created_at', 'updated_at',
        ]


class TaskDetailSerializer(serializers.ModelSerializer):
    assignee_name = serializers.CharField(source='assignee.username', read_only=True, default='')
    creator_name = serializers.CharField(source='creator.username', read_only=True, default='')
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_until_deadline = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True, default=0)
    files_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Task
        fields = [
            'id', 'task_no', 'title', 'description',
            'status', 'status_display', 'priority', 'priority_display',
            'progress', 'assignee', 'assignee_name',
            'creator', 'creator_name', 'reviewer', 'reviewer_name',
            'deadline', 'started_at', 'completed_at',
            'is_overdue', 'days_until_deadline',
            'tags', 'custom_fields', 'source', 'reward_points',
            'comments_count', 'files_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'task_no', 'creator', 'created_at', 'updated_at']


class TaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'deadline', 'assignee', 'reviewer', 'tags', 'custom_fields', 'reward_points']

    def validate_title(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('标题至少2个字符')
        return value


class TaskTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Task.Status.choices)
    note = serializers.CharField(required=False, default='', allow_blank=True)


class TaskProgressSerializer(serializers.Serializer):
    progress = serializers.IntegerField(min_value=0, max_value=100)


class TaskHistorySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.username', read_only=True, default='system')
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = TaskHistory
        fields = [
            'id', 'action', 'action_display', 'actor_name',
            'old_value', 'new_value', 'diff', 'note', 'created_at',
        ]


class TaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    author_email = serializers.CharField(source='author.email', read_only=True)

    class Meta:
        model = TaskComment
        fields = [
            'id', 'author_name', 'author_email', 'content',
            'is_internal', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaskCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = ['content', 'is_internal']

    def validate_content(self, value):
        if len(value.strip()) < 1:
            raise serializers.ValidationError('评论不能为空')
        return value
