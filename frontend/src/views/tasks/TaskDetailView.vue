<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  UploadFilled,
  VideoPlay,
  View,
  CircleCheck,
  Close,
  Remove,
  Edit,
  Delete,
  Plus,
} from '@element-plus/icons-vue'
import api from '@/api'
import { fileApi } from '@/api/modules'
import { useAuthStore } from '@/stores/auth'
import { usePermission } from '@/composables/usePermission'
import { useTaskStatus } from '@/composables/useTaskStatus'
import StatusTag from '@/components/StatusTag.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import { formatDateTime, formatFileSize } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { canTransition } = usePermission()
const { getStatusLabel, getStatusColor, getAvailableTransitions } = useTaskStatus()

const task = ref<any>(null)
const history = ref<any[]>([])
const comments = ref<any[]>([])
const files = ref<any[]>([])
const loading = ref(true)
const newComment = ref('')
const claimLoading = ref(false)
const completeLoading = ref(false)

// Participant management
const users = ref<any[]>([])
const participantDialogVisible = ref(false)
const participantDialogMode = ref<'add' | 'edit'>('add')
const participantFormLoading = ref(false)
const editingParticipant = ref<any>(null)
const participantForm = ref({ user: '', role: 'PARTICIPANT', points: 0 })

// File upload
const fileUploadProgress = ref<Record<string, number>>({})
const isDragging = ref(false)
const selectedFileIds = ref<string[]>([])
const batchDeleteLoading = ref(false)

// Status transition
const transitionDialogVisible = ref(false)
const transitionTarget = ref('')
const transitionNote = ref('')

// Progress update
const progressValue = ref(0)
let progressDebounceTimer: ReturnType<typeof setTimeout> | null = null

const transitions = computed(() => {
  if (!task.value) return []
  return getAvailableTransitions(task.value.status)
})

const isAssignedMode = computed(() => task.value?.task_mode === 'ASSIGNED')
const isClaimMode = computed(() => task.value?.task_mode === 'FREE_CLAIM' || task.value?.task_mode === 'FIXED_CLAIM')

const canClaim = computed(() => {
  if (!task.value) return false
  return isClaimMode.value
    && task.value.status === 'PENDING'
    && !task.value.participants?.some((p: any) => p.user === authStore.user?.id)
})

const canCompleteAsChiefLead = computed(() => {
  if (!task.value || !isAssignedMode.value) return false
  if (task.value.status !== 'IN_REVIEW') return false
  if (authStore.user?.is_superuser || authStore.user?.role === 'LEADER' || authStore.user?.role === 'ADMIN') return true
  return task.value.participants?.some(
    (p: any) => p.user === authStore.user?.id && p.role === 'CHIEF_LEAD'
  )
})

const currentUserParticipant = computed(() => {
  if (!task.value) return null
  return task.value.participants?.find((p: any) => p.user === authStore.user?.id)
})

const canManageParticipants = computed(() => {
  if (authStore.user?.is_superuser || authStore.user?.role === 'LEADER' || authStore.user?.role === 'ADMIN') return true
  return task.value?.creator === authStore.user?.id
})

const canUpdateProgress = computed(() => {
  if (!task.value) return false
  if (['COMPLETED', 'CANCELLED'].includes(task.value.status)) return false
  if (authStore.user?.is_superuser || authStore.user?.role === 'LEADER' || authStore.user?.role === 'ADMIN') return true
  return task.value.assignee === authStore.user?.id || task.value.creator === authStore.user?.id
})

const selectedAllFiles = computed({
  get: () => files.value.length > 0 && selectedFileIds.value.length === files.value.length,
  set: (val: boolean) => {
    selectedFileIds.value = val ? files.value.map((f: any) => f.id) : []
  },
})

const hasSelectedFiles = computed(() => selectedFileIds.value.length > 0)

const transitionIconMap: Record<string, any> = {
  IN_PROGRESS: VideoPlay,
  IN_REVIEW: View,
  COMPLETED: CircleCheck,
  REJECTED: Close,
  CANCELLED: Remove,
}

const transitionTypeMap: Record<string, string> = {
  IN_PROGRESS: 'primary',
  IN_REVIEW: 'warning',
  COMPLETED: 'success',
  REJECTED: 'danger',
  CANCELLED: 'info',
}

function getFileType(filename: string): string {
  if (!filename) return 'other'
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  if (['pdf'].includes(ext)) return 'pdf'
  if (['xls', 'xlsx', 'csv'].includes(ext)) return 'excel'
  if (['doc', 'docx'].includes(ext)) return 'word'
  if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp'].includes(ext)) return 'image'
  if (['ppt', 'pptx'].includes(ext)) return 'ppt'
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return 'archive'
  return 'other'
}

function getFileTypeIcon(filename: string): string {
  const type = getFileType(filename)
  const iconMap: Record<string, string> = {
    pdf: '📄', excel: '📊', word: '📝', image: '🖼️', ppt: '📑', archive: '📦', other: '📎',
  }
  return iconMap[type] || '📎'
}

function getFileTypeColor(filename: string): string {
  const type = getFileType(filename)
  const colorMap: Record<string, string> = {
    pdf: '#F56C6C', excel: '#67C23A', word: '#409EFF', image: '#9B59B6', ppt: '#E6A23C', archive: '#909399', other: '#909399',
  }
  return colorMap[type] || '#909399'
}

const fetchTask = async () => {
  loading.value = true
  try {
    const id = route.params.id as string
    const [taskRes, historyRes, commentsRes, filesRes] = await Promise.all([
      api.get(`/tasks/${id}/`),
      api.get(`/tasks/${id}/history/`),
      api.get(`/tasks/${id}/comments/`),
      fileApi.list(id).catch(() => ({ data: [] })),
    ])
    task.value = taskRes.data
    history.value = historyRes.data.results || historyRes.data || []
    comments.value = commentsRes.data.results || commentsRes.data || []
    files.value = filesRes.data.results || filesRes.data || []
    progressValue.value = task.value?.progress || 0
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

const fetchUsers = async () => {
  try {
    const res = await api.get('/users/')
    users.value = res.data.results || res.data || []
  } catch {
    users.value = []
  }
}

const handleClaim = async () => {
  claimLoading.value = true
  try {
    await ElMessageBox.confirm('确定领取此任务？领取后任务将变为进行中状态。', '领取任务', {
      confirmButtonText: '确认领取',
      cancelButtonText: '取消',
      type: 'info',
    })
    await api.post(`/tasks/${route.params.id}/claim/`)
    ElMessage.success('任务领取成功')
    await fetchTask()
  } catch {
    // cancelled or error
  } finally {
    claimLoading.value = false
  }
}

const openTransitionDialog = (targetStatus: string) => {
  transitionTarget.value = targetStatus
  transitionNote.value = ''
  transitionDialogVisible.value = true
}

const confirmTransition = async () => {
  const label = getStatusLabel(transitionTarget.value)
  try {
    await api.post(`/tasks/${route.params.id}/transition/`, {
      status: transitionTarget.value,
      note: transitionNote.value || undefined,
    })
    ElMessage.success(`状态已变更为「${label}」`)
    transitionDialogVisible.value = false
    await fetchTask()
  } catch {
    // handled by interceptor
  }
}

const handleTransition = async (targetStatus: string) => {
  openTransitionDialog(targetStatus)
}

const handleCompleteParticipant = async (participantId: string) => {
  completeLoading.value = true
  try {
    await ElMessageBox.confirm('确认该领取人已完成任务？将为其发放积分。', '确认完成', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await api.post(`/tasks/${route.params.id}/participants/${participantId}/complete/`)
    ElMessage.success('已确认完成，积分已发放')
    await fetchTask()
  } catch {
    // cancelled or error
  } finally {
    completeLoading.value = false
  }
}

const openAddParticipant = () => {
  participantDialogMode.value = 'add'
  participantForm.value = { user: '', role: 'PARTICIPANT', points: 0 }
  editingParticipant.value = null
  participantDialogVisible.value = true
  if (!users.value.length) fetchUsers()
}

const openEditParticipant = (participant: any) => {
  participantDialogMode.value = 'edit'
  editingParticipant.value = participant
  participantForm.value = {
    user: participant.user,
    role: participant.role,
    points: participant.points || 0,
  }
  participantDialogVisible.value = true
  if (!users.value.length) fetchUsers()
}

const submitParticipant = async () => {
  if (participantDialogMode.value === 'add' && !participantForm.value.user) {
    ElMessage.warning('请选择用户')
    return
  }
  participantFormLoading.value = true
  try {
    const taskId = route.params.id as string
    if (participantDialogMode.value === 'add') {
      await api.post(`/tasks/${taskId}/participants/`, participantForm.value)
      ElMessage.success('参与者已添加')
    } else {
      await api.put(`/tasks/${taskId}/participants/${editingParticipant.value.id}/`, {
        role: participantForm.value.role,
        points: participantForm.value.points,
      })
      ElMessage.success('参与者已更新')
    }
    participantDialogVisible.value = false
    await fetchTask()
  } catch {
    // handled by interceptor
  } finally {
    participantFormLoading.value = false
  }
}

const removeParticipant = async (participant: any) => {
  try {
    await ElMessageBox.confirm(
      `确定移除参与者「${participant.user_name}」？此操作不可撤销。`,
      '移除确认',
      { type: 'warning' }
    )
    await api.delete(`/tasks/${route.params.id}/participants/${participant.id}/`)
    ElMessage.success('参与者已移除')
    await fetchTask()
  } catch {
    // cancelled or error
  }
}

const handleProgressChange = (val: number) => {
  if (progressDebounceTimer) clearTimeout(progressDebounceTimer)
  progressDebounceTimer = setTimeout(async () => {
    try {
      await api.post(`/tasks/${route.params.id}/progress/`, { progress: val })
      ElMessage.success('进度已更新')
      if (task.value) task.value.progress = val
    } catch {
      // handled by interceptor
    }
  }, 500)
}

const handleUpload = async (options: any) => {
  const fileName = options.file.name
  fileUploadProgress.value[fileName] = 0
  try {
    await fileApi.upload(route.params.id as string, options.file)
    ElMessage.success('文件上传成功')
    const filesRes = await fileApi.list(route.params.id as string)
    files.value = filesRes.data.results || filesRes.data || []
    options.onSuccess()
  } catch (err) {
    options.onError(err)
  } finally {
    delete fileUploadProgress.value[fileName]
  }
}

const handleUploadProgress = (event: any, file: any) => {
  if (event.percent) {
    fileUploadProgress.value[file.name] = Math.round(event.percent)
  }
}

const handleDragOver = (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = true
}

const handleDragLeave = () => {
  isDragging.value = false
}

const handleDrop = async (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = false
  const droppedFiles = e.dataTransfer?.files
  if (!droppedFiles?.length) return
  for (let i = 0; i < droppedFiles.length; i++) {
    const file = droppedFiles[i]
    fileUploadProgress.value[file.name] = 0
    try {
      await fileApi.upload(route.params.id as string, file)
    } catch {
      ElMessage.error(`文件「${file.name}」上传失败`)
    } finally {
      delete fileUploadProgress.value[file.name]
    }
  }
  ElMessage.success('文件上传完成')
  const filesRes = await fileApi.list(route.params.id as string)
  files.value = filesRes.data.results || filesRes.data || []
}

const toggleFileSelection = (fileId: string) => {
  const idx = selectedFileIds.value.indexOf(fileId)
  if (idx >= 0) {
    selectedFileIds.value.splice(idx, 1)
  } else {
    selectedFileIds.value.push(fileId)
  }
}

const handleBatchDelete = async () => {
  if (!selectedFileIds.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedFileIds.value.length} 个文件？此操作不可撤销。`,
      '批量删除',
      { type: 'warning' }
    )
    batchDeleteLoading.value = true
    await Promise.all(selectedFileIds.value.map((id) => fileApi.delete(id)))
    ElMessage.success('批量删除成功')
    selectedFileIds.value = []
    const filesRes = await fileApi.list(route.params.id as string)
    files.value = filesRes.data.results || filesRes.data || []
  } catch {
    // cancelled or error
  } finally {
    batchDeleteLoading.value = false
  }
}

const handleDownloadFile = async (file: any) => {
  try {
    const res = await fileApi.download(file.id)
    const blob = new Blob([res.data])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = file.filename || file.original_name || 'download'
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('下载失败')
  }
}

const handleDeleteFile = async (file: any) => {
  try {
    await ElMessageBox.confirm(`确定删除文件「${file.filename || file.original_name}」？`, '删除确认', {
      type: 'warning',
    })
    await fileApi.delete(file.id)
    ElMessage.success('文件已删除')
    const filesRes = await fileApi.list(route.params.id as string)
    files.value = filesRes.data.results || filesRes.data || []
  } catch {
    // cancelled or error
  }
}

const addComment = async () => {
  if (!newComment.value.trim()) return
  try {
    await api.post(`/tasks/${route.params.id}/comments/`, { content: newComment.value })
    newComment.value = ''
    ElMessage.success('评论已发送')
    await fetchTask()
  } catch {
    // handled by interceptor
  }
}

onMounted(fetchTask)
</script>

<template>
  <div class="page-container" v-loading="loading">
    <template v-if="task">
      <!-- Overdue alert -->
      <el-alert
        v-if="task.is_overdue"
        title="此任务已逾期，请尽快处理！"
        type="error"
        show-icon
        :closable="false"
        style="margin-bottom: 16px;"
      />

      <div class="page-container__header">
        <div>
          <h2>{{ task.title }}</h2>
          <span style="color: #909399; font-size: 13px;">{{ task.task_no }}</span>
          <el-tag size="small" style="margin-left: 8px;" :type="isAssignedMode ? 'info' : 'warning'">
            {{ task.task_mode_display }}
          </el-tag>
        </div>
        <div style="display: flex; gap: 8px;">
          <el-button v-if="canClaim" type="primary" :loading="claimLoading" @click="handleClaim">
            领取任务
          </el-button>
          <el-button v-if="canCompleteAsChiefLead" type="success" :loading="completeLoading" @click="handleTransition('COMPLETED')">
            完成任务（全团队发分）
          </el-button>
        </div>
      </div>

      <el-row :gutter="20">
        <el-col :span="16">
          <!-- Task Details -->
          <el-card shadow="hover" style="margin-bottom: 20px;">
            <template #header><span>任务详情</span></template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="状态">
                <StatusTag :status="task.status" />
              </el-descriptions-item>
              <el-descriptions-item label="优先级">
                <PriorityTag :priority="task.priority" />
              </el-descriptions-item>
              <el-descriptions-item label="任务模式">
                <el-tag size="small" :type="isAssignedMode ? 'info' : 'warning'">
                  {{ task.task_mode_display }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="负责人">{{ task.assignee_name || '未分配' }}</el-descriptions-item>
              <el-descriptions-item label="创建人">{{ task.creator_name }}</el-descriptions-item>
              <el-descriptions-item label="进度">
                <el-progress :percentage="task.progress" :stroke-width="8" />
              </el-descriptions-item>
              <el-descriptions-item label="截止日期">
                <span :style="{ color: task.is_overdue ? '#f56c6c' : '' }">
                  {{ task.deadline ? formatDateTime(task.deadline) : '-' }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="奖励积分">
                <el-tag v-if="task.reward_points" type="warning" size="small">
                  {{ task.reward_points }} 积分
                </el-tag>
                <span v-else style="color:#909399;">无</span>
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">
                {{ formatDateTime(task.created_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="描述" :span="2">{{ task.description || '暂无' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- ===== 进度更新 ===== -->
          <el-card v-if="canUpdateProgress" shadow="hover" style="margin-bottom: 20px;">
            <template #header><span>任务进度</span></template>
            <div class="progress-section">
              <el-slider
                v-model="progressValue"
                :min="0"
                :max="100"
                :step="5"
                show-stops
                @change="handleProgressChange"
              />
              <div class="progress-label">{{ progressValue }}%</div>
            </div>
          </el-card>

          <!-- ===== 状态转换区域 ===== -->
          <el-card shadow="hover" style="margin-bottom: 20px;">
            <template #header><span>状态操作</span></template>
            <div class="status-display">
              <div class="status-current">
                <span class="status-current__label">当前状态</span>
                <div
                  class="status-current__badge"
                  :style="{ backgroundColor: getStatusColor(task.status) + '20', color: getStatusColor(task.status), borderColor: getStatusColor(task.status) }"
                >
                  {{ getStatusLabel(task.status) }}
                </div>
              </div>
              <div v-if="transitions.length && canTransition(task)" class="status-transitions">
                <span class="status-transitions__label">可用操作</span>
                <div class="status-transitions__buttons">
                  <el-button
                    v-for="t in transitions"
                    :key="t.value"
                    :type="(transitionTypeMap[t.value] as any) || 'default'"
                    size="large"
                    class="transition-btn"
                    @click="openTransitionDialog(t.value)"
                  >
                    <el-icon style="margin-right: 6px;">
                      <component :is="transitionIconMap[t.value] || CircleCheck" />
                    </el-icon>
                    {{ t.label }}
                  </el-button>
                </div>
              </div>
              <div v-else-if="!transitions.length" class="status-transitions">
                <span class="status-transitions__label" style="color: #909399;">当前状态无可用操作</span>
              </div>
            </div>
          </el-card>

          <!-- ===== 派发模式 — 参与者卡片 ===== -->
          <el-card v-if="isAssignedMode && task.participants?.length" shadow="hover" style="margin-bottom: 20px;">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>团队参与者 ({{ task.participants.length }}人)</span>
              </div>
            </template>
            <el-table :data="task.participants" stripe size="small">
              <el-table-column prop="user_name" label="姓名" width="120" />
              <el-table-column prop="role_display" label="角色" width="120">
                <template #default="{ row }">
                  <el-tag
                    :type="row.role === 'CHIEF_LEAD' ? 'danger' : row.role === 'GROUP_LEAD' ? 'warning' : 'info'"
                    size="small"
                  >
                    {{ row.role_display }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="points" label="积分" width="80" align="center" />
              <el-table-column prop="status_display" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag
                    :type="row.status === 'COMPLETED' ? 'success' : row.status === 'ACCEPTED' ? 'primary' : 'info'"
                    size="small"
                  >
                    {{ row.status_display }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <!-- ===== 参与者管理 ===== -->
          <el-card v-if="isAssignedMode && canManageParticipants" shadow="hover" style="margin-bottom: 20px;">
            <template #header>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>参与者管理</span>
                <el-button type="primary" size="small" @click="openAddParticipant">
                  <el-icon style="margin-right: 4px;"><Plus /></el-icon>
                  添加参与者
                </el-button>
              </div>
            </template>
            <el-table :data="task.participants" stripe size="small">
              <el-table-column prop="user_name" label="姓名" width="100" />
              <el-table-column prop="role_display" label="角色" width="100">
                <template #default="{ row }">
                  <el-tag
                    :type="row.role === 'CHIEF_LEAD' ? 'danger' : row.role === 'GROUP_LEAD' ? 'warning' : 'info'"
                    size="small"
                  >
                    {{ row.role_display }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="points" label="积分" width="80" align="center" />
              <el-table-column prop="status_display" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag
                    :type="row.status === 'COMPLETED' ? 'success' : 'info'"
                    size="small"
                  >
                    {{ row.status_display }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="140" align="center">
                <template #default="{ row }">
                  <el-button size="small" text type="primary" @click="openEditParticipant(row)">
                    <el-icon><Edit /></el-icon>
                    编辑
                  </el-button>
                  <el-button size="small" text type="danger" @click="removeParticipant(row)">
                    <el-icon><Delete /></el-icon>
                    移除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="!task.participants?.length" description="暂无参与者" :image-size="40" />
          </el-card>

          <!-- ===== 揭榜模式 — 领取人卡片 ===== -->
          <el-card v-if="isClaimMode && task.participants?.length" shadow="hover" style="margin-bottom: 20px;">
            <template #header>
              <span>
                已领取 ({{ task.current_claimers }}{{ task.max_claimers ? `/${task.max_claimers}` : '' }}人)
              </span>
            </template>
            <el-table :data="task.participants" stripe size="small">
              <el-table-column prop="user_name" label="姓名" width="120" />
              <el-table-column prop="status_display" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag
                    :type="row.status === 'COMPLETED' ? 'success' : 'primary'"
                    size="small"
                  >
                    {{ row.status_display }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="points" label="积分" width="80" align="center" />
              <el-table-column label="操作" width="120" align="center">
                <template #default="{ row }">
                  <el-button
                    v-if="row.status !== 'COMPLETED' && (authStore.user?.is_superuser || authStore.user?.role === 'LEADER' || authStore.user?.role === 'ADMIN' || task.creator === authStore.user?.id)"
                    size="small"
                    type="success"
                    @click="handleCompleteParticipant(row.id)"
                    :loading="completeLoading"
                  >
                    确认完成
                  </el-button>
                  <span v-else-if="row.status === 'COMPLETED'" style="color: #67C23A; font-size: 12px;">已完成</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <!-- Comments -->
          <el-card shadow="hover" style="margin-bottom: 20px;">
            <template #header><span>评论 ({{ comments.length }})</span></template>
            <div v-for="c in comments" :key="c.id" class="comment-item">
              <div style="display: flex; justify-content: space-between;">
                <strong>{{ c.author_name }}</strong>
                <span style="color: #909399; font-size: 12px;">{{ formatDateTime(c.created_at) }}</span>
              </div>
              <p style="margin-top: 4px; color: #606266;">{{ c.content }}</p>
            </div>
            <el-empty v-if="!comments.length" description="暂无评论" :image-size="40" />
            <el-input v-model="newComment" type="textarea" :rows="3" placeholder="添加评论..." style="margin-top: 12px;" />
            <el-button type="primary" style="margin-top: 8px;" @click="addComment" :disabled="!newComment.trim()">
              发送评论
            </el-button>
          </el-card>

          <!-- ===== Enhanced File Attachments ===== -->
          <el-card shadow="hover">
            <template #header>
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span>附件 ({{ files.length }})</span>
                <el-button
                  v-if="hasSelectedFiles"
                  type="danger"
                  size="small"
                  :loading="batchDeleteLoading"
                  @click="handleBatchDelete"
                >
                  删除选中 ({{ selectedFileIds.length }})
                </el-button>
              </div>
            </template>
            <!-- Drag-and-drop zone -->
            <div
              class="upload-drop-zone"
              :class="{ 'is-dragging': isDragging }"
              @dragover="handleDragOver"
              @dragleave="handleDragLeave"
              @drop="handleDrop"
            >
              <el-upload
                :http-request="handleUpload"
                :show-file-list="false"
                multiple
                :on-progress="handleUploadProgress"
                class="upload-area"
              >
                <div class="upload-content">
                  <el-icon class="upload-icon"><UploadFilled /></el-icon>
                  <div class="upload-text">拖拽文件到此处，或 <em>点击上传</em></div>
                </div>
              </el-upload>
            </div>

            <!-- Upload progress indicators -->
            <div v-if="Object.keys(fileUploadProgress).length" class="upload-progress-list">
              <div v-for="(progress, name) in fileUploadProgress" :key="name" class="upload-progress-item">
                <span class="upload-progress-name">{{ name }}</span>
                <el-progress :percentage="progress" :stroke-width="6" style="flex: 1; margin: 0 12px;" />
              </div>
            </div>

            <!-- File list -->
            <div v-if="files.length" class="file-list">
              <div class="file-select-all">
                <el-checkbox
                  v-model="selectedAllFiles"
                  :indeterminate="selectedFileIds.length > 0 && selectedFileIds.length < files.length"
                >
                  全选
                </el-checkbox>
              </div>
              <div v-for="f in files" :key="f.id" class="file-item" :class="{ 'is-selected': selectedFileIds.includes(f.id) }">
                <el-checkbox
                  :model-value="selectedFileIds.includes(f.id)"
                  @change="toggleFileSelection(f.id)"
                  class="file-checkbox"
                />
                <div class="file-item__icon" :style="{ color: getFileTypeColor(f.filename || f.original_name) }">
                  {{ getFileTypeIcon(f.filename || f.original_name) }}
                </div>
                <div class="file-item__info">
                  <span class="file-item__name">{{ f.filename || f.original_name }}</span>
                  <div class="file-item__meta">
                    <span v-if="f.file_size" class="file-item__size">{{ formatFileSize(f.file_size) }}</span>
                    <span v-if="f.created_at" class="file-item__time">{{ formatDateTime(f.created_at) }}</span>
                  </div>
                </div>
                <div class="file-item__actions">
                  <el-button size="small" text type="primary" @click="handleDownloadFile(f)">下载</el-button>
                  <el-button size="small" text type="danger" @click="handleDeleteFile(f)">删除</el-button>
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无附件" :image-size="40" />
          </el-card>
        </el-col>

        <!-- History -->
        <el-col :span="8">
          <el-card shadow="hover">
            <template #header><span>操作历史</span></template>
            <el-timeline>
              <el-timeline-item
                v-for="h in history"
                :key="h.id"
                :timestamp="formatDateTime(h.created_at)"
                placement="top"
              >
                <div>
                  <strong>{{ h.actor_name }}</strong>
                  <span style="margin-left: 4px;">{{ h.action_display }}</span>
                </div>
                <div v-if="h.note" style="color: #909399; font-size: 12px; margin-top: 2px;">{{ h.note }}</div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-if="!history.length" description="暂无记录" :image-size="40" />
          </el-card>
        </el-col>
      </el-row>

      <!-- ===== 参与者管理对话框 ===== -->
      <el-dialog
        v-model="participantDialogVisible"
        :title="participantDialogMode === 'add' ? '添加参与者' : '编辑参与者'"
        width="480px"
        destroy-on-close
      >
        <el-form :model="participantForm" label-width="80px">
          <el-form-item v-if="participantDialogMode === 'add'" label="用户" required>
            <el-select
              v-model="participantForm.user"
              filterable
              placeholder="搜索并选择用户"
              style="width: 100%;"
            >
              <el-option
                v-for="u in users"
                :key="u.id"
                :label="u.username || u.name"
                :value="u.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item v-else label="用户">
            <span>{{ editingParticipant?.user_name }}</span>
          </el-form-item>
          <el-form-item label="角色" required>
            <el-select v-model="participantForm.role" style="width: 100%;">
              <el-option label="总牵头人" value="CHIEF_LEAD" />
              <el-option label="小组长" value="GROUP_LEAD" />
              <el-option label="参与者" value="PARTICIPANT" />
            </el-select>
          </el-form-item>
          <el-form-item label="积分">
            <el-input-number v-model="participantForm.points" :min="0" :max="9999" style="width: 100%;" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="participantDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="participantFormLoading" @click="submitParticipant">
            {{ participantDialogMode === 'add' ? '添加' : '保存' }}
          </el-button>
        </template>
      </el-dialog>

      <!-- ===== 状态转换确认对话框 ===== -->
      <el-dialog
        v-model="transitionDialogVisible"
        title="状态变更确认"
        width="480px"
        destroy-on-close
      >
        <div class="transition-dialog-content">
          <div class="transition-flow">
            <div class="transition-flow__item">
              <div
                class="transition-flow__badge"
                :style="{ backgroundColor: getStatusColor(task.status) + '20', color: getStatusColor(task.status), borderColor: getStatusColor(task.status) }"
              >
                {{ getStatusLabel(task.status) }}
              </div>
              <span class="transition-flow__label">当前状态</span>
            </div>
            <div class="transition-flow__arrow">→</div>
            <div class="transition-flow__item">
              <div
                class="transition-flow__badge"
                :style="{ backgroundColor: getStatusColor(transitionTarget) + '20', color: getStatusColor(transitionTarget), borderColor: getStatusColor(transitionTarget) }"
              >
                {{ getStatusLabel(transitionTarget) }}
              </div>
              <span class="transition-flow__label">目标状态</span>
            </div>
          </div>
          <el-form style="margin-top: 20px;">
            <el-form-item label="变更备注">
              <el-input
                v-model="transitionNote"
                type="textarea"
                :rows="3"
                placeholder="请输入变更原因或备注（可选）"
              />
            </el-form-item>
          </el-form>
        </div>
        <template #footer>
          <el-button @click="transitionDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmTransition">确认变更</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<style scoped lang="scss">
.comment-item {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;

  &:last-child {
    border-bottom: none;
  }
}

/* Progress section */
.progress-section {
  display: flex;
  align-items: center;
  gap: 16px;

  .el-slider {
    flex: 1;
  }

  .progress-label {
    min-width: 48px;
    text-align: right;
    font-size: 16px;
    font-weight: 600;
    color: #409EFF;
  }
}

/* Status display */
.status-display {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.status-current {
  display: flex;
  align-items: center;
  gap: 12px;

  &__label {
    font-size: 13px;
    color: #909399;
    min-width: 60px;
  }

  &__badge {
    padding: 8px 20px;
    border-radius: 8px;
    border: 2px solid;
    font-size: 16px;
    font-weight: 600;
  }
}

.status-transitions {
  &__label {
    display: block;
    font-size: 13px;
    color: #909399;
    margin-bottom: 12px;
  }

  &__buttons {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
}

.transition-btn {
  min-width: 120px;
  height: 48px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
}

/* Upload drop zone */
.upload-drop-zone {
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  transition: all 0.3s;
  cursor: pointer;
  background: #fafafa;

  &:hover {
    border-color: #409EFF;
    background: #f0f7ff;
  }

  &.is-dragging {
    border-color: #409EFF;
    background: #ecf5ff;
    transform: scale(1.01);
  }
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  font-size: 36px;
  color: #c0c4cc;
}

.upload-text {
  font-size: 14px;
  color: #606266;

  em {
    color: #409EFF;
    font-style: normal;
    cursor: pointer;
  }
}

.upload-area {
  width: 100%;
}

/* Upload progress */
.upload-progress-list {
  margin-top: 12px;
}

.upload-progress-item {
  display: flex;
  align-items: center;
  padding: 8px 0;
}

.upload-progress-name {
  font-size: 13px;
  color: #606266;
  min-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* File list */
.file-list {
  margin-top: 12px;
}

.file-select-all {
  padding: 4px 0 8px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 6px;
  background: #fafafa;
  margin-bottom: 8px;
  transition: background 0.2s;

  &:hover {
    background: #f0f7ff;
  }

  &.is-selected {
    background: #ecf5ff;
  }

  .file-checkbox {
    margin-right: 8px;
  }

  &__icon {
    font-size: 22px;
    margin-right: 10px;
    flex-shrink: 0;
  }

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__name {
    font-size: 13px;
    color: #303133;
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__meta {
    display: flex;
    gap: 12px;
    margin-top: 2px;
  }

  &__size {
    font-size: 12px;
    color: #909399;
  }

  &__time {
    font-size: 12px;
    color: #c0c4cc;
  }

  &__actions {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }
}

/* Transition dialog */
.transition-dialog-content {
  padding: 0 8px;
}

.transition-flow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;

  &__item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }

  &__badge {
    padding: 10px 24px;
    border-radius: 8px;
    border: 2px solid;
    font-size: 15px;
    font-weight: 600;
  }

  &__label {
    font-size: 12px;
    color: #909399;
  }

  &__arrow {
    font-size: 24px;
    color: #909399;
    font-weight: bold;
  }
}
</style>
