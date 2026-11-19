<script lang="ts">
/**
 * Module-level label cache — shared across ALL InlineCell instances so the
 * same User / Vehicle / Activity is only fetched once per page load.
 */
const _cache = new Map<string, string>();
</script>

<script setup lang="ts">
/**
 * InlineCell — a single table cell that can be viewed or edited in-place.
 *
 * Supported types:
 *   text      – plain text <input>
 *   number    – numeric <input>
 *   currency  – numeric, right-aligned, formatted with commas
 *   select    – static <select> dropdown; pass colorMap for pill display
 *   link      – Frappe link field: searchable typeahead against any doctype
 *
 * For link fields the component resolves the display label (e.g. full_name for
 * User) via a debounced Frappe list call and caches the result module-wide.
 *
 * Usage in a <td>:
 *   <td class="ic-td">
 *     <InlineCell
 *       :value="row.person" type="link"
 *       :link-conf="{ doctype:'User', labelField:'full_name', showAvatar:true }"
 *       @update="updateRow('ep_time_schedule', i, 'person', $event)"
 *     />
 *   </td>
 */
import { ref, watch, nextTick } from "vue";
import Avatar from "./Avatar.vue";
import { frappeList } from "../composables/useFrappe";

// ── Prop types ────────────────────────────────────────────────────────────────

export interface LinkConf {
  doctype:     string;
  labelField:  string;          // field to display
  searchField?: string;         // field to filter on (defaults to labelField)
  filters?:    any[];           // static extra filters [[field, op, val], ...]
  showAvatar?: boolean;         // show Frappe-style avatar (for User)
}

const props = defineProps<{
  value:        any;
  type:         "text" | "number" | "currency" | "select" | "link";
  linkConf?:    LinkConf;
  options?:     string[];       // for 'select'
  colorMap?:    Record<string, string>; // for 'select' pill colouring
  placeholder?: string;
  align?:       "left" | "right";
}>();

const emit = defineEmits<{ update: [v: any] }>();

// ── Label resolution (link fields only) ───────────────────────────────────────

async function resolveLabel(conf: LinkConf, name: string): Promise<string> {
  if (!name) return "";
  const cacheKey = `${conf.doctype}::${name}::${conf.labelField}`;
  if (_cache.has(cacheKey)) return _cache.get(cacheKey)!;
  try {
    const rows = await frappeList(conf.doctype, {
      filters: [["name", "=", name]],
      fields:  ["name", conf.labelField],
      limit:   1,
    });
    const label = rows[0]?.[conf.labelField] || name;
    _cache.set(cacheKey, label);
    return label;
  } catch { return name; }
}

// ── Local state ───────────────────────────────────────────────────────────────

const editing  = ref(false);
const inputEl  = ref<HTMLInputElement | HTMLSelectElement | null>(null);
const label    = ref("");     // resolved display label
const editVal  = ref<any>(""); // text/number edit buffer
const query    = ref("");     // link search query
const results  = ref<any[]>([]);
const showDrop = ref(false);
let   dropTimer: ReturnType<typeof setTimeout>   | null = null;
let   searchTimer: ReturnType<typeof setTimeout> | null = null;

// Resolve label when value changes
watch(() => props.value, async (v) => {
  editVal.value = v ?? "";
  if (props.type === "link" && props.linkConf && v) {
    label.value = await resolveLabel(props.linkConf, v);
  } else {
    label.value = v != null ? String(v) : "";
  }
}, { immediate: true });

// ── Activate / deactivate ─────────────────────────────────────────────────────

async function activate() {
  editing.value  = true;
  editVal.value  = props.value ?? "";
  query.value    = label.value || String(props.value || "");
  await nextTick();
  if (inputEl.value) {
    inputEl.value.focus();
    if (typeof (inputEl.value as HTMLInputElement).select === "function")
      (inputEl.value as HTMLInputElement).select();
  }
  if (props.type === "link") doSearch(query.value);
}

function deactivate() {
  editing.value = false;
  showDrop.value = false;
  if (dropTimer)   clearTimeout(dropTimer);
  if (searchTimer) clearTimeout(searchTimer);
  results.value = [];
}

// ── Commit helpers ────────────────────────────────────────────────────────────

function commitText() {
  emit("update", editVal.value.trim() || null);
  deactivate();
}

function commitNumber() {
  const n = parseFloat(String(editVal.value));
  emit("update", isNaN(n) ? null : n);
  deactivate();
}

function commitSelect(v: string) {
  emit("update", v || null);
  deactivate();
}

function pickLinkRow(row: any) {
  const lbl = row[props.linkConf!.labelField] || row.name;
  // Warm cache for next render
  _cache.set(`${props.linkConf!.doctype}::${row.name}::${props.linkConf!.labelField}`, lbl);
  label.value = lbl;
  emit("update", row.name);
  deactivate();
}

function clearLink(e: Event) {
  e.stopPropagation();
  label.value = "";
  emit("update", null);
  deactivate();
}

// ── Link search ───────────────────────────────────────────────────────────────

function doSearch(q: string) {
  if (!props.linkConf) return;
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    const sf      = props.linkConf!.searchField || props.linkConf!.labelField;
    const filters = props.linkConf!.filters ? [...props.linkConf!.filters] : [] as any[];
    if (q) filters.push([sf, "like", `%${q}%`]);

    const fields = new Set<string>(["name", props.linkConf!.labelField]);
    if (props.linkConf!.searchField) fields.add(props.linkConf!.searchField);

    results.value = await frappeList(props.linkConf!.doctype, {
      filters: filters.length ? filters : undefined,
      fields:  [...fields],
      limit:   15,
    }).catch(() => []);
    showDrop.value = true;
  }, 180);
}

function onQueryInput() { doSearch(query.value); }

function cancelHideDrop() { if (dropTimer) clearTimeout(dropTimer); }
function hideDrop()       { dropTimer = setTimeout(() => { showDrop.value = false; }, 200); }

// ── Keyboard ──────────────────────────────────────────────────────────────────

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") { deactivate(); e.preventDefault(); }
  if (e.key === "Enter") {
    if      (props.type === "text")                          { commitText();   e.preventDefault(); }
    else if (props.type === "number" || props.type === "currency") { commitNumber(); e.preventDefault(); }
  }
  if (e.key === "Tab") {
    if      (props.type === "text")                          commitText();
    else if (props.type === "number" || props.type === "currency") commitNumber();
  }
}

// ── Display helpers ───────────────────────────────────────────────────────────

function fmtCurrency(v: any) {
  if (v == null || v === "") return "";
  return Number(v).toLocaleString("en-US");
}
</script>

<template>
  <span
    class="ic"
    :class="[
      editing        && 'ic--editing',
      align === 'right' && 'ic--right',
      type           && `ic--${type}`,
    ]"
    @click.stop="!editing && activate()"
  >
    <!-- ╔══════════════════════════════════════════════════════╗ -->
    <!-- ║  VIEW MODE                                           ║ -->
    <!-- ╚══════════════════════════════════════════════════════╝ -->
    <template v-if="!editing">

      <!-- Link with avatar (User type) -->
      <template v-if="type === 'link' && linkConf?.showAvatar && value">
        <span class="ic-avatar-row">
          <Avatar :name="value" :size="18" />
          <span class="ic-lbl">{{ label || value }}</span>
        </span>
      </template>

      <!-- Select with pill colour -->
      <template v-else-if="type === 'select' && colorMap && value">
        <span
          class="ic-pill"
          :style="{ '--pill-c': colorMap[value] || '#8F8A7E' }"
        >{{ value }}</span>
      </template>

      <!-- Currency -->
      <template v-else-if="type === 'currency'">
        <span v-if="value != null && value !== ''" class="ic-lbl ic-mono">
          {{ fmtCurrency(value) }}
        </span>
        <span v-else class="ic-empty">—</span>
      </template>

      <!-- Generic -->
      <template v-else>
        <span v-if="label || (value != null && value !== '')" class="ic-lbl">
          {{ label || value }}
        </span>
        <span v-else class="ic-empty">—</span>
      </template>

      <!-- Hover edit hint -->
      <span class="ic-hint" aria-hidden="true">✎</span>
    </template>

    <!-- ╔══════════════════════════════════════════════════════╗ -->
    <!-- ║  EDIT MODE                                           ║ -->
    <!-- ╚══════════════════════════════════════════════════════╝ -->
    <template v-else>

      <!-- SELECT ─────────────────────────────────────────────── -->
      <template v-if="type === 'select'">
        <select
          ref="inputEl"
          v-model="editVal"
          class="ic-input ic-input--select"
          @change="commitSelect(editVal)"
          @keydown="onKeydown"
          @blur="deactivate"
        >
          <option value="">— None —</option>
          <option v-for="o in options" :key="o" :value="o">{{ o }}</option>
        </select>
      </template>

      <!-- LINK ───────────────────────────────────────────────── -->
      <template v-else-if="type === 'link'">
        <div class="ic-link-wrap" @mouseenter="cancelHideDrop">
          <input
            ref="inputEl"
            v-model="query"
            class="ic-input ic-input--link"
            :placeholder="placeholder || 'Search…'"
            autocomplete="off"
            @input="onQueryInput"
            @focus="doSearch(query)"
            @blur="hideDrop"
            @keydown="onKeydown"
          />
          <!-- Clear button -->
          <button
            v-if="value"
            class="ic-clear"
            title="Clear"
            @mousedown.prevent="clearLink"
          >×</button>

          <!-- Dropdown -->
          <div
            v-if="showDrop"
            class="ic-drop"
            @mouseenter="cancelHideDrop"
            @mouseleave="hideDrop"
          >
            <template v-if="results.length">
              <button
                v-for="row in results"
                :key="row.name"
                class="ic-drop-item"
                @mousedown.prevent="pickLinkRow(row)"
              >
                <template v-if="linkConf?.showAvatar">
                  <Avatar :name="row.name" :size="16" />
                  <span class="ic-drop-info">
                    <span class="ic-drop-main">{{ row[linkConf.labelField] || row.name }}</span>
                    <span class="ic-drop-sub">{{ row.name }}</span>
                  </span>
                </template>
                <template v-else>
                  <span class="ic-drop-main">{{ row[linkConf!.labelField] || row.name }}</span>
                </template>
              </button>
            </template>
            <div v-else class="ic-drop-empty">No results</div>
          </div>
        </div>
      </template>

      <!-- NUMBER / CURRENCY ──────────────────────────────────── -->
      <template v-else-if="type === 'number' || type === 'currency'">
        <input
          ref="inputEl"
          v-model="editVal"
          type="number"
          class="ic-input ic-input--num"
          :class="align === 'right' && 'ic-input--right'"
          @keydown="onKeydown"
          @blur="commitNumber"
        />
      </template>

      <!-- TEXT (default) ─────────────────────────────────────── -->
      <template v-else>
        <input
          ref="inputEl"
          v-model="editVal"
          type="text"
          class="ic-input"
          :placeholder="placeholder || ''"
          @keydown="onKeydown"
          @blur="commitText"
        />
      </template>

    </template>
  </span>
</template>

<style scoped>
/* ── Cell shell ─────────────────────────────────────────────────────────────── */
.ic {
  display: inline-flex;
  align-items: center;
  width: 100%;
  min-height: 28px;
  cursor: pointer;
  border-radius: 5px;
  padding: 4px 6px;
  position: relative;
  gap: 5px;
  transition: background 100ms;
  box-sizing: border-box;
}
.ic:not(.ic--editing):hover { background: rgba(0,0,0,.045); }
.ic--editing { padding: 2px 0; cursor: default; background: transparent !important; }
.ic--right   { justify-content: flex-end; }

/* ── View mode ──────────────────────────────────────────────────────────────── */
.ic-lbl   { font-size: 12.5px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ic-empty { font-size: 12.5px; color: var(--text-3); }
.ic-mono  { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }

.ic-avatar-row {
  display: inline-flex; align-items: center; gap: 6px;
  white-space: nowrap; overflow: hidden;
}

/* Pill for select+colorMap */
.ic-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 500;
  background: color-mix(in srgb, var(--pill-c) 14%, transparent);
  color: color-mix(in srgb, var(--pill-c) 90%, var(--text));
  border: 1px solid color-mix(in srgb, var(--pill-c) 25%, transparent);
  white-space: nowrap;
}

/* Hover edit hint */
.ic-hint {
  position: absolute;
  right: 5px;
  opacity: 0;
  font-size: 9px;
  color: var(--text-3);
  transition: opacity 100ms;
  pointer-events: none;
  flex-shrink: 0;
}
.ic:not(.ic--editing):hover .ic-hint { opacity: 1; }

/* ── Edit inputs ────────────────────────────────────────────────────────────── */
.ic-input {
  width: 100%;
  padding: 5px 8px;
  border: 1.5px solid var(--accent);
  border-radius: 5px;
  font-size: 12.5px;
  font-family: inherit;
  background: var(--panel);
  color: var(--text);
  outline: none;
  box-shadow: 0 0 0 3px rgba(204,120,92,.12);
  box-sizing: border-box;
}
.ic-input--select { cursor: pointer; }
.ic-input--num    { text-align: right; }
.ic-input--right  { text-align: right; }

/* ── Link field wrapper ─────────────────────────────────────────────────────── */
.ic-link-wrap {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
}

.ic-input--link { padding-right: 26px; }

.ic-clear {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-3);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 2px;
  border-radius: 3px;
}
.ic-clear:hover { color: var(--danger); }

/* ── Dropdown ────────────────────────────────────────────────────────────────── */
.ic-drop {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 200px;
  max-width: 340px;
  background: var(--panel);
  border: 1px solid var(--border-2);
  border-radius: 8px;
  box-shadow: var(--shadow-lg);
  z-index: 700;
  overflow: hidden;
  max-height: 220px;
  overflow-y: auto;
  padding: 4px;
}

.ic-drop-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
  font-size: 12.5px;
  text-align: left;
  border-radius: 5px;
  color: var(--text);
}
.ic-drop-item:hover { background: var(--row-hover); }

.ic-drop-info { display: flex; flex-direction: column; min-width: 0; }
.ic-drop-main { font-size: 12.5px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ic-drop-sub  { font-size: 11px; color: var(--text-3); margin-top: 1px; }

.ic-drop-empty { padding: 10px 12px; font-size: 12px; color: var(--text-3); text-align: center; }
</style>
