/**
 * 任务状态工具 composable。
 */

/** 状态定义 */
export const TASK_STATUSES = [
  { value: 'PENDING', label: '待领取', color: '#909399', icon: 'Clock' },
  { value: 'IN_PROGRESS', label: '进行中', color: '#409EFF', icon: 'Loading' },
  { value: 'IN_REVIEW', label: '待审核', color: '#E6A23C', icon: 'View' },
  { value: 'COMPLETED', label: '已完成', color: '#67C23A', icon: 'CircleCheck' },
  { value: 'REJECTED', label: '已退回', color: '#F56C6C', icon: 'CircleClose' },
  { value: 'CANCELLED', label: '已取消', color: '#909399', icon: 'Remove' },
] as const

/** 优先级定义 */
export const TASK_PRIORITIES = [
  { value: 'LOW', label: '低', color: '#909399' },
  { value: 'MEDIUM', label: '中', color: '#409EFF' },
  { value: 'HIGH', label: '高', color: '#E6A23C' },
  { value: 'URGENT', label: '紧急', color: '#F56C6C' },
] as const

/** 状态转换规则（与后端保持一致） */
export const STATUS_TRANSITIONS: Record<string, string[]> = {
  PENDING: ['IN_PROGRESS', 'CANCELLED'],
  IN_PROGRESS: ['IN_REVIEW', 'PENDING', 'CANCELLED'],
  IN_REVIEW: ['COMPLETED', 'REJECTED'],
  COMPLETED: [],
  REJECTED: ['IN_PROGRESS'],
  CANCELLED: [],
}

export function useTaskStatus() {
  /** 获取状态标签 */
  function getStatusLabel(status: string): string {
    return TASK_STATUSES.find((s) => s.value === status)?.label ?? status
  }

  /** 获取状态颜色 */
  function getStatusColor(status: string): string {
    return TASK_STATUSES.find((s) => s.value === status)?.color ?? '#909399'
  }

  /** 获取可用转换目标 */
  function getAvailableTransitions(currentStatus: string): { value: string; label: string }[] {
    const targets = STATUS_TRANSITIONS[currentStatus] || []
    return targets.map((v) => ({
      value: v,
      label: getStatusLabel(v),
    }))
  }

  /** 获取优先级标签 */
  function getPriorityLabel(priority: string): string {
    return TASK_PRIORITIES.find((p) => p.value === priority)?.label ?? priority
  }

  /** 获取优先级颜色 */
  function getPriorityColor(priority: string): string {
    return TASK_PRIORITIES.find((p) => p.value === priority)?.color ?? '#909399'
  }

  return {
    getStatusLabel,
    getStatusColor,
    getAvailableTransitions,
    getPriorityLabel,
    getPriorityColor,
    TASK_STATUSES,
    TASK_PRIORITIES,
  }
}
