<template>
  <el-card shadow="hover" class="workload-card">
    <template #header>
      <div class="card-header">
        <span>成员工作负载</span>
        <el-tag type="info" size="small">{{ members.length }} 人</el-tag>
      </div>
    </template>
    <el-table :data="members" style="width: 100%" size="small">
      <el-table-column prop="display_name" label="成员" min-width="120">
        <template #default="{ row }">
          <div class="member-cell">
            <span class="member-name">{{ row.display_name }}</span>
            <span v-if="row.team_name" class="member-team">{{ row.team_name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="in_progress" label="进行中" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.in_progress > 3 ? 'danger' : row.in_progress > 0 ? 'warning' : 'info'" size="small">
            {{ row.in_progress }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="completed_this_month" label="本月完成" width="90" align="center" />
      <el-table-column prop="total_points" label="本月积分" width="90" align="center">
        <template #default="{ row }">
          <span class="points-value">{{ row.total_points }}</span>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import type { MemberWorkload } from '@/types/dashboard'

interface Props {
  members: MemberWorkload[]
}

defineProps<Props>()
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.member-cell {
  display: flex;
  flex-direction: column;
}

.member-name {
  font-weight: 500;
}

.member-team {
  font-size: 12px;
  color: #909399;
}

.points-value {
  color: #409EFF;
  font-weight: 600;
}
</style>
