from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """仅超级管理员可访问。"""

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser and request.user.is_active


class IsGroupLeader(permissions.BasePermission):
    """组长及以上可访问（含 ADMIN）。"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_active:
            return False
        return request.user.is_superuser or request.user.role in ('LEADER', 'ADMIN')


class IsOwnerOrLeader(permissions.BasePermission):
    """任务负责人、创建人、参与者或组长及以上可操作。
    PENDING 状态的任务对所有登录用户可读（任务大厅），但仅创建人/组长可编辑。
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if request.user.role in ('LEADER', 'ADMIN'):
            return True
        # PENDING 任务大厅：所有登录用户可读（GET），编辑仍需权限
        if hasattr(obj, 'status') and obj.status == 'PENDING':
            if request.method in permissions.SAFE_METHODS:
                return True
            # PUT/PATCH 仅创建人可编辑
            if hasattr(obj, 'creator') and obj.creator == request.user:
                return True
            return False
        if hasattr(obj, 'assignee') and obj.assignee == request.user:
            return True
        if hasattr(obj, 'creator') and obj.creator == request.user:
            return True
        # 参与者可操作自己领取的任务（揭榜/派发）
        task = obj if hasattr(obj, 'participants') else obj
        if hasattr(task, 'participants') and task.participants.filter(user=request.user).exists():
            return True
        return False


class IsReadOnly(permissions.BasePermission):
    """仅允许 GET/HEAD/OPTIONS。"""

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class IsChiefLeadOrOwner(permissions.BasePermission):
    """派发模式总牵头人、创建人或组长及以上可操作。"""

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.role in ('LEADER', 'ADMIN'):
            return True
        task = obj if hasattr(obj, 'participants') else obj.task
        if hasattr(task, 'creator') and task.creator == request.user:
            return True
        return task.participants.filter(
            user=request.user,
            role='CHIEF_LEAD',
            status__in=['ACCEPTED', 'COMPLETED'],
        ).exists()
