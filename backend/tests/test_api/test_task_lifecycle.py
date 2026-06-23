"""
场景 S2 — 任务分配与完整生命周期模拟测试。
模拟：Leader 分配任务 → Member 收到通知 → 开始 → 更新进度 → 评论 → 提交审核 → 审核通过/退回。
"""
import pytest
from django.urls import reverse

from apps.tasks.models import Task, TaskHistory
from apps.notifications.models import Notification


@pytest.mark.django_db
class TestTaskAssignmentLifecycle:
    """S2: 任务分配与完整生命周期。"""

    def _auth(self, client, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        return client

    def test_s2_01_leader_creates_and_assigns_task(self, leader_client, leader_user, regular_user):
        """Leader 创建任务并分配给 member。"""
        url = reverse('task-list')
        response = leader_client.post(url, {
            'title': '开发登录模块',
            'priority': 'HIGH',
            'assignee': str(regular_user.id),
        }, format='json')
        assert response.status_code == 201
        data = response.json()
        assert data['task_no'].startswith('TASK-')
        # 有 assignee 时自动进入 IN_PROGRESS
        assert data['status'] == 'IN_PROGRESS'
        assert data['creator'] == str(leader_user.id)
        assert data['assignee'] == str(regular_user.id)

    def test_s2_02_member_receives_assignment_notification(self, leader_client, leader_user, regular_user):
        """分配任务后 Member 收到通知。"""
        url = reverse('task-list')
        leader_client.post(url, {
            'title': '通知测试任务',
            'assignee': str(regular_user.id),
        }, format='json')

        notif = Notification.objects.filter(
            recipient=regular_user,
            type=Notification.Type.TASK_ASSIGNED,
        )
        assert notif.count() >= 1
        assert '通知测试任务' in notif.first().title

    def test_s2_03_member_views_own_tasks(self, leader_client, member_client, leader_user, regular_user):
        """Member 查看任务列表：自己的任务 + PENDING 任务大厅。"""
        # Leader 创建自己的任务（PENDING，对所有人可见）
        leader_client.post(reverse('task-list'), {
            'title': 'Leader自己的任务',
        }, format='json')
        # Leader 创建分配给 Member 的任务
        leader_client.post(reverse('task-list'), {
            'title': '分配给Member的任务',
            'assignee': str(regular_user.id),
        }, format='json')

        response = member_client.get(reverse('task-list'))
        assert response.status_code == 200
        tasks = response.json().get('results', response.json())
        titles = [t['title'] for t in tasks]
        # PENDING 任务对所有成员可见（任务大厅）
        assert '分配给Member的任务' in titles
        assert 'Leader自己的任务' in titles  # PENDING 任务大厅

    def test_s2_04_member_starts_task(self, auth_client, member_client, admin_user, regular_user):
        """Member 开始任务: 创建揭榜任务后领取并开始。"""
        from apps.tasks.services.task_service import TaskService
        # 创建揭榜任务（FREE_CLAIM 模式，PENDING 状态）
        task = TaskService.create_task(
            {'title': '开始任务测试', 'task_mode': 'FREE_CLAIM', 'reward_points': 10}, admin_user
        )
        assert task.status == 'PENDING'
        assert task.task_mode == 'FREE_CLAIM'

        # Member 领取任务
        url_claim = reverse('task-claim', kwargs={'pk': task.pk})
        response = member_client.post(url_claim)
        # 领取成功返回 200 或 201
        assert response.status_code in (200, 201)

        # 验证 TaskHistory
        history = TaskHistory.objects.filter(task=task, action=TaskHistory.Action.STATUS_CHANGE)
        assert history.exists()

    def test_s2_05_member_updates_progress(self, auth_client, member_client, admin_user, regular_user):
        """Member 更新进度至 60%。"""
        from apps.tasks.services.task_service import TaskService
        # 创建任务（有 assignee 时自动进入 IN_PROGRESS）
        task = TaskService.create_task(
            {'title': '进度测试任务', 'assignee': regular_user}, admin_user
        )
        assert task.status == 'IN_PROGRESS'  # 自动进入进行中

        url = reverse('task-progress', kwargs={'pk': task.pk})
        response = member_client.post(url, {'progress': 60}, format='json')
        assert response.status_code == 200
        assert response.json()['progress'] == 60

    def test_s2_06_member_adds_comment(self, auth_client, member_client, admin_user, regular_user):
        """Member 添加评论并验证 TaskHistory。"""
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task(
            {'title': '评论测试任务', 'assignee': regular_user}, admin_user
        )

        url = reverse('task-comments', kwargs={'pk': task.pk})
        response = member_client.post(url, {'content': '登录UI已完成'}, format='json')
        assert response.status_code == 201

        history = TaskHistory.objects.filter(task=task, action=TaskHistory.Action.COMMENTED)
        assert history.exists()

    def test_s2_07_member_submits_for_review(self, auth_client, member_client, admin_user, regular_user, leader_user):
        """Member 提交审核: IN_PROGRESS -> IN_REVIEW。"""
        from apps.tasks.services.task_service import TaskService
        # 创建任务（有 assignee 时自动进入 IN_PROGRESS）
        task = TaskService.create_task(
            {'title': '审核测试任务', 'assignee': regular_user}, admin_user
        )
        assert task.status == 'IN_PROGRESS'  # 自动进入进行中

        url = reverse('task-transition', kwargs={'pk': task.pk})
        response = member_client.post(url, {
            'status': 'IN_REVIEW',
            'note': '请审核',
        }, format='json')
        assert response.status_code == 200
        assert response.json()['status'] == 'IN_REVIEW'

        # Leader 收到状态变更通知
        # (此处验证 TaskHistory 记录了 note)
        history = TaskHistory.objects.filter(
            task=task, action=TaskHistory.Action.STATUS_CHANGE
        ).order_by('-created_at').first()
        assert history.note == '请审核'

    def test_s2_08_leader_approves_task(self, auth_client, leader_client, admin_user, regular_user, leader_user):
        """Leader 审核通过: IN_REVIEW -> COMPLETED。"""
        from apps.tasks.services.task_service import TaskService
        # 创建任务（有 assignee 时自动进入 IN_PROGRESS）
        task = TaskService.create_task(
            {'title': '审核通过测试', 'assignee': regular_user}, admin_user
        )
        assert task.status == 'IN_PROGRESS'  # 自动进入进行中
        TaskService.transition_status(task, 'IN_REVIEW', regular_user)

        url = reverse('task-transition', kwargs={'pk': task.pk})
        response = leader_client.post(url, {'status': 'COMPLETED'}, format='json')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'COMPLETED'
        assert data['progress'] == 100
        assert data['completed_at'] is not None

    def test_s2_09_rejection_and_redo_flow(self, auth_client, leader_client, member_client, admin_user, regular_user):
        """退回重做流程: IP->IR->REJECTED->IP->IR->COMPLETED。"""
        from apps.tasks.services.task_service import TaskService
        # 创建任务（有 assignee 时自动进入 IN_PROGRESS）
        task = TaskService.create_task(
            {'title': '退回重做测试', 'assignee': regular_user}, admin_user
        )
        assert task.status == 'IN_PROGRESS'  # 自动进入进行中
        pk = task.pk
        url = reverse('task-transition', kwargs={'pk': pk})

        # IN_PROGRESS -> IN_REVIEW
        member_client.post(url, {'status': 'IN_REVIEW'}, format='json')

        # IN_REVIEW -> REJECTED (Leader 退回)
        resp = leader_client.post(url, {'status': 'REJECTED'}, format='json')
        assert resp.status_code == 200
        task.refresh_from_db()
        # 退回后进度减10
        assert task.progress == 0  # max(0, 0-10) = 0

        # REJECTED -> IN_PROGRESS (Member 重做)
        resp = member_client.post(url, {'status': 'IN_PROGRESS'}, format='json')
        assert resp.status_code == 200

        # IN_PROGRESS -> IN_REVIEW (再次提交)
        member_client.post(url, {'status': 'IN_REVIEW'}, format='json')
        # IN_REVIEW -> COMPLETED (Leader 通过)
        resp = leader_client.post(url, {'status': 'COMPLETED'}, format='json')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'COMPLETED'

    def test_s2_10_cancel_task_terminal_state(self, auth_client, admin_user):
        """取消任务: PENDING -> CANCELLED（终态不可再转换）。"""
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': '取消测试'}, admin_user)

        url = reverse('task-transition', kwargs={'pk': task.pk})
        resp = auth_client.post(url, {'status': 'CANCELLED'}, format='json')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'CANCELLED'

        # 终态不可再转换
        resp2 = auth_client.post(url, {'status': 'IN_PROGRESS'}, format='json')
        assert resp2.status_code == 400
