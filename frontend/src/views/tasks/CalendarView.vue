<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'
import { formatDate } from '@/utils/format'

interface CalendarTask {
  id: string
  title: string
  status: string
  priority: string
  deadline: string
  assignee: { id: string; username: string; name: string } | null
  assignee_name: string
  is_overdue: boolean
}

interface CalendarDay {
  date: Date
  dateStr: string
  day: number
  isCurrentMonth: boolean
  isToday: boolean
  tasks: CalendarTask[]
}

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const draggingTask = ref<CalendarTask | null>(null)
const dropTargetDate = ref<string | null>(null)
const updatingTaskId = ref<string | null>(null)

const currentView = ref<'month' | 'week'>('month')
const currentDate = ref(new Date())
const tasks = ref<CalendarTask[]>([])
const users = ref<any[]>([])

const filters = reactive({
  priority: '',
  status: '',
  assignee: '',
  myTasksOnly: false,
})

const statusColors: Record<string, string> = {
  PENDING: '#909399',
  IN_PROGRESS: '#409eff',
  IN_REVIEW: '#e6a23c',
  COMPLETED: '#67c23a',
  REJECTED: '#f56c6c',
}

const statusLabels: Record<string, string> = {
  PENDING: '待领取',
  IN_PROGRESS: '进行中',
  IN_REVIEW: '待审核',
  COMPLETED: '已完成',
  REJECTED: '已退回',
}

const priorityOptions = [
  { value: '', label: '全部优先级' },
  { value: 'LOW', label: '低' },
  { value: 'MEDIUM', label: '中' },
  { value: 'HIGH', label: '高' },
  { value: 'URGENT', label: '紧急' },
]

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'PENDING', label: '待领取' },
  { value: 'IN_PROGRESS', label: '进行中' },
  { value: 'IN_REVIEW', label: '待审核' },
  { value: 'COMPLETED', label: '已完成' },
  { value: 'REJECTED', label: '已退回' },
]

const currentYear = computed(() => currentDate.value.getFullYear())
const currentMonth = computed(() => currentDate.value.getMonth())

const monthLabel = computed(() => {
  return `${currentYear.value}年${currentMonth.value + 1}月`
})

const weekLabel = computed(() => {
  const start = getWeekStart(currentDate.value)
  const end = new Date(start)
  end.setDate(end.getDate() + 6)
  const fmt = (d: Date) => `${d.getMonth() + 1}月${d.getDate()}日`
  return `${fmt(start)} - ${fmt(end)}`
})

const headerTitle = computed(() => {
  return currentView.value === 'month' ? monthLabel.value : weekLabel.value
})

const weekDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const isSameDay = (d1: Date, d2: Date) => {
  return d1.getFullYear() === d2.getFullYear() &&
    d1.getMonth() === d2.getMonth() &&
    d1.getDate() === d2.getDate()
}

const formatDateStr = (d: Date) => {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const getWeekStart = (date: Date) => {
  const d = new Date(date)
  const day = d.getDay()
  const diff = day === 0 ? -6 : 1 - day
  d.setDate(d.getDate() + diff)
  d.setHours(0, 0, 0, 0)
  return d
}

const monthDays = computed<CalendarDay[]>(() => {
  const year = currentYear.value
  const month = currentMonth.value
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const today = new Date()

  const startOffset = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1
  const days: CalendarDay[] = []

  for (let i = startOffset - 1; i >= 0; i--) {
    const d = new Date(year, month, -i)
    days.push(createDayObj(d, false, today))
  }

  for (let i = 1; i <= lastDay.getDate(); i++) {
    const d = new Date(year, month, i)
    days.push(createDayObj(d, true, today))
  }

  const remaining = 42 - days.length
  for (let i = 1; i <= remaining; i++) {
    const d = new Date(year, month + 1, i)
    days.push(createDayObj(d, false, today))
  }

  return days
})

const weekDays_computed = computed<CalendarDay[]>(() => {
  const start = getWeekStart(currentDate.value)
  const today = new Date()
  const days: CalendarDay[] = []

  for (let i = 0; i < 7; i++) {
    const d = new Date(start)
    d.setDate(d.getDate() + i)
    days.push(createDayObj(d, true, today))
  }

  return days
})

function createDayObj(d: Date, isCurrentMonth: boolean, today: Date): CalendarDay {
  const dateStr = formatDateStr(d)
  return {
    date: new Date(d),
    dateStr,
    day: d.getDate(),
    isCurrentMonth,
    isToday: isSameDay(d, today),
    tasks: [],
  }
}

const filteredTasks = computed(() => {
  return tasks.value.filter((task) => {
    if (filters.priority && task.priority !== filters.priority) return false
    if (filters.status && task.status !== filters.status) return false
    if (filters.assignee && task.assignee?.id !== filters.assignee) return false
    if (filters.myTasksOnly && task.assignee?.id !== authStore.user?.id) return false
    return true
  })
})

const calendarDays = computed(() => {
  const days = currentView.value === 'month' ? monthDays.value : weekDays_computed.value
  const taskMap = new Map<string, CalendarTask[]>()

  for (const task of filteredTasks.value) {
    if (!task.deadline) continue
    const d = new Date(task.deadline)
    const key = formatDateStr(d)
    if (!taskMap.has(key)) taskMap.set(key, [])
    taskMap.get(key)!.push(task)
  }

  return days.map((day) => ({
    ...day,
    tasks: taskMap.get(day.dateStr) || [],
  }))
})

const visibleTasks = (tasks: CalendarTask[], max = 3) => {
  return tasks.slice(0, max)
}

const moreCount = (tasks: CalendarTask[], max = 3) => {
  return Math.max(0, tasks.length - max)
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const { data } = await api.get('/tasks/', { params: { page_size: 200 } })
    tasks.value = data.results || data || []
  } catch {
    tasks.value = []
  } finally {
    loading.value = false
  }
}

const fetchUsers = async () => {
  try {
    const { data } = await api.get('/auth/users/')
    users.value = data.results || data || []
  } catch {
    users.value = []
  }
}

const navigatePrev = () => {
  const d = new Date(currentDate.value)
  if (currentView.value === 'month') {
    d.setMonth(d.getMonth() - 1)
  } else {
    d.setDate(d.getDate() - 7)
  }
  currentDate.value = d
}

const navigateNext = () => {
  const d = new Date(currentDate.value)
  if (currentView.value === 'month') {
    d.setMonth(d.getMonth() + 1)
  } else {
    d.setDate(d.getDate() + 7)
  }
  currentDate.value = d
}

const goToday = () => {
  currentDate.value = new Date()
}

const toggleView = () => {
  currentView.value = currentView.value === 'month' ? 'week' : 'month'
}

const goToTask = (taskId: string) => {
  router.push(`/tasks/${taskId}`)
}

const isOverdue = (task: CalendarTask) => {
  if (!task.deadline) return false
  return new Date(task.deadline) < new Date() && task.status !== 'COMPLETED'
}

const onDragStart = (e: DragEvent, task: CalendarTask) => {
  draggingTask.value = task
  e.dataTransfer!.effectAllowed = 'move'
  e.dataTransfer!.setData('text/plain', task.id)
}

const onDragOver = (e: DragEvent, dateStr: string) => {
  e.preventDefault()
  e.dataTransfer!.dropEffect = 'move'
  dropTargetDate.value = dateStr
}

const onDragLeave = () => {
  dropTargetDate.value = null
}

const onDrop = async (e: DragEvent, dateStr: string) => {
  e.preventDefault()
  dropTargetDate.value = null

  if (!draggingTask.value) return
  if (draggingTask.value.deadline && formatDateStr(new Date(draggingTask.value.deadline)) === dateStr) {
    draggingTask.value = null
    return
  }

  const task = draggingTask.value
  const oldDeadline = task.deadline
  task.deadline = dateStr + 'T00:00:00'
  updatingTaskId.value = task.id

  try {
    await api.patch(`/tasks/${task.id}/`, { deadline: task.deadline })
    ElMessage.success('截止日期已更新')
  } catch {
    task.deadline = oldDeadline
    ElMessage.error('更新失败，已还原')
  } finally {
    updatingTaskId.value = null
    draggingTask.value = null
  }
}

const createDialogVisible = ref(false)
const createLoading = ref(false)
const createForm = reactive({
  title: '',
  description: '',
  priority: 'MEDIUM',
  deadline: '',
  assignee: '',
})

const openCreateDialog = (dateStr: string) => {
  createForm.deadline = dateStr
  createDialogVisible.value = true
}

const resetCreateForm = () => {
  createForm.title = ''
  createForm.description = ''
  createForm.priority = 'MEDIUM'
  createForm.deadline = ''
  createForm.assignee = ''
}

const handleCreateTask = async () => {
  if (!createForm.title.trim()) {
    ElMessage.warning('请输入任务标题')
    return
  }
  createLoading.value = true
  try {
    const payload: any = {
      title: createForm.title,
      description: createForm.description,
      priority: createForm.priority,
      deadline: createForm.deadline ? createForm.deadline + 'T00:00:00' : undefined,
    }
    if (createForm.assignee) payload.assignee = createForm.assignee
    await api.post('/tasks/', payload)
    ElMessage.success('任务创建成功')
    createDialogVisible.value = false
    resetCreateForm()
    await fetchTasks()
  } catch {
    // handled by interceptor
  } finally {
    createLoading.value = false
  }
}

watch(filters, () => {}, { deep: true })

onMounted(() => {
  fetchTasks()
  fetchUsers()
})
</script>

<template>
  <div class="page-container">
    <div class="page-container__header">
      <h2>日历视图</h2>
      <el-button @click="fetchTasks" :loading="loading">刷新</el-button>
    </div>

    <div class="calendar-toolbar">
      <div class="calendar-toolbar__left">
        <el-button-group>
          <el-button @click="navigatePrev">
            <el-icon><ArrowLeft /></el-icon>
          </el-button>
          <el-button @click="goToday">今天</el-button>
          <el-button @click="navigateNext">
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </el-button-group>
        <span class="calendar-toolbar__title">{{ headerTitle }}</span>
      </div>
      <div class="calendar-toolbar__right">
        <el-button :type="currentView === 'month' ? 'primary' : ''" @click="currentView = 'month'">月</el-button>
        <el-button :type="currentView === 'week' ? 'primary' : ''" @click="currentView = 'week'">周</el-button>
      </div>
    </div>

    <div class="calendar-filters">
      <el-select v-model="filters.priority" placeholder="优先级" clearable style="width: 130px;">
        <el-option v-for="o in priorityOptions" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 130px;">
        <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-select v-model="filters.assignee" placeholder="指派人" clearable filterable style="width: 160px;">
        <el-option v-for="u in users" :key="u.id" :label="u.username || u.name" :value="u.id" />
      </el-select>
      <el-switch v-model="filters.myTasksOnly" active-text="仅我的任务" style="margin-left: 8px;" />
    </div>

    <div class="calendar-grid" :class="{ 'calendar-grid--week': currentView === 'week' }" v-loading="loading">
      <div class="calendar-grid__header">
        <div v-for="day in weekDays" :key="day" class="calendar-grid__header-cell">
          {{ day }}
        </div>
      </div>
      <div class="calendar-grid__body">
        <div
          v-for="(day, idx) in calendarDays"
          :key="idx"
          class="calendar-cell"
          :class="{
            'calendar-cell--other': !day.isCurrentMonth,
            'calendar-cell--today': day.isToday,
            'calendar-cell--drop-target': dropTargetDate === day.dateStr,
          }"
          @dragover="onDragOver($event, day.dateStr)"
          @dragleave="onDragLeave"
          @drop="onDrop($event, day.dateStr)"
          @click.self="openCreateDialog(day.dateStr)"
        >
          <div class="calendar-cell__day" :class="{ 'calendar-cell__day--today': day.isToday }">
            {{ day.day }}
          </div>
          <div class="calendar-cell__tasks">
            <div
              v-for="task in visibleTasks(day.tasks)"
              :key="task.id"
              class="task-card"
              :class="{ 'task-card--overdue': isOverdue(task), 'task-card--dragging': draggingTask?.id === task.id }"
              :style="{ borderLeftColor: statusColors[task.status] || '#909399' }"
              draggable="true"
              @dragstart="onDragStart($event, task)"
              @click.stop="goToTask(task.id)"
            >
              <div class="task-card__header">
                <span class="task-card__title">{{ task.title }}</span>
                <span
                  class="task-card__priority"
                  :style="{ background: statusColors[task.status] || '#909399' }"
                />
              </div>
              <div class="task-card__info">
                <el-tag size="small" :style="{ background: statusColors[task.status], color: '#fff', border: 'none' }">
                  {{ statusLabels[task.status] || task.status }}
                </el-tag>
                <span v-if="task.assignee_name" class="task-card__assignee">{{ task.assignee_name }}</span>
              </div>
              <div v-if="isOverdue(task)" class="task-card__overdue-badge">逾期</div>
            </div>
            <div
              v-if="moreCount(day.tasks) > 0"
              class="task-card__more"
              @click.stop="openCreateDialog(day.dateStr)"
            >
              +{{ moreCount(day.tasks) }} 更多
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="createDialogVisible" title="快速创建任务" width="480px" destroy-on-close>
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="createForm.title" placeholder="请输入任务标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="createForm.priority" style="width: 100%;">
            <el-option v-for="o in priorityOptions.filter(o => o.value)" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker
            v-model="createForm.deadline"
            type="date"
            placeholder="选择截止日期"
            style="width: 100%;"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="指派人">
          <el-select v-model="createForm.assignee" placeholder="选择指派人（可选）" clearable filterable style="width: 100%;">
            <el-option v-for="u in users" :key="u.id" :label="u.username || u.name" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="请输入任务描述（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreateTask">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
export default { components: { ArrowLeft, ArrowRight } }
</script>

<style scoped lang="scss">
.calendar-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  &__left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  &__title {
    font-size: 18px;
    font-weight: 600;
    color: #303133;
  }

  &__right {
    display: flex;
    gap: 4px;
  }
}

.calendar-filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.calendar-grid {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  overflow: hidden;

  &__header {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    background: #f5f7fa;
    border-bottom: 1px solid #ebeef5;
  }

  &__header-cell {
    padding: 12px;
    text-align: center;
    font-size: 14px;
    font-weight: 600;
    color: #606266;
  }

  &__body {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
  }

  &--week &__body {
    grid-template-rows: 1fr;
  }
}

.calendar-cell {
  min-height: 120px;
  padding: 8px;
  border-right: 1px solid #ebeef5;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: background 0.2s;

  &:nth-child(7n) {
    border-right: none;
  }

  &:hover {
    background: #f5f7fa;
  }

  &--other {
    background: #fafafa;
    .calendar-cell__day {
      color: #c0c4cc;
    }
  }

  &--today {
    background: #ecf5ff;
  }

  &--drop-target {
    background: #d9ecff;
    outline: 2px dashed #409eff;
    outline-offset: -2px;
  }

  &__day {
    font-size: 14px;
    font-weight: 500;
    color: #303133;
    margin-bottom: 4px;

    &--today {
      display: inline-block;
      width: 24px;
      height: 24px;
      line-height: 24px;
      text-align: center;
      background: #409eff;
      color: #fff;
      border-radius: 50%;
    }
  }

  &__tasks {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
}

.calendar-grid--week .calendar-cell {
  min-height: 400px;
}

.task-card {
  padding: 6px 8px;
  background: #fff;
  border-radius: 4px;
  border-left: 3px solid #dcdfe6;
  cursor: grab;
  transition: all 0.2s;
  font-size: 12px;
  position: relative;

  &:hover {
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
    transform: translateY(-1px);
  }

  &:active {
    cursor: grabbing;
  }

  &--overdue {
    border-left-color: #f56c6c !important;
    background: #fef0f0;
  }

  &--dragging {
    opacity: 0.4;
  }

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
  }

  &__title {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #303133;
    font-weight: 500;
  }

  &__priority {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  &__info {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 4px;
  }

  &__assignee {
    font-size: 11px;
    color: #909399;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__overdue-badge {
    position: absolute;
    top: 4px;
    right: 4px;
    font-size: 10px;
    color: #f56c6c;
    font-weight: 600;
  }

  &__more {
    font-size: 12px;
    color: #409eff;
    cursor: pointer;
    padding: 2px 0;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
