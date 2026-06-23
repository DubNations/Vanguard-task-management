"""权限系统单元测试。"""
import pytest
from unittest.mock import Mock

from common.permissions import IsSuperAdmin, IsGroupLeader, IsOwnerOrLeader
from apps.tasks.models import Task


# ---------------------------------------------------------------------------
# IsSuperAdmin
# ---------------------------------------------------------------------------
class TestIsSuperAdmin:
    """IsSuperAdmin 权限类测试。"""

    def test_superuser_returns_true(self, admin_user):
        """超级管理员 → True。"""
        request = Mock()
        request.user = admin_user
        perm = IsSuperAdmin()
        assert perm.has_permission(request, None) is True

    def test_admin_role_not_superuser_returns_false(self, db, team):
        """role=ADMIN 但非 superuser → False。"""
        from apps.accounts.models import User
        user = User.objects.create_user(
            email='admin_no_super@test.com',
            password='testpass123',
            username='admin_no_super',
            role='ADMIN',
            team=team,
        )
        request = Mock()
        request.user = user
        perm = IsSuperAdmin()
        assert perm.has_permission(request, None) is False

    def test_inactive_superuser_returns_false(self, admin_user):
        """is_active=False 的超级管理员 → False。"""
        admin_user.is_active = False
        admin_user.save()
        request = Mock()
        request.user = admin_user
        perm = IsSuperAdmin()
        assert perm.has_permission(request, None) is False


# ---------------------------------------------------------------------------
# IsGroupLeader
# ---------------------------------------------------------------------------
class TestIsGroupLeader:
    """IsGroupLeader 权限类测试。"""

    def test_leader_returns_true(self, leader_user):
        """role=LEADER → True。"""
        request = Mock()
        request.user = leader_user
        perm = IsGroupLeader()
        assert perm.has_permission(request, None) is True

    def test_member_returns_false(self, regular_user):
        """role=MEMBER → False。"""
        request = Mock()
        request.user = regular_user
        perm = IsGroupLeader()
        assert perm.has_permission(request, None) is False

    def test_superuser_returns_true(self, admin_user):
        """超级管理员 → True。"""
        request = Mock()
        request.user = admin_user
        perm = IsGroupLeader()
        assert perm.has_permission(request, None) is True

    def test_inactive_leader_returns_false(self, leader_user):
        """is_active=False 的 LEADER → False。"""
        leader_user.is_active = False
        leader_user.save()
        request = Mock()
        request.user = leader_user
        perm = IsGroupLeader()
        assert perm.has_permission(request, None) is False


# ---------------------------------------------------------------------------
# IsOwnerOrLeader
# ---------------------------------------------------------------------------
class TestIsOwnerOrLeader:
    """IsOwnerOrLeader 权限类测试。"""

    def test_superuser_returns_true(self, admin_user, sample_task):
        """超级管理员 → True。"""
        request = Mock()
        request.user = admin_user
        perm = IsOwnerOrLeader()
        assert perm.has_object_permission(request, None, sample_task) is True

    def test_leader_returns_true(self, leader_user, sample_task):
        """LEADER → True。"""
        request = Mock()
        request.user = leader_user
        perm = IsOwnerOrLeader()
        assert perm.has_object_permission(request, None, sample_task) is True

    def test_assignee_returns_true(self, regular_user, admin_user):
        """任务负责人 → True。"""
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task(
            {'title': '分配给成员的任务', 'assignee': regular_user},
            admin_user,
        )
        request = Mock()
        request.user = regular_user
        perm = IsOwnerOrLeader()
        assert perm.has_object_permission(request, None, task) is True

    def test_non_assignee_member_returns_false(self, regular_user, admin_user):
        """非负责人的 MEMBER → False。"""
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task(
            {'title': '未分配给此成员的任务'},
            admin_user,
        )
        request = Mock()
        request.user = regular_user
        perm = IsOwnerOrLeader()
        assert perm.has_object_permission(request, None, task) is False


# ---------------------------------------------------------------------------
# 数据隔离
# ---------------------------------------------------------------------------
class TestDataIsolation:
    """数据隔离集成测试 — 通过 API 验证查询集过滤。"""

    def test_member_sees_only_own_tasks(
        self, member_client, regular_user, admin_user,
    ):
        """MEMBER 列表：自己的任务 + PENDING 任务大厅。"""
        from apps.tasks.services.task_service import TaskService
        # 创建分配给 regular_user 的任务（IN_PROGRESS）
        TaskService.create_task(
            {'title': '分配给成员的任务', 'assignee': regular_user},
            admin_user,
        )
        # 创建不相关的 PENDING 任务（任务大厅，对所有人可见）
        TaskService.create_task({'title': '其他任务'}, admin_user)

        resp = member_client.get('/api/v1/tasks/')
        assert resp.status_code == 200
        results = resp.data['results']
        # PENDING 任务对所有成员可见（任务大厅）
        assert len(results) == 2
        titles = [t['title'] for t in results]
        assert '分配给成员的任务' in titles
        assert '其他任务' in titles  # PENDING 任务大厅

    def test_leader_sees_all_tasks(
        self, leader_client, admin_user,
    ):
        """LEADER 能看到全部任务。"""
        from apps.tasks.services.task_service import TaskService
        TaskService.create_task({'title': '任务A'}, admin_user)
        TaskService.create_task({'title': '任务B'}, admin_user)

        resp = leader_client.get('/api/v1/tasks/')
        assert resp.status_code == 200
        results = resp.data['results']
        assert len(results) >= 2
