import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: add JWT token
api.interceptors.request.use((config) => {
  // 不给 refresh/login 请求带 expired token
  const skipAuthUrls = ['/auth/refresh/', '/auth/login/']
  const shouldSkip = skipAuthUrls.some((url) => config.url?.includes(url))
  if (!shouldSkip) {
    const auth = useAuthStore()
    if (auth.accessToken) {
      config.headers.Authorization = `Bearer ${auth.accessToken}`
    }
  }
  // FormData 请求：移除 Content-Type，让浏览器自动设置 multipart/form-data + boundary
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
})

// Response interceptor: handle 401 and refresh
let isRefreshing = false
let failedQueue: Array<{ resolve: Function; reject: Function }> = []

const processQueue = (error: any) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve()
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // 跳过 refresh/login 的 401，避免死循环
    const skipUrls = ['/auth/refresh/', '/auth/login/', '/auth/logout/']
    const isSkippable = skipUrls.some((url) => originalRequest.url?.includes(url))

    if (error.response?.status === 401 && !originalRequest._retry && !isSkippable) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(() => api(originalRequest))
      }

      originalRequest._retry = true
      isRefreshing = true

      const auth = useAuthStore()
      try {
        await auth.doRefreshToken()
        processQueue(null)
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError)
        // await logout 防止异步 logout 再触发循环
        try { await auth.logout() } catch { /* ignore */ }
        router.push('/login')
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // Show error message — match DRF error response format
    const data = error.response?.data
    const message = data?.detail || data?.error?.message || data?.error || error.message || '请求失败'
    ElMessage.error(message)

    return Promise.reject(error)
  }
)

export const resetRefreshLock = () => {
  isRefreshing = false
  failedQueue = []
}

export default api
