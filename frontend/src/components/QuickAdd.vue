<template>
  <div v-if="ctx.can.write">
    <button
      v-if="!open"
      class="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-ink-gray-4 hover:bg-surface-gray-2 hover:text-ink-gray-7"
      @click="start"
    >
      <span class="lucide-plus size-4" /> New work item
    </button>
    <div v-else class="flex items-center gap-2 rounded-xl border border-outline-gray-2 bg-surface-base px-2.5 py-1 shadow-sm">
      <span class="lucide-circle-dashed size-4 text-ink-gray-4" />
      <input
        ref="input"
        v-model="title"
        class="h-7 flex-1 border-0 bg-transparent p-0 text-sm focus:ring-0"
        placeholder="Work item title, Enter to add, Esc to stop"
        @keydown.enter.prevent="submit"
        @keydown.esc="open = false"
        @blur="!title && (open = false)"
      />
      <LoadingIndicator v-if="busy" class="size-4" />
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { LoadingIndicator } from 'frappe-ui'
import { api } from '../api'
import { ctx, fail } from '../store'

const props = defineProps({ defaults: { type: Object, default: () => ({}) } })
const emit = defineEmits(['created'])
const open = ref(false)
const title = ref('')
const busy = ref(false)
const input = ref(null)

async function start() {
  open.value = true
  await nextTick()
  input.value?.focus()
}

async function submit() {
  const subject = title.value.trim()
  if (!subject || busy.value) return
  busy.value = true
  try {
    const item = await api.createItem(ctx.project.name, { ...props.defaults, subject })
    title.value = ''
    emit('created', item)
  } catch (err) {
    fail(err)
  } finally {
    busy.value = false
    input.value?.focus()
  }
}
</script>
