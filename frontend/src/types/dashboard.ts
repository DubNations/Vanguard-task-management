/** 仪表盘类型定义 */

/** 状态统计（MEMBER 和 LEADER 共用） */
export interface DashboardSummary {
  total: number
  pending: number
  in_progress: number
  in_review: number
  completed: number
  overdue: number
}

/** 待办任务项 */
export interface TodoTask {
  id: string
  task_no: string
  title: string
  priority: string
  status: string
  deadline: string | null
  is_overdue: boolean
  days_until_deadline: number | null
  progress: number
  task_mode: string
  assignee_name: string
  days_label: string
}

/** MEMBER 工作台响应 */
export interface MemberDashboardResponse {
  summary: DashboardSummary
  monthly_points: {
    earned: number
    completed_count: number
    in_progress_count: number
  }
  todo_list: TodoTask[]
}

/** 成员负载项 */
export interface MemberWorkload {
  user_id: string
  username: string
  display_name: string
  team_name: string
  in_progress: number
  completed_this_month: number
  total_points: number
}

/** 逾期任务项（LEADER 用） */
export interface OverdueTask {
  id: string
  task_no: string
  title: string
  priority: string
  deadline: string | null
  is_overdue: boolean
  days_until_deadline: number | null
  assignee_name: string
  assignee_id: string | null
  creator_name: string
  days_label: string
}

/** LEADER 管理台响应 */
export interface LeaderDashboardResponse {
  summary: DashboardSummary
  monthly_team_points: {
    total_points: number
    completed_count: number
    completion_rate: number
  }
  member_workload: MemberWorkload[]
  overdue_tasks: OverdueTask[]
}
