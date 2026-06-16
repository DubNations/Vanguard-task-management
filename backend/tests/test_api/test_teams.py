"""团队管理测试。"""
import uuid

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestTeamCreate:
    """团队创建测试。"""

    def test_admin_create_team_201(self, auth_client):
        """ADMIN 创建团队 → 201。"""
        url = reverse('team-list')
        response = auth_client.post(url, {
            'name': '新团队',
            'description': '测试描述',
        }, format='json')
        assert response.status_code == 201
        assert response.json()['name'] == '新团队'

    def test_member_create_team_403(self, member_client):
        """MEMBER 创建团队 → 403。"""
        url = reverse('team-list')
        response = member_client.post(url, {
            'name': '新团队',
            'description': '测试描述',
        }, format='json')
        assert response.status_code == 403

    def test_leader_create_team_403(self, leader_client):
        """LEADER 创建团队 → 403 (IsSuperAdmin)。"""
        url = reverse('team-list')
        response = leader_client.post(url, {
            'name': '新团队',
            'description': '测试描述',
        }, format='json')
        assert response.status_code == 403

    def test_create_team_duplicate_name_400(self, auth_client, team):
        """重复团队名称 → 400 (unique 约束)。"""
        url = reverse('team-list')
        response = auth_client.post(url, {
            'name': team.name,
            'description': '重复名称',
        }, format='json')
        assert response.status_code == 400


@pytest.mark.django_db
class TestTeamListAndDetail:
    """团队列表与详情测试。"""

    def test_team_list_all_authenticated_200(self, member_client, team):
        """团队列表 → 所有已认证用户可访问 → 200。"""
        url = reverse('team-list')
        response = member_client.get(url)
        assert response.status_code == 200
        results = response.json()['results']
        assert len(results) >= 1

    def test_team_detail_member_count(self, auth_client, team, regular_user, leader_user):
        """团队详情 → member_count 正确。"""
        url = reverse('team-detail', kwargs={'pk': team.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['member_count'] == team.members.count()
        assert data['member_count'] >= 2  # regular_user + leader_user


@pytest.mark.django_db
class TestTeamUpdateDelete:
    """团队更新与删除测试。"""

    def test_admin_update_team_200(self, auth_client, team):
        """ADMIN 更新团队 → 200。"""
        url = reverse('team-detail', kwargs={'pk': team.pk})
        response = auth_client.patch(url, {
            'name': '更新后团队名',
        }, format='json')
        assert response.status_code == 200
        assert response.json()['name'] == '更新后团队名'

    def test_admin_delete_team_204(self, auth_client):
        """ADMIN 删除团队 → 204。"""
        from apps.accounts.models import Team
        temp_team = Team.objects.create(name='待删除团队', description='即将被删除')
        url = reverse('team-detail', kwargs={'pk': temp_team.pk})
        response = auth_client.delete(url)
        assert response.status_code == 204
        assert not Team.objects.filter(pk=temp_team.pk).exists()

    def test_delete_team_with_members_set_null(self, auth_client, team, regular_user, leader_user):
        """删除含成员的团队 → 成员 team 字段 SET_NULL。"""
        from apps.accounts.models import User
        assert regular_user.team == team
        assert leader_user.team == team

        url = reverse('team-detail', kwargs={'pk': team.pk})
        response = auth_client.delete(url)
        assert response.status_code == 204

        regular_user.refresh_from_db()
        leader_user.refresh_from_db()
        assert regular_user.team is None
        assert leader_user.team is None

    def test_non_admin_update_delete_team_403(self, leader_client, member_client, team):
        """非 ADMIN 更新/删除团队 → 403。"""
        url = reverse('team-detail', kwargs={'pk': team.pk})

        # LEADER 更新 → 403
        response = leader_client.patch(url, {'name': '不应成功'}, format='json')
        assert response.status_code == 403

        # MEMBER 删除 → 403
        response = member_client.delete(url)
        assert response.status_code == 403
