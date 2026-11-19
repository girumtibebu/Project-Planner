<script setup lang="ts">
/**
 * TimeWorkspace — three-tab view: Gantt | Kanban | Calendar
 * Replaces Timeline.vue as the /timeline route target.
 * Task data loaded once, shared across all three sub-views.
 */
import { computed, inject, onMounted, ref, watch, type Ref } from "vue";
import KanbanBoard from "../components/KanbanBoard.vue";
import CalendarBoard from "../components/CalendarBoard.vue";
import TaskPanel from "../components/TaskPanel.vue";
import TaskDialog from "../components/TaskDialog.vue";
import Avatar from "../components/Avatar.vue";
import { frappeCall, frappeList, frappeSave } from "../composables/useFrappe";
import { assigneeFromTask } from "../utils/assignment";

// ── Project context ───────────────────────────────────────────────────────────

const project     = inject<Ref<any>>("project");
const projectName = inject<Ref<string>>("projectName");

// ── Tab state ─────────────────────────────────────────────────────────────────

type Tab = "gantt" | "kanban" | "calendar";
// On mobile, Gantt is impractical → default to Kanban
const activeTab = ref<Tab>(typeof window !== "undefined" && window.innerWidth < 768 ? "kanban" : "gantt");

function setTab(tab: Tab) {
  if (tab === "gantt" && typeof window !== "undefined" && window.innerWidth < 768) {
    activeTab.value = "kanban";
    return;
  }
  activeTab.value = tab;
}

// ── Shared data ───────────────────────────────────────────────────────────────

const tasks      = ref<any[]>([]);
const categories = ref<any[]>([]);
const loading    = ref(true);

// ── Panel / dialog ────────────────────────────────────────────────────────────

const panel  = ref<{ open: boolean; task: any | null }>({ open: false, task: null });
const dialog = ref<{ open: boolean; task: any | null }>({ open: false, task: null });

function openTask(task: any) {
  panel.value = { open: true, task };
}

function createTask(defaults: Partial<any>) {
  dialog.value = { open: true, task: { ...defaults } };
}

async function onDialogSave(saved: any) {
  dialog.value = { open: false, task: null };
  await reload();
}

async function onPanelUpdated(updated: any) {
  const idx = tasks.value.findIndex(t => t.name === updated.name);
  if (idx >= 0) tasks.value.splice(idx, 1, updated);
  await reload();
}

// ── Load ──────────────────────────────────────────────────────────────────────

onMounted(() => { if (projectName?.value) reload(); });
watch(() => projectName?.value, (n) => { if (n) reload(); });

async function reload() {
  loading.value = true;
  try {
    const [hier, cats] = await Promise.all([
      frappeCall("event_planner.api.list_tasks_with_hierarchy", { project: projectName!.value }),
      frappeCall("event_planner.api.list_categories", { project: projectName!.value }),
    ]);
    tasks.value      = hier || [];
    categories.value = cats || [];
    // Seed category color cache from the category objects
    hier?.forEach((t: any) => {
      const cat = cats?.find((c: any) => c.name === t.ep_action_category);
      if (cat) t.category_color = cat.color || "";
    });
  } catch (e) {
    console.error("[TimeWorkspace] load error:", e);
  } finally {
    loading.value = false;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// GANTT TAB
// ═══════════════════════════════════════════════════════════════════════════════

type ViewMode = "day" | "week" | "month";
const ganttView = ref<ViewMode>("week");
const groupByCategory = ref(false);
const collapsedParents = ref<Set<string>>(new Set());

const DAY_WIDTH_MAP: Record<ViewMode, number> = { day: 80, week: 42, month: 20 };
const dayWidth = computed(() => DAY_WIDTH_MAP[ganttView.value]);

// Category color helper
const PALETTE = [
  "#3B82F6", "#A78BFA", "#0D9488", "#F59E0B",
  "#CC785C", "#22C55E", "#DB2777", "#2563EB",
  "#EF4444", "#CA8A04", "#6366F1", "#8F8A7E",
];
const colorCache = new Map<string, string>();
let pIdx = 0;

function categoryColor(catName: string): string {
  if (!catName) return PALETTE[0];
  const cat = categories.value.find(c => c.name === catName || c.title === catName);
  if (cat?.color) return cat.color;
  if (!colorCache.has(catName)) { colorCache.set(catName, PALETTE[pIdx++ % PALETTE.length]); }
  return colorCache.get(catName)!;
}

function taskColor(task: any): string {
  return task.category_color || categoryColor(task.ep_action_category || "");
}

// Visible tasks in Gantt — filter out hidden sub-tasks if parent is collapsed
const ganttTasks = computed(() => {
  if (groupByCategory.value) {
    // Group: show category header rows + task rows per category
    return tasks.value.filter(t => {
      const p = t.parent_task;
      if (p && collapsedParents.value.has(p)) return false;
      return true;
    });
  }
  return tasks.value.filter(t => {
    if (t.parent_task && collapsedParents.value.has(t.parent_task)) return false;
    return true;
  });
});

// Date helpers
const today = new Date(); today.setHours(0, 0, 0, 0);
const MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const DAY_LETTERS = ["S","M","T","W","T","F","S"];

function startOfDay(d: Date) { const c = new Date(d); c.setHours(0,0,0,0); return c; }

const projectStart = computed(() => {
  const cands: number[] = [];
  if (project?.value?.expected_start_date) cands.push(new Date(project.value.expected_start_date).getTime());
  const tMs = tasks.value.map(t => t.exp_start_date).filter(Boolean).map((d: string) => new Date(d).getTime());
  if (tMs.length) cands.push(Math.min(...tMs));
  if (cands.length) { const e = new Date(Math.min(...cands)); e.setDate(e.getDate() - 3); return startOfDay(e); }
  const d = new Date(today); d.setDate(d.getDate() - 3); return d;
});

const projectEnd = computed(() => {
  const cands: number[] = [];
  if (project?.value?.expected_end_date) cands.push(new Date(project.value.expected_end_date).getTime());
  const tMs = tasks.value.map(t => t.exp_end_date).filter(Boolean).map((d: string) => new Date(d).getTime());
  if (tMs.length) cands.push(Math.max(...tMs));
  if (cands.length) { const e = new Date(Math.max(...cands)); e.setDate(e.getDate() + 7); return startOfDay(e); }
  const d = new Date(today); d.setDate(d.getDate() + 25); return d;
});

const totalDays = computed(() => Math.max(30, Math.ceil((projectEnd.value.getTime() - projectStart.value.getTime()) / 86400000) + 1));
const ganttTotalWidth = computed(() => totalDays.value * dayWidth.value);

interface DayCol { idx: number; date: Date; letter: string; num: number; month: string; isWeekend: boolean; isToday: boolean; showMonth: boolean; }
const dayColumns = computed((): DayCol[] => {
  const cols: DayCol[] = [];
  for (let i = 0; i < totalDays.value; i++) {
    const d = new Date(projectStart.value); d.setDate(d.getDate() + i); d.setHours(0,0,0,0);
    const dow = d.getDay();
    cols.push({ idx: i, date: d, letter: DAY_LETTERS[dow], num: d.getDate(), month: MONTH_ABBR[d.getMonth()], isWeekend: dow === 0 || dow === 6, isToday: d.getTime() === today.getTime(), showMonth: d.getDate() === 1 });
  }
  return cols;
});

const todayOffset = computed(() => Math.round(((today.getTime() - projectStart.value.getTime()) / 86400000) * dayWidth.value));

interface TaskBar { left: number; width: number; }
function taskBar(task: any): TaskBar | null {
  if (!task.exp_start_date || !task.exp_end_date) return null;
  const s = startOfDay(new Date(task.exp_start_date));
  const e = startOfDay(new Date(task.exp_end_date));
  const left  = ((s.getTime() - projectStart.value.getTime()) / 86400000) * dayWidth.value;
  const width = Math.max(dayWidth.value, ((e.getTime() - s.getTime()) / 86400000 + 1) * dayWidth.value);
  return { left: Math.round(left), width: Math.round(width) };
}

// Drag-to-move bars
const drag = ref<{ name: string; origStart: string; origEnd: string; startX: number } | null>(null);
// Drag-resize handles
const resizing = ref<{ name: string; edge: "left" | "right"; origStart: string; origEnd: string; startX: number } | null>(null);

function onBarMouseDown(e: MouseEvent, task: any) {
  if (e.button !== 0) return;
  drag.value = { name: task.name, origStart: task.exp_start_date, origEnd: task.exp_end_date, startX: e.clientX };
  window.addEventListener("mousemove", onBarMouseMove);
  window.addEventListener("mouseup", onBarMouseUp);
  e.preventDefault(); e.stopPropagation();
}

function onResizeMouseDown(e: MouseEvent, task: any, edge: "left" | "right") {
  if (e.button !== 0) return;
  resizing.value = { name: task.name, edge, origStart: task.exp_start_date, origEnd: task.exp_end_date, startX: e.clientX };
  window.addEventListener("mousemove", onResizeMouseMove);
  window.addEventListener("mouseup", onResizeMouseUp);
  e.preventDefault(); e.stopPropagation();
}

function onBarMouseMove(e: MouseEvent) {
  if (!drag.value) return;
  const days = Math.round((e.clientX - drag.value.startX) / dayWidth.value);
  const task = tasks.value.find(t => t.name === drag.value!.name);
  if (!task || days === 0) return;
  const s = new Date(drag.value.origStart); s.setDate(s.getDate() + days);
  const en = new Date(drag.value.origEnd); en.setDate(en.getDate() + days);
  task.exp_start_date = s.toISOString().slice(0, 10);
  task.exp_end_date   = en.toISOString().slice(0, 10);
}

async function onBarMouseUp() {
  window.removeEventListener("mousemove", onBarMouseMove);
  window.removeEventListener("mouseup", onBarMouseUp);
  if (!drag.value) return;
  const task = tasks.value.find(t => t.name === drag.value!.name);
  if (task) await frappeSave("Task", task.name, { exp_start_date: task.exp_start_date, exp_end_date: task.exp_end_date }).catch(console.error);
  drag.value = null;
}

function onResizeMouseMove(e: MouseEvent) {
  if (!resizing.value) return;
  const days = Math.round((e.clientX - resizing.value.startX) / dayWidth.value);
  const task = tasks.value.find(t => t.name === resizing.value!.name);
  if (!task) return;
  if (resizing.value.edge === "right") {
    const en = new Date(resizing.value.origEnd); en.setDate(en.getDate() + days);
    if (en >= new Date(resizing.value.origStart)) task.exp_end_date = en.toISOString().slice(0, 10);
  } else {
    const s = new Date(resizing.value.origStart); s.setDate(s.getDate() + days);
    if (s <= new Date(resizing.value.origEnd)) task.exp_start_date = s.toISOString().slice(0, 10);
  }
}

async function onResizeMouseUp() {
  window.removeEventListener("mousemove", onResizeMouseMove);
  window.removeEventListener("mouseup", onResizeMouseUp);
  if (!resizing.value) return;
  const task = tasks.value.find(t => t.name === resizing.value!.name);
  if (task) await frappeSave("Task", task.name, { exp_start_date: task.exp_start_date, exp_end_date: task.exp_end_date }).catch(console.error);
  resizing.value = null;
}

// Click on empty row area to create task with that start date
function onRowDateClick(col: DayCol, task?: any) {
  const iso = col.date.toISOString().slice(0, 10);
  createTask({ exp_start_date: iso, exp_end_date: iso, parent_task: task?.name || null });
}

// Toggle parent collapse
function toggleCollapse(taskName: string) {
  const s = new Set(collapsedParents.value);
  s.has(taskName) ? s.delete(taskName) : s.add(taskName);
  collapsedParents.value = s;
}

// Format helpers
function fmtDate(d?: string) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function fmtDateRange(task: any) {
  if (!task.exp_start_date || !task.exp_end_date) return "";
  const s = new Date(task.exp_start_date), e = new Date(task.exp_end_date);
  if (s.getMonth() === e.getMonth()) return `${MONTH_ABBR[s.getMonth()]} ${s.getDate()}–${e.getDate()}`;
  return `${fmtDate(task.exp_start_date)} – ${fmtDate(task.exp_end_date)}`;
}

function assignee(task: any) { return assigneeFromTask(task._assign) || task.assigned_to || ""; }

const summaryLabel = computed(() => {
  const n = tasks.value.length, wk = Math.ceil(totalDays.value / 7);
  return `${n} task${n !== 1 ? "s" : ""} · ${wk} week horizon`;
});
</script>

<template>
  <div class="tw-page">

    <!-- ── Page header ──────────────────────────────────────────────────────── -->
    <div class="tw-head">
      <div class="tw-head-left">
        <div class="tw-tabs">
          <button class="tw-tab" :class="{ active: activeTab === 'gantt' }"    @click="setTab('gantt')">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M2 4h5M2 8h9M2 12h7"/></svg>
            Gantt
          </button>
          <button class="tw-tab" :class="{ active: activeTab === 'kanban' }"  @click="setTab('kanban')">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><rect x="2" y="2" width="4" height="12" rx="1"/><rect x="8" y="2" width="4" height="8" rx="1"/><rect x="14" y="2" width="4" height="10" rx="1" transform="translate(-4 0)"/></svg>
            Kanban
          </button>
          <button class="tw-tab" :class="{ active: activeTab === 'calendar' }" @click="setTab('calendar')">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><rect x="1.5" y="2.5" width="13" height="12" rx="1"/><path d="M5 1.5v2M11 1.5v2M1.5 6.5h13"/></svg>
            Calendar
          </button>
        </div>
        <span v-if="!loading && activeTab === 'gantt'" class="tw-meta">{{ summaryLabel }}</span>
      </div>

      <div class="tw-head-right">
        <!-- Gantt-only controls -->
        <template v-if="activeTab === 'gantt'">
          <div class="view-tabs">
            <button class="view-tab" :class="{ active: ganttView === 'day' }"   @click="ganttView = 'day'">Day</button>
            <button class="view-tab" :class="{ active: ganttView === 'week' }"  @click="ganttView = 'week'">Week</button>
            <button class="view-tab" :class="{ active: ganttView === 'month' }" @click="ganttView = 'month'">Month</button>
          </div>
          <button
            class="btn-ghost"
            :class="{ active: groupByCategory }"
            @click="groupByCategory = !groupByCategory"
          >
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M2 4h12M5 8h6M8 12h.01"/></svg>
            Group by category
          </button>
        </template>

        <button class="btn-ghost" @click="createTask({})">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3v10M3 8h10"/></svg>
          Add Task
        </button>
      </div>
    </div>

    <!-- ── Loading ─────────────────────────────────────────────────────────── -->
    <div v-if="loading" class="tw-loading">
      <div class="tw-spinner" /> Loading…
    </div>

    <!-- ── Gantt tab ────────────────────────────────────────────────────────── -->
    <div v-else-if="activeTab === 'gantt'" class="gantt-wrap">
      <div class="gantt">

        <!-- Left frozen panel -->
        <div class="gantt-left">
          <div class="gantt-left-header">
            <span>TASK</span>
            <span class="gl-col-dates">DATES</span>
          </div>

          <div
            v-for="task in ganttTasks"
            :key="task.name"
            class="gantt-left-row"
            :class="{ 'gl-no-date': !taskBar(task) }"
            :style="{ paddingLeft: (12 + (task.depth || 0) * 16) + 'px' }"
            @click="openTask(task)"
          >
            <!-- Collapse toggle for parents -->
            <button
              v-if="task.child_count > 0"
              class="gl-collapse-btn"
              @click.stop="toggleCollapse(task.name)"
              :title="collapsedParents.has(task.name) ? 'Expand' : 'Collapse'"
            >
              <span :class="collapsedParents.has(task.name) ? 'gl-chevron-right' : 'gl-chevron-down'">▾</span>
            </button>
            <span v-else class="gl-collapse-placeholder" />

            <span class="gl-task-name">{{ task.subject }}</span>

            <span v-if="task.child_count > 0" class="gl-subtask-badge">
              {{ task.child_count }}
            </span>

            <Avatar v-if="assignee(task)" :name="assignee(task)" :size="18" class="gl-avatar" />

            <span v-if="task.exp_start_date" class="gl-dates mono">
              {{ fmtDate(task.exp_start_date) }}
            </span>
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
              <div v-if="todayOffset >= 0" class="today-line" :style="{ left: todayOffset + 'px' }" />

              <!-- Category section headers (group by category mode) -->
              <template v-if="groupByCategory">
                <template v-for="(cat, ci) in [...new Set(ganttTasks.map(t => t.ep_action_category || '__none__'))]" :key="cat">
                  <div class="gantt-cat-header" :style="{ background: categoryColor(cat) + '22', borderLeft: '3px solid ' + categoryColor(cat) }">
                    <span class="gch-label">{{ categories.find(c => c.name === cat)?.title || (cat === '__none__' ? 'Uncategorised' : cat) }}</span>
                    <span class="gch-count">{{ ganttTasks.filter(t => (t.ep_action_category || '__none__') === cat).length }} tasks</span>
                  </div>
                  <div
                    v-for="task in ganttTasks.filter(t => (t.ep_action_category || '__none__') === cat)"
                    :key="task.name"
                    class="gantt-row"
                    @click.self="onRowDateClick(dayColumns[0], task)"
                  >
                    <!-- Weekend/today bg shading -->
                    <div v-for="col in dayColumns" :key="col.idx" class="gcol-shade" :class="{ 'weekend-shade': col.isWeekend, 'today-shade': col.isToday }" :style="{ left: col.idx * dayWidth + 'px', width: dayWidth + 'px' }" />
                    <!-- Row click to create -->
                    <div class="gantt-row-hit" v-for="col in dayColumns" :key="'hit-'+col.idx" :style="{ left: col.idx * dayWidth + 'px', width: dayWidth + 'px' }" @click.stop="onRowDateClick(col)" />
                    <template v-if="taskBar(task)">
                      <div class="gantt-bar" :style="{ left: taskBar(task)!.left + 'px', width: taskBar(task)!.width + 'px', background: taskColor(task), marginLeft: (task.depth || 0) * 10 + 'px' }" :title="`${task.subject} · ${fmtDateRange(task)}`" @mousedown="(e) => onBarMouseDown(e, task)" @click.stop="openTask(task)">
                        <div class="bar-resize bar-resize--left" @mousedown.stop="(e) => onResizeMouseDown(e, task, 'left')" />
                        <span class="bar-label">{{ task.subject }}</span>
                        <span v-if="taskBar(task)!.width > 100" class="bar-date mono">{{ fmtDateRange(task) }}</span>
                        <div class="bar-resize bar-resize--right" @mousedown.stop="(e) => onResizeMouseDown(e, task, 'right')" />
                      </div>
                    </template>
                  </div>
                </template>
              </template>

              <!-- Flat mode (default) -->
              <template v-else>
                <div
                  v-for="task in ganttTasks"
                  :key="task.name"
                  class="gantt-row"
                >
                  <div v-for="col in dayColumns" :key="col.idx" class="gcol-shade" :class="{ 'weekend-shade': col.isWeekend, 'today-shade': col.isToday }" :style="{ left: col.idx * dayWidth + 'px', width: dayWidth + 'px' }" />
                  <div v-for="col in dayColumns" :key="'hit-'+col.idx" class="gantt-row-hit" :style="{ left: col.idx * dayWidth + 'px', width: dayWidth + 'px' }" @click.stop="onRowDateClick(col)" />
                  <template v-if="taskBar(task)">
                    <div class="gantt-bar" :style="{ left: taskBar(task)!.left + 'px', width: taskBar(task)!.width + 'px', background: taskColor(task), marginLeft: (task.depth || 0) * 10 + 'px' }" :title="`${task.subject} · ${fmtDateRange(task)}`" @mousedown="(e) => onBarMouseDown(e, task)" @click.stop="openTask(task)">
                      <div class="bar-resize bar-resize--left" @mousedown.stop="(e) => onResizeMouseDown(e, task, 'left')" />
                      <span class="bar-label">{{ task.subject }}</span>
                      <span v-if="taskBar(task)!.width > 100" class="bar-date mono">{{ fmtDateRange(task) }}</span>
                      <div class="bar-resize bar-resize--right" @mousedown.stop="(e) => onResizeMouseDown(e, task, 'right')" />
                    </div>
                  </template>
                </div>
              </template>

            </div><!-- /gantt-body -->
          </div><!-- /gantt-canvas -->
        </div><!-- /gantt-right -->
      </div><!-- /gantt -->

      <!-- Empty -->
      <div v-if="!loading && tasks.length === 0" class="tw-empty">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        <span>No tasks. <button class="tw-link" @click="createTask({})">Add the first one.</button></span>
      </div>
    </div>

    <!-- ── Kanban tab ────────────────────────────────────────────────────────── -->
    <KanbanBoard
      v-else-if="activeTab === 'kanban'"
      :tasks="tasks"
      :categories="categories"
      @open-task="openTask"
      @create-task="createTask"
      @updated="reload"
    />

    <!-- ── Calendar tab ──────────────────────────────────────────────────────── -->
    <CalendarBoard
      v-else-if="activeTab === 'calendar'"
      :tasks="tasks"
      :categories="categories"
      @open-task="openTask"
      @create-task="createTask"
      @updated="reload"
    />

    <!-- ── Task panel ────────────────────────────────────────────────────────── -->
    <TaskPanel
      v-if="panel.open"
      :task="panel.task"
      :categories="categories"
      @close="panel.open = false"
      @updated="onPanelUpdated"
    />

    <!-- ── Create dialog ─────────────────────────────────────────────────────── -->
    <TaskDialog
      v-if="dialog.open"
      :task="dialog.task"
      :project-name="projectName ?? ''"
      :categories="categories"
      @save="onDialogSave"
      @close="dialog.open = false"
    />

  </div>
</template>

<style scoped>
/* ── Page shell ──────────────────────────────────────────────────────────── */
.tw-page {
  display: flex; flex-direction: column; height: 100%; overflow: hidden;
  background: var(--bg);
}

/* ── Header ──────────────────────────────────────────────────────────────── */
.tw-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; height: 48px; border-bottom: 1px solid var(--border);
  background: var(--panel-2); flex-shrink: 0; gap: 16px; flex-wrap: wrap;
}
.tw-head-left { display: flex; align-items: center; gap: 16px; }
.tw-head-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

.tw-tabs { display: flex; gap: 0; }
.tw-tab {
  display: flex; align-items: center; gap: 6px;
  padding: 0 16px; height: 47px;
  font-size: 13px; font-weight: 500; color: var(--text-3);
  background: none; border: none; border-bottom: 2px solid transparent;
  cursor: pointer; font-family: inherit;
  transition: color 120ms, border-color 120ms;
}
.tw-tab:hover { color: var(--text); }
.tw-tab.active { color: var(--accent-2); border-bottom-color: var(--accent); }

.tw-meta { font-size: 12px; color: var(--text-3); }

.view-tabs { display: flex; border: 1px solid var(--border-2); border-radius: 6px; overflow: hidden; }
.view-tab  { font-size: 12px; font-weight: 500; padding: 4px 10px; border: none; background: none; cursor: pointer; font-family: inherit; color: var(--text-2); }
.view-tab.active { background: var(--accent); color: white; }
.view-tab:hover:not(.active) { background: var(--row-hover); }

.btn-ghost {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 10px; height: 28px; border: 1px solid var(--border-2);
  border-radius: 6px; background: var(--panel); color: var(--text-2);
  font-size: 12px; font-weight: 500; cursor: pointer;
  transition: background 120ms, color 120ms; white-space: nowrap;
}
.btn-ghost:hover  { background: var(--bg-2); color: var(--text); }
.btn-ghost.active { background: var(--accent-soft); border-color: var(--accent); color: var(--accent-2); }

/* ── Loading / empty ────────────────────────────────────────────────────── */
.tw-loading {
  flex: 1; display: flex; align-items: center; justify-content: center;
  gap: 10px; font-size: 13px; color: var(--text-3);
}
.tw-spinner {
  width: 16px; height: 16px; border: 2px solid var(--border);
  border-top-color: var(--accent); border-radius: 50%;
  animation: twSpin .7s linear infinite;
}
@keyframes twSpin { to { transform: rotate(360deg); } }
.tw-empty {
  padding: 40px; display: flex; align-items: center; justify-content: center;
  gap: 10px; font-size: 13px; color: var(--text-3);
}
.tw-link { background: none; border: none; color: var(--accent); cursor: pointer; font-size: 13px; font-weight: 500; }
.tw-link:hover { text-decoration: underline; }

/* ════════════════════════════════════════════════════════════════════════════
   GANTT STYLES
   ════════════════════════════════════════════════════════════════════════════ */
.gantt-wrap { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.gantt { display: flex; flex: 1; overflow: hidden; }

/* Left frozen panel */
.gantt-left {
  width: 260px; flex-shrink: 0; border-right: 1px solid var(--border);
  display: flex; flex-direction: column; overflow-y: auto; overflow-x: hidden;
}
.gantt-left-header {
  display: flex; align-items: center; justify-content: space-between;
  height: 40px; padding: 0 12px; border-bottom: 1px solid var(--border);
  font-size: 10.5px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
  color: var(--text-3); background: var(--panel-2); flex-shrink: 0;
}
.gl-col-dates { font-size: 10px; color: var(--text-3); }

.gantt-left-row {
  display: flex; align-items: center; gap: 6px; padding: 0 12px;
  height: 36px; border-bottom: 1px solid var(--border);
  cursor: pointer; transition: background 100ms;
  font-size: 12.5px; color: var(--text);
}
.gantt-left-row:hover { background: var(--row-hover); }
.gl-no-date { opacity: .55; }

.gl-collapse-btn {
  width: 16px; height: 16px; border: none; background: none;
  cursor: pointer; padding: 0; color: var(--text-3); font-size: 12px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.gl-collapse-btn:hover { color: var(--text); }
.gl-chevron-right { display: inline-block; transform: rotate(-90deg); }
.gl-chevron-down  { display: inline-block; }
.gl-collapse-placeholder { width: 16px; flex-shrink: 0; }

.gl-task-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500; }
.gl-subtask-badge { font-size: 10px; background: var(--bg-2); border: 1px solid var(--border); border-radius: 8px; padding: 1px 5px; color: var(--text-3); flex-shrink: 0; }
.gl-avatar { flex-shrink: 0; }
.gl-dates { font-size: 10.5px; color: var(--text-3); flex-shrink: 0; display: none; }

/* Right scrollable canvas */
.gantt-right { flex: 1; overflow: auto; }
.gantt-canvas { position: relative; }

.gantt-header {
  display: flex; height: 40px; border-bottom: 1px solid var(--border);
  background: var(--panel-2); position: sticky; top: 0; z-index: 5;
}
.gantt-hcol {
  flex-shrink: 0; display: flex; flex-direction: column; align-items: center;
  justify-content: center; border-right: 1px solid var(--border);
  font-size: 10px; gap: 2px;
}
.is-weekend { background: rgba(26,25,21,.025); }
.is-today   { background: color-mix(in srgb, var(--accent) 8%, transparent); }
.hcol-letter { color: var(--text-3); font-weight: 600; line-height: 1; font-size: 9.5px; }
.hcol-num { color: var(--text-2); font-weight: 600; font-size: 11px; position: relative; }
.hcol-month { color: var(--accent); font-size: 9px; }
.today-pill {
  position: absolute; top: 2px; font-size: 7px; font-weight: 700; letter-spacing: .06em;
  color: var(--accent); text-transform: uppercase;
}

.gantt-body { position: relative; min-height: 200px; }
.today-line {
  position: absolute; top: 0; bottom: 0; width: 1px;
  background: var(--accent); z-index: 3; pointer-events: none;
}

.gantt-row {
  position: relative; height: 36px; border-bottom: 1px solid var(--border);
}
.gantt-row:hover > .gantt-row-hit { background: rgba(204,120,92,.04); }

.gcol-shade {
  position: absolute; top: 0; bottom: 0; pointer-events: none;
}
.weekend-shade { background: rgba(26,25,21,.018); }
.today-shade   { background: color-mix(in srgb, var(--accent) 5%, transparent); }

.gantt-row-hit {
  position: absolute; top: 0; bottom: 0; cursor: crosshair; z-index: 1;
}

/* Category header rows */
.gantt-cat-header {
  display: flex; align-items: center; gap: 10px; padding: 0 12px;
  height: 26px; border-bottom: 1px solid var(--border);
  position: sticky; top: 40px; z-index: 4;
}
.gch-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--text-2); }
.gch-count { font-size: 10.5px; color: var(--text-3); }

/* Task bar */
.gantt-bar {
  position: absolute; top: 6px; height: 24px; border-radius: 5px;
  cursor: grab; display: flex; align-items: center; z-index: 2; overflow: hidden;
  box-shadow: 0 1px 3px rgba(26,25,21,.12); transition: filter 100ms;
}
.gantt-bar:hover { filter: brightness(1.08); }
.gantt-bar:active { cursor: grabbing; }
.bar-label { font-size: 11px; font-weight: 600; color: white; padding: 0 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; }
.bar-date { font-size: 10px; color: rgba(255,255,255,.75); padding-right: 8px; white-space: nowrap; flex-shrink: 0; }
.bar-resize { width: 6px; height: 100%; cursor: ew-resize; flex-shrink: 0; }
.bar-resize:hover { background: rgba(255,255,255,.2); }
.bar-resize--left  { margin-right: auto; position: absolute; left: 0; top: 0; }
.bar-resize--right { margin-left: auto; position: absolute; right: 0; top: 0; }

/* ── Mobile ──────────────────────────────────────────────────────────────────*/
@media (max-width: 767px) {
  .tw-header { flex-direction: column; align-items: flex-start; gap: 8px; }
  .tw-header__right { flex-wrap: wrap; }
  /* Keep Gantt tab visible but hide actual gantt content */
  .gantt-scroll, .gantt-grid-wrap { display: none !important; }
  .gantt-wrap > *:not(.tw-tabs):not(.tw-header) { display: none; }
}
</style>
