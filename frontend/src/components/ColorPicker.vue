<template>
  <!-- Colour: a palette, any custom colour, and a preview of how it shows -->
  <Popover align="start">
    <!-- the popover's trigger opens on its own click; `toggle` is a no-op for callers -->
    <template #trigger>
      <slot :toggle="noop" :color="modelValue">
        <button class="flex h-7 items-center gap-1.5 rounded-md px-1.5 text-sm hover:bg-surface-gray-2" :title="modelValue || 'No colour'">
          <span class="size-4 rounded-full ring-1 ring-black/10" :style="{ background: modelValue || 'transparent' }" :class="!modelValue && 'border border-dashed border-outline-gray-3'" />
          <span class="lucide-chevron-down size-3 text-ink-gray-4" />
        </button>
      </slot>
    </template>
    <template #default="{ close }">
      <div class="w-64 p-3" @click.stop>
        <!-- preview -->
        <div class="mb-3 flex items-center gap-2 rounded-lg border border-outline-gray-1 px-2.5 py-2">
          <span :class="icon" class="size-4" :style="{ color: draft || '#9CA3AF' }" />
          <span class="truncate text-sm font-medium text-ink-gray-8">{{ label || 'Preview' }}</span>
          <span class="ml-auto rounded-full px-2 py-0.5 text-xs font-medium" :style="chip">{{ label || 'Tag' }}</span>
        </div>

        <div v-for="row in PALETTE" :key="row[0]" class="mb-1.5 grid grid-cols-8 gap-1.5">
          <button
            v-for="c in row"
            :key="c"
            class="flex size-6 items-center justify-center rounded-full ring-offset-1 transition hover:scale-110"
            :class="same(c) && 'ring-2 ring-outline-gray-7'"
            :style="{ background: c }"
            :title="c"
            @click="pick(c, close)"
          >
            <span v-if="same(c)" class="lucide-check size-3.5 text-white" />
          </button>
        </div>

        <div class="mt-3 flex items-center gap-2 border-t border-outline-gray-1 pt-3">
          <label class="relative size-7 shrink-0 cursor-pointer overflow-hidden rounded-full ring-1 ring-black/10" :style="{ background: draft || '#ffffff' }" title="Any colour">
            <span v-if="!draft" class="lucide-palette absolute inset-1.5 text-ink-gray-5" />
            <input type="color" class="absolute inset-0 cursor-pointer opacity-0" :value="draft || '#3B82F6'" @input="(e) => (draft = e.target.value.toUpperCase())" @change="commit" />
          </label>
          <input
            v-model="draft"
            class="h-7 min-w-0 flex-1 rounded-md border-0 bg-surface-gray-2 px-2 font-mono text-sm uppercase focus:ring-1 focus:ring-outline-gray-3"
            placeholder="#3B82F6"
            maxlength="7"
            @keydown.enter="commit() || close()"
            @blur="commit"
          />
          <button v-if="clearable" class="rounded p-1 text-ink-gray-4 hover:bg-surface-gray-2 hover:text-ink-gray-8" title="No colour" @click="pick('', close)">
            <span class="lucide-ban block size-4" />
          </button>
        </div>
      </div>
    </template>
  </Popover>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Popover } from 'frappe-ui'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: '' }, // shown in the preview
  icon: { type: String, default: 'lucide-boxes' },
  clearable: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'change'])
const noop = () => {}

// 500 and 700 shades of each hue, then greys
const PALETTE = [
  ['#EF4444', '#F97316', '#F59E0B', '#EAB308', '#84CC16', '#22C55E', '#10B981', '#14B8A6'],
  ['#06B6D4', '#0EA5E9', '#3B82F6', '#6366F1', '#8B5CF6', '#A855F7', '#D946EF', '#EC4899'],
  ['#B91C1C', '#C2410C', '#B45309', '#A16207', '#4D7C0F', '#15803D', '#047857', '#0F766E'],
  ['#0E7490', '#0369A1', '#1D4ED8', '#4338CA', '#6D28D9', '#7E22CE', '#A21CAF', '#BE185D'],
  ['#F43F5E', '#78716C', '#6B7280', '#9CA3AF', '#475569', '#334155', '#1F2937', '#000000'],
]

const draft = ref(props.modelValue || '')
watch(
  () => props.modelValue,
  (v) => (draft.value = v || ''),
)
const same = (c) => (props.modelValue || '').toUpperCase() === c.toUpperCase()
const chip = computed(() => (draft.value ? { background: `${draft.value}22`, color: draft.value } : { background: '#F3F4F6', color: '#6B7280' }))

function pick(color, close) {
  draft.value = color
  emit('update:modelValue', color)
  emit('change', color)
  close?.()
}
function commit() {
  const v = draft.value.trim()
  if (v === (props.modelValue || '')) return
  if (v && !/^#[0-9a-fA-F]{6}$/.test(v)) return (draft.value = props.modelValue || '')
  pick(v.toUpperCase())
}
</script>
