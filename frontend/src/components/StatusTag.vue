<template>
  <el-tag
    :type="statusType"
    :effect="effect"
    size="small"
    round
  >
    {{ statusLabel }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type TagType = 'primary' | 'success' | 'warning' | 'danger' | 'info'

const props = withDefaults(defineProps<{
  status: string
  effect?: 'light' | 'dark' | 'plain'
}>(), {
  effect: 'light',
})

const statusMap: Record<string, { label: string; type: TagType }> = {
  PENDING: { label: '待领取', type: 'info' },
  IN_PROGRESS: { label: '进行中', type: 'primary' },
  IN_REVIEW: { label: '待审核', type: 'warning' },
  COMPLETED: { label: '已完成', type: 'success' },
  REJECTED: { label: '已退回', type: 'danger' },
  CANCELLED: { label: '已取消', type: 'info' },
}

const statusLabel = computed(() => statusMap[props.status]?.label ?? props.status)
const statusType = computed<TagType>(() => statusMap[props.status]?.type ?? 'info')
</script>
