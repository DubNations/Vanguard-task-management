"""
API 层集成测试 — 任务相关接口。
"""
import pytest
from django.urls import reverse

from apps.tasks.models import Task


@pytest.mark.django_db
class TestTaskListAPI:
    """任务列表接口测试。"""

    def test_create_task(self, auth_client, admin_user):
        url = reverse('task-list')
        response = auth_client.post(url, {
            'title': '测试任务',
            'description': '这是一个测试任务',
            'priority': 'HIGH',
        }, format='json')
        assert response.status_code == 201
        data = response.json()
        assert data['title'] == '测试任务'
        assert data['task_no'].startswith('TASK-')
        assert data['status'] == 'PENDING'

    def test_list_tasks(self, auth_client, admin_user):
        # 先创建一个任务
        from apps.tasks.services.task_service import TaskService
        TaskService.create_task({'title': '任务A'}, admin_user)

        url = reverse('task-list')
        response = auth_client.get(url)
        assert response.status_code == 200

    def test_member_sees_own_tasks_only(self, api_client, regular_user, admin_user):
        from rest_framework_simplejwt.tokens import RefreshToken
        from apps.tasks.services.task_service import TaskService

        # 创建管理员的任务
        TaskService.create_task({'title': '管理员任务'}, admin_user)
        # 创建普通用户的任务
        TaskService.create_task({'title': '成员任务', 'assignee': regular_user}, admin_user)

        refresh = RefreshToken.for_user(regular_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        url = reverse('task-list')
        response = api_client.get(url)
        assert response.status_code == 200
        # 成员只能看到自己的任务
        tasks = response.json().get('results', response.json())
        assert len(tasks) == 1
        assert tasks[0]['title'] == '成员任务'

    def test_create_task_empty_title(self, auth_client):
        url = reverse('task-list')
        response = auth_client.post(url, {'title': ''}, format='json')
        assert response.status_code == 400


@pytest.mark.django_db
class TestTaskDetailAPI:
    """任务详情接口测试。"""

    def test_get_task_detail(self, auth_client, admin_user):
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': '详情测试'}, admin_user)

        url = reverse('task-detail', kwargs={'pk': task.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert response.json()['title'] == '详情测试'

    def test_update_task(self, auth_client, admin_user):
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': '原标题'}, admin_user)

        url = reverse('task-detail', kwargs={'pk': task.pk})
        response = auth_client.patch(url, {'title': '新标题'}, format='json')
        assert response.status_code == 200
        assert response.json()['title'] == '新标题'


@pytest.mark.django_db
class TestTaskTransitionAPI:
    """任务状态转换接口测试。"""

    def test_transition_pending_to_in_progress(self, auth_client, admin_user):
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': '状态测试'}, admin_user)

        url = reverse('task-transition', kwargs={'pk': task.pk})
        response = auth_client.post(url, {
            'status': 'IN_PROGRESS',
        }, format='json')
        assert response.status_code == 200
        assert response.json()['status'] == 'IN_PROGRESS'

    def test_invalid_transition(self, auth_client, admin_user):
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': '非法转换测试'}, admin_user)

        # PENDING -> COMPLETED 不合法
        url = reverse('task-transition', kwargs={'pk': task.pk})
        response = auth_client.post(url, {
            'status': 'COMPLETED',
        }, format='json')
        assert response.status_code == 400

    def test_full_lifecycle(self, auth_client, admin_user):
        """完整生命周期: PENDING -> IN_PROGRESS -> IN_REVIEW -> COMPLETED"""
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': '生命周期测试'}, admin_user)
        pk = task.pk

        # PENDING -> IN_PROGRESS
        url = reverse('task-transition', kwargs={'pk': pk})
        r = auth_client.post(url, {'status': 'IN_PROGRESS'}, format='json')
        assert r.status_code == 200

        # IN_PROGRESS -> IN_REVIEW
        r = auth_client.post(url, {'status': 'IN_REVIEW'}, format='json')
        assert r.status_code == 200

        # IN_REVIEW -> COMPLETED
        r = auth_client.post(url, {'status': 'COMPLETED'}, format='json')
        assert r.status_code == 200
        assert r.json()['progress'] == 100


@pytest.mark.django_db
class TestTaskProgressAPI:
    """进度更新接口测试。"""

    def test_update_progress(self, auth_client, admin_user):
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': '进度测试'}, admin_user)

        url = reverse('task-progress', kwargs={'pk': task.pk})
        response = auth_client.post(url, {'progress': 50}, format='json')
        assert response.status_code == 200
        assert response.json()['progress'] == 50

    def test_progress_out_of_range(self, auth_client, admin_user):
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': '超范围测试'}, admin_user)

        url = reverse('task-progress', kwargs={'pk': task.pk})
        response = auth_client.post(url, {'progress': 150}, format='json')
        assert response.status_code == 400


@pytest.mark.django_db
class TestTaskCommentsAPI:
    """评论接口测试。"""

    def test_add_comment(self, auth_client, admin_user):
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': '评论测试'}, admin_user)

        url = reverse('task-comments', kwargs={'pk': task.pk})
        response = auth_client.post(url, {
            'content': '这是一条评论',
        }, format='json')
        assert response.status_code == 201

    def test_list_comments(self, auth_client, admin_user):
        from apps.tasks.services.task_service import TaskService
        task = TaskService.create_task({'title': '评论列表测试'}, admin_user)

        # 添加评论
        url = reverse('task-comments', kwargs={'pk': task.pk})
        auth_client.post(url, {'content': '评论1'}, format='json')

        response = auth_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestKanbanAPI:
    """看板接口测试。"""

    def test_kanban_returns_columns(self, auth_client, admin_user):
        from apps.tasks.services.task_service import TaskService
        TaskService.create_task({'title': '看板任务'}, admin_user)

        url = reverse('task-kanban')
        response = auth_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert 'PENDING' in data
        assert 'IN_PROGRESS' in data
