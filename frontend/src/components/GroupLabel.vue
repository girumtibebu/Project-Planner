<template>
  <span class="flex min-w-0 items-center gap-2">
    <StateIcon v-if="g.state" :state="g.state(k)" />
    <Avatar v-else-if="g.user && k" :label="memberName(k)" :image="memberIndex[k]?.user_image" size="xs" />
    <span v-else-if="g.iconClass" :class="g.iconClass(k)" class="size-4" :style="{ color: g.color?.(k) }" />
    <span class="truncate text-sm font-medium text-ink-gray-8">{{ g.label(k) }}</span>
    <span class="text-sm text-ink-gray-4">{{ count }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { Avatar } from 'frappe-ui'
import StateIcon from './StateIcon.vue'
import { memberIndex, memberName } from '../store'

const props = defineProps({ grouper: Object, k: [String, Number], count: Number })
const g = computed(() => props.grouper)
</script>
