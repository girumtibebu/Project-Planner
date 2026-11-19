<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import Btn from "../Btn.vue";
import Icons from "../Icons.vue";
import Avatar from "../Avatar.vue";
import { frappeList } from "../../composables/useFrappe";

const props = defineProps<{ row: any; projectName: string }>();
const emit  = defineEmits<{ (e: "save", row: any): void; (e: "close"): void }>();

const form = ref({ ...props.row });

// User search
const userSearch  = ref(form.value.user || "");
const userResults = ref<any[]>([]);
const showUserDrop = ref(false);

// Role suggestions (distinct roles on existing crew)
const roleSuggestions = ref<string[]>([
  "Stage Manager", "Lead A2 — Audio", "Lighting Designer",
  "Artist Liaison", "Runner", "Registration Lead", "Director of Photography",
  "Live Stream Tech",
]);

// Vehicle search
const vehicles = ref<any[]>([]);
const vehicleSearch = ref(form.value.vehicle || "");
const showVehDrop = ref(false);

// Task search
const projectTasks = ref<any[]>([]);
const taskSearch = ref(form.value.task || "");
const showTaskDrop = ref(false);

onMounted(async () => {
  vehicles.value = await frappeList("Vehicle", {
    fields: ["name", "license_plate", "make", "model"],
    limit: 100,
  });
  projectTasks.value = await frappeList("Task", {
    filters: { project: props.projectName },
    fields: ["name", "subject"],
    limit: 200,
  });
});

async function searchUsers(q: string) {
  if (!q || q.length < 2) { userResults.value = []; return; }
  userResults.value = await frappeList("User", {
    filters: [["full_name", "like", `%${q}%`], ["enabled", "=", 1]],
    fields: ["name", "full_name"],
    limit: 10,
  });
}
watch(userSearch, searchUsers);

function pickUser(u: any) {
  form.value.user = u.name;
  userSearch.value = u.full_name || u.name;
  showUserDrop.value = false;
}
function pickVehicle(v: any) {
  form.value.vehicle = v.name;
  vehicleSearch.value = v.license_plate || v.name;
  showVehDrop.value = false;
}
function pickTask(t: any) {
  form.value.task = t.name;
  taskSearch.value = t.subject;
  showTaskDrop.value = false;
}

const filteredVehicles = ref<any[]>([]);
function searchVehicle(q: string) {
  filteredVehicles.value = !q
    ? vehicles.value
    : vehicles.value.filter((v) =>
        (v.name + " " + (v.license_plate || "")).toLowerCase().includes(q.toLowerCase())
      );
}
const filteredTasks = ref<any[]>([]);
function searchTask(q: string) {
  filteredTasks.value = !q
    ? projectTasks.value
    : projectTasks.value.filter((t) =>
        t.subject.toLowerCase().includes(q.toLowerCase())
      );
}
</script>

<template>
  <Teleport to="body">
    <div class="overlay" @click.self="emit('close')">
      <div class="dialog">
        <div class="dialog__head">
          <span>{{ form.user ? "Edit Crew" : "Add Crew Member" }}</span>
          <button @click="emit('close')"><Icons name="close" :size="14" /></button>
        </div>
        <div class="dialog__body">
          <!-- Role -->
          <div class="field">
            <label>Role *</label>
            <input v-model="form.role" class="ep-input" placeholder="e.g. Stage Manager" list="role-suggestions" />
            <datalist id="role-suggestions">
              <option v-for="s in roleSuggestions" :key="s" :value="s" />
            </datalist>
          </div>

          <!-- User -->
          <div class="field" style="position:relative;">
            <label>Team Member</label>
            <input
              v-model="userSearch"
              class="ep-input"
              placeholder="Search by name…"
              @focus="showUserDrop=true"
              @blur="setTimeout(()=>showUserDrop=false,200)"
            />
            <div v-if="showUserDrop && userResults.length" class="dropdown">
              <button v-for="u in userResults" :key="u.name" class="dropdown-item" @mousedown="pickUser(u)">
                <span>{{ u.full_name || u.name }}</span>
                <span class="item-sub">{{ u.name }}</span>
              </button>
            </div>
          </div>

          <!-- Vehicle -->
          <div class="field" style="position:relative;">
            <label>Vehicle (optional)</label>
            <input
              v-model="vehicleSearch"
              class="ep-input"
              placeholder="Search vehicle…"
              @focus="showVehDrop=true;searchVehicle(vehicleSearch)"
              @input="searchVehicle(vehicleSearch)"
              @blur="setTimeout(()=>showVehDrop=false,200)"
            />
            <div v-if="showVehDrop" class="dropdown">
              <button v-for="v in filteredVehicles" :key="v.name" class="dropdown-item" @mousedown="pickVehicle(v)">
                {{ v.license_plate || v.name }}
              </button>
            </div>
          </div>

          <!-- Task -->
          <div class="field" style="position:relative;">
            <label>Task (optional)</label>
            <input
              v-model="taskSearch"
              class="ep-input"
              placeholder="Link to a task…"
              @focus="showTaskDrop=true;searchTask(taskSearch)"
              @input="searchTask(taskSearch)"
              @blur="setTimeout(()=>showTaskDrop=false,200)"
            />
            <div v-if="showTaskDrop" class="dropdown">
              <button v-for="t in filteredTasks" :key="t.name" class="dropdown-item" @mousedown="pickTask(t)">
                {{ t.subject }}
              </button>
            </div>
          </div>

          <div class="field-row">
            <div class="field">
              <label>Call Time</label>
              <input v-model="form.call_time" type="datetime-local" class="ep-input" />
            </div>
            <div class="field">
              <label>Wrap Time</label>
              <input v-model="form.wrap_time" type="datetime-local" class="ep-input" />
            </div>
          </div>

          <div class="field">
            <label>Remark</label>
            <input v-model="form.remark" class="ep-input" placeholder="Optional note" />
          </div>
        </div>
        <div class="dialog__foot">
          <Btn @click="emit('close')">Cancel</Btn>
          <Btn kind="primary" @click="emit('save', form)">Save</Btn>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay { position:fixed;inset:0;background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;z-index:100; }
.dialog { background:var(--panel);border-radius:12px;width:520px;border:1px solid var(--border-2);box-shadow:0 24px 64px rgba(0,0,0,.22);display:flex;flex-direction:column;max-height:88vh; }
.dialog__head { display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border);font-size:13px;font-weight:600; }
.dialog__head button { background:none;border:none;cursor:pointer;color:var(--text-3); }
.dialog__body { padding:18px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:12px; }
.dialog__foot { display:flex;justify-content:flex-end;gap:8px;padding:12px 18px;border-top:1px solid var(--border); }
.field { display:flex;flex-direction:column;gap:4px; }
.field label { font-size:11.5px;color:var(--text-3);font-weight:500; }
.field-row { display:grid;grid-template-columns:1fr 1fr;gap:12px; }
.ep-input { padding:7px 9px;border:1px solid var(--border-2);border-radius:6px;font-size:12.5px;font-family:inherit;background:var(--panel-2);color:var(--text);width:100%; }
.ep-input:focus { outline:none;border-color:var(--accent); }
.dropdown { position:absolute;top:100%;left:0;right:0;background:var(--panel);border:1px solid var(--border-2);border-radius:7px;box-shadow:0 8px 24px rgba(0,0,0,.15);z-index:10;max-height:200px;overflow-y:auto;margin-top:2px; }
.dropdown-item { display:flex;flex-direction:column;width:100%;padding:8px 12px;background:none;border:none;cursor:pointer;font-family:inherit;font-size:12.5px;text-align:left; }
.dropdown-item:hover { background:var(--row-hover); }
.item-sub { font-size:11px;color:var(--text-3); }
</style>
