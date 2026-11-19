<template>
  <!-- Who changed what on a page, newest first -->
  <aside class="flex h-full w-80 shrink-0 flex-col border-l border-outline-gray-1 bg-surface-base">
    <header class="flex h-11 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-3">
      <span class="lucide-history size-4 text-ink-gray-5" />
      <span class="text-sm font-medium text-ink-gray-8">History</span>
      <Button class="ml-auto" size="sm" variant="ghost" icon="lucide-x" @click="emit('close')" />
    </header>
    <div class="min-h-0 flex-1 overflow-y-auto px-3 py-2">
      <div v-if="!events" class="flex h-24 items-center justify-center"><LoadingIndicator class="size-4" /></div>
      <ol v-else class="relative border-l border-outline-gray-2 pl-4">
        <li v-for="(e, i) in events" :key="i" class="relative pb-4">
          <span class="absolute -left-[1.4rem] top-0.5 flex size-4 items-center justify-center rounded-full bg-surface-base">
            <span :class="ICON[e.kind] || 'lucide-dot'" class="size-3.5" :style="{ color: COLOR[e.kind] }" />
          </span>
          <div class="text-sm leading-snug text-ink-gray-7">
            <span class="font-medium text-ink-gray-9">{{ memberName(e.user) }}</span>
            <!-- server text: fixed wording with escaped values in <b> -->
            <span v-html="` ${e.text}`" />
            <span v-if="e.count > 1" class="text-ink-gray-5"> ({{ e.count }} saves)</span>
          </div>
          <div class="mt-0.5 text-xs text-ink-gray-4" :title="e.at">{{ timeAgo(e.at) }}</div>
        </li>
        <li v-if="!events.length" class="text-sm text-ink-gray-5">No changes yet.</li>
      </ol>
    </div>
  </aside>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Button, LoadingIndicator, call } from 'frappe-ui'
import { fail, memberName } from '../store'
import { timeAgo } from '../utils'

const props = defineProps({ page: { type: String, required: true }, stamp: { type: String, default: '' } })
const emit = defineEmits(['close'])

const ICON = {
  page: 'lucide-file-pen',
  text: 'lucide-pencil-line',
  lock: 'lucide-lock',
  review: 'lucide-check-check',
  add: 'lucide-plus',
  line: 'lucide-arrow-right-left',
  remove: 'lucide-minus',
}
const COLOR = { add: '#10B981', remove: '#EF4444', review: '#3B82F6', lock: '#F59E0B' }

const events = ref(null)
let timer = null
// reload when the page changes, and shortly after its last save
watch(
  () => [props.page, props.stamp],
  ([page], [oldPage] = []) => {
    if (page !== oldPage) events.value = null
    clearTimeout(timer)
    timer = setTimeout(load, page !== oldPage ? 0 : 1500)
  },
  { immediate: true },
)
async function load() {
  try {
    events.value = await call('event_planner.planner.history.page_history', { page: props.page })
  } catch (err) {
    fail(err)
  }
}
</script>
