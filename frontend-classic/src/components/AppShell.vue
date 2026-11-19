<script setup lang="ts">
import { computed, inject, ref, type Ref, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";
import Icons from "./Icons.vue";
import Pill from "./Pill.vue";
import Btn from "./Btn.vue";
import Avatar from "./Avatar.vue";
import { RouterView } from "vue-router";

const route = useRoute();
const router = useRouter();

const project = inject<Ref<any>>("project");
const projectName = inject<Ref<string>>("projectName");

const NAV = [
  { key: "landing",  label: "Landing",       icon: "home" },
  { key: "brief",    label: "Event Brief",   icon: "brief" },
  { key: "action",   label: "Action Plan",   icon: "action" },
  { key: "timeline", label: "Timeline",      icon: "timeline" },
  { key: "schedule", label: "Scheduling",    icon: "schedule" },
  { key: "debrief",  label: "Event Debrief", icon: "debrief" },
];

const activePage = computed(() => {
  const path = route.path;
  const found = NAV.find((n) => path.endsWith("/" + n.key));
  return found?.key ?? "landing";
});

function navigate(key: string) {
  if (!projectName?.value) return;
  router.push(`/${encodeURIComponent(projectName.value)}/${key}`);
  // Close drawer on mobile after navigation
  if (window.innerWidth < 768) drawerOpen.value = false;
}

function goToDesk() {
  if (projectName?.value) {
    window.location.href = `/app/project/${encodeURIComponent(projectName.value)}`;
  } else {
    window.location.href = "/app";
  }
}

const statusColor: Record<string, string> = {
  Open: "#3B82F6",
  "In Progress": "#CC785C",
  Completed: "#22C55E",
  Cancelled: "#8F8A7E",
  Overdue: "#EF4444",
};

// ── Responsive ────────────────────────────────────────────────────────────────

const drawerOpen = ref(false);
const isMobile   = ref(false);
const isTablet   = ref(false);

function checkBreakpoints() {
  isMobile.value  = window.innerWidth < 768;
  isTablet.value  = window.innerWidth >= 768 && window.innerWidth < 1024;
}

onMounted(() => { checkBreakpoints(); window.addEventListener("resize", checkBreakpoints); });
onBeforeUnmount(() => { window.removeEventListener("resize", checkBreakpoints); });
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell--tablet': isTablet, 'app-shell--mobile': isMobile }">

    <!-- Mobile drawer backdrop -->
    <div v-if="isMobile && drawerOpen" class="drawer-backdrop" @click="drawerOpen = false" />

    <!-- Sidebar (desktop: always visible; tablet: icon-only rail; mobile: slide-over drawer) -->
    <aside class="sidebar" :class="{ 'sidebar--open': drawerOpen || (!isMobile && !isTablet), 'sidebar--rail': isTablet && !drawerOpen }">
      <div class="sidebar__brand">
        <span class="brand-mark">EP</span>
        <template v-if="!isTablet || drawerOpen">
          <div class="brand-text">
            <div class="brand-name">Planner</div>
            <div class="brand-tag">Event Planner</div>
          </div>
        </template>
        <button
          v-if="!isMobile"
          class="close-btn"
          title="Back to Desk"
          @click="goToDesk"
        >
          <Icons name="close" :size="12" />
        </button>
      </div>

      <div v-if="!isTablet || drawerOpen" class="section-lbl">Workspace</div>
      <nav class="nav">
        <button
          v-for="n in NAV"
          :key="n.key"
          class="nav-item"
          :class="{ 'nav-item--active': activePage === n.key, 'nav-item--rail': isTablet && !drawerOpen }"
          :title="(isTablet && !drawerOpen) ? n.label : undefined"
          @click="navigate(n.key)"
        >
          <Icons :name="n.icon" :size="15" />
          <span v-if="!isTablet || drawerOpen">{{ n.label }}</span>
        </button>
      </nav>

      <template v-if="!isTablet || drawerOpen">
        <div class="section-lbl">Current Event</div>
        <div class="event-card">
          <div class="event-card__name">{{ project?.project_name || projectName }}</div>
          <div class="event-card__id mono">{{ projectName }}</div>
          <div class="event-card__meta">
            <Pill :color="statusColor[project?.status] || '#8F8A7E'">
              {{ project?.status || "Open" }}
            </Pill>
          </div>
        </div>
      </template>

      <div class="sidebar__footer" :class="{ 'sidebar__footer--rail': isTablet && !drawerOpen }">
        <Avatar :name="project?.owner" :size="22" />
        <template v-if="!isTablet || drawerOpen">
          <div class="footer-user">
            <div class="footer-user__name">{{ project?.owner }}</div>
            <div class="footer-user__role">Project Owner</div>
          </div>
        </template>
      </div>
    </aside>

    <!-- Main content -->
    <div class="main">
      <!-- Topbar -->
      <header class="topbar">
        <!-- Hamburger (mobile/tablet) -->
        <button v-if="isMobile || isTablet" class="hamburger" @click="drawerOpen = !drawerOpen" aria-label="Toggle menu">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
            <path d="M2 4h12M2 8h12M2 12h12"/>
          </svg>
        </button>

        <button class="desk-btn" @click="goToDesk">
          <Icons name="back" :size="12" />
          <span class="desk-btn-label">Desk</span>
        </button>
        <span class="topbar__sep"><Icons name="chevright" :size="12" /></span>
        <div class="topbar__title">{{ project?.project_name || projectName }}</div>
        <Pill :color="statusColor[project?.status] || '#8F8A7E'" style="margin-left:4px;flex-shrink:0;">
          {{ project?.status || "Open" }}
        </Pill>
      </header>

      <!-- Page content -->
      <div class="content">
        <RouterView />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── Drawer backdrop ──────────────────────────────────────────────────────── */
.drawer-backdrop {
  position: fixed; inset: 0; z-index: 98;
  background: rgba(0,0,0,.3);
  animation: fadein 120ms ease-out;
}
@keyframes fadein { from { opacity: 0; } to { opacity: 1; } }

/* ── Shell ────────────────────────────────────────────────────────────────── */
.app-shell {
  display: grid;
  grid-template-columns: 232px 1fr;
  height: 100vh;
  overflow: hidden;
  background: var(--bg);
}

/* ── Sidebar ── */
.sidebar {
  border-right: 1px solid var(--border);
  background: var(--bg-2);
  display: flex;
  flex-direction: column;
  min-height: 0;
  transition: width 180ms ease, transform 180ms ease;
}
.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  border-bottom: 1px solid var(--border);
}
.brand-mark {
  width: 26px; height: 26px; border-radius: 7px;
  background: var(--accent); color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 10px; letter-spacing: .02em;
  flex-shrink: 0;
}
.brand-text { line-height: 1.15; }
.brand-name { font-size: 13.5px; font-weight: 600; letter-spacing: -.015em; }
.brand-tag  { font-size: 10px; color: var(--text-3); text-transform: uppercase; letter-spacing: .1em; margin-top: 1px; }
.close-btn {
  margin-left: auto; background: transparent; border: 1px solid var(--border);
  color: var(--text-2); width: 24px; height: 24px; border-radius: 5px;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
.section-lbl {
  font-size: 10px; color: var(--text-3); text-transform: uppercase;
  letter-spacing: .12em; padding: 18px 16px 8px; font-weight: 500;
}
.nav { display: flex; flex-direction: column; gap: 1px; }
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; margin: 0 8px; border-radius: 7px;
  color: var(--text-2); background: transparent;
  border: 1px solid transparent; font-size: 13px; font-weight: 450;
  cursor: pointer; text-align: left; font-family: inherit;
  transition: background .12s, color .12s;
}
.nav-item:hover { background: var(--row-hover); }
.nav-item--active { color: var(--accent); background: var(--accent-soft); font-weight: 550; }
.nav-item--active:hover { background: var(--accent-soft); }

.event-card {
  margin: 4px 10px 10px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: var(--panel);
}
.event-card__name { font-size: 12px; font-weight: 600; letter-spacing: -.01em; }
.event-card__id { font-size: 10.5px; color: var(--text-3); margin-top: 2px; }
.event-card__meta { display: flex; gap: 6px; margin-top: 8px; align-items: center; }

.sidebar__footer {
  margin-top: auto;
  border-top: 1px solid var(--border);
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.footer-user { min-width: 0; flex: 1; }
.footer-user__name { font-size: 12px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.footer-user__role { font-size: 10.5px; color: var(--text-3); }

/* ── Main ── */
.main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
.topbar {
  height: 52px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 10px;
  padding: 0 20px;
  background: var(--panel);
  flex-shrink: 0;
  z-index: 10;
}
.desk-btn {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--panel); border: 1px solid var(--border);
  color: var(--text-2); padding: 4px 10px; border-radius: 6px;
  cursor: pointer; font-size: 11.5px; height: 28px; font-weight: 500;
  flex-shrink: 0; font-family: inherit;
}
.desk-btn:hover { background: var(--row-hover); }
.topbar__sep { color: var(--text-3); }
.topbar__title {
  font-size: 13.5px; font-weight: 600; letter-spacing: -.015em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* Content area: fills remaining height; pages scroll inside here.
   Pages that want fixed/Gantt layout use height:100%+overflow:hidden themselves. */
.content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  background: var(--bg);
  /* Lets child pages use height:100% to fill this area */
  display: flex;
  flex-direction: column;
}

/* ── Hamburger ────────────────────────────────────────────────────────────── */
.hamburger {
  width: 32px; height: 32px; border-radius: 6px;
  background: none; border: 1px solid var(--border); cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  color: var(--text-2); flex-shrink: 0;
}
.hamburger:hover { background: var(--row-hover); }

/* ── Tablet: icon-only rail ──────────────────────────────────────────────── */
.app-shell--tablet {
  grid-template-columns: 52px 1fr;
}
.sidebar--rail {
  width: 52px; overflow: hidden;
}
.sidebar--rail .sidebar__brand { justify-content: center; padding: 12px 8px; }
.nav-item--rail {
  padding: 8px; margin: 0 4px; justify-content: center;
}
.nav-item--rail > span { display: none; }
.sidebar__footer--rail {
  justify-content: center; padding: 10px 0;
}
.sidebar__footer--rail .footer-user { display: none; }

/* ── Mobile: full drawer ─────────────────────────────────────────────────── */
.app-shell--mobile {
  grid-template-columns: 1fr;
}
.app-shell--mobile .sidebar {
  position: fixed; top: 0; left: 0; bottom: 0;
  width: 260px; z-index: 99; transform: translateX(-100%);
  box-shadow: 4px 0 20px rgba(26,25,21,.15);
}
.app-shell--mobile .sidebar--open {
  transform: translateX(0);
}
.app-shell--mobile .main {
  grid-column: 1;
}
.desk-btn-label { display: none; }
@media (min-width: 768px) {
  .desk-btn-label { display: inline; }
}
</style>
