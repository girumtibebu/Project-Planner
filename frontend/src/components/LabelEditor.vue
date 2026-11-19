<template>
  <div class="flex flex-wrap items-center gap-1">
    <span
      v-for="label in labels"
      :key="label"
      class="inline-flex items-center gap-1 rounded-full border border-outline-gray-2 px-2 py-0.5 text-xs text-ink-gray-7"
    >
      <span class="size-1.5 rounded-full bg-surface-gray-6" />
      {{ label }}
      <button v-if="!disabled" class="lucide-x size-3 text-ink-gray-4 hover:text-ink-gray-7" @click="remove(label)" />
    </span>
    <input
      v-if="!disabled"
      v-model="draft"
      class="h-6 w-24 rounded border-0 bg-transparent px-1 text-sm focus:bg-surface-gray-2 focus:ring-0"
      placeholder="+ label"
      @keydown.enter.prevent="add"
      @blur="add"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({ labels: { type: Array, default: () => [] }, disabled: Boolean })
const emit = defineEmits(['change'])
const draft = ref('')

function add() {
  const label = draft.value.trim()
  draft.value = ''
  if (label && !props.labels.includes(label)) emit('change', [...props.labels, label])
}

function remove(label) {
  emit('change', props.labels.filter((l) => l !== label))
}
</script>
