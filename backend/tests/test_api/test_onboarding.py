"""
场景 S1 — 新用户入职流程模拟测试。
模拟：Admin 创建团队 → 创建用户 → 用户首次登录 → 修改密码 → 重新登录 → 查看空仪表盘。
"""
import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestOnboardingFlow:
    """S1: 新用户入职全流程。"""

    def test_s1_01_admin_creates_team(self, auth_client):
        """Admin 创建团队。"""
        url = reverse('team-list')
        response = auth_client.post(url, {
            'name': '尖兵特战队',
            'description': '精英小队',
        }, format='json')
        assert response.status_code == 201
        assert response.json()['member_count'] == 0

    def test_s1_02_admin_creates_user(self, auth_client, team):
        """Admin 创建用户并分配到团队。"""
        url = reverse('user-list')
        response = auth_client.post(url, {
            'email': 'newmember@test.com',
            'username': 'newmember',
            'password': 'Init@12345',
            'role': 'MEMBER',
            'team': str(team.id),
        }, format='json')
        assert response.status_code == 201
        data = response.json()
        assert data['team'] == str(team.id)
        assert data['role'] == 'MEMBER'
        # UserCreateSerializer 不返回 is_active，通过模型验证
        from apps.accounts.models import User
        created = User.objects.get(email='newmember@test.com')
        assert created.is_active is True
        assert created.team_id == team.id

    def test_s1_03_new_user_first_login(self, api_client, team):
        """新创建的用户首次登录。"""
        from apps.accounts.models import User
        User.objects.create_user(
            email='newlogin@test.com',
            password='Init@12345',
            username='newlogin',
            role='MEMBER',
            team=team,
        )

        url = reverse('auth-login')
        response = api_client.post(url, {
            'email': 'newlogin@test.com',
            'password': 'Init@12345',
        })
        assert response.status_code == 200
        data = response.json()
        assert 'access' in data
        assert 'refresh' in data
        assert data['user']['email'] == 'newlogin@test.com'
        assert data['user']['role'] == 'MEMBER'
        assert data['user']['team_name'] == team.name

    def test_s1_04_change_initial_password(self, api_client, team):
        """新用户修改初始密码。"""
        from apps.accounts.models import User
        user = User.objects.create_user(
            email='changepw@test.com',
            password='Init@12345',
            username='changepw',
            role='MEMBER',
            team=team,
        )
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        url = reverse('auth-password')
        response = api_client.post(url, {
            'old_password': 'Init@12345',
            'new_password': 'SecureNew@789!',
        })
        assert response.status_code == 200

        user.refresh_from_db()
        assert user.check_password('SecureNew@789!')

    def test_s1_05_relogin_with_new_password(self, api_client, team):
        """使用新密码重新登录。"""
        from apps.accounts.models import User
        user = User.objects.create_user(
            email='relogin@test.com',
            password='OldPass@123',
            username='relogin',
            role='MEMBER',
            team=team,
        )
        user.set_password('NewPass@456!')
        user.save()

        url = reverse('auth-login')
        response = api_client.post(url, {
            'email': 'relogin@test.com',
            'password': 'NewPass@456!',
        })
        assert response.status_code == 200
        assert 'access' in response.json()

    def test_s1_06_view_empty_dashboard(self, api_client, team):
        """新用户查看空仪表盘。"""
        from apps.accounts.models import User
        user = User.objects.create_user(
            email='dashuser@test.com',
            password='testpass123',
            username='dashuser',
            role='MEMBER',
            team=team,
        )
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        url = reverse('dashboard-member')
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['summary']['total'] == 0
        assert data['summary']['pending'] == 0
        assert data['summary']['in_progress'] == 0
        assert data['summary']['completed'] == 0
        assert data['summary']['overdue'] == 0
