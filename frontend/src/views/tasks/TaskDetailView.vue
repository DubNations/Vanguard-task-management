<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import api from '@/api'
import { fileApi } from '@/api/modules'
import { useAuthStore } from '@/stores/auth'
import { usePermission } from '@/composables/usePermission'
import { useTaskStatus } from '@/composables/useTaskStatus'
import StatusTag from '@/components/StatusTag.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import { formatDateTime, formatDate, formatFileSize } from '@/utils/format'
import type { UploadFile } from 'element-plus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { canTransition } = usePermission()
const { getStatusLabel, getAvailableTransitions } = useTaskStatus()

const task = ref<any>(null)
const history = ref<any[]>([])
const comments = ref<any[]>([])
const files = ref<any[]>([])
const loading = ref(true)
const newComment = ref('')
const claimLoading = ref(false)
const completeLoading = ref(false)

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
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
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

const handleTransition = async (targetStatus: string) => {
  const label = getStatusLabel(targetStatus)
  try {
    await ElMessageBox.confirm(
      `确定将任务状态变更为「${label}」？`,
      '状态变更确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await api.post(`/tasks/${route.params.id}/transition/`, { status: targetStatus })
    ElMessage.success(`状态已变更为「${label}」`)
    await fetchTask()
  } catch {
    // cancelled or error
  }
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

const handleUpload = async (options: any) => {
  try {
    await fileApi.upload(route.params.id as string, options.file)
    ElMessage.success('文件上传成功')
    const filesRes = await fileApi.list(route.params.id as string)
    files.value = filesRes.data.results || filesRes.data || []
    options.onSuccess()
  } catch (err) {
    options.onError(err)
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
          <!-- 揭榜领取按钮 -->
          <el-button v-if="canClaim" type="primary" :loading="claimLoading" @click="handleClaim">
            领取任务
          </el-button>
          <!-- 派发模式总牵头人完成按钮 -->
          <el-button v-if="canCompleteAsChiefLead" type="success" :loading="completeLoading" @click="handleTransition('COMPLETED')">
            完成任务（全团队发分）
          </el-button>
          <!-- 普通状态转换按钮 -->
          <template v-if="canTransition(task) && !canCompleteAsChiefLead">
            <el-button
              v-for="t in transitions"
              :key="t.value"
              :type="(t.value === 'COMPLETED' ? 'success' : t.value === 'CANCELLED' || t.value === 'REJECTED' ? 'danger' : 'primary')"
              @click="handleTransition(t.value)"
            >
              {{ t.label }}
            </el-button>
          </template>
        </div>
      </div>

      <el-row :gutter="20">
        <el-col :span="16">
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

          <!-- ===== 派发模式 — 参与者卡片 ===== -->
          <el-card v-if="isAssignedMode && task.participants?.length" shadow="hover" style="margin-bottom: 20px;">
            <template #header>
              <span>团队参与者 ({{ task.participants.length }}人)</span>
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

          <!-- File Attachments -->
          <el-card shadow="hover">
            <template #header>
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span>附件 ({{ files.length }})</span>
              </div>
            </template>
            <el-upload
              :http-request="handleUpload"
              :show-file-list="false"
              multiple
            >
              <el-button type="primary" plain>
                <el-icon style="margin-right:4px;"><UploadFilled /></el-icon>
                上传文件
              </el-button>
            </el-upload>
            <div v-if="files.length" class="file-list">
              <div v-for="f in files" :key="f.id" class="file-item">
                <div class="file-item__info">
                  <span class="file-item__name">{{ f.filename || f.original_name }}</span>
                  <span class="file-item__size">{{ f.file_size ? formatFileSize(f.file_size) : '' }}</span>
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

.file-list {
  margin-top: 12px;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  background: #fafafa;
  margin-bottom: 8px;
  transition: background 0.2s;

  &:hover {
    background: #f0f7ff;
  }

  &__info {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  &__name {
    font-size: 13px;
    color: #303133;
  }

  &__size {
    font-size: 12px;
    color: #909399;
  }

  &__actions {
    display: flex;
    gap: 4px;
  }
}
</style>
