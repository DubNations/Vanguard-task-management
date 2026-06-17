<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

const loading = ref(true)
const error = ref<string | null>(null)
const teams = ref<any[]>([])
const dialogVisible = ref(false)
const dialogTitle = ref('创建团队')
const formRef = ref<FormInstance>()
const submitting = ref(false)
const editingId = ref<number | null>(null)

const form = reactive({
  name: '',
  leader_id: null as number | null,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入团队名称', trigger: 'blur' }],
}

const users = ref<any[]>([])

const fetchTeams = async () => {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get('/auth/teams/')
    teams.value = data.results || data || []
  } catch {
    error.value = '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

const fetchUsers = async () => {
  try {
    const { data } = await api.get('/auth/users/')
    users.value = data.results || data || []
  } catch {}
}

const openCreate = () => {
  dialogTitle.value = '创建团队'
  editingId.value = null
  form.name = ''
  form.leader_id = null
  dialogVisible.value = true
}

const openEdit = (team: any) => {
  dialogTitle.value = '编辑团队'
  editingId.value = team.id
  form.name = team.name
  form.leader_id = team.leader_id || null
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editingId.value) {
      await api.patch(`/auth/teams/${editingId.value}/`, {
        name: form.name,
        leader_id: form.leader_id,
      })
      ElMessage.success('团队已更新')
    } else {
      await api.post('/auth/teams/', {
        name: form.name,
        leader_id: form.leader_id,
      })
      ElMessage.success('团队已创建')
    }
    dialogVisible.value = false
    fetchTeams()
  } catch {} finally {
    submitting.value = false
  }
}

const handleDelete = async (team: any) => {
  await ElMessageBox.confirm(`确定删除团队「${team.name}」？`, '确认删除', { type: 'warning' })
  try {
    await api.delete(`/auth/teams/${team.id}/`)
    ElMessage.success('已删除')
    fetchTeams()
  } catch {}
}

onMounted(() => {
  fetchTeams()
  fetchUsers()
})
</script>

<template>
  <div class="page-container">
    <el-result v-if="error" icon="error" :title="error">
      <template #extra><el-button @click="fetchTeams">重试</el-button></template>
    </el-result>
    <div class="page-container__header">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <h2>团队管理</h2>
        <el-button type="primary" @click="openCreate">创建团队</el-button>
      </div>
    </div>

    <el-table :data="teams" v-loading="loading" stripe>
      <el-table-column prop="name" label="团队名称" min-width="150" />
      <el-table-column label="队长" width="120">
        <template #default="{ row }">{{ row.leader_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="member_count" label="成员数" width="80" align="center" />
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="150" align="center">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="480px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="团队名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入团队名称" />
        </el-form-item>
        <el-form-item label="队长">
          <el-select v-model="form.leader_id" placeholder="选择队长" clearable style="width: 100%;">
            <el-option
              v-for="u in users"
              :key="u.id"
              :label="u.username"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ editingId ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.page-container {
  padding: 0;
}
</style>
