import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

/** 角色层级：值越大权限越高 */
const ROLE_HIERARCHY: Record<string, number> = {
  MEMBER: 0,
  LEADER: 1,
  ADMIN: 2,
}

/**
 * 权限相关 composable。
 * 所有前端权限判断统一由此处消费，避免散落在各组件中硬编码。
 */
export function usePermission() {
  const auth = useAuthStore()

  const isAdmin = computed(() => auth.isAdmin)
  const isLeader = computed(() => auth.isLeader || auth.isAdmin)
  const isMember = computed(() => !isLeader.value)
  const isSuperAdmin = computed(() => auth.user?.is_superuser === true)

  /**
   * 判断当前用户是否拥有指定最低角色。
   * 等级：MEMBER(0) < LEADER(1) < ADMIN(2)
   * superuser 自动获得 ADMIN 级别。
   */
  function hasRole(minRole: 'MEMBER' | 'LEADER' | 'ADMIN'): boolean {
    if (!auth.user) return false
    const userLevel = auth.user.is_superuser
      ? ROLE_HIERARCHY['ADMIN']
      : (ROLE_HIERARCHY[auth.user.role] ?? 0)
    return userLevel >= (ROLE_HIERARCHY[minRole] ?? 0)
  }

  /** 是否可编辑任务（管理员/组长/负责人/参与者） */
  function canEditTask(task: { assignee?: string; creator?: string; participants?: string[] }) {
    if (isAdmin.value || isLeader.value) return true
    if (task.assignee === auth.user?.id || task.creator === auth.user?.id) return true
    if (task.participants?.includes(auth.user?.id || '')) return true
    return false
  }

  /** 是否可执行状态转换（管理员/组长/负责人） */
  function canTransition(task: { assignee?: string }) {
    if (isAdmin.value || isLeader.value) return true
    return task.assignee === auth.user?.id
  }

  /** 是否可删除任务（管理员/创建人） */
  function canDeleteTask(task: { creator?: string }) {
    if (isAdmin.value) return true
    return task.creator === auth.user?.id
  }

  /** 是否可查看内部评论 */
  function canViewInternalComments() {
    return isAdmin.value || isLeader.value
  }

  // ---- 管理后台细粒度权限（与后端权限类对齐） ----

  /** 用户管理：查看/创建用户列表 — 后端 IsGroupLeader (LEADER+) */
  function canManageUsers() {
    return hasRole('LEADER')
  }

  /** 用户管理：禁用/重置密码 — 后端 IsSuperAdmin (superuser only) */
  function canToggleUsers() {
    return isSuperAdmin.value
  }

  /** 团队管理：查看团队 — 后端 IsAuthenticated */
  function canViewTeams() {
    return !!auth.user
  }

  /** 团队管理：创建/编辑/删除团队 — 后端 IsSuperAdmin */
  function canManageTeams() {
    return isSuperAdmin.value
  }

  /** 操作日志：查看 — 后端 IsGroupLeader */
  function canViewAuditLog() {
    return hasRole('LEADER')
  }

  /** 积分配置：查看/编辑 — 后端 IsSuperAdmin (inferred) */
  function canManagePointsConfig() {
    return isSuperAdmin.value
  }

  return {
    isAdmin,
    isLeader,
    isMember,
    isSuperAdmin,
    hasRole,
    canEditTask,
    canTransition,
    canDeleteTask,
    canViewInternalComments,
    canManageUsers,
    canToggleUsers,
    canViewTeams,
    canManageTeams,
    canViewAuditLog,
    canManagePointsConfig,
  }
}
