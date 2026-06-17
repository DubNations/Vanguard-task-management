<script setup lang="ts">
import { ref } from 'vue'
import api from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const uploading = ref(false)
const previewData = ref<any[]>([])
const sessionId = ref('')
const importResult = ref<any>(null)

const handleUpload = async (file: File) => {
  uploading.value = true
  const formData = new FormData()
  formData.append('file', file)

  try {
    // 不手动设置 Content-Type，让浏览器自动生成带 boundary 的 multipart/form-data
    const { data } = await api.post('/imports/upload/', formData)
    sessionId.value = data.session_id
    previewData.value = data.preview_data || []
    ElMessage.success(`解析完成: ${data.valid_rows} 条有效 / ${data.error_rows} 条错误`)
  } catch {} finally {
    uploading.value = false
  }
  return false
}

const handleConfirm = async () => {
  await ElMessageBox.confirm(`确认导入 ${previewData.value.filter(r => r.valid).length} 条有效数据？`, '确认导入', {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
  })

  try {
    const { data } = await api.post(`/imports/${sessionId.value}/confirm/`)
    importResult.value = data
    ElMessage.success(`成功导入 ${data.imported_count} 条任务`)
  } catch {}
}
</script>

<template>
  <div class="page-container">
    <div class="page-container__header">
      <h2>任务导入</h2>
    </div>

    <el-card shadow="hover">
      <template #header><span>上传文件</span></template>
      <el-upload
        drag
        action=""
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls,.csv,.wps"
        :on-change="(f: any) => handleUpload(f.raw)"
      >
        <el-icon size="40" style="color: #909399;"><Upload /></el-icon>
        <div style="margin-top: 8px;">拖拽文件到此处或 <em>点击上传</em></div>
        <template #tip>
          <div style="color: #909399; font-size: 12px;">支持 .xlsx / .xls / .csv / .wps 格式</div>
        </template>
      </el-upload>
    </el-card>

    <!-- Preview -->
    <el-card v-if="previewData.length" shadow="hover" style="margin-top: 20px;">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>预览数据 ({{ previewData.length }} 行)</span>
          <el-button type="primary" @click="handleConfirm">确认导入</el-button>
        </div>
      </template>
      <el-table :data="previewData" max-height="400" size="small" stripe>
        <el-table-column prop="row" label="行" width="60" />
        <el-table-column label="有效" width="60">
          <template #default="{ row }">
            <el-icon :color="row.valid ? '#67c23a' : '#f56c6c'">
              <component :is="row.valid ? 'CircleCheck' : 'CircleClose'" />
            </el-icon>
          </template>
        </el-table-column>
        <el-table-column label="标题" min-width="200">
          <template #default="{ row }">{{ row.data?.title }}</template>
        </el-table-column>
        <el-table-column label="负责人" width="100">
          <template #default="{ row }">{{ row.data?.assignee_name }}</template>
        </el-table-column>
        <el-table-column label="优先级" width="80">
          <template #default="{ row }">{{ row.data?.priority }}</template>
        </el-table-column>
        <el-table-column label="截止日期" width="120">
          <template #default="{ row }">{{ row.data?.deadline }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Result -->
    <el-card v-if="importResult" shadow="hover" style="margin-top: 20px;">
      <el-result icon="success" :title="`成功导入 ${importResult.imported_count} 条任务`">
        <template #sub-title>
          <el-button type="primary" @click="$router.push('/tasks')">查看任务列表</el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>
