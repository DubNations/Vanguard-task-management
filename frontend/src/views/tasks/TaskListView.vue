<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useTaskStore } from '@/stores/task'
import { useAuthStore } from '@/stores/auth'
import { usePermission } from '@/composables/usePermission'
import StatusTag from '@/components/StatusTag.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import { formatDate } from '@/utils/format'
import api from '@/api'

const router = useRouter()
const taskStore = useTaskStore()
const authStore = useAuthStore()
const { isLeader } = usePermission()

const activeTab = ref('list')
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = reactive({ status: '', priority: '', search: '', task_mode: '' })

// 新建任务对话框
const createDialogVisible = ref(false)
const createLoading = ref(false)
const createForm = reactive({
  title: '',
  description: '',
  priority: 'MEDIUM',
  deadline: '',
  task_mode: 'ASSIGNED',
  reward_points: 0,
  max_claimers: 3,
  // 派发模式
  chief_lead_points: 20,
  group_lead_points: 10,
  participant_points: 5,
  chief_leads: [] as string[],
  group_leads: [] as string[],
  participants: [] as string[],
})
const userOptions = ref<any[]>([])

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'PENDING', label: '待领取' },
  { value: 'IN_PROGRESS', label: '进行中' },
  { value: 'IN_REVIEW', label: '待审核' },
  { value: 'COMPLETED', label: '已完成' },
  { value: 'REJECTED', label: '已退回' },
]

const priorityOptions = [
  { value: 'LOW', label: '低' },
  { value: 'MEDIUM', label: '中' },
  { value: 'HIGH', label: '高' },
  { value: 'URGENT', label: '紧急' },
]

const taskModeOptions = [
  { value: 'ASSIGNED', label: '派发' },
  { value: 'FREE_CLAIM', label: '自由揭榜' },
  { value: 'FIXED_CLAIM', label: '固定揭榜' },
]

const tasks = computed(() => taskStore.tasks)

const totalPointsPreview = computed(() => {
  if (createForm.task_mode !== 'ASSIGNED') return createForm.reward_points
  return (
    createForm.chief_leads.length * createForm.chief_lead_points +
    createForm.group_leads.length * createForm.group_lead_points +
    createForm.participants.length * createForm.participant_points
  )
})

const fetchTasks = async () => {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filters.status) params.status = filters.status
    if (filters.priority) params.priority = filters.priority
    if (filters.search) params.search = filters.search
    if (filters.task_mode) params.task_mode = filters.task_mode
    await taskStore.fetchTasks(params)
    total.value = taskStore.totalCount
  } finally {
    loading.value = false
  }
}

const handlePageChange = (p: number) => {
  page.value = p
  fetchTasks()
}

const openCreateDialog = async () => {
  createDialogVisible.value = true
  try {
    const { data } = await api.get('/auth/users/')
    userOptions.value = data.results || data || []
  } catch {
    userOptions.value = []
  }
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
      task_mode: createForm.task_mode,
    }
    if (createForm.deadline) payload.deadline = createForm.deadline

    if (createForm.task_mode === 'ASSIGNED') {
      const participants: any[] = []
      for (const uid of createForm.chief_leads) {
        participants.push({ user_id: uid, role: 'CHIEF_LEAD', points: createForm.chief_lead_points })
      }
      for (const uid of createForm.group_leads) {
        participants.push({ user_id: uid, role: 'GROUP_LEAD', points: createForm.group_lead_points })
      }
      for (const uid of createForm.participants) {
        participants.push({ user_id: uid, role: 'PARTICIPANT', points: createForm.participant_points })
      }
      payload.participants = participants
    } else {
      payload.reward_points = createForm.reward_points
      if (createForm.task_mode === 'FIXED_CLAIM') {
        payload.max_claimers = createForm.max_claimers
      }
    }

    await taskStore.createTask(payload)
    ElMessage.success('任务创建成功')
    createDialogVisible.value = false
    resetCreateForm()
    fetchTasks()
  } catch {
    // handled by interceptor
  } finally {
    createLoading.value = false
  }
}

const resetCreateForm = () => {
  createForm.title = ''
  createForm.description = ''
  createForm.priority = 'MEDIUM'
  createForm.deadline = ''
  createForm.task_mode = 'ASSIGNED'
  createForm.reward_points = 0
  createForm.max_claimers = 3
  createForm.chief_lead_points = 20
  createForm.group_lead_points = 10
  createForm.participant_points = 5
  createForm.chief_leads = []
  createForm.group_leads = []
  createForm.participants = []
}

const goToKanban = () => {
  router.push('/tasks/kanban')
}

onMounted(fetchTasks)
</script>

<template>
  <div class="page-container">
    <div class="page-container__header">
      <h2>任务管理</h2>
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-select v-model="filters.status" placeholder="状态筛选" style="width: 130px" @change="fetchTasks">
          <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-select v-model="filters.priority" placeholder="优先级" style="width: 120px" @change="fetchTasks">
          <el-option v-for="o in priorityOptions" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-select v-model="filters.task_mode" placeholder="任务模式" style="width: 130px" @change="fetchTasks">
          <el-option label="全部模式" value="" />
          <el-option v-for="o in taskModeOptions" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-input v-model="filters.search" placeholder="搜索任务..." style="width: 200px" clearable @clear="fetchTasks" @keyup.enter="fetchTasks" />
        <el-button type="primary" @click="fetchTasks">搜索</el-button>
        <el-button v-if="isLeader" type="success" @click="openCreateDialog">
          <el-icon style="margin-right:4px;"><Plus /></el-icon>
          新建任务
        </el-button>
      </div>
    </div>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" style="margin-bottom: 16px;">
      <el-tab-pane label="列表" name="list" />
      <el-tab-pane label="看板" name="kanban" />
    </el-tabs>

    <!-- 列表视图 -->
    <template v-if="activeTab === 'list'">
      <el-table :data="tasks" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="task_no" label="编号" width="160" />
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="router.push(`/tasks/${row.id}`)">{{ row.title }}</el-link>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="90">
          <template #default="{ row }">
            <PriorityTag :priority="row.priority" />
          </template>
        </el-table-column>
        <el-table-column label="模式" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.task_mode === 'ASSIGNED' ? 'info' : 'warning'">
              {{ row.task_mode_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="110">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :stroke-width="6" :show-text="true" />
          </template>
        </el-table-column>
        <el-table-column prop="assignee_name" label="负责人" width="100" />
        <el-table-column label="截止日期" width="120">
          <template #default="{ row }">
            <span :style="{ color: row.is_overdue ? '#f56c6c' : '' }">
              {{ row.deadline ? formatDate(row.deadline) : '-' }}
            </span>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        style="margin-top: 16px; justify-content: flex-end;"
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="handlePageChange"
      />
    </template>

    <!-- 看板视图 -->
    <template v-if="activeTab === 'kanban'">
      <el-empty description="点击前往看板视图">
        <el-button type="primary" @click="goToKanban">打开看板</el-button>
      </el-empty>
    </template>

    <!-- 新建任务对话框 -->
    <el-dialog v-model="createDialogVisible" title="新建任务" width="640px" destroy-on-close>
      <el-form :model="createForm" label-width="100px">
        <!-- 通用字段 -->
        <el-form-item label="标题" required>
          <el-input v-model="createForm.title" placeholder="请输入任务标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="请输入任务描述" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="createForm.priority" style="width: 100%">
            <el-option v-for="o in priorityOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker
            v-model="createForm.deadline"
            type="datetime"
            placeholder="选择截止日期"
            style="width: 100%"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>

        <!-- 任务模式选择 -->
        <el-form-item label="任务模式">
          <el-radio-group v-model="createForm.task_mode">
            <el-radio v-for="o in taskModeOptions" :key="o.value" :value="o.value">{{ o.label }}</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- ===== 派发模式专属 ===== -->
        <template v-if="createForm.task_mode === 'ASSIGNED'">
          <el-divider content-position="left">派发模式设置</el-divider>

          <el-form-item label="积分设置">
            <el-space direction="vertical" :size="8" style="width: 100%;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="width:80px; font-size:13px;">总牵头人:</span>
                <el-input-number v-model="createForm.chief_lead_points" :min="1" :max="999" size="small" />
                <span style="font-size:12px; color:#909399;">积分/人</span>
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="width:80px; font-size:13px;">小组牵头:</span>
                <el-input-number v-model="createForm.group_lead_points" :min="0" :max="999" size="small" />
                <span style="font-size:12px; color:#909399;">积分/人</span>
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="width:80px; font-size:13px;">参与:</span>
                <el-input-number v-model="createForm.participant_points" :min="0" :max="999" size="small" />
                <span style="font-size:12px; color:#909399;">积分/人</span>
              </div>
            </el-space>
          </el-form-item>

          <el-form-item label="总牵头人" required>
            <el-select v-model="createForm.chief_leads" multiple placeholder="选择总牵头人（至少1人）" style="width: 100%">
              <el-option
                v-for="u in userOptions"
                :key="u.id"
                :label="`${u.username} (${u.team_name || '-'})`"
                :value="u.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="小组牵头">
            <el-select v-model="createForm.group_leads" multiple placeholder="选择小组牵头（可多人）" style="width: 100%">
              <el-option
                v-for="u in userOptions"
                :key="u.id"
                :label="`${u.username} (${u.team_name || '-'})`"
                :value="u.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="参与人员">
            <el-select v-model="createForm.participants" multiple placeholder="选择参与人员（可多人）" style="width: 100%">
              <el-option
                v-for="u in userOptions"
                :key="u.id"
                :label="`${u.username} (${u.team_name || '-'})`"
                :value="u.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="总积分">
            <el-tag type="warning" size="large">{{ totalPointsPreview }} 积分</el-tag>
          </el-form-item>
        </template>

        <!-- ===== 揭榜模式专属 ===== -->
        <template v-else>
          <el-divider content-position="left">揭榜模式设置</el-divider>

          <el-form-item label="奖励积分" required>
            <el-input-number v-model="createForm.reward_points" :min="1" :max="9999" />
            <span style="margin-left: 8px; font-size: 12px; color: #909399;">完成可获得的固定积分</span>
          </el-form-item>

          <template v-if="createForm.task_mode === 'FIXED_CLAIM'">
            <el-form-item label="名额数量" required>
              <el-input-number v-model="createForm.max_claimers" :min="1" :max="100" />
              <span style="margin-left: 8px; font-size: 12px; color: #909399;">额满后停止领取</span>
            </el-form-item>
          </template>

          <template v-if="createForm.task_mode === 'FREE_CLAIM'">
            <el-alert title="发布后所有成员可见并可领取，不限人数" type="info" show-icon :closable="false" />
          </template>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreateTask">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>
