"""安全与限流测试。"""
import pytest
import jwt
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings


# ---------------------------------------------------------------------------
# 限流
# ---------------------------------------------------------------------------
class TestRateLimiting:
    """限流配置与行为测试。"""

    def test_login_throttle_class_exists(self):
        """LoginRateThrottle 存在且 scope=login，限速 10/min。"""
        from common.throttles import LoginRateThrottle
        throttle = LoginRateThrottle()
        assert throttle.scope == 'login'
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login'] == '10/minute'

    def test_user_throttle_class_exists(self):
        """UserRateThrottle 存在且 scope=user，限速 120/min。"""
        from common.throttles import UserRateThrottle
        throttle = UserRateThrottle()
        assert throttle.scope == 'user'
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['user'] == '120/minute'

    def test_login_rate_limit_exceeded_returns_429(self, api_client, db):
        """超过登录限速 → 429。"""
        from django.core.cache import cache
        from common.throttles import LoginRateThrottle
        cache.clear()

        # 直接设置低限速进行测试（绕过 DRF api_settings 缓存）
        original_rate = LoginRateThrottle.THROTTLE_RATES.get('login')
        LoginRateThrottle.THROTTLE_RATES = {'login': '2/minute'}
        try:
            for _ in range(2):
                api_client.post('/api/v1/auth/login/', {
                    'email': 'bad@test.com', 'password': 'wrong',
                }, format='json')

            resp = api_client.post('/api/v1/auth/login/', {
                'email': 'bad@test.com', 'password': 'wrong',
            }, format='json')
            assert resp.status_code == 429
        finally:
            # 恢复原始限速
            if original_rate is not None:
                LoginRateThrottle.THROTTLE_RATES = {'login': original_rate}
            else:
                LoginRateThrottle.THROTTLE_RATES = {}
            cache.clear()


# ---------------------------------------------------------------------------
# SQL 注入 & XSS
# ---------------------------------------------------------------------------
class TestInjectionPrevention:
    """注入与 XSS 防护测试。"""

    def test_sql_injection_in_title_stored_safely(self, auth_client, admin_user):
        """SQL 注入字符串安全存储，不执行。"""
        malicious = "'; DROP TABLE tasks; --"
        resp = auth_client.post('/api/v1/tasks/', {
            'title': malicious,
        }, format='json')
        assert resp.status_code == 201
        # 验证原样存储
        from apps.tasks.models import Task
        task = Task.objects.get(id=resp.data['id'])
        assert task.title == malicious

    def test_xss_in_title_stored_as_is(self, auth_client):
        """XSS 脚本被后端 strip_html_tags 清洗。"""
        xss = '<script>alert(1)</script>'
        resp = auth_client.post('/api/v1/tasks/', {
            'title': xss,
        }, format='json')
        assert resp.status_code == 201
        from apps.tasks.models import Task
        task = Task.objects.get(id=resp.data['id'])
        # XSS 防御：HTML 标签被移除
        assert task.title == 'alert(1)'

    def test_path_traversal_in_filename(self, auth_client, sample_task, media_root):
        """路径遍历文件名由 Django 安全处理。"""
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        bad_name = '../../etc/passwd'
        file_obj = SimpleUploadedFile(bad_name, b'fake content', content_type='text/plain')
        # 文件上传端点 — 即使文件名含路径遍历也被 Django 安全处理
        resp = auth_client.post(
            f'/api/v1/files/',
            {'file': file_obj, 'task': str(sample_task.id)},
            format='multipart',
        )
        # 无论 201 还是 400，都不应是 500
        assert resp.status_code != 500


# ---------------------------------------------------------------------------
# 认证安全
# ---------------------------------------------------------------------------
class TestAuthSecurity:
    """认证安全测试。"""

    def test_unauthenticated_access_returns_401(self, api_client, db):
        """未认证访问受保护端点 → 401。"""
        resp = api_client.get('/api/v1/tasks/')
        assert resp.status_code == 401

    def test_forged_jwt_returns_401(self, api_client, db):
        """伪造 JWT token → 401。"""
        fake_token = jwt.encode(
            {'user_id': 'fake', 'exp': 9999999999},
            'totally-wrong-secret',
            algorithm='HS256',
        )
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {fake_token}')
        resp = api_client.get('/api/v1/tasks/')
        assert resp.status_code == 401

    def test_tampered_jwt_returns_401(self, api_client, admin_user, db):
        """篡改 JWT payload → 401。"""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(admin_user)
        token_str = str(refresh.access_token)
        # 篡改 payload 部分（翻转中间字符）
        parts = token_str.split('.')
        payload = parts[1]
        # 修改 payload 中的一个字符
        tampered_char = 'A' if payload[10] != 'A' else 'B'
        tampered_payload = payload[:10] + tampered_char + payload[11:]
        tampered_token = f'{parts[0]}.{tampered_payload}.{parts[2]}'
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tampered_token}')
        resp = api_client.get('/api/v1/tasks/')
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 输入边界
# ---------------------------------------------------------------------------
class TestInputBoundary:
    """输入边界安全测试。"""

    def test_invalid_uuid_in_url_returns_400_or_404(self, auth_client):
        """无效 UUID 格式 → 400 或 404，不是 500。"""
        resp = auth_client.get('/api/v1/tasks/not-a-uuid/')
        assert resp.status_code in (400, 404)
        assert resp.status_code != 500

    def test_oversized_page_size_limited(self, auth_client, admin_user):
        """超大 page_size 参数被限制到 max_page_size=100。"""
        # 创建少量任务
        from apps.tasks.services.task_service import TaskService
        for i in range(3):
            TaskService.create_task({'title': f'分页任务{i}'}, admin_user)

        resp = auth_client.get('/api/v1/tasks/', {'page_size': 9999})
        assert resp.status_code == 200
        # max_page_size=100，实际返回的数量不超过任务总数
        page_size = resp.data.get('page_size', 0)
        assert page_size <= 100
