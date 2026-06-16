import uuid

from django.conf import settings
from django.db import models


class PointRule(models.Model):
    """积分规则配置。"""

    class Action(models.TextChoices):
        TASK_COMPLETED = 'TASK_COMPLETED', '完成任务'
        TASK_ASSIGNED = 'TASK_ASSIGNED', '被分配任务'
        TASK_CLAIMED = 'TASK_CLAIMED', '领取任务'

    class Mode(models.TextChoices):
        FIXED = 'FIXED', '固定积分'
        PRIORITY_BASED = 'PRIORITY_BASED', '按优先级'
        CUSTOM = 'CUSTOM', '自定义'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField('动作类型', max_length=20, choices=Action.choices, unique=True)
    mode = models.CharField('分配模式', max_length=20, choices=Mode.choices, default=Mode.FIXED)
    base_points = models.IntegerField('基础积分', default=10)
    priority_multiplier = models.FloatField('优先级倍率', default=1.0,
        help_text='PRIORITY_BASED 模式下：URGENT=4x, HIGH=3x, MEDIUM=2x, LOW=1x')
    is_active = models.BooleanField('启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'point_rules'
        verbose_name = '积分规则'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.get_action_display()} - {self.get_mode_display()} ({self.base_points}pts)'


class PointTransaction(models.Model):
    """积分流水。"""

    class Type(models.TextChoices):
        EARN = 'EARN', '获得'
        DEDUCT = 'DEDUCT', '扣除'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='point_transactions', verbose_name='用户'
    )
    type = models.CharField('类型', max_length=10, choices=Type.choices)
    points = models.IntegerField('积分变动')
    balance_after = models.IntegerField('变动后余额')
    reason = models.CharField('原因', max_length=200, blank=True, default='')
    task = models.ForeignKey(
        'tasks.Task', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='point_transactions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'point_transactions'
        verbose_name = '积分流水'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} {self.type} {self.points}pts'


class PointBalance(models.Model):
    """用户积分余额。"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='point_balance', verbose_name='用户'
    )
    total_earned = models.IntegerField('累计获得', default=0)
    total_spent = models.IntegerField('累计消费', default=0)
    balance = models.IntegerField('当前余额', default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'point_balances'
        verbose_name = '积分余额'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.user.username}: {self.balance}pts'
