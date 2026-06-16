import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """站内通知。"""

    class Type(models.TextChoices):
        TASK_ASSIGNED = 'TASK_ASSIGNED', '任务分配'
        TASK_STATUS = 'TASK_STATUS', '状态变更'
        TASK_DEADLINE = 'TASK_DEADLINE', '即将到期'
        TASK_OVERDUE = 'TASK_OVERDUE', '已逾期'
        TASK_COMMENT = 'TASK_COMMENT', '新评论'
        SYSTEM = 'SYSTEM', '系统通知'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications', verbose_name='接收人'
    )
    type = models.CharField('类型', max_length=20, choices=Type.choices)
    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容', blank=True, default='')

    # 关联
    task = models.ForeignKey(
        'tasks.Task', on_delete=models.CASCADE, null=True, blank=True,
        related_name='notifications'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='triggered_notifications', verbose_name='触发人'
    )

    is_read = models.BooleanField('已读', default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    email_sent = models.BooleanField('邮件已发送', default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = '通知'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f'{self.title} -> {self.recipient.username}'

    def mark_read(self):
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
