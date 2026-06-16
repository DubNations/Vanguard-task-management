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
const filters = reactive({ status: '', priority: '', search: '' })

// 新建任务对话框
const createDialogVisible = ref(false)
const createLoading = ref(false)
const createForm = reactive({
  title: '',
  description: '',
  priority: 'MEDIUM',
  deadline: '',
  assignee: '',
  reward_points: 0,
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

const tasks = computed(() => taskStore.tasks)

const fetchTasks = async () => {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filters.status) params.status = filters.status
    if (filters.priority) params.priority = filters.priority
    if (filters.search) params.search = filters.search
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
  // 加载用户列表作为负责人选项
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
      reward_points: createForm.reward_points,
    }
    if (createForm.deadline) payload.deadline = createForm.deadline
    if (createForm.assignee) payload.assignee = createForm.assignee
    await taskStore.createTask(payload)
    ElMessage.success('任务创建成功')
    createDialogVisible.value = false
    // 重置表单
    createForm.title = ''
    createForm.description = ''
    createForm.priority = 'MEDIUM'
    createForm.deadline = ''
    createForm.assignee = ''
    createForm.reward_points = 0
    fetchTasks()
  } catch {
    // handled by interceptor
  } finally {
    createLoading.value = false
  }
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

    <!-- 看板视图（跳转到看板页） -->
    <template v-if="activeTab === 'kanban'">
      <el-empty description="点击前往看板视图">
        <el-button type="primary" @click="goToKanban">打开看板</el-button>
      </el-empty>
    </template>

    <!-- 新建任务对话框 -->
    <el-dialog v-model="createDialogVisible" title="新建任务" width="560px" destroy-on-close>
      <el-form :model="createForm" label-width="80px">
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
        <el-form-item label="负责人">
          <el-select v-model="createForm.assignee" placeholder="选择负责人" clearable style="width: 100%">
            <el-option
              v-for="u in userOptions"
              :key="u.id"
              :label="`${u.username} (${u.team_name || '-'})`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="奖励积分">
          <el-input-number v-model="createForm.reward_points" :min="0" :max="1000" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreateTask">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>
