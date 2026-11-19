<script setup lang="ts">
import { computed, inject, onMounted, ref, watch, type Ref } from "vue";
import Btn from "../components/Btn.vue";
import Avatar from "../components/Avatar.vue";
import Icons from "../components/Icons.vue";
import TaskDialog from "../components/TaskDialog.vue";
import TaskPanel from "../components/TaskPanel.vue";
import CategoryManager from "../components/CategoryManager.vue";
import { frappeCall, frappeList, frappeSave } from "../composables/useFrappe";
import { assignJsonForUser, assigneeFromTask } from "../utils/assignment";

const project     = inject<Ref<any>>("project");
const projectName = inject<Ref<string>>("projectName");

const categories  = ref<any[]>([]);
const tasks       = ref<any[]>([]);
const loading     = ref(true);
const collapsed   = ref<Set<string>>(new Set());

// Multi-select
const selected    = ref<Set<string>>(new Set());

// Popovers
const showBulkAssign  = ref(false);
const showBulkStatus  = ref(false);
const showBulkMove    = ref(false);
const bulkUserSearch  = ref("");
const bulkUserResults = ref<any[]>([]);

// Dialog (create)
const dialog = ref<{ open: boolean; task: any | null }>({ open: false, task: null });
// Side panel
const panel  = ref<{ open: boolean; task: any | null }>({ open: false, task: null });
// Category manager
const showCategoryManager = ref(false);

const STATUS_COLOR: Record<string, string> = {
  Open:             "#6C7280",
  Working:          "#F59E0B",
  "Pending Review": "#A78BFA",
  Overdue:          "#EF4444",
  Completed:        "#22C55E",
  Cancelled:        "#9CA3AF",
};
const STATUS_LIST = ["Open", "Working", "Pending Review", "Overdue", "Completed", "Cancelled"];

onMounted(async () => {
  if (!projectName?.value) return;
  await reload();
});

async function reload() {
  loading.value = true;
  try {
    const [cats, tks] = await Promise.all([
      frappeCall("event_planner.api.list_categories", { project: projectName!.value }),
      frappeList("Task", {
        filters: { project: projectName!.value },
        fields: [
          "name", "subject", "status", "_assign", "assigned_to",
          "exp_start_date", "exp_end_date",
          "ep_action_category", "ep_sort_order", "description", "priority",
        ],
        limit: 500,
        order_by: "ep_sort_order asc, creation asc",
      }),
    ]);
    categories.value = cats;
    tasks.value = tks;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

// ── Grouping ──────────────────────────────────────────────────────────────────
const grouped = computed(() => {
  const map: Record<string, any[]> = { __none__: [] };
  for (const c of categories.value) map[c.name] = [];
  for (const t of tasks.value) {
    const key = t.ep_action_category || "__none__";
    if (!map[key]) map[key] = [];
    map[key].push(t);
  }
  const result = [];
  for (const c of categories.value) {
    result.push({ key: c.name, label: c.title, color: c.color, items: map[c.name] ?? [] });
  }
  if (map["__none__"].length) {
    result.push({ key: "__none__", label: "Uncategorised", color: "#8F8A7E", items: map["__none__"] });
  }
  return result;
});

const completedCount = computed(() => tasks.value.filter(t => t.status === "Completed").length);

// ── Multi-select ──────────────────────────────────────────────────────────────
function toggleSelect(name: string, e: Event) {
  e.stopPropagation();
  const s = new Set(selected.value);
  if (s.has(name)) s.delete(name);
  else s.add(name);
  selected.value = s;
}

function clearSelection() {
  selected.value = new Set();
  showBulkAssign.value = false;
  showBulkStatus.value = false;
  showBulkMove.value   = false;
}

watch(bulkUserSearch, async (q) => {
  if (!q || q.length < 2) { bulkUserResults.value = []; return; }
  bulkUserResults.value = await frappeList("User", {
    filters: [["full_name", "like", `%${q}%`], ["enabled", "=", 1]],
    fields: ["name", "full_name"],
    limit: 8,
  });
});

async function bulkAssign(user: any) {
  const assign = assignJsonForUser(user.name);
  for (const name of selected.value) {
    const t = tasks.value.find(t => t.name === name);
    if (t) t._assign = assign;
    await frappeSave("Task", name, { _assign: assign }).catch(console.error);
  }
  bulkUserSearch.value = "";
  showBulkAssign.value = false;
  clearSelection();
}

async function bulkSetStatus(status: string) {
  for (const name of selected.value) {
    const t = tasks.value.find(t => t.name === name);
    if (t) t.status = status;
    await frappeSave("Task", name, { status }).catch(console.error);
  }
  showBulkStatus.value = false;
  clearSelection();
}

async function bulkMoveCategory(catName: string) {
  const cat = catName === "__none__" ? "" : catName;
  for (const name of selected.value) {
    const t = tasks.value.find(t => t.name === name);
    if (t) t.ep_action_category = cat;
    await frappeSave("Task", name, { ep_action_category: cat }).catch(console.error);
  }
  showBulkMove.value = false;
  clearSelection();
}

// ── Drag / drop ───────────────────────────────────────────────────────────────
const drag = ref<{ fromCat: string; fromIdx: number } | null>(null);

function onDragStart(catKey: string, idx: number) { drag.value = { fromCat: catKey, fromIdx: idx }; }
function onDragOver(e: DragEvent) { e.preventDefault(); }
function onDrop(catKey: string, toIdx: number) {
  if (!drag.value) return;
  const { fromCat, fromIdx } = drag.value;
  drag.value = null;
  const fromGroup = grouped.value.find(g => g.key === fromCat);
  const toGroup   = grouped.value.find(g => g.key === catKey);
  if (!fromGroup || !toGroup) return;
  const [moved] = fromGroup.items.splice(fromIdx, 1);
  if (fromCat !== catKey) {
    moved.ep_action_category = catKey === "__none__" ? "" : catKey;
    frappeSave("Task", moved.name, { ep_action_category: moved.ep_action_category }).catch(console.error);
  }
  toGroup.items.splice(toIdx, 0, moved);
  frappeCall("event_planner.api.reorder_tasks_in_category", {
    project: projectName!.value,
    category: catKey === "__none__" ? "" : catKey,
    ordered_names: toGroup.items.map(t => t.name),
  }).catch(console.error);
}

// ── Status cycle ──────────────────────────────────────────────────────────────
async function cycleStatus(task: any, e: Event) {
  e.stopPropagation();
  const CYCLE = ["Open", "Working", "Pending Review", "Completed"];
  const next = CYCLE[(CYCLE.indexOf(task.status) + 1) % CYCLE.length];
  task.status = next;
  await frappeSave("Task", task.name, { status: next });
}

// ── Create / Panel ────────────────────────────────────────────────────────────
function openCreate(categoryKey: string) {
  dialog.value = {
    open: true,
    task: {
      ep_action_category: categoryKey === "__none__" || categoryKey === "" ? "" : categoryKey,
      project: projectName!.value,
    },
  };
}

function openPanel(task: any) {
  panel.value = { open: true, task: { ...task } };
}

function onPanelUpdated(saved: any) {
  const idx = tasks.value.findIndex(t => t.name === saved.name);
  if (idx !== -1) {
    tasks.value[idx] = { ...tasks.value[idx], ...saved };
  }
  if (panel.value.task?.name === saved.name) {
    panel.value.task = { ...panel.value.task, ...saved };
  }
}

async function onDialogSave(taskData: any) {
  try {
    await frappeSave("Task", taskData.name ?? null, {
      subject: taskData.subject,
      project: projectName!.value,
      ep_action_category: taskData.ep_action_category,
      _assign: assignJsonForUser(taskData.assignee),
      exp_start_date: taskData.exp_start_date,
      exp_end_date: taskData.exp_end_date,
      description: taskData.description,
      priority: taskData.priority,
    });
    dialog.value.open = false;
    await reload();
  } catch (e) { console.error(e); }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtDate(d?: string) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function assignee(task: any): string { return assigneeFromTask(task._assign); }

function catColor(catName: string): string {
  return categories.value.find(c => c.name === catName)?.color || "#8F8A7E";
}

function categoryLabel(catName: string): string {
  return categories.value.find(c => c.name === catName)?.title || catName;
}

function shortId(name: string) {
  const m = name.match(/(\d+)$/);
  return m ? `#${parseInt(m[1], 10)}` : name.slice(0, 7);
}

// Unique assignees in a group (for avatar stack)
function groupAssignees(items: any[]): string[] {
  const seen = new Set<string>();
  return items
    .map(t => assigneeFromTask(t._assign))
    .filter(a => { if (!a || seen.has(a)) return false; seen.add(a); return true; })
    .slice(0, 4);
}

function toggleCollapse(key: string) {
  const s = new Set(collapsed.value);
  if (s.has(key)) s.delete(key); else s.add(key);
  collapsed.value = s;
}

function isOverdue(task: any) {
  return task.status !== "Completed" && task.exp_end_date
    && task.exp_end_date < new Date().toISOString().slice(0, 10);
}
</script>

<template>
  <div class="ap-wrap">
    <!-- ── Page header ──────────────────────────────────────────────── -->
    <div class="ap-head">
      <div class="ap-head__left">
        <h1 class="ap-title">Action Plan</h1>
        <div class="ap-sub" v-if="!loading">
          {{ completedCount }}/{{ tasks.length }} tasks complete
          <span class="ap-sub__dot">·</span>
          click any row to open detail
        </div>
      </div>
      <div class="ap-head__right">
        <button class="ghost-btn"><Icons name="filter" :size="13" /> Filter</button>
        <button class="ghost-btn"><Icons name="download" :size="13" /> Export PDF</button>
        <button class="ghost-btn" @click="showCategoryManager = true">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4h10M3 8h7M3 12h5"/><circle cx="13" cy="10.5" r="2.5"/><path d="M13 9v1.5l1 1"/></svg>
          Categories
        </button>
        <button class="primary-btn" @click="openCreate('')">
          <Icons name="plus" :size="13" /> Add Task
        </button>
      </div>
    </div>

    <!-- ── Multi-select action bar ─────────────────────────────────── -->
    <Transition name="bar">
      <div v-if="selected.size > 0" class="action-bar">
        <div class="action-bar__left">
          <button class="ab-check-btn" @click="clearSelection">
            <Icons name="check" :size="12" />
          </button>
          <span class="ab-count">{{ selected.size }} selected</span>

          <!-- Assign -->
          <div class="ab-popover-wrap" style="position:relative;">
            <button class="ab-action-btn" @click="showBulkAssign = !showBulkAssign; showBulkStatus = false; showBulkMove = false">
              Assign… <Icons name="chevdown" :size="11" />
            </button>
            <div v-if="showBulkAssign" class="ab-drop">
              <div class="ab-drop__search">
                <input v-model="bulkUserSearch" placeholder="Search user…" class="ab-input" autofocus />
              </div>
              <div class="ab-drop__results">
                <div v-if="!bulkUserResults.length && bulkUserSearch.length >= 2" class="ab-drop__empty">No results</div>
                <button
                  v-for="u in bulkUserResults"
                  :key="u.name"
                  class="ab-drop__item"
                  @click="bulkAssign(u)"
                >
                  <Avatar :name="u.name" :size="18" />
                  <span>{{ u.full_name || u.name }}</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Set Status -->
          <div style="position:relative;">
            <button class="ab-action-btn" @click="showBulkStatus = !showBulkStatus; showBulkAssign = false; showBulkMove = false">
              Set Status… <Icons name="chevdown" :size="11" />
            </button>
            <div v-if="showBulkStatus" class="ab-drop">
              <button
                v-for="s in STATUS_LIST"
                :key="s"
                class="ab-drop__item"
                @click="bulkSetStatus(s)"
              >
                <span class="status-dot-sm" :style="{ background: STATUS_COLOR[s] || '#8F8A7E' }" />
                {{ s }}
              </button>
            </div>
          </div>

          <!-- Move to -->
          <div style="position:relative;">
            <button class="ab-action-btn" @click="showBulkMove = !showBulkMove; showBulkAssign = false; showBulkStatus = false">
              Move to… <Icons name="chevdown" :size="11" />
            </button>
            <div v-if="showBulkMove" class="ab-drop">
              <button class="ab-drop__item" @click="bulkMoveCategory('__none__')">
                <span class="cat-dot-sm" style="background: var(--text-3)" />
                Uncategorised
              </button>
              <button
                v-for="c in categories"
                :key="c.name"
                class="ab-drop__item"
                @click="bulkMoveCategory(c.name)"
              >
                <span class="cat-dot-sm" :style="{ background: c.color || 'var(--text-3)' }" />
                {{ c.title }}
              </button>
            </div>
          </div>
        </div>

        <div class="action-bar__right">
          <button class="ab-cancel-btn" @click="clearSelection">Cancel</button>
        </div>
      </div>
    </Transition>

    <!-- ── Loading ──────────────────────────────────────────────────── -->
    <div v-if="loading" class="ap-loading">
      <div class="ap-spinner" /> Loading tasks…
    </div>

    <!-- ── Table ────────────────────────────────────────────────────── -->
    <div v-else class="ap-table">
      <!-- Column headers -->
      <div class="ap-col-head">
        <span /><!-- drag -->
        <span /><!-- checkbox -->
        <span class="col-lbl">Task</span>
        <span /><!-- title (part of task) -->
        <span class="col-lbl">Category</span>
        <span class="col-lbl">Assignee</span>
        <span class="col-lbl">Status</span>
        <span class="col-lbl">Due</span>
      </div>

      <!-- Groups -->
      <div
        v-for="group in grouped"
        :key="group.key"
        class="ap-group"
        @dragover="onDragOver"
        @drop="onDrop(group.key, group.items.length)"
      >
        <!-- Group header -->
        <div class="grp-head" @click="toggleCollapse(group.key)">
          <span class="grp-chevron" :class="{ 'grp-chevron--closed': collapsed.has(group.key) }">
            <Icons name="chevdown" :size="12" />
          </span>
          <span class="grp-dot" :style="{ background: group.color || '#8F8A7E' }" />
          <span class="grp-name">{{ group.label }}</span>
          <span class="grp-count mono">{{ group.items.length }} items</span>

          <!-- Avatar stack -->
          <div class="grp-avatars">
            <Avatar
              v-for="(a, i) in groupAssignees(group.items)"
              :key="a"
              :name="a"
              :size="20"
              :style="{ marginLeft: i > 0 ? '-6px' : '0', zIndex: 10 - i }"
            />
          </div>

          <button class="grp-add-btn" @click.stop="openCreate(group.key)">
            <Icons name="plus" :size="11" /> Add
          </button>
        </div>

        <!-- Task rows -->
        <template v-if="!collapsed.has(group.key)">
          <div
            v-for="(task, idx) in group.items"
            :key="task.name"
            class="ap-row"
            :class="{ 'ap-row--selected': selected.has(task.name) }"
            draggable="true"
            @dragstart="onDragStart(group.key, idx)"
            @drop.stop="onDrop(group.key, idx)"
            @dragover.stop="onDragOver"
            @click="openPanel(task)"
          >
            <!-- Drag handle -->
            <span class="ap-drag" @click.stop>
              <Icons name="drag" :size="13" />
            </span>

            <!-- Checkbox -->
            <span class="ap-cb" @click.stop="toggleSelect(task.name, $event)">
              <span class="cb-box" :class="{ 'cb-box--checked': selected.has(task.name) }">
                <Icons v-if="selected.has(task.name)" name="check" :size="10" />
              </span>
            </span>

            <!-- ID + Subject -->
            <span class="ap-id mono">{{ shortId(task.name) }}</span>
            <span class="ap-subject">{{ task.subject }}</span>

            <!-- Category pill -->
            <span class="ap-cat">
              <span v-if="task.ep_action_category" class="cat-pill" :style="{ '--cat-c': catColor(task.ep_action_category) }">
                <span class="cat-pill__dot" />
                {{ categoryLabel(task.ep_action_category) }}
              </span>
              <span v-else class="ap-empty">—</span>
            </span>

            <!-- Assignee -->
            <span class="ap-assignee">
              <template v-if="assignee(task)">
                <Avatar :name="assignee(task)" :size="20" />
                <span class="ap-assignee__name">{{ assignee(task).split('@')[0] }}</span>
              </template>
              <span v-else class="ap-empty">—</span>
            </span>

            <!-- Status pill -->
            <span class="ap-status" @click.stop="cycleStatus(task, $event)">
              <span
                class="status-pill"
                :style="{
                  '--st-c': STATUS_COLOR[task.status] || '#8F8A7E',
                }"
              >
                <span class="status-pill__dot" />
                {{ task.status }}
              </span>
            </span>

            <!-- Due date -->
            <span class="ap-due mono" :class="{ 'ap-due--over': isOverdue(task) }">
              {{ fmtDate(task.exp_end_date) || '—' }}
            </span>
          </div>

          <!-- Add task inline row -->
          <button class="ap-add-row" @click="openCreate(group.key)">
            <Icons name="plus" :size="12" />
            Add task in {{ group.label }}
          </button>
        </template>
      </div>
    </div>

    <!-- Create dialog -->
    <TaskDialog
      v-if="dialog.open"
      :task="dialog.task"
      :project-name="projectName ?? ''"
      :categories="categories"
      @save="onDialogSave"
      @close="dialog.open = false"
    />

    <!-- Task side panel -->
    <TaskPanel
      v-if="panel.open"
      :task="panel.task"
      :categories="categories"
      @close="panel.open = false"
      @updated="onPanelUpdated"
    />

    <!-- Category manager -->
    <CategoryManager
      v-if="showCategoryManager && projectName"
      :project-name="projectName"
      @close="showCategoryManager = false"
      @updated="reload"
    />
  </div>
</template>

<style scoped>
/* ── Wrapper ───────────────────────────────────────────────────────────────── */
.ap-wrap { padding: 20px 24px 60px; width: 100%; flex: 1; }

/* ── Head ──────────────────────────────────────────────────────────────────── */
.ap-head {
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 16px; margin-bottom: 14px;
}
.ap-title { font-size: 17px; font-weight: 600; letter-spacing: -.02em; margin: 0; }
.ap-sub { font-size: 12px; color: var(--text-3); margin-top: 3px; }
.ap-sub__dot { margin: 0 5px; }
.ap-head__right { display: flex; align-items: center; gap: 7px; }

.ghost-btn {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--panel); border: 1px solid var(--border-2);
  border-radius: 6px; padding: 5px 11px; font-size: 12.5px;
  color: var(--text-2); cursor: pointer; font-family: inherit;
  font-weight: 500;
}
.ghost-btn:hover { background: var(--row-hover); }

.primary-btn {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--accent); border: 1px solid rgba(0,0,0,.1);
  border-radius: 6px; padding: 5px 13px; font-size: 12.5px;
  color: #fff; cursor: pointer; font-family: inherit; font-weight: 600;
}
.primary-btn:hover { background: var(--accent-2); }

/* ── Action bar ────────────────────────────────────────────────────────────── */
.action-bar {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--panel); border: 1px solid var(--border-2);
  border-radius: 8px; padding: 7px 12px; margin-bottom: 10px;
  box-shadow: 0 2px 8px rgba(0,0,0,.07);
}
.action-bar__left { display: flex; align-items: center; gap: 8px; }
.ab-check-btn {
  width: 22px; height: 22px; border-radius: 5px;
  background: var(--accent); border: none; color: #fff;
  cursor: pointer; display: inline-flex; align-items: center; justify-content: center;
}
.ab-count { font-size: 12.5px; font-weight: 600; color: var(--text); margin-right: 4px; }
.ab-action-btn {
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--panel-2); border: 1px solid var(--border-2);
  border-radius: 6px; padding: 4px 10px; font-size: 12px;
  color: var(--text-2); cursor: pointer; font-family: inherit;
}
.ab-action-btn:hover { background: var(--row-hover); color: var(--text); }
.ab-cancel-btn {
  background: none; border: none; cursor: pointer;
  font-size: 12px; color: var(--text-3); font-family: inherit;
}
.ab-cancel-btn:hover { color: var(--text); }

.ab-drop {
  position: absolute; top: calc(100% + 6px); left: 0; min-width: 190px;
  background: var(--panel); border: 1px solid var(--border-2);
  border-radius: 8px; box-shadow: var(--shadow-lg);
  z-index: 400; overflow: hidden; padding: 4px;
}
.ab-drop__search { padding: 6px 8px; border-bottom: 1px solid var(--border); }
.ab-input {
  width: 100%; padding: 5px 8px; border: 1px solid var(--border-2);
  border-radius: 5px; font-size: 12.5px; font-family: inherit;
  background: var(--panel-2); color: var(--text);
}
.ab-input:focus { outline: none; border-color: var(--accent); }
.ab-drop__results { max-height: 200px; overflow-y: auto; }
.ab-drop__empty { padding: 10px 12px; font-size: 12px; color: var(--text-3); }
.ab-drop__item {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 10px; border-radius: 5px;
  background: none; border: none; width: 100%;
  text-align: left; font-family: inherit; font-size: 12.5px;
  color: var(--text); cursor: pointer;
}
.ab-drop__item:hover { background: var(--row-hover); }

/* transition */
.bar-enter-active, .bar-leave-active { transition: opacity .15s, transform .15s; }
.bar-enter-from, .bar-leave-to { opacity: 0; transform: translateY(-6px); }

/* ── Loading ───────────────────────────────────────────────────────────────── */
.ap-loading { display: flex; align-items: center; gap: 8px; color: var(--text-3); padding: 40px; }
.ap-spinner {
  width: 16px; height: 16px; border: 2px solid var(--border);
  border-top-color: var(--accent); border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Table ─────────────────────────────────────────────────────────────────── */
.ap-table { display: flex; flex-direction: column; gap: 8px; }

/* Grid shared by col-head + ap-row */
.ap-col-head, .ap-row {
  display: grid;
  grid-template-columns: 24px 32px 52px minmax(180px, 1fr) 150px 160px 148px 90px;
  align-items: center;
}

.ap-col-head {
  padding: 0 0 4px 0;
}
.col-lbl {
  font-size: 10.5px; font-weight: 600; text-transform: uppercase;
  letter-spacing: .08em; color: var(--text-3); padding: 0 10px;
}

/* Groups */
.ap-group {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 9px; overflow: hidden;
}

/* Group header */
.grp-head {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 12px; border-bottom: 1px solid var(--border);
  background: var(--panel-2); cursor: pointer; user-select: none;
}
.grp-head:hover { background: var(--row-hover); }
.grp-chevron {
  color: var(--text-3); display: inline-flex;
  transition: transform 140ms ease; flex-shrink: 0;
}
.grp-chevron--closed { transform: rotate(-90deg); }
.grp-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.grp-name { font-size: 13px; font-weight: 600; letter-spacing: -.01em; }
.grp-count { font-size: 11px; color: var(--text-3); }
.grp-avatars { display: flex; align-items: center; margin-left: 6px; }
.grp-add-btn {
  margin-left: auto; display: inline-flex; align-items: center; gap: 4px;
  background: none; border: 1px solid var(--border-2);
  border-radius: 5px; padding: 3px 9px; font-size: 11.5px;
  color: var(--text-3); cursor: pointer; font-family: inherit;
}
.grp-add-btn:hover { background: var(--panel); color: var(--text); }

/* Task row */
.ap-row {
  border-bottom: 1px solid var(--border);
  cursor: pointer; transition: background 100ms;
  min-height: 40px;
}
.ap-row:last-of-type { border-bottom: none; }
.ap-row:hover { background: var(--row-hover); }
.ap-row--selected { background: var(--accent-softer); }
.ap-row--selected:hover { background: var(--accent-soft); }

.ap-drag {
  display: flex; align-items: center; justify-content: center;
  color: var(--border-2); cursor: grab; height: 40px;
}
.ap-row:hover .ap-drag { color: var(--text-3); }

.ap-cb {
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.cb-box {
  width: 15px; height: 15px; border-radius: 4px;
  border: 1.5px solid var(--border-2); background: var(--panel);
  display: flex; align-items: center; justify-content: center;
  transition: all 120ms;
}
.cb-box--checked {
  background: var(--accent); border-color: var(--accent); color: #fff;
}
.ap-row:hover .cb-box { border-color: var(--accent); }

.ap-id {
  font-size: 11px; color: var(--text-3); padding: 0 6px;
  white-space: nowrap;
}
.ap-subject {
  font-size: 13px; padding: 0 10px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  color: var(--text);
}

/* Category pill */
.ap-cat { padding: 0 10px; }
.cat-pill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 9px 3px 7px; border-radius: 999px;
  font-size: 11.5px; font-weight: 500;
  background: color-mix(in srgb, var(--cat-c) 12%, transparent);
  color: color-mix(in srgb, var(--cat-c) 80%, var(--text));
  border: 1px solid color-mix(in srgb, var(--cat-c) 25%, transparent);
  white-space: nowrap;
}
.cat-pill__dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--cat-c); flex-shrink: 0;
}

/* Assignee */
.ap-assignee {
  display: flex; align-items: center; gap: 7px; padding: 0 10px;
  overflow: hidden;
}
.ap-assignee__name {
  font-size: 12.5px; color: var(--text-2);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* Status pill */
.ap-status { padding: 0 10px; cursor: pointer; }
.status-pill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 9px 3px 7px; border-radius: 999px;
  font-size: 11.5px; font-weight: 500;
  background: color-mix(in srgb, var(--st-c) 12%, transparent);
  color: color-mix(in srgb, var(--st-c) 90%, var(--text));
  border: 1px solid color-mix(in srgb, var(--st-c) 25%, transparent);
  white-space: nowrap; cursor: pointer;
  transition: background 120ms;
}
.status-pill:hover { background: color-mix(in srgb, var(--st-c) 20%, transparent); }
.status-pill__dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--st-c); flex-shrink: 0;
}

/* Due date */
.ap-due { font-size: 12px; color: var(--text-3); padding: 0 10px; white-space: nowrap; }
.ap-due--over { color: var(--danger); font-weight: 500; }

.ap-empty { color: var(--border-2); font-size: 13px; }

/* Inline add row */
.ap-add-row {
  display: flex; align-items: center; gap: 7px;
  padding: 8px 12px 8px 52px;
  color: var(--text-3); font-size: 12px;
  background: none; border: none; border-top: 1px dashed var(--border);
  cursor: pointer; font-family: inherit; width: 100%; text-align: left;
}
.ap-add-row:hover { background: var(--row-hover); color: var(--accent); }

/* Misc */
.status-dot-sm { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.cat-dot-sm { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

/* ── Mobile responsive ────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .ap-wrap { padding: 12px 12px 48px; }

  .ap-head { flex-direction: column; align-items: flex-start; gap: 8px; margin-bottom: 10px; }
  .ap-head__right { flex-wrap: wrap; }

  /* Card-style rows on mobile */
  .ap-task-row {
    display: flex; flex-direction: column; align-items: flex-start;
    gap: 5px; padding: 10px 12px;
  }
  .ap-task-row > * { max-width: 100%; }
  .ap-subject { font-size: 13px; }

  /* Hide less critical columns */
  .ap-due, .ap-assignee { display: none; }

  /* Category header sticky */
  .ap-cat-header { position: sticky; top: 0; z-index: 2; }
}

@media (max-width: 480px) {
  .ap-head__right .ghost-btn { display: none; }
}
</style>
