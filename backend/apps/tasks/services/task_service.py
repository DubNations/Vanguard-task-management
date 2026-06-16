import uuid
from datetime import datetime

from django.utils import timezone

from apps.tasks.models import Task, TaskHistory
from apps.notifications.models import Notification


class TaskService:
    """任务核心业务逻辑。"""

    @staticmethod
    def generate_task_no():
        """生成任务编号: TASK-YYYYMMDD-XXXX。"""
        now = timezone.now()
        prefix = now.strftime('TASK-%Y%m%d')
        # Find latest
        last = Task.objects.filter(task_no__startswith=prefix).order_by('-task_no').first()
        if last:
            seq = int(last.task_no.split('-')[-1]) + 1
        else:
            seq = 1
        return f'{prefix}-{seq:04d}'

    @staticmethod
    def create_task(data, user):
        """创建任务并记录历史。"""
        task_no = TaskService.generate_task_no()
        task = Task.objects.create(
            task_no=task_no,
            title=data['title'],
            description=data.get('description', ''),
            priority=data.get('priority', Task.Priority.MEDIUM),
            deadline=data.get('deadline'),
            assignee=data.get('assignee'),
            reviewer=data.get('reviewer'),
            creator=user,
            tags=data.get('tags', []),
            custom_fields=data.get('custom_fields', {}),
            reward_points=data.get('reward_points', 0),
        )

        TaskHistory.objects.create(
            task=task,
            action=TaskHistory.Action.CREATED,
            actor=user,
            new_value={
                'title': task.title,
                'priority': task.priority,
                'assignee': str(task.assignee_id) if task.assignee_id else None,
                'deadline': task.deadline.isoformat() if task.deadline else None,
            },
            note='任务创建',
        )

        # 通知被分配的人 + 积分奖励
        if task.assignee and task.assignee != user:
            Notification.objects.create(
                recipient=task.assignee,
                type=Notification.Type.TASK_ASSIGNED,
                title=f'您有新任务: {task.title}',
                content=f'任务编号: {task.task_no}，创建人: {user.display_name}',
                task=task,
                actor=user,
            )
            # 积分触发：被分配任务
            try:
                from apps.points.services.point_service import PointService
                PointService.award(task.assignee, task, 'TASK_ASSIGNED', '被分配新任务')
            except Exception:
                pass  # 积分系统异常不影响核心流程

        return task

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

        # 积分触发：完成任务
        if new_status == Task.Status.COMPLETED and task.assignee:
            try:
                from apps.points.services.point_service import PointService
                PointService.award(task.assignee, task, 'TASK_COMPLETED', '完成任务')
            except Exception:
                pass

        return task

    @staticmethod
    def update_task(task, data, user):
        """更新任务字段并记录 diff。"""
        old_values = {}
        new_values = {}

        updatable = ['title', 'description', 'priority', 'deadline', 'progress',
                      'assignee', 'reviewer', 'tags', 'custom_fields', 'reward_points']

        for field in updatable:
            if field not in data:
                continue
            old_val = getattr(task, field)
            new_val = data[field]

            # Skip if same
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
