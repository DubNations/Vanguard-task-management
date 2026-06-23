<template>
  <el-card v-if="tasks.length > 0" shadow="hover" class="overdue-alert">
    <template #header>
      <div class="alert-header">
        <el-icon :size="18" color="#E6A23C"><WarningFilled /></el-icon>
        <span class="alert-title">逾期任务</span>
        <el-tag type="danger" size="small">{{ tasks.length }} 项</el-tag>
      </div>
    </template>
    <div class="task-list">
      <div
        v-for="task in tasks"
        :key="task.id"
        class="task-item"
        @click="$emit('viewTask', task.id)"
      >
        <div class="task-main">
          <span class="task-no">{{ task.task_no }}</span>
          <span class="task-title">{{ task.title }}</span>
        </div>
        <div class="task-meta">
          <el-tag :type="priorityType(task.priority)" size="small">
            {{ priorityLabel(task.priority) }}
          </el-tag>
          <span class="task-assignee">{{ task.assignee_name }}</span>
          <span class="task-days" :class="{ 'is-critical': (task.days_until_deadline ?? 0) < -7 }">
            {{ task.days_label }}
          </span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { WarningFilled } from '@element-plus/icons-vue'
import type { OverdueTask } from '@/types/dashboard'

interface Props {
  tasks: OverdueTask[]
}

defineProps<Props>()
defineEmits<{
  viewTask: [taskId: string]
}>()

const priorityMap: Record<string, { type: 'success' | 'warning' | 'danger' | 'info'; label: string }> = {
  URGENT: { type: 'danger', label: '紧急' },
  HIGH: { type: 'warning', label: '高' },
  MEDIUM: { type: 'info', label: '中' },
  LOW: { type: 'info', label: '低' },
}

function priorityType(priority: string) {
  return priorityMap[priority]?.type ?? 'info'
}

function priorityLabel(priority: string) {
  return priorityMap[priority]?.label || priority
}
</script>

<style scoped>
.overdue-alert {
  border-left: 3px solid #E6A23C;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.alert-title {
  font-weight: 600;
  flex: 1;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-item {
  padding: 12px;
  border-radius: 8px;
  background: #fafafa;
  cursor: pointer;
  transition: background 0.2s;
}

.task-item:hover {
  background: #f0f2f5;
}

.task-main {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.task-no {
  font-size: 12px;
  color: #909399;
  font-family: monospace;
}

.task-title {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #909399;
}

.task-assignee {
  color: #606266;
}

.task-days {
  color: #E6A23C;
}

.task-days.is-critical {
  color: #F56C6C;
  font-weight: 600;
}
</style>
