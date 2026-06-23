"""
django-q2 定时任务 — 逾期检查 & 每日摘要。

通过 management command `register_scheduled_tasks` 注册到 django-q2 Schedule 表。
也可手动调用: python manage.py run_scheduled_tasks
"""
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)


def check_overdue_tasks():
    """
    检查逾期任务：
    1. 找出所有已过截止日期但仍未完成的任务
    2. 为负责人创建站内通知
    3. 发送逾期提醒邮件（每个任务只发一次）
    """
    from apps.tasks.models import Task
    from apps.notifications.models import Notification
    from apps.notifications.services import send_task_overdue_email

    now = timezone.now()
    overdue_tasks = Task.objects.filter(
        deadline__lt=now,
    ).exclude(
        status__in=[Task.Status.COMPLETED, Task.Status.CANCELLED]
    ).select_related('assignee', 'creator')

    count = 0
    for task in overdue_tasks:
        if not task.assignee:
            continue

        # 创建站内通知（每天最多一条相同任务的通知）
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        already_notified = Notification.objects.filter(
            recipient=task.assignee,
            task=task,
            type=Notification.Type.TASK_OVERDUE,
            created_at__gte=today_start,
        ).exists()

        if not already_notified:
            try:
                Notification.objects.create(
                    recipient=task.assignee,
                    type=Notification.Type.TASK_OVERDUE,
                    title=f'任务逾期提醒: {task.title}',
                    content=f'任务 {task.task_no} 已于 {task.deadline.strftime("%m-%d %H:%M")} 到期，请尽快处理。',
                    task=task,
                )

                # 发送邮件
                send_task_overdue_email(task, task.assignee)
                count += 1
            except Exception:
                logger.error('逾期通知发送失败: task=%s', task.task_no, exc_info=True)

    logger.info('逾期检查完成: 发送 %d 条提醒', count)
    return count


def send_daily_digest_emails():
    """
    每日任务摘要：
    1. 为每个活跃用户生成任务摘要
    2. 发送邮件（仅当有待办/逾期任务时发送）
    """
    from apps.accounts.models import User
    from apps.tasks.models import Task
    from apps.notifications.services import send_daily_digest

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    active_users = User.objects.filter(is_active=True).select_related('team')
    sent = 0

    for user in active_users:
        user_tasks = Task.objects.filter(
            assignee=user
        ).exclude(
            status__in=[Task.Status.COMPLETED, Task.Status.CANCELLED]
        )

        overdue_tasks = user_tasks.filter(deadline__lt=now)
        upcoming_tasks = user_tasks.filter(
            deadline__gte=now,
            deadline__lte=now + timedelta(days=3),
        )
        completed_today = Task.objects.filter(
            assignee=user,
            status=Task.Status.COMPLETED,
            completed_at__gte=today_start,
            completed_at__lt=today_end,
        ).count()

        # 只有待办/逾期任务才发邮件
        if not (overdue_tasks.exists() or upcoming_tasks.exists()):
            continue

        summary = {
            'date': now.strftime('%Y-%m-%d'),
            'completed_today': completed_today,
            'in_progress': user_tasks.filter(status=Task.Status.IN_PROGRESS).count(),
            'overdue': overdue_tasks.count(),
            'overdue_tasks': list(overdue_tasks[:5].values('task_no', 'title', 'deadline', 'progress')),
            'upcoming_tasks': list(upcoming_tasks[:5].values('task_no', 'title', 'deadline', 'progress')),
        }

        send_daily_digest(user, summary)
        sent += 1

    logger.info('每日摘要完成: 发送 %d 封邮件', sent)
    return sent


def check_upcoming_deadlines():
    """
    检查即将到期的任务（24小时内）并提前通知。
    """
    from apps.tasks.models import Task
    from apps.notifications.models import Notification

    now = timezone.now()
    upcoming = Task.objects.filter(
        deadline__gt=now,
        deadline__lte=now + timedelta(hours=24),
    ).exclude(
        status__in=[Task.Status.COMPLETED, Task.Status.CANCELLED]
    ).select_related('assignee')

    count = 0
    for task in upcoming:
        if not task.assignee:
            continue

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        already_notified = Notification.objects.filter(
            recipient=task.assignee,
            task=task,
            type=Notification.Type.TASK_DEADLINE,
            created_at__gte=today_start,
        ).exists()

        if not already_notified:
            try:
                hours_left = int((task.deadline - now).total_seconds() / 3600)
                Notification.objects.create(
                    recipient=task.assignee,
                    type=Notification.Type.TASK_DEADLINE,
                    title=f'任务即将到期: {task.title}',
                    content=f'任务 {task.task_no} 将在 {hours_left} 小时后到期，请抓紧完成。',
                    task=task,
                )
                count += 1
            except Exception:
                logger.error('到期预警通知发送失败: task=%s', task.task_no, exc_info=True)

    logger.info('到期预警完成: 创建 %d 条通知', count)
    return count
