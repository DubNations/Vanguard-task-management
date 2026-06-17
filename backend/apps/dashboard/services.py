from django.db import models
from django.db.models import Count, Q, Avg, F
from django.utils import timezone
from datetime import timedelta


class DashboardService:
    """仪表盘数据聚合。"""

    @staticmethod
    def _filter_by_user(qs, user):
        """根据用户角色过滤查询集：非 superuser/leader/admin 只统计自己的任务。"""
        if user and not user.is_superuser and user.role not in ('LEADER', 'ADMIN'):
            qs = qs.filter(Q(assignee=user) | Q(creator=user))
        return qs

    @staticmethod
    def get_summary(user=None):
        """首页统计概览。"""
        from apps.tasks.models import Task

        qs = Task.objects.all()
        qs = DashboardService._filter_by_user(qs, user)

        now = timezone.now()
        stats = qs.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='PENDING')),
            in_progress=Count('id', filter=Q(status='IN_PROGRESS')),
            in_review=Count('id', filter=Q(status='IN_REVIEW')),
            completed=Count('id', filter=Q(status='COMPLETED')),
            overdue=Count('id', filter=Q(deadline__lt=now) & ~Q(status__in=['COMPLETED', 'CANCELLED'])),
            completed_today=Count('id', filter=Q(status='COMPLETED', completed_at__date=now.date())),
            created_this_week=Count('id', filter=Q(created_at__gte=now - timedelta(days=7))),
        )
        return stats

    @staticmethod
    def get_status_distribution(user=None):
        """任务状态分布(饼图)。"""
        from apps.tasks.models import Task
        qs = Task.objects.all()
        qs = DashboardService._filter_by_user(qs, user)
        return list(
            qs.values('status')
            .annotate(count=Count('id'))
            .order_by('status')
        )

    @staticmethod
    def get_priority_distribution(user=None):
        """优先级分布(饼图)。"""
        from apps.tasks.models import Task
        qs = Task.objects.all()
        qs = DashboardService._filter_by_user(qs, user)
        return list(
            qs.values('priority')
            .annotate(count=Count('id'))
            .order_by('priority')
        )

    @staticmethod
    def get_weekly_trend(weeks=8, user=None):
        """周趋势(折线图)。"""
        from apps.tasks.models import Task
        weeks = min(int(weeks), 52)  # 上限校验
        now = timezone.now()
        qs = Task.objects.all()
        qs = DashboardService._filter_by_user(qs, user)
        result = []
        for i in range(weeks - 1, -1, -1):
            week_start = now - timedelta(weeks=i + 1)
            week_end = now - timedelta(weeks=i)
            label = week_start.strftime('%m/%d')
            created = qs.filter(
                created_at__gte=week_start, created_at__lt=week_end
            ).count()
            completed = qs.filter(
                completed_at__gte=week_start, completed_at__lt=week_end
            ).count()
            result.append({
                'week': label,
                'created': created,
                'completed': completed,
            })
        return result

    @staticmethod
    def get_team_workload(user=None):
        """团队工作量分布(柱状图)。"""
        from apps.tasks.models import Task
        qs = Task.objects.filter(assignee__isnull=False)
        qs = DashboardService._filter_by_user(qs, user)
        return list(
            qs.values(
                team_name=F('assignee__team__name')
            ).annotate(
                total=Count('id'),
                completed=Count('id', filter=Q(status='COMPLETED')),
            ).order_by('-total')
        )

    @staticmethod
    def get_overdue_tasks(limit=10, user=None):
        """逾期任务列表。"""
        from apps.tasks.models import Task
        limit = min(int(limit), 100)  # 上限校验
        now = timezone.now()
        qs = Task.objects.filter(
            deadline__lt=now
        ).exclude(
            status__in=['COMPLETED', 'CANCELLED']
        )
        qs = DashboardService._filter_by_user(qs, user)
        return list(
            qs.select_related(
                'assignee', 'creator'
            ).order_by('deadline')[:limit].values(
                'id', 'task_no', 'title', 'status', 'priority',
                'deadline', 'assignee__username', 'assignee__email',
            )
        )
