<template>
  <el-tag
    :type="priorityType"
    :effect="effect"
    size="small"
  >
    <el-icon v-if="priority === 'URGENT'" style="margin-right: 2px;">
      <WarningFilled />
    </el-icon>
    {{ priorityLabel }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'

type TagType = 'primary' | 'success' | 'warning' | 'danger' | 'info'

const props = withDefaults(defineProps<{
  priority: string
  effect?: 'light' | 'dark' | 'plain'
}>(), {
  effect: 'light',
})

const priorityMap: Record<string, { label: string; type: TagType }> = {
  LOW: { label: '低', type: 'info' },
  MEDIUM: { label: '中', type: 'primary' },
  HIGH: { label: '高', type: 'warning' },
  URGENT: { label: '紧急', type: 'danger' },
}

const priorityLabel = computed(() => priorityMap[props.priority]?.label ?? props.priority)
const priorityType = computed<TagType>(() => priorityMap[props.priority]?.type ?? 'info')
</script>
