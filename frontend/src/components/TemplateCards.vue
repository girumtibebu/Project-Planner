<template>
  <!-- Saved boards to start a project from, as cards; Blank first -->
  <div class="grid gap-2 sm:grid-cols-3">
    <button v-for="t in cards" :key="t.name" class="card" :class="modelValue === t.name && 'card-on'" @click="emit('update:modelValue', t.name)">
      <span class="flex w-full min-w-0 items-center gap-2 font-medium text-ink-gray-9">
        <span :class="t.name ? 'lucide-layout-template' : 'lucide-file'" class="size-4 shrink-0 text-ink-gray-5" />
        <span class="min-w-0 truncate" :title="t.template_name">{{ t.template_name }}</span>
      </span>
      <span class="line-clamp-2 w-full text-xs text-ink-gray-5">{{ t.description || (t.name ? 'Saved board' : 'Start empty and add parts from the sidebar.') }}</span>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ modelValue: { type: String, default: '' }, templates: { type: Array, default: () => [] } })
const emit = defineEmits(['update:modelValue'])
const cards = computed(() => [{ name: '', template_name: 'Blank' }, ...props.templates])
</script>

<style scoped>
.card {
  @apply flex min-h-[4.5rem] min-w-0 flex-col items-start gap-1 overflow-hidden rounded-lg border border-outline-gray-2 p-3 text-left text-sm hover:border-outline-gray-4 hover:bg-surface-gray-1;
}
.card-on {
  @apply border-outline-gray-8 bg-surface-gray-2 ring-1 ring-outline-gray-8;
}
</style>
