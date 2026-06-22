import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const ROLE_HIERARCHY: Record<string, number> = {
  MEMBER: 0,
  LEADER: 1,
  ADMIN: 2,
}

function meetsRole(userRole: string, isSuperuser: boolean, minRole?: string): boolean {
  if (!minRole) return true
  const userLevel = isSuperuser ? ROLE_HIERARCHY['ADMIN'] : (ROLE_HIERARCHY[userRole] ?? 0)
  return userLevel >= (ROLE_HIERARCHY[minRole] ?? 0)
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'Dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: '工作台' },
        },
        {
          path: 'tasks',
          name: 'Tasks',
          component: () => import('@/views/tasks/TaskListView.vue'),
          meta: { title: '任务管理' },
        },
        {
          path: 'tasks/kanban',
          name: 'Kanban',
          component: () => import('@/views/tasks/KanbanView.vue'),
          meta: { title: '看板视图' },
        },
        {
          path: 'tasks/timeline',
          name: 'Timeline',
          component: () => import('@/views/tasks/TimelineView.vue'),
          meta: { title: '时间线' },
        },
        {
          path: 'tasks/calendar',
          name: 'Calendar',
          component: () => import('@/views/tasks/CalendarView.vue'),
          meta: { title: '日历视图' },
        },
        {
          path: 'tasks/:id',
          name: 'TaskDetail',
          component: () => import('@/views/tasks/TaskDetailView.vue'),
          props: true,
          meta: { title: '任务详情', parent: { path: '/tasks', title: '任务管理' } },
        },
        {
          path: 'points',
          name: 'Points',
          component: () => import('@/views/points/PointsView.vue'),
          meta: { title: '积分排行' },
        },
        {
          path: 'imports',
          name: 'Imports',
          component: () => import('@/views/imports/ImportView.vue'),
          meta: { title: '任务导入', minRole: 'LEADER' },
        },
        {
          path: 'exports',
          name: 'Exports',
          component: () => import('@/views/exports/ExportView.vue'),
          meta: { title: '任务导出', minRole: 'LEADER' },
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('@/views/profile/ProfileView.vue'),
          meta: { title: '个人中心' },
        },
        {
          path: 'admin/teams',
          name: 'TeamManagement',
          component: () => import('@/views/admin/TeamManagement.vue'),
          meta: { title: '团队管理', minRole: 'ADMIN' },
        },
        {
          path: 'admin/users',
          name: 'UserManagement',
          component: () => import('@/views/admin/UserManagement.vue'),
          meta: { title: '用户管理', minRole: 'LEADER' },
        },
        {
          path: 'admin/audit',
          name: 'AuditLog',
          component: () => import('@/views/admin/AuditLogView.vue'),
          meta: { title: '操作日志', minRole: 'LEADER' },
        },
        {
          path: 'admin/points',
          name: 'PointsConfig',
          component: () => import('@/views/admin/PointsConfigView.vue'),
          meta: { title: '积分配置', minRole: 'ADMIN' },
        },
      ],
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth !== false && !auth.isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && auth.isLoggedIn) {
    next({ name: 'Dashboard' })
  } else if (to.meta.minRole && auth.user && !meetsRole(auth.user.role, auth.user.is_superuser, to.meta.minRole as string)) {
    // 角色不足时静默跳转到工作台（体验优化：不暴露无权限路由的存在）
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router
