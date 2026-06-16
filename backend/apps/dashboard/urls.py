from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from .services import DashboardService


class SummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = DashboardService.get_summary(request.user)
        return Response(data)


class StatusDistributionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(DashboardService.get_status_distribution(request.user))


class PriorityDistributionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(DashboardService.get_priority_distribution(request.user))


class WeeklyTrendView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        weeks = int(request.query_params.get('weeks', 8))
        return Response(DashboardService.get_weekly_trend(weeks, request.user))


class TeamWorkloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(DashboardService.get_team_workload(request.user))


class OverdueTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        return Response(DashboardService.get_overdue_tasks(limit, request.user))


urlpatterns = [
    path('summary/', SummaryView.as_view(), name='dashboard-summary'),
    path('status/', StatusDistributionView.as_view(), name='dashboard-status'),
    path('priority/', PriorityDistributionView.as_view(), name='dashboard-priority'),
    path('trend/', WeeklyTrendView.as_view(), name='dashboard-trend'),
    path('workload/', TeamWorkloadView.as_view(), name='dashboard-workload'),
    path('overdue/', OverdueTasksView.as_view(), name='dashboard-overdue'),
]
