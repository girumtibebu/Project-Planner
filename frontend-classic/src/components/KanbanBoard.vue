<script setup lang="ts">
import { computed, ref } from "vue";
import Avatar from "./Avatar.vue";
import { frappeSave } from "../composables/useFrappe";
import { assigneeFromTask } from "../utils/assignment";

// ── Props / emits ─────────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    tasks:      any[];
    categories: any[];
    groupBy?:   "status" | "category";
  }>(),
  { groupBy: "status" }
);

const emit = defineEmits<{
  (e: "open-task",   task: any): void;
  (e: "create-task", defaults: Partial<any>): void;
  (e: "updated"): void;
}>();

// ── Constants ─────────────────────────────────────────────────────────────────

const STATUSES = ["Open", "Working", "Pending Review", "Overdue", "Completed", "Cancelled"];
const STATUS_COLOR: Record<string, string> = {
  Open: "#6C7280", Working: "#F59E0B", "Pending Review": "#A78BFA",
  Overdue: "#EF4444", Completed: "#22C55E", Cancelled: "#9CA3AF",
};

// ── Local group-by toggle ─────────────────────────────────────────────────────

const localGroupBy = ref<"status" | "category">(props.groupBy);

// ── Columns ───────────────────────────────────────────────────────────────────

const columns = computed(() => {
  if (localGroupBy.value === "status") {
    return STATUSES.map(s => ({
      key:   s,
      label: s,
      color: STATUS_COLOR[s] || "#8F8A7E",
      items: props.tasks.filter(t => t.status === s),
    }));
  }
  // Group by category
  const catKeys = [...new Set(props.tasks.map(t => t.ep_action_category || "__none__"))];
  return catKeys.map(k => {
    const cat = props.categories.find(c => c.name === k || c.title === k);
    return {
      key:   k,
      label: cat?.title || (k === "__none__" ? "Uncategorised" : k),
      color: cat?.color || "#8F8A7E",
      items: props.tasks.filter(t => (t.ep_action_category || "__none__") === k),
    };
  });
});

// ── Drag-and-drop ─────────────────────────────────────────────────────────────

const dragging     = ref<any | null>(null);
const dragOverCol  = ref<string | null>(null);

function onCardDragStart(e: DragEvent, task: any) {
  dragging.value = task;
  e.dataTransfer!.effectAllowed = "move";
}

function onColDragOver(e: DragEvent, colKey: string) {
  if (!dragging.value) return;
  e.preventDefault();
  e.dataTransfer!.dropEffect = "move";
  dragOverCol.value = colKey;
}

function onColDragLeave() { dragOverCol.value = null; }

async function onColDrop(_e: DragEvent, colKey: string) {
  dragOverCol.value = null;
  if (!dragging.value || dragging.value.status === colKey) { dragging.value = null; return; }
  const task = dragging.value;
  dragging.value = null;

  // Optimistic update
  if (localGroupBy.value === "status") {
    task.status = colKey;
    await frappeSave("Task", task.name, { status: colKey }).catch(console.error);
  } else {
    const newCat = colKey === "__none__" ? null : colKey;
    task.ep_action_category = newCat;
    await frappeSave("Task", task.name, { ep_action_category: newCat }).catch(console.error);
  }
  emit("updated");
}

// ── Inline "add card" ─────────────────────────────────────────────────────────

const addingTo     = ref<string | null>(null);
const addingTitle  = ref("");

function startAdd(colKey: string) {
  addingTo.value    = colKey;
  addingTitle.value = "";
}

function commitAdd(colKey: string) {
  const title = addingTitle.value.trim();
  addingTo.value = null;
  if (!title) return;
  const defaults: Partial<any> =
    localGroupBy.value === "status"
      ? { status: colKey, subject: title }
      : { ep_action_category: colKey === "__none__" ? null : colKey, subject: title };
  emit("create-task", defaults);
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function assignee(task: any) { return assigneeFromTask(task._assign) || task.assigned_to || ""; }

function fmtDate(d?: string) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function isOverdue(task: any) {
  if (!task.exp_end_date || task.status === "Completed") return false;
  return new Date(task.exp_end_date) < new Date();
}
</script>

<template>
  <div class="kb-wrap">

    <!-- Group-by toggle -->
    <div class="kb-toolbar">
      <div class="kb-toggle">
        <button
          class="kb-toggle-btn"
          :class="{ active: localGroupBy === 'status' }"
          @click="localGroupBy = 'status'"
        >By Status</button>
        <button
          class="kb-toggle-btn"
          :class="{ active: localGroupBy === 'category' }"
          @click="localGroupBy = 'category'"
        >By Category</button>
      </div>
    </div>

    <!-- Kanban columns -->
    <div class="kb-board">
      <div
        v-for="col in columns"
        :key="col.key"
        class="kb-col"
        :class="{ 'kb-col--drag-over': dragOverCol === col.key }"
        @dragover="onColDragOver($event, col.key)"
        @dragleave="onColDragLeave"
        @drop="onColDrop($event, col.key)"
      >
        <!-- Column header -->
        <div class="kb-col-header">
          <span class="kb-col-dot" :style="{ background: col.color }" />
          <span class="kb-col-label">{{ col.label }}</span>
          <span class="kb-col-count">{{ col.items.length }}</span>
        </div>

        <!-- Cards -->
        <div class="kb-cards">
          <div
            v-for="task in col.items"
            :key="task.name"
            class="kb-card"
            :class="{ 'kb-card--overdue': isOverdue(task) }"
            draggable="true"
            @dragstart="onCardDragStart($event, task)"
            @click="emit('open-task', task)"
          >
            <!-- Card content -->
            <div class="kb-card-title">{{ task.subject }}</div>

            <div class="kb-card-meta">
              <!-- Category pill (status view only) -->
              <template v-if="localGroupBy === 'status' && task.ep_action_category">
                <span
                  class="kb-chip"
                  :style="{ '--c': categories.find(c => c.name === task.ep_action_category)?.color || '#8F8A7E' }"
                >{{ categories.find(c => c.name === task.ep_action_category)?.title || task.ep_action_category }}</span>
              </template>

              <!-- Date -->
              <span v-if="task.exp_end_date" class="kb-date" :class="{ 'kb-date--late': isOverdue(task) }">
                <svg width="9" height="9" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4"><rect x="1" y="2" width="10" height="9" rx="1"/><path d="M4 1v2M8 1v2M1 5h10"/></svg>
                {{ fmtDate(task.exp_end_date) }}
              </span>
            </div>

            <!-- Sub-task count -->
            <span v-if="task.child_count > 0" class="kb-subtask-badge">
              ⤷ {{ task.child_count }}
            </span>

            <!-- Assignee avatar -->
            <Avatar
              v-if="assignee(task)"
              :name="assignee(task)"
              :size="18"
              class="kb-avatar"
            />
          </div>

          <!-- Add card inline -->
          <div v-if="addingTo === col.key" class="kb-add-form">
            <textarea
              v-model="addingTitle"
              class="kb-add-input"
              placeholder="Task title…"
              rows="2"
              autofocus
              @keydown.enter.prevent="commitAdd(col.key)"
              @keydown.escape="addingTo = null"
            />
            <div class="kb-add-actions">
              <button class="kb-add-confirm" @click="commitAdd(col.key)">Add</button>
              <button class="kb-add-cancel" @click="addingTo = null">Cancel</button>
            </div>
          </div>
          <button v-else class="kb-add-btn" @click="startAdd(col.key)">
            <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2v8M2 6h8"/></svg>
            Add card
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kb-wrap { display: flex; flex-direction: column; height: 100%; overflow: hidden; }

.kb-toolbar {
  display: flex; align-items: center; padding: 10px 20px;
  border-bottom: 1px solid var(--border); flex-shrink: 0;
  background: var(--panel-2);
}

.kb-toggle { display: flex; border: 1px solid var(--border-2); border-radius: 6px; overflow: hidden; }
.kb-toggle-btn {
  font-size: 12px; font-weight: 500; padding: 5px 12px; border: none; background: none;
  cursor: pointer; font-family: inherit; color: var(--text-2); transition: background 100ms;
}
.kb-toggle-btn.active { background: var(--accent); color: white; }
.kb-toggle-btn:hover:not(.active) { background: var(--row-hover); }

/* ── Board ──────────────────────────────────────────────────────────────────── */
.kb-board {
  flex: 1; overflow-x: auto; display: flex; gap: 12px;
  padding: 16px 20px 20px; align-items: flex-start;
}

.kb-col {
  width: 240px; flex-shrink: 0; display: flex; flex-direction: column;
  background: var(--panel-2); border: 1px solid var(--border); border-radius: 10px;
  overflow: hidden; transition: border-color 120ms, background 120ms;
}
.kb-col--drag-over { border-color: var(--accent); background: var(--accent-soft); }

.kb-col-header {
  display: flex; align-items: center; gap: 7px;
  padding: 10px 12px; border-bottom: 1px solid var(--border);
  background: var(--panel); flex-shrink: 0;
}
.kb-col-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.kb-col-label { flex: 1; font-size: 12.5px; font-weight: 600; color: var(--text); }
.kb-col-count { font-size: 11px; color: var(--text-3); font-variant-numeric: tabular-nums; }

.kb-cards { flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 6px; }

/* ── Card ───────────────────────────────────────────────────────────────────── */
.kb-card {
  background: var(--panel); border: 1px solid var(--border); border-radius: 7px;
  padding: 10px 10px 8px; cursor: pointer; position: relative;
  transition: box-shadow 120ms, border-color 120ms; user-select: none;
}
.kb-card:hover { border-color: var(--accent); box-shadow: 0 2px 8px rgba(26,25,21,.06); }
.kb-card--overdue { border-left: 2px solid var(--danger); }
.kb-card[draggable="true"] { cursor: grab; }
.kb-card[draggable="true"]:active { cursor: grabbing; }

.kb-card-title {
  font-size: 13px; font-weight: 500; color: var(--text); line-height: 1.4;
  margin-bottom: 6px; word-break: break-word;
}
.kb-card-meta {
  display: flex; flex-wrap: wrap; gap: 5px; align-items: center;
}

.kb-chip {
  font-size: 10px; padding: 2px 7px; border-radius: 10px;
  background: color-mix(in srgb, var(--c) 14%, transparent);
  color: color-mix(in srgb, var(--c) 90%, var(--text));
  font-weight: 600; white-space: nowrap;
}

.kb-date {
  display: flex; align-items: center; gap: 3px;
  font-size: 10.5px; color: var(--text-3); font-weight: 500;
}
.kb-date--late { color: var(--danger); }

.kb-subtask-badge {
  position: absolute; bottom: 7px; right: 30px;
  font-size: 10px; color: var(--text-3); font-weight: 600;
}
.kb-avatar { position: absolute; bottom: 6px; right: 8px; }

/* ── Add card ───────────────────────────────────────────────────────────────── */
.kb-add-btn {
  display: flex; align-items: center; justify-content: center; gap: 5px;
  width: 100%; padding: 7px; border: 1px dashed var(--border-2); border-radius: 7px;
  background: none; color: var(--text-3); font-size: 12px; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: background 100ms, color 100ms;
}
.kb-add-btn:hover { background: var(--row-hover); color: var(--text); border-color: var(--border); }

.kb-add-form { padding: 4px; }
.kb-add-input {
  width: 100%; background: var(--panel); border: 1px solid var(--accent);
  border-radius: 5px; font-size: 13px; font-family: inherit; padding: 6px 8px;
  color: var(--text); resize: none; outline: none;
}
.kb-add-actions { display: flex; gap: 6px; margin-top: 5px; }
.kb-add-confirm {
  font-size: 12px; padding: 4px 10px; border-radius: 5px;
  background: var(--accent); border: none; color: white; cursor: pointer; font-weight: 500;
}
.kb-add-confirm:hover { background: var(--accent-2); }
.kb-add-cancel {
  font-size: 12px; padding: 4px 10px; border-radius: 5px;
  background: var(--panel-2); border: 1px solid var(--border-2); color: var(--text-2); cursor: pointer;
}
.kb-add-cancel:hover { background: var(--row-hover); }
</style>
