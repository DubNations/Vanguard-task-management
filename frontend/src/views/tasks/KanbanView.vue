<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import StatusTag from '@/components/StatusTag.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import { formatDate } from '@/utils/format'

const router = useRouter()
const loading = ref(true)
const columns = ref<Record<string, any>>({})

const statusOrder = ['PENDING', 'IN_PROGRESS', 'IN_REVIEW', 'COMPLETED', 'REJECTED']
const statusColors: Record<string, string> = {
  PENDING: '#909399', IN_PROGRESS: '#409eff', IN_REVIEW: '#e6a23c',
  COMPLETED: '#67c23a', REJECTED: '#f56c6c', CANCELLED: '#c0c4cc',
}

const fetchKanban = async () => {
  loading.value = true
  try {
    const { data } = await api.get('/tasks/kanban/')
    columns.value = data
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

const goToTask = (taskId: string) => {
  router.push(`/tasks/${taskId}`)
}

onMounted(fetchKanban)
</script>

<template>
  <div class="page-container">
    <div class="page-container__header">
      <h2>看板视图</h2>
      <el-button @click="fetchKanban" :loading="loading">刷新</el-button>
    </div>

    <div class="kanban-board" v-loading="loading">
      <div v-for="status in statusOrder" :key="status" class="kanban-column">
        <div class="kanban-column__header" :style="{ borderTopColor: statusColors[status] }">
          <div style="display:flex; align-items:center; gap:8px;">
            <StatusTag :status="status" />
            <span>{{ columns[status]?.label || '' }}</span>
          </div>
          <el-tag size="small" round>{{ columns[status]?.count || 0 }}</el-tag>
        </div>
        <div class="kanban-column__body">
          <div
            v-for="task in (columns[status]?.tasks || [])"
            :key="task.id"
            class="kanban-card"
            @click="goToTask(task.id)"
          >
            <div class="kanban-card__title">{{ task.title }}</div>
            <div class="kanban-card__tags">
              <PriorityTag :priority="task.priority" />
            </div>
            <div class="kanban-card__meta">
              <span>{{ task.task_no }}</span>
              <span v-if="task.assignee_name">{{ task.assignee_name }}</span>
            </div>
            <div class="kanban-card__deadline" v-if="task.deadline">
              <span :style="{ color: task.is_overdue ? '#f56c6c' : '#909399', fontWeight: task.is_overdue ? '600' : '400' }">
                {{ formatDate(task.deadline) }}
                <el-tag v-if="task.is_overdue" type="danger" size="small" style="margin-left:4px;">逾期</el-tag>
              </span>
            </div>
            <el-progress
              v-if="task.progress > 0"
              :percentage="task.progress"
              :stroke-width="4"
              :show-text="false"
              style="margin-top: 6px;"
            />
          </div>
          <el-empty v-if="!columns[status]?.tasks?.length" description="暂无" :image-size="40" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.kanban-board {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  min-height: 500px;
}

.kanban-column {
  flex: 1;
  min-width: 260px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;

  &__header {
    padding: 12px 16px;
    font-weight: 600;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 3px solid #ddd;
    border-radius: 8px 8px 0 0;
  }

  &__body {
    padding: 8px;
    flex: 1;
    overflow-y: auto;
  }
}

.kanban-card {
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
    border-color: #e0e0e0;
    transform: translateY(-1px);
  }

  &__title {
    font-size: 14px;
    font-weight: 500;
    color: #303133;
    margin-bottom: 6px;
    line-height: 1.4;
  }

  &__tags {
    margin-bottom: 6px;
  }

  &__meta {
    font-size: 12px;
    color: #909399;
    display: flex;
    justify-content: space-between;
  }

  &__deadline {
    font-size: 12px;
    margin-top: 4px;
  }
}
</style>
