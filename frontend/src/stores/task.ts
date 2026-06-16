import { defineStore } from 'pinia'
import api from '@/api'

export interface Task {
  id: string
  task_no: string
  title: string
  description: string
  status: string
  status_display: string
  priority: string
  priority_display: string
  progress: number
  assignee: string | null
  assignee_name: string
  creator: string
  creator_name: string
  reviewer: string | null
  reviewer_name: string
  deadline: string | null
  started_at: string | null
  completed_at: string | null
  is_overdue: boolean
  days_until_deadline: number | null
  tags: string[]
  custom_fields: Record<string, unknown>
  comments_count: number
  files_count: number
  created_at: string
  updated_at: string
}

export interface TaskListParams {
  page?: number
  page_size?: number
  status?: string
  priority?: string
  assignee?: string
  search?: string
  ordering?: string
}

export interface KanbanColumn {
  label: string
  count: number
  tasks: Task[]
}

interface TaskState {
  tasks: Task[]
  currentTask: Task | null
  totalCount: number
  loading: boolean
  kanbanData: Record<string, KanbanColumn>
}

export const useTaskStore = defineStore('tasks', {
  state: (): TaskState => ({
    tasks: [],
    currentTask: null,
    totalCount: 0,
    loading: false,
    kanbanData: {},
  }),

  getters: {
    overdueTasks: (state) => state.tasks.filter((t) => t.is_overdue),
    tasksByStatus: (state) => (status: string) =>
      state.tasks.filter((t) => t.status === status),
  },

  actions: {
    async fetchTasks(params: TaskListParams = {}) {
      this.loading = true
      try {
        const { data } = await api.get('/tasks/', { params })
        this.tasks = data.results || data
        this.totalCount = data.count || this.tasks.length
      } finally {
        this.loading = false
      }
    },

    async fetchTask(id: string) {
      this.loading = true
      try {
        const { data } = await api.get(`/tasks/${id}/`)
        this.currentTask = data
        return data
      } finally {
        this.loading = false
      }
    },

    async createTask(payload: Partial<Task>) {
      const { data } = await api.post('/tasks/', payload)
      this.tasks.unshift(data)
      return data
    },

    async updateTask(id: string, payload: Partial<Task>) {
      const { data } = await api.patch(`/tasks/${id}/`, payload)
      const idx = this.tasks.findIndex((t) => t.id === id)
      if (idx >= 0) this.tasks[idx] = data
      if (this.currentTask?.id === id) this.currentTask = data
      return data
    },

    async transitionTask(id: string, status: string, note = '') {
      const { data } = await api.post(`/tasks/${id}/transition/`, { status, note })
      const idx = this.tasks.findIndex((t) => t.id === id)
      if (idx >= 0) this.tasks[idx] = data
      if (this.currentTask?.id === id) this.currentTask = data
      return data
    },

    async updateProgress(id: string, progress: number) {
      const { data } = await api.post(`/tasks/${id}/progress/`, { progress })
      if (this.currentTask?.id === id) {
        this.currentTask.progress = data.progress
      }
      return data
    },

    async fetchKanban() {
      this.loading = true
      try {
        const { data } = await api.get('/tasks/kanban/')
        this.kanbanData = data
      } finally {
        this.loading = false
      }
    },

    async fetchHistory(id: string) {
      const { data } = await api.get(`/tasks/${id}/history/`)
      return data.results || data
    },

    async fetchComments(id: string) {
      const { data } = await api.get(`/tasks/${id}/comments/`)
      return data.results || data
    },

    async addComment(id: string, content: string, isInternal = false) {
      const { data } = await api.post(`/tasks/${id}/comments/`, {
        content,
        is_internal: isInternal,
      })
      return data
    },
  },
})
