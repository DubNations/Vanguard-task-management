"""
API 层集成测试 — 认证和用户管理。
"""
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAuthAPI:
    """认证接口测试。"""

    def test_login_success(self, api_client, admin_user):
        url = reverse('auth-login')
        response = api_client.post(url, {
            'email': 'test@test.com',
            'password': 'testpass123',
        })
        assert response.status_code == 200
        data = response.json()
        assert 'access' in data
        assert 'refresh' in data
        assert data['user']['email'] == 'test@test.com'

    def test_login_wrong_password(self, api_client, admin_user):
        url = reverse('auth-login')
        response = api_client.post(url, {
            'email': 'test@test.com',
            'password': 'wrongpass',
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, api_client):
        url = reverse('auth-login')
        response = api_client.post(url, {'email': 'test@test.com'})
        assert response.status_code == 400

    def test_me_authenticated(self, auth_client):
        url = reverse('auth-me')
        response = auth_client.get(url)
        assert response.status_code == 200
        assert response.json()['email'] == 'test@test.com'

    def test_me_unauthenticated(self, api_client):
        url = reverse('auth-me')
        response = api_client.get(url)
        assert response.status_code in (401, 403)

    def test_change_password(self, auth_client, admin_user):
        url = reverse('auth-password')
        response = auth_client.post(url, {
            'old_password': 'testpass123',
            'new_password': 'newSecurePass456!',
        })
        assert response.status_code == 200

        # 验证新密码可以登录
        admin_user.refresh_from_db()
        assert admin_user.check_password('newSecurePass456!')

    def test_logout(self, auth_client):
        url = reverse('auth-logout')
        response = auth_client.post(url, {})
        assert response.status_code == 200


@pytest.mark.django_db
class TestUserAPI:
    """用户管理接口测试。"""

    def test_user_list_as_admin(self, auth_client):
        url = reverse('user-list')
        response = auth_client.get(url)
        assert response.status_code == 200

    def test_user_list_as_member(self, api_client, regular_user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(regular_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        url = reverse('user-list')
        response = api_client.get(url)
        # 普通成员可查看用户列表（仅 id+username）
        assert response.status_code == 200
        data = response.json()
        # MEMBER 只返回 id 和 username
        assert len(data) > 0
        assert 'id' in data[0]
        assert 'username' in data[0]

    def test_user_toggle_active(self, auth_client, regular_user):
        url = reverse('user-toggle', kwargs={'pk': regular_user.pk})
        response = auth_client.post(url)
        assert response.status_code == 200

        regular_user.refresh_from_db()
        assert regular_user.is_active is False

        # 再次切换
        response = auth_client.post(url)
        assert response.status_code == 200
        regular_user.refresh_from_db()
        assert regular_user.is_active is True

    def test_cannot_disable_self(self, auth_client, admin_user):
        url = reverse('user-toggle', kwargs={'pk': admin_user.pk})
        response = auth_client.post(url)
        assert response.status_code == 400


@pytest.mark.django_db
class TestHealthCheck:
    def test_health(self, api_client):
        response = api_client.get('/api/v1/health')
        assert response.status_code == 200
        assert response.json()['status'] == 'ok'
