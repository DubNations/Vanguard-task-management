<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  Search,
  Clock,
  Plus,
  Switch,
  Edit,
  ChatDotRound,
  User,
} from '@element-plus/icons-vue'
import StatusTag from '@/components/StatusTag.vue'
import { formatDateTime, timeAgo } from '@/utils/format'
import api from '@/api'

const router = useRouter()

interface TimelineEntry {
  id: string
  timestamp: string
  actor_name: string
  action_type: 'created' | 'status_change' | 'updated' | 'comment' | 'claim'
  task_id: string
  task_title: string
  task_no: string
  description: string
  old_status?: string
  new_status?: string
  _highlight?: boolean
}

const loading = ref(true)
const entries = ref<TimelineEntry[]>([])
const page = ref(1)
const pageSize = ref(50)
const totalEntries = ref(0)
const hasMore = ref(true)

const filters = reactive({
  actionTypes: [] as string[],
  userId: '',
  timeRange: 'all',
  search: '',
})

const autoRefreshEnabled = ref(false)
const refreshInterval = ref(30)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const userOptions = ref<any[]>([])

const actionTypeOptions = [
  { value: 'created', label: '创建', color: '#409eff' },
  { value: 'status_change', label: '状态变更', color: '#e6a23c' },
  { value: 'updated', label: '更新', color: '#67c23a' },
  { value: 'comment', label: '评论', color: '#9b59b6' },
  { value: 'claim', label: '领取', color: '#00bcd4' },
]

const timeRangeOptions = [
  { value: 'all', label: '全部时间' },
  { value: 'today', label: '今天' },
  { value: 'week', label: '本周' },
  { value: 'month', label: '本月' },
]

const refreshIntervalOptions = [
  { value: 15, label: '15秒' },
  { value: 30, label: '30秒' },
  { value: 60, label: '60秒' },
]

const statusMap: Record<string, string> = {
  PENDING: '待领取',
  IN_PROGRESS: '进行中',
  IN_REVIEW: '待审核',
  COMPLETED: '已完成',
  REJECTED: '已退回',
  CANCELLED: '已取消',
}

const statusTagType: Record<string, string> = {
  PENDING: 'info',
  IN_PROGRESS: '',
  IN_REVIEW: 'warning',
  COMPLETED: 'success',
  REJECTED: 'danger',
  CANCELLED: 'info',
}

const actionIconMap: Record<string, any> = {
  created: Plus,
  status_change: Switch,
  updated: Edit,
  comment: ChatDotRound,
  claim: User,
}

const actionColorMap: Record<string, string> = {
  created: '#409eff',
  status_change: '#e6a23c',
  updated: '#67c23a',
  comment: '#9b59b6',
  claim: '#00bcd4',
}

const fetchTimeline = async (reset = false) => {
  if (reset) {
    page.value = 1
    entries.value = []
    hasMore.value = true
  }
  loading.value = true
  try {
    const params: any = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (filters.search) params.search = filters.search
    if (filters.timeRange !== 'all') params.time_range = filters.timeRange

    const { data: taskData } = await api.get('/tasks/', { params })
    const tasks = taskData.results || taskData || []
    const allEntries: TimelineEntry[] = []

    for (const task of tasks) {
      allEntries.push({
        id: `created-${task.id}`,
        timestamp: task.created_at,
        actor_name: task.created_by_name || '系统',
        action_type: 'created',
        task_id: task.id,
        task_title: task.title,
        task_no: task.task_no,
        description: `创建了任务「${task.title}」`,
      })

      try {
        const { data: historyData } = await api.get(`/tasks/${task.id}/history/`)
        const historyItems = historyData.results || historyData || []

        for (const h of historyItems) {
          const entry: TimelineEntry = {
            id: `history-${h.id || `${task.id}-${h.timestamp}`}`,
            timestamp: h.timestamp || h.created_at,
            actor_name: h.user_name || h.actor_name || '系统',
            action_type: mapActionType(h.action || h.action_type),
            task_id: task.id,
            task_title: task.title,
            task_no: task.task_no,
            description: h.description || h.note || buildDescription(h, task.title),
          }

          if (h.old_status || h.new_status) {
            entry.old_status = h.old_status
            entry.new_status = h.new_status
            entry.action_type = 'status_change'
          }

          allEntries.push(entry)
        }
      } catch {
        // history fetch failed, skip
      }

      if (task.claimed_at) {
        allEntries.push({
          id: `claim-${task.id}`,
          timestamp: task.claimed_at,
          actor_name: task.assignee_name || '未知',
          action_type: 'claim',
          task_id: task.id,
          task_title: task.title,
          task_no: task.task_no,
          description: `领取了任务「${task.title}」`,
        })
      }
    }

    allEntries.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

    const filtered = filterEntries(allEntries)

    if (reset) {
      entries.value = filtered
    } else {
      entries.value.push(...filtered)
    }

    totalEntries.value = taskData.count || entries.value.length
    hasMore.value = tasks.length === pageSize.value
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

const mapActionType = (action: string): TimelineEntry['action_type'] => {
  if (!action) return 'updated'
  const lower = action.toLowerCase()
  if (lower.includes('create') || lower.includes('创建')) return 'created'
  if (lower.includes('status') || lower.includes('transition') || lower.includes('状态')) return 'status_change'
  if (lower.includes('claim') || lower.includes('领取')) return 'claim'
  if (lower.includes('comment') || lower.includes('评论')) return 'comment'
  return 'updated'
}

const buildDescription = (h: any, taskTitle: string): string => {
  const action = h.action || h.action_type || ''
  const lower = action.toLowerCase()
  if (lower.includes('status') || lower.includes('transition')) {
    const old = statusMap[h.old_status] || h.old_status || ''
    const cur = statusMap[h.new_status] || h.new_status || ''
    return `将任务「${taskTitle}」状态从 ${old} 变更为 ${cur}`
  }
  if (lower.includes('claim')) return `领取了任务「${taskTitle}」`
  if (lower.includes('comment')) return `评论了任务「${taskTitle}」`
  return `更新了任务「${taskTitle}」`
}

const filterEntries = (list: TimelineEntry[]): TimelineEntry[] => {
  let result = [...list]

  if (filters.actionTypes.length > 0) {
    result = result.filter((e) => filters.actionTypes.includes(e.action_type))
  }

  if (filters.userId) {
    result = result.filter((e) => e.actor_name === filters.userId)
  }

  if (filters.timeRange !== 'all') {
    const now = new Date()
    let start: Date
    switch (filters.timeRange) {
      case 'today':
        start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
        break
      case 'week':
        start = new Date(now)
        start.setDate(start.getDate() - start.getDay())
        start.setHours(0, 0, 0, 0)
        break
      case 'month':
        start = new Date(now.getFullYear(), now.getMonth(), 1)
        break
      default:
        start = new Date(0)
    }
    result = result.filter((e) => new Date(e.timestamp) >= start)
  }

  if (filters.search) {
    const keyword = filters.search.toLowerCase()
    result = result.filter(
      (e) =>
        e.task_title.toLowerCase().includes(keyword) ||
        e.task_no.toLowerCase().includes(keyword) ||
        e.description.toLowerCase().includes(keyword)
    )
  }

  return result
}

const filteredEntries = computed(() => filterEntries(entries.value))

const uniqueActors = computed(() => {
  const names = new Set(entries.value.map((e) => e.actor_name))
  return Array.from(names).sort()
})

const loadMore = () => {
  page.value++
  fetchTimeline()
}

const handleRefresh = () => {
  fetchTimeline(true)
}

const toggleAutoRefresh = () => {
  autoRefreshEnabled.value = !autoRefreshEnabled.value
  if (autoRefreshEnabled.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

const startAutoRefresh = () => {
  stopAutoRefresh()
  refreshTimer = setInterval(() => {
    fetchTimeline(true)
  }, refreshInterval.value * 1000)
}

const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

watch(refreshInterval, () => {
  if (autoRefreshEnabled.value) {
    startAutoRefresh()
  }
})

watch(
  () => filters.actionTypes,
  () => {},
  { deep: true }
)

const getActionIcon = (type: string) => actionIconMap[type] || Edit
const getActionColor = (type: string) => actionColorMap[type] || '#909399'
const getActionLabel = (type: string) => actionTypeOptions.find((o) => o.value === type)?.label || type
const getStatusLabel = (status: string) => statusMap[status] || status
const getStatusTagType = (status: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' => {
  return (statusTagType[status] as any) || 'info'
}

const goToTask = (taskId: string) => {
  router.push(`/tasks/${taskId}`)
}

const fetchUsers = async () => {
  try {
    const { data } = await api.get('/auth/users/')
    userOptions.value = data.results || data || []
  } catch {
    userOptions.value = []
  }
}

onMounted(() => {
  fetchTimeline(true)
  fetchUsers()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<template>
  <div class="page-container">
    <div class="page-container__header">
      <h2>操作时间线</h2>
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-input
          v-model="filters.search"
          placeholder="搜索任务标题..."
          style="width: 200px"
          clearable
          @clear="fetchTimeline(true)"
          @keyup.enter="fetchTimeline(true)"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>

        <el-select
          v-model="filters.actionTypes"
          placeholder="操作类型"
          multiple
          collapse-tags
          collapse-tags-tooltip
          style="width: 200px"
          @change="() => {}"
        >
          <el-option
            v-for="o in actionTypeOptions"
            :key="o.value"
            :label="o.label"
            :value="o.value"
          />
        </el-select>

        <el-select
          v-model="filters.userId"
          placeholder="操作人"
          clearable
          style="width: 150px"
        >
          <el-option label="全部操作人" value="" />
          <el-option
            v-for="name in uniqueActors"
            :key="name"
            :label="name"
            :value="name"
          />
        </el-select>

        <el-select
          v-model="filters.timeRange"
          placeholder="时间范围"
          style="width: 130px"
        >
          <el-option
            v-for="o in timeRangeOptions"
            :key="o.value"
            :label="o.label"
            :value="o.value"
          />
        </el-select>

        <el-button type="primary" @click="handleRefresh">
          <el-icon style="margin-right: 4px;"><Refresh /></el-icon>
          刷新
        </el-button>

        <el-button
          :type="autoRefreshEnabled ? 'success' : 'info'"
          @click="toggleAutoRefresh"
        >
          <el-icon style="margin-right: 4px;"><Clock /></el-icon>
          {{ autoRefreshEnabled ? '自动刷新中' : '自动刷新' }}
        </el-button>

        <el-select
          v-model="refreshInterval"
          style="width: 90px"
          :disabled="!autoRefreshEnabled"
        >
          <el-option
            v-for="o in refreshIntervalOptions"
            :key="o.value"
            :label="o.label"
            :value="o.value"
          />
        </el-select>
      </div>
    </div>

    <div v-loading="loading" class="timeline-wrapper">
      <template v-if="filteredEntries.length > 0">
        <div class="timeline">
          <div
            v-for="entry in filteredEntries"
            :key="entry.id"
            class="timeline-item"
            :class="{ 'timeline-item--highlight': entry._highlight }"
          >
            <div class="timeline-item__time">
              <el-tooltip :content="formatDateTime(entry.timestamp)" placement="top">
                <span>{{ timeAgo(entry.timestamp) }}</span>
              </el-tooltip>
            </div>

            <div class="timeline-item__dot" :style="{ backgroundColor: getActionColor(entry.action_type) }" />

            <div class="timeline-item__content">
              <div class="timeline-item__header">
                <el-icon :style="{ color: getActionColor(entry.action_type), marginRight: '6px' }">
                  <component :is="getActionIcon(entry.action_type)" />
                </el-icon>
                <span class="timeline-item__actor">{{ entry.actor_name }}</span>
                <el-tag
                  size="small"
                  :color="getActionColor(entry.action_type)"
                  style="color: #fff; border: none; margin: 0 8px;"
                >
                  {{ getActionLabel(entry.action_type) }}
                </el-tag>
                <el-link type="primary" @click="goToTask(entry.task_id)">
                  {{ entry.task_no }} {{ entry.task_title }}
                </el-link>
              </div>

              <div class="timeline-item__desc">{{ entry.description }}</div>

              <div v-if="entry.action_type === 'status_change' && entry.old_status && entry.new_status" class="timeline-item__status-change">
                <el-tag :type="getStatusTagType(entry.old_status)" size="small" effect="plain">
                  {{ getStatusLabel(entry.old_status) }}
                </el-tag>
                <span class="timeline-item__arrow">→</span>
                <el-tag :type="getStatusTagType(entry.new_status)" size="small">
                  {{ getStatusLabel(entry.new_status) }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>

        <div v-if="hasMore" style="text-align: center; margin-top: 24px;">
          <el-button @click="loadMore" :loading="loading">
            加载更多
          </el-button>
        </div>
      </template>

      <el-empty v-else-if="!loading" description="暂无操作记录" />
    </div>
  </div>
</template>

<style scoped lang="scss">
.timeline-wrapper {
  min-height: 400px;
  padding: 16px 0;
}

.timeline {
  position: relative;
  padding-left: 20px;

  &::before {
    content: '';
    position: absolute;
    left: 140px;
    top: 0;
    bottom: 0;
    width: 2px;
    background-color: #e4e7ed;
  }
}

.timeline-item {
  display: flex;
  align-items: flex-start;
  position: relative;
  padding-bottom: 24px;

  &--highlight {
    animation: pulse 2s ease-in-out;
  }

  &__time {
    width: 120px;
    flex-shrink: 0;
    text-align: right;
    padding-right: 20px;
    font-size: 13px;
    color: #909399;
    line-height: 24px;
    cursor: default;

    span {
      border-bottom: 1px dashed #c0c4cc;
    }
  }

  &__dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
    position: relative;
    left: -6px;
    top: 6px;
    z-index: 1;
    box-shadow: 0 0 0 3px #fff;
  }

  &__content {
    flex: 1;
    background: #fff;
    border: 1px solid #ebeef5;
    border-radius: 8px;
    padding: 14px 18px;
    margin-left: 8px;
    transition: box-shadow 0.2s;

    &:hover {
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
    }
  }

  &__header {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 6px;
  }

  &__actor {
    font-weight: 600;
    color: #303133;
  }

  &__desc {
    font-size: 13px;
    color: #606266;
    line-height: 1.6;
  }

  &__status-change {
    margin-top: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__arrow {
    color: #c0c4cc;
    font-size: 16px;
  }
}

@keyframes pulse {
  0% {
    background-color: transparent;
  }
  30% {
    background-color: rgba(64, 158, 255, 0.08);
  }
  100% {
    background-color: transparent;
  }
}
</style>
