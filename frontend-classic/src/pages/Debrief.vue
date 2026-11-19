<script setup lang="ts">
import { inject, onMounted, ref, watch, computed } from "vue";
import type { Ref } from "vue";
import BriefGallery from "../components/BriefGallery.vue";
import TiptapEditor from "../components/TiptapEditor.vue";
import ActivityFeed from "../components/ActivityFeed.vue";
import { frappeCall, frappeList, frappeSave } from "../composables/useFrappe";

const project     = inject<Ref<any>>("project");
const projectName = inject<Ref<string>>("projectName");

const debrief        = ref<any>(null);
const debriefLoaded  = ref(false);
const showGallery    = ref(false);
const saveState      = ref<"saved" | "saving" | "error">("saved");
const markdownContent = ref("");
let saveTimer: ReturnType<typeof setTimeout> | null = null;

const sidebarOpen = ref(false);
const sidebarTab  = ref<"activity">("activity");

const docMeta = ref<any>(null);

const tiptap = ref<InstanceType<typeof TiptapEditor> | null>(null);

function tbIsActive(name: string, attrs?: Record<string, unknown>) {
  return tiptap.value?.isActive(name, attrs) ?? false;
}

function tbRun(cmd: string) {
  tiptap.value?.run(cmd);
}

onMounted(async () => { if (projectName?.value) await loadDebrief(); });

watch(() => projectName?.value, async (n) => { if (n) await loadDebrief(); });

async function loadDebrief() {
  debriefLoaded.value = false;
  docMeta.value = null;
  try {
    const rows = await frappeList("Event Debrief", {
      filters: { project: projectName!.value },
      fields: ["name", "project", "title", "content", "version", "modified", "modified_by", "template", "owner"],
      limit: 1,
    });
    if (rows.length) {
      debrief.value = rows[0];
      markdownContent.value = rows[0].content || getStarterTemplate();
      showGallery.value = false;
      loadDocMeta(rows[0].name);
    } else {
      debrief.value = null;
      markdownContent.value = "";
      showGallery.value = true;
    }
  } catch (e) {
    console.error("[Debrief] load error:", e);
  } finally {
    debriefLoaded.value = true;
  }
}

async function loadDocMeta(name: string) {
  try {
    docMeta.value = await frappeCall("event_planner.api.get_doc_meta", {
      doctype: "Event Debrief",
      name,
    });
  } catch { /* non-critical */ }
}

function getStarterTemplate(): string {
  return `## Summary\n\nA short summary of how the event went — dates, scale, headline outcome.\n\n## What Went Well\n\n- Highlight 1\n- Highlight 2\n- Highlight 3\n\n## What Didn't Go Well\n\n- Issue 1\n- Issue 2\n- Issue 3\n\n## Metrics\n\n- **Attendance (target / actual):**\n- **Budget (planned / spent):**\n- **On-time delivery:**\n- **Client satisfaction:**\n\n## Lessons Learned\n\n1. Lesson 1\n2. Lesson 2\n3. Lesson 3\n\n## Action Items For Next Time\n\n- [ ] Owner — Action\n- [ ] Owner — Action\n\n## Sign-off\n\n- **Debriefed by:**\n- **Date:**\n`;
}

function onContentChange(content: string) {
  markdownContent.value = content;
  if (!debrief.value) return;
  saveState.value = "saving";
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => persistDebrief(content), 800);
}

async function persistDebrief(content: string) {
  if (!debrief.value) return;
  try {
    const updated = await frappeSave("Event Debrief", debrief.value.name, {
      project:  projectName!.value,
      title:    debrief.value.title,
      template: debrief.value.template,
      content,
    });
    debrief.value = { ...debrief.value, ...updated };
    saveState.value = "saved";
    if (debrief.value?.name) loadDocMeta(debrief.value.name);
  } catch {
    saveState.value = "error";
  }
}

async function onTemplateChosen(templateName: string | null) {
  const result = await frappeCall("event_planner.api.create_debrief_from_template", {
    project: projectName!.value,
    template: templateName,
  });
  debrief.value = result;
  markdownContent.value = result.content || getStarterTemplate();
  showGallery.value = false;
  loadDocMeta(result.name);
}

function relativeTime(dt?: string) {
  if (!dt) return "";
  const diff = (Date.now() - new Date(dt).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`;
  return `${Math.floor(diff / 86400)} days ago`;
}

function exportPdf() {
  if (!debrief.value?.name) return;
  // Reuses the Event Brief print format until a dedicated debrief format ships.
  const url = `/api/method/frappe.utils.print_format.download_pdf?doctype=Event Debrief&name=${encodeURIComponent(debrief.value.name)}&format=Standard`;
  window.open(url, "_blank");
}

const lastEditedBy = computed(() => docMeta.value?.modified_by_full_name || debrief.value?.modified_by || "");
const lastEditedAt = computed(() => docMeta.value?.modified || debrief.value?.modified || "");
const createdBy    = computed(() => docMeta.value?.owner_full_name || debrief.value?.owner || "");
const createdAt    = computed(() => docMeta.value?.creation || "");
</script>

<template>
  <!-- Template gallery -->
  <BriefGallery
    v-if="debriefLoaded && showGallery"
    :project-name="projectName ?? ''"
    kind="debrief"
    @chosen="onTemplateChosen"
  />

  <!-- Document editor -->
  <div v-else-if="debriefLoaded && debrief" class="brief-wrap" :class="{ 'brief-wrap--sidebar': sidebarOpen }">

    <!-- Sticky formatting toolbar -->
    <div class="doc-toolbar">
      <div class="tb-left">
        <button class="tb-btn" :class="{ active: tbIsActive('heading', { level: 1 }) }" @click="tbRun('h1')" title="Heading 1">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v10M9 3v10M3 8h6M11.5 5l1.5-1v9"/></svg>
        </button>
        <button class="tb-btn" :class="{ active: tbIsActive('heading', { level: 2 }) }" @click="tbRun('h2')" title="Heading 2">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v10M8 3v10M3 8h5M10 5.5a1.5 1.5 0 0 1 3 0c0 2.5-3 3.5-3 5.5h3"/></svg>
        </button>
        <button class="tb-btn" :class="{ active: tbIsActive('heading', { level: 3 }) }" @click="tbRun('h3')" title="Heading 3">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v10M8 3v10M3 8h5M10 5.5a1.5 1.5 0 0 1 2 0M10 8a1.5 1.5 0 0 1 2 0v.5a1.5 1.5 0 0 1-2 0"/></svg>
        </button>

        <div class="tb-sep" />

        <button class="tb-btn" :class="{ active: tbIsActive('bold') }"        @click="tbRun('bold')"        title="Bold">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 3h3.5a2 2 0 0 1 0 4H4.5zM4.5 7h4.5a2 2 0 0 1 0 4H4.5z"/></svg>
        </button>
        <button class="tb-btn" :class="{ active: tbIsActive('italic') }"      @click="tbRun('italic')"      title="Italic">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M7 3h5M4 13h5M9.5 3 6.5 13"/></svg>
        </button>
        <button class="tb-btn" :class="{ active: tbIsActive('underline') }"   @click="tbRun('underline')"   title="Underline">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 3v5a3.5 3.5 0 0 0 7 0V3M3.5 13.5h9"/></svg>
        </button>
        <button class="tb-btn" :class="{ active: tbIsActive('highlight') }"   @click="tbRun('highlight')"   title="Highlight">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="m5 11-3 3v1h3l8-8-3-3z"/><path d="M12 4.5 13.5 6"/></svg>
        </button>
        <button class="tb-btn" :class="{ active: tbIsActive('code') }"        @click="tbRun('code')"        title="Inline code">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5.5 4 2 8l3.5 4M10.5 4 14 8l-3.5 4"/></svg>
        </button>

        <div class="tb-sep" />

        <button class="tb-btn" :class="{ active: tbIsActive('bulletList') }"  @click="tbRun('bulletList')"  title="Bullet list">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4h.01M3 8h.01M3 12h.01M6 4h7M6 8h7M6 12h7"/></svg>
        </button>
        <button class="tb-btn" :class="{ active: tbIsActive('orderedList') }" @click="tbRun('orderedList')" title="Numbered list">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3.5h1.5v3H3M3 7h1.5M7 4h6M7 8h6M7 12h6"/></svg>
        </button>
        <button class="tb-btn" :class="{ active: tbIsActive('blockquote') }"  @click="tbRun('blockquote')"  title="Quote">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5.5c0-1 .5-2 2-2M3 5.5h2.5V9H3zM8 5.5c0-1 .5-2 2-2M8 5.5h2.5V9H8z"/></svg>
        </button>

        <div class="tb-sep" />

        <button class="tb-btn" title="Insert table" @click="tbRun('table')">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="12" height="12" rx="1"/><path d="M2 6h12M2 10h12M6 2v12"/></svg>
        </button>
        <button class="tb-btn" title="Insert image" @click="tbRun('image')">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="1.5" y="3" width="13" height="10" rx="1"/><path d="m1.5 10 4-3 3 2.5 2.5-2 4 3.5"/><circle cx="5" cy="6.5" r="1.2"/></svg>
        </button>
        <button class="tb-btn" :class="{ active: tbIsActive('link') }" @click="tbRun('link')" title="Link">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M7 9.5a2.5 2.5 0 0 0 3.5 0l2-2a2.5 2.5 0 0 0-3.5-3.5l-1 1M9 6.5a2.5 2.5 0 0 0-3.5 0l-2 2a2.5 2.5 0 0 0 3.5 3.5l1-1"/></svg>
        </button>

        <div class="tb-sep" />

        <div class="tb-save" :class="`tb-save--${saveState}`">
          <span class="tb-save-dot" />
          <span class="tb-save-label">{{ saveState === 'saved' ? 'Saved' : saveState === 'saving' ? 'Saving…' : 'Error' }}</span>
        </div>
      </div>

      <div class="tb-right">
        <span v-if="lastEditedBy" class="tb-last-edit" :title="`Created by ${createdBy}${createdAt ? ' · ' + new Date(createdAt).toLocaleString() : ''}`">
          <svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2a6 6 0 1 1 0 12A6 6 0 0 1 8 2zM8 5v4l2.5 1.5"/></svg>
          Edited by {{ lastEditedBy }} · {{ relativeTime(lastEditedAt) }}
        </span>

        <button class="tb-action" @click="showGallery = true" title="Change template">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 2.5h6l2.5 2.5v8a.5.5 0 0 1-.5.5H4a.5.5 0 0 1-.5-.5v-10A.5.5 0 0 1 4 2.5ZM10 2.5V5h2.5M5.5 8h5M5.5 10.5h5"/></svg>
          Template
        </button>
        <button class="tb-action tb-action--primary" @click="exportPdf">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2.5v8M4.5 7 8 10.5 11.5 7M3 13h10"/></svg>
          Export PDF
        </button>

        <button
          class="tb-action tb-icon-btn"
          :class="{ active: sidebarOpen }"
          title="Toggle activity"
          @click="sidebarOpen = !sidebarOpen"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 2a6 6 0 0 1 0 12 6 6 0 0 1 0-12z"/>
            <circle cx="8" cy="8" r="1.5" fill="currentColor" stroke="none"/>
            <path d="M8 5v1M8 10v1M5 8H4M12 8h-1"/>
          </svg>
          Activity
        </button>
      </div>
    </div>

    <!-- Main content area (editor + optional sidebar) -->
    <div class="doc-body-wrap">
      <div class="doc-body">
        <div class="doc-header">
          <div class="doc-kicker">Event Debrief · <span class="mono">v{{ debrief.version }}</span></div>
          <h1 class="doc-title">{{ debrief.title || projectName }}</h1>
          <div class="doc-meta">
            <span class="mono">{{ debrief.name }}</span>
            <span class="meta-dot">·</span>
            <span>Owner: {{ createdBy || debrief.owner }}</span>
            <span class="meta-dot">·</span>
            <span>Last edited {{ relativeTime(lastEditedAt) }}<template v-if="lastEditedBy"> by <strong>{{ lastEditedBy }}</strong></template></span>
          </div>
        </div>

        <div class="doc-editor">
          <TiptapEditor
            ref="tiptap"
            v-model="markdownContent"
            placeholder="Start writing the debrief…"
            :last-modified="lastEditedAt"
            :last-modified-by="lastEditedBy"
            @update:model-value="onContentChange"
          />
        </div>
      </div>

      <!-- Activity sidebar -->
      <aside v-if="sidebarOpen" class="brief-sidebar">
        <div class="bs-header">
          <div class="bs-tabs">
            <button class="bs-tab active">Activity</button>
          </div>
          <button class="bs-close" @click="sidebarOpen = false" title="Close">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 3l10 10M13 3 3 13"/></svg>
          </button>
        </div>

        <div class="bs-body">
          <div class="bs-info-strip">
            <div class="bsi-row">
              <span class="bsi-label">Created by</span>
              <span class="bsi-val">{{ createdBy }}</span>
            </div>
            <div v-if="createdAt" class="bsi-row">
              <span class="bsi-label">Created on</span>
              <span class="bsi-val">{{ new Date(createdAt).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) }}</span>
            </div>
            <div class="bsi-row">
              <span class="bsi-label">Last edited by</span>
              <span class="bsi-val">{{ lastEditedBy }}</span>
            </div>
            <div v-if="lastEditedAt" class="bsi-row">
              <span class="bsi-label">Last edited</span>
              <span class="bsi-val">{{ relativeTime(lastEditedAt) }}</span>
            </div>
          </div>

          <div class="bs-divider" />

          <ActivityFeed
            v-if="debrief?.name"
            doctype="Event Debrief"
            :name="debrief.name"
            :compact="false"
          />
        </div>
      </aside>
    </div>
  </div>

  <!-- Loading state -->
  <div v-else class="brief-loading">
    <div class="loading-spinner" />
    <span>Loading debrief…</span>
  </div>
</template>

<style scoped>
/* ── Outer wrapper ──────────────────────────────────────────────────────── */
.brief-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--bg);
}

/* ── Sticky toolbar ─────────────────────────────────────────────────────── */
.doc-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 20px;
  height: 42px;
  background: rgba(250, 249, 247, .92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 20;
  overflow-x: auto;
}

.tb-left  { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }
.tb-right { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }

.tb-sep { width: 1px; height: 16px; background: var(--border); margin: 0 4px; flex-shrink: 0; }

.tb-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; padding: 0;
  border: 1px solid transparent; border-radius: 4px;
  background: transparent; color: var(--text-2); cursor: pointer;
  transition: background 120ms, color 120ms, border-color 120ms;
  flex-shrink: 0;
}
.tb-btn:hover { background: var(--row-hover); color: var(--text); }
.tb-btn.active { background: var(--accent-soft); color: var(--accent-2); border-color: rgba(204, 120, 92, .3); }

.tb-save {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 8px; border: 1px solid var(--border); border-radius: 4px;
  font-size: 11px; color: var(--text-3);
}
.tb-save-dot { width: 6px; height: 6px; border-radius: 999px; background: currentColor; flex-shrink: 0; }
.tb-save--saved  { color: var(--ok); }
.tb-save--saving { color: var(--warn); }
.tb-save--error  { color: var(--danger); }
.tb-save-label   { font-size: 11px; font-weight: 500; }

.tb-last-edit {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 10.5px; color: var(--text-3);
  cursor: default; white-space: nowrap; padding: 0 6px;
}

.tb-action {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 10px; height: 28px;
  border: 1px solid var(--border-2); border-radius: 6px;
  background: var(--panel); color: var(--text-2);
  font-size: 12px; font-weight: 500; cursor: pointer;
  transition: background 120ms, color 120ms;
  box-shadow: 0 1px 2px rgba(26,25,21,.03);
  white-space: nowrap; flex-shrink: 0;
}
.tb-action:hover { background: var(--bg-2); color: var(--text); }
.tb-action--primary { background: var(--accent); border-color: var(--accent); color: white; box-shadow: 0 1px 2px rgba(204,120,92,.25); }
.tb-action--primary:hover { background: var(--accent-2); border-color: var(--accent-2); }
.tb-action.active { background: var(--accent-soft); border-color: var(--accent); color: var(--accent-2); }

/* ── Body wrap: editor + sidebar ────────────────────────────────────────── */
.doc-body-wrap { flex: 1; min-height: 0; display: flex; }
.doc-body      { flex: 1; overflow-y: auto; min-height: 0; min-width: 0; }

.doc-header { max-width: 860px; margin: 0 auto; padding: 36px 48px 0; }
.doc-kicker { font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: .14em; color: var(--text-3); margin-bottom: 12px; }
.doc-title  { font-size: 30px; font-weight: 600; letter-spacing: -.025em; line-height: 1.15; margin: 0 0 12px; color: var(--text); }
.doc-meta   {
  display: flex; align-items: center; flex-wrap: wrap; gap: 8px;
  font-size: 11.5px; color: var(--text-3);
  padding-bottom: 24px; border-bottom: 1px solid var(--border); margin-bottom: 8px;
}
.doc-meta strong { font-weight: 600; color: var(--text-2); }
.meta-dot { color: var(--border-2); }

.doc-editor { max-width: 860px; margin: 0 auto; padding: 0 48px 80px; }

.doc-editor :deep(.notion-editor) { background: transparent; border-radius: 0; }
.doc-editor :deep(.ProseMirror)   { padding: 8px 0 40px; font-size: 14px; line-height: 1.72; min-height: 320px; }
.doc-editor :deep(.editor-footer) { border-top: none; background: transparent; padding: 4px 0 0; }
.doc-editor :deep(.ProseMirror h2) {
  display: flex; align-items: center; gap: 7px;
  font-size: 10.5px !important; font-weight: 600 !important;
  text-transform: uppercase; letter-spacing: .12em; color: var(--text-3) !important;
  margin: 2.8em 0 0.6em !important; line-height: 1 !important; padding: 0 !important; border: none !important;
}
.doc-editor :deep(.ProseMirror h2::before) {
  content: ''; display: inline-block; width: 5px; height: 5px;
  border-radius: 50%; background: var(--accent); flex-shrink: 0;
}
.doc-editor :deep(.ProseMirror h2:first-child) { margin-top: 0.6em !important; }
.doc-editor :deep(.ProseMirror h3) { font-size: 20px !important; font-weight: 600 !important; letter-spacing: -.02em !important; margin: 0 0 8px !important; line-height: 1.25 !important; color: var(--text) !important; }
.doc-editor :deep(.ProseMirror p) { margin: 0.5em 0; color: var(--text); }
.doc-editor :deep(.ProseMirror ul),
.doc-editor :deep(.ProseMirror ol) { margin: 0.4em 0; }
.doc-editor :deep(.ProseMirror h1) { font-size: 24px !important; font-weight: 700 !important; letter-spacing: -.03em !important; margin: 1.5em 0 0.5em !important; }

/* ── Activity sidebar ───────────────────────────────────────────────────── */
.brief-sidebar {
  width: 300px; flex-shrink: 0;
  border-left: 1px solid var(--border); background: var(--panel);
  display: flex; flex-direction: column; overflow: hidden;
}
.bs-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-bottom: 1px solid var(--border);
  background: var(--panel-2); flex-shrink: 0;
}
.bs-tabs { display: flex; gap: 4px; }
.bs-tab {
  font-size: 12px; font-weight: 500; padding: 3px 10px; border-radius: 5px;
  border: 1px solid transparent; background: none; cursor: pointer; color: var(--text-2);
}
.bs-tab.active { background: var(--accent-soft); color: var(--accent-2); border-color: rgba(204,120,92,.25); }

.bs-close {
  width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;
  border: none; background: none; cursor: pointer; color: var(--text-3); border-radius: 4px;
}
.bs-close:hover { background: var(--row-hover); color: var(--text); }

.bs-body { flex: 1; overflow-y: auto; min-height: 0; }
.bs-info-strip { padding: 10px 12px; display: flex; flex-direction: column; gap: 5px; }
.bsi-row { display: flex; align-items: center; gap: 6px; font-size: 11.5px; }
.bsi-label { color: var(--text-3); font-weight: 500; min-width: 80px; flex-shrink: 0; }
.bsi-val   { color: var(--text); }
.bs-divider { height: 1px; background: var(--border); margin: 0 12px 4px; }

/* ── Loading ────────────────────────────────────────────────────────────── */
.brief-loading {
  display: flex; align-items: center; justify-content: center;
  height: 60vh; gap: 12px; color: var(--text-3); font-size: 13px;
}
.loading-spinner {
  width: 18px; height: 18px; border: 2px solid var(--border);
  border-top-color: var(--accent); border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Responsive ─────────────────────────────────────────────────────────── */
@media (max-width: 1024px) {
  .doc-header, .doc-editor { padding-left: 24px; padding-right: 24px; }
  .brief-sidebar { width: 260px; }
}
@media (max-width: 768px) {
  .brief-sidebar { width: 100%; border-left: none; border-top: 1px solid var(--border); max-height: 50vh; }
  .doc-body-wrap { flex-direction: column; }
  .tb-last-edit  { display: none; }
}
</style>
