<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const creating = ref(false)
const error = ref<string | null>(null)
const exports = ref<any[]>([])
const format = ref<'excel' | 'csv'>('excel')

const fetchExports = async () => {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get('/exports/')
    exports.value = data.results || data || []
  } catch {
    error.value = '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

const createExport = async () => {
  creating.value = true
  try {
    await api.post('/exports/create/', { format: format.value })
    ElMessage.success('导出任务已创建')
    fetchExports()
  } catch {} finally {
    creating.value = false
  }
}

const downloadFile = (row: any) => {
  if (row.file_url) {
    window.open(row.file_url, '_blank')
  } else {
    ElMessage.warning('文件暂不可下载')
  }
}

const statusMap: Record<string, { label: string; type: 'success' | 'warning' | 'danger' | 'info' }> = {
  PENDING: { label: '等待中', type: 'info' },
  PROCESSING: { label: '处理中', type: 'warning' },
  COMPLETED: { label: '已完成', type: 'success' },
  FAILED: { label: '失败', type: 'danger' },
}

onMounted(fetchExports)
</script>

<template>
  <div class="page-container">
    <el-result v-if="error" icon="error" :title="error">
      <template #extra><el-button @click="fetchExports">重试</el-button></template>
    </el-result>
    <div class="page-container__header">
      <h2>任务导出</h2>
    </div>

    <!-- Create Export -->
    <el-card shadow="hover">
      <template #header><span>创建导出</span></template>
      <el-form inline>
        <el-form-item label="导出格式">
          <el-select v-model="format" style="width: 160px;">
            <el-option label="Excel (.xlsx)" value="excel" />
            <el-option label="CSV (.csv)" value="csv" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="creating" @click="createExport">
            创建导出
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Export History -->
    <el-card shadow="hover" style="margin-top: 20px;">
      <template #header><span>导出记录</span></template>
      <el-table :data="exports" v-loading="loading" stripe>
        <el-table-column label="格式" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.format === 'excel' ? 'Excel' : 'CSV' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type ?? 'info'" size="small">
              {{ statusMap[row.status]?.label ?? row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_name" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="row_count" label="行数" width="80" align="right" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              link
              :disabled="row.status !== 'COMPLETED'"
              @click="downloadFile(row)"
            >
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.page-container {
  padding: 0;
}
</style>
