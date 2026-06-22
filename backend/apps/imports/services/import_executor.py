"""
导入执行器 — 确认后将预览数据写入数据库。
"""
from django.db import models
from apps.tasks.models import Task, TaskHistory, TaskParticipant
from apps.tasks.services.task_service import TaskService
from apps.accounts.models import User
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

        # 展开嵌套的 custom_fields（表单解析器会将扩展字段放入 custom_fields dict）
        nested_custom = record.pop('custom_fields', {})
        if nested_custom:
            for k, v in nested_custom.items():
                if v and k not in record:
                    record[k] = v

        # 解析优先级
        priority = PRIORITY_MAP.get(record.get('priority', ''), 'MEDIUM')

        # 解析负责人（按姓名查找）
        assignee = None
        assignee_name = record.get('assignee_name', '') or record.get('lead_name', '')
        assignee_name = assignee_name.strip()
        if assignee_name:
            assignee = User.objects.filter(username=assignee_name).first()
            if not assignee:
                assignee = User.objects.filter(
                    models.Q(username__icontains=assignee_name) |
                    models.Q(first_name__icontains=assignee_name)
                ).first()

        # 解析状态
        status_raw = record.get('status', '')
        status = STATUS_MAP.get(status_raw, 'PENDING')

        # 解析截止日期
        deadline = _parse_datetime(record.get('deadline', ''))

        # 解析开始时间
        started_at = _parse_datetime(record.get('start_date', '') or record.get('started_at', ''))

        # 解析进度
        progress = 0
        progress_raw = record.get('progress', '')
        if progress_raw:
            try:
                progress = int(progress_raw.replace('%', ''))
                progress = min(100, max(0, progress))
            except (ValueError, TypeError):
                pass

        # 构建描述（事项内容）
        description = record.get('description', '')

        # 积分
        reward_points = 0
        rp_raw = record.get('reward_points', '')
        if rp_raw:
            try:
                reward_points = int(rp_raw)
            except (ValueError, TypeError):
                pass

        # 创建任务
        task_data = {
            'title': title,
            'description': description,
            'priority': priority,
            'assignee': assignee,
            'deadline': deadline,
            'reward_points': reward_points,
            'task_source': record.get('task_source', ''),
            'completion_criteria': record.get('completion_criteria', ''),
            'dispatcher_name': record.get('dispatcher_name', ''),
            'output': record.get('output', ''),
            'tags': [],
            'custom_fields': {},
        }

        task = TaskService.create_task(task_data, user)

        # 设置开始时间
        if started_at:
            task.started_at = started_at
            task.save(update_fields=['started_at', 'updated_at'])

        # 如果状态不是默认值，尝试转换
        if status != 'PENDING' and task.can_transition_to(status):
            TaskService.transition_status(task, status, user, note='导入时自动设置')

        # 设置进度
        if progress > 0:
            task.progress = progress
            task.save(update_fields=['progress', 'updated_at'])

        # 存储附件路径到 custom_fields（只有附件是非标准字段）
        custom = {}
        if record.get('attachments'):
            custom['attachments'] = record['attachments']
        if custom:
            task.custom_fields = custom
            task.save(update_fields=['custom_fields', 'updated_at'])

        # 解析参与人并创建 TaskParticipant
        participants_text = record.get('participant_names_text', '') or record.get('participant_names', '')
        if participants_text:
            _create_participants(task, participants_text, assignee)

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


def _parse_datetime(raw):
    """解析日期字符串，支持多种格式。"""
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None

    from django.utils.dateparse import parse_datetime, parse_date
    from django.utils import timezone as tz
    from datetime import datetime
    import re

    # 尝试标准解析
    dt = parse_datetime(raw)
    if dt:
        if tz.is_naive(dt):
            dt = tz.make_aware(dt)
        return dt

    d = parse_date(raw)
    if d:
        return tz.make_aware(datetime(d.year, d.month, d.day, 23, 59))

    # 中文日期格式："6 月 22 日" / "7月24日" / "2025年6月30日"
    m = re.match(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?', raw)
    if m:
        return tz.make_aware(datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 23, 59))

    m = re.match(r'(\d{1,2})\s*月\s*(\d{1,2})\s*日?', raw)
    if m:
        from datetime import date
        today = date.today()
        return tz.make_aware(datetime(today.year, int(m.group(1)), int(m.group(2)), 23, 59))

    return None


def _create_participants(task, participants_text, chief_lead):
    """解析参与人字符串并创建 TaskParticipant 记录。

    格式支持：逗号、顿号、分号分隔的姓名列表。
    牵头人自动标记为 CHIEF_LEAD，其余为 PARTICIPANT。
    """
    import re
    names = re.split(r'[,，、；;\s]+', participants_text)
    names = [n.strip() for n in names if n.strip()]

    for i, name in enumerate(names):
        user = User.objects.filter(username=name).first()
        if not user:
            user = User.objects.filter(
                models.Q(username__icontains=name) |
                models.Q(first_name__icontains=name)
            ).first()
        if not user:
            continue

        # 第一个人（或与牵头人同名）标记为 CHIEF_LEAD，其余为 PARTICIPANT
        if chief_lead and user == chief_lead:
            role = TaskParticipant.Role.CHIEF_LEAD
        elif i == 0 and not chief_lead:
            role = TaskParticipant.Role.CHIEF_LEAD
        else:
            role = TaskParticipant.Role.PARTICIPANT

        points = 0  # 导入时积分默认为 0，后续可按规则计算

        TaskParticipant.objects.get_or_create(
            task=task,
            user=user,
            defaults={'role': role, 'points': points},
        )
