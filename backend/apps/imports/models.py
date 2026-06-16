import uuid

from django.conf import settings
from django.db import models


class ImportSession(models.Model):
    """导入会话 — 两阶段导入(预览+确认)。"""

    class Status(models.TextChoices):
        PENDING = 'PENDING', '待解析'
        PARSING = 'PARSING', '解析中'
        PREVIEW = 'PREVIEW', '待确认'
        CONFIRMING = 'CONFIRMING', '导入中'
        COMPLETED = 'COMPLETED', '已完成'
        FAILED = 'FAILED', '失败'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='import_sessions', verbose_name='上传者'
    )
    file = models.FileField('导入文件', upload_to='imports/%Y/%m/')
    original_name = models.CharField('原始文件名', max_length=255)
    file_format = models.CharField('文件格式', max_length=10)  # xlsx, csv, wps

    status = models.CharField(
        '状态', max_length=20, choices=Status.choices, default=Status.PENDING
    )

    # 解析结果
    total_rows = models.PositiveIntegerField('总行数', default=0)
    valid_rows = models.PositiveIntegerField('有效行数', default=0)
    skipped_rows = models.PositiveIntegerField('跳过行数', default=0)
    error_rows = models.PositiveIntegerField('错误行数', default=0)

    preview_data = models.JSONField('预览数据', default=list, blank=True)
    column_mapping = models.JSONField('列映射', default=dict, blank=True)
    errors = models.JSONField('错误详情', default=list, blank=True)

    # 结果
    imported_task_ids = models.JSONField('已导入任务ID', default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'import_sessions'
        verbose_name = '导入会话'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.original_name} ({self.status})'
