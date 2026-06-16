"""仪表盘测试 — 数据聚合与角色过滤。"""
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Team, User
from apps.tasks.models import Task


def _make_task(title, creator, assignee=None, status='PENDING', priority='MEDIUM',
               deadline=None, completed_at=None):
    """辅助：快速创建任务。"""
    task_no = f'T-{title}-{Task.objects.count() + 1}'
    return Task.objects.create(
        task_no=task_no,
        title=title,
        creator=creator,
        assignee=assignee,
        status=status,
        priority=priority,
        deadline=deadline,
        completed_at=completed_at,
    )


@pytest.mark.django_db
class TestDashboardSummary:
    """summary 接口测试。"""

    def test_summary_empty(self, auth_client):
        """1. 无任务时所有计数为 0。"""
        resp = auth_client.get(reverse('dashboard-summary'))
        assert resp.status_code == 200
        data = resp.data
        assert data['total'] == 0
        assert data['pending'] == 0
        assert data['in_progress'] == 0
        assert data['completed'] == 0
        assert data['overdue'] == 0
        assert data['completed_today'] == 0

    def test_summary_admin_sees_all(self, auth_client, admin_user, regular_user):
        """2. ADMIN(superuser) 看到所有任务。"""
        _make_task('管理员任务A', creator=admin_user, assignee=admin_user)
        _make_task('成员任务B', creator=regular_user, assignee=regular_user)
        resp = auth_client.get(reverse('dashboard-summary'))
        assert resp.status_code == 200
        assert resp.data['total'] == 2

    def test_summary_member_own_tasks_only(self, member_client, admin_user, regular_user):
        """3. MEMBER 只看到自己相关任务。"""
        _make_task('我的任务', creator=admin_user, assignee=regular_user)
        _make_task('别人任务', creator=admin_user, assignee=admin_user)
        resp = member_client.get(reverse('dashboard-summary'))
        assert resp.status_code == 200
        assert resp.data['total'] == 1

    def test_summary_overdue_excludes_completed_cancelled(self, auth_client, admin_user):
        """4. overdue 不含 COMPLETED/CANCELLED。"""
        past = timezone.now() - timedelta(days=3)
        _make_task('逾期', creator=admin_user, deadline=past, status='PENDING')
        _make_task('已完成', creator=admin_user, deadline=past, status='COMPLETED')
        _make_task('已取消', creator=admin_user, deadline=past, status='CANCELLED')
        resp = auth_client.get(reverse('dashboard-summary'))
        assert resp.status_code == 200
        assert resp.data['overdue'] == 1

    def test_summary_completed_today(self, auth_client, admin_user):
        """5. completed_today 只统计今日完成。"""
        now = timezone.now()
        _make_task('今日完成', creator=admin_user, status='COMPLETED',
                   completed_at=now, assignee=admin_user)
        _make_task('昨日完成', creator=admin_user, status='COMPLETED',
                   completed_at=now - timedelta(days=1), assignee=admin_user)
        resp = auth_client.get(reverse('dashboard-summary'))
        assert resp.status_code == 200
        assert resp.data['completed_today'] == 1

    def test_summary_created_this_week(self, auth_client, admin_user):
        """6. created_this_week 统计最近 7 天。"""
        _make_task('新任务', creator=admin_user, assignee=admin_user)
        old = _make_task('旧任务', creator=admin_user, assignee=admin_user)
        Task.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=10)
        )
        resp = auth_client.get(reverse('dashboard-summary'))
        assert resp.status_code == 200
        assert resp.data['created_this_week'] == 1


@pytest.mark.django_db
class TestDistributions:
    """状态/优先级分布。"""

    def test_status_distribution(self, auth_client, admin_user):
        """7. 状态分布按 status 分组。"""
        _make_task('P1', creator=admin_user, status='PENDING')
        _make_task('P2', creator=admin_user, status='PENDING')
        _make_task('IP', creator=admin_user, status='IN_PROGRESS')
        resp = auth_client.get(reverse('dashboard-status'))
        assert resp.status_code == 200
        data = resp.data
        status_map = {item['status']: item['count'] for item in data}
        assert status_map.get('PENDING') == 2
        assert status_map.get('IN_PROGRESS') == 1

    def test_priority_distribution(self, auth_client, admin_user):
        """8. 优先级分布按 priority 分组。"""
        _make_task('H1', creator=admin_user, priority='HIGH')
        _make_task('H2', creator=admin_user, priority='HIGH')
        _make_task('L1', creator=admin_user, priority='LOW')
        resp = auth_client.get(reverse('dashboard-priority'))
        assert resp.status_code == 200
        data = resp.data
        prio_map = {item['priority']: item['count'] for item in data}
        assert prio_map.get('HIGH') == 2
        assert prio_map.get('LOW') == 1


@pytest.mark.django_db
class TestWeeklyTrend:
    """周趋势接口。"""

    def test_weekly_trend_default_8_weeks(self, auth_client):
        """9. 默认 8 个数据点。"""
        resp = auth_client.get(reverse('dashboard-trend'))
        assert resp.status_code == 200
        assert len(resp.data) == 8

    def test_weekly_trend_custom_4_weeks(self, auth_client):
        """10. weeks=4 → 4 个数据点。"""
        resp = auth_client.get(reverse('dashboard-trend'), {'weeks': 4})
        assert resp.status_code == 200
        assert len(resp.data) == 4


@pytest.mark.django_db
class TestTeamWorkload:
    """团队工作量。"""

    def test_workload_grouped_by_team(self, auth_client, admin_user, team):
        """11. 按团队分组，包含 total 和 completed。"""
        user_a = User.objects.create_user(
            email='wa@test.com', username='wa', password='p', team=team
        )
        user_b = User.objects.create_user(
            email='wb@test.com', username='wb', password='p', team=team
        )
        _make_task('WA1', creator=admin_user, assignee=user_a)
        _make_task('WA2', creator=admin_user, assignee=user_a, status='COMPLETED')
        _make_task('WB1', creator=admin_user, assignee=user_b)
        resp = auth_client.get(reverse('dashboard-workload'))
        assert resp.status_code == 200
        data = resp.data
        assert len(data) >= 1
        team_entry = next(
            (item for item in data if item.get('team_name') == team.name), None
        )
        assert team_entry is not None
        assert team_entry['total'] == 3
        assert team_entry['completed'] == 1


@pytest.mark.django_db
class TestOverdueTasks:
    """逾期任务列表。"""

    def test_overdue_limit(self, auth_client, admin_user):
        """12. limit 参数限制返回数量。"""
        for i in range(5):
            _make_task(
                f'逾期{i}', creator=admin_user,
                deadline=timezone.now() - timedelta(days=i + 1),
            )
        resp = auth_client.get(reverse('dashboard-overdue'), {'limit': 3})
        assert resp.status_code == 200
        assert len(resp.data) == 3

    def test_overdue_ordered_by_deadline_asc(self, auth_client, admin_user):
        """13. 按 deadline 升序排列。"""
        now = timezone.now()
        _make_task('最久', creator=admin_user, deadline=now - timedelta(days=5))
        _make_task('较近', creator=admin_user, deadline=now - timedelta(days=1))
        _make_task('中间', creator=admin_user, deadline=now - timedelta(days=3))
        resp = auth_client.get(reverse('dashboard-overdue'))
        assert resp.status_code == 200
        deadlines = [item['deadline'] for item in resp.data]
        assert deadlines == sorted(deadlines)


@pytest.mark.django_db
class TestDashboardAuth:
    """未认证访问。"""

    def test_unauthenticated_access(self, api_client):
        """14. 未认证 → 401/403。"""
        resp = api_client.get(reverse('dashboard-summary'))
        assert resp.status_code in (401, 403)
