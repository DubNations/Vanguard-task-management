"""
email_service 单元测试。
"""
import pytest
from django.core import mail
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
class TestEmailService:
    """测试邮件服务。"""

    def _make_task(self, admin_user):
        from apps.tasks.services.task_service import TaskService
        return TaskService.create_task({'title': '邮件测试任务'}, admin_user)

    # ------------------------------------------------------------------
    # send_task_assigned_email
    # ------------------------------------------------------------------
    def test_send_task_assigned_email(self, admin_user, regular_user, settings):
        """发送任务分配邮件。"""
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        from apps.notifications.services.email_service import send_task_assigned_email

        task = self._make_task(admin_user)
        send_task_assigned_email(task, regular_user)
        assert len(mail.outbox) == 1

    def test_assigned_email_subject(self, admin_user, regular_user, settings):
        """任务分配邮件主题包含任务编号。"""
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        from apps.notifications.services.email_service import send_task_assigned_email

        task = self._make_task(admin_user)
        send_task_assigned_email(task, regular_user)
        assert task.task_no in mail.outbox[0].subject
        assert '[任务分配]' in mail.outbox[0].subject

    def test_assigned_email_recipient(self, admin_user, regular_user, settings):
        """邮件收件人正确。"""
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        from apps.notifications.services.email_service import send_task_assigned_email

        task = self._make_task(admin_user)
        send_task_assigned_email(task, regular_user)
        assert regular_user.email in mail.outbox[0].to

    # ------------------------------------------------------------------
    # send_task_overdue_email
    # ------------------------------------------------------------------
    def test_send_task_overdue_email(self, admin_user, regular_user, settings):
        """发送逾期提醒邮件。"""
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        from apps.notifications.services.email_service import send_task_overdue_email

        task = self._make_task(admin_user)
        send_task_overdue_email(task, regular_user)
        assert len(mail.outbox) == 1
        assert '[逾期提醒]' in mail.outbox[0].subject

    # ------------------------------------------------------------------
    # send_task_status_email
    # ------------------------------------------------------------------
    def test_send_task_status_email(self, admin_user, regular_user, settings):
        """发送状态变更邮件。"""
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        from apps.notifications.services.email_service import send_task_status_email

        task = self._make_task(admin_user)
        send_task_status_email(task, regular_user, 'PENDING', 'IN_PROGRESS')
        assert len(mail.outbox) == 1
        assert '[状态变更]' in mail.outbox[0].subject

    # ------------------------------------------------------------------
    # send_daily_digest
    # ------------------------------------------------------------------
    def test_send_daily_digest(self, admin_user, settings):
        """发送每日摘要邮件。"""
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        from apps.notifications.services.email_service import send_daily_digest

        summary = {'date': '2026-06-15', 'completed_today': 3, 'in_progress': 2, 'overdue': 1}
        send_daily_digest(admin_user, summary)
        assert len(mail.outbox) == 1
        assert '[每日摘要]' in mail.outbox[0].subject

    # ------------------------------------------------------------------
    # _send 失败不抛异常
    # ------------------------------------------------------------------
    @patch('apps.notifications.services.email_service.send_mail', side_effect=Exception('SMTP error'))
    def test_send_failure_no_exception(self, mock_send, admin_user, regular_user):
        """send_mail 失败时 _send 不抛出异常。"""
        from apps.notifications.services.email_service import send_task_assigned_email

        task = self._make_task(admin_user)
        # 不应抛出异常
        send_task_assigned_email(task, regular_user)

    # ------------------------------------------------------------------
    # 批量发送
    # ------------------------------------------------------------------
    def test_batch_send(self, admin_user, regular_user, member_b_user, settings):
        """批量发送多封邮件。"""
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        from apps.notifications.services.email_service import send_task_assigned_email

        task = self._make_task(admin_user)
        send_task_assigned_email(task, regular_user)
        send_task_assigned_email(task, member_b_user)
        assert len(mail.outbox) == 2
