<template>
  <!-- Plane-style state glyph: empty dashed circle, circle, half circle, check, cross -->
  <svg :width="size" :height="size" viewBox="0 0 16 16" class="shrink-0" aria-hidden="true">
    <circle
      v-if="group === 'Backlog'"
      cx="8" cy="8" r="6" fill="none" :stroke="color" stroke-width="1.5" stroke-dasharray="2.2 2"
    />
    <circle v-else-if="group === 'Unstarted'" cx="8" cy="8" r="6" fill="none" :stroke="color" stroke-width="1.5" />
    <template v-else-if="group === 'Started'">
      <circle cx="8" cy="8" r="6" fill="none" :stroke="color" stroke-width="1.5" />
      <path d="M8 4a4 4 0 0 1 0 8z" :fill="color" />
    </template>
    <template v-else-if="group === 'Completed'">
      <circle cx="8" cy="8" r="6.5" :fill="color" />
      <path d="M5.2 8.2 7.2 10.1 10.9 6" fill="none" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
    </template>
    <template v-else>
      <circle cx="8" cy="8" r="6.5" :fill="color" />
      <path d="M5.8 5.8 10.2 10.2M10.2 5.8 5.8 10.2" stroke="white" stroke-width="1.6" stroke-linecap="round" />
    </template>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ state: { type: Object, default: () => ({}) }, size: { type: Number, default: 14 } })
const group = computed(() => props.state?.state_group || 'Unstarted')
const color = computed(() => props.state?.color || '#6B7280')
</script>
