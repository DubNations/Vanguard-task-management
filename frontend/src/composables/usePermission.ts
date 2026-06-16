import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

/**
 * 权限相关 composable。
 */
export function usePermission() {
  const auth = useAuthStore()

  const isAdmin = computed(() => auth.isAdmin)
  const isLeader = computed(() => auth.isLeader || auth.isAdmin)
  const isMember = computed(() => !isLeader.value)

  /** 是否可编辑任务（管理员/组长/负责人） */
  function canEditTask(task: { assignee?: string; creator?: string }) {
    if (isAdmin.value || isLeader.value) return true
    return task.assignee === auth.user?.id || task.creator === auth.user?.id
  }

  /** 是否可执行状态转换 */
  function canTransition(task: { assignee?: string }) {
    if (isAdmin.value || isLeader.value) return true
    return task.assignee === auth.user?.id
  }

  /** 是否可删除任务 */
  function canDeleteTask(task: { creator?: string }) {
    if (isAdmin.value) return true
    return task.creator === auth.user?.id
  }

  /** 是否可查看内部评论 */
  function canViewInternalComments() {
    return isAdmin.value || isLeader.value
  }

  return {
    isAdmin,
    isLeader,
    isMember,
    canEditTask,
    canTransition,
    canDeleteTask,
    canViewInternalComments,
  }
}
