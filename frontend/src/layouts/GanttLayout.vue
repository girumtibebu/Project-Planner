<template>
  <div class="flex h-full min-h-0 flex-col select-none">
    <div class="flex h-10 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-4">
      <TabButtons :model-value="zoom" :buttons="ZOOMS" @update:model-value="(z) => emit('display', { zoom: z })" />
      <Button size="sm" label="Today" @click="scrollToToday" />
      <Button size="sm" :icon="allCollapsed ? 'lucide-chevrons-up-down' : 'lucide-chevrons-down-up'" :title="allCollapsed ? 'Expand all' : 'Collapse all'" @click="toggleAll" />
      <span class="ml-auto hidden text-xs text-ink-gray-5 xl:inline">
        Drag a bar to move · its ends to resize · its dot onto another bar to link · drag in an empty row to schedule or create
      </span>
    </div>

    <div class="flex min-h-0 flex-1">
      <!-- left: lanes and work items -->
      <div class="w-80 shrink-0 overflow-hidden border-r border-outline-gray-1">
        <div class="h-12 border-b border-outline-gray-1 px-3 pt-4 text-xs text-ink-gray-5">{{ groupLabel }}</div>
        <div ref="leftScroll" class="h-[calc(100%-3rem)] overflow-hidden">
          <template v-for="row in rows" :key="row.key">
            <div
              v-if="row.kind === 'group'"
              class="flex cursor-pointer items-center gap-2 border-b border-outline-gray-1 bg-surface-gray-1 px-3"
              :style="{ height: `${ROW}px` }"
              @click="toggle(row.group)"
            >
              <span :class="collapsed.has(row.group) ? 'lucide-chevron-right' : 'lucide-chevron-down'" class="size-4 text-ink-gray-5" />
              <GroupLabel :grouper="g" :k="row.group" :count="row.count" />
            </div>
            <div
              v-else-if="row.kind === 'item'"
              class="flex cursor-pointer items-center gap-2 border-b border-outline-gray-1 px-3 hover:bg-surface-gray-1"
              :style="{ height: `${ROW}px`, paddingLeft: `${row.item.parent_task ? 28 : 12}px` }"
              @click="emit('open', row.item)"
            >
              <StateIcon :state="stateOf(row.item)" />
              <span class="w-14 shrink-0 text-xs text-ink-gray-5">{{ itemId(ctx.project, row.item) }}</span>
              <span class="truncate text-sm text-ink-gray-8">{{ row.item.subject }}</span>
            </div>
            <button
              v-else
              class="flex w-full items-center gap-2 border-b border-outline-gray-1 px-3 text-left text-xs text-ink-gray-4 hover:text-ink-gray-7"
              :style="{ height: `${ROW}px` }"
              @click="emit('create', g.patch(row.group, {}, null) || {})"
            >
              <span class="lucide-plus size-3.5" /> Add work item
            </button>
          </template>
        </div>
      </div>

      <!-- right: timeline -->
      <div ref="scroller" class="min-w-0 flex-1 overflow-auto" @scroll="syncScroll">
        <div class="relative" :style="{ width: `${days.length * dayWidth}px` }">
          <!-- header -->
          <div class="sticky top-0 z-30 h-12 border-b border-outline-gray-1 bg-surface-base">
            <div class="relative h-6">
              <div
                v-for="m in months"
                :key="m.key"
                class="absolute top-0 h-6 truncate border-l border-outline-gray-1 px-2 text-xs font-medium leading-6 text-ink-gray-7"
                :style="{ left: `${m.start * dayWidth}px`, width: `${m.length * dayWidth}px` }"
              >{{ m.label }}</div>
            </div>
            <div class="relative h-6">
              <div
                v-for="(d, i) in days"
                v-show="dayWidth >= 20 || d.getDay() === 1"
                :key="i"
                class="absolute top-0 h-6 text-center text-[11px] leading-6"
                :class="dayKey(d) === today ? 'font-semibold text-ink-blue-5' : 'text-ink-gray-5'"
                :style="{ left: `${i * dayWidth}px`, width: `${Math.max(dayWidth, 20)}px` }"
              >{{ dayWidth >= 40 ? d.toLocaleDateString(undefined, { weekday: 'narrow' }) + ' ' : '' }}{{ d.getDate() }}</div>
            </div>
          </div>

          <!-- body -->
          <div class="relative" :style="{ height: `${rows.length * ROW}px` }">
            <div
              v-for="(d, i) in days"
              v-show="isWeekend(d)"
              :key="`w${i}`"
              class="absolute top-0 h-full bg-surface-gray-1"
              :style="{ left: `${i * dayWidth}px`, width: `${dayWidth}px` }"
            />
            <div
              v-if="projectStart != null"
              class="absolute top-0 h-full border-l border-dashed border-outline-gray-3"
              :style="{ left: `${projectStart * dayWidth}px` }"
              title="Project start"
            />
            <div
              v-if="projectEnd != null"
              class="absolute top-0 h-full border-r border-dashed border-outline-gray-3"
              :style="{ left: `${(projectEnd + 1) * dayWidth}px` }"
              title="Project end"
            />
            <div class="absolute top-0 z-20 h-full w-px bg-surface-red-5" :style="{ left: `${(todayIndex + 0.5) * dayWidth}px` }" />

            <div
              v-for="(row, r) in rows"
              :key="row.key"
              class="absolute left-0 w-full border-b border-outline-gray-1"
              :class="row.kind === 'group' && 'bg-surface-gray-1/70'"
              :style="{ top: `${r * ROW}px`, height: `${ROW}px` }"
              @pointerdown="row.kind !== 'group' && startRange($event, row)"
            >
              <!-- lane summary on group rows: from the earliest start to the latest end -->
              <div
                v-if="row.kind === 'group' && row.summary"
                class="absolute top-3.5 h-2 rounded-full opacity-40"
                :style="{ left: `${row.summary.start * dayWidth}px`, width: `${(row.summary.end - row.summary.start + 1) * dayWidth}px`, background: g.color?.(row.group) || '#6B7280' }"
              />
              <div
                v-if="range && range.row === row.key"
                class="absolute top-1.5 h-6 rounded border border-dashed border-outline-blue-3 bg-surface-blue-1"
                :style="{ left: `${Math.min(range.a, range.b) * dayWidth}px`, width: `${(Math.abs(range.b - range.a) + 1) * dayWidth}px` }"
              />
              <template v-if="row.kind === 'item' && bar(row.item)">
                <div
                  v-if="row.item.is_milestone"
                  class="absolute top-2 z-10 size-4 rotate-45 cursor-grab rounded-sm"
                  :style="{ left: `${(bar(row.item).end + 0.5) * dayWidth - 8}px`, background: barColor(row.item) }"
                  :title="row.item.subject"
                  @pointerdown.stop="startMove($event, row.item, 'move')"
                  @pointerup="finishLink(row.item)"
                  @click.stop="clickItem(row.item)"
                />
                <div
                  v-else
                  class="group absolute top-1 z-10 flex h-7 cursor-grab items-center rounded-lg px-2.5 text-ink-gray-9 transition-shadow hover:shadow-md"
                  :class="dragging === row.item.name && 'ring-2 ring-outline-gray-4'"
                  :style="barStyle(row.item)"
                  :title="`${row.item.subject}: ${formatDate(row.item.exp_start_date)} – ${formatDate(row.item.exp_end_date)}`"
                  @pointerdown.stop="startMove($event, row.item, 'move')"
                  @pointerup="finishLink(row.item)"
                  @click.stop="clickItem(row.item)"
                >
                  <span v-if="ctx.can.write" class="absolute left-0 top-0 h-full w-2 cursor-ew-resize rounded-l-lg" @pointerdown.stop="startMove($event, row.item, 'start')" />
                  <ItemCard :item="row.item" :fields="cardFields" compact class="min-w-0 flex-1" />
                  <span v-if="ctx.can.write" class="absolute right-0 top-0 h-full w-2 cursor-ew-resize rounded-r-lg" @pointerdown.stop="startMove($event, row.item, 'end')" />
                  <span
                    v-if="ctx.can.write"
                    class="absolute -right-3.5 top-2 size-3 cursor-crosshair rounded-full border-2 border-white bg-surface-gray-7 opacity-0 group-hover:opacity-100"
                    title="Drag onto the work item that depends on this one"
                    @pointerdown.stop="startLink(row.item)"
                  />
                </div>
              </template>
            </div>

            <svg class="pointer-events-none absolute left-0 top-0 z-0" :width="days.length * dayWidth" :height="rows.length * ROW">
              <defs>
                <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto">
                  <path d="M0 0 8 4 0 8z" fill="#9CA3AF" />
                </marker>
              </defs>
              <path v-for="link in links" :key="link.key" :d="link.d" fill="none" stroke="#9CA3AF" stroke-width="1.4" marker-end="url(#arrow)" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { Button, TabButtons, toast } from 'frappe-ui'
import GroupLabel from '../components/GroupLabel.vue'
import ItemCard from '../components/ItemCard.vue'
import StateIcon from '../components/StateIcon.vue'
import { GROUP_BY, grouper } from '../grouping'
import { startDrag } from '../pointer'
import { ctx, groupIndex, stateOf, typeIndex } from '../store'
import { addDays, dayKey, diffDays, formatDate, groupItems, itemId, toDate, withDay } from '../utils'

const props = defineProps({
  items: { type: Array, default: () => [] },
  groupBy: { type: String, default: 'group' },
  display: { type: Object, default: () => ({}) },
  cardFields: { type: Array, default: () => [] },
})
const emit = defineEmits(['open', 'save', 'create', 'display'])

const ROW = 36
const ZOOMS = [
  { label: 'Day', value: 'day' },
  { label: 'Week', value: 'week' },
  { label: 'Month', value: 'month' },
  { label: 'Quarter', value: 'quarter' },
]
const WIDTH = { day: 64, week: 30, month: 14, quarter: 6 }
const zoom = computed(() => props.display.zoom || 'week')
const dayWidth = computed(() => WIDTH[zoom.value] || 30)
const today = dayKey(new Date())

const g = computed(() => grouper(props.groupBy))
const groupLabel = computed(() => (props.groupBy === 'none' ? 'Work items' : `Lanes by ${GROUP_BY.find((x) => x.value === props.groupBy)?.label.toLowerCase()}`))

// lanes
const collapsed = reactive(new Set())
const toggle = (key) => (collapsed.has(key) ? collapsed.delete(key) : collapsed.add(key))
const groups = computed(() => [...groupItems(props.items, g.value.keyOf, g.value.keys()).entries()])
const allCollapsed = computed(() => groups.value.length > 0 && groups.value.every(([k]) => collapsed.has(k)))
function toggleAll() {
  if (allCollapsed.value) collapsed.clear()
  else groups.value.forEach(([k]) => collapsed.add(k))
}

const rows = computed(() => {
  const out = []
  const noGroups = props.groupBy === 'none'
  for (const [key, list] of groups.value) {
    if (!list.length && !noGroups && g.value.keys().length > 8) continue
    if (!noGroups) out.push({ kind: 'group', key: `g:${key}`, group: key, count: list.length, summary: summary(list) })
    if (collapsed.has(key) && !noGroups) continue
    for (const item of list) out.push({ kind: 'item', key: `i:${key}:${item.name}`, item, group: key })
    if (ctx.can.write) out.push({ kind: 'add', key: `a:${key}`, group: key })
  }
  return out
})

function summary(list) {
  const bars = list.map(bar).filter(Boolean)
  if (!bars.length) return null
  return { start: Math.min(...bars.map((b) => b.start)), end: Math.max(...bars.map((b) => b.end)) }
}

// time axis
const range0 = computed(() => {
  const dates = [new Date(), toDate(ctx.project?.expected_start_date), toDate(ctx.project?.expected_end_date)]
  for (const item of props.items) dates.push(toDate(item.exp_start_date), toDate(item.exp_end_date))
  const known = dates.filter(Boolean).map((d) => d.getTime())
  const start = addDays(new Date(Math.min(...known)), -14)
  const end = addDays(new Date(Math.max(...known)), 45)
  return { start, length: diffDays(start, end) + 1 }
})
const days = computed(() => Array.from({ length: range0.value.length }, (_, i) => addDays(range0.value.start, i)))
const todayIndex = computed(() => diffDays(range0.value.start, new Date()))
const projectStart = computed(() => (ctx.project?.expected_start_date ? diffDays(range0.value.start, ctx.project.expected_start_date) : null))
const projectEnd = computed(() => (ctx.project?.expected_end_date ? diffDays(range0.value.start, ctx.project.expected_end_date) : null))
const isWeekend = (d) => d.getDay() === 0 || d.getDay() === 6
const months = computed(() => {
  const out = []
  days.value.forEach((d, i) => {
    const key = `${d.getFullYear()}-${d.getMonth()}`
    if (!out.length || out[out.length - 1].key !== key) {
      out.push({ key, start: i, length: 0, label: d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }) })
    }
    out[out.length - 1].length++
  })
  return out
})

// bars
const preview = ref({})
function bar(item) {
  const p = preview.value[item.name]
  const s = toDate(p?.start ?? item.exp_start_date)
  const e = toDate(p?.end ?? item.exp_end_date)
  if (!s && !e) return null
  const a = diffDays(range0.value.start, s || e)
  const b = diffDays(range0.value.start, e || s)
  return { start: Math.min(a, b), end: Math.max(a, b) }
}

const COLOR_BY = {
  state: (item) => stateOf(item).color,
  group: (item) => groupIndex.value[item.ep_action_category]?.color,
  type: (item) => typeIndex.value[item.type]?.ep_color,
  priority: (item) => ({ Urgent: '#EF4444', High: '#F59E0B', Medium: '#6B7280', Low: '#9CA3AF' })[item.priority],
}
const barColor = (item) => (COLOR_BY[props.display.bar_color || 'state'] || COLOR_BY.state)(item) || '#6B7280'
function barStyle(item) {
  const b = bar(item)
  const c = barColor(item)
  return {
    left: `${b.start * dayWidth.value + 1}px`,
    width: `${Math.max(1, b.end - b.start + 1) * dayWidth.value - 2}px`,
    background: `${c}24`,
    border: `1px solid ${c}59`,
  }
}

// move / resize
const dragging = ref(null)
let justDragged = false
function startMove(event, item, mode) {
  if (!ctx.can.write || linkFrom.value) return
  const start0 = item.exp_start_date || item.exp_end_date
  const end0 = item.exp_end_date || item.exp_start_date
  dragging.value = item.name
  startDrag(event, {
    onMove(dx) {
      const delta = Math.round(dx / dayWidth.value)
      let s = toDate(start0)
      let e = toDate(end0)
      if (mode === 'move') {
        s = addDays(s, delta)
        e = addDays(e, delta)
      } else if (mode === 'start') {
        s = addDays(s, delta)
        if (s > e) s = e
      } else {
        e = addDays(e, delta)
        if (e < s) e = s
      }
      preview.value = { ...preview.value, [item.name]: { start: s, end: e } }
    },
    onEnd(dx, dy, moved) {
      dragging.value = null
      const p = preview.value[item.name]
      if (moved && p) {
        justDragged = true
        setTimeout(() => (justDragged = false), 50)
        emit('save', item, { exp_start_date: withDay(p.start, item.exp_start_date), exp_end_date: withDay(p.end, item.exp_end_date) })
      }
      setTimeout(() => {
        const next = { ...preview.value }
        delete next[item.name]
        preview.value = next
      }, 600)
    },
  })
}
function clickItem(item) {
  if (!justDragged) emit('open', item)
}

// drag across an empty row: schedule an undated item, or create one in that lane
const range = ref(null)
const scroller = ref(null)
function startRange(event, row) {
  if (!ctx.can.write || (row.kind === 'item' && bar(row.item))) return
  const rect = event.currentTarget.getBoundingClientRect()
  const dayAt = (x) => Math.floor((x - rect.left) / dayWidth.value)
  const a = dayAt(event.clientX)
  range.value = { row: row.key, a, b: a }
  startDrag(event, {
    threshold: 0,
    onMove(dx, dy, e) {
      range.value = { row: row.key, a, b: dayAt(e.clientX) }
    },
    onEnd() {
      const { a: x, b: y } = range.value
      range.value = null
      const start = addDays(range0.value.start, Math.min(x, y))
      const end = addDays(range0.value.start, Math.max(x, y))
      const dates = { exp_start_date: withDay(start), exp_end_date: withDay(end) }
      if (row.kind === 'item') emit('save', row.item, dates)
      else emit('create', { ...(g.value.patch(row.group, {}, null) || {}), ...dates })
    },
  })
}

// dependency links
const linkFrom = ref(null)
function startLink(item) {
  linkFrom.value = item
  window.addEventListener('pointerup', () => setTimeout(() => (linkFrom.value = null), 0), { once: true })
}
function finishLink(target) {
  const source = linkFrom.value
  if (!source || source.name === target.name) return
  if (target.depends_on.includes(source.name)) return toast.info('That dependency exists already')
  emit('save', target, { depends_on: [...target.depends_on, source.name] })
}

const links = computed(() => {
  const index = {}
  rows.value.forEach((row, r) => {
    if (row.kind === 'item' && index[row.item.name] == null) index[row.item.name] = r
  })
  const out = []
  rows.value.forEach((row, r) => {
    if (row.kind !== 'item') return
    const to = bar(row.item)
    if (!to) return
    for (const dep of row.item.depends_on || []) {
      const fromRow = index[dep]
      const from = fromRow != null && bar(rows.value[fromRow].item)
      if (!from) continue
      const x1 = (from.end + 1) * dayWidth.value
      const y1 = fromRow * ROW + ROW / 2
      const x2 = to.start * dayWidth.value
      const y2 = r * ROW + ROW / 2
      const mid = Math.max(x1 + 8, x2 - 8)
      out.push({ key: `${dep}>${row.item.name}`, d: `M${x1} ${y1} H${mid} V${y2} H${x2}` })
    }
  })
  return out
})

// scrolling
const leftScroll = ref(null)
function syncScroll() {
  if (leftScroll.value) leftScroll.value.scrollTop = scroller.value.scrollTop
}
function scrollToToday() {
  scroller.value?.scrollTo({ left: Math.max(0, (todayIndex.value - 7) * dayWidth.value), behavior: 'smooth' })
}
onMounted(() => nextTick(scrollToToday))
</script>
