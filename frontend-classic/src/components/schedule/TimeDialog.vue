<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import Btn from "../Btn.vue";
import Icons from "../Icons.vue";
import Avatar from "../Avatar.vue";
import { frappeList } from "../../composables/useFrappe";

const props = defineProps<{ row: any; projectName: string }>();
const emit  = defineEmits<{ (e: "save", row: any): void; (e: "close"): void }>();

const form = ref({ ...props.row });

// ── Activity picker ────────────────────────────────────────────────────────
const activities  = ref<any[]>([]);
const actGroups   = ref<Record<string, any[]>>({});
const actSearch   = ref(form.value.event_activity || "");
const showActDrop = ref(false);

onMounted(async () => {
  activities.value = await frappeList("Event Activity", {
    fields: ["name", "activity_name", "group"],
    limit: 200,
    order_by: "group asc, activity_name asc",
  });
  for (const a of activities.value) {
    const g = a.group || "Other";
    if (!actGroups.value[g]) actGroups.value[g] = [];
    actGroups.value[g].push(a);
  }
});

function pickAct(a: any) {
  form.value.event_activity = a.activity_name;
  actSearch.value = a.activity_name;
  showActDrop.value = false;
}

// ── Person picker (User search) ────────────────────────────────────────────
const personSearch   = ref(form.value.person || "");
const personResults  = ref<any[]>([]);
const showPersonDrop = ref(false);

async function searchPerson(q: string) {
  if (!q || q.length < 1) {
    personResults.value = await frappeList("User", {
      filters: [["enabled", "=", 1], ["user_type", "=", "System User"]],
      fields: ["name", "full_name"],
      limit: 10,
    }).catch(() => []);
    return;
  }
  personResults.value = await frappeList("User", {
    filters: [["full_name", "like", `%${q}%`], ["enabled", "=", 1], ["user_type", "=", "System User"]],
    fields: ["name", "full_name"],
    limit: 10,
  }).catch(() => []);
}

watch(personSearch, (q) => {
  if (showPersonDrop.value) searchPerson(q);
});

function pickPerson(u: any) {
  form.value.person = u.name;
  personSearch.value = u.full_name || u.name;
  showPersonDrop.value = false;
}

function openPersonDrop() {
  showPersonDrop.value = true;
  searchPerson(personSearch.value);
}

const TAGS = ["", "Ops", "Talent", "Guest", "Program", "Break", "Other"];
</script>

<template>
  <Teleport to="body">
    <div class="overlay" @click.self="emit('close')">
      <div class="dialog">
        <div class="dialog__head">
          <span>{{ form.event_activity ? "Edit Time Slot" : "Add Time Slot" }}</span>
          <button @click="emit('close')"><Icons name="close" :size="14" /></button>
        </div>
        <div class="dialog__body">
          <!-- Activity search -->
          <div class="field" style="position:relative;">
            <label>Event Activity *</label>
            <input
              v-model="actSearch"
              class="ep-input"
              placeholder="Search or type activity…"
              @focus="showActDrop=true; searchAct(actSearch)"
              @input="searchAct(actSearch)"
              @blur="setTimeout(() => showActDrop=false, 200)"
            />
            <div v-if="showActDrop" class="dropdown">
              <div v-for="(items, group) in actGroups" :key="group">
                <template v-if="items.some(a => !actSearch || a.activity_name.toLowerCase().includes(actSearch.toLowerCase()))">
                  <div class="dropdown-group">{{ group }}</div>
                  <button
                    v-for="a in items.filter(a => !actSearch || a.activity_name.toLowerCase().includes(actSearch.toLowerCase()))"
                    :key="a.name"
                    class="dropdown-item"
                    @mousedown="pickAct(a)"
                  >{{ a.activity_name }}</button>
                </template>
              </div>
              <div v-if="!activities.length" class="dropdown-empty">No activities</div>
            </div>
          </div>

          <div class="field-row">
            <div class="field">
              <label>From *</label>
              <input v-model="form.from_datetime" type="datetime-local" class="ep-input" />
            </div>
            <div class="field">
              <label>To *</label>
              <input v-model="form.to_datetime" type="datetime-local" class="ep-input" />
            </div>
          </div>

          <div class="field-row">
            <div class="field" style="position:relative;">
              <label>Person</label>
              <input
                v-model="personSearch"
                class="ep-input"
                placeholder="Search by name…"
                autocomplete="off"
                @focus="openPersonDrop"
                @blur="setTimeout(() => showPersonDrop=false, 200)"
              />
              <button
                v-if="form.person"
                class="person-clear"
                title="Clear"
                @mousedown.prevent="form.person=''; personSearch=''"
              >×</button>
              <div v-if="showPersonDrop" class="dropdown">
                <button
                  v-for="u in personResults" :key="u.name"
                  class="dropdown-item"
                  @mousedown="pickPerson(u)"
                >
                  <Avatar :name="u.name" :size="16" />
                  <span>{{ u.full_name || u.name }}</span>
                  <span class="item-sub">{{ u.name }}</span>
                </button>
                <div v-if="personResults.length === 0" class="dropdown-empty">No users found</div>
              </div>
            </div>
            <div class="field">
              <label>Location</label>
              <input v-model="form.location" class="ep-input" placeholder="e.g. Main stage" />
            </div>
          </div>

          <div class="field-row">
            <div class="field">
              <label>Tag</label>
              <select v-model="form.tag" class="ep-input">
                <option v-for="t in TAGS" :key="t" :value="t">{{ t || "—" }}</option>
              </select>
            </div>
            <div class="field">
              <label>Remark</label>
              <input v-model="form.remark" class="ep-input" placeholder="Optional note" />
            </div>
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
.dialog { background:var(--panel);border-radius:12px;width:540px;border:1px solid var(--border-2);box-shadow:0 24px 64px rgba(0,0,0,.22);display:flex;flex-direction:column; }
.dialog__head { display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border);font-size:13px;font-weight:600; }
.dialog__head button { background:none;border:none;cursor:pointer;color:var(--text-3); }
.dialog__body { padding:18px;display:flex;flex-direction:column;gap:12px; }
.dialog__foot { display:flex;justify-content:flex-end;gap:8px;padding:12px 18px;border-top:1px solid var(--border); }
.field { display:flex;flex-direction:column;gap:4px; }
.field label { font-size:11.5px;color:var(--text-3);font-weight:500; }
.field-row { display:grid;grid-template-columns:1fr 1fr;gap:12px; }
.ep-input { padding:7px 9px;border:1px solid var(--border-2);border-radius:6px;font-size:12.5px;font-family:inherit;background:var(--panel-2);color:var(--text);width:100%; }
.ep-input:focus { outline:none;border-color:var(--accent); }
.dropdown { position:absolute;top:100%;left:0;right:0;background:var(--panel);border:1px solid var(--border-2);border-radius:7px;box-shadow:0 8px 24px rgba(0,0,0,.15);z-index:200;max-height:220px;overflow-y:auto;margin-top:2px;padding:4px; }
.dropdown-group { padding:5px 10px;font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--text-3);background:var(--panel-2);border-radius:4px; }
.dropdown-item { display:flex;align-items:center;gap:8px;width:100%;padding:7px 10px;background:none;border:none;cursor:pointer;font-family:inherit;font-size:12.5px;text-align:left;border-radius:5px; }
.dropdown-item:hover { background:var(--row-hover); }
.dropdown-empty { padding:10px 12px;font-size:12px;color:var(--text-3);text-align:center; }
.item-sub { font-size:11px;color:var(--text-3);margin-left:auto; }
.person-clear { position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--text-3);cursor:pointer;font-size:14px;padding:2px 4px;border-radius:3px; }
.person-clear:hover { color:var(--danger); }
</style>
