<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

const loading = ref(true)
const rules = ref<any[]>([])
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const submitting = ref(false)
const editingId = ref<number | null>(null)

const form = reactive({
  action: '',
  mode: '',
  base_points: 1,
  priority_multiplier: 1,
  is_active: true,
})

const formRules: FormRules = {
  action: [{ required: true, message: '请输入动作名称', trigger: 'blur' }],
  mode: [{ required: true, message: '请选择模式', trigger: 'change' }],
  base_points: [{ required: true, message: '请输入基础积分', trigger: 'blur' }],
}

const fetchRules = async () => {
  loading.value = true
  try {
    const { data } = await api.get('/points/rules/')
    rules.value = data.results || data || []
  } catch {} finally {
    loading.value = false
  }
}

const openEdit = (rule: any) => {
  editingId.value = rule.id
  form.action = rule.action
  form.mode = rule.mode
  form.base_points = rule.base_points
  form.priority_multiplier = rule.priority_multiplier
  form.is_active = rule.is_active
  dialogVisible.value = true
}

const handleSave = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editingId.value) {
      await api.patch(`/points/rules/${editingId.value}/`, {
        action: form.action,
        mode: form.mode,
        base_points: form.base_points,
        priority_multiplier: form.priority_multiplier,
        is_active: form.is_active,
      })
      ElMessage.success('规则已更新')
    } else {
      await api.post('/points/rules/', {
        action: form.action,
        mode: form.mode,
        base_points: form.base_points,
        priority_multiplier: form.priority_multiplier,
        is_active: form.is_active,
      })
      ElMessage.success('规则已创建')
    }
    dialogVisible.value = false
    fetchRules()
  } catch {} finally {
    submitting.value = false
  }
}

const openCreate = () => {
  editingId.value = null
  form.action = ''
  form.mode = ''
  form.base_points = 1
  form.priority_multiplier = 1
  form.is_active = true
  dialogVisible.value = true
}

onMounted(fetchRules)
</script>

<template>
  <div class="page-container">
    <div class="page-container__header">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <h2>积分配置</h2>
        <el-button type="primary" @click="openCreate">添加规则</el-button>
      </div>
    </div>

    <el-table :data="rules" v-loading="loading" stripe>
      <el-table-column prop="action" label="动作" min-width="150" />
      <el-table-column label="模式" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ row.mode }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="base_points" label="基础积分" width="100" align="center" />
      <el-table-column label="优先级倍率" width="100" align="center">
        <template #default="{ row }">{{ row.priority_multiplier }}x</template>
      </el-table-column>
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" align="center">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Dialog -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑规则' : '添加规则'" width="480px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="动作" prop="action">
          <el-input v-model="form.action" placeholder="如：complete_task" />
        </el-form-item>
        <el-form-item label="模式" prop="mode">
          <el-select v-model="form.mode" placeholder="选择模式" style="width: 100%;">
            <el-option label="FIXED" value="FIXED" />
            <el-option label="MULTIPLIER" value="MULTIPLIER" />
          </el-select>
        </el-form-item>
        <el-form-item label="基础积分" prop="base_points">
          <el-input-number v-model="form.base_points" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="优先级倍率">
          <el-input-number v-model="form.priority_multiplier" :min="0" :max="10" :step="0.1" :precision="1" />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSave">
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
