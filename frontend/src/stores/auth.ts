import { defineStore } from 'pinia'
import api from '@/api'

interface User {
  id: string
  username: string
  email: string
  role: string
  team_name: string
  is_superuser: boolean
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    accessToken: localStorage.getItem('access_token'),
    refreshToken: localStorage.getItem('refresh_token'),
    user: (() => {
      try { return JSON.parse(localStorage.getItem('user') || 'null') }
      catch { return null }
    })(),
  }),

  getters: {
    isLoggedIn: (state) => !!state.accessToken,
    isAdmin: (state) => state.user?.is_superuser || state.user?.role === 'ADMIN',
    isLeader: (state) => state.user?.role === 'LEADER',
    username: (state) => state.user?.username || '',
  },

  actions: {
    async login(email: string, password: string) {
      const { data } = await api.post('/auth/login/', { email, password })
      this.accessToken = data.access
      this.refreshToken = data.refresh
      this.user = data.user

      localStorage.setItem('access_token', data.access)
      localStorage.setItem('refresh_token', data.refresh)
      localStorage.setItem('user', JSON.stringify(data.user))
    },

    async doRefreshToken() {
      if (!this.refreshToken) throw new Error('No refresh token')
      const { data } = await api.post('/auth/refresh/', { refresh: this.refreshToken })
      this.accessToken = data.access
      localStorage.setItem('access_token', data.access)
      if (data.refresh) {
        this.refreshToken = data.refresh
        localStorage.setItem('refresh_token', data.refresh)
      }
    },

    async logout() {
      try {
        await api.post('/auth/logout/', { refresh: this.refreshToken })
      } catch {
        // ignore
      }
      this.accessToken = null
      this.refreshToken = null
      this.user = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
    },

    async fetchMe() {
      const { data } = await api.get('/auth/me/')
      this.user = data
      localStorage.setItem('user', JSON.stringify(data))
    },
  },
})
