<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

const route = useRoute()
const activeTab = ref((route.query.tab as string) || 'profile')
const loading = ref(true)
const profile = ref<any>({})
const editing = ref(false)
const phoneForm = reactive({ phone: '' })
const phoneFormRef = ref<FormInstance>()

const passwordFormRef = ref<FormInstance>()
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})
const submitting = ref(false)

const phoneRules: FormRules = {
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号', trigger: 'blur' },
  ],
}

const passwordRules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不少于6位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: any) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

const fetchProfile = async () => {
  loading.value = true
  try {
    const { data } = await api.get('/auth/me/')
    profile.value = data
    phoneForm.phone = data.phone || ''
  } catch {} finally {
    loading.value = false
  }
}

const startEdit = () => {
  phoneForm.phone = profile.value.phone || ''
  editing.value = true
}

const savePhone = async () => {
  const valid = await phoneFormRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    const { data } = await api.patch('/auth/me/', { phone: phoneForm.phone })
    profile.value = data
    editing.value = false
    ElMessage.success('手机号已更新')
  } catch {}
}

const cancelEdit = () => {
  editing.value = false
  phoneForm.phone = profile.value.phone || ''
}

const changePassword = async () => {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await api.post('/auth/password/', {
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success('密码修改成功')
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    passwordFormRef.value?.resetFields()
  } catch {} finally {
    submitting.value = false
  }
}

onMounted(fetchProfile)
</script>

<template>
  <div class="page-container" v-loading="loading">
    <div class="page-container__header">
      <h2>个人中心</h2>
    </div>

    <el-card shadow="hover">
      <el-tabs v-model="activeTab">
        <!-- Profile Tab -->
        <el-tab-pane label="个人资料" name="profile">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="用户名">{{ profile.username }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ profile.email }}</el-descriptions-item>
            <el-descriptions-item label="角色">
              <el-tag :type="profile.role === 'ADMIN' ? 'danger' : profile.role === 'LEADER' ? 'warning' : 'info'" size="small">
                {{ profile.role }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="团队">{{ profile.team_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="手机号">
              <template v-if="!editing">
                {{ profile.phone || '-' }}
                <el-button size="small" type="primary" link style="margin-left: 8px;" @click="startEdit">编辑</el-button>
              </template>
              <template v-else>
                <el-form ref="phoneFormRef" :model="phoneForm" :rules="phoneRules" inline>
                  <el-form-item prop="phone" style="margin-bottom: 0;">
                    <el-input v-model="phoneForm.phone" placeholder="请输入手机号" style="width: 200px;" />
                  </el-form-item>
                  <el-form-item style="margin-bottom: 0;">
                    <el-button type="primary" size="small" @click="savePhone">保存</el-button>
                    <el-button size="small" @click="cancelEdit">取消</el-button>
                  </el-form-item>
                </el-form>
              </template>
            </el-descriptions-item>
            <el-descriptions-item label="注册时间">{{ profile.date_joined }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <!-- Password Tab -->
        <el-tab-pane label="修改密码" name="password">
          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-width="100px"
            style="max-width: 420px; margin-top: 20px;"
          >
            <el-form-item label="原密码" prop="old_password">
              <el-input v-model="passwordForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="passwordForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm_password">
              <el-input v-model="passwordForm.confirm_password" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="submitting" @click="changePassword">
                修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.page-container {
  padding: 0;
}
</style>
