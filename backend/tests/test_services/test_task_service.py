"""
任务服务单元测试。
用法: cd backend && python -m pytest tests/ -v
"""
import pytest
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
class TestTaskService:
    """测试任务服务层。"""

    def test_generate_task_no(self):
        from apps.tasks.services.task_service import TaskService
        no = TaskService.generate_task_no()
        assert no.startswith('TASK-')
        assert len(no) == 18  # TASK-YYYYMMDD-NNNN = 5+8+1+4 = 18

    def test_create_task(self, admin_user):
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({
            'title': '测试任务',
            'description': '描述',
            'priority': 'HIGH',
        }, admin_user)
        assert task.title == '测试任务'
        assert task.status == 'PENDING'
        assert task.creator == admin_user

    def test_transition_valid(self, admin_user):
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': 'T1'}, admin_user)
        task = TaskService.transition_status(task, 'IN_PROGRESS', admin_user)
        assert task.status == 'IN_PROGRESS'
        assert task.started_at is not None

    def test_transition_invalid(self, admin_user):
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': 'T2'}, admin_user)
        with pytest.raises(ValueError):
            TaskService.transition_status(task, 'COMPLETED', admin_user)

    def test_update_progress(self, admin_user):
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': 'T3'}, admin_user)
        task = TaskService.update_progress(task, 50, admin_user)
        assert task.progress == 50


@pytest.mark.django_db
class TestTaskModel:
    """测试任务模型属性。"""

    def test_is_overdue(self, admin_user):
        from apps.tasks.models import Task
        task = Task.objects.create(
            task_no='TEST-0001',
            title='逾期测试',
            creator=admin_user,
            deadline=timezone.now() - timedelta(days=1),
        )
        assert task.is_overdue is True

    def test_not_overdue_when_completed(self, admin_user):
        from apps.tasks.models import Task
        task = Task.objects.create(
            task_no='TEST-0002',
            title='已完成',
            creator=admin_user,
            status='COMPLETED',
            deadline=timezone.now() - timedelta(days=1),
        )
        assert task.is_overdue is False
