<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Message, Lock, Trophy } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({
  email: '',
  password: '',
})

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' },
  ],
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    await auth.login(form.email, form.password)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-container">
      <!-- 左侧品牌展示 -->
      <div class="login-brand">
        <div class="brand-content">
          <el-icon :size="56" color="#fff"><Trophy /></el-icon>
          <h1>尖兵部队</h1>
          <p class="brand-subtitle">任务管理系统</p>
          <p class="brand-desc">高效协同 · 使命必达</p>
        </div>
      </div>

      <!-- 右侧登录表单 -->
      <div class="login-form-wrapper">
        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>请登录您的账号继续</p>
        </div>

        <el-form ref="formRef" :model="form" :rules="rules" class="login-form" @submit.prevent="handleSubmit">
          <el-form-item prop="email">
            <el-input
              v-model="form.email"
              placeholder="邮箱地址"
              :prefix-icon="Message"
              size="large"
            />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              :prefix-icon="Lock"
              size="large"
              show-password
              @keyup.enter="handleSubmit"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              class="login-btn"
              @click="handleSubmit"
            >
              登 录
            </el-button>
          </el-form-item>
        </el-form>

        <div class="login-footer">
          <span>尖兵部队 © 2026</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #409eff 0%, #337ecc 100%);
}

.login-container {
  display: flex;
  width: 860px;
  min-height: 520px;
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.login-brand {
  flex: 1;
  background: linear-gradient(135deg, #1d2b3a 0%, #2c3e50 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;

  .brand-content {
    text-align: center;
    color: white;

    h1 {
      margin: 16px 0 4px;
      font-size: 28px;
      font-weight: 700;
      letter-spacing: 2px;
    }

    .brand-subtitle {
      font-size: 16px;
      opacity: 0.9;
      margin-bottom: 12px;
    }

    .brand-desc {
      font-size: 13px;
      opacity: 0.6;
      margin-bottom: 32px;
    }
  }
}

.login-form-wrapper {
  flex: 1;
  padding: 60px 48px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.form-header {
  margin-bottom: 32px;

  h2 {
    font-size: 24px;
    color: #303133;
    margin-bottom: 8px;
  }

  p {
    color: #909399;
    font-size: 14px;
  }
}

.login-form {
  :deep(.el-input__wrapper) {
    border-radius: 8px;
    box-shadow: 0 0 0 1px #dcdfe6 inset;
    padding: 4px 12px;
  }

  :deep(.el-input__wrapper:hover) {
    box-shadow: 0 0 0 1px #409eff inset;
  }
}

.login-btn {
  width: 100%;
  border-radius: 8px;
  font-size: 16px;
  height: 44px;
  letter-spacing: 4px;
}

.login-footer {
  text-align: center;
  margin-top: 32px;
  color: #c0c4cc;
  font-size: 12px;
}
</style>
