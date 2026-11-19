<template>
  <div class="flex h-full min-h-0 flex-col select-none">
    <!-- toolbar -->
    <div class="flex h-10 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-4">
      <TabButtons :model-value="mode" :buttons="MODES" @update:model-value="setMode" />
      <Button size="sm" icon="lucide-chevron-left" @click="shift(-1)" />
      <Button size="sm" label="Today" @click="cursor = new Date()" />
      <Button size="sm" icon="lucide-chevron-right" @click="shift(1)" />
      <span class="ml-2 text-base font-medium text-ink-gray-8">{{ title }}</span>
      <span class="ml-auto hidden text-xs text-ink-gray-5 lg:inline">
        Drag to move · drag an edge to change length · drag on empty space to create
      </span>
    </div>

    <!-- MONTH -->
    <template v-if="mode === 'month'">
      <div class="grid shrink-0 grid-cols-7 border-b border-outline-gray-1 text-xs text-ink-gray-5">
        <div v-for="d in WEEKDAYS" :key="d" class="px-2 py-1">{{ d }}</div>
      </div>
      <div ref="monthEl" class="min-h-0 flex-1 overflow-y-auto">
        <div v-for="(week, w) in weeks" :key="w" class="relative grid grid-cols-7 border-b border-outline-gray-1" :style="{ height: `${MONTH_ROW}px` }">
          <div
            v-for="(day, c) in week.days"
            :key="day.key"
            class="relative border-r border-outline-gray-1"
            :class="[day.inMonth ? '' : 'bg-surface-gray-1', inSelection(day.key) && '!bg-surface-blue-1']"
            @pointerdown="startSelect($event, day.date)"
            @pointerenter="extendSelect(day.date)"
          >
            <div class="flex items-center justify-between px-1.5 pt-1">
              <button
                class="rounded-full px-1.5 text-xs"
                :class="day.key === today ? 'bg-surface-gray-7 text-ink-white' : day.inMonth ? 'text-ink-gray-7' : 'text-ink-gray-4'"
                @pointerdown.stop
                @click="openDay(day.date)"
              >{{ day.date.getDate() }}</button>
              <button
                v-if="week.hidden[c]"
                class="text-[11px] text-ink-gray-5 hover:underline"
                @pointerdown.stop
                @click="openDay(day.date)"
              >+{{ week.hidden[c] }} more</button>
            </div>
          </div>
          <!-- bars -->
          <div
            v-for="seg in week.segments"
            :key="seg.item.name + w"
            class="absolute z-10 cursor-grab overflow-hidden rounded-md px-1.5"
            :class="dragging?.item.name === seg.item.name && 'opacity-60'"
            :style="segStyle(seg, 7, 24 + seg.lane * (LANE + 2))"
            @pointerdown.stop="startMove($event, seg.item, 'days')"
            @click.stop="clickItem(seg.item)"
          >
            <ItemCard :item="seg.item" :fields="cardFields" compact />
            <span v-if="ctx.can.write && seg.isEnd" class="absolute right-0 top-0 h-full w-1.5 cursor-ew-resize" @pointerdown.stop="startResize($event, seg.item, 'days')" />
          </div>
        </div>
      </div>
    </template>

    <!-- WEEK / DAY -->
    <template v-else>
      <div class="flex shrink-0 border-b border-outline-gray-1">
        <div class="w-14 shrink-0" />
        <div class="grid flex-1" :style="{ gridTemplateColumns: `repeat(${days.length}, minmax(0, 1fr))` }">
          <button
            v-for="d in days"
            :key="dayKey(d)"
            class="border-l border-outline-gray-1 py-1 text-center text-xs"
            :class="dayKey(d) === today ? 'font-semibold text-ink-blue-5' : 'text-ink-gray-6'"
            @click="openDay(d)"
          >
            {{ d.toLocaleDateString(undefined, { weekday: 'short' }) }} <span class="text-sm">{{ d.getDate() }}</span>
          </button>
        </div>
      </div>
      <!-- all-day lane -->
      <div class="flex shrink-0 border-b border-outline-gray-1">
        <div class="w-14 shrink-0 py-1 pr-1 text-right text-[11px] text-ink-gray-4">all-day</div>
        <div ref="allDayEl" class="relative flex-1" :style="{ height: `${Math.max(1, allDay.lanes) * (LANE + 2) + 6}px` }">
          <div class="absolute inset-0 grid" :style="{ gridTemplateColumns: `repeat(${days.length}, minmax(0, 1fr))` }">
            <div
              v-for="d in days"
              :key="dayKey(d)"
              class="border-l border-outline-gray-1"
              :class="inSelection(dayKey(d)) && 'bg-surface-blue-1'"
              @pointerdown="startSelect($event, d)"
              @pointerenter="extendSelect(d)"
            />
          </div>
          <div
            v-for="seg in allDay.segments"
            :key="seg.item.name"
            class="absolute z-10 cursor-grab overflow-hidden rounded-md px-1.5"
            :style="segStyle(seg, days.length, 3 + seg.lane * (LANE + 2))"
            @pointerdown.stop="startMove($event, seg.item, 'days')"
            @click.stop="clickItem(seg.item)"
          >
            <ItemCard :item="seg.item" :fields="cardFields" compact />
            <span v-if="ctx.can.write && seg.isEnd" class="absolute right-0 top-0 h-full w-1.5 cursor-ew-resize" @pointerdown.stop="startResize($event, seg.item, 'days')" />
          </div>
        </div>
      </div>
      <!-- time grid -->
      <div ref="gridScroll" class="min-h-0 flex-1 overflow-y-auto">
        <div class="relative flex" :style="{ height: `${24 * HOUR}px` }">
          <div class="w-14 shrink-0">
            <div v-for="h in 24" :key="h" class="relative text-right text-[11px] text-ink-gray-4" :style="{ height: `${HOUR}px` }">
              <span v-if="h > 1" class="absolute -top-2 right-1">{{ minLabel((h - 1) * 60) }}</span>
            </div>
          </div>
          <div ref="gridEl" class="relative grid flex-1" :style="{ gridTemplateColumns: `repeat(${days.length}, minmax(0, 1fr))` }">
            <div
              v-for="(d, c) in days"
              :key="dayKey(d)"
              class="relative border-l border-outline-gray-1"
              @pointerdown="startTimeSelect($event, c)"
            >
              <div v-for="h in 24" :key="h" class="border-b border-outline-gray-1" :style="{ height: `${HOUR}px` }" />
              <div v-if="dayKey(d) === today" class="absolute left-0 right-0 z-20 h-px bg-surface-red-5" :style="{ top: `${(nowMinutes * HOUR) / 60}px` }" />
              <div
                v-if="timeSel && timeSel.col === c"
                class="absolute left-1 right-1 z-10 rounded bg-surface-blue-2 px-1 text-[11px] text-ink-blue-6 opacity-80"
                :style="{ top: `${(Math.min(timeSel.a, timeSel.b) * HOUR) / 60}px`, height: `${(Math.abs(timeSel.b - timeSel.a) * HOUR) / 60}px` }"
              >{{ minLabel(Math.min(timeSel.a, timeSel.b)) }}–{{ minLabel(Math.max(timeSel.a, timeSel.b)) }}</div>
              <div
                v-for="ev in timedByDay[c] || []"
                :key="ev.item.name"
                class="absolute z-10 cursor-grab overflow-hidden rounded-lg border-l-[3px] px-2 py-1 transition-shadow hover:shadow-md"
                :class="dragging?.item.name === ev.item.name && 'opacity-60'"
                :style="timedStyle(ev)"
                @pointerdown.stop="startMove($event, ev.item, 'time')"
                @click.stop="clickItem(ev.item)"
              >
                <ItemCard :item="ev.item" :fields="cardFields" compact />
                <div v-if="ev.height > 34" class="text-[11px] opacity-70">{{ minLabel(ev.start) }}–{{ minLabel(ev.end) }}</div>
                <span v-if="ctx.can.write" class="absolute bottom-0 left-0 h-1.5 w-full cursor-ns-resize" @pointerdown.stop="startResize($event, ev.item, 'time')" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Button, TabButtons } from 'frappe-ui'
import ItemCard from '../components/ItemCard.vue'
import { startDrag } from '../pointer'
import { ctx, stateOf } from '../store'
import { addDays, dayKey, diffDays, toDate } from '../utils'

const props = defineProps({
  items: { type: Array, default: () => [] },
  display: { type: Object, default: () => ({}) },
  cardFields: { type: Array, default: () => [] },
})
const emit = defineEmits(['open', 'save', 'create', 'display'])

const MODES = [
  { label: 'Day', value: 'day' },
  { label: 'Week', value: 'week' },
  { label: 'Month', value: 'month' },
]
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const MONTH_ROW = 128
const LANE = 20
const HOUR = 44
const SNAP = 15
const today = dayKey(new Date())

const mode = computed(() => props.display.cal_mode || 'month')
const setMode = (m) => emit('display', { cal_mode: m })
const cursor = ref(new Date())

const pad = (n) => String(n).padStart(2, '0')
const minutesOf = (d) => d.getHours() * 60 + d.getMinutes()
const stamp = (date, minutes = 0) => `${dayKey(date)} ${pad(Math.floor(minutes / 60))}:${pad(minutes % 60)}:00`
const stampOf = (d) => stamp(d, minutesOf(d))
const minLabel = (m) => `${pad(Math.floor(m / 60) % 24)}:${pad(m % 60)}`
const color = (item) => stateOf(item).color || '#6B7280'
const nowMinutes = minutesOf(new Date())

function shift(step) {
  const d = new Date(cursor.value)
  if (mode.value === 'month') {
    d.setDate(1)
    d.setMonth(d.getMonth() + step)
  } else d.setDate(d.getDate() + step * (mode.value === 'week' ? 7 : 1))
  cursor.value = d
}
function openDay(date) {
  cursor.value = new Date(date)
  setMode('day')
}

const weekStart = (date) => addDays(date, -((date.getDay() + 6) % 7))
const title = computed(() => {
  const c = cursor.value
  if (mode.value === 'month') return c.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
  if (mode.value === 'day') return c.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  const s = weekStart(c)
  return `${s.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })} – ${addDays(s, 6).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}`
})

const preview = ref({})

/** An item's span: start..end, or the one date it has. `timed` = same day with a time of day. */
function span(item) {
  const o = preview.value[item.name]
  const s = toDate(o?.start ?? item.exp_start_date) || toDate(o?.end ?? item.exp_end_date)
  const e = toDate(o?.end ?? item.exp_end_date) || s
  if (!s) return null
  const [start, end] = s <= e ? [s, e] : [e, s]
  const timed = dayKey(start) === dayKey(end) && (minutesOf(start) > 0 || minutesOf(end) > 0)
  return { start, end, timed }
}

/** Multi-day bars over a run of days, packed into lanes. */
function layoutBars(rangeStart, length, keep) {
  const segs = []
  for (const item of props.items) {
    const sp = span(item)
    if (!sp || !keep(sp)) continue
    const a = diffDays(rangeStart, sp.start)
    const b = diffDays(rangeStart, sp.end)
    if (b < 0 || a > length - 1) continue
    segs.push({ item, col: Math.max(0, a), end: Math.min(length - 1, b), isEnd: b <= length - 1 })
  }
  segs.sort((x, y) => x.col - y.col || y.end - y.col - (x.end - x.col))
  const lanes = []
  for (const seg of segs) {
    let lane = lanes.findIndex((last) => last < seg.col)
    if (lane < 0) lane = lanes.length
    lanes[lane] = seg.end
    seg.lane = lane
  }
  return { segs, lanes: lanes.length }
}

const weeks = computed(() => {
  const first = new Date(cursor.value.getFullYear(), cursor.value.getMonth(), 1)
  const start = weekStart(first)
  const maxLanes = Math.floor((MONTH_ROW - 26) / (LANE + 2))
  return Array.from({ length: 6 }, (_, w) => {
    const ws = addDays(start, w * 7)
    const days = Array.from({ length: 7 }, (_, i) => {
      const date = addDays(ws, i)
      return { date, key: dayKey(date), inMonth: date.getMonth() === first.getMonth() }
    })
    const { segs } = layoutBars(ws, 7, () => true)
    const hidden = Array(7).fill(0)
    const segments = []
    for (const seg of segs) {
      if (seg.lane < maxLanes) segments.push(seg)
      else for (let c = seg.col; c <= seg.end; c++) hidden[c]++
    }
    return { days, segments, hidden }
  })
})

function segStyle(seg, columns, top) {
  return {
    left: `calc(${(seg.col / columns) * 100}% + 2px)`,
    width: `calc(${((seg.end - seg.col + 1) / columns) * 100}% - 4px)`,
    top: `${top}px`,
    height: `${LANE}px`,
    background: `${color(seg.item)}24`,
    boxShadow: `inset 3px 0 0 ${color(seg.item)}`,
  }
}

const days = computed(() => {
  const c = cursor.value
  if (mode.value === 'day') return [new Date(c.getFullYear(), c.getMonth(), c.getDate())]
  const s = weekStart(c)
  return Array.from({ length: 7 }, (_, i) => addDays(s, i))
})

const allDay = computed(() => {
  const { segs, lanes } = layoutBars(days.value[0], days.value.length, (sp) => !sp.timed)
  return { segments: segs, lanes }
})

/** Timed items per day, side by side where they overlap. */
const timedByDay = computed(() => {
  const out = {}
  days.value.forEach((d, c) => {
    const evs = []
    for (const item of props.items) {
      const sp = span(item)
      if (!sp || !sp.timed || dayKey(sp.start) !== dayKey(d)) continue
      const start = minutesOf(sp.start)
      const end = Math.max(start + 30, minutesOf(sp.end))
      evs.push({ item, start, end })
    }
    evs.sort((a, b) => a.start - b.start)
    const cols = []
    for (const ev of evs) {
      let i = cols.findIndex((last) => last <= ev.start)
      if (i < 0) i = cols.length
      cols[i] = ev.end
      ev.col = i
    }
    for (const ev of evs) {
      ev.cols = cols.length
      ev.height = ((ev.end - ev.start) * HOUR) / 60
    }
    out[c] = evs
  })
  return out
})
function timedStyle(ev) {
  return {
    top: `${(ev.start * HOUR) / 60}px`,
    height: `${Math.max(18, ev.height - 2)}px`,
    left: `calc(${(ev.col / ev.cols) * 100}% + 2px)`,
    width: `calc(${100 / ev.cols}% - 4px)`,
    background: `${color(ev.item)}26`,
    borderColor: color(ev.item),
  }
}

// moving and resizing
const dragging = ref(null)
let justDragged = false
const monthEl = ref(null)
const gridEl = ref(null)
const allDayEl = ref(null)
const gridScroll = ref(null)

function colWidth() {
  const el = mode.value === 'month' ? monthEl.value : gridEl.value || allDayEl.value
  return (el?.clientWidth || 700) / (mode.value === 'month' ? 7 : days.value.length)
}

function startMove(event, item, kind) {
  if (!ctx.can.write) return
  const sp = span(item)
  if (!sp) return
  dragging.value = { item }
  startDrag(event, {
    onMove(dx, dy) {
      let shiftDays = Math.round(dx / colWidth())
      if (mode.value === 'month') shiftDays += Math.round(dy / MONTH_ROW) * 7
      let start = addDays(sp.start, shiftDays)
      let end = addDays(sp.end, shiftDays)
      if (kind === 'time') {
        const mins = Math.round((dy * 60) / HOUR / SNAP) * SNAP
        start = new Date(start.getTime() + mins * 60000)
        end = new Date(end.getTime() + mins * 60000)
      }
      preview.value = { [item.name]: { start, end } }
    },
    onEnd(dx, dy, moved) {
      dragging.value = null
      if (moved) commit(item)
    },
  })
}

function startResize(event, item, kind) {
  if (!ctx.can.write) return
  const sp = span(item)
  startDrag(event, {
    onMove(dx, dy) {
      let end
      if (kind === 'time') {
        const mins = Math.round((dy * 60) / HOUR / SNAP) * SNAP
        end = new Date(Math.max(sp.start.getTime() + SNAP * 60000, sp.end.getTime() + mins * 60000))
      } else {
        end = addDays(sp.end, Math.round(dx / colWidth()))
        if (end < sp.start) end = new Date(sp.start)
      }
      preview.value = { [item.name]: { start: sp.start, end } }
    },
    onEnd(dx, dy, moved) {
      if (moved) commit(item)
    },
  })
}

function commit(item) {
  justDragged = true
  setTimeout(() => (justDragged = false), 50)
  const p = preview.value[item.name]
  if (!p) return
  const patch = { exp_end_date: stampOf(p.end) }
  // an item with only a due date keeps having only a due date when it moves on one day
  if (item.exp_start_date || dayKey(p.start) !== dayKey(p.end)) patch.exp_start_date = stampOf(p.start)
  emit('save', item, patch)
  setTimeout(() => (preview.value = {}), 600)
}

function clickItem(item) {
  if (!justDragged) emit('open', item)
}

// creating: drag across days, or over hours
const selection = ref(null)
function startSelect(event, date) {
  if (!ctx.can.write || event.button !== 0) return
  selection.value = { a: date, b: date }
  const up = () => {
    window.removeEventListener('pointerup', up)
    const { a, b } = selection.value
    selection.value = null
    const [s, e] = a <= b ? [a, b] : [b, a]
    emit('create', { exp_start_date: stamp(s), exp_end_date: stamp(e) })
  }
  window.addEventListener('pointerup', up)
}
function extendSelect(date) {
  if (selection.value) selection.value = { ...selection.value, b: date }
}
function inSelection(key) {
  if (!selection.value) return false
  const [s, e] = [dayKey(selection.value.a), dayKey(selection.value.b)].sort()
  return key >= s && key <= e
}

const timeSel = ref(null)
function startTimeSelect(event, col) {
  if (!ctx.can.write || event.button !== 0) return
  const rect = event.currentTarget.getBoundingClientRect()
  const toMin = (y) => Math.max(0, Math.min(24 * 60, Math.round(((y - rect.top) * 60) / HOUR / SNAP) * SNAP))
  const a = Math.floor(toMin(event.clientY) / 30) * 30
  timeSel.value = { col, a, b: a + 60 }
  startDrag(event, {
    threshold: 0,
    onMove(dx, dy, e) {
      timeSel.value = { col, a, b: Math.max(a + SNAP, toMin(e.clientY)) }
    },
    onEnd() {
      const { a: s, b: e } = timeSel.value
      timeSel.value = null
      const day = days.value[col]
      emit('create', { exp_start_date: stamp(day, s), exp_end_date: stamp(day, Math.min(e, 24 * 60 - 1)) })
    },
  })
}

async function scrollToMorning() {
  await nextTick()
  if (gridScroll.value) gridScroll.value.scrollTop = 7 * HOUR
}
onMounted(scrollToMorning)
watch(mode, (m) => m !== 'month' && scrollToMorning())
</script>
