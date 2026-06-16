from rest_framework import serializers

from .models import User, Team


class TeamSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'leader', 'member_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_member_count(self, obj):
        return obj.members.count()


class UserListSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True, default='')

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'role',
            'team', 'team_name', 'avatar', 'is_active',
            'date_joined', 'last_login',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserDetailSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True, default='')

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'role',
            'team', 'team_name', 'avatar', 'is_active',
            'is_superuser', 'date_joined', 'last_login', 'last_login_ip',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'last_login_ip']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, min_length=8)
    new_password = serializers.CharField(required=True, min_length=8)

    def validate_new_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value)
        return value


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """个人中心专用更新 serializer，仅允许修改 phone 和 avatar。"""

    class Meta:
        model = User
        fields = ['phone', 'avatar']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'phone', 'role', 'team']

    def validate_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
