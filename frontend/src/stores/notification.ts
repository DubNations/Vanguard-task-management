import { defineStore } from 'pinia'
import api from '@/api'

export interface Notification {
  id: string
  type: string
  title: string
  content: string
  is_read: boolean
  task_id: string | null
  actor: string
  created_at: string
}

interface NotificationState {
  notifications: Notification[]
  unreadCount: number
  loading: boolean
}

export const useNotificationStore = defineStore('notifications', {
  state: (): NotificationState => ({
    notifications: [],
    unreadCount: 0,
    loading: false,
  }),

  actions: {
    async fetchNotifications(unreadOnly = false) {
      this.loading = true
      try {
        const { data } = await api.get('/notifications/', {
          params: { unread: unreadOnly },
        })
        this.notifications = data.notifications
        this.unreadCount = data.unread_count
      } finally {
        this.loading = false
      }
    },

    async markRead(id: string) {
      await api.post(`/notifications/${id}/read/`)
      const n = this.notifications.find((n) => n.id === id)
      if (n && !n.is_read) {
        n.is_read = true
        this.unreadCount = Math.max(0, this.unreadCount - 1)
      }
    },

    async markAllRead() {
      await api.post('/notifications/mark-all-read/')
      this.notifications.forEach((n) => (n.is_read = true))
      this.unreadCount = 0
    },
  },
})
