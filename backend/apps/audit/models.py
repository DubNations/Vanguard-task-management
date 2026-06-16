import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """全局审计日志。"""

    class Action(models.TextChoices):
        LOGIN = 'LOGIN', '登录'
        LOGOUT = 'LOGOUT', '登出'
        CREATE = 'CREATE', '创建'
        UPDATE = 'UPDATE', '修改'
        DELETE = 'DELETE', '删除'
        EXPORT = 'EXPORT', '导出'
        IMPORT = 'IMPORT', '导入'
        ADMIN = 'ADMIN', '管理操作'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='audit_logs', verbose_name='操作人'
    )
    action = models.CharField('操作类型', max_length=20, choices=Action.choices, db_index=True)
    resource_type = models.CharField('资源类型', max_length=50, db_index=True)
    resource_id = models.CharField('资源ID', max_length=50, blank=True, default='')
    description = models.TextField('描述', blank=True, default='')
    detail = models.JSONField('详情', default=dict, blank=True)

    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    user_agent = models.CharField('User Agent', max_length=300, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        verbose_name = '审计日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', 'resource_type']),
        ]

    def __str__(self):
        return f'{self.user} {self.action} {self.resource_type} @ {self.created_at}'
