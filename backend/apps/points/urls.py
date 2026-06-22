from django.urls import path
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from common.permissions import IsSuperAdmin
from .models import PointRule
from .services.point_service import PointService


class PointBalanceView(APIView):
    """当前用户积分余额。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PointService.get_balance(request.user))


class PointTransactionListView(APIView):
    """积分流水（分页）。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        return Response(PointService.get_transactions(request.user, page, page_size))


class PointLeaderboardView(APIView):
    """排行榜。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.query_params.get('period', 'all')
        limit = min(int(request.query_params.get('limit', 20)), 100)
        if period not in ('week', 'month', 'all'):
            period = 'all'
        return Response(PointService.get_leaderboard(period, limit))


class PointStatsView(APIView):
    """个人积分统计。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PointService.get_stats(request.user))


class PointRuleListView(APIView):
    """积分规则 — 查看/配置。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rules = PointRule.objects.all().order_by('action')
        data = [{
            'id': str(r.id),
            'action': r.action,
            'action_display': r.get_action_display(),
            'mode': r.mode,
            'mode_display': r.get_mode_display(),
            'base_points': r.base_points,
            'priority_multiplier': r.priority_multiplier,
            'is_active': r.is_active,
        } for r in rules]
        return Response(data)

    def post(self, request):
        """仅超管可配置规则。"""
        if not (request.user.is_superuser or request.user.role == 'ADMIN'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('仅管理员可配置积分规则')

        action = request.data.get('action')
        if not action:
            return Response({'error': 'action 字段必填'}, status=status.HTTP_400_BAD_REQUEST)

        rule, created = PointRule.objects.get_or_create(
            action=action,
            defaults={
                'mode': request.data.get('mode', 'FIXED'),
                'base_points': request.data.get('base_points', 10),
                'priority_multiplier': request.data.get('priority_multiplier', 1.0),
            }
        )
        if not created:
            for field in ['mode', 'base_points', 'priority_multiplier', 'is_active']:
                if field in request.data:
                    setattr(rule, field, request.data[field])
            rule.save()

        return Response({
            'id': str(rule.id),
            'action': rule.action,
            'mode': rule.mode,
            'base_points': rule.base_points,
            'priority_multiplier': rule.priority_multiplier,
            'is_active': rule.is_active,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class PointRuleDetailView(APIView):
    """单条积分规则 — PATCH/DELETE。"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def patch(self, request, pk):
        try:
            rule = PointRule.objects.get(pk=pk)
        except PointRule.DoesNotExist:
            return Response({'error': '规则不存在'}, status=status.HTTP_404_NOT_FOUND)

        for field in ['action', 'mode', 'base_points', 'priority_multiplier', 'is_active']:
            if field in request.data:
                setattr(rule, field, request.data[field])
        rule.save()

        return Response({
            'id': str(rule.id),
            'action': rule.action,
            'mode': rule.mode,
            'base_points': rule.base_points,
            'priority_multiplier': rule.priority_multiplier,
            'is_active': rule.is_active,
        })

    def delete(self, request, pk):
        try:
            rule = PointRule.objects.get(pk=pk)
        except PointRule.DoesNotExist:
            return Response({'error': '规则不存在'}, status=status.HTTP_404_NOT_FOUND)
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


urlpatterns = [
    path('balance/', PointBalanceView.as_view(), name='point-balance'),
    path('transactions/', PointTransactionListView.as_view(), name='point-transactions'),
    path('leaderboard/', PointLeaderboardView.as_view(), name='point-leaderboard'),
    path('my-stats/', PointStatsView.as_view(), name='point-stats'),
    path('rules/', PointRuleListView.as_view(), name='point-rules'),
    path('rules/<uuid:pk>/', PointRuleDetailView.as_view(), name='point-rule-detail'),
]
