<script setup lang="ts">
/**
 * Schedule page — edits Project's 4 child tables via inline cell editing.
 *
 * Inline-editable:   text, number, currency, select, link fields
 * Dialog (⋯ button): datetime-heavy rows (call/wrap times, from/to datetimes)
 *
 * All saves go through updateRow() → debounced saveProject().
 */
import { computed, inject, onMounted, ref, type Ref } from "vue";
import Btn from "../components/Btn.vue";
import Avatar from "../components/Avatar.vue";
import Icons from "../components/Icons.vue";
import InlineCell, { type LinkConf } from "../components/InlineCell.vue";
import TimeDialog from "../components/schedule/TimeDialog.vue";
import EquipDialog from "../components/schedule/EquipDialog.vue";
import CrewDialog from "../components/schedule/CrewDialog.vue";
import VehicleDialog from "../components/schedule/VehicleDialog.vue";
import { frappeGet, frappeSave } from "../composables/useFrappe";

const project     = inject<Ref<any>>("project");
const projectName = inject<Ref<string>>("projectName");

const projectDoc  = ref<any>(null);
const saving      = ref(false);
const loading     = ref(true);
let   saveTimer:   ReturnType<typeof setTimeout> | null = null;

const dialog = ref<{ type: string; row: any; idx: number } | null>(null);

// ── Link field configs ────────────────────────────────────────────────────────

const LC = {
  user: {
    doctype:    "User",
    labelField: "full_name",
    searchField:"full_name",
    filters:    [["enabled", "=", 1], ["user_type", "=", "System User"]],
    showAvatar: true,
  } as LinkConf,

  eventActivity: {
    doctype:    "Event Activity",
    labelField: "activity_name",
    searchField:"activity_name",
  } as LinkConf,

  equipBundle: {
    doctype:    "Equipment Bundle",
    labelField: "bundle_name",
    searchField:"bundle_name",
  } as LinkConf,

  uom: {
    doctype:    "UOM",
    labelField: "name",
  } as LinkConf,

  supplier: {
    doctype:    "Supplier",
    labelField: "supplier_name",
    searchField:"supplier_name",
  } as LinkConf,

  vehicle: {
    doctype:    "Vehicle",
    labelField: "license_plate",
    searchField:"license_plate",
  } as LinkConf,

  // task link is built dynamically (project-scoped) — see computed
};

const taskLinkConf = computed<LinkConf>(() => ({
  doctype:     "Task",
  labelField:  "subject",
  searchField: "subject",
  filters:     [["project", "=", projectName?.value ?? ""]],
}));

// ── Day filter ────────────────────────────────────────────────────────────────

const activeDay = ref(0);

const eventStart = computed(() =>
  project?.value?.expected_start_date ? new Date(project.value.expected_start_date) : null
);

const dayOptions = computed(() => {
  if (!eventStart.value) return [];
  return [0, 1, 2, 3, 4, 5].map((d) => {
    const dt = new Date(eventStart.value!);
    dt.setDate(dt.getDate() + d);
    return {
      idx:   d,
      label: d === 0 ? "All Days" : `Day ${d} · ${dt.toLocaleDateString("en-GB", { day: "numeric", month: "short" })}`,
      date:  dt.toISOString().slice(0, 10),
    };
  });
});

const filteredTimeRows = computed(() => {
  const all = rows("ep_time_schedule");
  if (activeDay.value === 0) return all;
  const dayDate = dayOptions.value.find((d) => d.idx === activeDay.value)?.date;
  return dayDate ? all.filter((r: any) => r.from_datetime?.slice(0, 10) === dayDate) : all;
});

// ── Data ──────────────────────────────────────────────────────────────────────

onMounted(async () => {
  loading.value = true;
  try {
    projectDoc.value = await frappeGet("Project", projectName!.value);
  } catch (e) { console.error(e); }
  finally { loading.value = false; }
});

function rows(key: string): any[] {
  return projectDoc.value?.[key] ?? [];
}

// ── Inline cell update + debounced save ───────────────────────────────────────

function updateRow(tableKey: string, rowIdx: number, field: string, value: any) {
  const list = projectDoc.value?.[tableKey];
  if (!list?.[rowIdx]) return;
  list[rowIdx][field] = value;
  scheduleSave();
}

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(saveProject, 900);
}

async function saveProject() {
  saving.value = true;
  try {
    await frappeSave("Project", projectName!.value, {
      ep_time_schedule:       projectDoc.value.ep_time_schedule,
      ep_equipment_schedule:  projectDoc.value.ep_equipment_schedule,
      ep_crew_schedule:       projectDoc.value.ep_crew_schedule,
      ep_vehicle_schedule:    projectDoc.value.ep_vehicle_schedule,
    });
  } catch (e) { console.error(e); }
  finally { saving.value = false; }
}

// ── Dialog actions ────────────────────────────────────────────────────────────

function openAdd(type: string) {
  dialog.value = { type, row: {}, idx: -1 };
}

function openEdit(type: string, row: any, idx: number) {
  dialog.value = { type, row: { ...row }, idx };
}

function onDialogSave(row: any) {
  if (!dialog.value) return;
  const key = ({
    time:    "ep_time_schedule",
    equip:   "ep_equipment_schedule",
    crew:    "ep_crew_schedule",
    vehicle: "ep_vehicle_schedule",
  } as Record<string, string>)[dialog.value.type];
  if (!projectDoc.value[key]) projectDoc.value[key] = [];
  const list = projectDoc.value[key] as any[];
  if (dialog.value.idx >= 0) list.splice(dialog.value.idx, 1, row);
  else                        list.push(row);
  dialog.value = null;
  saveProject();
}

function deleteRow(key: string, idx: number) {
  projectDoc.value?.[key]?.splice(idx, 1);
  saveProject();
}

// ── Formatting ────────────────────────────────────────────────────────────────

function fmtDt(dt?: string) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString("en-GB", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

// ── Tag / Status colour maps ──────────────────────────────────────────────────

const TAG_OPTIONS  = ["Ops", "Talent", "Guest", "Program", "Break", "Other"];
const TAG_COLORS: Record<string, string> = {
  Ops:     "#6C6E76",
  Talent:  "#A78BFA",
  Guest:   "#3B82F6",
  Program: "#CC785C",
  Break:   "#22C55E",
  Other:   "#8F8A7E",
};

const EQUIP_STATUS_OPTIONS = ["Reserved", "In Transit", "Delivered", "Missing"];
const EQUIP_STATUS_COLORS: Record<string, string> = {
  Reserved:    "#6C6E76",
  "In Transit":"#F59E0B",
  Delivered:   "#22C55E",
  Missing:     "#EF4444",
};
</script>

<template>
  <div class="sched-wrap">

    <!-- ── Page head ─────────────────────────────────────────────────────── -->
    <div class="sched-head">
      <div>
        <h1 class="sched-title">Scheduling</h1>
        <div class="sched-sub">Day-by-day run sheet, equipment manifest, crew & vehicle assignments</div>
      </div>
      <div class="sched-head__right">
        <div v-if="dayOptions.length" class="day-toggle">
          <button
            v-for="d in dayOptions"
            :key="d.idx"
            :class="['day-btn', activeDay === d.idx && 'day-btn--active']"
            @click="activeDay = d.idx"
          >{{ d.label }}</button>
        </div>
        <Btn icon="download">Export Run-of-Show</Btn>
        <span v-if="saving" class="saving-chip">Saving…</span>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner" /> Loading schedule…
    </div>

    <template v-else>

      <!-- ── Time Schedule ─────────────────────────────────────────────────── -->
      <div class="sched-card">
        <div class="sched-card__head">
          <Icons name="clock" :size="14" />
          <span class="sched-card__title">Time Schedule</span>
          <span class="sched-card__sub">{{ filteredTimeRows.length }} slots</span>
          <Btn size="sm" icon="plus" style="margin-left:auto;" @click="openAdd('time')">Add Slot</Btn>
        </div>

        <table class="sched-table">
          <thead>
            <tr>
              <th class="col-activity">Activity</th>
              <th class="col-dt">From</th>
              <th class="col-dt">To</th>
              <th class="col-person">Person</th>
              <th class="col-location">Location</th>
              <th class="col-tag">Tag</th>
              <th class="col-actions"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in filteredTimeRows" :key="i">
              <!-- Activity (link → Event Activity) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.event_activity" type="link" :link-conf="LC.eventActivity"
                  placeholder="Pick activity…"
                  @update="updateRow('ep_time_schedule', i, 'event_activity', $event)"
                />
              </td>
              <!-- From / To — datetime, edit via dialog only -->
              <td class="mono datetime-cell" @click="openEdit('time', r, i)">{{ fmtDt(r.from_datetime) }}</td>
              <td class="mono datetime-cell" @click="openEdit('time', r, i)">{{ fmtDt(r.to_datetime) }}</td>
              <!-- Person (link → User) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.person" type="link" :link-conf="LC.user"
                  placeholder="Assign person…"
                  @update="updateRow('ep_time_schedule', i, 'person', $event)"
                />
              </td>
              <!-- Location (text) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.location" type="text" placeholder="Location…"
                  @update="updateRow('ep_time_schedule', i, 'location', $event)"
                />
              </td>
              <!-- Tag (select + pill) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.tag" type="select"
                  :options="TAG_OPTIONS" :color-map="TAG_COLORS"
                  @update="updateRow('ep_time_schedule', i, 'tag', $event)"
                />
              </td>
              <td class="actions-cell">
                <button class="row-edit" title="Edit all fields" @click="openEdit('time', r, i)">
                  <Icons name="dots" :size="13" />
                </button>
                <button class="row-del" title="Delete" @click="deleteRow('ep_time_schedule', i)">
                  <Icons name="close" :size="11" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <button class="add-row-btn" @click="openAdd('time')">
          <Icons name="plus" :size="12" /> Add time slot
        </button>
      </div>

      <!-- ── Equipment Schedule ────────────────────────────────────────────── -->
      <div class="sched-card">
        <div class="sched-card__head">
          <Icons name="box" :size="14" />
          <span class="sched-card__title">Equipment Schedule</span>
          <span class="sched-card__sub">{{ rows('ep_equipment_schedule').length }} items</span>
          <Btn size="sm" icon="plus" style="margin-left:auto;" @click="openAdd('equip')">Add Equipment</Btn>
        </div>

        <table class="sched-table">
          <thead>
            <tr>
              <th class="col-bundle">Bundle</th>
              <th class="col-qty" style="text-align:right;">Qty</th>
              <th class="col-uom">UOM</th>
              <th class="col-status">Status</th>
              <th class="col-vendor">Vendor</th>
              <th class="col-cost" style="text-align:right;">Cost</th>
              <th class="col-actions"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in rows('ep_equipment_schedule')" :key="i">
              <!-- Bundle (link → Equipment Bundle) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.equipment_bundle" type="link" :link-conf="LC.equipBundle"
                  placeholder="Pick bundle…"
                  @update="updateRow('ep_equipment_schedule', i, 'equipment_bundle', $event)"
                />
              </td>
              <!-- Qty (number) -->
              <td class="ic-td" style="text-align:right;">
                <InlineCell
                  :value="r.quantity" type="number" align="right"
                  placeholder="0"
                  @update="updateRow('ep_equipment_schedule', i, 'quantity', $event)"
                />
              </td>
              <!-- UOM (link → UOM) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.uom" type="link" :link-conf="LC.uom"
                  placeholder="UOM…"
                  @update="updateRow('ep_equipment_schedule', i, 'uom', $event)"
                />
              </td>
              <!-- Status (select + pill) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.status" type="select"
                  :options="EQUIP_STATUS_OPTIONS" :color-map="EQUIP_STATUS_COLORS"
                  @update="updateRow('ep_equipment_schedule', i, 'status', $event)"
                />
              </td>
              <!-- Vendor (link → Supplier) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.vendor" type="link" :link-conf="LC.supplier"
                  placeholder="Supplier…"
                  @update="updateRow('ep_equipment_schedule', i, 'vendor', $event)"
                />
              </td>
              <!-- Cost (currency) -->
              <td class="ic-td" style="text-align:right;">
                <InlineCell
                  :value="r.cost" type="currency" align="right"
                  placeholder="0"
                  @update="updateRow('ep_equipment_schedule', i, 'cost', $event)"
                />
              </td>
              <td class="actions-cell">
                <button class="row-edit" @click="openEdit('equip', r, i)">
                  <Icons name="dots" :size="13" />
                </button>
                <button class="row-del" @click="deleteRow('ep_equipment_schedule', i)">
                  <Icons name="close" :size="11" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <button class="add-row-btn" @click="openAdd('equip')">
          <Icons name="plus" :size="12" /> Add equipment item
        </button>
      </div>

      <!-- ── Crew Schedule ─────────────────────────────────────────────────── -->
      <div class="sched-card">
        <div class="sched-card__head">
          <Icons name="user" :size="14" />
          <span class="sched-card__title">Crew Schedule</span>
          <span class="sched-card__sub">{{ rows('ep_crew_schedule').length }} crew</span>
          <Btn size="sm" icon="plus" style="margin-left:auto;" @click="openAdd('crew')">Add Crew</Btn>
        </div>

        <table class="sched-table">
          <thead>
            <tr>
              <th class="col-role">Role</th>
              <th class="col-person">Name</th>
              <th class="col-vehicle">Vehicle</th>
              <th class="col-task">Task</th>
              <th class="col-dt">Call</th>
              <th class="col-dt">Wrap</th>
              <th class="col-actions"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in rows('ep_crew_schedule')" :key="i">
              <!-- Role (text) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.role" type="text" placeholder="Role…"
                  @update="updateRow('ep_crew_schedule', i, 'role', $event)"
                />
              </td>
              <!-- User (link → User) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.user" type="link" :link-conf="LC.user"
                  placeholder="Team member…"
                  @update="updateRow('ep_crew_schedule', i, 'user', $event)"
                />
              </td>
              <!-- Vehicle (link → Vehicle) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.vehicle" type="link" :link-conf="LC.vehicle"
                  placeholder="Vehicle…"
                  @update="updateRow('ep_crew_schedule', i, 'vehicle', $event)"
                />
              </td>
              <!-- Task (link → Task, project-scoped) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.task" type="link" :link-conf="taskLinkConf"
                  placeholder="Link task…"
                  @update="updateRow('ep_crew_schedule', i, 'task', $event)"
                />
              </td>
              <!-- Call / Wrap — datetime, dialog only -->
              <td class="mono datetime-cell" @click="openEdit('crew', r, i)">{{ fmtDt(r.call_time) }}</td>
              <td class="mono datetime-cell" @click="openEdit('crew', r, i)">{{ fmtDt(r.wrap_time) }}</td>
              <td class="actions-cell">
                <button class="row-edit" @click="openEdit('crew', r, i)">
                  <Icons name="dots" :size="13" />
                </button>
                <button class="row-del" @click="deleteRow('ep_crew_schedule', i)">
                  <Icons name="close" :size="11" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <button class="add-row-btn" @click="openAdd('crew')">
          <Icons name="plus" :size="12" /> Add crew member
        </button>
      </div>

      <!-- ── Vehicle Schedule ──────────────────────────────────────────────── -->
      <div class="sched-card">
        <div class="sched-card__head">
          <Icons name="truck" :size="14" />
          <span class="sched-card__title">Vehicle Schedule</span>
          <span class="sched-card__sub">{{ rows('ep_vehicle_schedule').length }} assignments</span>
          <Btn size="sm" icon="plus" style="margin-left:auto;" @click="openAdd('vehicle')">Add Vehicle</Btn>
        </div>

        <table class="sched-table">
          <thead>
            <tr>
              <th class="col-vehicle">Vehicle</th>
              <th class="col-person">Driver</th>
              <th class="col-task">Task</th>
              <th class="col-dt">From</th>
              <th class="col-dt">To</th>
              <th class="col-remark">Remark</th>
              <th class="col-actions"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in rows('ep_vehicle_schedule')" :key="i">
              <!-- Vehicle (link → Vehicle) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.vehicle" type="link" :link-conf="LC.vehicle"
                  placeholder="Vehicle…"
                  @update="updateRow('ep_vehicle_schedule', i, 'vehicle', $event)"
                />
              </td>
              <!-- Driver (link → User) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.driver" type="link" :link-conf="LC.user"
                  placeholder="Driver…"
                  @update="updateRow('ep_vehicle_schedule', i, 'driver', $event)"
                />
              </td>
              <!-- Task (link → Task) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.task" type="link" :link-conf="taskLinkConf"
                  placeholder="Link task…"
                  @update="updateRow('ep_vehicle_schedule', i, 'task', $event)"
                />
              </td>
              <!-- From / To — datetime, dialog only -->
              <td class="mono datetime-cell" @click="openEdit('vehicle', r, i)">{{ fmtDt(r.from_datetime) }}</td>
              <td class="mono datetime-cell" @click="openEdit('vehicle', r, i)">{{ fmtDt(r.to_datetime) }}</td>
              <!-- Remark (text) -->
              <td class="ic-td">
                <InlineCell
                  :value="r.remark" type="text" placeholder="Note…"
                  @update="updateRow('ep_vehicle_schedule', i, 'remark', $event)"
                />
              </td>
              <td class="actions-cell">
                <button class="row-edit" @click="openEdit('vehicle', r, i)">
                  <Icons name="dots" :size="13" />
                </button>
                <button class="row-del" @click="deleteRow('ep_vehicle_schedule', i)">
                  <Icons name="close" :size="11" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <button class="add-row-btn" @click="openAdd('vehicle')">
          <Icons name="plus" :size="12" /> Add vehicle assignment
        </button>
      </div>
    </template>

    <!-- ── Dialogs ────────────────────────────────────────────────────────── -->
    <TimeDialog
      v-if="dialog?.type === 'time'"
      :row="dialog.row" :project-name="projectName ?? ''"
      @save="onDialogSave" @close="dialog = null"
    />
    <EquipDialog
      v-if="dialog?.type === 'equip'"
      :row="dialog.row"
      @save="onDialogSave" @close="dialog = null"
    />
    <CrewDialog
      v-if="dialog?.type === 'crew'"
      :row="dialog.row" :project-name="projectName ?? ''"
      @save="onDialogSave" @close="dialog = null"
    />
    <VehicleDialog
      v-if="dialog?.type === 'vehicle'"
      :row="dialog.row" :project-name="projectName ?? ''"
      @save="onDialogSave" @close="dialog = null"
    />
  </div>
</template>

<style scoped>
.sched-wrap { padding: 20px 24px 60px; width: 100%; flex: 1; }
.sched-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.sched-title { font-size: 18px; font-weight: 600; letter-spacing: -.01em; margin: 0; }
.sched-sub   { font-size: 12px; color: var(--text-3); margin-top: 2px; }
.sched-head__right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.day-toggle { display: inline-flex; padding: 2px; background: var(--panel); border: 1px solid var(--border); border-radius: 6px; }
.day-btn { padding: 4px 10px; font-size: 11.5px; border-radius: 4px; background: transparent; border: 1px solid transparent; color: var(--text-3); cursor: pointer; font-family: inherit; transition: all 100ms; }
.day-btn--active { background: var(--panel-2); border-color: var(--border-2); color: var(--text); }
.saving-chip { font-size: 11px; color: var(--accent); padding: 4px 8px; border: 1px solid var(--accent-soft); border-radius: 4px; animation: pulse 1s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.6; } }

.loading-state { display: flex; align-items: center; gap: 8px; color: var(--text-3); font-size: 13px; padding: 40px; }
.spinner { width: 16px; height: 16px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Card ────────────────────────────────────────────────────────────────── */
.sched-card { border: 1px solid var(--border); border-radius: 8px; overflow: visible; background: var(--panel); margin-bottom: 16px; }
.sched-card__head {
  padding: 10px 14px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 8px; background: var(--panel-2);
  border-radius: 8px 8px 0 0;
}
.sched-card__title { font-size: 13px; font-weight: 600; }
.sched-card__sub   { color: var(--text-3); font-size: 11.5px; }

/* ── Table ───────────────────────────────────────────────────────────────── */
.sched-table { width: 100%; border-collapse: collapse; font-size: 12.5px; table-layout: fixed; }
.sched-table th {
  padding: 6px 12px; text-align: left; font-size: 10.5px;
  text-transform: uppercase; letter-spacing: .1em; color: var(--text-3);
  font-weight: 500; border-bottom: 1px solid var(--border); background: var(--panel-2);
  white-space: nowrap; overflow: hidden;
}
.sched-table td { padding: 0; border-bottom: 1px solid var(--border); vertical-align: middle; }
.sched-table tr:last-child td { border-bottom: none; }
.sched-table tr:hover td { background: var(--row-hover); }

/* ic-td: the cell provides padding via InlineCell, so td has none */
.ic-td { padding: 0 !important; }

/* Datetime cells - read-only looking but clickable hint */
.datetime-cell {
  padding: 7px 12px !important;
  cursor: pointer;
  font-size: 12px;
  color: var(--text-2);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  transition: background 100ms;
}
.datetime-cell:hover { background: var(--row-hover) !important; }
.datetime-cell:hover::after {
  content: " ✎";
  font-size: 9px;
  color: var(--text-3);
  font-family: var(--font-sans);
}

/* Actions column */
.actions-cell { padding: 0 8px !important; width: 56px; text-align: right; white-space: nowrap; }
.row-edit, .row-del {
  background: none; border: none; cursor: pointer; color: var(--text-3);
  padding: 4px; border-radius: 3px; display: inline-flex;
  transition: background 100ms, color 100ms;
}
.row-edit:hover { background: var(--border); color: var(--text); }
.row-del:hover  { background: rgba(194,65,12,.10); color: var(--danger); }

/* Column widths */
.col-activity { width: 18%; }
.col-dt       { width: 11%; }
.col-person   { width: 14%; }
.col-location { width: 16%; }
.col-tag      { width: 9%; }
.col-bundle   { width: 20%; }
.col-qty      { width: 7%; }
.col-uom      { width: 9%; }
.col-status   { width: 10%; }
.col-vendor   { width: 16%; }
.col-cost     { width: 10%; }
.col-role     { width: 14%; }
.col-vehicle  { width: 13%; }
.col-task     { width: 18%; }
.col-remark   { width: 20%; }
.col-actions  { width: 56px; }

.add-row-btn {
  padding: 8px 14px; color: var(--text-3); font-size: 11.5px;
  cursor: pointer; display: flex; align-items: center; gap: 6px;
  background: transparent; border: none; font-family: inherit;
  border-top: 1px dashed var(--border); width: 100%; text-align: left;
  transition: background 100ms, color 100ms;
}
.add-row-btn:hover { background: var(--row-hover); color: var(--text); }

/* ── Mobile responsive ─────────────────────────────────────────────────────── */
@media (max-width: 1023px) {
  /* Tables scroll horizontally on tablet */
  .schedule-table-wrap { overflow-x: auto; }
}

@media (max-width: 767px) {
  .schedule-wrap { padding: 10px 8px 60px; }

  /* Card list instead of table on mobile */
  .schedule-section { margin-bottom: 16px; }
  .section-title { font-size: 11px; padding: 8px 8px 6px; }

  /* Hide table headers */
  thead { display: none; }

  /* Each row becomes a card */
  tbody tr {
    display: flex; flex-direction: column; gap: 4px;
    border: 1px solid var(--border); border-radius: 8px;
    margin: 4px 2px; padding: 10px 12px;
    background: var(--panel); box-shadow: 0 1px 3px rgba(26,25,21,.04);
  }
  tbody tr + tr { margin-top: 6px; }
  tbody td { border: none !important; padding: 0 !important; }
  tbody td::before {
    content: attr(data-label);
    font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: .07em; color: var(--text-3); display: block; margin-bottom: 2px;
  }
  tbody td:first-child { display: none; }  /* Hide row number on mobile */

  /* Small tap targets OK */
  .schedule-add-btn { width: 100%; justify-content: center; margin-top: 6px; }
}
</style>
