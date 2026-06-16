"""
导入执行器 — 确认后将预览数据写入数据库。
"""
from apps.tasks.models import Task, TaskHistory
from apps.tasks.services.task_service import TaskService
from apps.accounts.models import User


# 中文 → 英文映射
PRIORITY_MAP = {
    '低': 'LOW', '中': 'MEDIUM', '高': 'HIGH', '紧急': 'URGENT',
    'LOW': 'LOW', 'MEDIUM': 'MEDIUM', 'HIGH': 'HIGH', 'URGENT': 'URGENT',
}

STATUS_MAP = {
    '待领取': 'PENDING', '进行中': 'IN_PROGRESS', '待审核': 'IN_REVIEW',
    '已完成': 'COMPLETED', '已退回': 'REJECTED',
    'PENDING': 'PENDING', 'IN_PROGRESS': 'IN_PROGRESS', 'IN_REVIEW': 'IN_REVIEW',
    'COMPLETED': 'COMPLETED', 'REJECTED': 'REJECTED',
}


def execute_import(session, user):
    """执行导入，将有效数据创建为任务。"""
    task_ids = []

    for item in session.preview_data:
        if not item.get('valid'):
            continue

        record = item.get('data', {})
        title = record.get('title', '').strip()
        if not title:
            continue

        # 解析优先级
        priority = PRIORITY_MAP.get(record.get('priority', ''), 'MEDIUM')

        # 解析负责人（按姓名查找）
        assignee = None
        assignee_name = record.get('assignee_name', '').strip()
        if assignee_name:
            assignee = User.objects.filter(username=assignee_name).first()

        # 解析状态
        status_raw = record.get('status', '')
        status = STATUS_MAP.get(status_raw, 'PENDING')

        # 解析截止日期
        deadline = None
        deadline_raw = record.get('deadline', '').strip()
        if deadline_raw:
            from django.utils.dateparse import parse_datetime, parse_date
            from django.utils import timezone as tz
            dt = parse_datetime(deadline_raw)
            if dt:
                if tz.is_naive(dt):
                    dt = tz.make_aware(dt)
            else:
                d = parse_date(deadline_raw)
                if d:
                    from datetime import datetime
                    dt = tz.make_aware(datetime(d.year, d.month, d.day, 23, 59))
            deadline = dt

        # 解析进度
        progress = 0
        progress_raw = record.get('progress', '')
        if progress_raw:
            try:
                progress = int(progress_raw.replace('%', ''))
                progress = min(100, max(0, progress))
            except (ValueError, TypeError):
                pass

        # 创建任务
        task_data = {
            'title': title,
            'description': record.get('description', ''),
            'priority': priority,
            'assignee': assignee,
            'deadline': deadline,
            'tags': [],
            'custom_fields': {},
        }

        task = TaskService.create_task(task_data, user)

        # 如果状态不是默认值，尝试转换
        if status != 'PENDING' and task.can_transition_to(status):
            TaskService.transition_status(task, status, user, note='导入时自动设置')

        # 设置进度
        if progress > 0:
            task.progress = progress
            task.save(update_fields=['progress', 'updated_at'])

        # 标记来源
        task.source = f'IMPORT:{session.file_format}'
        task.external_id = str(session.id)
        task.save(update_fields=['source', 'external_id', 'updated_at'])

        TaskHistory.objects.create(
            task=task,
            action=TaskHistory.Action.IMPORTED,
            actor=user,
            note=f'从 {session.original_name} 导入 (行 {item.get("row", "?")})',
        )

        task_ids.append(str(task.id))

    return {'task_ids': task_ids}
