<script setup lang="ts">
import { computed, inject, onMounted, ref, type Ref } from "vue";
import Pill from "../components/Pill.vue";
import Btn from "../components/Btn.vue";
import Avatar from "../components/Avatar.vue";
import Icons from "../components/Icons.vue";
import { frappeCall, frappeList } from "../composables/useFrappe";

const project = inject<Ref<any>>("project");
const projectName = inject<Ref<string>>("projectName");

// --- Stats from api ---
const summary = ref<any>(null);
const activity = ref<any[]>([]);
const loading = ref(true);

onMounted(async () => {
  if (!projectName?.value) return;
  try {
    const [s, a] = await Promise.all([
      frappeCall("event_planner.api.get_landing_summary", { project: projectName.value }),
      frappeCall("event_planner.api.get_recent_activity", { project: projectName.value, limit: 8 }),
    ]);
    summary.value = s;
    activity.value = a || [];
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
});

// Days remaining
const daysRemaining = computed(() => {
  const end = project?.value?.expected_end_date;
  if (!end) return null;
  const diff = Math.ceil((new Date(end).getTime() - Date.now()) / 86400000);
  return diff;
});

// Format date nicely
function fmtDate(d?: string) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

// Activity icon type → colour
const ACT_COLOR: Record<string, string> = {
  task: "#3B82F6",
  file: "#A78BFA",
  budget: "#22C55E",
  assign: "#F59E0B",
  comment: "#6C6E76",
};
</script>

<template>
  <div class="landing">
    <!-- Page header -->
    <div class="landing__head">
      <div>
        <h1 class="landing__title">{{ project?.project_name || projectName }}</h1>
        <div class="landing__sub">
          Overview · last edited by {{ project?.modified_by || project?.owner }}
        </div>
      </div>
      <div class="landing__actions">
        <Btn icon="download">Export Summary</Btn>
        <Btn kind="primary" icon="check">Mark as Complete</Btn>
      </div>
    </div>

    <!-- Stat strip -->
    <div class="stat-strip" v-if="!loading">
      <div class="stat-card">
        <div class="stat-card__num mono">{{ summary?.tasks_total ?? "—" }}</div>
        <div class="stat-card__lbl">Tasks Total</div>
        <div class="stat-card__sub">
          {{ summary?.tasks_open ?? 0 }} open ·
          {{ summary?.tasks_done ?? 0 }} done
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__num mono">{{ daysRemaining !== null ? daysRemaining : "—" }}</div>
        <div class="stat-card__lbl">Days Remaining</div>
        <div class="stat-card__sub" v-if="project?.expected_end_date">
          Event ends {{ fmtDate(project.expected_end_date) }}
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__num mono">{{ summary?.equipment_lines ?? "—" }}</div>
        <div class="stat-card__lbl">Equipment Lines</div>
        <div class="stat-card__sub">{{ summary?.equipment_delivered ?? 0 }} delivered</div>
      </div>
      <div class="stat-card">
        <div class="stat-card__num mono">{{ summary?.crew_members ?? "—" }}</div>
        <div class="stat-card__lbl">Crew Members</div>
        <div class="stat-card__sub">{{ summary?.vehicle_assignments ?? 0 }} vehicle assignments</div>
      </div>
    </div>
    <div class="stat-strip stat-strip--skeleton" v-else>
      <div class="stat-card skeleton" v-for="i in 4" :key="i" />
    </div>

    <!-- Two-column grid -->
    <div class="landing__grid">
      <!-- Event details card -->
      <div class="ep-card">
        <h3 class="card-title">Event Details</h3>
        <dl class="kv">
          <dt>Project</dt>
          <dd>{{ project?.project_name }}</dd>
          <dt>Customer</dt>
          <dd>{{ project?.customer || "—" }}</dd>
          <dt>Start Date</dt>
          <dd class="mono">{{ fmtDate(project?.expected_start_date) }}</dd>
          <dt>End Date</dt>
          <dd class="mono">{{ fmtDate(project?.expected_end_date) }}</dd>
          <dt>Location</dt>
          <dd>{{ project?.ep_location || "—" }}</dd>
          <dt>Department</dt>
          <dd>{{ project?.department || "—" }}</dd>
          <dt>Schedule Status</dt>
          <dd>
            <Pill :color="project?.ep_schedule_status === 'Scheduled' ? '#3B82F6' : '#F59E0B'">
              {{ project?.ep_schedule_status || "—" }}
            </Pill>
          </dd>
          <dt>Owner</dt>
          <dd>
            <span style="display:inline-flex;align-items:center;gap:6px;">
              <Avatar :name="project?.owner" :size="18" />
              {{ project?.owner }}
            </span>
          </dd>
        </dl>
      </div>

      <!-- Recent activity card -->
      <div class="ep-card">
        <h3 class="card-title">Recent Activity</h3>
        <div v-if="loading" class="activity-skeleton">
          <div v-for="i in 5" :key="i" class="activity-skeleton__row" />
        </div>
        <div v-else-if="activity.length === 0" style="color:var(--text-3);font-size:12px;padding:8px 0;">
          No recent activity.
        </div>
        <div v-else class="activity-list">
          <div
            v-for="(a, i) in activity"
            :key="i"
            class="activity-row"
            :style="{ borderBottom: i < activity.length - 1 ? '1px solid var(--border)' : 'none' }"
          >
            <Avatar :name="a.owner" :size="20" :color="ACT_COLOR[a.type] || '#8F8A7E'" />
            <div class="activity-row__body">
              <div class="activity-row__text">
                <span class="activity-row__who">{{ a.owner }}</span>
                {{ " " }}
                <span style="color:var(--text-2);">{{ a.content }}</span>
              </div>
              <div class="activity-row__when mono">{{ a.when }}</div>
            </div>
          </div>
        </div>
        <button class="view-all-btn">View all activity →</button>
      </div>
    </div>

    <!-- Milestones rail -->
    <div class="ep-card milestones" v-if="summary?.milestones?.length">
      <div class="milestones__head">
        <h3 class="card-title" style="margin-bottom:0;">Milestones</h3>
        <span class="mono" style="font-size:11px;color:var(--text-3);">
          {{ summary.milestones.filter((m: any) => m.done).length }} of {{ summary.milestones.length }} complete
        </span>
      </div>
      <div class="milestones__rail">
        <div class="milestones__line" />
        <div
          class="milestones__progress"
          :style="{ width: (summary.milestones.filter((m:any)=>m.done).length / summary.milestones.length * 86) + '%' }"
        />
        <div
          v-for="(m, i) in summary.milestones"
          :key="i"
          class="milestone"
        >
          <div class="milestone__dot" :class="{ 'milestone__dot--done': m.done }">
            <Icons v-if="m.done" name="check" :size="10" />
            <span v-else class="milestone__inner" />
          </div>
          <div class="milestone__label" :class="{ 'milestone__label--done': m.done }">{{ m.label }}</div>
          <div class="milestone__date mono">{{ m.date }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.landing { padding: 24px 28px; width: 100%; flex: 1; }
.landing__head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; }
.landing__title { font-size: 22px; font-weight: 600; letter-spacing: -.02em; margin: 0; }
.landing__sub { color: var(--text-3); font-size: 12.5px; margin-top: 4px; }
.landing__actions { display: flex; gap: 8px; }

/* Stat strip */
.stat-strip { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-top: 20px; }
.stat-card {
  border: 1px solid var(--border); background: var(--panel);
  border-radius: 8px; padding: 14px;
}
.stat-card__num { font-size: 24px; font-weight: 600; letter-spacing: -.02em; }
.stat-card__lbl { font-size: 11px; color: var(--text-3); text-transform: uppercase; letter-spacing: .08em; margin-top: 4px; }
.stat-card__sub { font-size: 11.5px; color: var(--text-3); margin-top: 6px; }
.skeleton { background: var(--bg-2); border-color: var(--border); min-height: 80px; border-radius: 8px; animation: pulse 1.4s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.55} }

/* 2-col grid */
.landing__grid { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-top: 20px; }
.card-title { font-size: 11px; text-transform: uppercase; letter-spacing: .1em; color: var(--text-3); margin: 0 0 12px; }

/* KV table */
.kv { display: grid; grid-template-columns: 120px 1fr; row-gap: 10px; column-gap: 12px; font-size: 12.5px; margin: 0; }
.kv dt { color: var(--text-3); }
.kv dd { margin: 0; color: var(--text); }

/* Activity */
.activity-list { display: flex; flex-direction: column; }
.activity-row { display: flex; gap: 10px; padding: 8px 0; align-items: flex-start; }
.activity-row__body { flex: 1; min-width: 0; }
.activity-row__text { font-size: 12.5px; }
.activity-row__who { font-weight: 500; }
.activity-row__when { font-size: 10.5px; color: var(--text-3); margin-top: 2px; }
.activity-skeleton__row { height: 36px; background: var(--bg-2); border-radius: 4px; margin-bottom: 8px; animation: pulse 1.4s infinite; }
.view-all-btn {
  margin-top: 10px; width: 100%; padding: 6px;
  background: transparent; border: 1px dashed var(--border-2);
  color: var(--text-2); border-radius: 5px; font-size: 11.5px; cursor: pointer;
}

/* Milestones */
.milestones { margin-top: 16px; }
.milestones__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.milestones__rail {
  display: grid; gap: 0; position: relative;
  grid-template-columns: repeat(v-bind("summary?.milestones?.length ?? 7"), 1fr);
}
.milestones__line {
  position: absolute; top: 9px; left: 7%; right: 7%;
  height: 1px; background: var(--border); z-index: 0;
}
.milestones__progress {
  position: absolute; top: 9px; left: 7%;
  height: 1px; background: var(--accent); z-index: 1;
}
.milestone { text-align: center; position: relative; z-index: 2; }
.milestone__dot {
  width: 18px; height: 18px; border-radius: 999px;
  background: var(--panel); border: 1px solid var(--border-2);
  margin: 0 auto; display: flex; align-items: center; justify-content: center;
  color: var(--text-3);
}
.milestone__dot--done { background: var(--accent); border-color: var(--accent); color: #fff; }
.milestone__inner { width: 5px; height: 5px; border-radius: 999px; background: var(--text-3); }
.milestone__label { font-size: 11.5px; margin-top: 8px; color: var(--text-2); }
.milestone__label--done { color: var(--text); }
.milestone__date { font-size: 10.5px; color: var(--text-3); }
</style>
