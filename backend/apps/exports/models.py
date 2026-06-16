import uuid

from django.conf import settings
from django.db import models


class ExportJob(models.Model):
    """导出任务。"""

    class Format(models.TextChoices):
        EXCEL = 'EXCEL', 'Excel'
        PDF = 'PDF', 'PDF'
        CSV = 'CSV', 'CSV'

    class Status(models.TextChoices):
        PENDING = 'PENDING', '等待中'
        GENERATING = 'GENERATING', '生成中'
        COMPLETED = 'COMPLETED', '已完成'
        FAILED = 'FAILED', '失败'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='export_jobs', verbose_name='请求人'
    )
    format = models.CharField('格式', max_length=10, choices=Format.choices)
    status = models.CharField(
        '状态', max_length=20, choices=Status.choices, default=Status.PENDING
    )

    filters = models.JSONField('筛选条件', default=dict, blank=True)
    file = models.FileField('导出文件', upload_to='exports/%Y/%m/', blank=True)
    file_name = models.CharField('文件名', max_length=255, blank=True, default='')
    row_count = models.PositiveIntegerField('行数', default=0)
    error_message = models.TextField('错误信息', blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'export_jobs'
        verbose_name = '导出任务'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.file_name} ({self.status})'
