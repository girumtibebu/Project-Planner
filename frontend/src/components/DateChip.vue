<template>
  <label
    class="relative inline-flex h-7 cursor-pointer items-center gap-1.5 rounded px-1.5 text-sm hover:bg-surface-gray-2"
    :class="[overdue ? 'text-ink-red-4' : value ? 'text-ink-gray-7' : 'text-ink-gray-4', disabled && 'pointer-events-none']"
    @click.stop
  >
    <span :class="icon" class="size-4" />
    <span>{{ value ? formatDate(value) : placeholder }}</span>
    <input
      type="date"
      class="absolute inset-0 cursor-pointer opacity-0"
      :value="dayKey(value)"
      :disabled="disabled"
      @change="onChange"
    />
  </label>
</template>

<script setup>
import { dayKey, formatDate, withDay } from '../utils'

const props = defineProps({
  value: { type: String, default: null },
  icon: { type: String, default: 'lucide-calendar' },
  placeholder: { type: String, default: 'Date' },
  overdue: Boolean,
  disabled: Boolean,
})
const emit = defineEmits(['change'])

function onChange(event) {
  const day = event.target.value
  emit('change', day ? withDay(day, props.value) : null)
}
</script>
