"""
import_executor 单元测试。
"""
import uuid
import pytest
from unittest.mock import MagicMock


@pytest.mark.django_db
class TestImportExecutor:
    """测试导入执行器。"""

    def _make_session(self, preview_data, file_format='xlsx', original_name='test.xlsx'):
        session = MagicMock()
        session.preview_data = preview_data
        session.file_format = file_format
        session.original_name = original_name
        session.id = uuid.uuid4()
        return session

    # ------------------------------------------------------------------
    # execute_import
    # ------------------------------------------------------------------
    def test_execute_creates_valid_tasks(self, admin_user):
        """执行导入创建有效任务。"""
        from apps.imports.services.import_executor import execute_import
        from apps.tasks.models import Task

        preview = [
            {'row': 2, 'data': {'title': '导入任务A', 'priority': '高'}, 'valid': True},
            {'row': 3, 'data': {'title': '导入任务B', 'priority': '中'}, 'valid': True},
        ]
        session = self._make_session(preview)
        result = execute_import(session, admin_user)
        assert len(result['task_ids']) == 2
        assert Task.objects.count() == 2

    def test_skip_invalid_rows(self, admin_user):
        """跳过 valid=False 的行。"""
        from apps.imports.services.import_executor import execute_import
        from apps.tasks.models import Task

        preview = [
            {'row': 2, 'data': {'title': '有效'}, 'valid': True},
            {'row': 3, 'data': {'title': ''}, 'valid': False},
        ]
        session = self._make_session(preview)
        result = execute_import(session, admin_user)
        assert len(result['task_ids']) == 1
        assert Task.objects.count() == 1

    def test_chinese_priority_mapping(self, admin_user):
        """中文优先级正确映射。"""
        from apps.imports.services.import_executor import execute_import
        from apps.tasks.models import Task

        preview = [
            {'row': 2, 'data': {'title': '紧急任务', 'priority': '紧急'}, 'valid': True},
        ]
        session = self._make_session(preview)
        execute_import(session, admin_user)
        task = Task.objects.first()
        assert task.priority == 'URGENT'

    def test_english_priority_mapping(self, admin_user):
        """英文优先级正确映射。"""
        from apps.imports.services.import_executor import execute_import
        from apps.tasks.models import Task

        preview = [
            {'row': 2, 'data': {'title': 'High Task', 'priority': 'HIGH'}, 'valid': True},
        ]
        session = self._make_session(preview)
        execute_import(session, admin_user)
        task = Task.objects.first()
        assert task.priority == 'HIGH'

    def test_assignee_not_found(self, admin_user):
        """负责人不存在时 assignee 为 None。"""
        from apps.imports.services.import_executor import execute_import
        from apps.tasks.models import Task

        preview = [
            {'row': 2, 'data': {'title': 'No One', 'assignee_name': '不存在的人'}, 'valid': True},
        ]
        session = self._make_session(preview)
        execute_import(session, admin_user)
        task = Task.objects.first()
        assert task.assignee is None

    def test_source_marked_correctly(self, admin_user):
        """source 标记为 IMPORT:xlsx。"""
        from apps.imports.services.import_executor import execute_import
        from apps.tasks.models import Task

        preview = [
            {'row': 2, 'data': {'title': 'Source Test'}, 'valid': True},
        ]
        session = self._make_session(preview, file_format='xlsx')
        execute_import(session, admin_user)
        task = Task.objects.first()
        assert task.source == 'IMPORT:xlsx'

    def test_imported_history_recorded(self, admin_user):
        """IMPORTED 历史记录创建。"""
        from apps.imports.services.import_executor import execute_import
        from apps.tasks.models import Task, TaskHistory

        preview = [
            {'row': 2, 'data': {'title': 'History Test'}, 'valid': True},
        ]
        session = self._make_session(preview)
        execute_import(session, admin_user)
        task = Task.objects.first()
        history = TaskHistory.objects.filter(task=task, action='IMPORTED')
        assert history.exists()

    def test_empty_preview_data(self, admin_user):
        """空 preview_data 无任务创建。"""
        from apps.imports.services.import_executor import execute_import
        from apps.tasks.models import Task

        session = self._make_session([])
        result = execute_import(session, admin_user)
        assert result['task_ids'] == []
        assert Task.objects.count() == 0
