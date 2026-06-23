<template>
  <el-card shadow="hover" class="stat-card" :body-style="{ padding: '20px' }">
    <div class="stat-content">
      <div class="stat-info">
        <span class="stat-label">{{ label }}</span>
        <span class="stat-value" :style="{ color: valueColor }">{{ displayValue }}</span>
        <span v-if="subtitle" class="stat-subtitle">{{ subtitle }}</span>
      </div>
      <div class="stat-icon" :style="{ backgroundColor: iconBg }">
        <el-icon :size="24" :color="iconColor">
          <component :is="icon" />
        </el-icon>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  label: string
  value: number | string
  icon: Component
  iconColor?: string
  iconBg?: string
  valueColor?: string
  subtitle?: string
  format?: 'number' | 'percentage'
}

const props = withDefaults(defineProps<Props>(), {
  iconColor: '#409EFF',
  iconBg: '#ecf5ff',
  valueColor: '#303133',
  format: 'number',
})

const displayValue = computed(() => {
  if (props.format === 'percentage') {
    return `${(Number(props.value) * 100).toFixed(0)}%`
  }
  return props.value
})
</script>

<style scoped>
.stat-card {
  height: 100%;
}

.stat-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  line-height: 1.2;
}

.stat-subtitle {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
