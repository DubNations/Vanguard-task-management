<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import api from '@/api'

const loading = ref(true)
const error = ref<string | null>(null)
const myStats = ref<any>({})
const leaderboard = ref<any[]>([])
const period = ref<'week' | 'month' | 'all'>('week')
const leaderboardLoading = ref(false)

const medalMap: Record<number, string> = {
  1: '🥇',
  2: '🥈',
  3: '🥉',
}

const fetchMyStats = async () => {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get('/points/my-stats/')
    myStats.value = data
  } catch {
    error.value = '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

const fetchLeaderboard = async () => {
  leaderboardLoading.value = true
  try {
    const { data } = await api.get('/points/leaderboard/', { params: { period: period.value } })
    leaderboard.value = data.results || data || []
  } catch {} finally {
    leaderboardLoading.value = false
  }
}

watch(period, fetchLeaderboard)
onMounted(() => {
  fetchMyStats()
  fetchLeaderboard()
})
</script>

<template>
  <div class="page-container" v-loading="loading">
    <el-result v-if="error" icon="error" :title="error">
      <template #extra><el-button @click="fetchMyStats">重试</el-button></template>
    </el-result>
    <div class="page-container__header">
      <h2>积分排行</h2>
    </div>

    <!-- Stats Cards -->
    <div class="stats-row">
      <el-card shadow="hover" class="stats-card stats-card--primary">
        <div class="stats-card__value">{{ myStats.total_points ?? 0 }}</div>
        <div class="stats-card__label">我的积分</div>
      </el-card>
      <el-card shadow="hover" class="stats-card stats-card--green">
        <div class="stats-card__value">{{ myStats.weekly_points ?? 0 }}</div>
        <div class="stats-card__label">本周获得</div>
      </el-card>
      <el-card shadow="hover" class="stats-card stats-card--orange">
        <div class="stats-card__value">{{ myStats.rank ?? '-' }}</div>
        <div class="stats-card__label">当前排名</div>
      </el-card>
    </div>

    <!-- Leaderboard -->
    <el-card shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>排行榜</span>
          <el-radio-group v-model="period" size="small">
            <el-radio-button value="week">本周</el-radio-button>
            <el-radio-button value="month">本月</el-radio-button>
            <el-radio-button value="all">全部</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-table :data="leaderboard" v-loading="leaderboardLoading" stripe>
        <el-table-column label="排名" width="80" align="center">
          <template #default="{ row, $index }">
            <span v-if="medalMap[$index + 1]" class="medal">{{ medalMap[$index + 1] }}</span>
            <span v-else>{{ $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" min-width="150" />
        <el-table-column prop="team_name" label="团队" width="150" />
        <el-table-column label="积分" width="120" align="right">
          <template #default="{ row }">
            <span class="points-value">{{ row.points ?? row.total_points ?? 0 }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.stats-card {
  text-align: center;
  padding: 10px 0;

  &__value {
    font-size: 36px;
    font-weight: 700;
    line-height: 1.2;
  }

  &__label {
    font-size: 14px;
    color: #909399;
    margin-top: 6px;
  }

  &--primary .stats-card__value { color: #409eff; }
  &--green .stats-card__value { color: #67c23a; }
  &--orange .stats-card__value { color: #e6a23c; }
}

.medal {
  font-size: 20px;
}

.points-value {
  font-weight: 600;
  color: #409eff;
}
</style>
