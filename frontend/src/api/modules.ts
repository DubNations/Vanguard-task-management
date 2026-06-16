import api from './index'

/** 仪表盘 API */
export const dashboardApi = {
  getSummary: () => api.get('/dashboard/summary/'),
  getStatusDistribution: () => api.get('/dashboard/status/'),
  getPriorityDistribution: () => api.get('/dashboard/priority/'),
  getWeeklyTrend: (weeks = 8) => api.get('/dashboard/trend/', { params: { weeks } }),
  getTeamWorkload: () => api.get('/dashboard/workload/'),
  getOverdueTasks: (limit = 10) => api.get('/dashboard/overdue/', { params: { limit } }),
}

/** 导入 API */
export const importApi = {
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/imports/upload/', formData)
  },
  confirm: (sessionId: string) => api.post(`/imports/${sessionId}/confirm/`),
  getDetail: (sessionId: string) => api.get(`/imports/${sessionId}/`),
  getHistory: () => api.get('/imports/'),
}

/** 导出 API */
export const exportApi = {
  create: (format: string, filters?: Record<string, unknown>) =>
    api.post('/exports/create/', { format, filters }),
  download: (jobId: string) =>
    api.get(`/exports/${jobId}/download/`, { responseType: 'blob' }),
  getHistory: () => api.get('/exports/'),
}

/** 文件 API */
export const fileApi = {
  upload: (taskId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/files/upload/${taskId}/`, formData)
  },
  list: (taskId: string) => api.get(`/files/list/${taskId}/`),
  download: (fileId: string) =>
    api.get(`/files/download/${fileId}/`, { responseType: 'blob' }),
  delete: (fileId: string) => api.delete(`/files/${fileId}/`),
}

/** 通知 API */
export const notificationApi = {
  list: (unreadOnly = false) =>
    api.get('/notifications/', { params: { unread: unreadOnly } }),
  markRead: (id: string) => api.post(`/notifications/${id}/read/`),
  markAllRead: () => api.post('/notifications/mark-all-read/'),
}

/** 管理 API */
export const adminApi = {
  getAuditLogs: (params?: Record<string, unknown>) =>
    api.get('/admin/audit/', { params }),
  getSystemStatus: () => api.get('/admin/status/'),
}

/** 积分 API */
export const pointsApi = {
  getBalance: () => api.get('/points/balance/'),
  getTransactions: (page = 1) => api.get('/points/transactions/', { params: { page } }),
  getLeaderboard: (period = 'all') => api.get('/points/leaderboard/', { params: { period } }),
  getMyStats: () => api.get('/points/my-stats/'),
  getRules: () => api.get('/points/rules/'),
  updateRule: (data: Record<string, unknown>) => api.post('/points/rules/', data),
}
