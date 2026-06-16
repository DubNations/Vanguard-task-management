"""
任务模块扩展测试 — 约 53 个测试用例，覆盖所有场景。
"""
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.tasks.models import Task, TaskHistory, TaskComment
from apps.notifications.models import Notification

BASE_URL = '/api/v1/tasks/'


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def _task_url(task_id=None):
    if task_id is None:
        return BASE_URL
    return f'{BASE_URL}{task_id}/'


def _transition_url(task_id):
    return f'{BASE_URL}{task_id}/transition/'


def _progress_url(task_id):
    return f'{BASE_URL}{task_id}/progress/'


def _history_url(task_id):
    return f'{BASE_URL}{task_id}/history/'


def _comments_url(task_id):
    return f'{BASE_URL}{task_id}/comments/'


KANBAN_URL = f'{BASE_URL}kanban/'


# =========================================================================
# 14a. 任务创建 (15 个)
# =========================================================================
@pytest.mark.django_db
class TestTaskCreate:
    """任务创建边界测试。"""

    # 1. 标题 2 字符 → 成功
    def test_create_title_min_length(self, auth_client):
        resp = auth_client.post(BASE_URL, {'title': 'AB'}, format='json')
        assert resp.status_code == 201
        assert resp.data['title'] == 'AB'

    # 2. 标题 1 字符 → 400
    def test_create_title_too_short(self, auth_client):
        resp = auth_client.post(BASE_URL, {'title': 'A'}, format='json')
        assert resp.status_code == 400
        assert 'error' in resp.data

    # 3. 标题 200 字符 → 成功
    def test_create_title_max_length(self, auth_client):
        title = '测' * 200
        resp = auth_client.post(BASE_URL, {'title': title}, format='json')
        assert resp.status_code == 201
        assert resp.data['title'] == title

    # 4. 标题超 200 字符 → 400
    def test_create_title_exceeds_max(self, auth_client):
        title = '测' * 201
        resp = auth_client.post(BASE_URL, {'title': title}, format='json')
        assert resp.status_code == 400

    # 5. 标题纯空格 → 400
    def test_create_title_spaces_only(self, auth_client):
        resp = auth_client.post(BASE_URL, {'title': '    '}, format='json')
        assert resp.status_code == 400

    # 6. 标题特殊字符(中文) → 成功
    def test_create_title_chinese(self, auth_client):
        resp = auth_client.post(BASE_URL, {'title': '测试任务一'}, format='json')
        assert resp.status_code == 201

    # 7. 标题含 emoji → 成功
    def test_create_title_emoji(self, auth_client):
        resp = auth_client.post(BASE_URL, {'title': '任务🚀发射'}, format='json')
        assert resp.status_code == 201

    # 8. 标题含 HTML 标签 → 成功(原样存储)
    def test_create_title_html(self, auth_client):
        title = '<b>加粗</b>任务'
        resp = auth_client.post(BASE_URL, {'title': title}, format='json')
        assert resp.status_code == 201
        assert resp.data['title'] == title

    # 9. 指定有效 assignee → 成功
    def test_create_with_valid_assignee(self, auth_client, regular_user):
        resp = auth_client.post(
            BASE_URL,
            {'title': '分配任务', 'assignee': str(regular_user.id)},
            format='json',
        )
        assert resp.status_code == 201
        assert str(resp.data['assignee']) == str(regular_user.id)

    # 10. 指定无效 assignee UUID → 400
    def test_create_with_invalid_assignee(self, auth_client):
        resp = auth_client.post(
            BASE_URL,
            {'title': '无效分配', 'assignee': str(uuid.uuid4())},
            format='json',
        )
        assert resp.status_code == 400

    # 11. 截止日期为未来 → 成功
    def test_create_future_deadline(self, auth_client):
        deadline = (timezone.now() + timedelta(days=30)).isoformat()
        resp = auth_client.post(
            BASE_URL,
            {'title': '未来截止', 'deadline': deadline},
            format='json',
        )
        assert resp.status_code == 201

    # 12. 截止日期为过去 → 成功(不校验)
    def test_create_past_deadline(self, auth_client):
        deadline = (timezone.now() - timedelta(days=30)).isoformat()
        resp = auth_client.post(
            BASE_URL,
            {'title': '过去截止', 'deadline': deadline},
            format='json',
        )
        assert resp.status_code == 201

    # 13. 所有 priority 值 → 成功
    @pytest.mark.parametrize('priority', ['LOW', 'MEDIUM', 'HIGH', 'URGENT'])
    def test_create_all_priorities(self, auth_client, priority):
        resp = auth_client.post(
            BASE_URL,
            {'title': f'{priority}任务', 'priority': priority},
            format='json',
        )
        assert resp.status_code == 201
        assert resp.data['priority'] == priority

    # 14. 不存在 priority → 400
    def test_create_invalid_priority(self, auth_client):
        resp = auth_client.post(
            BASE_URL,
            {'title': '无效优先级', 'priority': 'EXTREME'},
            format='json',
        )
        assert resp.status_code == 400

    # 15. 创建触发 TASK_ASSIGNED 通知
    def test_create_triggers_notification(self, auth_client, admin_user, regular_user):
        resp = auth_client.post(
            BASE_URL,
            {'title': '通知测试', 'assignee': str(regular_user.id)},
            format='json',
        )
        assert resp.status_code == 201
        assert Notification.objects.filter(
            recipient=regular_user,
            type=Notification.Type.TASK_ASSIGNED,
        ).exists()


# =========================================================================
# 14b. 状态转换全矩阵 (13 个, 含参数化)
# =========================================================================
@pytest.mark.django_db
class TestTaskTransition:
    """状态机转换测试。"""

    # 合法转换参数化: P→IP, P→C, IP→IR, IP→P, IP→C, IR→COMPLETED, IR→REJECTED, REJ→IP
    @pytest.mark.parametrize('from_status,to_status,setup_transitions', [
        ('PENDING', 'IN_PROGRESS', []),
        ('PENDING', 'CANCELLED', []),
        ('IN_PROGRESS', 'IN_REVIEW', ['IN_PROGRESS']),
        ('IN_PROGRESS', 'PENDING', ['IN_PROGRESS']),
        ('IN_PROGRESS', 'CANCELLED', ['IN_PROGRESS']),
        ('IN_REVIEW', 'COMPLETED', ['IN_PROGRESS', 'IN_REVIEW']),
        ('IN_REVIEW', 'REJECTED', ['IN_PROGRESS', 'IN_REVIEW']),
        ('REJECTED', 'IN_PROGRESS', ['IN_PROGRESS', 'IN_REVIEW', 'REJECTED']),
    ])
    def test_valid_transition(
        self, auth_client, sample_task, from_status, to_status, setup_transitions
    ):
        # 先把任务转到 from_status
        task = sample_task
        for intermediate in setup_transitions:
            task = _do_transition_direct(task, intermediate)
        assert task.status == from_status

        resp = _post_transition(auth_client, task.id, to_status)
        assert resp.status_code == 200
        assert resp.data['status'] == to_status

    # 非法转换参数化: P→IR, P→COMPLETED, P→REJECTED, IP→COMPLETED, IR→IP
    @pytest.mark.parametrize('from_status,to_status,setup_transitions', [
        ('PENDING', 'IN_REVIEW', []),
        ('PENDING', 'COMPLETED', []),
        ('PENDING', 'REJECTED', []),
        ('IN_PROGRESS', 'COMPLETED', ['IN_PROGRESS']),
        ('IN_REVIEW', 'IN_PROGRESS', ['IN_PROGRESS', 'IN_REVIEW']),
    ])
    def test_invalid_transition(
        self, auth_client, sample_task, from_status, to_status, setup_transitions
    ):
        task = sample_task
        for intermediate in setup_transitions:
            task = _do_transition_direct(task, intermediate)
        assert task.status == from_status

        resp = _post_transition(auth_client, task.id, to_status)
        assert resp.status_code == 400
        assert 'error' in resp.data

    # 29. 不存在任务 → 404
    def test_transition_nonexistent_task(self, auth_client):
        fake_id = uuid.uuid4()
        resp = _post_transition(auth_client, fake_id, 'IN_PROGRESS')
        assert resp.status_code == 404
        assert resp.data['error'] == '任务不存在'

    # 30. 无效 status 值 → 400
    def test_transition_invalid_status_value(self, auth_client, sample_task):
        resp = _post_transition(auth_client, sample_task.id, 'NONEXISTENT')
        assert resp.status_code == 400

    # 31. 带 note 的转换
    def test_transition_with_note(self, auth_client, sample_task):
        resp = _post_transition(auth_client, sample_task.id, 'IN_PROGRESS', note='开始处理')
        assert resp.status_code == 200
        # 检查历史中记录了 note
        hist = TaskHistory.objects.filter(
            task=sample_task, action=TaskHistory.Action.STATUS_CHANGE
        ).first()
        assert hist is not None
        assert hist.note == '开始处理'


# =========================================================================
# 14c. 进度 (6 个)
# =========================================================================
@pytest.mark.django_db
class TestTaskProgress:
    """进度更新测试。"""

    # 32. progress=0 → 成功
    def test_progress_zero(self, auth_client, sample_task):
        resp = auth_client.post(
            _progress_url(sample_task.id), {'progress': 0}, format='json'
        )
        assert resp.status_code == 200
        assert resp.data['progress'] == 0

    # 33. progress=100 → 成功
    def test_progress_hundred(self, auth_client, sample_task):
        resp = auth_client.post(
            _progress_url(sample_task.id), {'progress': 100}, format='json'
        )
        assert resp.status_code == 200
        assert resp.data['progress'] == 100

    # 34. progress=-1 → 400
    def test_progress_negative(self, auth_client, sample_task):
        resp = auth_client.post(
            _progress_url(sample_task.id), {'progress': -1}, format='json'
        )
        assert resp.status_code == 400

    # 35. progress=101 → 400
    def test_progress_over_hundred(self, auth_client, sample_task):
        resp = auth_client.post(
            _progress_url(sample_task.id), {'progress': 101}, format='json'
        )
        assert resp.status_code == 400

    # 36. progress 不变 → 不创建 history
    def test_progress_no_change_no_history(self, auth_client, sample_task):
        # sample_task progress 默认为 0，再设 0
        before_count = TaskHistory.objects.filter(task=sample_task).count()
        resp = auth_client.post(
            _progress_url(sample_task.id), {'progress': 0}, format='json'
        )
        assert resp.status_code == 200
        after_count = TaskHistory.objects.filter(task=sample_task).count()
        assert after_count == before_count

    # 37. progress 非数字 → 400
    def test_progress_non_numeric(self, auth_client, sample_task):
        resp = auth_client.post(
            _progress_url(sample_task.id), {'progress': 'abc'}, format='json'
        )
        assert resp.status_code == 400


# =========================================================================
# 14d. 评论 (5 个)
# =========================================================================
@pytest.mark.django_db
class TestTaskComment:
    """评论功能测试。"""

    # 38. 空内容 → 400
    def test_comment_empty_content(self, auth_client, sample_task):
        resp = auth_client.post(
            _comments_url(sample_task.id), {'content': ''}, format='json'
        )
        assert resp.status_code == 400

    # 39. 纯空格 → 400
    def test_comment_spaces_only(self, auth_client, sample_task):
        resp = auth_client.post(
            _comments_url(sample_task.id), {'content': '   '}, format='json'
        )
        assert resp.status_code == 400

    # 40. 内部评论 MEMBER 不可见(列表过滤)
    def test_internal_comment_hidden_from_member(self, auth_client, member_client, sample_task):
        # 管理员添加内部评论
        auth_client.post(
            _comments_url(sample_task.id),
            {'content': '内部讨论', 'is_internal': True},
            format='json',
        )
        # MEMBER 查看列表看不到
        resp = member_client.get(_comments_url(sample_task.id), format='json')
        assert resp.status_code == 200
        results = resp.data.get('results', resp.data)
        assert len(results) == 0

    # 41. 内部评论 LEADER 可见
    def test_internal_comment_visible_to_leader(self, auth_client, leader_client, sample_task):
        auth_client.post(
            _comments_url(sample_task.id),
            {'content': '内部讨论', 'is_internal': True},
            format='json',
        )
        resp = leader_client.get(_comments_url(sample_task.id), format='json')
        assert resp.status_code == 200
        results = resp.data.get('results', resp.data)
        assert len(results) == 1
        assert results[0]['is_internal'] is True

    # 42. 评论创建 history 记录
    def test_comment_creates_history(self, auth_client, sample_task):
        auth_client.post(
            _comments_url(sample_task.id),
            {'content': '有记录的评论'},
            format='json',
        )
        assert TaskHistory.objects.filter(
            task=sample_task, action=TaskHistory.Action.COMMENTED
        ).exists()


# =========================================================================
# 14e. 历史 (3 个)
# =========================================================================
@pytest.mark.django_db
class TestTaskHistory:
    """任务历史记录测试。"""

    # 43. CREATED 记录存在
    def test_created_history_exists(self, auth_client, sample_task):
        resp = auth_client.get(_history_url(sample_task.id), format='json')
        assert resp.status_code == 200
        results = resp.data.get('results', resp.data)
        actions = [h['action'] for h in results]
        assert 'CREATED' in actions

    # 44. UPDATED 包含 diff
    def test_updated_history_has_diff(self, auth_client, sample_task):
        # 更新标题
        auth_client.patch(
            _task_url(sample_task.id),
            {'title': '新标题'},
            format='json',
        )
        resp = auth_client.get(_history_url(sample_task.id), format='json')
        results = resp.data.get('results', resp.data)
        updated = [h for h in results if h['action'] == 'UPDATED']
        assert len(updated) >= 1
        diff = updated[0]['diff']
        assert 'title' in diff

    # 45. 按时间倒序排列
    def test_history_ordered_by_time_desc(self, auth_client, sample_task):
        # 多做一些操作
        auth_client.patch(
            _task_url(sample_task.id), {'title': '第二次标题'}, format='json'
        )
        resp = auth_client.get(_history_url(sample_task.id), format='json')
        results = resp.data.get('results', resp.data)
        dates = [h['created_at'] for h in results]
        assert dates == sorted(dates, reverse=True)


# =========================================================================
# 14f. 看板与列表 (5 个)
# =========================================================================
@pytest.mark.django_db
class TestKanbanAndList:
    """看板和列表视图测试。"""

    # 46. 空看板
    def test_empty_kanban(self, auth_client):
        resp = auth_client.get(KANBAN_URL, format='json')
        assert resp.status_code == 200
        # 所有列的 count 为 0
        for col_data in resp.data.values():
            assert col_data['count'] == 0

    # 47. CANCELLED 排除在看板外
    def test_kanban_excludes_cancelled(self, auth_client, sample_task):
        _do_transition_direct(sample_task, 'CANCELLED')
        resp = auth_client.get(KANBAN_URL, format='json')
        assert resp.status_code == 200
        assert resp.data['CANCELLED']['count'] == 0

    # 48. MEMBER 只看自己
    def test_member_sees_only_own_tasks(self, auth_client, member_client, regular_user, admin_user):
        # admin 创建一个无负责人的任务
        auth_client.post(BASE_URL, {'title': '管理员任务'}, format='json')
        # admin 创建一个分配给 member 的任务
        auth_client.post(BASE_URL, {'title': '成员任务', 'assignee': str(regular_user.pk)}, format='json')

        resp = member_client.get(BASE_URL, format='json')
        results = resp.data.get('results', resp.data)
        # MEMBER 只能看到分配给自己的任务
        titles = [t['title'] for t in results]
        assert '成员任务' in titles
        assert '管理员任务' not in titles

    # 49. 按 status 过滤
    def test_list_filter_by_status(self, auth_client, sample_task):
        # sample_task 是 PENDING
        auth_client.post(BASE_URL, {'title': '另一个任务'}, format='json')
        resp = auth_client.get(BASE_URL, {'status': 'PENDING'}, format='json')
        assert resp.status_code == 200

    # 50. 分页
    def test_list_pagination(self, auth_client):
        for i in range(12):
            auth_client.post(BASE_URL, {'title': f'分页任务{i:02d}'}, format='json')
        resp = auth_client.get(BASE_URL, format='json')
        assert resp.status_code == 200
        # 有分页结构
        assert 'results' in resp.data or 'count' in resp.data


# =========================================================================
# 14g. 更新 (3 个)
# =========================================================================
@pytest.mark.django_db
class TestTaskUpdate:
    """任务更新测试。"""

    # 51. 更新 title + history diff
    def test_update_title_with_diff(self, auth_client, sample_task):
        resp = auth_client.patch(
            _task_url(sample_task.id),
            {'title': '更新后的标题'},
            format='json',
        )
        assert resp.status_code == 200
        hist = TaskHistory.objects.filter(
            task=sample_task, action=TaskHistory.Action.UPDATED
        ).first()
        assert hist is not None
        assert 'title' in hist.diff

    # 52. 相同值不创建 history
    def test_update_same_value_no_history(self, auth_client, sample_task):
        original_title = sample_task.title
        before_count = TaskHistory.objects.filter(
            task=sample_task, action=TaskHistory.Action.UPDATED
        ).count()
        auth_client.patch(
            _task_url(sample_task.id),
            {'title': original_title},
            format='json',
        )
        after_count = TaskHistory.objects.filter(
            task=sample_task, action=TaskHistory.Action.UPDATED
        ).count()
        assert after_count == before_count

    # 53. 不存在任务
    def test_update_nonexistent_task(self, auth_client):
        fake_id = uuid.uuid4()
        resp = auth_client.patch(
            _task_url(fake_id),
            {'title': '不存在的'},
            format='json',
        )
        assert resp.status_code == 404


# =========================================================================
# 辅助函数 (模块级)
# =========================================================================
def _do_transition_direct(task, new_status):
    """直接通过 TaskService 转换状态，不走 HTTP。"""
    from apps.tasks.services.task_service import TaskService
    from apps.accounts.models import User
    # 用 creator 作为操作人
    return TaskService.transition_status(task, new_status, task.creator)


def _post_transition(client, task_id, new_status, note=''):
    """通过 API 提交状态转换。"""
    data = {'status': new_status}
    if note:
        data['note'] = note
    return client.post(_transition_url(task_id), data, format='json')
