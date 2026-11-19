<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import Btn from "./Btn.vue";
import Icons from "./Icons.vue";
import { frappeList } from "../composables/useFrappe";

const props = withDefaults(
  defineProps<{ projectName: string; kind?: "brief" | "debrief" }>(),
  { kind: "brief" }
);
const emit  = defineEmits<{
  (e: "chosen", templateName: string | null): void;
}>();

// --- data ---
const templates  = ref<any[]>([]);
const recentBriefs = ref<any[]>([]);
const loading    = ref(true);
const activeTab  = ref("All");
const hovering   = ref<string | null>(null);

const CATEGORIES = ["All", "Production", "Marketing", "Conference", "Concert", "Corporate", "Other"];

// Doctype name varies by kind: Event Brief vs Event Debrief share the same template
// doctype (Event Brief Template) — only the `kind` field differs.
const previousDoctype = computed(() => (props.kind === "debrief" ? "Event Debrief" : "Event Brief"));
const labels = computed(() => props.kind === "debrief"
  ? {
      title: "Start your Event Debrief",
      sub: "Choose a debrief template to get started, or begin with a blank document.",
      blankName: "Blank debrief",
      blankDesc: "Start from scratch with an empty document.",
      recent: "Start from a previous debrief",
    }
  : {
      title: "Start your Event Brief",
      sub: "Choose a template to get started, or begin with a blank document.",
      blankName: "Blank brief",
      blankDesc: "Start from scratch with an empty document.",
      recent: "Start from a previous brief",
    });

onMounted(async () => {
  try {
    const [t, r] = await Promise.all([
      frappeList("Event Brief Template", {
        filters: { is_active: 1, kind: props.kind },
        fields: ["name", "template_name", "category", "description", "thumbnail", "content"],
        limit: 100,
      }),
      frappeList(previousDoctype.value, {
        fields: ["name", "project", "title", "modified"],
        filters: [["project", "!=", props.projectName]],
        limit: 5,
        order_by: "modified desc",
      }),
    ]);
    templates.value = t;
    recentBriefs.value = r;
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
});

const filtered = computed(() => {
  if (activeTab.value === "All") return templates.value;
  return templates.value.filter((t) => t.category === activeTab.value);
});

function previewContent(t: any): string {
  if (!t.content) return "";
  // Strip markdown syntax markers for plain-text preview
  return t.content
    .replace(/^#{1,6}\s+/gm, "")          // headings
    .replace(/\*\*(.+?)\*\*/g, "$1")       // bold
    .replace(/\*(.+?)\*/g, "$1")           // italic
    .replace(/`{1,3}[^`]*`{1,3}/g, "")    // code
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // links
    .replace(/^[-*+]\s+/gm, "")           // bullets
    .replace(/^\d+\.\s+/gm, "")           // numbered list
    .replace(/^[-]{3,}$/gm, "")           // hr
    .replace(/\n{2,}/g, " ")
    .trim()
    .slice(0, 140) + "…";
}
</script>

<template>
  <div class="gallery-wrap">
    <div class="gallery-head">
      <div>
        <h2 class="gallery-title">{{ labels.title }}</h2>
        <p class="gallery-sub">{{ labels.sub }}</p>
      </div>
    </div>

    <!-- Category tabs -->
    <div class="gallery-tabs">
      <button
        v-for="cat in CATEGORIES"
        :key="cat"
        class="gallery-tab"
        :class="{ 'gallery-tab--active': activeTab === cat }"
        @click="activeTab = cat"
      >{{ cat }}</button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="gallery-grid">
      <div v-for="i in 4" :key="i" class="template-card skeleton" />
    </div>

    <div v-else class="gallery-grid">
      <!-- Blank card -->
      <div
        v-if="activeTab === 'All'"
        class="template-card template-card--blank"
        @click="emit('chosen', null)"
      >
        <div class="template-card__icon"><Icons name="plus" :size="22" /></div>
        <div class="template-card__name">{{ labels.blankName }}</div>
        <div class="template-card__desc">{{ labels.blankDesc }}</div>
      </div>

      <!-- Template cards -->
      <div
        v-for="t in filtered"
        :key="t.name"
        class="template-card"
        :class="{ 'template-card--hover': hovering === t.name }"
        @mouseenter="hovering = t.name"
        @mouseleave="hovering = null"
        @click="emit('chosen', t.template_name)"
      >
        <div v-if="t.thumbnail" class="template-card__thumb">
          <img :src="t.thumbnail" :alt="t.template_name" />
        </div>
        <div v-else class="template-card__thumb template-card__thumb--default">
          <Icons name="brief" :size="28" style="color:var(--text-3);" />
        </div>

        <div class="template-card__info">
          <div class="template-card__cat">{{ t.category }}</div>
          <div class="template-card__name">{{ t.template_name }}</div>
          <div class="template-card__desc">{{ t.description }}</div>
        </div>

        <!-- Preview on hover -->
        <div v-if="hovering === t.name" class="template-preview">
          {{ previewContent(t) }}
        </div>
      </div>
    </div>

    <!-- Start from a previous brief / debrief -->
    <div v-if="recentBriefs.length && activeTab === 'All'" class="recent-section">
      <div class="recent-title">{{ labels.recent }}</div>
      <div class="recent-list">
        <button
          v-for="b in recentBriefs"
          :key="b.name"
          class="recent-item"
          @click="emit('chosen', b.name)"
        >
          <Icons name="brief" :size="14" style="flex-shrink:0;color:var(--text-3);" />
          <span class="recent-item__name">{{ b.title || b.project }}</span>
          <span class="recent-item__date mono">{{ new Date(b.modified).toLocaleDateString() }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.gallery-wrap { padding: 32px 40px 60px; max-width: 1100px; margin: 0 auto; }
.gallery-head { margin-bottom: 20px; }
.gallery-title { font-size: 22px; font-weight: 600; letter-spacing: -.02em; margin: 0 0 4px; }
.gallery-sub { font-size: 13px; color: var(--text-3); margin: 0; }

.gallery-tabs { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid var(--border); }
.gallery-tab {
  padding: 8px 12px; font-size: 12px; font-weight: 500;
  background: transparent; border: none; border-bottom: 2px solid transparent;
  cursor: pointer; color: var(--text-3); font-family: inherit;
  transition: color .12s;
}
.gallery-tab:hover { color: var(--text); }
.gallery-tab--active { color: var(--accent); border-bottom-color: var(--accent); }

.gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }

.template-card {
  border: 1px solid var(--border); background: var(--panel);
  border-radius: 10px; overflow: hidden; cursor: pointer;
  transition: border-color .15s, box-shadow .15s; position: relative;
}
.template-card:hover, .template-card--hover {
  border-color: var(--accent); box-shadow: 0 4px 16px rgba(204,120,92,.12);
}
.template-card--blank {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 8px; padding: 32px 20px;
  border-style: dashed; background: var(--bg-2);
}
.template-card--blank .template-card__icon { color: var(--text-3); }
.template-card--blank .template-card__name { font-size: 13px; font-weight: 600; }
.template-card--blank .template-card__desc { font-size: 11.5px; color: var(--text-3); text-align: center; }

.template-card__thumb {
  height: 120px; background: var(--bg-2);
  display: flex; align-items: center; justify-content: center; overflow: hidden;
}
.template-card__thumb img { width: 100%; height: 100%; object-fit: cover; }
.template-card__info { padding: 12px; }
.template-card__cat { font-size: 10px; text-transform: uppercase; letter-spacing: .1em; color: var(--text-3); margin-bottom: 4px; }
.template-card__name { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.template-card__desc { font-size: 11.5px; color: var(--text-3); line-height: 1.5; }

.template-preview {
  position: absolute; inset: 0; background: rgba(250,249,247,.95);
  padding: 12px; font-size: 11px; color: var(--text-2); line-height: 1.6;
  overflow: hidden; pointer-events: none;
}

.skeleton { height: 200px; background: var(--bg-2); animation: pulse 1.4s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.55} }

.recent-section { margin-top: 32px; }
.recent-title { font-size: 11px; text-transform: uppercase; letter-spacing: .1em; color: var(--text-3); margin-bottom: 10px; }
.recent-list { display: flex; flex-direction: column; gap: 4px; }
.recent-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; border-radius: 7px; cursor: pointer;
  background: transparent; border: 1px solid var(--border);
  color: var(--text); font-family: inherit; font-size: 12.5px; text-align: left;
  transition: background .1s;
}
.recent-item:hover { background: var(--row-hover); }
.recent-item__name { flex: 1; }
.recent-item__date { font-size: 11px; color: var(--text-3); }
</style>
