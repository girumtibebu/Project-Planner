<template>
  <!-- A searchable option list in a popover, single or multiple choice -->
  <Popover align="start" @update:open="(o) => (o ? (query = '') : null)">
    <!-- the popover's trigger opens on its own click; `toggle` stays a no-op so callers' @click="toggle" does not close it again -->
    <template #trigger>
      <slot :toggle="noop">
        <Button variant="ghost" size="sm">{{ selectedLabel || placeholder }}</Button>
      </slot>
    </template>
    <template #default="{ close }">
      <div class="w-60 p-1" @click.stop>
        <input
          v-if="options.length > 6 || creatable"
          v-model="query"
          class="mb-1 w-full rounded-md border-0 bg-surface-gray-2 px-2 py-1 text-sm focus:ring-1 focus:ring-outline-gray-3"
          :placeholder="creatable ? `Search or create ${label.toLowerCase()}…` : `Search ${label.toLowerCase()}…`"
          @keydown.enter="canCreate && create(close)"
        />
        <div class="max-h-72 overflow-y-auto">
          <button
            v-for="option in filtered"
            :key="option.value"
            class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2"
            @click="choose(option, close)"
          >
            <slot name="option" :option="option">
              <span v-if="option.iconClass" :class="option.iconClass" class="size-4" :style="{ color: option.color }" />
            </slot>
            <span class="min-w-0 flex-1 truncate">{{ option.label }}</span>
            <span v-if="isSelected(option)" class="lucide-check size-4 text-ink-gray-7" />
          </button>
          <div v-if="!filtered.length && !canCreate" class="px-2 py-1.5 text-sm text-ink-gray-4">No match</div>
        </div>
        <button
          v-if="canCreate"
          class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2"
          @click="create(close)"
        >
          <span class="lucide-plus size-4 text-ink-gray-5" /> Create “{{ query.trim() }}”
        </button>
        <button
          v-if="clearable && hasValue"
          class="mt-1 w-full rounded border-t border-outline-gray-1 px-2 py-1.5 text-left text-sm text-ink-gray-5 hover:bg-surface-gray-2"
          @click="clear(close)"
        >
          Clear
        </button>
      </div>
    </template>
  </Popover>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Button, Popover } from 'frappe-ui'

const props = defineProps({
  modelValue: { type: [String, Number, Array, Boolean], default: null },
  options: { type: Array, default: () => [] }, // [{ value, label, iconClass?, color? }]
  multiple: { type: Boolean, default: false },
  clearable: { type: Boolean, default: false },
  label: { type: String, default: 'Option' },
  placeholder: { type: String, default: 'Select' },
  creatable: { type: Boolean, default: false }, // offer "Create …" for a new name; the parent handles @create
})
const emit = defineEmits(['update:modelValue', 'change', 'create'])
const noop = () => {}

const canCreate = computed(() => {
  const q = query.value.trim().toLowerCase()
  return props.creatable && q && !props.options.some((o) => String(o.label).toLowerCase() === q)
})
function create(close) {
  emit('create', query.value.trim())
  close()
}
const query = ref('')

const values = computed(() => (props.multiple ? props.modelValue || [] : props.modelValue == null ? [] : [props.modelValue]))
const hasValue = computed(() => values.value.length > 0)
const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  return q ? props.options.filter((o) => String(o.label).toLowerCase().includes(q)) : props.options
})
const selectedLabel = computed(() =>
  props.options.filter((o) => values.value.includes(o.value)).map((o) => o.label).join(', '),
)

const isSelected = (option) => values.value.includes(option.value)

function choose(option, close) {
  let next = option.value
  if (props.multiple) {
    next = isSelected(option) ? values.value.filter((v) => v !== option.value) : [...values.value, option.value]
  } else {
    close()
  }
  emit('update:modelValue', next)
  emit('change', next)
}

function clear(close) {
  const next = props.multiple ? [] : null
  emit('update:modelValue', next)
  emit('change', next)
  close()
}
</script>
