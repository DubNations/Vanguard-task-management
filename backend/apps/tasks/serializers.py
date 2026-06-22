from rest_framework import serializers
from .models import Task, TaskHistory, TaskComment, TaskParticipant
from common.utils import strip_html_tags


class TaskParticipantSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = TaskParticipant
        fields = [
            'id', 'user', 'user_name', 'role', 'role_display',
            'points', 'status', 'status_display',
            'created_at', 'completed_at',
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']


class TaskParticipantCreateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=TaskParticipant.Role.choices)
    points = serializers.IntegerField(min_value=0)


class TaskListSerializer(serializers.ModelSerializer):
    assignee_name = serializers.CharField(source='assignee.username', read_only=True, default='')
    creator_name = serializers.CharField(source='creator.username', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    task_mode_display = serializers.CharField(source='get_task_mode_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True, default=0)
    files_count = serializers.IntegerField(read_only=True, default=0)
    participants_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Task
        fields = [
            'id', 'task_no', 'title', 'status', 'status_display',
            'priority', 'priority_display', 'progress',
            'task_mode', 'task_mode_display',
            'assignee', 'assignee_name', 'creator_name',
            'task_source', 'dispatcher_name',
            'deadline', 'is_overdue', 'tags',
            'reward_points', 'max_claimers', 'current_claimers',
            'comments_count', 'files_count', 'participants_count',
            'created_at', 'updated_at',
        ]


class TaskDetailSerializer(serializers.ModelSerializer):
    assignee_name = serializers.CharField(source='assignee.username', read_only=True, default='')
    creator_name = serializers.CharField(source='creator.username', read_only=True, default='')
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    task_mode_display = serializers.CharField(source='get_task_mode_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_until_deadline = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True, default=0)
    files_count = serializers.IntegerField(read_only=True, default=0)
    participants = TaskParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'task_no', 'title', 'description',
            'status', 'status_display', 'priority', 'priority_display',
            'progress',
            'task_mode', 'task_mode_display',
            'max_claimers', 'current_claimers',
            'assignee', 'assignee_name',
            'creator', 'creator_name', 'reviewer', 'reviewer_name',
            'deadline', 'started_at', 'completed_at',
            'task_source', 'completion_criteria', 'dispatcher_name', 'output',
            'is_overdue', 'days_until_deadline',
            'tags', 'custom_fields', 'source', 'reward_points',
            'participants',
            'comments_count', 'files_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'task_no', 'status', 'creator', 'created_at', 'updated_at']


class TaskCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, default='', allow_blank=True)
    priority = serializers.ChoiceField(choices=Task.Priority.choices, default=Task.Priority.MEDIUM)
    deadline = serializers.DateTimeField(required=False, allow_null=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    custom_fields = serializers.DictField(required=False, default=dict)
    reward_points = serializers.IntegerField(min_value=0, default=0)

    # WPS 模板字段
    task_source = serializers.CharField(max_length=200, required=False, default='', allow_blank=True)
    completion_criteria = serializers.CharField(required=False, default='', allow_blank=True)
    dispatcher_name = serializers.CharField(max_length=50, required=False, default='', allow_blank=True)
    output = serializers.CharField(required=False, default='', allow_blank=True)

    # 任务模式字段
    task_mode = serializers.ChoiceField(
        choices=Task.TaskMode.choices, default=Task.TaskMode.ASSIGNED
    )
    participants = TaskParticipantCreateSerializer(many=True, required=False, default=list)
    max_claimers = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import User
        user_qs = User.objects.all()
        self.fields['assignee'] = serializers.PrimaryKeyRelatedField(
            required=False, allow_null=True, queryset=user_qs
        )
        self.fields['reviewer'] = serializers.PrimaryKeyRelatedField(
            required=False, allow_null=True, queryset=user_qs
        )

    def validate_title(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('标题至少2个字符')
        return value

    def validate(self, data):
        # XSS 防御：清洗所有文本字段的 HTML 标签
        text_fields = ['title', 'description', 'task_source', 'completion_criteria',
                        'dispatcher_name', 'output']
        for field in text_fields:
            if field in data and isinstance(data[field], str):
                data[field] = strip_html_tags(data[field])

        # 清洗 tags 中的 HTML
        if 'tags' in data and data['tags']:
            data['tags'] = [strip_html_tags(t) for t in data['tags']]

        task_mode = data.get('task_mode', Task.TaskMode.ASSIGNED)
        participants = data.get('participants', [])
        reward_points = data.get('reward_points', 0)
        max_claimers = data.get('max_claimers')

        if task_mode == Task.TaskMode.ASSIGNED:
            # If participants provided, validate them; otherwise require assignee
            if participants:
                for p in participants:
                    if p['role'] not in (
                        TaskParticipant.Role.CHIEF_LEAD,
                        TaskParticipant.Role.GROUP_LEAD,
                        TaskParticipant.Role.PARTICIPANT,
                    ):
                        raise serializers.ValidationError(
                            {'participants': f"派发模式角色必须为总牵头人/小组牵头/参与，收到: {p['role']}"}
                        )
                chief_leads = [p for p in participants if p['role'] == TaskParticipant.Role.CHIEF_LEAD]
                if not chief_leads:
                    raise serializers.ValidationError({'participants': '派发模式必须指定至少一名总牵头人'})
        elif task_mode == Task.TaskMode.FREE_CLAIM:
            if reward_points <= 0:
                raise serializers.ValidationError({'reward_points': '揭榜挂帅模式必须设置积分'})
            if participants:
                raise serializers.ValidationError({'participants': '揭榜挂帅模式不需要指定参与者'})
        elif task_mode == Task.TaskMode.FIXED_CLAIM:
            if reward_points <= 0:
                raise serializers.ValidationError({'reward_points': '揭榜挂帅模式必须设置积分'})
            if not max_claimers:
                raise serializers.ValidationError({'max_claimers': '固定揭榜必须设置名额数'})
            if participants:
                raise serializers.ValidationError({'participants': '揭榜挂帅模式不需要指定参与者'})

        return data


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
        if len(value) > 2000:
            raise serializers.ValidationError('评论不能超过2000字符')
        return strip_html_tags(value)
