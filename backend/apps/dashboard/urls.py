import logging
from django.core.cache import cache
from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from .services import DashboardService, DASHBOARD_CACHE_TTL

logger = logging.getLogger('apps')


class MemberDashboardView(APIView):
    """MEMBER 个人工作台。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # LEADER/ADMIN 走 leader 端点，这里也兼容（降级为个人视角）
        cache_key = f'dashboard:member:{user.id}'
        data = cache.get(cache_key)
        if data is None:
            data = DashboardService.get_member_dashboard(user)
            cache.set(cache_key, data, timeout=DASHBOARD_CACHE_TTL)
        return Response(data)


class LeaderDashboardView(APIView):
    """LEADER/ADMIN 团队管理台。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # 非 LEADER/ADMIN 降级为 member 视图
        if not user.is_superuser and user.role not in ('LEADER', 'ADMIN'):
            return MemberDashboardView.as_view()(request)
        cache_key = f'dashboard:leader:{user.id}'
        data = cache.get(cache_key)
        if data is None:
            data = DashboardService.get_leader_dashboard(user)
            cache.set(cache_key, data, timeout=DASHBOARD_CACHE_TTL)
        return Response(data)


class DeprecatedDashboardView(APIView):
    """旧端点兼容层：返回空数据 + 警告日志，避免前端缓存导致 404。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.warning(
            'Deprecated dashboard endpoint called: %s by user %s',
            request.path, request.user,
        )
        return Response({})


urlpatterns = [
    # 新端点
    path('member/', MemberDashboardView.as_view(), name='dashboard-member'),
    path('leader/', LeaderDashboardView.as_view(), name='dashboard-leader'),
    # 旧端点（废弃兼容）
    path('summary/', DeprecatedDashboardView.as_view(), name='dashboard-summary-deprecated'),
    path('status/', DeprecatedDashboardView.as_view(), name='dashboard-status-deprecated'),
    path('priority/', DeprecatedDashboardView.as_view(), name='dashboard-priority-deprecated'),
    path('trend/', DeprecatedDashboardView.as_view(), name='dashboard-trend-deprecated'),
    path('workload/', DeprecatedDashboardView.as_view(), name='dashboard-workload-deprecated'),
    path('overdue/', DeprecatedDashboardView.as_view(), name='dashboard-overdue-deprecated'),
]
