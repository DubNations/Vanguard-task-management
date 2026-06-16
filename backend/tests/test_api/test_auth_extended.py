"""认证与授权扩展测试。"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
class TestLoginEdgeCases:
    """登录边界情况测试。"""

    def test_login_disabled_account(self, api_client, regular_user):
        """登录已禁用账号 → 401 (Django ModelBackend 对 inactive 用户返回 None)。"""
        regular_user.is_active = False
        regular_user.save(update_fields=['is_active'])

        url = reverse('auth-login')
        response = api_client.post(url, {
            'email': regular_user.email,
            'password': 'testpass123',
        }, format='json')
        # Django ModelBackend.authenticate() 对 is_active=False 返回 None
        assert response.status_code == 401

    def test_login_nonexistent_email_401(self, api_client):
        """不存在的邮箱 → 401。"""
        url = reverse('auth-login')
        response = api_client.post(url, {
            'email': 'nobody@test.com',
            'password': 'testpass123',
        }, format='json')
        assert response.status_code == 401

    def test_login_empty_password_400(self, api_client, admin_user):
        """空密码 → 400。"""
        url = reverse('auth-login')
        response = api_client.post(url, {
            'email': admin_user.email,
            'password': '',
        }, format='json')
        assert response.status_code == 400

    def test_login_invalid_email_format(self, api_client):
        """无效邮箱格式 → 401 (authenticate 返回 None)。"""
        url = reverse('auth-login')
        response = api_client.post(url, {
            'email': 'not-an-email',
            'password': 'testpass123',
        }, format='json')
        assert response.status_code == 401


@pytest.mark.django_db
class TestTokenRefresh:
    """Token 刷新测试。"""

    def test_token_refresh_returns_new_access(self, api_client, admin_user):
        """Token 刷新 → 返回新 access token。"""
        refresh = RefreshToken.for_user(admin_user)
        url = reverse('token-refresh')
        response = api_client.post(url, {'refresh': str(refresh)}, format='json')
        assert response.status_code == 200
        assert 'access' in response.json()

    def test_blacklisted_refresh_token_401(self, api_client, admin_user):
        """已加入黑名单的 refresh token → 401。"""
        refresh = RefreshToken.for_user(admin_user)
        refresh_str = str(refresh)

        # 登出使 refresh token 加入黑名单
        logout_url = reverse('auth-logout')
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        client.post(logout_url, {'refresh': refresh_str}, format='json')

        # 再次使用同一 refresh token → 应失败
        url = reverse('token-refresh')
        response = api_client.post(url, {'refresh': refresh_str}, format='json')
        assert response.status_code == 401


@pytest.mark.django_db
class TestChangePassword:
    """修改密码测试。"""

    def test_change_password_wrong_old_400(self, auth_client):
        """原密码错误 → 400 "原密码错误"。"""
        url = reverse('auth-password')
        response = auth_client.post(url, {
            'old_password': 'WrongOldPass123!',
            'new_password': 'NewSecurePass456!',
        }, format='json')
        assert response.status_code == 400
        assert '原密码错误' in str(response.data)

    def test_change_password_too_short_400(self, auth_client):
        """新密码过短 → 400。"""
        url = reverse('auth-password')
        response = auth_client.post(url, {
            'old_password': 'testpass123',
            'new_password': 'Ab1',
        }, format='json')
        assert response.status_code == 400

    def test_change_password_same_as_old(self, auth_client):
        """修改为相同密码 → 取决于 Django 密码验证器（一般允许）。"""
        url = reverse('auth-password')
        response = auth_client.post(url, {
            'old_password': 'testpass123',
            'new_password': 'testpass123',
        }, format='json')
        # 标准 Django 验证器不禁止相同密码（除非与用户属性相似）
        assert response.status_code == 200


@pytest.mark.django_db
class TestMeUpdate:
    """个人信息更新测试。"""

    def test_patch_me_update_phone(self, auth_client, admin_user):
        """PATCH /me/ 更新手机号 → 200，手机号已更新。"""
        url = reverse('auth-me')
        response = auth_client.patch(url, {
            'phone': '13812345678',
        }, format='json')
        assert response.status_code == 200
        assert response.json()['phone'] == '13812345678'

        admin_user.refresh_from_db()
        assert admin_user.phone == '13812345678'


@pytest.mark.django_db
class TestConcurrentLogins:
    """并发登录测试。"""

    def test_multiple_concurrent_logins(self, api_client, admin_user, regular_user):
        """多次并发登录 → 每个 token 独立有效。"""
        url = reverse('auth-login')

        # 用户 A 登录
        resp_a = api_client.post(url, {
            'email': admin_user.email,
            'password': 'testpass123',
        }, format='json')
        assert resp_a.status_code == 200
        token_a = resp_a.json()['access']

        # 用户 B 登录
        resp_b = api_client.post(url, {
            'email': regular_user.email,
            'password': 'testpass123',
        }, format='json')
        assert resp_b.status_code == 200
        token_b = resp_b.json()['access']

        # Token A 可独立使用
        client_a = APIClient()
        client_a.credentials(HTTP_AUTHORIZATION=f'Bearer {token_a}')
        me_resp = client_a.get(reverse('auth-me'))
        assert me_resp.status_code == 200
        assert me_resp.json()['email'] == admin_user.email

        # Token B 可独立使用
        client_b = APIClient()
        client_b.credentials(HTTP_AUTHORIZATION=f'Bearer {token_b}')
        me_resp = client_b.get(reverse('auth-me'))
        assert me_resp.status_code == 200
        assert me_resp.json()['email'] == regular_user.email


@pytest.mark.django_db
class TestLogoutBlacklist:
    """登出后 Token 黑名单测试。"""

    def test_after_logout_refresh_blacklisted_401(self, api_client, admin_user):
        """登出后 refresh token 加入黑名单 → 401。"""
        # 登录获取 tokens
        login_url = reverse('auth-login')
        resp = api_client.post(login_url, {
            'email': admin_user.email,
            'password': 'testpass123',
        }, format='json')
        assert resp.status_code == 200
        access_token = resp.json()['access']
        refresh_token = resp.json()['refresh']

        # 登出并将 refresh token 加入黑名单
        logout_url = reverse('auth-logout')
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_resp = client.post(logout_url, {'refresh': refresh_token}, format='json')
        assert logout_resp.status_code == 200

        # 尝试使用已黑名单的 refresh token → 应失败
        refresh_url = reverse('token-refresh')
        refresh_resp = api_client.post(refresh_url, {'refresh': refresh_token}, format='json')
        assert refresh_resp.status_code == 401
