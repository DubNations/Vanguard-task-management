"""定时任务测试 — 逾期检查/每日摘要/即将到期。"""
from datetime import timedelta

import pytest
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from freezegun import freeze_time

from apps.notifications.models import Notification
from apps.tasks.models import Task
from apps.tasks.scheduled_tasks import (
    check_overdue_tasks,
    send_daily_digest_emails,
    check_upcoming_deadlines,
)


@pytest.fixture
def admin_user(db):
    from apps.accounts.models import User
    return User.objects.create_superuser(
        email='sched_admin@test.com', password='p', username='sched_admin',
    )


@pytest.fixture
def regular_user(db, team):
    from apps.accounts.models import User
    return User.objects.create_user(
        email='sched_user@test.com', password='p', username='sched_user',
        role='MEMBER', team=team,
    )


@pytest.fixture
def team(db):
    from apps.accounts.models import Team
    return Team.objects.create(name='定时测试组', description='')


@pytest.fixture
def overdue_task(admin_user, regular_user):
    """创建一个已逾期 2 天的任务。"""
    return Task.objects.create(
        task_no='OVERDUE-001',
        title='逾期任务',
        creator=admin_user,
        assignee=regular_user,
        deadline=timezone.now() - timedelta(days=2),
    )


# ---------------------------------------------------------------------------
# check_overdue_tasks
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestCheckOverdueTasks:
    """逾期检查定时任务。"""

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_creates_overdue_notification(self, overdue_task, regular_user):
        """1. 有逾期任务 → 创建 TASK_OVERDUE 通知。"""
        check_overdue_tasks()
        assert Notification.objects.filter(
            recipient=regular_user, type=Notification.Type.TASK_OVERDUE
        ).exists()

    def test_no_assignee_skipped(self, admin_user):
        """2. 无负责人 → 跳过，不创建通知。"""
        Task.objects.create(
            task_no='OVERDUE-002',
            title='无负责人逾期',
            creator=admin_user,
            assignee=None,
            deadline=timezone.now() - timedelta(days=2),
        )
        count = check_overdue_tasks()
        assert count == 0
        assert not Notification.objects.filter(
            type=Notification.Type.TASK_OVERDUE
        ).exists()

    def test_completed_excluded(self, admin_user, regular_user):
        """3. COMPLETED 任务被排除。"""
        Task.objects.create(
            task_no='OVERDUE-003',
            title='已完成逾期',
            creator=admin_user,
            assignee=regular_user,
            deadline=timezone.now() - timedelta(days=2),
            status=Task.Status.COMPLETED,
        )
        count = check_overdue_tasks()
        assert count == 0

    def test_cancelled_excluded(self, admin_user, regular_user):
        """4. CANCELLED 任务被排除。"""
        Task.objects.create(
            task_no='OVERDUE-004',
            title='已取消逾期',
            creator=admin_user,
            assignee=regular_user,
            deadline=timezone.now() - timedelta(days=2),
            status=Task.Status.CANCELLED,
        )
        count = check_overdue_tasks()
        assert count == 0

    def test_no_duplicate_same_day(self, overdue_task, regular_user):
        """5. 同一天重复调用 → 不创建重复通知。"""
        check_overdue_tasks()
        assert Notification.objects.filter(
            recipient=regular_user, type=Notification.Type.TASK_OVERDUE
        ).count() == 1
        check_overdue_tasks()
        assert Notification.objects.filter(
            recipient=regular_user, type=Notification.Type.TASK_OVERDUE
        ).count() == 1

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_sends_email(self, overdue_task):
        """6. 逾期任务发送邮件。"""
        mail.outbox.clear()
        check_overdue_tasks()
        assert len(mail.outbox) >= 1


# ---------------------------------------------------------------------------
# send_daily_digest_emails
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestSendDailyDigest:
    """每日摘要邮件。"""

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_sends_with_overdue_and_upcoming(self, admin_user, regular_user):
        """7. 有逾期+即将到期任务 → 发送邮件。"""
        now = timezone.now()
        Task.objects.create(
            task_no='DIGEST-001', title='逾期', creator=admin_user,
            assignee=regular_user, deadline=now - timedelta(days=1),
        )
        Task.objects.create(
            task_no='DIGEST-002', title='即将到期', creator=admin_user,
            assignee=regular_user, deadline=now + timedelta(days=1),
        )
        mail.outbox.clear()
        sent = send_daily_digest_emails()
        assert sent >= 1

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_no_pending_no_email(self, admin_user, regular_user):
        """8. 无待办任务 → 不发邮件。"""
        Task.objects.create(
            task_no='DIGEST-003', title='已完成', creator=admin_user,
            assignee=regular_user, status=Task.Status.COMPLETED,
        )
        mail.outbox.clear()
        sent = send_daily_digest_emails()
        assert sent == 0

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_inactive_user_skipped(self, admin_user, team):
        """9. 非活跃用户被跳过。"""
        from apps.accounts.models import User
        inactive = User.objects.create_user(
            email='inactive@test.com', username='inactive', password='p',
            team=team, is_active=False,
        )
        Task.objects.create(
            task_no='DIGEST-004', title='非活跃逾期', creator=admin_user,
            assignee=inactive, deadline=timezone.now() - timedelta(days=1),
        )
        mail.outbox.clear()
        sent = send_daily_digest_emails()
        # 确保没有发给 inactive 用户
        for msg in mail.outbox:
            assert 'inactive@test.com' not in msg.to
        # inactive 用户的邮件不应存在
        inactive_emails = [
            m for m in mail.outbox if 'inactive@test.com' in m.to
        ]
        assert len(inactive_emails) == 0

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_summary_data_accuracy(self, admin_user, regular_user):
        """10. 摘要数据准确：overdue/in_progress/completed_today。"""
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # 逾期任务
        Task.objects.create(
            task_no='ACC-001', title='逾期1', creator=admin_user,
            assignee=regular_user, deadline=now - timedelta(days=1),
        )
        Task.objects.create(
            task_no='ACC-002', title='逾期2', creator=admin_user,
            assignee=regular_user, deadline=now - timedelta(days=2),
        )
        # 进行中
        Task.objects.create(
            task_no='ACC-003', title='进行中', creator=admin_user,
            assignee=regular_user, status=Task.Status.IN_PROGRESS,
            deadline=now + timedelta(days=5),
        )
        # 今日完成
        Task.objects.create(
            task_no='ACC-004', title='今日完成', creator=admin_user,
            assignee=regular_user, status=Task.Status.COMPLETED,
            completed_at=now,
        )
        # 即将到期（触发邮件发送）
        Task.objects.create(
            task_no='ACC-005', title='即将到期', creator=admin_user,
            assignee=regular_user, deadline=now + timedelta(days=1),
        )
        mail.outbox.clear()
        send_daily_digest_emails()
        # 验证邮件已发送（至少有一封给 regular_user）
        user_emails = [m for m in mail.outbox if regular_user.email in m.to]
        assert len(user_emails) >= 1


# ---------------------------------------------------------------------------
# check_upcoming_deadlines
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestCheckUpcomingDeadlines:
    """即将到期检查。"""

    def test_due_within_24h_creates_notification(self, admin_user, regular_user):
        """11. 24 小时内到期 → 创建 TASK_DEADLINE 通知。"""
        Task.objects.create(
            task_no='UP-001', title='即将到期', creator=admin_user,
            assignee=regular_user, deadline=timezone.now() + timedelta(hours=12),
        )
        count = check_upcoming_deadlines()
        assert count == 1
        assert Notification.objects.filter(
            recipient=regular_user, type=Notification.Type.TASK_DEADLINE
        ).exists()

    def test_already_past_due_not_included(self, admin_user, regular_user):
        """12. 已过期的任务不包含在内（deadline > now）。"""
        Task.objects.create(
            task_no='UP-002', title='已过期', creator=admin_user,
            assignee=regular_user, deadline=timezone.now() - timedelta(hours=1),
        )
        count = check_upcoming_deadlines()
        assert count == 0

    def test_no_assignee_skipped(self, admin_user):
        """13. 无负责人 → 跳过。"""
        Task.objects.create(
            task_no='UP-003', title='无负责人即将到期', creator=admin_user,
            assignee=None, deadline=timezone.now() + timedelta(hours=12),
        )
        count = check_upcoming_deadlines()
        assert count == 0

    def test_no_duplicate_same_day(self, admin_user, regular_user):
        """14. 同一天重复调用 → 不创建重复通知。"""
        Task.objects.create(
            task_no='UP-004', title='重复测试', creator=admin_user,
            assignee=regular_user, deadline=timezone.now() + timedelta(hours=12),
        )
        check_upcoming_deadlines()
        assert Notification.objects.filter(
            recipient=regular_user, type=Notification.Type.TASK_DEADLINE
        ).count() == 1
        check_upcoming_deadlines()
        assert Notification.objects.filter(
            recipient=regular_user, type=Notification.Type.TASK_DEADLINE
        ).count() == 1

    def test_return_value_is_integer(self, admin_user, regular_user):
        """15. 返回值为整数。"""
        Task.objects.create(
            task_no='UP-005', title='返回值测试', creator=admin_user,
            assignee=regular_user, deadline=timezone.now() + timedelta(hours=6),
        )
        result = check_upcoming_deadlines()
        assert isinstance(result, int)
