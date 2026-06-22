<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, MoreFilled } from '@element-plus/icons-vue'

const loading = ref(true)
const error = ref<string | null>(null)
const users = ref<any[]>([])
const searchText = ref('')

// 角色中文映射
const roleLabels: Record<string, string> = {
  ADMIN: '管理员',
  LEADER: '组长',
  MEMBER: '成员',
}

const roleTypes: Record<string, string> = {
  ADMIN: 'danger',
  LEADER: 'warning',
  MEMBER: 'info',
}

// 搜索过滤
const filteredUsers = computed(() => {
  if (!searchText.value) return users.value
  const keyword = searchText.value.toLowerCase()
  return users.value.filter(
    (u) =>
      u.username?.toLowerCase().includes(keyword) ||
      u.email?.toLowerCase().includes(keyword) ||
      u.team_name?.toLowerCase().includes(keyword)
  )
})

// 创建用户对话框
const createDialogVisible = ref(false)
const createLoading = ref(false)
const createForm = reactive({
  username: '',
  email: '',
  password: '',
  role: 'MEMBER',
  team: '',
})
const teamOptions = ref<any[]>([])

const roleOptions = [
  { value: 'ADMIN', label: '管理员' },
  { value: 'LEADER', label: '组长' },
  { value: 'MEMBER', label: '成员' },
]

const fetchUsers = async () => {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get('/auth/users/')
    users.value = data.results || data || []
  } catch {
    error.value = '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

const toggleUser = async (user: any) => {
  const action = user.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定${action}用户 ${user.username}？`, '提示', {
      type: 'warning',
    })
    await api.post(`/auth/users/${user.id}/toggle/`)
    ElMessage.success(`已${action}`)
    fetchUsers()
  } catch {
    // cancelled or error
  }
}

const resetPassword = async (user: any) => {
  try {
    const { value: newPassword } = await ElMessageBox.prompt(
      `请输入用户 ${user.username} 的新密码（至少6位）`,
      '重置密码',
      {
        type: 'warning',
        confirmButtonText: '确认重置',
        cancelButtonText: '取消',
        inputPattern: /^.{6,}$/,
        inputErrorMessage: '密码长度不能少于6位',
        inputType: 'password',
      }
    )
    if (newPassword) {
      await api.post(`/auth/users/${user.id}/reset-password/`, { new_password: newPassword })
      ElMessage.success('密码已重置')
    }
  } catch {
    // cancelled or error
  }
}

const openCreateDialog = async () => {
  createDialogVisible.value = true
  // 加载团队列表
  try {
    const { data } = await api.get('/auth/teams/')
    teamOptions.value = data.results || data || []
  } catch {
    teamOptions.value = []
  }
}

const handleCreateUser = async () => {
  if (!createForm.username.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!createForm.email.trim()) {
    ElMessage.warning('请输入邮箱')
    return
  }
  if (!createForm.password.trim()) {
    ElMessage.warning('请输入密码')
    return
  }
  createLoading.value = true
  try {
    const payload: any = {
      username: createForm.username,
      email: createForm.email,
      password: createForm.password,
      role: createForm.role,
    }
    if (createForm.team) payload.team = createForm.team
    await api.post('/auth/users/', payload)
    ElMessage.success('用户创建成功')
    createDialogVisible.value = false
    // 重置表单
    createForm.username = ''
    createForm.email = ''
    createForm.password = ''
    createForm.role = 'MEMBER'
    createForm.team = ''
    fetchUsers()
  } catch {
    // handled by interceptor
  } finally {
    createLoading.value = false
  }
}

onMounted(fetchUsers)
</script>

<template>
  <div class="page-container">
    <el-result v-if="error" icon="error" :title="error">
      <template #extra><el-button @click="fetchUsers">重试</el-button></template>
    </el-result>
    <div class="page-container__header">
      <h2>用户管理</h2>
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-input
          v-model="searchText"
          placeholder="搜索用户名、邮箱、团队..."
          style="width: 260px"
          clearable
        />
        <el-button type="primary" @click="openCreateDialog">
          <el-icon style="margin-right:4px;"><Plus /></el-icon>
          创建用户
        </el-button>
      </div>
    </div>

    <el-table :data="filteredUsers" v-loading="loading" stripe>
      <el-table-column prop="username" label="用户名" width="150" />
      <el-table-column prop="email" label="邮箱" min-width="200" />
      <el-table-column label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="(roleTypes[row.role] as any) || 'info'" size="small">
            {{ roleLabels[row.role] || row.role }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="team_name" label="团队" width="120" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-dropdown trigger="click" @command="(cmd: string) => {
            if (cmd === 'toggle') toggleUser(row)
            else if (cmd === 'reset') resetPassword(row)
          }">
            <el-button size="small" text type="primary">
              操作 <el-icon style="margin-left:4px;"><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item :command="'toggle'">
                  {{ row.is_active ? '禁用' : '启用' }}
                </el-dropdown-item>
                <el-dropdown-item command="reset" divided>
                  重置密码
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建用户对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建用户" width="500px" destroy-on-close>
      <el-form :model="createForm" label-width="70px">
        <el-form-item label="用户名" required>
          <el-input v-model="createForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱" required>
          <el-input v-model="createForm.email" type="email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="createForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role" style="width: 100%">
            <el-option v-for="o in roleOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="团队">
          <el-select v-model="createForm.team" placeholder="选择团队" clearable style="width: 100%">
            <el-option
              v-for="t in teamOptions"
              :key="t.id"
              :label="t.name"
              :value="t.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreateUser">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>
