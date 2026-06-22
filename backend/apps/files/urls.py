import logging

try:
    import magic
    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    MAGIC_AVAILABLE = False

from django.urls import path
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.exceptions import PermissionDenied
from urllib.parse import quote

from .models import TaskFile

logger = logging.getLogger(__name__)

# 危险扩展名黑名单
DANGEROUS_EXTENSIONS = {'.exe', '.bat', '.sh', '.php', '.ps1', '.cmd', '.vbs', '.msi'}

# 允许的 MIME 类型白名单
ALLOWED_MIMETYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/zip',
    'application/x-rar-compressed',
    'application/x-7z-compressed',
    'text/plain',
    'text/csv',
    'text/markdown',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/svg+xml',
}


def _check_task_permission(task, user):
    """校验用户是否有权操作该任务的文件（含参与者）。"""
    if user.is_superuser:
        return True
    if user.role in ('LEADER', 'ADMIN'):
        return True
    if task.assignee == user or task.creator == user:
        return True
    # 参与者可操作关联任务的文件
    if task.participants.filter(user=user).exists():
        return True
    return False


class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, task_pk):
        from apps.tasks.models import Task
        try:
            task = Task.objects.get(pk=task_pk)
        except Task.DoesNotExist:
            return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 权限检查
        if not _check_task_permission(task, request.user):
            raise PermissionDenied('您无权操作此任务的文件')

        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'error': '请选择文件'}, status=status.HTTP_400_BAD_REQUEST)

        # 危险扩展名检查
        ext = '.' + uploaded.name.rsplit('.', 1)[-1].lower() if '.' in uploaded.name else ''
        if ext in DANGEROUS_EXTENSIONS:
            return Response({'error': f'不允许上传 {ext} 格式的文件'}, status=status.HTTP_400_BAD_REQUEST)

        # MIME 类型检测（读取文件头部，不依赖扩展名）
        if MAGIC_AVAILABLE:
            header = uploaded.read(2048)
            uploaded.seek(0)
            detected_mime = magic.from_buffer(header, mime=True)
            if detected_mime not in ALLOWED_MIMETYPES:
                logger.warning('MIME 类型被拒绝: file=%s detected=%s user=%s',
                               uploaded.name, detected_mime, request.user.pk)
                return Response(
                    {'error': f'不允许上传该类型的文件 ({detected_mime})'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # 50MB limit
        if uploaded.size > 50 * 1024 * 1024:
            return Response({'error': '文件大小不能超过50MB'}, status=status.HTTP_400_BAD_REQUEST)

        sha256 = TaskFile.compute_sha256(uploaded)
        file_type = TaskFile.detect_file_type(uploaded.name, uploaded.content_type or '')

        task_file = TaskFile.objects.create(
            task=task,
            uploader=request.user,
            file=uploaded,
            original_name=uploaded.name,
            file_type=file_type,
            file_size=uploaded.size,
            mime_type=uploaded.content_type or '',
            sha256=sha256,
        )

        return Response({
            'id': str(task_file.id),
            'original_name': task_file.original_name,
            'file_type': task_file.file_type,
            'file_size': task_file.file_size,
            'sha256': task_file.sha256,
        }, status=status.HTTP_201_CREATED)


class FileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_pk):
        from apps.tasks.models import Task
        try:
            task = Task.objects.get(pk=task_pk)
        except Task.DoesNotExist:
            return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not _check_task_permission(task, request.user):
            raise PermissionDenied('您无权查看此任务的文件')

        files = TaskFile.objects.filter(task_id=task_pk).order_by('-created_at')
        data = [{
            'id': str(f.id),
            'original_name': f.original_name,
            'file_type': f.file_type,
            'file_size': f.file_size,
            'uploader': f.uploader.username if f.uploader else '',
            'download_count': f.download_count,
            'created_at': f.created_at.isoformat(),
            'download_url': f'/api/v1/files/download/{f.id}/',
        } for f in files]
        return Response(data)


class FileDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import FileResponse
        try:
            task_file = TaskFile.objects.get(pk=pk)
        except TaskFile.DoesNotExist:
            return Response({'error': '文件不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 权限检查
        if not _check_task_permission(task_file.task, request.user):
            raise PermissionDenied('您无权下载此文件')

        from django.db.models import F
        TaskFile.objects.filter(pk=pk).update(download_count=F('download_count') + 1)

        response = FileResponse(task_file.file.open('rb'))
        # 使用 urllib.parse.quote 防止 HTTP 头注入
        encoded_name = quote(task_file.original_name)
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_name}"
        return response


class FileDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            task_file = TaskFile.objects.get(pk=pk)
        except TaskFile.DoesNotExist:
            return Response({'error': '文件不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 权限检查：上传者本人、组长及以上、超管
        if (task_file.uploader != request.user
                and not request.user.is_superuser
                and request.user.role not in ('LEADER', 'ADMIN')):
            raise PermissionDenied('无权删除此文件')

        task_file.file.delete()
        task_file.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


urlpatterns = [
    path('upload/<uuid:task_pk>/', FileUploadView.as_view(), name='file-upload'),
    path('list/<uuid:task_pk>/', FileListView.as_view(), name='file-list'),
    path('download/<uuid:pk>/', FileDownloadView.as_view(), name='file-download'),
    path('<uuid:pk>/', FileDeleteView.as_view(), name='file-delete'),
]
