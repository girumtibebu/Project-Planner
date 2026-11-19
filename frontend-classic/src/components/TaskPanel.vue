<script setup lang="ts">
import { ref, watch, computed } from "vue";
import Icons from "./Icons.vue";
import Avatar from "./Avatar.vue";
import TiptapEditor from "./TiptapEditor.vue";
import ActivityFeed from "./ActivityFeed.vue";
import { frappeGet, frappeList, frappeSave, frappeCall } from "../composables/useFrappe";
import { assigneeFromTask, assignJsonForUser } from "../utils/assignment";

const props = defineProps<{
  task: any | null;
  categories: any[];
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "updated", task: any): void;
}>();

const STATUS_COLOR: Record<string, string> = {
  Open:             "#6C7280",
  Working:          "#F59E0B",
  "Pending Review": "#A78BFA",
  Overdue:          "#EF4444",
  Completed:        "#22C55E",
  Cancelled:        "#9CA3AF",
};
const STATUS_LIST = ["Open", "Working", "Pending Review", "Overdue", "Completed", "Cancelled"];
const PRIORITY_LIST = ["Low", "Medium", "High", "Urgent"];
const PRIORITY_COLOR: Record<string, string> = {
  Low: "#6C7280", Medium: "#3B82F6", High: "#F59E0B", Urgent: "#EF4444",
};

// Form state
const subject     = ref("");
const status      = ref("Open");
const category    = ref("");
const priority    = ref("");
const startDate   = ref("");
const endDate     = ref("");
const assignee    = ref("");        // user email / id
const assigneeName = ref("");       // display name
const description  = ref("");
const saving      = ref(false);
const fetchingFull = ref(false);
const saveTimer   = ref<ReturnType<typeof setTimeout> | null>(null);

// Currently displayed task name (to guard stale updates)
const loadedTaskName = ref("");

// Tab state
const activeTab = ref<"description" | "activity">("description");

// Doc meta
const taskMeta = ref<any>(null);

// Dropdown state
const showStatusDrop  = ref(false);
const showCatDrop     = ref(false);
const showAssignDrop  = ref(false);
const userSearch      = ref("");
const userResults     = ref<any[]>([]);

// ── Load task into form ────────────────────────────────────────────────────
function applyTaskToForm(t: any) {
  subject.value     = t.subject             ?? "";
  status.value      = t.status              ?? "Open";
  category.value    = t.ep_action_category  ?? "";
  priority.value    = t.priority            ?? "";
  // Dates may arrive as "YYYY-MM-DD HH:mm:ss" — keep only date part
  startDate.value   = (t.exp_start_date ?? "").slice(0, 10);
  endDate.value     = (t.exp_end_date   ?? "").slice(0, 10);
  description.value = t.description        ?? "";

  // Resolve assignee: prefer assigned_to (Link → User) then _assign (JSON)
  const a = t.assigned_to || assigneeFromTask(t._assign);
  assignee.value     = a;
  // If we already have a full_name stored, prefer that
  if (t._assignee_full_name) {
    assigneeName.value = t._assignee_full_name;
  } else {
    assigneeName.value = a ? (a.split("@")[0].replace(/[._]/g, " ")) : "";
  }
  userSearch.value = "";
}

watch(() => props.task, async (t) => {
  if (!t) return;
  loadedTaskName.value = t.name ?? "";
  taskMeta.value = null;
  activeTab.value = "description";

  // Immediately render with cached list data for responsiveness
  applyTaskToForm(t);

  // Then fetch the full document so description and all fields are complete
  if (!t.name) return;
  fetchingFull.value = true;
  try {
    const full = await frappeGet("Task", t.name);
    if (loadedTaskName.value !== t.name) return; // panel changed while loading

    // Resolve assignee full name from User
    const rawAssignee = full.assigned_to || assigneeFromTask(full._assign);
    let displayName = rawAssignee ? (rawAssignee.split("@")[0].replace(/[._]/g, " ")) : "";
    if (rawAssignee) {
      try {
        const u = await frappeGet("User", rawAssignee);
        displayName = u.full_name || displayName;
      } catch { /* ignore */ }
    }
    full._assignee_full_name = displayName;
    applyTaskToForm(full);

    // Fetch doc meta (non-critical)
    try {
      taskMeta.value = await frappeCall("event_planner.api.get_doc_meta", {
        doctype: "Task", name: t.name,
      });
    } catch { /* ignore */ }
  } catch (e) {
    console.error("[TaskPanel] full fetch failed:", e);
  } finally {
    fetchingFull.value = false;
  }
}, { immediate: true });

// ── Auto-save (debounced 700ms) ────────────────────────────────────────────
function scheduleAutoSave() {
  if (!props.task?.name) return;
  if (saveTimer.value) clearTimeout(saveTimer.value);
  saveTimer.value = setTimeout(doSave, 700);
}

async function doSave() {
  if (!props.task?.name) return;
  saving.value = true;
  try {
    const payload: Record<string, any> = {
      subject:            subject.value,
      status:             status.value,
      ep_action_category: category.value || null,
      priority:           priority.value || null,
      exp_start_date:     startDate.value  || null,
      exp_end_date:       endDate.value    || null,
      description:        description.value,
      // Save to both the system _assign field and our custom assigned_to Link
      _assign:     assignJsonForUser(assignee.value),
      assigned_to: assignee.value || null,
    };
    const saved = await frappeSave("Task", props.task!.name, payload);
    // Merge saved doc back, preserving the display name we resolved
    emit("updated", {
      ...props.task,
      ...(saved ?? {}),
      _assignee_full_name: assigneeName.value,
    });
  } catch (e) {
    console.error("[TaskPanel] save error:", e);
  } finally {
    saving.value = false;
  }
}

function setStatus(s: string) {
  status.value = s;
  showStatusDrop.value = false;
  scheduleAutoSave();
}

function setCategory(c: string) {
  category.value = c;
  showCatDrop.value = false;
  scheduleAutoSave();
}

// ── User search ────────────────────────────────────────────────────────────
watch(userSearch, async (q) => {
  if (!q || q.length < 2) { userResults.value = []; return; }
  try {
    userResults.value = await frappeList("User", {
      filters: [["full_name", "like", `%${q}%`], ["enabled", "=", 1], ["user_type", "=", "System User"]],
      fields: ["name", "full_name"],
      limit: 10,
    });
  } catch { userResults.value = []; }
});

function pickUser(u: any) {
  assignee.value     = u.name;
  assigneeName.value = u.full_name || u.name;
  userSearch.value   = "";
  showAssignDrop.value = false;
  scheduleAutoSave();
}

function clearAssignee() {
  assignee.value     = "";
  assigneeName.value = "";
  userSearch.value   = "";
  scheduleAutoSave();
}

function hideAssignDropDelayed() {
  setTimeout(() => { showAssignDrop.value = false; }, 200);
}

// ── Computed ───────────────────────────────────────────────────────────────
const catColor = computed(() =>
  props.categories.find(c => c.name === category.value)?.color || "var(--text-3)"
);
const catLabel = computed(() =>
  props.categories.find(c => c.name === category.value)?.title || category.value || "None"
);

function shortId(name: string) {
  const m = name?.match(/(\d+)$/);
  return m ? `#${parseInt(m[1], 10)}` : (name?.slice(0, 8) ?? "");
}

function fmtDate(d?: string) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function fmtRelative(iso?: string) {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

const taskCreatedBy   = computed(() => taskMeta.value?.owner_full_name || "");
const taskCreatedAt   = computed(() => taskMeta.value?.creation || "");
const taskModifiedBy  = computed(() => taskMeta.value?.modified_by_full_name || "");
const taskModifiedAt  = computed(() => taskMeta.value?.modified || "");
</script>

<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <div class="tp-backdrop" @click="emit('close')" />

    <!-- Panel -->
    <div class="tp-panel" :class="{ 'tp-panel--open': !!task }">
      <template v-if="task">

        <!-- ── Top bar ─────────────────────────────────────────────── -->
        <div class="tp-bar">
          <div class="tp-bar__left">
            <span class="tp-id mono">{{ shortId(task.name) }}</span>
            <span class="tp-dot-sep">·</span>
            <span class="tp-typename">Task</span>
            <Transition name="fade">
              <span v-if="saving" class="tp-saving">Saving…</span>
              <span v-else-if="fetchingFull" class="tp-saving" style="color:var(--text-3)">Loading…</span>
            </Transition>
          </div>
          <div class="tp-bar__right">
            <button class="tp-icon-btn" title="Close panel" @click="emit('close')">
              <Icons name="close" :size="14" />
            </button>
          </div>
        </div>

        <!-- ── Metadata strip ────────────────────────────────────── -->
        <div v-if="taskMeta" class="tp-meta-strip">
          <span v-if="taskCreatedBy" class="tp-meta-item">
            <span class="tp-meta-lbl">Created by</span>
            <span class="tp-meta-val">{{ taskCreatedBy }}</span>
            <span v-if="taskCreatedAt" class="tp-meta-dot">·</span>
            <span v-if="taskCreatedAt" class="tp-meta-date">{{ fmtDate(taskCreatedAt) }}</span>
          </span>
          <span v-if="taskModifiedBy" class="tp-meta-item">
            <span class="tp-meta-lbl">Last edited by</span>
            <span class="tp-meta-val">{{ taskModifiedBy }}</span>
            <span v-if="taskModifiedAt" class="tp-meta-dot">·</span>
            <span v-if="taskModifiedAt" class="tp-meta-date" :title="taskModifiedAt">{{ fmtRelative(taskModifiedAt) }}</span>
          </span>
        </div>

        <!-- ── Scrollable body ────────────────────────────────────── -->
        <div class="tp-body">

          <!-- Title -->
          <div class="tp-title-section">
            <textarea
              v-model="subject"
              class="tp-title"
              rows="2"
              placeholder="Task title…"
              @input="scheduleAutoSave"
            />
          </div>

          <!-- ── Properties grid ──────────────────────────────────── -->
          <div class="tp-props">

            <!-- Status -->
            <div class="tp-prop">
              <span class="tp-prop__lbl"><Icons name="dot" :size="13" /> Status</span>
              <div class="tp-prop__val" style="position:relative;">
                <button
                  class="tp-status-pill"
                  :style="{ '--c': STATUS_COLOR[status] || '#8F8A7E' }"
                  @click="showStatusDrop = !showStatusDrop; showCatDrop = false; showAssignDrop = false"
                >
                  <span class="tp-pill__dot" />
                  {{ status }}
                  <Icons name="chevdown" :size="10" />
                </button>
                <div v-if="showStatusDrop" class="tp-drop" @mouseleave="showStatusDrop = false">
                  <button
                    v-for="s in STATUS_LIST"
                    :key="s"
                    class="tp-drop__item"
                    :class="{ 'tp-drop__item--active': s === status }"
                    @click="setStatus(s)"
                  >
                    <span class="tp-drop__dot" :style="{ background: STATUS_COLOR[s] || '#8F8A7E' }" />
                    {{ s }}
                  </button>
                </div>
              </div>
            </div>

            <!-- Priority -->
            <div class="tp-prop">
              <span class="tp-prop__lbl"><Icons name="arrow" :size="13" /> Priority</span>
              <div class="tp-prop__val">
                <select
                  v-model="priority"
                  class="tp-select"
                  :style="{ color: PRIORITY_COLOR[priority] || 'var(--text-2)' }"
                  @change="scheduleAutoSave"
                >
                  <option value="">— None —</option>
                  <option v-for="p in PRIORITY_LIST" :key="p" :value="p">{{ p }}</option>
                </select>
              </div>
            </div>

            <!-- Category -->
            <div class="tp-prop">
              <span class="tp-prop__lbl"><Icons name="kanban" :size="13" /> Category</span>
              <div class="tp-prop__val" style="position:relative;">
                <button
                  class="tp-cat-btn"
                  @click="showCatDrop = !showCatDrop; showStatusDrop = false; showAssignDrop = false"
                >
                  <span class="tp-cat-dot" :style="{ background: catColor }" />
                  {{ catLabel }}
                  <Icons name="chevdown" :size="10" />
                </button>
                <div v-if="showCatDrop" class="tp-drop" @mouseleave="showCatDrop = false">
                  <button class="tp-drop__item" @click="setCategory('')">
                    <span class="tp-drop__dot" style="background: var(--text-3)" />
                    None
                  </button>
                  <button
                    v-for="c in categories"
                    :key="c.name"
                    class="tp-drop__item"
                    :class="{ 'tp-drop__item--active': c.name === category }"
                    @click="setCategory(c.name)"
                  >
                    <span class="tp-drop__dot" :style="{ background: c.color || 'var(--text-3)' }" />
                    {{ c.title }}
                  </button>
                </div>
              </div>
            </div>

            <!-- Assignee -->
            <div class="tp-prop">
              <span class="tp-prop__lbl"><Icons name="user" :size="13" /> Assignee</span>
              <div class="tp-prop__val" style="position:relative;">
                <div v-if="assignee" class="tp-assignee-chip">
                  <Avatar :name="assignee" :size="20" />
                  <span class="tp-assignee-chip__name">{{ assigneeName || assignee.split('@')[0].replace(/[._]/g, ' ') }}</span>
                  <button class="tp-assignee-chip__rm" @click="clearAssignee">
                    <Icons name="close" :size="11" />
                  </button>
                </div>
                <div v-else>
                  <div class="tp-assign-input-wrap">
                    <Icons name="user" :size="13" class="tp-assign-icon" />
                    <input
                      v-model="userSearch"
                      class="tp-assign-input"
                      placeholder="Assign to someone…"
                      @focus="showAssignDrop = true"
                      @blur="hideAssignDropDelayed"
                    />
                  </div>
                </div>
                <div v-if="showAssignDrop" class="tp-drop tp-drop--user">
                  <div v-if="userSearch.length < 2" class="tp-drop__hint">
                    Type at least 2 characters to search
                  </div>
                  <div v-else-if="!userResults.length" class="tp-drop__hint">No users found</div>
                  <button
                    v-for="u in userResults"
                    :key="u.name"
                    class="tp-drop__item"
                    @mousedown="pickUser(u)"
                  >
                    <Avatar :name="u.name" :size="20" />
                    <div class="tp-drop__user">
                      <span class="tp-drop__user-name">{{ u.full_name || u.name }}</span>
                      <span class="tp-drop__user-email">{{ u.name }}</span>
                    </div>
                  </button>
                </div>
              </div>
            </div>

            <!-- Dates row -->
            <div class="tp-prop">
              <span class="tp-prop__lbl"><Icons name="calendar" :size="13" /> Start date</span>
              <div class="tp-prop__val">
                <input v-model="startDate" type="date" class="tp-date-input" @change="scheduleAutoSave" />
              </div>
            </div>

            <div class="tp-prop">
              <span class="tp-prop__lbl"><Icons name="clock" :size="13" /> Due date</span>
              <div class="tp-prop__val">
                <input v-model="endDate" type="date" class="tp-date-input" @change="scheduleAutoSave" />
              </div>
            </div>

          </div>

          <!-- ── Tabs: Description | Activity ─────────────────────── -->
          <div class="tp-tabs">
            <button
              class="tp-tab"
              :class="{ 'tp-tab--active': activeTab === 'description' }"
              @click="activeTab = 'description'"
            >Description</button>
            <button
              class="tp-tab"
              :class="{ 'tp-tab--active': activeTab === 'activity' }"
              @click="activeTab = 'activity'"
            >Activity</button>
          </div>

          <!-- Description tab -->
          <div v-if="activeTab === 'description'" class="tp-desc-section">
            <div class="tp-editor-wrap">
              <TiptapEditor
                v-model="description"
                placeholder="Add notes, context, or links…"
                :last-modified="taskModifiedAt"
                :last-modified-by="taskModifiedBy"
                @update:modelValue="scheduleAutoSave"
              />
            </div>
          </div>

          <!-- Activity tab -->
          <div v-else-if="activeTab === 'activity'" class="tp-activity-section">
            <ActivityFeed
              v-if="task?.name"
              doctype="Task"
              :name="task.name"
            />
          </div>

        </div><!-- /tp-body -->
      </template>
    </div>
  </Teleport>
</template>

<style scoped>
/* ── Backdrop ──────────────────────────────────────────────────────────────── */
.tp-backdrop {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0,0,0,.20);
}

/* ── Panel shell ───────────────────────────────────────────────────────────── */
.tp-panel {
  position: fixed; top: 0; right: 0; bottom: 0;
  width: 680px; z-index: 201;
  background: var(--panel);
  border-left: 1px solid var(--border-2);
  box-shadow: -12px 0 60px rgba(26,25,21,.12);
  display: flex; flex-direction: column;
  transform: translateX(100%);
  transition: transform 220ms cubic-bezier(.25,.46,.45,.94);
  overflow: hidden;
}
.tp-panel--open { transform: translateX(0); }

/* ── Top bar ───────────────────────────────────────────────────────────────── */
.tp-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 20px; border-bottom: 1px solid var(--border);
  flex-shrink: 0; background: var(--panel-2);
}
.tp-bar__left { display: flex; align-items: center; gap: 8px; }
.tp-id { font-size: 11.5px; color: var(--text-3); font-weight: 500; }
.tp-dot-sep { color: var(--border-2); }
.tp-typename { font-size: 11.5px; color: var(--text-3); }
.tp-saving { font-size: 11px; color: var(--accent); margin-left: 4px; }
.tp-bar__right { display: flex; align-items: center; gap: 6px; }

.tp-icon-btn {
  width: 28px; height: 28px; border-radius: 6px;
  background: none; border: none; cursor: pointer;
  color: var(--text-3); display: inline-flex;
  align-items: center; justify-content: center;
}
.tp-icon-btn:hover { background: var(--row-hover); color: var(--text); }

/* ── Scrollable body ───────────────────────────────────────────────────────── */
.tp-body {
  flex: 1; overflow-y: auto; padding: 0;
}

/* ── Title ─────────────────────────────────────────────────────────────────── */
.tp-title-section {
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--border);
}
.tp-title {
  width: 100%; font-size: 20px; font-weight: 700;
  color: var(--text); border: none; background: transparent;
  font-family: inherit; letter-spacing: -.02em; line-height: 1.35;
  resize: none; padding: 0;
}
.tp-title:focus { outline: none; }

/* ── Properties ────────────────────────────────────────────────────────────── */
.tp-props {
  padding: 14px 24px;
  display: flex; flex-direction: column; gap: 2px;
  border-bottom: 1px solid var(--border);
}
.tp-prop {
  display: grid;
  grid-template-columns: 148px 1fr;
  align-items: center;
  min-height: 36px;
  border-radius: 7px;
  padding: 2px 4px;
  transition: background 100ms;
}
.tp-prop:hover { background: var(--panel-2); }
.tp-prop__lbl {
  display: flex; align-items: center; gap: 7px;
  font-size: 12.5px; color: var(--text-3); font-weight: 500;
}
.tp-prop__val { position: relative; }

/* Status pill */
.tp-status-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px 4px 8px; border-radius: 999px;
  font-size: 12.5px; font-weight: 500; cursor: pointer;
  font-family: inherit; border: 1px solid color-mix(in srgb, var(--c) 28%, transparent);
  background: color-mix(in srgb, var(--c) 12%, transparent);
  color: color-mix(in srgb, var(--c) 90%, var(--text));
  transition: background 120ms;
}
.tp-status-pill:hover { background: color-mix(in srgb, var(--c) 20%, transparent); }
.tp-pill__dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--c); flex-shrink: 0;
}

/* Select (priority) */
.tp-select {
  background: transparent; border: 1px solid transparent;
  border-radius: 6px; font-size: 12.5px; font-family: inherit;
  cursor: pointer; padding: 4px 8px; font-weight: 500;
}
.tp-select:hover { border-color: var(--border-2); background: var(--panel-2); }
.tp-select:focus { outline: none; border-color: var(--accent); }

/* Category button */
.tp-cat-btn {
  display: inline-flex; align-items: center; gap: 7px;
  background: none; border: 1px solid transparent;
  border-radius: 6px; font-size: 12.5px; font-family: inherit;
  color: var(--text); cursor: pointer; padding: 4px 8px; font-weight: 500;
}
.tp-cat-btn:hover { border-color: var(--border-2); background: var(--panel-2); }
.tp-cat-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }

/* Dropdown */
.tp-drop {
  position: absolute; top: calc(100% + 5px); left: 0; min-width: 180px;
  background: var(--panel); border: 1px solid var(--border-2);
  border-radius: 9px; box-shadow: var(--shadow-lg);
  z-index: 500; overflow: hidden; padding: 5px;
}
.tp-drop--user { min-width: 240px; }
.tp-drop__item {
  display: flex; align-items: center; gap: 9px;
  padding: 8px 10px; border-radius: 6px;
  background: none; border: none; width: 100%;
  text-align: left; font-family: inherit; font-size: 12.5px;
  color: var(--text); cursor: pointer;
}
.tp-drop__item:hover { background: var(--row-hover); }
.tp-drop__item--active { background: var(--accent-soft); color: var(--accent); }
.tp-drop__dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.tp-drop__hint { padding: 10px 12px; font-size: 11.5px; color: var(--text-3); }
.tp-drop__user { display: flex; flex-direction: column; }
.tp-drop__user-name { font-size: 12.5px; font-weight: 500; }
.tp-drop__user-email { font-size: 11px; color: var(--text-3); margin-top: 1px; }

/* Assignee chip */
.tp-assignee-chip {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 3px 8px 3px 4px; border-radius: 999px;
  background: var(--panel-2); border: 1px solid var(--border);
}
.tp-assignee-chip__name { font-size: 12.5px; font-weight: 500; }
.tp-assignee-chip__rm {
  background: none; border: none; cursor: pointer;
  color: var(--text-3); padding: 1px; border-radius: 3px;
  display: inline-flex;
}
.tp-assignee-chip__rm:hover { color: var(--text); }

/* Assign input */
.tp-assign-input-wrap {
  display: flex; align-items: center; gap: 6px;
  border: 1px solid transparent; border-radius: 6px; padding: 3px 8px;
  transition: border-color 120ms;
}
.tp-assign-input-wrap:focus-within { border-color: var(--accent); background: var(--panel-2); }
.tp-assign-icon { color: var(--text-3); flex-shrink: 0; }
.tp-assign-input {
  background: none; border: none; font-size: 12.5px;
  font-family: inherit; color: var(--text); width: 100%;
}
.tp-assign-input:focus { outline: none; }
.tp-assign-input::placeholder { color: var(--text-3); }

/* Date input */
.tp-date-input {
  background: transparent; border: 1px solid transparent;
  border-radius: 6px; font-size: 12.5px; font-family: inherit;
  color: var(--text); padding: 4px 8px; cursor: pointer;
}
.tp-date-input:hover { border-color: var(--border-2); background: var(--panel-2); }
.tp-date-input:focus { outline: none; border-color: var(--accent); background: var(--panel-2); }

/* ── Metadata strip ────────────────────────────────────────────────────────── */
.tp-meta-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 24px;
  background: var(--panel-2);
  border-bottom: 1px solid var(--border);
  font-size: 11px;
}
.tp-meta-item  { display: flex; align-items: center; gap: 4px; }
.tp-meta-lbl   { color: var(--text-3); font-weight: 500; }
.tp-meta-val   { color: var(--text); font-weight: 600; }
.tp-meta-dot   { color: var(--border-2); }
.tp-meta-date  { color: var(--text-3); cursor: default; }

/* ── Tabs ──────────────────────────────────────────────────────────────────── */
.tp-tabs {
  display: flex;
  gap: 0;
  padding: 0 24px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.tp-tab {
  padding: 11px 16px 9px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-3);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-family: inherit;
  transition: color 120ms, border-color 120ms;
}
.tp-tab:hover { color: var(--text); }
.tp-tab--active { color: var(--accent-2); border-bottom-color: var(--accent); }

/* ── Description ───────────────────────────────────────────────────────────── */
.tp-desc-section {
  padding: 20px 24px 32px;
}
.tp-section-lbl {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .1em; color: var(--text-3); margin-bottom: 12px;
}
.tp-editor-wrap {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  min-height: 240px;
}

/* ── Activity tab ──────────────────────────────────────────────────────────── */
.tp-activity-section {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

/* ── Transition ────────────────────────────────────────────────────────────── */
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── Mobile: full-screen panel ─────────────────────────────────────────────── */
@media (max-width: 767px) {
  .tp-panel {
    width: 100vw; left: 0;
    transform: translateY(100%);
    border-left: none;
    border-top: 1px solid var(--border-2);
    border-radius: 16px 16px 0 0;
    box-shadow: 0 -8px 40px rgba(26,25,21,.18);
  }
  .tp-panel--open { transform: translateY(0); }

  /* Drag handle indicator */
  .tp-bar::before {
    content: '';
    position: absolute; top: 8px; left: 50%; transform: translateX(-50%);
    width: 36px; height: 4px; border-radius: 2px;
    background: var(--border-2);
  }
  .tp-bar { position: relative; padding-top: 20px; }
}
</style>
