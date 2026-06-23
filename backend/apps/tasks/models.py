import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Task(models.Model):
    """任务单 — 核心业务模型。"""

    class Status(models.TextChoices):
        PENDING = 'PENDING', '待领取'
        IN_PROGRESS = 'IN_PROGRESS', '进行中'
        IN_REVIEW = 'IN_REVIEW', '待审核'
        COMPLETED = 'COMPLETED', '已完成'
        REJECTED = 'REJECTED', '已退回'
        CANCELLED = 'CANCELLED', '已取消'

    class Priority(models.TextChoices):
        LOW = 'LOW', '低'
        MEDIUM = 'MEDIUM', '中'
        HIGH = 'HIGH', '高'
        URGENT = 'URGENT', '紧急'

    class TaskMode(models.TextChoices):
        ASSIGNED = 'ASSIGNED', '派发'
        FREE_CLAIM = 'FREE_CLAIM', '自由揭榜'
        FIXED_CLAIM = 'FIXED_CLAIM', '固定揭榜'

    # 合法状态转换
    STATUS_TRANSITIONS = {
        Status.PENDING: [Status.IN_PROGRESS, Status.CANCELLED],
        Status.IN_PROGRESS: [Status.IN_REVIEW, Status.PENDING, Status.CANCELLED],
        Status.IN_REVIEW: [Status.COMPLETED, Status.REJECTED],
        Status.COMPLETED: [],
        Status.REJECTED: [Status.IN_PROGRESS],
        Status.CANCELLED: [],
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_no = models.CharField('任务编号', max_length=32, unique=True, db_index=True)
    title = models.CharField('标题', max_length=200)
    description = models.TextField('详细描述', blank=True, default='')

    status = models.CharField(
        '状态', max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    priority = models.CharField(
        '优先级', max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    progress = models.PositiveSmallIntegerField('进度(%)', default=0)

    # 人员
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='created_tasks', verbose_name='创建人'
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_tasks', verbose_name='负责人'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_tasks', verbose_name='审核人'
    )

    # 时间
    deadline = models.DateTimeField('截止日期', null=True, blank=True)
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)

    # 扩展
    # 任务模式
    task_mode = models.CharField(
        '任务模式', max_length=20, choices=TaskMode.choices,
        default=TaskMode.ASSIGNED, db_index=True
    )
    max_claimers = models.PositiveIntegerField('揭榜名额', null=True, blank=True,
        help_text='固定揭榜模式下的名额数，null 表示不限')
    current_claimers = models.PositiveIntegerField('已领取人数', default=0)

    # WPS 模板字段（标准参数项）
    task_source = models.CharField('任务来源', max_length=200, blank=True, default='',
        help_text='如：关于征集公司2026年第一批...、部门自选等')
    completion_criteria = models.TextField('完成标准', blank=True, default='')
    dispatcher_name = models.CharField('派发人', max_length=50, blank=True, default='')
    output = models.TextField('产出要求', blank=True, default='')

    tags = models.JSONField('标签', default=list, blank=True)
    custom_fields = models.JSONField('自定义字段', default=dict, blank=True)
    external_id = models.CharField('外部ID(导入用)', max_length=100, blank=True, default='')
    source = models.CharField('来源', max_length=20, default='MANUAL', blank=True)
    reward_points = models.IntegerField('任务积分', default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tasks'
        verbose_name = '任务'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['deadline']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['completed_at']),
        ]

    def __str__(self):
        return f'[{self.task_no}] {self.title}'

    def can_transition_to(self, new_status):
        return new_status in self.STATUS_TRANSITIONS.get(self.status, [])

    @property
    def is_overdue(self):
        if self.deadline and self.status not in (self.Status.COMPLETED, self.Status.CANCELLED):
            return timezone.now() > self.deadline
        return False

    @property
    def days_until_deadline(self):
        if self.deadline:
            delta = self.deadline - timezone.now()
            return delta.days
        return None


class TaskHistory(models.Model):
    """任务变更历史 — 用于审计和回溯。"""

    class Action(models.TextChoices):
        CREATED = 'CREATED', '创建'
        STATUS_CHANGE = 'STATUS_CHANGE', '状态变更'
        ASSIGNED = 'ASSIGNED', '分配'
        UPDATED = 'UPDATED', '更新'
        COMMENTED = 'COMMENTED', '评论'
        IMPORTED = 'IMPORTED', '导入'
        EXPORTED = 'EXPORTED', '导出'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history')
    action = models.CharField('操作类型', max_length=20, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='task_actions', verbose_name='操作人'
    )

    # 变更详情
    old_value = models.JSONField('变更前', default=dict, blank=True)
    new_value = models.JSONField('变更后', default=dict, blank=True)
    diff = models.JSONField('差异', default=dict, blank=True)
    note = models.TextField('备注', blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'task_history'
        verbose_name = '任务历史'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.task.task_no} - {self.get_action_display()} @ {self.created_at}'


class TaskComment(models.Model):
    """任务评论。"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='task_comments', verbose_name='评论人'
    )
    content = models.TextField('评论内容')
    is_internal = models.BooleanField('内部评论(仅组长/管理员可见)', default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'task_comments'
        verbose_name = '任务评论'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.author.username} on {self.task.task_no}'


class TaskParticipant(models.Model):
    """任务参与者 — 统一承载派发/揭榜两种模式。"""

    class Role(models.TextChoices):
        CHIEF_LEAD = 'CHIEF_LEAD', '总牵头人'
        GROUP_LEAD = 'GROUP_LEAD', '小组牵头'
        PARTICIPANT = 'PARTICIPANT', '参与'
        CLAIMER = 'CLAIMER', '领取人'

    class Status(models.TextChoices):
        INVITED = 'INVITED', '已邀请'
        ACCEPTED = 'ACCEPTED', '已接受'
        COMPLETED = 'COMPLETED', '已完成'
        CANCELLED = 'CANCELLED', '已取消'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='task_participations', verbose_name='参与者'
    )
    role = models.CharField('角色', max_length=20, choices=Role.choices)
    points = models.IntegerField('该角色积分')
    status = models.CharField(
        '状态', max_length=20, choices=Status.choices, default=Status.INVITED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)

    class Meta:
        db_table = 'task_participants'
        verbose_name = '任务参与者'
        verbose_name_plural = verbose_name
        unique_together = ('task', 'user')
        indexes = [
            models.Index(fields=['task', 'role']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.task.task_no} ({self.get_role_display()})'
