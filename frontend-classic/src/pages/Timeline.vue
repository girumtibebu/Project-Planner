<script setup lang="ts">
/**
 * Timeline — Gantt chart + Kanban view
 * Design spec: §7.4 from DESIGN_HANDOFF.md
 * Left panel 240px frozen, right panel scrollable Gantt canvas
 */
import { computed, inject, onMounted, ref, type Ref } from "vue";
import { frappeList, frappeSave } from "../composables/useFrappe";
import { assigneeFromTask } from "../utils/assignment";

const project     = inject<Ref<any>>("project");
const projectName = inject<Ref<string>>("projectName");

type ViewMode = "day" | "week" | "month";
const view    = ref<ViewMode>("week");
const tasks   = ref<any[]>([]);
const loading = ref(true);

// ── Day width per view mode ────────────────────────────────────────────────
const DAY_WIDTH_MAP: Record<ViewMode, number> = { day: 80, week: 42, month: 20 };
const dayWidth = computed(() => DAY_WIDTH_MAP[view.value]);

// ── Category → color (consistent palette) ─────────────────────────────────
const PALETTE = [
  "#3B82F6", "#A78BFA", "#0D9488", "#F59E0B",
  "#CC785C", "#22C55E", "#DB2777", "#2563EB",
  "#EF4444", "#CA8A04", "#6366F1", "#8F8A7E",
];

const categoryColorCache = new Map<string, string>();
let paletteIdx = 0;

function categoryColor(cat: string): string {
  if (!categoryColorCache.has(cat)) {
    categoryColorCache.set(cat, PALETTE[paletteIdx % PALETTE.length]);
    paletteIdx++;
  }
  return categoryColorCache.get(cat)!;
}

function taskColor(task: any): string {
  const cat = task.ep_action_category || "Uncategorised";
  return categoryColor(cat);
}

// ── Assignee helpers ───────────────────────────────────────────────────────
function assignee(task: any): string {
  return assigneeFromTask(task._assign);
}

function assigneeInitials(task: any): string {
  const a = assignee(task);
  if (!a) return "";
  const localPart = a.split("@")[0];
  const parts = localPart.split(/[._-]/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return localPart.slice(0, 2).toUpperCase();
}

// ── Data load ──────────────────────────────────────────────────────────────
onMounted(async () => {
  if (!projectName?.value) return;
  loading.value = true;
  try {
    const rows = await frappeList("Task", {
      filters: { project: projectName.value },
      fields: [
        "name", "subject", "status", "_assign",
        "exp_start_date", "exp_end_date",
        "ep_action_category", "ep_sort_order",
        "description",
      ],
      limit: 500,
      order_by: "ep_sort_order asc, exp_start_date asc",
    });
    tasks.value = rows;

    // Pre-seed the category color cache so colors are stable
    const cats = [...new Set(rows.map((r: any) => r.ep_action_category || "Uncategorised"))];
    cats.forEach((c) => taskColor({ ep_action_category: c }));
  } catch (e) {
    console.error("[Timeline] load error:", e);
  } finally {
    loading.value = false;
  }
});

// ── Date range helpers ─────────────────────────────────────────────────────
const today = new Date();
today.setHours(0, 0, 0, 0);

const projectStart = computed(() => {
  const candidates: number[] = [];

  if (project?.value?.expected_start_date)
    candidates.push(new Date(project.value.expected_start_date).getTime());

  // Tasks can start before the project date — always include task starts
  const taskMs = tasks.value
    .map((t) => t.exp_start_date).filter(Boolean)
    .map((d: string) => new Date(d).getTime());
  if (taskMs.length) candidates.push(Math.min(...taskMs));

  if (candidates.length) {
    const earliest = new Date(Math.min(...candidates));
    earliest.setDate(earliest.getDate() - 3); // 3-day left gutter
    return startOfDay(earliest);
  }
  const d = new Date(today); d.setDate(d.getDate() - 3);
  return d;
});

const projectEnd = computed(() => {
  const candidates: number[] = [];

  if (project?.value?.expected_end_date)
    candidates.push(new Date(project.value.expected_end_date).getTime());

  const taskMs = tasks.value
    .map((t) => t.exp_end_date).filter(Boolean)
    .map((d: string) => new Date(d).getTime());
  if (taskMs.length) candidates.push(Math.max(...taskMs));

  if (candidates.length) {
    const latest = new Date(Math.max(...candidates));
    latest.setDate(latest.getDate() + 7); // 7-day right gutter
    return startOfDay(latest);
  }
  const d = new Date(today); d.setDate(d.getDate() + 25);
  return d;
});

function startOfDay(d: Date) {
  const c = new Date(d); c.setHours(0, 0, 0, 0); return c;
}

const totalDays = computed(() => {
  const ms = projectEnd.value.getTime() - projectStart.value.getTime();
  return Math.max(30, Math.ceil(ms / 86400000) + 1);
});

const ganttTotalWidth = computed(() => totalDays.value * dayWidth.value);

// ── Day columns ────────────────────────────────────────────────────────────
const DAY_LETTERS = ["S", "M", "T", "W", "T", "F", "S"]; // Sun=0
const MONTH_ABBR  = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

interface DayCol {
  idx:        number;
  date:       Date;
  letter:     string;
  num:        number;
  month:      string;
  isWeekend:  boolean;
  isToday:    boolean;
  showMonth:  boolean;
}

const dayColumns = computed((): DayCol[] => {
  const cols: DayCol[] = [];
  for (let i = 0; i < totalDays.value; i++) {
    const d = new Date(projectStart.value);
    d.setDate(d.getDate() + i);
    d.setHours(0, 0, 0, 0);
    const dow = d.getDay();
    cols.push({
      idx:       i,
      date:      d,
      letter:    DAY_LETTERS[dow],
      num:       d.getDate(),
      month:     MONTH_ABBR[d.getMonth()],
      isWeekend: dow === 0 || dow === 6,
      isToday:   d.getTime() === today.getTime(),
      showMonth: d.getDate() === 1,
    });
  }
  return cols;
});

// ── Today offset ───────────────────────────────────────────────────────────
const todayOffset = computed(() => {
  const ms = today.getTime() - projectStart.value.getTime();
  return Math.round((ms / 86400000) * dayWidth.value);
});

// ── Task bars ──────────────────────────────────────────────────────────────
interface TaskBar { left: number; width: number; }

function taskBar(task: any): TaskBar | null {
  if (!task.exp_start_date || !task.exp_end_date) return null;
  const s = startOfDay(new Date(task.exp_start_date));
  const e = startOfDay(new Date(task.exp_end_date));
  const msPerDay = 86400000;
  const left  = ((s.getTime() - projectStart.value.getTime()) / msPerDay) * dayWidth.value;
  const width = Math.max(dayWidth.value, ((e.getTime() - s.getTime()) / msPerDay + 1) * dayWidth.value);
  return { left: Math.round(left), width: Math.round(width) };
}

// ── Drag-to-move ───────────────────────────────────────────────────────────
const drag = ref<{ name: string; origStart: string; origEnd: string; startX: number } | null>(null);

function onBarMouseDown(e: MouseEvent, task: any) {
  if (e.button !== 0) return;
  drag.value = {
    name: task.name,
    origStart: task.exp_start_date,
    origEnd:   task.exp_end_date,
    startX:    e.clientX,
  };
  window.addEventListener("mousemove", onBarMouseMove);
  window.addEventListener("mouseup",   onBarMouseUp);
  e.preventDefault();
}

function onBarMouseMove(e: MouseEvent) {
  if (!drag.value) return;
  const dx   = e.clientX - drag.value.startX;
  const days = Math.round(dx / dayWidth.value);
  const task = tasks.value.find((t) => t.name === drag.value!.name);
  if (!task || days === 0) return;

  const newStart = new Date(drag.value.origStart);
  const newEnd   = new Date(drag.value.origEnd);
  newStart.setDate(newStart.getDate() + days);
  newEnd.setDate(newEnd.getDate() + days);
  task.exp_start_date = newStart.toISOString().slice(0, 10);
  task.exp_end_date   = newEnd.toISOString().slice(0, 10);
}

async function onBarMouseUp() {
  window.removeEventListener("mousemove", onBarMouseMove);
  window.removeEventListener("mouseup",   onBarMouseUp);
  if (!drag.value) return;
  const task = tasks.value.find((t) => t.name === drag.value!.name);
  if (task) {
    await frappeSave("Task", task.name, {
      exp_start_date: task.exp_start_date,
      exp_end_date:   task.exp_end_date,
    }).catch(console.error);
  }
  drag.value = null;
}

// ── Format helpers ─────────────────────────────────────────────────────────
function fmtDate(d?: string) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function fmtDateRange(task: any) {
  if (!task.exp_start_date || !task.exp_end_date) return "";
  const s = new Date(task.exp_start_date);
  const e = new Date(task.exp_end_date);
  if (s.getMonth() === e.getMonth())
    return `${MONTH_ABBR[s.getMonth()]} ${s.getDate()}–${e.getDate()}`;
  return `${fmtDate(task.exp_start_date)} – ${fmtDate(task.exp_end_date)}`;
}

const tasksWithBar  = computed(() => tasks.value.filter((t) => taskBar(t)));
const tasksMissingDate = computed(() => tasks.value.filter((t) => !taskBar(t)));

// ── Kanban ─────────────────────────────────────────────────────────────────
type KanbanView = "kanban";
const kanbanView = ref(false);
const groupBy    = ref<"status" | "category">("status");

const STATUSES = ["Open", "Working", "Pending Review", "Overdue", "Completed", "Cancelled"];
const STATUS_COLOR: Record<string, string> = {
  Open: "#6C7280", Working: "#F59E0B", "Pending Review": "#A78BFA",
  Overdue: "#EF4444", Completed: "#22C55E", Cancelled: "#9CA3AF",
};

const kanbanCols = computed(() => {
  if (groupBy.value === "status") {
    return STATUSES.map((s) => ({
      key: s, label: s, color: STATUS_COLOR[s],
      items: tasks.value.filter((t) => t.status === s),
    }));
  }
  const cats = [...new Set(tasks.value.map((t) => t.ep_action_category || "Uncategorised"))];
  return cats.map((cat) => ({
    key: cat, label: cat, color: categoryColor(cat),
    items: tasks.value.filter((t) => (t.ep_action_category || "Uncategorised") === cat),
  }));
});

// ── Summary ─────────────────────────────────────────────────────────────────
const summaryLabel = computed(() => {
  const n  = tasks.value.length;
  const wk = Math.ceil(totalDays.value / 7);
  return `${n} ${n === 1 ? "bar" : "bars"} · ${wk} week horizon`;
});

function exportPdf() {
  if (!projectName?.value) return;
  window.print();
}
</script>

<template>
  <div class="tl-page">

    <!-- ── Page Header ──────────────────────────────────────── -->
    <div class="tl-head">
      <div class="tl-head-left">
        <h1 class="tl-title">Timeline</h1>
        <span v-if="!loading" class="tl-meta">{{ summaryLabel }}</span>
      </div>

      <div class="tl-head-right">
        <!-- Day/Week/Month view tabs (Gantt only) -->
        <template v-if="!kanbanView">
          <div class="view-tabs">
            <button class="view-tab" :class="{ active: view === 'day' }"   @click="view = 'day'">Day</button>
            <button class="view-tab" :class="{ active: view === 'week' }"  @click="view = 'week'">Week</button>
            <button class="view-tab" :class="{ active: view === 'month' }" @click="view = 'month'">Month</button>
          </div>
        </template>

        <!-- Kanban group-by -->
        <template v-if="kanbanView">
          <select v-model="groupBy" class="ep-select">
            <option value="status">By Status</option>
            <option value="category">By Category</option>
          </select>
        </template>

        <!-- Switch to Kanban / Gantt -->
        <button class="btn-ghost" @click="kanbanView = !kanbanView">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
            <rect x="3" y="3" width="7" height="7" rx="1"/>
            <rect x="14" y="3" width="7" height="7" rx="1"/>
            <rect x="3" y="14" width="7" height="7" rx="1"/>
            <rect x="14" y="14" width="7" height="7" rx="1"/>
          </svg>
          {{ kanbanView ? 'Switch to Gantt' : 'Switch to Kanban' }}
        </button>

        <button class="btn-ghost">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
          Filter
        </button>

        <button class="btn-primary" @click="exportPdf">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Export PDF
        </button>
      </div>
    </div>

    <!-- ── Loading ────────────────────────────────────────────── -->
    <div v-if="loading" class="loading-state">
      <div class="spinner" /> Loading tasks…
    </div>

    <!-- ── Kanban ─────────────────────────────────────────────── -->
    <div v-else-if="kanbanView" class="kanban-board">
      <div v-for="col in kanbanCols" :key="col.key" class="kanban-col">
        <div class="kanban-col-head">
          <span class="kanban-dot" :style="{ background: col.color }" />
          <span class="kanban-label">{{ col.label }}</span>
          <span class="kanban-count mono">{{ col.items.length }}</span>
        </div>
        <div class="kanban-cards">
          <div v-for="t in col.items" :key="t.name" class="kanban-card">
            <div class="kanban-card-title">{{ t.subject }}</div>
            <div class="kanban-card-meta">
              <span v-if="t.exp_end_date" class="mono">Due {{ fmtDate(t.exp_end_date) }}</span>
              <div v-if="assigneeInitials(t)" class="assignee-badge-sm"
                :style="{ background: taskColor(t) + '22', color: taskColor(t), borderColor: taskColor(t) + '55' }">
                {{ assigneeInitials(t) }}
              </div>
            </div>
          </div>
          <div v-if="!col.items.length" class="kanban-empty">No items</div>
        </div>
      </div>
    </div>

    <!-- ── Gantt ──────────────────────────────────────────────── -->
    <div v-else class="gantt-wrap">
      <div class="gantt">

        <!-- Left frozen panel -->
        <div class="gantt-left">
          <!-- Header -->
          <div class="gantt-left-header">TASKS</div>

          <!-- Task rows -->
          <div
            v-for="(task, idx) in tasks"
            :key="task.name"
            class="gantt-left-row"
            :class="{ 'no-date': !taskBar(task) }"
          >
            <span class="task-num mono">{{ String(idx + 1).padStart(2, '0') }}</span>
            <span class="task-name">{{ task.subject }}</span>
            <span
              v-if="assigneeInitials(task)"
              class="assignee-badge"
              :style="{
                background: taskColor(task) + '22',
                color: taskColor(task),
                borderColor: taskColor(task) + '55',
              }"
            >{{ assigneeInitials(task) }}</span>
          </div>
        </div>

        <!-- Right scrollable Gantt canvas -->
        <div class="gantt-right">
          <div class="gantt-canvas" :style="{ width: ganttTotalWidth + 'px' }">

            <!-- Date header -->
            <div class="gantt-header">
              <div
                v-for="col in dayColumns"
                :key="col.idx"
                class="gantt-hcol"
                :class="{ 'is-weekend': col.isWeekend, 'is-today': col.isToday }"
                :style="{ width: dayWidth + 'px' }"
              >
                <span class="hcol-letter">{{ col.letter }}</span>
                <span class="hcol-num">
                  {{ col.num }}
                  <span v-if="col.showMonth" class="hcol-month"> {{ col.month }}</span>
                </span>
                <div v-if="col.isToday" class="today-pill">TODAY</div>
              </div>
            </div>

            <!-- Gantt body -->
            <div class="gantt-body">
              <!-- Today vertical line -->
              <div
                v-if="todayOffset >= 0 && todayOffset <= ganttTotalWidth"
                class="today-line"
                :style="{ left: todayOffset + 'px' }"
              />

              <!-- One row per task -->
              <div
                v-for="(task, idx) in tasks"
                :key="task.name"
                class="gantt-row"
              >
                <!-- Column background shading (weekends) -->
                <div
                  v-for="col in dayColumns"
                  :key="col.idx"
                  class="gcol-shade"
                  :class="{ 'weekend-shade': col.isWeekend, 'today-shade': col.isToday }"
                  :style="{ left: col.idx * dayWidth + 'px', width: dayWidth + 'px' }"
                />

                <!-- Task bar -->
                <template v-if="taskBar(task)">
                  <div
                    class="gantt-bar"
                    :style="{
                      left:       taskBar(task)!.left + 'px',
                      width:      taskBar(task)!.width + 'px',
                      background: taskColor(task),
                    }"
                    :title="`${task.subject} · ${fmtDateRange(task)}`"
                    @mousedown="(e) => onBarMouseDown(e, task)"
                  >
                    <span class="bar-label">{{ task.subject }}</span>
                    <span
                      v-if="taskBar(task)!.width > 120"
                      class="bar-date mono"
                    >{{ fmtDateRange(task) }}</span>
                  </div>
                </template>
              </div>
            </div>

          </div>
        </div>
      </div>

      <!-- Legend row -->
      <div v-if="tasks.length > 0" class="gantt-legend">
        <div
          v-for="[cat, col] in [...categoryColorCache.entries()]"
          :key="cat"
          class="legend-item"
        >
          <span class="legend-dot" :style="{ background: col }" />
          <span class="legend-label">{{ cat }}</span>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="tasks.length === 0" class="empty-state">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-3)"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        <span>No tasks with date ranges found.</span>
        <span class="empty-hint">Add expected start and end dates to tasks in the Action Plan.</span>
      </div>
    </div>

  </div>
</template>

<style scoped>
.tl-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--bg);
}

/* ── Header ─────────────────────────────────────────────── */
.tl-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--panel);
  flex-shrink: 0;
}

.tl-head-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.tl-title {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.02em;
  margin: 0;
  color: var(--text);
}

.tl-meta {
  font-size: 11.5px;
  color: var(--text-3);
}

.tl-head-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* View tabs */
.view-tabs {
  display: inline-flex;
  background: var(--bg-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 3px;
}

.view-tab {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-3);
  cursor: pointer;
  font-family: inherit;
  transition: all 120ms ease;
}

.view-tab.active {
  background: var(--panel);
  border-color: var(--border-2);
  color: var(--text);
  box-shadow: 0 1px 2px rgba(0,0,0,.04);
}

.view-tab:hover:not(.active) { color: var(--text-2); }

/* Buttons */
.btn-ghost {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 12px;
  background: var(--panel); border: 1px solid var(--border-2);
  border-radius: 6px; font-size: 12px; font-weight: 500;
  color: var(--text-2); cursor: pointer; font-family: inherit;
  transition: all 120ms ease;
}
.btn-ghost:hover { background: var(--bg-2); color: var(--text); }

.btn-primary {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 12px;
  background: var(--accent); border: 1px solid var(--accent);
  border-radius: 6px; font-size: 12px; font-weight: 500;
  color: #fff; cursor: pointer; font-family: inherit;
  transition: background 120ms ease;
}
.btn-primary:hover { background: var(--accent-2); }

.ep-select {
  padding: 5px 10px; border: 1px solid var(--border-2); border-radius: 5px;
  font-size: 12px; font-family: inherit; background: var(--bg-2); color: var(--text);
}

/* Loading */
.loading-state {
  display: flex; align-items: center; gap: 10px;
  padding: 60px 24px; color: var(--text-3); font-size: 13px;
}
.spinner {
  width: 18px; height: 18px;
  border: 2px solid var(--border); border-top-color: var(--accent);
  border-radius: 50%; animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Gantt ──────────────────────────────────────────────── */
.gantt-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 0 0;
}

.gantt {
  display: flex;
  flex: 1;
  overflow: hidden;
  margin: 0 20px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--panel);
}

/* Left frozen panel */
.gantt-left {
  flex-shrink: 0;
  width: 260px;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.gantt-left-header {
  height: 52px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-3);
  background: var(--panel-2);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.gantt-left-row {
  height: 36px;
  display: flex;
  align-items: center;
  padding: 0 10px;
  gap: 6px;
  border-bottom: 1px solid var(--border);
  transition: background 100ms;
}

.gantt-left-row:last-child { border-bottom: none; }
.gantt-left-row:hover { background: var(--row-hover); }
.gantt-left-row.no-date { opacity: 0.55; }

.task-num {
  font-size: 10px;
  color: var(--text-3);
  width: 20px;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.task-name {
  flex: 1;
  font-size: 12.5px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.assignee-badge {
  flex-shrink: 0;
  width: 24px; height: 24px;
  border-radius: 6px;
  border: 1px solid;
  display: flex; align-items: center; justify-content: center;
  font-size: 9px; font-weight: 700;
  font-family: var(--font-mono);
}

/* Right scrollable */
.gantt-right {
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
}

.gantt-canvas {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

/* Date header */
.gantt-header {
  height: 52px;
  display: flex;
  border-bottom: 1px solid var(--border);
  background: var(--panel-2);
  flex-shrink: 0;
}

.gantt-hcol {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  border-right: 1px solid var(--border);
  position: relative;
  cursor: default;
}

.gantt-hcol.is-weekend {
  background: rgba(0,0,0,.02);
}

.gantt-hcol.is-today {
  background: var(--accent-soft);
}

.hcol-letter {
  font-size: 9.5px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-3);
  line-height: 1;
}

.hcol-num {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
  line-height: 1;
  font-family: var(--font-mono);
}

.hcol-month {
  font-size: 9px;
  color: var(--accent);
  font-weight: 700;
  text-transform: lowercase;
}

.is-today .hcol-letter,
.is-today .hcol-num {
  color: var(--accent);
}

.today-pill {
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--accent);
  color: white;
  font-size: 8px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 999px;
  white-space: nowrap;
  z-index: 5;
  letter-spacing: 0.05em;
}

/* Gantt body */
.gantt-body {
  position: relative;
  flex: 1;
}

.today-line {
  position: absolute;
  top: 0; bottom: 0;
  width: 2px;
  background: var(--accent);
  opacity: 0.5;
  z-index: 4;
  pointer-events: none;
}

.gantt-row {
  height: 36px;
  border-bottom: 1px solid var(--border);
  position: relative;
}

.gantt-row:last-child { border-bottom: none; }
.gantt-row:hover { background: var(--row-hover); }

/* Column shading */
.gcol-shade {
  position: absolute;
  top: 0; bottom: 0;
  pointer-events: none;
  z-index: 0;
}
.gcol-shade.weekend-shade { background: rgba(0,0,0,.025); }
.gcol-shade.today-shade   { background: rgba(204,120,92,.06); }

/* Task bar */
.gantt-bar {
  position: absolute;
  top: 8px;
  height: 20px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  overflow: hidden;
  cursor: grab;
  user-select: none;
  z-index: 2;
  transition: filter 150ms ease;
}

.gantt-bar:hover { filter: brightness(1.08); }
.gantt-bar:active { cursor: grabbing; }

.bar-label {
  padding: 0 8px;
  font-size: 11px;
  font-weight: 500;
  color: white;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.bar-date {
  padding-right: 8px;
  font-size: 9.5px;
  color: rgba(255,255,255,.8);
  white-space: nowrap;
  flex-shrink: 0;
}

/* Legend */
.gantt-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 10px 20px;
  border-top: 1px solid var(--border);
  background: var(--panel-2);
  margin: 0 20px;
  border-radius: 0 0 8px 8px;
}

.legend-item {
  display: flex; align-items: center; gap: 6px;
  font-size: 11.5px; color: var(--text-2);
}

.legend-dot {
  width: 10px; height: 10px;
  border-radius: 2px; flex-shrink: 0;
}

.legend-label { font-size: 11.5px; }

/* Empty state */
.empty-state {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 10px; padding: 80px 24px;
  color: var(--text-3); font-size: 13px;
  text-align: center;
}

.empty-hint { font-size: 12px; color: var(--text-3); max-width: 320px; }

/* ── Kanban ─────────────────────────────────────────────── */
.kanban-board {
  display: flex;
  gap: 16px;
  padding: 16px 20px;
  overflow-x: auto;
  flex: 1;
}

.kanban-col { flex-shrink: 0; width: 240px; }

.kanban-col-head {
  display: flex; align-items: center; gap: 6px;
  padding: 0 0 10px;
  font-size: 12.5px; font-weight: 600; color: var(--text);
}

.kanban-dot {
  width: 8px; height: 8px; border-radius: 999px; flex-shrink: 0;
}

.kanban-label { flex: 1; }
.kanban-count { font-size: 11px; color: var(--text-3); }

.kanban-cards { display: flex; flex-direction: column; gap: 8px; }

.kanban-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  transition: box-shadow 120ms ease;
}

.kanban-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,.06);
}

.kanban-card-title {
  font-size: 12.5px; font-weight: 500;
  color: var(--text); margin-bottom: 8px;
  line-height: 1.4;
}

.kanban-card-meta {
  display: flex; align-items: center;
  justify-content: space-between;
  font-size: 11px; color: var(--text-3);
}

.assignee-badge-sm {
  width: 20px; height: 20px;
  border-radius: 5px; border: 1px solid;
  display: flex; align-items: center; justify-content: center;
  font-size: 8px; font-weight: 700;
  font-family: var(--font-mono);
}

.kanban-empty {
  padding: 16px 12px; font-size: 12px;
  color: var(--text-3); text-align: center;
  border: 1px dashed var(--border); border-radius: 8px;
}
</style>
