"""通知模块测试 — 列表/标记已读/全部已读。"""
import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.notifications.models import Notification
from apps.tasks.models import Task
from apps.tasks.services.task_service import TaskService


def _create_notification(recipient, task=None, n_type=Notification.Type.TASK_ASSIGNED,
                         title='测试通知', actor=None):
    """辅助：创建通知。"""
    return Notification.objects.create(
        recipient=recipient,
        type=n_type,
        title=title,
        task=task,
        actor=actor,
    )


@pytest.mark.django_db
class TestNotificationList:
    """通知列表接口。"""

    def test_list_unread_count(self, member_client, regular_user):
        """1. 有未读通知时 unread_count > 0。"""
        _create_notification(regular_user, title='通知A')
        _create_notification(regular_user, title='通知B')
        resp = member_client.get(reverse('notification-list'))
        assert resp.status_code == 200
        assert resp.data['unread_count'] == 2

    def test_list_filter_unread_only(self, member_client, regular_user):
        """2. ?unread=true 只返回未读通知。"""
        n1 = _create_notification(regular_user, title='未读')
        n2 = _create_notification(regular_user, title='已读')
        n2.mark_read()
        resp = member_client.get(reverse('notification-list'), {'unread': 'true'})
        assert resp.status_code == 200
        ids = [n['id'] for n in resp.data['notifications']]
        assert str(n1.id) in ids
        assert str(n2.id) not in ids

    def test_list_limit_50(self, member_client, regular_user):
        """11. 通知列表最多返回 50 条。"""
        for i in range(55):
            _create_notification(regular_user, title=f'通知{i}')
        resp = member_client.get(reverse('notification-list'))
        assert resp.status_code == 200
        assert len(resp.data['notifications']) == 50


@pytest.mark.django_db
class TestNotificationMarkRead:
    """标记单条通知已读。"""

    def test_mark_single_read(self, member_client, regular_user):
        """3. 标记已读后 is_read=True, read_at 不为空。"""
        n = _create_notification(regular_user)
        resp = member_client.post(reverse('notification-read', kwargs={'pk': n.id}))
        assert resp.status_code == 200
        n.refresh_from_db()
        assert n.is_read is True
        assert n.read_at is not None

    def test_mark_someone_else_notification_404(self, member_client, member_b_user):
        """4. 标记他人通知 → 404（按 recipient 过滤）。"""
        n = _create_notification(member_b_user)
        resp = member_client.post(reverse('notification-read', kwargs={'pk': n.id}))
        assert resp.status_code == 404

    def test_mark_nonexistent_notification_404(self, member_client):
        """5. 标记不存在的通知 → 404。"""
        fake_id = uuid.uuid4()
        resp = member_client.post(reverse('notification-read', kwargs={'pk': fake_id}))
        assert resp.status_code == 404

    def test_mark_read_idempotency(self, member_client, regular_user):
        """12. 已读通知再次标记 read_at 不变。"""
        n = _create_notification(regular_user)
        past = timezone.now() - timedelta(hours=1)
        n.is_read = True
        n.read_at = past
        n.save(update_fields=['is_read', 'read_at'])

        member_client.post(reverse('notification-read', kwargs={'pk': n.id}))
        n.refresh_from_db()
        assert n.read_at == past


@pytest.mark.django_db
class TestNotificationMarkAll:
    """全部标记已读。"""

    def test_mark_all_read(self, member_client, regular_user):
        """6. 全部标记已读 → 200，所有通知 is_read=True。"""
        for i in range(3):
            _create_notification(regular_user, title=f'通知{i}')
        resp = member_client.post(reverse('notification-mark-all'))
        assert resp.status_code == 200
        assert Notification.objects.filter(
            recipient=regular_user, is_read=False
        ).count() == 0

    def test_mark_all_read_no_unread(self, member_client, regular_user):
        """7. 没有未读通知时调用 → 200，无副作用。"""
        n = _create_notification(regular_user)
        n.mark_read()
        resp = member_client.post(reverse('notification-mark-all'))
        assert resp.status_code == 200


@pytest.mark.django_db
class TestNotificationCreation:
    """任务操作触发通知。"""

    def test_task_assignment_creates_notification(self, admin_user, regular_user):
        """8. 分配任务给他人 → 创建 TASK_ASSIGNED 通知。"""
        TaskService.create_task(
            {'title': '分配任务', 'assignee': regular_user}, admin_user
        )
        assert Notification.objects.filter(
            recipient=regular_user, type=Notification.Type.TASK_ASSIGNED
        ).exists()

    def test_self_assignment_no_notification(self, admin_user):
        """9. 自己分配给自己 → 不创建通知。"""
        TaskService.create_task(
            {'title': '自我任务', 'assignee': admin_user}, admin_user
        )
        assert not Notification.objects.filter(
            recipient=admin_user, type=Notification.Type.TASK_ASSIGNED
        ).exists()

    def test_status_change_creates_notification(self, admin_user, regular_user):
        """10. 状态变更 → 创建 TASK_STATUS 通知。"""
        task = TaskService.create_task(
            {'title': '状态任务', 'assignee': regular_user}, admin_user
        )
        TaskService.transition_status(task, Task.Status.IN_PROGRESS, admin_user)
        assert Notification.objects.filter(
            recipient=regular_user, type=Notification.Type.TASK_STATUS
        ).exists()
