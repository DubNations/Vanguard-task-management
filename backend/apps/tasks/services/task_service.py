import logging
from django.db import transaction, IntegrityError
from django.utils import timezone

from apps.tasks.models import Task, TaskHistory, TaskParticipant
from apps.notifications.models import Notification
from common.utils import strip_html_tags

logger = logging.getLogger('apps')


class TaskService:
    """任务核心业务逻辑。"""

    @staticmethod
    def generate_task_no():
        """生成任务编号: TASK-YYYYMMDD-XXXX。"""
        from django.db import transaction
        now = timezone.now()
        prefix = now.strftime('TASK-%Y%m%d')
        with transaction.atomic():
            last = Task.objects.filter(
                task_no__startswith=prefix
            ).order_by('-task_no').select_for_update().first()
            if last:
                seq = int(last.task_no.split('-')[-1]) + 1
            else:
                seq = 1
            return f'{prefix}-{seq:04d}'

    @staticmethod
    def create_task(data, user):
        """创建任务并记录历史（支持三种模式）。"""
        task_mode = data.get('task_mode', Task.TaskMode.ASSIGNED)
        participants_data = data.get('participants', [])

        # Mode-level validation
        if task_mode == Task.TaskMode.FREE_CLAIM:
            if data.get('reward_points', 0) <= 0:
                raise ValueError('揭榜挂帅模式必须设置积分')
        elif task_mode == Task.TaskMode.FIXED_CLAIM:
            if data.get('reward_points', 0) <= 0:
                raise ValueError('揭榜挂帅模式必须设置积分')
            if not data.get('max_claimers'):
                raise ValueError('固定揭榜必须设置名额数')
        elif task_mode == Task.TaskMode.ASSIGNED and participants_data:
            chief_leads = [p for p in participants_data if p.get('role') == TaskParticipant.Role.CHIEF_LEAD]
            if not chief_leads:
                raise ValueError('派发模式必须指定至少一名总牵头人')

        for _retry in range(5):
            try:
                task_no = TaskService.generate_task_no()
                # 派发模式有负责人/参与者：直接进入进行中；揭榜模式：待领取
                initial_status = Task.Status.PENDING
                initial_started_at = None
                if task_mode == Task.TaskMode.ASSIGNED:
                    has_assignee = data.get('assignee') is not None
                    has_participants = bool(participants_data)
                    if has_assignee or has_participants:
                        initial_status = Task.Status.IN_PROGRESS
                        initial_started_at = timezone.now()

                task = Task.objects.create(
                    task_no=task_no,
                    title=data['title'],
                    description=data.get('description', ''),
                    priority=data.get('priority', Task.Priority.MEDIUM),
                    status=initial_status,
                    deadline=data.get('deadline'),
                    started_at=initial_started_at,
                    assignee=data.get('assignee'),
                    reviewer=data.get('reviewer'),
                    creator=user,
                    tags=data.get('tags', []),
                    custom_fields=data.get('custom_fields', {}),
                    reward_points=data.get('reward_points', 0),
                    task_mode=task_mode,
                    max_claimers=data.get('max_claimers'),
                    task_source=data.get('task_source', ''),
                    completion_criteria=data.get('completion_criteria', ''),
                    dispatcher_name=data.get('dispatcher_name', ''),
                    output=data.get('output', ''),
                )
                break
            except IntegrityError:
                if _retry == 4:
                    raise
                logger.warning('任务编号 %s 冲突，重试 (%d/5)', task_no, _retry + 1)
                continue

        # 按模式处理参与者
        if task_mode == Task.TaskMode.ASSIGNED and participants_data:
            TaskService._create_assigned_participants(task, participants_data, user)

        # 通知 assignee（非参与者模式下直接分配）
        if task.assignee and task.assignee != user and not participants_data:
            try:
                Notification.objects.create(
                    recipient=task.assignee,
                    type=Notification.Type.TASK_ASSIGNED,
                    title=f'您有新任务: {task.title}',
                    content=f'任务编号: {task.task_no}，创建人: {user.display_name}',
                    task=task,
                    actor=user,
                )
            except Exception:
                logger.warning('Failed to create TASK_ASSIGNED notification for task %s', task.task_no, exc_info=True)

        TaskHistory.objects.create(
            task=task,
            action=TaskHistory.Action.CREATED,
            actor=user,
            new_value={
                'title': task.title,
                'priority': task.priority,
                'task_mode': task_mode,
                'assignee': str(task.assignee_id) if task.assignee_id else None,
                'deadline': task.deadline.isoformat() if task.deadline else None,
            },
            note=f'任务创建（{task.get_task_mode_display()}模式）',
        )

        return task

    @staticmethod
    def _create_assigned_participants(task, participants_data, creator):
        """派发模式：批量创建参与者并发送通知。"""
        for p_data in participants_data:
            user_id = p_data['user_id']
            role = p_data['role']
            points = p_data['points']

            participant = TaskParticipant.objects.create(
                task=task,
                user_id=user_id,
                role=role,
                points=points,
                status=TaskParticipant.Status.INVITED,
            )

            # 通知参与者
            try:
                from apps.accounts.models import User
                recipient = User.objects.get(pk=user_id)
                Notification.objects.create(
                    recipient=recipient,
                    type=Notification.Type.TASK_ASSIGNED,
                    title=f'您被分配了任务: {task.title}',
                    content=f'任务编号: {task.task_no}，角色: {participant.get_role_display()}，积分: {points}',
                    task=task,
                    actor=creator,
                )
            except Exception:
                logger.warning('通知发送失败: task=%s user=%s', task.task_no, user_id)

    @staticmethod
    def transition_status(task, new_status, user, note=''):
        """状态机转换。"""
        if not task.can_transition_to(new_status):
            raise ValueError(
                f'无法从 {task.get_status_display()} 转为 '
                f'{Task.Status(new_status).label}'
            )

        old_status = task.status
        task.status = new_status

        # 自动设置时间
        now = timezone.now()
        if new_status == Task.Status.IN_PROGRESS and not task.started_at:
            task.started_at = now
        if new_status == Task.Status.COMPLETED:
            task.completed_at = now
            task.progress = 100
        if new_status == Task.Status.REJECTED:
            task.progress = max(0, task.progress - 10)

        task.save()

        TaskHistory.objects.create(
            task=task,
            action=TaskHistory.Action.STATUS_CHANGE,
            actor=user,
            old_value={'status': old_status},
            new_value={'status': new_status},
            diff={'from': old_status, 'to': new_status},
            note=note,
        )

        # 通知相关人员
        if task.assignee and task.assignee != user:
            Notification.objects.create(
                recipient=task.assignee,
                type=Notification.Type.TASK_STATUS,
                title=f'任务状态变更: {task.title}',
                content=f'状态: {Task.Status(old_status).label} → {Task.Status(new_status).label}',
                task=task,
                actor=user,
            )

        # ===== 派发模式完成：批量发放全团队积分 =====
        if (new_status == Task.Status.COMPLETED
                and task.task_mode == Task.TaskMode.ASSIGNED):
            TaskService._batch_award_on_completed(task, user)

        # ===== 揭榜模式完成（仅记录，积分由管理员逐个判定） =====
        # FREE_CLAIM / FIXED_CLAIM 的积分在 TaskParticipantCompleteView 中发放

        return task

    @staticmethod
    def _batch_award_on_completed(task, actor):
        """派发模式：总牵头人完成任务后，批量发放全团队积分。"""
        from apps.points.services.point_service import PointService

        participants = task.participants.filter(
            status__in=[TaskParticipant.Status.ACCEPTED, TaskParticipant.Status.COMPLETED]
        )

        for p in participants:
            try:
                PointService.award(
                    p.user, task,
                    action='TASK_COMPLETED',
                    points=p.points,
                    reason=f'[派发] {task.task_no} {p.get_role_display()}完成',
                )
                p.status = TaskParticipant.Status.COMPLETED
                p.completed_at = timezone.now()
                p.save(update_fields=['status', 'completed_at'])
            except Exception:
                logger.error('积分发放失败: task=%s user=%s', task.task_no, p.user_id)

        # 通知所有参与者
        for p in participants:
            try:
                Notification.objects.create(
                    recipient=p.user,
                    type=Notification.Type.TASK_STATUS,
                    title=f'任务已完成: {task.title}',
                    content=f'积分 {p.points} 已发放',
                    task=task,
                    actor=actor,
                )
            except Exception:
                logger.warning('通知发送失败: task=%s user=%s', task.task_no, p.user_id, exc_info=True)

    @staticmethod
    def update_task(task, data, user):
        """更新任务字段并记录 diff。"""
        # XSS 防御：清洗文本字段
        text_fields = ['title', 'description', 'task_source', 'completion_criteria',
                        'dispatcher_name', 'output']
        for field in text_fields:
            if field in data and isinstance(data[field], str):
                data[field] = strip_html_tags(data[field])
        if 'tags' in data and isinstance(data['tags'], list):
            data['tags'] = [strip_html_tags(t) for t in data['tags']]

        old_values = {}
        new_values = {}

        updatable = ['title', 'description', 'priority', 'deadline', 'progress',
                      'assignee', 'reviewer', 'tags', 'custom_fields', 'reward_points',
                      'task_source', 'completion_criteria', 'dispatcher_name', 'output',
                      'task_mode', 'max_claimers']

        for field in updatable:
            if field not in data:
                continue
            old_val = getattr(task, field)
            new_val = data[field]

            if str(old_val) == str(new_val):
                continue

            old_values[field] = str(old_val) if old_val else None
            new_values[field] = str(new_val) if new_val else None
            setattr(task, field, new_val)

        if old_values:
            task.save()
            TaskHistory.objects.create(
                task=task,
                action=TaskHistory.Action.UPDATED,
                actor=user,
                old_value=old_values,
                new_value=new_values,
                diff={k: {'old': old_values.get(k), 'new': new_values.get(k)} for k in old_values},
                note=data.get('note', ''),
            )

        return task

    @staticmethod
    def update_progress(task, progress, user):
        """更新进度。"""
        old = task.progress
        task.progress = min(100, max(0, progress))
        task.save(update_fields=['progress', 'updated_at'])

        if old != task.progress:
            TaskHistory.objects.create(
                task=task,
                action=TaskHistory.Action.UPDATED,
                actor=user,
                old_value={'progress': old},
                new_value={'progress': task.progress},
                note=f'进度更新: {old}% → {task.progress}%',
            )
        return task
