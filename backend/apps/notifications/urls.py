from django.urls import path
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import Notification


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread_only = request.query_params.get('unread', 'false') == 'true'
        qs = Notification.objects.filter(recipient=request.user)
        if unread_only:
            qs = qs.filter(is_read=False)

        notifications = qs.order_by('-created_at')[:50]
        data = [{
            'id': str(n.id),
            'type': n.type,
            'title': n.title,
            'content': n.content,
            'is_read': n.is_read,
            'task_id': str(n.task_id) if n.task_id else None,
            'actor': n.actor.username if n.actor else '',
            'created_at': n.created_at.isoformat(),
        } for n in notifications]

        unread_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()

        return Response({
            'unread_count': unread_count,
            'notifications': data,
        })


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            n = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return Response({'error': '通知不存在'}, status=status.HTTP_404_NOT_FOUND)

        n.mark_read()
        return Response({'detail': '已标记为已读'})


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        now = timezone.now()
        Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True, read_at=now)
        return Response({'detail': '全部标记为已读'})


urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('<uuid:pk>/read/', NotificationMarkReadView.as_view(), name='notification-read'),
    path('mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification-mark-all'),
]
