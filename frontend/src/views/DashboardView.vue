<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Document, Loading, Finished, WarningFilled, TrophyBase, UserFilled
} from '@element-plus/icons-vue'
import { dashboardApi } from '@/api/modules'
import { useAuthStore } from '@/stores/auth'
import DashboardStatCard from '@/components/dashboard/DashboardStatCard.vue'
import OverdueAlert from '@/components/dashboard/OverdueAlert.vue'
import MemberWorkload from '@/components/dashboard/MemberWorkload.vue'
import StatusTag from '@/components/StatusTag.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import type {
  MemberDashboardResponse, LeaderDashboardResponse,
  DashboardSummary, TodoTask, OverdueTask, MemberWorkload as MemberWorkloadType
} from '@/types/dashboard'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const error = ref<string | null>(null)

const isLeader = computed(() =>
  authStore.user?.role === 'LEADER' || authStore.user?.role === 'ADMIN' || authStore.user?.is_superuser
)

// MEMBER 数据
const memberData = ref<MemberDashboardResponse | null>(null)
// LEADER 数据
const leaderData = ref<LeaderDashboardResponse | null>(null)

const summary = computed<DashboardSummary>(() => {
  if (isLeader.value && leaderData.value) return leaderData.value.summary
  if (memberData.value) return memberData.value.summary
  return { total: 0, pending: 0, in_progress: 0, in_review: 0, completed: 0, overdue: 0 }
})

const todoList = computed<TodoTask[]>(() => memberData.value?.todo_list ?? [])
const overdueTasks = computed<OverdueTask[]>(() => leaderData.value?.overdue_tasks ?? [])
const memberWorkload = computed<MemberWorkloadType[]>(() => leaderData.value?.member_workload ?? [])
const monthlyPoints = computed(() => memberData.value?.monthly_points ?? { earned: 0, completed_count: 0, in_progress_count: 0 })
const monthlyTeamPoints = computed(() => leaderData.value?.monthly_team_points ?? { total_points: 0, completed_count: 0, completion_rate: 0 })

const fetchData = async () => {
  loading.value = true
  error.value = null
  try {
    // MEMBER 数据始终获取
    const memberRes = await dashboardApi.getMemberDashboard()
    memberData.value = memberRes.data

    // LEADER 额外获取管理台数据
    if (isLeader.value) {
      const leaderRes = await dashboardApi.getLeaderDashboard()
      leaderData.value = leaderRes.data
    }
  } catch (e: any) {
    console.error('Dashboard fetch error:', e)
    error.value = '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

function goToTask(taskId: string) {
  router.push(`/tasks/${taskId}`)
}

function goToTaskList(status?: string) {
  const query: Record<string, string> = {}
  if (status) query.status = status
  router.push({ path: '/tasks', query })
}
</script>

<template>
  <div class="page-container" v-loading="loading">
    <el-result v-if="error" icon="error" :title="error">
      <template #extra>
        <el-button @click="fetchData">重试</el-button>
      </template>
    </el-result>

    <template v-else>
      <!-- 页头 -->
      <div class="page-container__header">
        <h2>{{ isLeader ? '团队管理台' : '我的工作台' }}</h2>
        <el-button text @click="fetchData">
          <el-icon><Loading /></el-icon>
          刷新
        </el-button>
      </div>

      <!-- 状态卡片 -->
      <el-row :gutter="16" class="stat-row">
        <el-col :xs="12" :sm="8" :md="4">
          <DashboardStatCard
            label="总任务"
            :value="summary.total"
            :icon="Document"
            icon-color="#409EFF"
            icon-bg="#ecf5ff"
            @click="goToTaskList()"
          />
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <DashboardStatCard
            label="待领取"
            :value="summary.pending"
            :icon="WarningFilled"
            icon-color="#E6A23C"
            icon-bg="#fdf6ec"
            @click="goToTaskList('PENDING')"
          />
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <DashboardStatCard
            label="进行中"
            :value="summary.in_progress"
            :icon="Loading"
            icon-color="#409EFF"
            icon-bg="#ecf5ff"
            @click="goToTaskList('IN_PROGRESS')"
          />
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <DashboardStatCard
            label="待审核"
            :value="summary.in_review"
            :icon="Finished"
            icon-color="#E6A23C"
            icon-bg="#fdf6ec"
            @click="goToTaskList('IN_REVIEW')"
          />
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <DashboardStatCard
            label="已完成"
            :value="summary.completed"
            :icon="Finished"
            icon-color="#67C23A"
            icon-bg="#f0f9eb"
            @click="goToTaskList('COMPLETED')"
          />
        </el-col>
        <el-col :xs="12" :sm="8" :md="4">
          <DashboardStatCard
            label="已逾期"
            :value="summary.overdue"
            :icon="WarningFilled"
            icon-color="#F56C6C"
            icon-bg="#fef0f0"
          />
        </el-col>
      </el-row>

      <!-- MEMBER: 本月积分 + 待办列表 -->
      <el-row :gutter="16" class="content-row">
        <el-col :xs="24" :md="8">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <el-icon><TrophyBase /></el-icon>
                <span>本月积分</span>
              </div>
            </template>
            <div class="points-display">
              <div class="points-main">
                <span class="points-value">{{ monthlyPoints.earned }}</span>
                <span class="points-unit">分</span>
              </div>
              <div class="points-detail">
                <span>已完成 {{ monthlyPoints.completed_count }} 项</span>
                <span>进行中 {{ monthlyPoints.in_progress_count }} 项</span>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="16">
          <el-card shadow="hover" class="todo-card">
            <template #header>
              <div class="card-header">
                <span>待办任务</span>
                <el-tag type="info" size="small">{{ todoList.length }} 项</el-tag>
              </div>
            </template>
            <el-empty v-if="!todoList.length" description="暂无待办任务" :image-size="60" />
            <div v-else class="todo-list">
              <div
                v-for="task in todoList"
                :key="task.id"
                class="todo-item"
                :class="{ 'is-overdue': task.is_overdue }"
                @click="goToTask(task.id)"
              >
                <div class="todo-item__main">
                  <span class="todo-item__no">{{ task.task_no }}</span>
                  <span class="todo-item__title">{{ task.title }}</span>
                  <PriorityTag :priority="task.priority" />
                </div>
                <div class="todo-item__meta">
                  <StatusTag :status="task.status" />
                  <span v-if="task.days_label" class="todo-item__deadline" :class="{ 'is-overdue': task.is_overdue }">
                    {{ task.days_label }}
                  </span>
                  <span v-if="task.assignee_name" class="todo-item__assignee">{{ task.assignee_name }}</span>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- LEADER: 逾期预警 + 成员负载 -->
      <template v-if="isLeader">
        <el-row :gutter="16" class="content-row">
          <el-col :xs="24" :md="12">
            <OverdueAlert :tasks="overdueTasks" @view-task="goToTask" />
          </el-col>
          <el-col :xs="24" :md="12">
            <el-card shadow="hover">
              <template #header>
                <div class="card-header">
                  <el-icon><TrophyBase /></el-icon>
                  <span>本月团队积分</span>
                </div>
              </template>
              <div class="points-display">
                <div class="points-main">
                  <span class="points-value">{{ monthlyTeamPoints.total_points }}</span>
                  <span class="points-unit">分</span>
                </div>
                <div class="points-detail">
                  <span>已完成 {{ monthlyTeamPoints.completed_count }} 项</span>
                  <span>完成率 {{ (monthlyTeamPoints.completion_rate * 100).toFixed(0) }}%</span>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="16" class="content-row">
          <el-col :span="24">
            <MemberWorkload :members="memberWorkload" />
          </el-col>
        </el-row>
      </template>
    </template>
  </div>
</template>

<style scoped lang="scss">
.stat-row {
  margin-bottom: 16px;
}

.content-row {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

// 积分展示
.points-display {
  text-align: center;
  padding: 16px 0;
}

.points-main {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 4px;
}

.points-value {
  font-size: 36px;
  font-weight: 700;
  color: #409EFF;
}

.points-unit {
  font-size: 14px;
  color: #909399;
}

.points-detail {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
}

// 待办列表
.todo-card {
  height: 100%;
}

.todo-list {
  max-height: 360px;
  overflow-y: auto;
}

.todo-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid #f5f5f5;

  &:hover {
    background: #f0f7ff;
  }

  &:last-child {
    border-bottom: none;
  }

  &.is-overdue {
    background: #fef0f0;
    border-left: 3px solid #F56C6C;
  }

  &__main {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__no {
    font-size: 12px;
    color: #909399;
    font-family: monospace;
    flex-shrink: 0;
  }

  &__title {
    font-size: 14px;
    font-weight: 500;
    color: #303133;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }

  &__meta {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 6px;
    font-size: 12px;
    color: #909399;
  }

  &__deadline {
    color: #E6A23C;

    &.is-overdue {
      color: #F56C6C;
      font-weight: 600;
    }
  }

  &__assignee {
    color: #606266;
  }
}
</style>
