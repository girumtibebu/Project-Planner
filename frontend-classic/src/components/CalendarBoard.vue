<script setup lang="ts">
import { computed, ref } from "vue";
import { frappeSave } from "../composables/useFrappe";

// ── Props / emits ─────────────────────────────────────────────────────────────

const props = defineProps<{
  tasks:      any[];
  categories: any[];
}>();

const emit = defineEmits<{
  (e: "open-task",   task: any): void;
  (e: "create-task", defaults: Partial<any>): void;
  (e: "updated"): void;
}>();

// ── View mode ─────────────────────────────────────────────────────────────────

type CalMode = "month" | "week" | "day";
const mode = ref<CalMode>("month");

// ── Current reference date ────────────────────────────────────────────────────

const today   = new Date();
today.setHours(0, 0, 0, 0);
const refDate = ref(new Date(today));

function prevPeriod() {
  const d = new Date(refDate.value);
  if (mode.value === "month") { d.setMonth(d.getMonth() - 1); }
  else if (mode.value === "week") { d.setDate(d.getDate() - 7); }
  else { d.setDate(d.getDate() - 1); }
  refDate.value = d;
}

function nextPeriod() {
  const d = new Date(refDate.value);
  if (mode.value === "month") { d.setMonth(d.getMonth() + 1); }
  else if (mode.value === "week") { d.setDate(d.getDate() + 7); }
  else { d.setDate(d.getDate() + 1); }
  refDate.value = d;
}

function goToday() { refDate.value = new Date(today); }

// ── Header label ──────────────────────────────────────────────────────────────

const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
const DAYS   = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

const periodLabel = computed(() => {
  const d = refDate.value;
  if (mode.value === "month") return `${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
  if (mode.value === "week") {
    const start = weekStart(d);
    const end   = new Date(start); end.setDate(end.getDate() + 6);
    return `${MONTHS[start.getMonth()]} ${start.getDate()} – ${MONTHS[end.getMonth()] !== MONTHS[start.getMonth()] ? MONTHS[end.getMonth()] + " " : ""}${end.getDate()}, ${end.getFullYear()}`;
  }
  return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
});

// ── Date helpers ──────────────────────────────────────────────────────────────

function sod(d: Date) { const c = new Date(d); c.setHours(0,0,0,0); return c; }
function isoDate(d: Date) { return d.toISOString().slice(0, 10); }
function isToday(d: Date) { return sod(d).getTime() === today.getTime(); }
function weekStart(d: Date) { const c = sod(d); c.setDate(c.getDate() - c.getDay()); return c; }

// ── Month grid cells ──────────────────────────────────────────────────────────

interface CalCell { date: Date; iso: string; inMonth: boolean; isToday: boolean; }

const monthCells = computed((): CalCell[] => {
  const d     = refDate.value;
  const first = new Date(d.getFullYear(), d.getMonth(), 1);
  const last  = new Date(d.getFullYear(), d.getMonth() + 1, 0);
  const cells: CalCell[] = [];
  // Fill leading days from prev month
  for (let i = first.getDay(); i > 0; i--) {
    const dd = new Date(first); dd.setDate(dd.getDate() - i);
    cells.push({ date: dd, iso: isoDate(dd), inMonth: false, isToday: isToday(dd) });
  }
  // Fill current month
  for (let i = 1; i <= last.getDate(); i++) {
    const dd = new Date(d.getFullYear(), d.getMonth(), i);
    cells.push({ date: dd, iso: isoDate(dd), inMonth: true, isToday: isToday(dd) });
  }
  // Fill trailing days to complete last week row
  const trailing = 7 - (cells.length % 7 || 7);
  if (trailing < 7) {
    for (let i = 1; i <= trailing; i++) {
      const dd = new Date(last); dd.setDate(dd.getDate() + i);
      cells.push({ date: dd, iso: isoDate(dd), inMonth: false, isToday: isToday(dd) });
    }
  }
  return cells;
});

// ── Week grid cells ───────────────────────────────────────────────────────────

const weekCells = computed((): CalCell[] => {
  const start = weekStart(refDate.value);
  return Array.from({ length: 7 }, (_, i) => {
    const dd = new Date(start); dd.setDate(dd.getDate() + i);
    return { date: dd, iso: isoDate(dd), inMonth: true, isToday: isToday(dd) };
  });
});

// ── Day hours ─────────────────────────────────────────────────────────────────

const dayHours = computed(() =>
  Array.from({ length: 24 }, (_, h) => ({ hour: h, label: `${String(h).padStart(2, "0")}:00` }))
);

// ── Task placement helpers ────────────────────────────────────────────────────

function tasksForDate(iso: string): any[] {
  return props.tasks.filter(t => {
    if (!t.exp_start_date) return false;
    const s = t.exp_start_date.slice(0, 10);
    const e = t.exp_end_date ? t.exp_end_date.slice(0, 10) : s;
    return s <= iso && iso <= e;
  });
}

function taskColor(task: any): string {
  const cat = props.categories.find(c => c.name === task.ep_action_category);
  return cat?.color || task.category_color || "#CC785C";
}

// ── Drag chip ─────────────────────────────────────────────────────────────────

const dragging = ref<any | null>(null);

function onChipDragStart(e: DragEvent, task: any) {
  dragging.value = task;
  e.dataTransfer!.effectAllowed = "move";
}

function onCellDragOver(e: DragEvent) { e.preventDefault(); }

async function onCellDrop(_e: DragEvent, iso: string) {
  if (!dragging.value) return;
  const task = dragging.value;
  dragging.value = null;
  const origStart = task.exp_start_date?.slice(0, 10);
  const origEnd   = task.exp_end_date?.slice(0, 10);
  if (!origStart) { task.exp_start_date = iso; task.exp_end_date = iso; }
  else {
    const dur = origEnd ? (new Date(origEnd).getTime() - new Date(origStart).getTime()) / 86400000 : 0;
    const newEnd = new Date(iso); newEnd.setDate(newEnd.getDate() + dur);
    task.exp_start_date = iso;
    task.exp_end_date   = isoDate(newEnd);
  }
  await frappeSave("Task", task.name, {
    exp_start_date: task.exp_start_date,
    exp_end_date:   task.exp_end_date,
  }).catch(console.error);
  emit("updated");
}

// ── Click empty cell to create ────────────────────────────────────────────────

function onCellClick(iso: string) {
  emit("create-task", { exp_start_date: iso, exp_end_date: iso });
}
</script>

<template>
  <div class="cal-wrap">

    <!-- ── Toolbar ──────────────────────────────────────────────────────────── -->
    <div class="cal-toolbar">
      <div class="cal-nav">
        <button class="cal-nav-btn" @click="prevPeriod">‹</button>
        <span class="cal-period">{{ periodLabel }}</span>
        <button class="cal-nav-btn" @click="nextPeriod">›</button>
        <button class="cal-today-btn" @click="goToday">Today</button>
      </div>
      <div class="cal-mode-toggle">
        <button class="cal-mode-btn" :class="{ active: mode === 'month' }" @click="mode = 'month'">Month</button>
        <button class="cal-mode-btn" :class="{ active: mode === 'week' }"  @click="mode = 'week'">Week</button>
        <button class="cal-mode-btn" :class="{ active: mode === 'day' }"   @click="mode = 'day'">Day</button>
      </div>
    </div>

    <!-- ── Month view ────────────────────────────────────────────────────────── -->
    <template v-if="mode === 'month'">
      <!-- Day headers -->
      <div class="cal-month-header">
        <span v-for="day in DAYS" :key="day" class="cal-day-hdr">{{ day }}</span>
      </div>
      <!-- Grid -->
      <div class="cal-month-grid">
        <div
          v-for="cell in monthCells"
          :key="cell.iso"
          class="cal-cell"
          :class="{ 'cal-cell--out': !cell.inMonth, 'cal-cell--today': cell.isToday }"
          @click.self="onCellClick(cell.iso)"
          @dragover.prevent="onCellDragOver($event)"
          @drop="onCellDrop($event, cell.iso)"
        >
          <div class="cal-cell-num" @click="onCellClick(cell.iso)">{{ cell.date.getDate() }}</div>
          <div class="cal-cell-chips">
            <div
              v-for="task in tasksForDate(cell.iso)"
              :key="task.name"
              class="cal-chip"
              :style="{ '--c': taskColor(task) }"
              draggable="true"
              @dragstart="onChipDragStart($event, task)"
              @click.stop="emit('open-task', task)"
              :title="task.subject"
            >
              <span class="cal-chip-text">{{ task.subject }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ── Week view ─────────────────────────────────────────────────────────── -->
    <template v-else-if="mode === 'week'">
      <div class="cal-week-header">
        <div class="cal-time-gutter-hdr" />
        <div
          v-for="cell in weekCells"
          :key="cell.iso"
          class="cal-week-day-hdr"
          :class="{ 'cal-week-day-hdr--today': cell.isToday }"
        >
          <span class="cal-wh-dow">{{ DAYS[cell.date.getDay()] }}</span>
          <span class="cal-wh-num" :class="{ 'cal-wh-num--today': cell.isToday }">{{ cell.date.getDate() }}</span>
        </div>
      </div>
      <div class="cal-week-body">
        <div class="cal-time-gutter">
          <div v-for="h in dayHours" :key="h.hour" class="cal-hour-label">{{ h.label }}</div>
        </div>
        <div v-for="cell in weekCells" :key="cell.iso" class="cal-week-col">
          <div
            class="cal-week-cell"
            @click.self="onCellClick(cell.iso)"
            @dragover.prevent="onCellDragOver($event)"
            @drop="onCellDrop($event, cell.iso)"
          >
            <div
              v-for="task in tasksForDate(cell.iso)"
              :key="task.name"
              class="cal-chip cal-chip--week"
              :style="{ '--c': taskColor(task) }"
              draggable="true"
              @dragstart="onChipDragStart($event, task)"
              @click.stop="emit('open-task', task)"
            >
              <span class="cal-chip-text">{{ task.subject }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ── Day view ──────────────────────────────────────────────────────────── -->
    <template v-else>
      <div class="cal-day-wrap">
        <div class="cal-time-gutter cal-time-gutter--day">
          <div v-for="h in dayHours" :key="h.hour" class="cal-hour-label">{{ h.label }}</div>
        </div>
        <div class="cal-day-col">
          <div
            class="cal-day-cell"
            @click.self="onCellClick(isoDate(refDate))"
            @dragover.prevent="onCellDragOver($event)"
            @drop="onCellDrop($event, isoDate(refDate))"
          >
            <div
              v-for="task in tasksForDate(isoDate(refDate))"
              :key="task.name"
              class="cal-chip cal-chip--day"
              :style="{ '--c': taskColor(task) }"
              draggable="true"
              @dragstart="onChipDragStart($event, task)"
              @click.stop="emit('open-task', task)"
            >
              <span class="cal-chip-text">{{ task.subject }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

  </div>
</template>

<style scoped>
.cal-wrap {
  display: flex; flex-direction: column; height: 100%; overflow: hidden;
  user-select: none;
}

/* ── Toolbar ──────────────────────────────────────────────────────────────── */
.cal-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 20px; border-bottom: 1px solid var(--border); flex-shrink: 0;
  background: var(--panel-2); gap: 12px; flex-wrap: wrap;
}
.cal-nav { display: flex; align-items: center; gap: 6px; }
.cal-nav-btn {
  width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--border-2); border-radius: 5px; background: none; cursor: pointer;
  font-size: 16px; color: var(--text-2); line-height: 1;
}
.cal-nav-btn:hover { background: var(--row-hover); }
.cal-period { font-size: 13px; font-weight: 600; color: var(--text); min-width: 180px; }
.cal-today-btn {
  font-size: 12px; padding: 4px 10px; border: 1px solid var(--border-2); border-radius: 5px;
  background: none; color: var(--text-2); cursor: pointer;
}
.cal-today-btn:hover { background: var(--row-hover); color: var(--text); }
.cal-mode-toggle { display: flex; border: 1px solid var(--border-2); border-radius: 6px; overflow: hidden; }
.cal-mode-btn {
  font-size: 12px; font-weight: 500; padding: 5px 12px; border: none;
  background: none; cursor: pointer; font-family: inherit; color: var(--text-2);
}
.cal-mode-btn.active { background: var(--accent); color: white; }
.cal-mode-btn:hover:not(.active) { background: var(--row-hover); }

/* ── Month ────────────────────────────────────────────────────────────────── */
.cal-month-header {
  display: grid; grid-template-columns: repeat(7, 1fr);
  border-bottom: 1px solid var(--border); flex-shrink: 0;
  background: var(--panel-2);
}
.cal-day-hdr {
  padding: 6px 8px; font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .07em; color: var(--text-3); text-align: center;
}
.cal-month-grid {
  flex: 1; overflow-y: auto; display: grid; grid-template-columns: repeat(7, 1fr);
  grid-auto-rows: minmax(90px, 1fr); border-collapse: collapse;
}
.cal-cell {
  border-right: 1px solid var(--border); border-bottom: 1px solid var(--border);
  padding: 4px; cursor: pointer; min-height: 90px; position: relative;
  background: var(--panel); transition: background 80ms;
}
.cal-cell:hover { background: var(--row-hover); }
.cal-cell:nth-child(7n) { border-right: none; }
.cal-cell--out { background: var(--panel-2); }
.cal-cell--today .cal-cell-num { color: white; background: var(--accent); border-radius: 50%; }
.cal-cell-num {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; font-size: 12px; font-weight: 500;
  color: var(--text); margin-bottom: 2px; cursor: pointer;
}
.cal-cell-chips { display: flex; flex-direction: column; gap: 2px; }

/* ── Week ─────────────────────────────────────────────────────────────────── */
.cal-week-header {
  display: flex; border-bottom: 1px solid var(--border); flex-shrink: 0;
  background: var(--panel-2);
}
.cal-time-gutter-hdr { width: 52px; flex-shrink: 0; }
.cal-week-day-hdr {
  flex: 1; text-align: center; padding: 8px 4px; border-left: 1px solid var(--border);
}
.cal-wh-dow { display: block; font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--text-3); }
.cal-wh-num { font-size: 17px; font-weight: 600; color: var(--text); }
.cal-wh-num--today { color: var(--accent); }
.cal-week-body { flex: 1; overflow-y: auto; display: flex; }
.cal-time-gutter {
  width: 52px; flex-shrink: 0;
  display: flex; flex-direction: column;
}
.cal-hour-label {
  height: 52px; font-size: 10px; color: var(--text-3); text-align: right;
  padding-right: 6px; padding-top: 2px; flex-shrink: 0; font-family: var(--font-mono);
  border-bottom: 1px solid var(--border);
}
.cal-week-col { flex: 1; border-left: 1px solid var(--border); }
.cal-week-cell {
  min-height: 52px * 24; height: calc(52px * 24);
  position: relative; cursor: pointer; padding: 4px;
  display: flex; flex-direction: column; gap: 3px;
}

/* ── Day ──────────────────────────────────────────────────────────────────── */
.cal-day-wrap { flex: 1; overflow-y: auto; display: flex; }
.cal-time-gutter--day { width: 52px; flex-shrink: 0; }
.cal-day-col { flex: 1; border-left: 1px solid var(--border); }
.cal-day-cell {
  padding: 12px 16px; min-height: 400px; cursor: pointer;
  display: flex; flex-direction: column; gap: 6px;
}

/* ── Chip ─────────────────────────────────────────────────────────────────── */
.cal-chip {
  background: color-mix(in srgb, var(--c) 15%, transparent);
  border-left: 2px solid var(--c);
  border-radius: 4px; padding: 2px 6px; cursor: pointer;
  transition: opacity 120ms; max-width: 100%;
}
.cal-chip:hover { opacity: .85; }
.cal-chip-text {
  font-size: 11px; font-weight: 500; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  display: block; max-width: 100%;
}
.cal-chip--week, .cal-chip--day { margin-bottom: 2px; }
</style>
