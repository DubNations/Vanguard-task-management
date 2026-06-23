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
    # get_member_dashboard
    # ------------------------------------------------------------------
    def test_member_dashboard_empty(self, regular_user):
        """空数据时所有统计值为 0。"""
        from apps.dashboard.services import DashboardService
        data = DashboardService.get_member_dashboard(regular_user)
        assert data['summary']['total'] == 0
        assert data['summary']['pending'] == 0
        assert data['monthly_points']['earned'] == 0
        assert data['todo_list'] == []

    def test_member_dashboard_sees_own_tasks(self, admin_user, regular_user):
        """普通成员只看自己相关(creator/assignee/participant)的任务。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        Task.objects.create(task_no='T-010', title='Mine', creator=regular_user, status='PENDING')
        Task.objects.create(task_no='T-011', title='Assigned', creator=admin_user,
                            assignee=regular_user, status='IN_PROGRESS')
        Task.objects.create(task_no='T-012', title='Other', creator=admin_user, status='PENDING')

        data = DashboardService.get_member_dashboard(regular_user)
        assert data['summary']['total'] == 2
        assert data['summary']['pending'] == 1
        assert data['summary']['in_progress'] == 1

    def test_member_dashboard_todo_list_ordered(self, admin_user, regular_user):
        """待办列表按紧急度排序：逾期在前。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        past = timezone.now() - timedelta(days=3)
        future = timezone.now() + timedelta(days=30)
        Task.objects.create(task_no='T-020', title='Future', creator=regular_user,
                            status='IN_PROGRESS', deadline=future, priority='LOW')
        Task.objects.create(task_no='T-021', title='Overdue', creator=regular_user,
                            status='IN_PROGRESS', deadline=past, priority='HIGH')

        data = DashboardService.get_member_dashboard(regular_user)
        assert data['todo_list'][0]['task_no'] == 'T-021'  # 逾期排前面
        assert data['todo_list'][0]['is_overdue'] is True

    def test_member_dashboard_overdue_count(self, admin_user, regular_user):
        """overdue 统计排除 COMPLETED/CANCELLED。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        past = timezone.now() - timedelta(days=1)
        Task.objects.create(task_no='T-030', title='Overdue', creator=regular_user,
                            status='PENDING', deadline=past)
        Task.objects.create(task_no='T-031', title='Done', creator=regular_user,
                            status='COMPLETED', deadline=past)
        Task.objects.create(task_no='T-032', title='Cancelled', creator=regular_user,
                            status='CANCELLED', deadline=past)

        data = DashboardService.get_member_dashboard(regular_user)
        assert data['summary']['overdue'] == 1

    def test_member_dashboard_includes_participants(self, admin_user, regular_user):
        """参与者能看到关联的任务。"""
        from apps.tasks.models import Task, TaskParticipant
        from apps.dashboard.services import DashboardService

        task = Task.objects.create(task_no='T-040', title='Participated', creator=admin_user,
                                   status='IN_PROGRESS')
        TaskParticipant.objects.create(task=task, user=regular_user, role='CLAIMER', points=0)

        data = DashboardService.get_member_dashboard(regular_user)
        assert data['summary']['total'] == 1

    # ------------------------------------------------------------------
    # get_leader_dashboard
    # ------------------------------------------------------------------
    def test_leader_dashboard_sees_all(self, admin_user, regular_user):
        """admin(superuser) 看全局统计。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        Task.objects.create(task_no='T-100', title='A', creator=admin_user, status='PENDING')
        Task.objects.create(task_no='T-101', title='B', creator=regular_user, status='IN_PROGRESS')

        data = DashboardService.get_leader_dashboard(admin_user)
        assert data['summary']['total'] == 2
        assert data['summary']['pending'] == 1
        assert data['summary']['in_progress'] == 1

    def test_leader_dashboard_overdue_tasks(self, admin_user):
        """LEADER 能看到逾期任务列表。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        past = timezone.now() - timedelta(days=5)
        future = timezone.now() + timedelta(days=30)
        Task.objects.create(task_no='T-110', title='Overdue', creator=admin_user,
                            status='IN_PROGRESS', deadline=past)
        Task.objects.create(task_no='T-111', title='OnTime', creator=admin_user,
                            status='IN_PROGRESS', deadline=future)

        data = DashboardService.get_leader_dashboard(admin_user)
        assert len(data['overdue_tasks']) == 1
        assert data['overdue_tasks'][0]['task_no'] == 'T-110'

    def test_leader_dashboard_member_workload(self, admin_user, regular_user):
        """LEADER 能看到成员负载。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        Task.objects.create(task_no='T-120', title='A', creator=admin_user,
                            assignee=regular_user, status='IN_PROGRESS')

        data = DashboardService.get_leader_dashboard(admin_user)
        workload = data['member_workload']
        assert len(workload) >= 1
        entry = next(w for w in workload if w['user_id'] == str(regular_user.id))
        assert entry['in_progress'] == 1

    def test_leader_dashboard_monthly_team_points(self, admin_user):
        """LEADER 能看到本月团队积分。"""
        from apps.tasks.models import Task
        from apps.dashboard.services import DashboardService

        now = timezone.now()
        Task.objects.create(task_no='T-130', title='Done', creator=admin_user,
                            status='COMPLETED', completed_at=now, reward_points=10)

        data = DashboardService.get_leader_dashboard(admin_user)
        assert data['monthly_team_points']['total_points'] == 10
        assert data['monthly_team_points']['completed_count'] == 1

    def test_leader_dashboard_non_leader_falls_back(self, regular_user):
        """非 LEADER 用户调用 leader 端点降级为 member。"""
        from apps.dashboard.services import DashboardService
        data = DashboardService.get_leader_dashboard(regular_user)
        # 非 LEADER 不应看到成员负载
        assert 'member_workload' not in data or data.get('member_workload') == []


@pytest.mark.django_db
class TestSafeInt:
    """测试 _safe_int 参数安全解析。"""

    def test_valid_int(self):
        from apps.dashboard.services import _safe_int
        assert _safe_int(5, 10) == 5

    def test_string_int(self):
        from apps.dashboard.services import _safe_int
        assert _safe_int('8', 10) == 8

    def test_none_returns_default(self):
        from apps.dashboard.services import _safe_int
        assert _safe_int(None, 10) == 10

    def test_non_numeric_returns_default(self):
        from apps.dashboard.services import _safe_int
        assert _safe_int('abc', 10) == 10

    def test_below_min(self):
        from apps.dashboard.services import _safe_int
        assert _safe_int(0, 10, min_val=1, max_val=100) == 1

    def test_above_max(self):
        from apps.dashboard.services import _safe_int
        assert _safe_int(200, 10, min_val=1, max_val=100) == 100
