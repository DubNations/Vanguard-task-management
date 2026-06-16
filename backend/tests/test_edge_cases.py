"""边界与错误处理测试。"""
import json
import uuid
import threading

import pytest
from django.utils import timezone


# ---------------------------------------------------------------------------
# 自定义异常处理器
# ---------------------------------------------------------------------------
class TestCustomExceptionHandler:
    """验证 custom_exception_handler 统一错误格式。"""

    def test_404_returns_standard_error_format(self, auth_client):
        """404 → {error: {code, message}} 标准格式（DRF 视图内触发）。"""
        import uuid as _uuid
        nonexistent_uuid = _uuid.uuid4()
        resp = auth_client.get(f'/api/v1/tasks/{nonexistent_uuid}/')
        assert resp.status_code == 404
        data = resp.json()
        assert 'error' in data
        assert 'code' in data['error']
        assert 'message' in data['error']
        assert data['error']['code'] == 404

    def test_500_no_stack_trace_in_response(self, auth_client, admin_user):
        """500 内部错误 → 标准格式，无堆栈信息。"""
        # 构造一个会触发服务器内部错误的请求（通过 mock）
        from unittest.mock import patch
        with patch('apps.tasks.views.TaskListView.get_queryset') as mock_qs:
            mock_qs.side_effect = RuntimeError('模拟内部错误')
            resp = auth_client.get('/api/v1/tasks/')
        assert resp.status_code == 500
        data = resp.json()
        assert 'error' in data
        assert data['error']['code'] == 500
        # 确认不包含堆栈信息
        assert 'Traceback' not in json.dumps(data)
        assert 'RuntimeError' not in json.dumps(data)


# ---------------------------------------------------------------------------
# 请求格式错误
# ---------------------------------------------------------------------------
class TestRequestFormatErrors:
    """请求格式错误处理。"""

    def test_empty_json_body_post(self, auth_client):
        """空 JSON body POST → 400。"""
        resp = auth_client.post(
            '/api/v1/tasks/',
            data='{}',
            content_type='application/json',
        )
        assert resp.status_code == 400

    def test_non_json_content_type(self, auth_client):
        """非 JSON Content-Type 发往 JSON 端点 → 适当错误响应。"""
        resp = auth_client.post(
            '/api/v1/tasks/',
            data='title=plain text task',
            content_type='text/plain',
        )
        # DRF 可能返回 400（无法解析）或 415（Unsupported Media Type）
        assert resp.status_code in (400, 415)

    def test_invalid_uuid_path_parameter(self, auth_client):
        """无效 UUID 路径参数 → 400 或 404，不是 500。"""
        resp = auth_client.get('/api/v1/tasks/invalid-uuid-format/')
        assert resp.status_code in (400, 404)
        assert resp.status_code != 500


# ---------------------------------------------------------------------------
# 并发与一致性
# ---------------------------------------------------------------------------
class TestConcurrency:
    """并发场景测试。"""

    def test_concurrent_task_creation_uniqueness(self, admin_user, db):
        """并发创建任务 → task_no 唯一性。"""
        from apps.tasks.services.task_service import TaskService
        results = []
        errors = []

        def create_task(title):
            try:
                task = TaskService.create_task({'title': title}, admin_user)
                results.append(task.task_no)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=create_task, args=(f'并发任务{i}',))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有任务应该有不同的 task_no（或某些因唯一约束冲突而失败）
        # 成功创建的任务编号应唯一
        assert len(set(results)) == len(results), 'task_no 存在重复'

    def test_concurrent_status_transitions(self, admin_user, sample_task, db):
        """并发状态转换 → 数据库一致性。"""
        from apps.tasks.services.task_service import TaskService
        from apps.tasks.models import Task

        errors = []

        def try_transition(new_status):
            try:
                # 重新获取最新对象
                task = Task.objects.get(pk=sample_task.pk)
                TaskService.transition_status(task, new_status, admin_user)
            except (ValueError, Exception) as e:
                errors.append(str(e))

        # PENDING → IN_PROGRESS (合法) 和 PENDING → COMPLETED (非法)
        t1 = threading.Thread(target=try_transition, args=('IN_PROGRESS',))
        t2 = threading.Thread(target=try_transition, args=('COMPLETED',))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # 验证数据库中的状态是合法的
        task = Task.objects.get(pk=sample_task.pk)
        assert task.status in [s[0] for s in Task.Status.choices]


# ---------------------------------------------------------------------------
# 特殊数据处理
# ---------------------------------------------------------------------------
class TestSpecialData:
    """特殊数据处理测试。"""

    def test_unicode_field_handling(self, auth_client):
        """中文/日文/emoji → 正确存储和返回。"""
        unicode_title = '测试任务テスト 🚀🎉 emoji task'
        resp = auth_client.post('/api/v1/tasks/', {
            'title': unicode_title,
            'description': '含中文描述：任务详情 📝',
        }, format='json')
        assert resp.status_code == 201
        task_id = resp.data['id']

        # 获取并验证
        resp2 = auth_client.get(f'/api/v1/tasks/{task_id}/')
        assert resp2.status_code == 200
        assert resp2.data['title'] == unicode_title
        assert '📝' in resp2.data['description']

    def test_timezone_handling_for_deadline(self, auth_client):
        """截止日期带时区信息 → 正确存储。"""
        deadline_str = '2027-12-31T23:59:59+08:00'
        resp = auth_client.post('/api/v1/tasks/', {
            'title': '带时区的任务',
            'deadline': deadline_str,
        }, format='json')
        assert resp.status_code == 201

        from apps.tasks.models import Task
        task = Task.objects.get(id=resp.data['id'])
        # 验证 deadline 带时区信息
        assert task.deadline is not None
        assert timezone.is_aware(task.deadline), 'deadline 应包含时区信息'

    def test_oversized_json_payload(self, auth_client):
        """超大 JSON 载荷 → 被适当处理（不是 500）。"""
        # 生成一个超过一般限制的大 payload
        big_data = {
            'title': '大载荷任务',
            'description': 'x' * 100000,  # 100KB description
        }
        resp = auth_client.post(
            '/api/v1/tasks/',
            data=json.dumps(big_data),
            content_type='application/json',
        )
        # 无论成功还是被拒绝，都不应是 500
        assert resp.status_code != 500
