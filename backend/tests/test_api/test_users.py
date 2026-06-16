"""用户管理测试。"""
import uuid

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestUserCreate:
    """用户创建测试。"""

    def test_member_create_user_403(self, member_client):
        """MEMBER 创建用户 → 403 (IsGroupLeader)。"""
        url = reverse('user-list')
        response = member_client.post(url, {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'SecurePass99!',
            'role': 'MEMBER',
        }, format='json')
        assert response.status_code == 403

    def test_leader_create_user_201(self, leader_client, team):
        """LEADER 创建用户 → 201 (IsGroupLeader 允许)。"""
        url = reverse('user-list')
        response = leader_client.post(url, {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'SecurePass99!',
            'role': 'MEMBER',
            'team': str(team.pk),
        }, format='json')
        assert response.status_code == 201
        assert response.json()['username'] == 'newuser'

    def test_admin_create_user_all_fields_201(self, auth_client, team):
        """ADMIN 创建用户（含全部字段） → 201。"""
        url = reverse('user-list')
        response = auth_client.post(url, {
            'username': 'fulluser',
            'email': 'full@test.com',
            'password': 'SecurePass99!',
            'phone': '13900001111',
            'role': 'MEMBER',
            'team': str(team.pk),
        }, format='json')
        assert response.status_code == 201
        data = response.json()
        assert data['username'] == 'fulluser'
        assert data['email'] == 'full@test.com'
        assert data['phone'] == '13900001111'
        assert data['role'] == 'MEMBER'
        assert data['team'] == str(team.pk)

    def test_create_user_duplicate_email_400(self, auth_client, admin_user):
        """重复邮箱 → 400。"""
        url = reverse('user-list')
        response = auth_client.post(url, {
            'username': 'another',
            'email': admin_user.email,
            'password': 'SecurePass99!',
        }, format='json')
        assert response.status_code == 400

    def test_create_user_duplicate_username_400(self, auth_client, admin_user):
        """重复用户名 → 400。"""
        url = reverse('user-list')
        response = auth_client.post(url, {
            'username': admin_user.username,
            'email': 'unique@test.com',
            'password': 'SecurePass99!',
        }, format='json')
        assert response.status_code == 400


@pytest.mark.django_db
class TestUserDetail:
    """用户详情测试。"""

    def test_self_view_self_full_fields(self, member_client, regular_user):
        """自己查看自己 → 200，完整字段 (UserDetailSerializer)。"""
        url = reverse('user-detail', kwargs={'pk': regular_user.pk})
        response = member_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['email'] == regular_user.email
        # UserDetailSerializer 特有字段
        assert 'is_superuser' in data
        assert 'last_login_ip' in data

    def test_member_view_other_limited_fields(self, member_client, member_b_user):
        """MEMBER 查看他人 → 200，有限字段 (UserListSerializer)。"""
        url = reverse('user-detail', kwargs={'pk': member_b_user.pk})
        response = member_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['email'] == member_b_user.email
        # UserListSerializer 不包含这些字段
        assert 'is_superuser' not in data
        assert 'last_login_ip' not in data

    def test_leader_view_other_full_fields(self, leader_client, regular_user):
        """LEADER 查看他人 → 200，完整字段 (UserDetailSerializer)。"""
        url = reverse('user-detail', kwargs={'pk': regular_user.pk})
        response = leader_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert 'is_superuser' in data
        assert 'last_login_ip' in data


@pytest.mark.django_db
class TestUserList:
    """用户列表测试。"""

    def test_filter_by_role(self, auth_client, admin_user, leader_user, regular_user):
        """按角色筛选 → 结果正确。"""
        url = reverse('user-list')
        response = auth_client.get(url, {'role': 'MEMBER'})
        assert response.status_code == 200
        results = response.json()['results']
        for user in results:
            assert user['role'] == 'MEMBER'
        usernames = [u['username'] for u in results]
        assert regular_user.username in usernames
        assert admin_user.username not in usernames
        assert leader_user.username not in usernames

    def test_filter_by_team(self, auth_client, team, regular_user, admin_user):
        """按团队筛选 → 结果正确。"""
        url = reverse('user-list')
        response = auth_client.get(url, {'team': str(team.pk)})
        assert response.status_code == 200
        results = response.json()['results']
        for user in results:
            assert user['team'] == str(team.pk)
        usernames = [u['username'] for u in results]
        assert regular_user.username in usernames
        assert admin_user.username not in usernames

    def test_search_username_email_phone(self, auth_client, regular_user):
        """搜索 (username/email/phone) → 结果正确。"""
        url = reverse('user-list')
        # 按用户名搜索
        response = auth_client.get(url, {'search': regular_user.username})
        assert response.status_code == 200
        results = response.json()['results']
        assert len(results) >= 1
        assert any(u['username'] == regular_user.username for u in results)

        # 按邮箱搜索
        response = auth_client.get(url, {'search': regular_user.email})
        assert response.status_code == 200
        results = response.json()['results']
        assert len(results) >= 1

    def test_pagination_structure(self, auth_client, admin_user):
        """分页 → count/page/results 结构。"""
        url = reverse('user-list')
        response = auth_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert 'count' in data
        assert 'page' in data
        assert 'results' in data
        assert isinstance(data['results'], list)
        assert data['count'] >= 1


@pytest.mark.django_db
class TestUserToggle:
    """用户启用/禁用测试。"""

    def test_toggle_nonexistent_user_404(self, auth_client):
        """Toggle 不存在用户 → 404。"""
        fake_pk = uuid.uuid4()
        url = reverse('user-toggle', kwargs={'pk': fake_pk})
        response = auth_client.post(url)
        assert response.status_code == 404

    def test_leader_toggle_user_403(self, leader_client, regular_user):
        """LEADER 尝试 toggle 用户 → 403 (IsSuperAdmin)。"""
        url = reverse('user-toggle', kwargs={'pk': regular_user.pk})
        response = leader_client.post(url)
        assert response.status_code == 403
