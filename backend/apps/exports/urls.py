from django.urls import path
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from urllib.parse import quote

from common.permissions import IsGroupLeader
from .models import ExportJob


class ExportCreateView(APIView):
    """创建导出任务。仅组长及以上可导出。"""
    permission_classes = [IsAuthenticated, IsGroupLeader]

    def post(self, request):
        fmt = request.data.get('format', 'EXCEL')
        if fmt not in ('EXCEL', 'PDF', 'CSV'):
            return Response({'error': '不支持的格式'}, status=status.HTTP_400_BAD_REQUEST)

        job = ExportJob.objects.create(
            requester=request.user,
            format=fmt,
            filters=request.data.get('filters', {}),
        )

        from .services.export_generator import generate_export
        try:
            result = generate_export(job)
            job.status = ExportJob.Status.COMPLETED
            job.file = result['file']
            job.file_name = result['file_name']
            job.row_count = result['row_count']
            from django.utils import timezone
            job.completed_at = timezone.now()
            job.save()
        except Exception as e:
            job.status = ExportJob.Status.FAILED
            job.error_message = str(e)
            job.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'id': str(job.id),
            'file_name': job.file_name,
            'row_count': job.row_count,
            'download_url': f'/api/v1/exports/{job.id}/download/',
        })


class ExportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from django.http import FileResponse
        try:
            job = ExportJob.objects.get(pk=pk, status=ExportJob.Status.COMPLETED)
        except ExportJob.DoesNotExist:
            return Response({'error': '导出文件不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 权限检查：请求者本人或超管
        if job.requester != request.user and not request.user.is_superuser:
            raise PermissionDenied('您无权下载此导出文件')

        response = FileResponse(job.file.open('rb'))
        encoded_name = quote(job.file_name)
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_name}"
        return response


class ExportHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        jobs = ExportJob.objects.filter(
            requester=request.user
        ).order_by('-created_at')[:20]

        data = [{
            'id': str(j.id),
            'format': j.format,
            'status': j.status,
            'file_name': j.file_name,
            'row_count': j.row_count,
            'created_at': j.created_at.isoformat(),
        } for j in jobs]

        return Response(data)


urlpatterns = [
    path('', ExportHistoryView.as_view(), name='export-history'),
    path('create/', ExportCreateView.as_view(), name='export-create'),
    path('<uuid:pk>/download/', ExportDownloadView.as_view(), name='export-download'),
]
