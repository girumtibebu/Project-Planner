<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from "vue";
import { frappeCall } from "../composables/useFrappe";
import Avatar from "./Avatar.vue";

// ── Props ─────────────────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    doctype: string;
    name: string;
    /** Show compact mode: smaller font, no diff expansion */
    compact?: boolean;
  }>(),
  { compact: false }
);

// ── State ─────────────────────────────────────────────────────────────────────

const rows      = ref<any[]>([]);
const loading   = ref(false);
const error     = ref("");
const expanded  = ref<Set<string>>(new Set());
let   pollTimer: ReturnType<typeof setInterval> | null = null;

// ── Load ──────────────────────────────────────────────────────────────────────

async function load() {
  if (!props.name) return;
  loading.value = true;
  error.value   = "";
  try {
    rows.value = await frappeCall("event_planner.api.get_activity_log", {
      doctype: props.doctype,
      name:    props.name,
      limit:   50,
    });
  } catch (e: any) {
    error.value = e?.message || "Failed to load activity";
  } finally {
    loading.value = false;
  }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(load, 30_000);
}

onMounted(() => { load(); startPolling(); });
onBeforeUnmount(() => { if (pollTimer) clearInterval(pollTimer); });

watch(() => [props.doctype, props.name], () => { rows.value = []; load(); });

// ── Expand diff ───────────────────────────────────────────────────────────────

function toggleExpand(id: string) {
  const s = new Set(expanded.value);
  s.has(id) ? s.delete(id) : s.add(id);
  expanded.value = s;
}

// ── Time formatting ───────────────────────────────────────────────────────────

function fmtRelative(iso: string) {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)     return "just now";
  if (diff < 3600)   return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400)  return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "2-digit" });
}

function fmtFull(iso: string) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

// ── Icon per type ─────────────────────────────────────────────────────────────

function typeIcon(row: any) {
  if (row.type === "comment") return row.comment_type === "Assignment" ? "👤" : "💬";
  if (row.type === "version") return "✏️";
  if (row.type === "todo")    return "☑️";
  return "•";
}

// ── Diff rendering ────────────────────────────────────────────────────────────

function formatDiff(diff: any[]): string {
  if (!Array.isArray(diff) || !diff.length) return "";
  return diff.map(item => {
    if (Array.isArray(item)) {
      const [field, oldVal, newVal] = item;
      return `${field}: ${oldVal ?? "—"} → ${newVal ?? "—"}`;
    }
    return JSON.stringify(item);
  }).join("\n");
}
</script>

<template>
  <div class="af-wrap" :class="compact && 'af-compact'">
    <!-- Loading -->
    <div v-if="loading && !rows.length" class="af-loading">
      <span class="af-spinner" />
      Loading activity…
    </div>

    <!-- Error -->
    <div v-else-if="error" class="af-error">
      <span>⚠ {{ error }}</span>
      <button class="af-retry" @click="load">Retry</button>
    </div>

    <!-- Empty -->
    <div v-else-if="!rows.length" class="af-empty">
      No activity yet
    </div>

    <!-- Feed rows -->
    <div v-else class="af-list">
      <div
        v-for="row in rows"
        :key="row.id"
        class="af-row"
        :class="`af-row--${row.type}`"
      >
        <!-- Avatar + line -->
        <div class="af-left">
          <Avatar :name="row.owner" :size="compact ? 22 : 26" />
          <div class="af-line" />
        </div>

        <!-- Body -->
        <div class="af-body">
          <div class="af-header">
            <span class="af-who">{{ row.owner_full_name || row.owner }}</span>
            <span class="af-dot">·</span>
            <span class="af-when" :title="fmtFull(row.creation)">{{ fmtRelative(row.creation) }}</span>
            <span v-if="row.type === 'version' && row.diff?.length" class="af-type-badge af-badge--change">change</span>
            <span v-else-if="row.type === 'comment'" class="af-type-badge af-badge--comment">comment</span>
            <span v-else-if="row.type === 'todo'"    class="af-type-badge af-badge--todo">task</span>
          </div>

          <!-- Content -->
          <div
            class="af-content"
            :class="row.type === 'comment' && 'af-content--comment'"
            v-html="row.type === 'comment' ? row.content : row.content"
          />

          <!-- Diff expansion (version only) -->
          <template v-if="row.type === 'version' && row.diff?.length">
            <button
              class="af-expand-btn"
              @click="toggleExpand(row.id)"
            >
              {{ expanded.has(row.id) ? "▲ Hide changes" : "▶ View changes" }}
            </button>
            <pre v-if="expanded.has(row.id)" class="af-diff">{{ formatDiff(row.diff) }}</pre>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.af-wrap {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 8px 0;
  overflow-y: auto;
}

.af-loading,
.af-empty,
.af-error {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 28px 16px;
  font-size: 12.5px;
  color: var(--text-3);
}

.af-error { color: var(--danger); flex-direction: column; gap: 6px; }
.af-retry {
  font-size: 11px; padding: 3px 10px; border: 1px solid var(--border-2);
  border-radius: 5px; background: var(--panel); cursor: pointer; color: var(--text-2);
}
.af-retry:hover { background: var(--row-hover); }

.af-spinner {
  width: 14px; height: 14px; border: 2px solid var(--border);
  border-top-color: var(--accent); border-radius: 50%;
  animation: afSpin .7s linear infinite; flex-shrink: 0;
}
@keyframes afSpin { to { transform: rotate(360deg); } }

/* ── List ── */
.af-list { display: flex; flex-direction: column; }

.af-row {
  display: flex;
  gap: 10px;
  padding: 0 12px;
  position: relative;
}

.af-row:last-child .af-line { display: none; }

/* ── Left: avatar + vertical line ── */
.af-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  padding-top: 2px;
}

.af-line {
  width: 1px;
  flex: 1;
  min-height: 14px;
  background: var(--border);
  margin-top: 4px;
}

/* ── Body ── */
.af-body {
  flex: 1;
  min-width: 0;
  padding: 2px 0 14px;
}

.af-header {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
  margin-bottom: 3px;
}

.af-who {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
}

.af-dot { font-size: 11px; color: var(--text-3); }

.af-when {
  font-size: 11px;
  color: var(--text-3);
  cursor: default;
}

.af-type-badge {
  font-size: 9.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .07em;
  padding: 1px 5px;
  border-radius: 3px;
}
.af-badge--change  { background: color-mix(in srgb, var(--accent) 12%, transparent); color: var(--accent-2); }
.af-badge--comment { background: color-mix(in srgb, var(--info, #3b82f6) 12%, transparent); color: var(--info, #3b82f6); }
.af-badge--todo    { background: color-mix(in srgb, var(--ok) 12%, transparent); color: var(--ok); }

.af-content {
  font-size: 12.5px;
  color: var(--text-2);
  line-height: 1.5;
  word-break: break-word;
}

.af-content--comment {
  background: var(--bg-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--text);
}

.af-expand-btn {
  margin-top: 4px;
  font-size: 11px;
  color: var(--accent);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-family: var(--font-sans);
}
.af-expand-btn:hover { text-decoration: underline; }

.af-diff {
  margin-top: 5px;
  padding: 8px 10px;
  background: var(--bg-2);
  border: 1px solid var(--border);
  border-radius: 5px;
  font-size: 11px;
  color: var(--text-2);
  font-family: var(--font-mono);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ── Compact ── */
.af-compact .af-body { padding-bottom: 10px; }
.af-compact .af-who  { font-size: 11.5px; }
.af-compact .af-when { font-size: 10.5px; }
.af-compact .af-content { font-size: 11.5px; }
</style>
