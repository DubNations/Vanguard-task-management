"""
邮件通知服务 — 发送站内通知对应的邮件。
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_task_assigned_email(task, assignee):
    """发送任务分配邮件。"""
    context = {
        'task': task,
        'assignee': assignee,
        'site_name': '尖兵部队任务系统',
    }
    subject = f'[任务分配] {task.task_no} - {task.title}'
    html_message = render_to_string('email/task_assigned.html', context)
    _send(
        subject=subject,
        html_message=html_message,
        recipient_list=[assignee.email],
    )


def send_task_overdue_email(task, assignee):
    """发送任务逾期提醒邮件。"""
    context = {
        'task': task,
        'assignee': assignee,
        'site_name': '尖兵部队任务系统',
    }
    subject = f'[逾期提醒] {task.task_no} - {task.title}'
    html_message = render_to_string('email/task_overdue.html', context)
    _send(
        subject=subject,
        html_message=html_message,
        recipient_list=[assignee.email],
    )


def send_task_status_email(task, assignee, old_status, new_status):
    """发送任务状态变更邮件。"""
    from apps.tasks.models import Task
    context = {
        'task': task,
        'assignee': assignee,
        'old_status_label': Task.Status(old_status).label if old_status else '',
        'new_status_label': Task.Status(new_status).label if new_status else '',
        'site_name': '尖兵部队任务系统',
    }
    subject = f'[状态变更] {task.task_no} - {task.title}'
    html_message = render_to_string('email/task_status_change.html', context)
    _send(
        subject=subject,
        html_message=html_message,
        recipient_list=[assignee.email],
    )


def send_daily_digest(user, tasks_summary):
    """发送每日摘要邮件。"""
    context = {
        'user': user,
        'summary': tasks_summary,
        'site_name': '尖兵部队任务系统',
    }
    subject = f'[每日摘要] {tasks_summary.get("date", "")}'
    html_message = render_to_string('email/daily_digest.html', context)
    _send(
        subject=subject,
        html_message=html_message,
        recipient_list=[user.email],
    )


def _send(subject, html_message, recipient_list):
    """统一发送邮件，失败只记录日志不抛异常。"""
    try:
        send_mail(
            subject=subject,
            message='',
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info('邮件发送成功: %s -> %s', subject, recipient_list)
    except Exception as e:
        logger.error('邮件发送失败: %s -> %s: %s', subject, recipient_list, e)
