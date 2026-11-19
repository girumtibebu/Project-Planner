<script setup lang="ts">
import { ref, watch, onMounted, computed } from "vue";
import { frappeCall } from "../composables/useFrappe";

// ── Props / emits ─────────────────────────────────────────────────────────────

const props = defineProps<{
  projectName: string;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "updated"): void;
}>();

// ── State ─────────────────────────────────────────────────────────────────────

const categories   = ref<any[]>([]);
const loading      = ref(false);
const saving       = ref(false);
const error        = ref("");
const dragFrom     = ref<number | null>(null);
const dragOver     = ref<number | null>(null);

// New category form
const newTitle     = ref("");
const newColor     = ref("#CC785C");
const showAddRow   = ref(false);

// Rename edit state: { [index]: string }
const editTitles   = ref<Record<number, string>>({});
const editColors   = ref<Record<number, string>>({});
const editingIdx   = ref<number | null>(null);
const confirmDelete = ref<number | null>(null);

// Global presets (for import picker)
const showPresets   = ref(false);
const importBusy    = ref(false);

const projectCats  = computed(() => categories.value.filter(c => !c.is_global));
const globalCats   = computed(() => categories.value.filter(c => c.is_global));

// ── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  loading.value = true;
  error.value = "";
  try {
    categories.value = await frappeCall("event_planner.api.list_categories", {
      project: props.projectName,
    });
  } catch (e: any) {
    error.value = e?.message || "Failed to load categories";
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(() => props.projectName, load);

// ── Add ───────────────────────────────────────────────────────────────────────

async function addCategory() {
  const title = newTitle.value.trim();
  if (!title) return;
  saving.value = true;
  try {
    await frappeCall("event_planner.api.create_category", {
      project:    props.projectName,
      title,
      color:      newColor.value || null,
      sort_order: projectCats.value.length,
    });
    newTitle.value = "";
    newColor.value = "#CC785C";
    showAddRow.value = false;
    await load();
    emit("updated");
  } catch (e: any) {
    error.value = e?.message || "Failed to create category";
  } finally {
    saving.value = false;
  }
}

// ── Save edit ─────────────────────────────────────────────────────────────────

async function saveEdit(cat: any, idx: number) {
  const title = (editTitles.value[idx] ?? cat.title).trim();
  const color  = editColors.value[idx] ?? cat.color;
  if (!title) return;
  saving.value = true;
  try {
    await frappeCall("event_planner.api.update_category", {
      name:  cat.name,
      title,
      color: color || null,
    });
    editingIdx.value = null;
    await load();
    emit("updated");
  } catch (e: any) {
    error.value = e?.message || "Failed to update category";
  } finally {
    saving.value = false;
  }
}

function startEdit(cat: any, idx: number) {
  editingIdx.value  = idx;
  editTitles.value[idx] = cat.title;
  editColors.value[idx] = cat.color || "#CC785C";
}

function cancelEdit() { editingIdx.value = null; }

// ── Delete ────────────────────────────────────────────────────────────────────

async function deleteCategory(cat: any, idx: number) {
  saving.value = true;
  try {
    await frappeCall("event_planner.api.delete_category", { name: cat.name });
    confirmDelete.value = null;
    await load();
    emit("updated");
  } catch (e: any) {
    error.value = e?.message || "Failed to delete category";
  } finally {
    saving.value = false;
  }
}

// ── Drag-to-reorder ───────────────────────────────────────────────────────────

function onDragStart(idx: number) { dragFrom.value = idx; }
function onDragEnter(idx: number) { dragOver.value = idx; }
function onDragEnd() {
  if (dragFrom.value !== null && dragOver.value !== null && dragFrom.value !== dragOver.value) {
    const arr = [...projectCats.value];
    const [moved] = arr.splice(dragFrom.value, 1);
    arr.splice(dragOver.value, 0, moved);
    // Persist reorder
    const ordered = arr.map(c => c.name);
    frappeCall("event_planner.api.reorder_categories", {
      project: props.projectName,
      ordered_names: ordered,
    }).then(() => { load(); emit("updated"); }).catch(() => {});
  }
  dragFrom.value = null;
  dragOver.value = null;
}

// ── Import global preset ──────────────────────────────────────────────────────

async function importPreset(cat: any) {
  importBusy.value = true;
  try {
    await frappeCall("event_planner.api.create_category", {
      project:    props.projectName,
      title:      cat.title,
      color:      cat.color || null,
      sort_order: projectCats.value.length,
    });
    await load();
    emit("updated");
  } catch { /* already exists or other error – ignore */ } finally {
    importBusy.value = false;
  }
}

function closeModal() { emit("close"); }

// ── Color presets ─────────────────────────────────────────────────────────────
const COLOR_SWATCHES = [
  "#CC785C", "#E05252", "#F59E0B", "#22C55E", "#3B82F6",
  "#8B5CF6", "#EC4899", "#14B8A6", "#6C7280", "#1A1915",
];
</script>

<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <div class="cm-backdrop" @click="closeModal" />

    <!-- Modal -->
    <div class="cm-modal" role="dialog" aria-modal="true" aria-label="Manage Categories">

      <!-- Header -->
      <div class="cm-header">
        <div class="cm-header-left">
          <div class="cm-title">Manage Categories</div>
          <div class="cm-subtitle">Add, edit, reorder or delete categories for this event</div>
        </div>
        <button class="cm-close" @click="closeModal" title="Close">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 3l10 10M13 3 3 13"/></svg>
        </button>
      </div>

      <!-- Error -->
      <div v-if="error" class="cm-error">{{ error }}</div>

      <!-- Content -->
      <div class="cm-body">

        <!-- ── Project-scoped categories ── -->
        <div class="cm-section-lbl">Event categories</div>

        <div v-if="loading" class="cm-loading">
          <span class="cm-spinner" /> Loading…
        </div>

        <div v-else class="cm-list">
          <div
            v-for="(cat, idx) in projectCats"
            :key="cat.name"
            class="cm-row"
            :class="{
              'cm-row--drag-over': dragOver === idx && dragFrom !== idx,
              'cm-row--editing': editingIdx === idx,
            }"
            draggable="true"
            @dragstart="onDragStart(idx)"
            @dragenter.prevent="onDragEnter(idx)"
            @dragover.prevent
            @dragend="onDragEnd"
          >
            <!-- Drag handle -->
            <span class="cm-drag" title="Drag to reorder">
              <svg width="10" height="12" viewBox="0 0 8 12" fill="none"><circle cx="2" cy="2" r="1.2" fill="currentColor"/><circle cx="6" cy="2" r="1.2" fill="currentColor"/><circle cx="2" cy="6" r="1.2" fill="currentColor"/><circle cx="6" cy="6" r="1.2" fill="currentColor"/><circle cx="2" cy="10" r="1.2" fill="currentColor"/><circle cx="6" cy="10" r="1.2" fill="currentColor"/></svg>
            </span>

            <!-- Color dot / color picker (edit mode) -->
            <template v-if="editingIdx === idx">
              <input
                type="color"
                class="cm-color-picker"
                :value="editColors[idx] || '#CC785C'"
                @input="editColors[idx] = ($event.target as HTMLInputElement).value"
              />
            </template>
            <template v-else>
              <span class="cm-cat-dot" :style="{ background: cat.color || '#8F8A7E' }" />
            </template>

            <!-- Title (view/edit) -->
            <template v-if="editingIdx === idx">
              <input
                v-model="editTitles[idx]"
                class="cm-title-input"
                placeholder="Category name…"
                @keydown.enter="saveEdit(cat, idx)"
                @keydown.escape="cancelEdit"
              />
            </template>
            <template v-else>
              <span class="cm-cat-title">{{ cat.title }}</span>
            </template>

            <!-- Task count badge -->
            <span v-if="cat.task_count > 0" class="cm-count">{{ cat.task_count }}</span>

            <!-- Actions -->
            <div class="cm-row-actions">
              <template v-if="editingIdx === idx">
                <button class="cm-btn cm-btn--primary" :disabled="saving" @click="saveEdit(cat, idx)">Save</button>
                <button class="cm-btn" @click="cancelEdit">Cancel</button>
              </template>
              <template v-else-if="confirmDelete === idx">
                <span class="cm-confirm-text">Delete? ({{ cat.task_count }} tasks reassigned)</span>
                <button class="cm-btn cm-btn--danger" :disabled="saving" @click="deleteCategory(cat, idx)">Confirm</button>
                <button class="cm-btn" @click="confirmDelete = null">Cancel</button>
              </template>
              <template v-else>
                <button class="cm-icon-btn" title="Rename" @click="startEdit(cat, idx)">
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M11 2.5l2.5 2.5L4 14.5H1.5V12L11 2.5z"/></svg>
                </button>
                <button class="cm-icon-btn cm-icon-btn--danger" title="Delete" @click="confirmDelete = idx">
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5h10M6 5V3h4v2M6 7.5v5M10 7.5v5"/><rect x="3" y="5" width="10" height="9" rx="1.5"/></svg>
                </button>
              </template>
            </div>
          </div>

          <div v-if="projectCats.length === 0 && !loading" class="cm-empty">
            No custom categories yet. Add one below or import from global presets.
          </div>
        </div>

        <!-- Add new row -->
        <div v-if="showAddRow" class="cm-add-row">
          <input
            type="color"
            class="cm-color-picker"
            v-model="newColor"
          />
          <!-- Color swatches -->
          <div class="cm-swatches">
            <button
              v-for="c in COLOR_SWATCHES"
              :key="c"
              class="cm-swatch"
              :class="{ active: newColor === c }"
              :style="{ background: c }"
              @click="newColor = c"
            />
          </div>
          <input
            v-model="newTitle"
            class="cm-title-input"
            placeholder="Category name…"
            autofocus
            @keydown.enter="addCategory"
            @keydown.escape="showAddRow = false; newTitle = ''"
          />
          <button class="cm-btn cm-btn--primary" :disabled="saving || !newTitle.trim()" @click="addCategory">Add</button>
          <button class="cm-btn" @click="showAddRow = false; newTitle = ''">Cancel</button>
        </div>

        <button v-else class="cm-add-btn" @click="showAddRow = true">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M8 3v10M3 8h10"/></svg>
          Add category
        </button>

        <!-- ── Global presets ── -->
        <div class="cm-sep" />

        <button
          class="cm-presets-toggle"
          @click="showPresets = !showPresets"
        >
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2a6 6 0 1 1 0 12A6 6 0 0 1 8 2z"/><path d="M8 6v4M6 8h4"/></svg>
          Import from global presets
          <span class="cm-chevron" :class="{ open: showPresets }">▾</span>
        </button>

        <div v-if="showPresets && globalCats.length" class="cm-globals">
          <div
            v-for="g in globalCats"
            :key="g.name"
            class="cm-global-row"
          >
            <span class="cm-cat-dot" :style="{ background: g.color || '#8F8A7E' }" />
            <span class="cm-cat-title">{{ g.title }}</span>
            <span v-if="g.task_count > 0" class="cm-count">{{ g.task_count }}</span>
            <button
              class="cm-btn cm-btn--sm"
              :disabled="importBusy"
              @click="importPreset(g)"
            >Import</button>
          </div>
        </div>
        <div v-else-if="showPresets" class="cm-empty">No global presets.</div>

      </div><!-- /cm-body -->
    </div>
  </Teleport>
</template>

<style scoped>
/* ── Backdrop ──────────────────────────────────────────────────────────────── */
.cm-backdrop {
  position: fixed; inset: 0; z-index: 400;
  background: rgba(0,0,0,.25);
  animation: cmFadeIn 120ms ease-out;
}

/* ── Modal ─────────────────────────────────────────────────────────────────── */
.cm-modal {
  position: fixed; z-index: 401;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: min(600px, 96vw);
  max-height: 80vh;
  background: var(--panel);
  border: 1px solid var(--border-2);
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(26,25,21,.18), 0 4px 12px rgba(26,25,21,.08);
  display: flex; flex-direction: column;
  animation: cmSlideIn 150ms cubic-bezier(.25,.46,.45,.94);
  overflow: hidden;
}

@keyframes cmFadeIn  { from { opacity:0; } to { opacity:1; } }
@keyframes cmSlideIn { from { opacity:0; transform:translate(-50%,-48%); } to { opacity:1; transform:translate(-50%,-50%); } }

/* ── Header ────────────────────────────────────────────────────────────────── */
.cm-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  padding: 20px 24px 16px; border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.cm-title    { font-size: 16px; font-weight: 700; color: var(--text); letter-spacing: -.015em; }
.cm-subtitle { font-size: 12px; color: var(--text-3); margin-top: 2px; }
.cm-close {
  width: 28px; height: 28px; border: none; background: none; cursor: pointer;
  color: var(--text-3); border-radius: 5px; display: flex; align-items: center; justify-content: center;
}
.cm-close:hover { background: var(--row-hover); color: var(--text); }

/* ── Body ──────────────────────────────────────────────────────────────────── */
.cm-body {
  flex: 1; overflow-y: auto; padding: 16px 24px 20px;
  display: flex; flex-direction: column; gap: 6px;
}

.cm-error {
  margin: 0 24px; padding: 8px 12px; font-size: 12.5px; color: var(--danger);
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--danger) 25%, transparent);
  border-radius: 6px; flex-shrink: 0;
}

.cm-section-lbl {
  font-size: 10.5px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .1em; color: var(--text-3); margin-bottom: 4px;
}

.cm-loading {
  display: flex; align-items: center; gap: 8px;
  font-size: 12.5px; color: var(--text-3); padding: 12px 0;
}
.cm-spinner {
  width: 14px; height: 14px; border: 2px solid var(--border);
  border-top-color: var(--accent); border-radius: 50%;
  animation: cmSpin .7s linear infinite; flex-shrink: 0;
}
@keyframes cmSpin { to { transform: rotate(360deg); } }

/* ── Category list ─────────────────────────────────────────────────────────── */
.cm-list { display: flex; flex-direction: column; gap: 2px; }

.cm-row {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 8px; border-radius: 7px; border: 1px solid transparent;
  transition: background 100ms, border-color 100ms;
  cursor: grab;
}
.cm-row:hover { background: var(--row-hover); }
.cm-row--drag-over { border-color: var(--accent); background: var(--accent-soft); }
.cm-row--editing   { background: var(--panel-2); border-color: var(--border-2); }

.cm-drag { color: var(--text-3); cursor: grab; flex-shrink: 0; }
.cm-drag:active { cursor: grabbing; }

.cm-cat-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.cm-cat-title { flex: 1; font-size: 13px; color: var(--text); font-weight: 500; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cm-count { font-size: 10.5px; background: var(--bg-2); border: 1px solid var(--border); border-radius: 10px; padding: 1px 6px; color: var(--text-3); font-variant-numeric: tabular-nums; flex-shrink: 0; }

.cm-row-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }

.cm-icon-btn {
  width: 26px; height: 26px; display: flex; align-items: center; justify-content: center;
  border: none; background: none; cursor: pointer; color: var(--text-3); border-radius: 4px;
}
.cm-icon-btn:hover { background: var(--panel-2); color: var(--text); }
.cm-icon-btn--danger:hover { color: var(--danger); }

.cm-confirm-text { font-size: 11px; color: var(--text-3); white-space: nowrap; }

.cm-btn {
  font-size: 12px; font-weight: 500; padding: 4px 10px; border: 1px solid var(--border-2);
  border-radius: 5px; background: var(--panel); color: var(--text-2);
  cursor: pointer; font-family: inherit; white-space: nowrap;
}
.cm-btn:hover:not(:disabled) { background: var(--bg-2); color: var(--text); }
.cm-btn:disabled { opacity: .5; cursor: not-allowed; }
.cm-btn--primary { background: var(--accent); border-color: var(--accent); color: white; }
.cm-btn--primary:hover:not(:disabled) { background: var(--accent-2); border-color: var(--accent-2); }
.cm-btn--danger { background: var(--danger); border-color: var(--danger); color: white; }
.cm-btn--sm { font-size: 11px; padding: 3px 8px; }

.cm-empty { font-size: 12.5px; color: var(--text-3); padding: 8px 4px; }

/* ── Color picker ──────────────────────────────────────────────────────────── */
.cm-color-picker {
  width: 28px; height: 28px; border: 1px solid var(--border); border-radius: 5px;
  padding: 2px; cursor: pointer; flex-shrink: 0; background: none;
}

.cm-swatches {
  display: flex; gap: 4px; flex-wrap: wrap; max-width: 140px; flex-shrink: 0;
}
.cm-swatch {
  width: 18px; height: 18px; border-radius: 50%; border: 2px solid transparent;
  cursor: pointer; padding: 0;
}
.cm-swatch.active, .cm-swatch:hover { border-color: var(--text); }

/* ── Add row ───────────────────────────────────────────────────────────────── */
.cm-add-row {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  padding: 8px 8px; border: 1px dashed var(--border-2); border-radius: 7px;
  margin-top: 4px;
}

.cm-title-input {
  flex: 1; min-width: 120px; background: var(--bg-2); border: 1px solid var(--border);
  border-radius: 5px; font-size: 13px; font-family: inherit; padding: 5px 8px;
  color: var(--text);
}
.cm-title-input:focus { outline: none; border-color: var(--accent); background: var(--panel-2); }

.cm-add-btn {
  display: flex; align-items: center; gap: 6px; padding: 7px 10px;
  background: none; border: 1px dashed var(--border-2); border-radius: 7px;
  color: var(--text-3); font-size: 12.5px; font-weight: 500; cursor: pointer;
  font-family: inherit; width: 100%; justify-content: center;
  transition: background 100ms, color 100ms;
}
.cm-add-btn:hover { background: var(--row-hover); color: var(--text); border-color: var(--border); }

/* ── Separator ─────────────────────────────────────────────────────────────── */
.cm-sep { height: 1px; background: var(--border); margin: 8px 0; }

/* ── Presets toggle ────────────────────────────────────────────────────────── */
.cm-presets-toggle {
  display: flex; align-items: center; gap: 6px; padding: 7px 0;
  background: none; border: none; cursor: pointer; font-size: 12.5px;
  font-weight: 500; color: var(--text-2); font-family: inherit;
}
.cm-presets-toggle:hover { color: var(--text); }
.cm-chevron { font-size: 11px; transition: transform 150ms; }
.cm-chevron.open { transform: rotate(180deg); }

/* ── Global list ───────────────────────────────────────────────────────────── */
.cm-globals { display: flex; flex-direction: column; gap: 2px; margin-top: 4px; }
.cm-global-row {
  display: flex; align-items: center; gap: 8px; padding: 6px 8px;
  border-radius: 6px; background: var(--panel-2);
}
</style>
