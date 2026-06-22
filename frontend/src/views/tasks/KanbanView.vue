<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import draggable from 'vuedraggable'
import api from '@/api'
import { ElMessage } from 'element-plus'
import StatusTag from '@/components/StatusTag.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import { formatDate } from '@/utils/format'

const router = useRouter()
const loading = ref(false)
const error = ref<string | null>(null)
const columns = ref<Record<string, any>>({})
const transitioning = ref<string | null>(null)

const statusOrder = ['PENDING', 'IN_PROGRESS', 'IN_REVIEW', 'COMPLETED', 'REJECTED']
const statusColors: Record<string, string> = {
  PENDING: '#909399', IN_PROGRESS: '#409eff', IN_REVIEW: '#e6a23c',
  COMPLETED: '#67c23a', REJECTED: '#f56c6c', CANCELLED: '#c0c4cc',
}
const priorityBorderColors: Record<string, string> = {
  LOW: '#67c23a', MEDIUM: '#409eff', HIGH: '#e6a23c', URGENT: '#f56c6c',
}

const priorityOptions = [
  { label: '全部优先级', value: '' },
  { label: '低', value: 'LOW' },
  { label: '中', value: 'MEDIUM' },
  { label: '高', value: 'HIGH' },
  { label: '紧急', value: 'URGENT' },
]

const filters = reactive({
  priority: '',
  assignee: '',
  search: '',
})

const users = ref<any[]>([])

const collapsedColumns = ref<Record<string, boolean>>((() => {
  try {
    const saved = localStorage.getItem('kanban-collapsed')
    return saved ? JSON.parse(saved) : {}
  } catch {
    return {}
  }
})())

const toggleCollapse = (status: string) => {
  collapsedColumns.value[status] = !collapsedColumns.value[status]
  localStorage.setItem('kanban-collapsed', JSON.stringify(collapsedColumns.value))
}

const buildQueryParams = () => {
  const params: Record<string, string> = {}
  if (filters.priority) params.priority = filters.priority
  if (filters.assignee) params.assignee = filters.assignee
  if (filters.search) params.search = filters.search
  return params
}

const fetchKanban = async () => {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get('/tasks/kanban/', { params: buildQueryParams() })
    columns.value = data
  } catch {
    error.value = '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

const fetchUsers = async () => {
  try {
    const { data } = await api.get('/auth/users/')
    users.value = Array.isArray(data) ? data : data.results || []
  } catch {
    users.value = []
  }
}

const resetFilters = () => {
  filters.priority = ''
  filters.assignee = ''
  filters.search = ''
}

const goToTask = (taskId: string) => {
  router.push(`/tasks/${taskId}`)
}

// 领取任务
const claimingId = ref<string | null>(null)
const handleClaimTask = async (task: any) => {
  if (task.task_mode === 'ASSIGNED') return
  try {
    claimingId.value = task.id
    await api.post(`/tasks/${task.id}/claim/`)
    ElMessage.success(`已领取: ${task.title}`)
    fetchKanban()
  } catch {
    // handled by interceptor
  } finally {
    claimingId.value = null
  }
}

const getColumnTasks = (status: string) => {
  return columns.value[status]?.tasks || []
}

const setColumnTasks = (status: string, newTasks: any[]) => {
  if (columns.value[status]) {
    columns.value[status].tasks = newTasks
    columns.value[status].count = newTasks.length
  }
}

const onDragChange = async (status: string, evt: any) => {
  if (evt.added) {
    const task = evt.added.element
    const oldStatus = task.status
    task.status = status
    transitioning.value = task.id
    try {
      await api.post(`/tasks/${task.id}/transition/`, { status })
      if (columns.value[oldStatus]) {
        columns.value[oldStatus].count = columns.value[oldStatus].tasks.length
      }
      if (columns.value[status]) {
        columns.value[status].count = columns.value[status].tasks.length
      }
    } catch (e: any) {
      // BUG-009: 拖拽失败提示用户
      const msg = e?.response?.data?.error || '状态更新失败，已回退'
      ElMessage.error(msg)
      const sourceTasks = columns.value[status].tasks
      const idx = sourceTasks.findIndex((t: any) => t.id === task.id)
      if (idx !== -1) sourceTasks.splice(idx, 1)
      task.status = oldStatus
      if (columns.value[oldStatus]) {
        columns.value[oldStatus].tasks.splice(evt.added.newIndex, 0, task)
      }
    } finally {
      transitioning.value = null
    }
  }
}

const getInitials = (name: string) => {
  if (!name) return '?'
  return name.slice(0, 1)
}

const truncateTag = (tag: string, max = 8) => {
  return tag.length > max ? tag.slice(0, max) + '...' : tag
}

watch(filters, () => {
  fetchKanban()
}, { deep: true })

onMounted(() => {
  fetchKanban()
  fetchUsers()
})
</script>

<template>
  <div class="page-container">
    <div class="page-container__header">
      <h2>看板视图</h2>
      <el-button @click="fetchKanban" :loading="loading">刷新</el-button>
    </div>

    <div class="kanban-filters">
      <el-select v-model="filters.priority" placeholder="优先级" clearable style="width: 140px;">
        <el-option v-for="opt in priorityOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
      </el-select>
      <el-select v-model="filters.assignee" placeholder="指派人" clearable filterable style="width: 160px;">
        <el-option v-for="user in users" :key="user.id" :label="user.username || user.name" :value="user.id" />
      </el-select>
      <el-input v-model="filters.search" placeholder="搜索标题..." clearable style="width: 220px;" :prefix-icon="Search" />
      <el-button @click="resetFilters">重置</el-button>
    </div>

    <div class="kanban-board" v-loading="loading">
      <el-result v-if="error" icon="error" :title="error">
        <template #extra><el-button @click="fetchKanban">重试</el-button></template>
      </el-result>
      <div v-for="status in statusOrder" :key="status" class="kanban-column">
        <div class="kanban-column__header" :style="{ borderTopColor: statusColors[status] }">
          <div style="display:flex; align-items:center; gap:8px;">
            <el-icon class="collapse-btn" @click.stop="toggleCollapse(status)">
              <ArrowRight v-if="collapsedColumns[status]" />
              <ArrowDown v-else />
            </el-icon>
            <StatusTag :status="status" />
            <span>{{ columns[status]?.label || '' }}</span>
          </div>
          <el-tag size="small" round>{{ columns[status]?.count || 0 }}</el-tag>
        </div>
        <div v-show="!collapsedColumns[status]" class="kanban-column__body">
          <draggable
            :list="columns[status]?.tasks || []"
            item-key="id"
            group="tasks"
            ghost-class="kanban-ghost"
            drag-class="kanban-drag"
            @change="onDragChange(status, $event)"
          >
            <template #item="{ element: task }">
              <div
                class="kanban-card"
                :class="{ 'kanban-card--transitioning': transitioning === task.id }"
                :style="{ borderLeftColor: priorityBorderColors[task.priority] || '#dcdfe6' }"
                @click="goToTask(task.id)"
              >
                <div class="kanban-card__title">{{ task.title }}</div>
                <div class="kanban-card__tags">
                  <PriorityTag :priority="task.priority" />
                  <el-tag size="small" :type="task.task_mode === 'ASSIGNED' ? 'info' : 'warning'" style="margin-left:4px;">
                    {{ task.task_mode === 'ASSIGNED' ? '派发' : task.task_mode === 'FREE_CLAIM' ? '自由揭榜' : '固定揭榜' }}
                  </el-tag>
                </div>
                <div v-if="task.assignee" class="kanban-card__assignee">
                  <el-avatar :size="20" :style="{ background: statusColors[status] || '#909399', fontSize: '11px' }">
                    {{ getInitials(task.assignee.username || task.assignee.name) }}
                  </el-avatar>
                  <span class="assignee-name">{{ task.assignee.username || task.assignee.name }}</span>
                </div>
                <div class="kanban-card__deadline" v-if="task.deadline">
                  <span :style="{ color: task.is_overdue ? '#f56c6c' : '#909399', fontWeight: task.is_overdue ? '600' : '400' }">
                    {{ formatDate(task.deadline) }}
                    <el-tag v-if="task.is_overdue" type="danger" size="small" style="margin-left:4px;">逾期</el-tag>
                  </span>
                </div>
                <el-progress
                  v-if="task.progress > 0"
                  :percentage="task.progress"
                  :stroke-width="4"
                  :show-text="false"
                  style="margin-top: 6px;"
                />
                <div v-if="task.tags?.length" class="kanban-card__tags-row">
                  <el-tag v-for="tag in task.tags.slice(0, 3)" :key="tag" size="small" type="info" effect="plain" class="card-tag">
                    {{ truncateTag(tag) }}
                  </el-tag>
                </div>
                <div class="kanban-card__footer">
                  <span class="kanban-card__meta">{{ task.task_no }}</span>
                  <div class="kanban-card__counts">
                    <el-button
                      v-if="status === 'PENDING' && task.task_mode !== 'ASSIGNED'"
                      size="small"
                      type="primary"
                      :loading="claimingId === task.id"
                      @click.stop="handleClaimTask(task)"
                    >
                      领取
                    </el-button>
                    <span v-if="task.comment_count > 0" class="count-item">
                      <el-icon><ChatDotRound /></el-icon>{{ task.comment_count }}
                    </span>
                    <span v-if="task.file_count > 0" class="count-item">
                      <el-icon><Document /></el-icon>{{ task.file_count }}
                    </span>
                  </div>
                </div>
              </div>
            </template>
          </draggable>
          <el-empty v-if="!columns[status]?.tasks?.length" description="暂无" :image-size="40" />
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Search, ArrowRight, ArrowDown, ChatDotRound, Document } from '@element-plus/icons-vue'
export default { components: { Search, ArrowRight, ArrowDown, ChatDotRound, Document } }
</script>

<style scoped lang="scss">
.kanban-filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.kanban-board {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  min-height: 500px;
}

.kanban-column {
  flex: 1;
  min-width: 260px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;

  &__header {
    padding: 12px 16px;
    font-weight: 600;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 3px solid #ddd;
    border-radius: 8px 8px 0 0;
  }

  &__body {
    padding: 8px;
    flex: 1;
    overflow-y: auto;
    min-height: 100px;
  }
}

.collapse-btn {
  cursor: pointer;
  font-size: 14px;
  color: #909399;
  transition: color 0.2s;

  &:hover {
    color: #409eff;
  }
}

.kanban-ghost {
  opacity: 0.4;
  background: #e8f4fd;
  border-radius: 6px;
}

.kanban-drag {
  opacity: 0.9;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.kanban-card {
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  border-left: 3px solid #dcdfe6;

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
    border-color: #e0e0e0;
    border-left-color: inherit;
    transform: translateY(-1px);
  }

  &--transitioning {
    opacity: 0.6;
    pointer-events: none;
  }

  &__title {
    font-size: 14px;
    font-weight: 500;
    color: #303133;
    margin-bottom: 6px;
    line-height: 1.4;
  }

  &__tags {
    margin-bottom: 6px;
  }

  &__assignee {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
    font-size: 12px;
    color: #606266;
  }

  .assignee-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__deadline {
    font-size: 12px;
    margin-top: 4px;
  }

  &__tags-row {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 6px;
  }

  .card-tag {
    max-width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 6px;
  }

  &__meta {
    font-size: 12px;
    color: #909399;
  }

  &__counts {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .count-item {
    display: flex;
    align-items: center;
    gap: 2px;
    font-size: 12px;
    color: #909399;
  }
}
</style>
