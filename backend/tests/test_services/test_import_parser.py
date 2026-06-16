"""
import_parser 单元测试。
"""
import pytest
from types import SimpleNamespace


@pytest.mark.django_db
class TestImportParser:
    """测试导入解析器。"""

    # ------------------------------------------------------------------
    # parse_import_file
    # ------------------------------------------------------------------
    def test_parse_xlsx_valid(self, sample_xlsx):
        """解析有效 xlsx 文件。"""
        from apps.imports.services.import_parser import parse_import_file

        session = SimpleNamespace(
            file=SimpleNamespace(path=str(sample_xlsx)),
            file_format='xlsx',
        )
        result = parse_import_file(session)
        assert result['total_rows'] == 3
        assert result['valid_rows'] == 3
        assert result['error_rows'] == 0
        assert len(result['preview_data']) == 3

    def test_parse_csv_valid(self, sample_csv_file):
        """解析有效 csv 文件。"""
        from apps.imports.services.import_parser import parse_import_file

        session = SimpleNamespace(
            file=SimpleNamespace(path=str(sample_csv_file)),
            file_format='csv',
        )
        result = parse_import_file(session)
        assert result['total_rows'] == 2
        assert result['valid_rows'] == 2
        assert len(result['preview_data']) == 2

    def test_parse_unsupported_format(self, txt_file):
        """不支持的格式抛出 ValueError。"""
        from apps.imports.services.import_parser import parse_import_file

        session = SimpleNamespace(
            file=SimpleNamespace(path=str(txt_file)),
            file_format='txt',
        )
        with pytest.raises(ValueError, match='不支持的文件格式'):
            parse_import_file(session)

    def test_parse_empty_file(self, empty_file):
        """空 xlsx 文件返回 empty_result。"""
        from apps.imports.services.import_parser import parse_import_file

        session = SimpleNamespace(
            file=SimpleNamespace(path=str(empty_file)),
            file_format='xlsx',
        )
        result = parse_import_file(session)
        assert result['total_rows'] == 0
        assert result['valid_rows'] == 0

    # ------------------------------------------------------------------
    # _build_mapping
    # ------------------------------------------------------------------
    def test_build_mapping_chinese_headers(self):
        """中文列名正确映射。"""
        from apps.imports.services.import_parser import _build_mapping

        mapping = _build_mapping(['标题', '负责人', '优先级'])
        assert mapping['标题'] == 'title'
        assert mapping['负责人'] == 'assignee_name'
        assert mapping['优先级'] == 'priority'

    def test_build_mapping_english_headers(self):
        """英文列名正确映射。"""
        from apps.imports.services.import_parser import _build_mapping

        mapping = _build_mapping(['title', 'assignee', 'priority'])
        assert mapping['title'] == 'title'
        assert mapping['assignee'] == 'assignee_name'
        assert mapping['priority'] == 'priority'

    # ------------------------------------------------------------------
    # _validate_row
    # ------------------------------------------------------------------
    def test_validate_row_empty_title(self):
        """空标题返回错误。"""
        from apps.imports.services.import_parser import _validate_row

        errors = _validate_row(2, {'title': '', 'priority': 'HIGH'})
        assert len(errors) == 1
        assert errors[0]['field'] == 'title'

    def test_validate_row_invalid_priority(self):
        """无效优先级返回错误。"""
        from apps.imports.services.import_parser import _validate_row

        errors = _validate_row(3, {'title': 'Good', 'priority': 'SUPER_URGENT'})
        assert len(errors) == 1
        assert errors[0]['field'] == 'priority'

    def test_validate_row_valid_data(self):
        """有效数据无错误。"""
        from apps.imports.services.import_parser import _validate_row

        errors = _validate_row(4, {'title': 'Valid Task', 'priority': 'HIGH'})
        assert len(errors) == 0

    # ------------------------------------------------------------------
    # xlsx with errors
    # ------------------------------------------------------------------
    def test_xlsx_with_errors_returns_correct_error_rows(self, sample_xlsx_with_errors):
        """含错误行的 xlsx 文件正确标记错误行。"""
        from apps.imports.services.import_parser import parse_import_file

        session = SimpleNamespace(
            file=SimpleNamespace(path=str(sample_xlsx_with_errors)),
            file_format='xlsx',
        )
        result = parse_import_file(session)
        assert result['total_rows'] == 3
        assert result['error_rows'] == 2
        assert result['valid_rows'] == 1
        assert len(result['errors']) >= 2
