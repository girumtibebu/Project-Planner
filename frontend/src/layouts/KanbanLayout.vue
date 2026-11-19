<template>
  <div class="h-full overflow-auto p-4">
    <!-- one board per swimlane (or one board) -->
    <section v-for="lane in lanes" :key="lane.key" class="mb-4">
      <header v-if="swimlanes !== 'none'" class="sticky left-0 mb-2 flex items-center gap-2">
        <button class="text-ink-gray-5" @click="toggleLane(lane.key)">
          <span :class="collapsedLanes.has(lane.key) ? 'lucide-chevron-right' : 'lucide-chevron-down'" class="size-4" />
        </button>
        <GroupLabel :grouper="laneGrouper" :k="lane.key" :count="lane.count" />
      </header>

      <div v-if="!collapsedLanes.has(lane.key)" class="flex items-start gap-3">
        <template v-for="col in columns" :key="col">
          <!-- folded column -->
          <button
            v-if="folded.has(col)"
            class="flex w-10 shrink-0 flex-col items-center gap-2 rounded-2xl bg-surface-gray-1 py-3 hover:bg-surface-gray-2"
            :style="{ minHeight: swimlanes === 'none' ? 'calc(100vh - 12rem)' : '8rem' }"
            @click="folded.delete(col)"
            @dragover.prevent
            @drop.prevent="drop(col, lane.key, null)"
          >
            <span class="text-xs text-ink-gray-5">{{ cards(lane, col).length }}</span>
            <span class="text-sm font-medium text-ink-gray-7 [writing-mode:vertical-rl]">{{ g.label(col) }}</span>
          </button>

          <section
            v-else
            class="flex w-72 shrink-0 flex-col rounded-2xl bg-surface-gray-1"
            :class="over?.col === col && over?.lane === lane.key && 'ring-2 ring-outline-gray-3'"
            :style="{ minHeight: swimlanes === 'none' ? 'calc(100vh - 12rem)' : '8rem' }"
            @dragover.prevent="over = { col, lane: lane.key, before: over?.before ?? null }"
            @dragleave.self="over = null"
            @drop.prevent="drop(col, lane.key, over?.before)"
          >
            <header class="group flex h-10 shrink-0 items-center gap-1 px-3">
              <GroupHeader :grouper="g" :group-by="groupBy" :k="col" :count="cards(lane, col).length" />
              <div class="ml-auto flex items-center opacity-0 group-hover:opacity-100">
                <Tooltip text="Fold column"><Button size="sm" variant="ghost" icon="lucide-fold-horizontal" @click="folded.add(col)" /></Tooltip>
                <Tooltip v-if="ctx.can.write" text="New work item here">
                  <Button size="sm" variant="ghost" icon="lucide-plus" @click="emit('create', defaults(col, lane.key))" />
                </Tooltip>
              </div>
            </header>
            <div class="flex flex-1 flex-col gap-2 px-2 pb-2">
              <article
                v-for="item in cards(lane, col)"
                :key="item.name"
                class="cursor-pointer rounded-xl border bg-surface-base p-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition hover:shadow-md"
                :class="[
                  dragging?.item.name === item.name ? 'opacity-40' : '',
                  over?.before === item.name && over?.col === col && over?.lane === lane.key ? 'border-t-2 border-t-outline-gray-5' : 'border-outline-gray-1',
                ]"
                :draggable="ctx.can.write"
                @dragstart="dragging = { item, col, lane: lane.key }"
                @dragend="dragging = null; over = null"
                @dragover.prevent.stop="over = { col, lane: lane.key, before: item.name }"
                @click="emit('open', item)"
              >
                <ItemCard :item="item" :fields="cardFields" :hide="hidden" @save="(d) => emit('save', item, d)" />
              </article>
              <QuickAdd :defaults="defaults(col, lane.key)" @created="(item) => emit('created', item)" />
            </div>
          </section>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { Button, Tooltip } from 'frappe-ui'
import GroupHeader from '../components/GroupHeader.vue'
import GroupLabel from '../components/GroupLabel.vue'
import ItemCard from '../components/ItemCard.vue'
import QuickAdd from '../components/QuickAdd.vue'
import { grouper } from '../grouping'
import { ctx } from '../store'
import { groupItems } from '../utils'

const props = defineProps({
  items: { type: Array, default: () => [] },
  groupBy: { type: String, default: 'state' },
  display: { type: Object, default: () => ({}) },
  cardFields: { type: Array, default: () => [] },
})
const emit = defineEmits(['open', 'save', 'created', 'create', 'reorder'])

const by = computed(() => (props.groupBy === 'none' ? 'state' : props.groupBy))
const g = computed(() => grouper(by.value))
const swimlanes = computed(() => props.display.swimlanes || 'none')
const laneGrouper = computed(() => grouper(swimlanes.value))
// the column already says the state (or priority…), so the card need not repeat it
const hidden = computed(() => ({ state: ['state'], state_group: ['state'], priority: ['priority'], type: ['type'], group: ['group'], assignee: ['assignees'] })[by.value] || [])

const lanes = computed(() => {
  if (swimlanes.value === 'none') return [{ key: 'all', items: props.items, count: props.items.length }]
  return [...groupItems(props.items, laneGrouper.value.keyOf, laneGrouper.value.keys()).entries()]
    .filter(([, list]) => list.length)
    .map(([key, list]) => ({ key, items: list, count: list.length }))
})

const allColumns = computed(() => [...groupItems(props.items, g.value.keyOf, g.value.keys()).keys()])
const columns = computed(() =>
  props.display.hide_empty ? allColumns.value.filter((col) => props.items.some((i) => [].concat(g.value.keyOf(i)).includes(col))) : allColumns.value,
)

/** Cards of one column in one lane, in manual order when that is the view's order. */
function cards(lane, col) {
  return lane.items.filter((item) => {
    const keys = [].concat(g.value.keyOf(item))
    return keys.length ? keys.includes(col) : col === ''
  })
}

const folded = reactive(new Set())
const collapsedLanes = reactive(new Set())
const toggleLane = (key) => (collapsedLanes.has(key) ? collapsedLanes.delete(key) : collapsedLanes.add(key))

function defaults(col, lane) {
  return { ...(g.value.patch(col, {}, null) || {}), ...(swimlanes.value !== 'none' ? laneGrouper.value.patch(lane, {}, null) || {} : {}) }
}

const dragging = ref(null)
const over = ref(null)

function drop(col, lane, before) {
  const current = dragging.value
  dragging.value = null
  over.value = null
  if (!current) return
  const { item } = current
  const patch = {}
  if (current.col !== col) Object.assign(patch, g.value.patch(col, item, current.col) || {})
  if (swimlanes.value !== 'none' && current.lane !== lane) Object.assign(patch, laneGrouper.value.patch(lane, item, current.lane) || {})
  if (Object.keys(patch).length) emit('save', item, patch)

  // new manual order of the target column
  const target = cards(lanes.value.find((l) => l.key === lane) || lanes.value[0], col).filter((i) => i.name !== item.name)
  const at = before ? target.findIndex((i) => i.name === before) : -1
  target.splice(at < 0 ? target.length : at, 0, item)
  emit('reorder', target.map((i) => i.name))
}
</script>
