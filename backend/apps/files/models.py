import uuid
import hashlib

from django.conf import settings
from django.db import models


class TaskFile(models.Model):
    """任务附件。"""

    class FileType(models.TextChoices):
        DOCUMENT = 'DOCUMENT', '文档'
        IMAGE = 'IMAGE', '图片'
        EXCEL = 'EXCEL', '表格'
        WPS = 'WPS', 'WPS文件'
        PDF = 'PDF', 'PDF文件'
        OTHER = 'OTHER', '其他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        'tasks.Task', on_delete=models.CASCADE,
        related_name='files', verbose_name='关联任务'
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='uploaded_files', verbose_name='上传者'
    )
    file = models.FileField('文件', upload_to='task_files/%Y/%m/')
    original_name = models.CharField('原始文件名', max_length=255)
    file_type = models.CharField('文件类型', max_length=20, choices=FileType.choices, default=FileType.OTHER)
    file_size = models.PositiveIntegerField('文件大小(bytes)', default=0)
    mime_type = models.CharField('MIME类型', max_length=100, blank=True, default='')
    sha256 = models.CharField('SHA256', max_length=64, blank=True, default='', db_index=True)
    download_count = models.PositiveIntegerField('下载次数', default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'task_files'
        verbose_name = '任务附件'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.original_name} ({self.task.task_no})'

    @staticmethod
    def compute_sha256(file_obj):
        h = hashlib.sha256()
        for chunk in file_obj.chunks():
            h.update(chunk)
        file_obj.seek(0)
        return h.hexdigest()

    @staticmethod
    def detect_file_type(filename, mime_type=''):
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        mapping = {
            'DOCUMENT': ['doc', 'docx', 'txt', 'rtf', 'odt'],
            'IMAGE': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'],
            'EXCEL': ['xls', 'xlsx', 'csv', 'ods'],
            'WPS': ['wps', 'et', 'dps'],
            'PDF': ['pdf'],
        }
        for ftype, extensions in mapping.items():
            if ext in extensions:
                return ftype
        return 'OTHER'
