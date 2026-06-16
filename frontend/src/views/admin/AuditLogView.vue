<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import api from '@/api'
import { timeAgo, formatDateTime } from '@/utils/format'

const loading = ref(true)
const logs = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 50

const filters = reactive({
  action: '',
  dateRange: null as [string, string] | null,
})

// 操作类型选项及颜色映射
const actionTypes = [
  { value: '', label: '全部操作' },
  { value: 'CREATE', label: '创建' },
  { value: 'UPDATE', label: '更新' },
  { value: 'DELETE', label: '删除' },
  { value: 'LOGIN', label: '登录' },
  { value: 'LOGOUT', label: '登出' },
  { value: 'TRANSITION', label: '状态变更' },
  { value: 'ASSIGN', label: '分配' },
  { value: 'COMMENT', label: '评论' },
  { value: 'IMPORT', label: '导入' },
  { value: 'EXPORT', label: '导出' },
]

const actionColorMap: Record<string, { type: string; color?: string }> = {
  CREATE: { type: 'success' },
  UPDATE: { type: 'primary' },
  DELETE: { type: 'danger' },
  LOGIN: { type: '' },
  LOGOUT: { type: 'info' },
  TRANSITION: { type: 'warning' },
  ASSIGN: { type: '' },
  COMMENT: { type: 'info' },
  IMPORT: { type: 'success' },
  EXPORT: { type: 'success' },
}

const actionLabelMap: Record<string, string> = {
  CREATE: '创建',
  UPDATE: '更新',
  DELETE: '删除',
  LOGIN: '登录',
  LOGOUT: '登出',
  TRANSITION: '状态变更',
  ASSIGN: '分配',
  COMMENT: '评论',
  IMPORT: '导入',
  EXPORT: '导出',
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize }
    if (filters.action) params.action = filters.action
    if (filters.dateRange && filters.dateRange[0]) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }
    const { data } = await api.get('/admin/audit/', { params })
    logs.value = data.results || []
    total.value = data.count || 0
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

const handlePageChange = (p: number) => {
  page.value = p
  fetchLogs()
}

// 监听筛选变化自动刷新
watch(() => filters.action, () => { page.value = 1; fetchLogs() })
watch(() => filters.dateRange, () => { page.value = 1; fetchLogs() })

const resetFilters = () => {
  filters.action = ''
  filters.dateRange = null
  page.value = 1
  fetchLogs()
}

onMounted(fetchLogs)
</script>

<template>
  <div class="page-container">
    <div class="page-container__header">
      <h2>审计日志</h2>
    </div>

    <!-- 筛选区 -->
    <el-card shadow="hover" style="margin-bottom: 16px;">
      <div class="filter-bar">
        <div class="filter-bar__items">
          <el-select v-model="filters.action" placeholder="操作类型" clearable style="width: 140px">
            <el-option v-for="o in actionTypes" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 280px"
          />
          <el-button @click="resetFilters">重置</el-button>
        </div>
      </div>
    </el-card>

    <el-table :data="logs" v-loading="loading" stripe size="small">
      <el-table-column prop="user" label="用户" width="120" />
      <el-table-column label="操作" width="110">
        <template #default="{ row }">
          <el-tag
            size="small"
            :type="(actionColorMap[row.action]?.type as any) || 'info'"
          >
            {{ actionLabelMap[row.action] || row.action }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="resource_type" label="资源" width="120" />
      <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip />
      <el-table-column prop="ip_address" label="IP" width="140" />
      <el-table-column label="时间" width="160">
        <template #default="{ row }">
          <el-tooltip :content="formatDateTime(row.created_at)" placement="top">
            <span style="cursor: help;">{{ timeAgo(row.created_at) }}</span>
          </el-tooltip>
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
  </div>
</template>

<style scoped lang="scss">
.filter-bar {
  &__items {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
  }
}
</style>
