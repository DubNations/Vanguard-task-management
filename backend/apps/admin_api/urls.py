from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from common.permissions import IsGroupLeader, IsSuperAdmin
from apps.audit.models import AuditLog


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated, IsGroupLeader]

    def get(self, request):
        qs = AuditLog.objects.select_related('user').all()

        # Filters
        action = request.query_params.get('action')
        if action:
            qs = qs.filter(action=action)
        resource = request.query_params.get('resource_type')
        if resource:
            qs = qs.filter(resource_type=resource)
        user_id = request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)

        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        total = qs.count()
        qs = qs[(page - 1) * page_size:page * page_size]

        results = []
        for log in qs:
            results.append({
                'id': str(log.id),
                'user': log.user.username if log.user else 'system',
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'description': log.description,
                'ip_address': log.ip_address,
                'created_at': log.created_at.isoformat(),
            })

        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': results,
        })


class SystemStatusView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        from django.conf import settings
        from apps.tasks.models import Task
        from apps.accounts.models import User

        return Response({
            'django_version': '5.0',
            'debug': settings.DEBUG,
            'database': settings.DATABASES['default']['ENGINE'],
            'task_count': Task.objects.count(),
            'user_count': User.objects.filter(is_active=True).count(),
            'time_zone': settings.TIME_ZONE,
        })


urlpatterns = [
    path('audit/', AuditLogListView.as_view(), name='admin-audit'),
    path('status/', SystemStatusView.as_view(), name='admin-status'),
]
