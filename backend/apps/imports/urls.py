from django.urls import path
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.exceptions import PermissionDenied

from common.permissions import IsGroupLeader
from .models import ImportSession


class ImportUploadView(APIView):
    """阶段1：上传文件并解析预览。仅组长及以上可导入。"""
    permission_classes = [IsAuthenticated, IsGroupLeader]
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'error': '请选择文件'}, status=status.HTTP_400_BAD_REQUEST)

        ext = uploaded.name.rsplit('.', 1)[-1].lower() if '.' in uploaded.name else ''
        if ext not in ('xlsx', 'xls', 'csv', 'wps'):
            return Response({'error': '仅支持 xlsx/xls/csv/wps 格式'}, status=status.HTTP_400_BAD_REQUEST)

        session = ImportSession.objects.create(
            uploader=request.user,
            file=uploaded,
            original_name=uploaded.name,
            file_format=ext,
        )

        # 触发解析
        from .services.import_parser import parse_import_file
        try:
            result = parse_import_file(session)
            session.status = ImportSession.Status.PREVIEW
            session.total_rows = result['total_rows']
            session.valid_rows = result['valid_rows']
            session.error_rows = result['error_rows']
            session.preview_data = result['preview_data']
            session.column_mapping = result['column_mapping']
            session.errors = result['errors']
            session.save()
        except Exception as e:
            session.status = ImportSession.Status.FAILED
            session.errors = [{'row': 0, 'message': str(e)}]
            session.save()
            return Response(
                {'error': f'文件解析失败: {e}', 'session_id': str(session.id)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response({
            'session_id': str(session.id),
            'status': session.status,
            'total_rows': session.total_rows,
            'valid_rows': session.valid_rows,
            'error_rows': session.error_rows,
            'preview_data': session.preview_data[:10],
            'column_mapping': session.column_mapping,
            'errors': session.errors[:20],
        })


class ImportConfirmView(APIView):
    """阶段2：确认导入。校验上传者或超管。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            session = ImportSession.objects.get(pk=pk)
        except ImportSession.DoesNotExist:
            return Response({'error': '导入会话不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 权限检查：上传者本人或超管
        if session.uploader != request.user and not request.user.is_superuser:
            raise PermissionDenied('您无权确认此导入')

        if session.status != ImportSession.Status.PREVIEW:
            return Response({'error': f'当前状态不允许确认: {session.status}'}, status=status.HTTP_400_BAD_REQUEST)

        session.status = ImportSession.Status.CONFIRMING
        session.save()

        from .services.import_executor import execute_import
        try:
            result = execute_import(session, request.user)
            session.status = ImportSession.Status.COMPLETED
            session.imported_task_ids = result['task_ids']
            session.save()
            return Response({
                'imported_count': len(result['task_ids']),
                'task_ids': result['task_ids'],
            })
        except Exception as e:
            session.status = ImportSession.Status.FAILED
            session.errors.append({'row': 0, 'message': str(e)})
            session.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImportSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            session = ImportSession.objects.get(pk=pk)
        except ImportSession.DoesNotExist:
            return Response({'error': '导入会话不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 权限检查：上传者、组长及以上可看
        if (session.uploader != request.user
                and not request.user.is_superuser
                and request.user.role not in ('LEADER', 'ADMIN')):
            raise PermissionDenied('您无权查看此导入会话')

        return Response({
            'id': str(session.id),
            'original_name': session.original_name,
            'file_format': session.file_format,
            'status': session.status,
            'total_rows': session.total_rows,
            'valid_rows': session.valid_rows,
            'error_rows': session.error_rows,
            'errors': session.errors,
            'created_at': session.created_at.isoformat(),
        })


class ImportHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = ImportSession.objects.filter(
            uploader=request.user
        ).order_by('-created_at')[:20]

        data = [{
            'id': str(s.id),
            'original_name': s.original_name,
            'status': s.status,
            'total_rows': s.total_rows,
            'valid_rows': s.valid_rows,
            'created_at': s.created_at.isoformat(),
        } for s in sessions]

        return Response(data)


urlpatterns = [
    path('upload/', ImportUploadView.as_view(), name='import-upload'),
    path('<uuid:pk>/confirm/', ImportConfirmView.as_view(), name='import-confirm'),
    path('<uuid:pk>/', ImportSessionDetailView.as_view(), name='import-detail'),
    path('', ImportHistoryView.as_view(), name='import-history'),
]
