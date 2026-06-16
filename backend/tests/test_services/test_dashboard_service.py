"""
DashboardService 单元测试。
"""
import pytest
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
class TestDashboardService:
    """测试仪表盘服务层。"""

    # ------------------------------------------------------------------
    # get_summary
    # ------------------------------------------------------------------
    def test_get_summary_empty(self):
        """空数据时所有统计值为 0。"""
        from apps.dashboard.services import DashboardService
        summary = DashboardService.get_summary()
        assert summary['total'] == 0
        assert summary['pending'] == 0
        assert summary['in_progress'] == 0
        assert summary['in_review'] == 0
        assert summary['completed'] == 0
        assert summary['overdue'] == 0
        assert summary['completed_today'] == 0
        assert summary['created_this_week'] == 0

    def test_get_summary_admin_sees_all(self, admin_user, regular_user):
        """admin(superuser) 看全局统计。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        Task.objects.create(task_no='T-001', title='A', creator=admin_user, status='PENDING')
        Task.objects.create(task_no='T-002', title='B', creator=regular_user, status='IN_PROGRESS')

        summary = DashboardService.get_summary(user=admin_user)
        assert summary['total'] == 2
        assert summary['pending'] == 1
        assert summary['in_progress'] == 1

    def test_get_summary_member_sees_own(self, admin_user, regular_user):
        """普通成员只看自己相关(creator 或 assignee)的任务。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        Task.objects.create(task_no='T-010', title='Mine', creator=regular_user, status='PENDING')
        Task.objects.create(task_no='T-011', title='Assigned', creator=admin_user,
                            assignee=regular_user, status='IN_PROGRESS')
        Task.objects.create(task_no='T-012', title='Other', creator=admin_user, status='PENDING')

        summary = DashboardService.get_summary(user=regular_user)
        assert summary['total'] == 2
        assert summary['pending'] == 1
        assert summary['in_progress'] == 1

    def test_get_summary_overdue_excludes_completed(self, admin_user):
        """overdue 统计排除 COMPLETED/CANCELLED 状态。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        past = timezone.now() - timedelta(days=1)
        Task.objects.create(task_no='T-020', title='Overdue', creator=admin_user,
                            status='PENDING', deadline=past)
        Task.objects.create(task_no='T-021', title='Done', creator=admin_user,
                            status='COMPLETED', deadline=past)
        Task.objects.create(task_no='T-022', title='Cancelled', creator=admin_user,
                            status='CANCELLED', deadline=past)

        summary = DashboardService.get_summary(user=admin_user)
        assert summary['overdue'] == 1

    # ------------------------------------------------------------------
    # get_status_distribution
    # ------------------------------------------------------------------
    def test_get_status_distribution(self, admin_user):
        """状态分布按 status 分组。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        Task.objects.create(task_no='T-030', title='A', creator=admin_user, status='PENDING')
        Task.objects.create(task_no='T-031', title='B', creator=admin_user, status='PENDING')
        Task.objects.create(task_no='T-032', title='C', creator=admin_user, status='COMPLETED')

        dist = DashboardService.get_status_distribution()
        dist_map = {item['status']: item['count'] for item in dist}
        assert dist_map['PENDING'] == 2
        assert dist_map['COMPLETED'] == 1

    # ------------------------------------------------------------------
    # get_priority_distribution
    # ------------------------------------------------------------------
    def test_get_priority_distribution(self, admin_user):
        """优先级分布按 priority 分组。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        Task.objects.create(task_no='T-040', title='A', creator=admin_user, priority='HIGH')
        Task.objects.create(task_no='T-041', title='B', creator=admin_user, priority='LOW')

        dist = DashboardService.get_priority_distribution()
        dist_map = {item['priority']: item['count'] for item in dist}
        assert dist_map['HIGH'] == 1
        assert dist_map['LOW'] == 1

    # ------------------------------------------------------------------
    # get_weekly_trend
    # ------------------------------------------------------------------
    def test_get_weekly_trend_default_8_weeks(self, admin_user):
        """默认返回 8 周数据。"""
        from apps.dashboard.services import DashboardService
        trend = DashboardService.get_weekly_trend()
        assert len(trend) == 8
        for item in trend:
            assert 'week' in item
            assert 'created' in item
            assert 'completed' in item

    def test_get_weekly_trend_custom_4_weeks(self, admin_user):
        """自定义 4 周返回 4 个数据点。"""
        from apps.dashboard.services import DashboardService
        trend = DashboardService.get_weekly_trend(weeks=4)
        assert len(trend) == 4

    # ------------------------------------------------------------------
    # get_team_workload
    # ------------------------------------------------------------------
    def test_get_team_workload(self, admin_user, regular_user, team):
        """按团队分组工作量。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        admin_user.team = team
        admin_user.save()

        Task.objects.create(task_no='T-060', title='A', creator=admin_user, assignee=admin_user, status='COMPLETED')
        Task.objects.create(task_no='T-061', title='B', creator=admin_user, assignee=admin_user, status='PENDING')
        Task.objects.create(task_no='T-062', title='C', creator=admin_user, assignee=regular_user, status='PENDING')

        workload = DashboardService.get_team_workload()
        assert len(workload) >= 1
        team_entry = next(w for w in workload if w['team_name'] == team.name)
        assert team_entry['total'] >= 2

    # ------------------------------------------------------------------
    # get_overdue_tasks
    # ------------------------------------------------------------------
    def test_get_overdue_tasks_limit(self, admin_user):
        """limit 参数生效。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        past = timezone.now() - timedelta(days=1)
        for i in range(5):
            Task.objects.create(
                task_no=f'T-OD-{i:04d}', title=f'Overdue{i}', creator=admin_user,
                status='PENDING', deadline=past - timedelta(hours=i),
            )

        result = DashboardService.get_overdue_tasks(limit=3)
        assert len(result) == 3

    def test_get_overdue_tasks_ordered_by_deadline(self, admin_user):
        """逾期任务按 deadline 升序排列。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        past1 = timezone.now() - timedelta(days=3)
        past2 = timezone.now() - timedelta(days=1)
        past3 = timezone.now() - timedelta(days=2)
        Task.objects.create(task_no='T-OD-0010', title='A', creator=admin_user, status='PENDING', deadline=past1)
        Task.objects.create(task_no='T-OD-0011', title='B', creator=admin_user, status='PENDING', deadline=past2)
        Task.objects.create(task_no='T-OD-0012', title='C', creator=admin_user, status='PENDING', deadline=past3)

        result = DashboardService.get_overdue_tasks(limit=10)
        deadlines = [r['deadline'] for r in result]
        assert deadlines == sorted(deadlines)
