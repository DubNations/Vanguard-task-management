from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

import logging

from common.permissions import IsSuperAdmin, IsGroupLeader
from .models import User, Team
from .serializers import (
    UserListSerializer, UserDetailSerializer, UserCreateSerializer,
    UserProfileUpdateSerializer, ChangePasswordSerializer, TeamSerializer,
)

logger = logging.getLogger('audit')


class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': '请输入邮箱和密码'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=email, password=password)
        if not user:
            return Response(
                {'error': '邮箱或密码错误'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {'error': '账号已被禁用'},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserDetailSerializer(user).data,
        })


class LogoutView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import logging
        logger = logging.getLogger('audit')
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            logger.warning('Token blacklist failed during logout', exc_info=True)
        return Response({'detail': '已登出'}, status=status.HTTP_200_OK)


class MeView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserDetailSerializer(request.user).data)

    def patch(self, request):
        """个人中心只允许修改 phone、avatar。"""
        serializer = UserProfileUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserDetailSerializer(request.user).data)


class ChangePasswordView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': '原密码错误'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'detail': '密码修改成功'})


class UserListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.select_related('team').all()
    filterset_fields = ['role', 'team', 'is_active']
    search_fields = ['username', 'email', 'phone']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserListSerializer

    def list(self, request, *args, **kwargs):
        # 组长及以上返回完整列表；普通成员仅返回 id+username（用于下拉选择）
        if request.user.is_superuser or request.user.role in ('LEADER', 'ADMIN'):
            return super().list(request, *args, **kwargs)

        users = User.objects.filter(is_active=True).values('id', 'username')
        return Response(list(users))


class UserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.select_related('team').all()
    serializer_class = UserDetailSerializer

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        # 超管/组长可查看任何人；普通成员只能查看自己
        if not (user.is_superuser or user.role in ('LEADER', 'ADMIN')):
            if obj.pk != user.pk:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('您无权查看其他用户信息')
        return obj

    def get_serializer_class(self):
        if self.request.user.is_superuser or self.request.user.role in ('LEADER', 'ADMIN'):
            return UserDetailSerializer
        # 普通成员查看自己也用 DetailSerializer
        target_pk = self.kwargs.get('pk')
        if str(self.request.user.pk) == str(target_pk):
            return UserDetailSerializer
        return UserListSerializer


class UserToggleActiveView(views.APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

        if user == request.user:
            return Response({'error': '不能禁用自己的账号'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        action = '启用' if user.is_active else '禁用'
        return Response({'detail': f'用户已{action}', 'is_active': user.is_active})


class TeamListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Team.objects.select_related('leader').all()
    serializer_class = TeamSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            self.permission_classes = [IsAuthenticated, IsSuperAdmin]
        return super().get_permissions()


class TeamDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    queryset = Team.objects.select_related('leader').all()
    serializer_class = TeamSerializer


class UserResetPasswordView(views.APIView):
    """管理员重置用户密码。"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

        new_password = request.data.get('new_password', '')
        if not new_password or len(new_password) < 6:
            return Response({'error': '密码长度至少6位'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'detail': '密码已重置'})
