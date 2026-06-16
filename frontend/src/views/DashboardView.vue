<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import StatusTag from '@/components/StatusTag.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const summary = ref<any>({})
const statusData = ref<any[]>([])
const trendData = ref<any[]>([])
const myInProgress = ref<any[]>([])
const myPending = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const [summaryRes, statusRes, trendRes, inProgressRes, pendingRes] = await Promise.all([
      api.get('/dashboard/summary/'),
      api.get('/dashboard/status/'),
      api.get('/dashboard/trend/'),
      api.get('/tasks/', { params: { status: 'IN_PROGRESS', page_size: 5 } }),
      api.get('/tasks/', { params: { status: 'PENDING', page_size: 5 } }),
    ])
    summary.value = summaryRes.data
    statusData.value = statusRes.data
    trendData.value = trendRes.data
    myInProgress.value = inProgressRes.data.results || inProgressRes.data || []
    myPending.value = pendingRes.data.results || pendingRes.data || []
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
})

const statusLabels: Record<string, string> = {
  PENDING: '待领取',
  IN_PROGRESS: '进行中',
  IN_REVIEW: '待审核',
  COMPLETED: '已完成',
  REJECTED: '已退回',
  CANCELLED: '已取消',
}

const statusColors: Record<string, string> = {
  PENDING: '#909399',
  IN_PROGRESS: '#409eff',
  IN_REVIEW: '#e6a23c',
  COMPLETED: '#67c23a',
  REJECTED: '#f56c6c',
  CANCELLED: '#c0c4cc',
}

/** 周趋势柱状图最大值，用于计算相对高度 */
const trendMax = ref(1)
const calcTrendMax = () => {
  if (!trendData.value.length) return 1
  return Math.max(...trendData.value.flatMap((w: any) => [w.created, w.completed]), 1)
}

import { watch } from 'vue'
watch(trendData, () => { trendMax.value = calcTrendMax() }, { immediate: true })
</script>

<template>
  <div class="page-container" v-loading="loading">
    <div class="page-container__header">
      <h2>仪表盘</h2>
    </div>

    <!-- Stat Cards -->
    <div class="stat-cards">
      <div class="stat-card stat-card--blue">
        <div class="stat-card__value">{{ summary.total || 0 }}</div>
        <div class="stat-card__label">总任务数</div>
      </div>
      <div class="stat-card stat-card--blue">
        <div class="stat-card__value">{{ summary.in_progress || 0 }}</div>
        <div class="stat-card__label">进行中</div>
      </div>
      <div class="stat-card stat-card--orange">
        <div class="stat-card__value">{{ summary.in_review || 0 }}</div>
        <div class="stat-card__label">待审核</div>
      </div>
      <div class="stat-card stat-card--green">
        <div class="stat-card__value">{{ summary.completed || 0 }}</div>
        <div class="stat-card__label">已完成</div>
      </div>
      <div class="stat-card stat-card--red">
        <div class="stat-card__value">{{ summary.overdue || 0 }}</div>
        <div class="stat-card__label">已逾期</div>
      </div>
      <div class="stat-card stat-card--green">
        <div class="stat-card__value">{{ summary.completed_today || 0 }}</div>
        <div class="stat-card__label">今日完成</div>
      </div>
    </div>

    <!-- Charts -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>任务状态分布</span>
          </template>
          <div class="status-dist">
            <el-empty v-if="!statusData.length" description="暂无数据" />
            <div v-else>
              <div v-for="item in statusData" :key="item.status" class="status-dist__row">
                <div class="status-dist__label">
                  <StatusTag :status="item.status" />
                </div>
                <div class="status-dist__bar-wrap">
                  <el-progress
                    :percentage="summary.total ? Math.round(item.count / summary.total * 100) : 0"
                    :color="statusColors[item.status] || '#409eff'"
                    :stroke-width="14"
                    :text-inside="true"
                    :format="() => `${item.count}`"
                  />
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>周趋势</span>
          </template>
          <div class="trend-chart-wrap">
            <el-empty v-if="!trendData.length" description="暂无数据" />
            <div v-else class="trend-chart">
              <div class="trend-chart__legend">
                <span class="trend-chart__legend-item"><i style="background:#409eff"></i>新建</span>
                <span class="trend-chart__legend-item"><i style="background:#67c23a"></i>完成</span>
              </div>
              <div class="trend-chart__bars">
                <div v-for="week in trendData" :key="week.week" class="trend-bar">
                  <div class="trend-bar__values">
                    <span class="trend-bar__created">{{ week.created }}</span>
                    <span class="trend-bar__completed">{{ week.completed }}</span>
                  </div>
                  <div class="trend-bar__bars">
                    <div
                      class="trend-bar__created-bar"
                      :style="{ height: Math.max((week.created / trendMax) * 140, 4) + 'px' }"
                    />
                    <div
                      class="trend-bar__completed-bar"
                      :style="{ height: Math.max((week.completed / trendMax) * 140, 4) + 'px' }"
                    />
                  </div>
                  <div class="trend-bar__label">{{ week.week }}</div>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 我的待办 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span>我的进行中</span>
              <el-tag size="small" type="primary" round>{{ myInProgress.length }}</el-tag>
            </div>
          </template>
          <el-empty v-if="!myInProgress.length" description="暂无进行中任务" :image-size="60" />
          <div v-else class="todo-list">
            <div
              v-for="task in myInProgress"
              :key="task.id"
              class="todo-item"
              @click="router.push(`/tasks/${task.id}`)"
            >
              <div class="todo-item__main">
                <span class="todo-item__title">{{ task.title }}</span>
                <div class="todo-item__tags">
                  <PriorityTag :priority="task.priority" />
                </div>
              </div>
              <div class="todo-item__meta">
                <span>{{ task.task_no }}</span>
                <span :style="{ color: task.is_overdue ? '#f56c6c' : '#909399' }">
                  {{ task.deadline ? formatDateTime(task.deadline) : '-' }}
                </span>
              </div>
              <el-progress :percentage="task.progress" :stroke-width="4" :show-text="false" style="margin-top:4px;" />
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span>我的待领取</span>
              <el-tag size="small" type="info" round>{{ myPending.length }}</el-tag>
            </div>
          </template>
          <el-empty v-if="!myPending.length" description="暂无待领取任务" :image-size="60" />
          <div v-else class="todo-list">
            <div
              v-for="task in myPending"
              :key="task.id"
              class="todo-item"
              @click="router.push(`/tasks/${task.id}`)"
            >
              <div class="todo-item__main">
                <span class="todo-item__title">{{ task.title }}</span>
                <div class="todo-item__tags">
                  <PriorityTag :priority="task.priority" />
                </div>
              </div>
              <div class="todo-item__meta">
                <span>{{ task.task_no }}</span>
                <span :style="{ color: task.is_overdue ? '#f56c6c' : '#909399' }">
                  {{ task.deadline ? formatDateTime(task.deadline) : '-' }}
                </span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.status-dist {
  min-height: 200px;
  display: flex;
  align-items: center;

  > div { width: 100%; }
}

.status-dist__row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.status-dist__label {
  min-width: 70px;
  flex-shrink: 0;
}

.status-dist__bar-wrap {
  flex: 1;
}

.trend-chart-wrap {
  min-height: 260px;
  display: flex;
  align-items: center;
}

.trend-chart {
  width: 100%;
  &__legend {
    display: flex;
    gap: 16px;
    margin-bottom: 12px;
    justify-content: flex-end;
  }
  &__legend-item {
    font-size: 12px;
    color: #606266;
    display: flex;
    align-items: center;
    gap: 4px;
    i {
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 2px;
    }
  }
  &__bars {
    display: flex;
    align-items: flex-end;
    justify-content: space-around;
    height: 200px;
    padding: 10px 0;
  }
}

.trend-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;

  &__values {
    font-size: 11px;
    display: flex;
    gap: 8px;
  }
  &__created { color: #409eff; }
  &__completed { color: #67c23a; }

  &__bars {
    display: flex;
    gap: 4px;
    align-items: flex-end;
    min-height: 80px;
  }
  &__created-bar {
    width: 18px;
    background: linear-gradient(180deg, #409eff, #79bbff);
    border-radius: 4px 4px 0 0;
    transition: height 0.4s ease;
  }
  &__completed-bar {
    width: 18px;
    background: linear-gradient(180deg, #67c23a, #95d475);
    border-radius: 4px 4px 0 0;
    transition: height 0.4s ease;
  }
  &__label {
    font-size: 11px;
    color: #909399;
    margin-top: 2px;
  }
}

.todo-list {
  max-height: 320px;
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

  &__main {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
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

  &__tags {
    flex-shrink: 0;
  }

  &__meta {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
  }
}
</style>
