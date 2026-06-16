"""
TaskFile 模型单元测试。
"""
import io
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db
class TestTaskFileModel:
    """测试 TaskFile 模型静态方法。"""

    # ------------------------------------------------------------------
    # detect_file_type
    # ------------------------------------------------------------------
    def test_detect_docx(self):
        """.docx -> DOCUMENT"""
        from apps.files.models import TaskFile
        assert TaskFile.detect_file_type('report.docx') == 'DOCUMENT'

    def test_detect_png(self):
        """.png -> IMAGE"""
        from apps.files.models import TaskFile
        assert TaskFile.detect_file_type('screenshot.png') == 'IMAGE'

    def test_detect_xlsx(self):
        """.xlsx -> EXCEL"""
        from apps.files.models import TaskFile
        assert TaskFile.detect_file_type('data.xlsx') == 'EXCEL'

    def test_detect_wps(self):
        """.wps -> WPS"""
        from apps.files.models import TaskFile
        assert TaskFile.detect_file_type('letter.wps') == 'WPS'

    def test_detect_pdf(self):
        """.pdf -> PDF"""
        from apps.files.models import TaskFile
        assert TaskFile.detect_file_type('manual.pdf') == 'PDF'

    def test_detect_exe(self):
        """.exe -> OTHER"""
        from apps.files.models import TaskFile
        assert TaskFile.detect_file_type('virus.exe') == 'OTHER'

    def test_detect_no_extension(self):
        """无扩展名 -> OTHER"""
        from apps.files.models import TaskFile
        assert TaskFile.detect_file_type('Makefile') == 'OTHER'

    def test_detect_uppercase_extension(self):
        """大写扩展名也能识别 (.DOCX -> DOCUMENT)。"""
        from apps.files.models import TaskFile
        assert TaskFile.detect_file_type('Report.DOCX') == 'DOCUMENT'

    # ------------------------------------------------------------------
    # compute_sha256
    # ------------------------------------------------------------------
    def test_compute_sha256_correctness(self):
        """SHA256 计算结果正确。"""
        from apps.files.models import TaskFile
        import hashlib

        content = b'hello world'
        expected = hashlib.sha256(content).hexdigest()
        file_obj = SimpleUploadedFile('test.txt', content)
        result = TaskFile.compute_sha256(file_obj)
        assert result == expected

    def test_compute_sha256_consistency(self):
        """相同内容得到相同哈希值。"""
        from apps.files.models import TaskFile

        content = b'consistent data'
        f1 = SimpleUploadedFile('a.txt', content)
        f2 = SimpleUploadedFile('b.txt', content)
        assert TaskFile.compute_sha256(f1) == TaskFile.compute_sha256(f2)
