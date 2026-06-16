"""文件操作测试 — 上传/下载/删除附件。"""
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.files.models import TaskFile
from apps.tasks.services.task_service import TaskService


@pytest.mark.django_db
class TestFileUpload:
    """文件上传测试。"""

    def test_upload_docx(self, auth_client, admin_user, sample_task, media_root):
        """上传 .docx → file_type=DOCUMENT, sha256 非空。"""
        f = SimpleUploadedFile(
            'test.docx', b'docx content here',
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        assert response.status_code == 201
        data = response.json()
        assert data['file_type'] == 'DOCUMENT'
        assert len(data['sha256']) == 64

    def test_upload_png(self, auth_client, admin_user, sample_task, media_root):
        """上传 .png → file_type=IMAGE。"""
        f = SimpleUploadedFile('test.png', b'\x89PNG\r\n\x1a\n', content_type='image/png')
        response = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        assert response.status_code == 201
        assert response.json()['file_type'] == 'IMAGE'

    def test_upload_xlsx(self, auth_client, admin_user, sample_task, media_root):
        """上传 .xlsx → file_type=EXCEL。"""
        f = SimpleUploadedFile(
            'test.xlsx', b'PK\x03\x04xlsx content',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        assert response.status_code == 201
        assert response.json()['file_type'] == 'EXCEL'

    def test_upload_pdf(self, auth_client, admin_user, sample_task, media_root):
        """上传 .pdf → file_type=PDF。"""
        f = SimpleUploadedFile('test.pdf', b'%PDF-1.4 fake pdf', content_type='application/pdf')
        response = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        assert response.status_code == 201
        assert response.json()['file_type'] == 'PDF'

    def test_upload_exe_blocked(self, auth_client, admin_user, sample_task, media_root):
        """上传 .exe → 400（危险扩展名被拒绝）。"""
        f = SimpleUploadedFile('test.exe', b'MZ\x90\x00 exe content', content_type='application/octet-stream')
        response = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        assert response.status_code == 400

    def test_upload_without_file(self, auth_client, admin_user, sample_task, media_root):
        """不传文件字段 → 400。"""
        response = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {},
            format='multipart',
        )
        assert response.status_code == 400
        assert '请选择文件' in response.json()['error']

    def test_upload_over_50mb(self, auth_client, admin_user, sample_task, media_root):
        """上传超过 50MB → 400。"""
        big_content = b'\x00' * (50 * 1024 * 1024 + 1)
        f = SimpleUploadedFile('bigfile.bin', big_content, content_type='application/octet-stream')
        response = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        assert response.status_code == 400
        assert '50MB' in response.json()['error']

    def test_upload_to_nonexistent_task(self, auth_client, admin_user, media_root):
        """上传到不存在的任务 → 404。"""
        f = SimpleUploadedFile('test.txt', b'hello', content_type='text/plain')
        response = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': uuid.uuid4()}),
            {'file': f},
            format='multipart',
        )
        assert response.status_code == 404

    def test_sha256_consistency(self, auth_client, admin_user, sample_task, media_root):
        """相同文件 → 相同 SHA256。"""
        content = b'same content for hash'
        f1 = SimpleUploadedFile('file1.txt', content, content_type='text/plain')
        resp1 = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f1},
            format='multipart',
        )
        f2 = SimpleUploadedFile('file2.txt', content, content_type='text/plain')
        resp2 = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f2},
            format='multipart',
        )
        assert resp1.json()['sha256'] == resp2.json()['sha256']

    def test_sha256_different_files(self, auth_client, admin_user, sample_task, media_root):
        """不同文件 → 不同 SHA256。"""
        f1 = SimpleUploadedFile('a.txt', b'content A', content_type='text/plain')
        resp1 = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f1},
            format='multipart',
        )
        f2 = SimpleUploadedFile('b.txt', b'content B', content_type='text/plain')
        resp2 = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f2},
            format='multipart',
        )
        assert resp1.json()['sha256'] != resp2.json()['sha256']

    def test_upload_wps(self, auth_client, admin_user, sample_task, media_root):
        """上传 .wps → file_type=WPS。"""
        f = SimpleUploadedFile('test.wps', b'wps file content', content_type='application/octet-stream')
        response = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        assert response.status_code == 201
        assert response.json()['file_type'] == 'WPS'

    def test_upload_empty_file(self, auth_client, admin_user, sample_task, media_root):
        """上传 0 字节空文件 → 验证行为。"""
        f = SimpleUploadedFile('empty.txt', b'', content_type='text/plain')
        response = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        # 空文件仍然可以上传成功（视业务逻辑而定）
        assert response.status_code in (201, 400)

    def test_no_extension_file(self, auth_client, admin_user, sample_task, media_root):
        """无扩展名文件 → file_type=OTHER。"""
        f = SimpleUploadedFile('noext', b'some content', content_type='application/octet-stream')
        response = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        assert response.status_code == 201
        assert response.json()['file_type'] == 'OTHER'

    def test_uppercase_extension(self, auth_client, admin_user, sample_task, media_root):
        """大写扩展名 .PNG → IMAGE。"""
        f = SimpleUploadedFile('photo.PNG', b'\x89PNG\r\n\x1a\n', content_type='image/png')
        response = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        assert response.status_code == 201
        assert response.json()['file_type'] == 'IMAGE'


@pytest.mark.django_db
class TestFileList:
    """文件列表测试。"""

    def test_file_list_ordered(self, auth_client, admin_user, sample_task, media_root):
        """文件列表 → 按 created_at 降序。"""
        import time

        f1 = SimpleUploadedFile('first.txt', b'first', content_type='text/plain')
        auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f1},
            format='multipart',
        )

        time.sleep(0.05)

        f2 = SimpleUploadedFile('second.txt', b'second', content_type='text/plain')
        auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f2},
            format='multipart',
        )

        response = auth_client.get(reverse('file-list', kwargs={'task_pk': sample_task.pk}))
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]['original_name'] == 'second.txt'
        assert data[1]['original_name'] == 'first.txt'


@pytest.mark.django_db
class TestFileDownload:
    """文件下载测试。"""

    def test_download_file(self, auth_client, admin_user, sample_task, media_root):
        """下载文件 → 200, Content-Disposition 正确。"""
        f = SimpleUploadedFile('download_me.txt', b'hello download', content_type='text/plain')
        upload_resp = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        file_id = upload_resp.json()['id']

        response = auth_client.get(reverse('file-download', kwargs={'pk': file_id}))
        assert response.status_code == 200
        assert 'download_me.txt' in response['Content-Disposition']

    def test_download_count_increments(self, auth_client, admin_user, sample_task, media_root):
        """下载次数递增。"""
        f = SimpleUploadedFile('count.txt', b'count test', content_type='text/plain')
        upload_resp = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        file_id = upload_resp.json()['id']

        auth_client.get(reverse('file-download', kwargs={'pk': file_id}))
        auth_client.get(reverse('file-download', kwargs={'pk': file_id}))

        task_file = TaskFile.objects.get(pk=file_id)
        assert task_file.download_count == 2

    def test_download_nonexistent(self, auth_client, admin_user, media_root):
        """下载不存在的文件 → 404。"""
        response = auth_client.get(reverse('file-download', kwargs={'pk': uuid.uuid4()}))
        assert response.status_code == 404


@pytest.mark.django_db
class TestFileDelete:
    """文件删除测试。"""

    def test_uploader_deletes_own(self, auth_client, admin_user, sample_task, media_root):
        """上传者删除自己的文件 → 204。"""
        f = SimpleUploadedFile('my_file.txt', b'my content', content_type='text/plain')
        upload_resp = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        file_id = upload_resp.json()['id']

        response = auth_client.delete(reverse('file-delete', kwargs={'pk': file_id}))
        assert response.status_code == 204
        assert not TaskFile.objects.filter(pk=file_id).exists()

    def test_non_uploader_member_deletes(self, auth_client, member_client, admin_user, regular_user,
                                         sample_task, media_root):
        """非上传者 MEMBER 删除 → 403。"""
        f = SimpleUploadedFile('admin_file.txt', b'admin content', content_type='text/plain')
        upload_resp = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        file_id = upload_resp.json()['id']

        response = member_client.delete(reverse('file-delete', kwargs={'pk': file_id}))
        assert response.status_code == 403

    def test_admin_deletes_any(self, auth_client, admin_user, sample_task, media_root):
        """ADMIN/superuser 删除任意文件 → 204。"""
        f = SimpleUploadedFile('some_file.txt', b'some content', content_type='text/plain')
        upload_resp = auth_client.post(
            reverse('file-upload', kwargs={'task_pk': sample_task.pk}),
            {'file': f},
            format='multipart',
        )
        file_id = upload_resp.json()['id']

        response = auth_client.delete(reverse('file-delete', kwargs={'pk': file_id}))
        assert response.status_code == 204

    def test_delete_nonexistent(self, auth_client, admin_user, media_root):
        """删除不存在的文件 → 404。"""
        response = auth_client.delete(reverse('file-delete', kwargs={'pk': uuid.uuid4()}))
        assert response.status_code == 404
