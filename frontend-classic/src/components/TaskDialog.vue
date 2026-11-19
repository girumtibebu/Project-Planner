<script setup lang="ts">
import { ref, watch } from "vue";
import Btn from "./Btn.vue";
import Icons from "./Icons.vue";
import { frappeList } from "../composables/useFrappe";
import { assigneeFromTask } from "../utils/assignment";

const props = defineProps<{
  task: any;
  projectName: string;
  categories: any[];
}>();

const emit = defineEmits<{
  (e: "save", task: any): void;
  (e: "close"): void;
}>();

const form = ref<any>({});

// User search (declared before task watch — immediate handler reads userSearch)
const userSearch = ref("");
const userResults = ref<any[]>([]);
const showUserDrop = ref(false);

watch(
  () => props.task,
  (t) => {
    form.value = {
      ...(t || {}),
      assignee: assigneeFromTask(t?._assign),
    };
    userSearch.value = form.value.assignee || "";
  },
  { immediate: true }
);

async function searchUsers(q: string) {
  if (!q || q.length < 2) { userResults.value = []; return; }
  userResults.value = await frappeList("User", {
    filters: [["full_name", "like", `%${q}%`], ["enabled", "=", 1]],
    fields: ["name", "full_name", "user_image"],
    limit: 10,
  });
}

watch(userSearch, searchUsers);

function pickUser(u: any) {
  form.value.assignee = u.name;
  userSearch.value = u.full_name || u.name;
  showUserDrop.value = false;
}

// Sub-tasks
const newSub = ref("");
const subtasks = ref<string[]>([]);
function addSub() {
  if (newSub.value.trim()) {
    subtasks.value.push(newSub.value.trim());
    newSub.value = "";
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="overlay" @click.self="emit('close')">
      <div class="dialog">
        <!-- Header -->
        <div class="dialog__head">
          <span class="dialog__title">{{ form.name ? "Edit Task" : "New Task" }}</span>
          <button @click="emit('close')"><Icons name="close" :size="15" /></button>
        </div>

        <div class="dialog__body">
          <!-- Title -->
          <div class="field">
            <label>Task Title <span class="req">*</span></label>
            <input
              v-model="form.subject"
              class="ep-input"
              placeholder="e.g. Set up main stage AV"
              autofocus
            />
          </div>

          <div class="field-row">
            <!-- Category -->
            <div class="field">
              <label>Action Category</label>
              <select v-model="form.ep_action_category" class="ep-input">
                <option value="">— None —</option>
                <option v-for="c in categories" :key="c.name" :value="c.name">{{ c.title }}</option>
              </select>
            </div>

            <!-- Priority -->
            <div class="field">
              <label>Priority</label>
              <select v-model="form.priority" class="ep-input">
                <option value="">—</option>
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Urgent">Urgent</option>
              </select>
            </div>
          </div>

          <div class="field-row">
            <!-- Start date -->
            <div class="field">
              <label>Start Date</label>
              <input v-model="form.exp_start_date" type="date" class="ep-input" />
            </div>
            <!-- End date -->
            <div class="field">
              <label>End Date</label>
              <input v-model="form.exp_end_date" type="date" class="ep-input" />
            </div>
          </div>

          <!-- Assignee -->
          <div class="field" style="position:relative;">
            <label>Assigned To</label>
            <input
              v-model="userSearch"
              class="ep-input"
              placeholder="Search by name…"
              @focus="showUserDrop = true"
              @blur="setTimeout(() => showUserDrop = false, 200)"
            />
            <div v-if="showUserDrop && userResults.length" class="user-drop">
              <button
                v-for="u in userResults"
                :key="u.name"
                class="user-drop__item"
                @mousedown="pickUser(u)"
              >
                <span>{{ u.full_name || u.name }}</span>
                <span class="user-drop__email">{{ u.name }}</span>
              </button>
            </div>
          </div>

          <!-- Description -->
          <div class="field">
            <label>Description</label>
            <textarea
              v-model="form.description"
              class="ep-input"
              rows="4"
              placeholder="Add context, links, or notes…"
            />
          </div>

          <!-- Sub-tasks (informational in v1) -->
          <div class="field">
            <label>Sub-tasks</label>
            <div class="subtask-list">
              <div v-for="(s, i) in subtasks" :key="i" class="subtask-item">
                <span class="subtask-dot">·</span>
                <span>{{ s }}</span>
                <button @click="subtasks.splice(i,1)" class="subtask-rm">
                  <Icons name="close" :size="10" />
                </button>
              </div>
            </div>
            <div class="subtask-add">
              <input
                v-model="newSub"
                class="ep-input"
                placeholder="Add sub-task…"
                @keydown.enter.prevent="addSub"
              />
              <Btn size="sm" icon="plus" @click="addSub">Add</Btn>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="dialog__foot">
          <Btn @click="emit('close')">Cancel</Btn>
          <Btn kind="primary" @click="emit('save', form)">
            {{ form.name ? "Save Changes" : "Create Task" }}
          </Btn>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.4);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.dialog {
  background: var(--panel); border-radius: 12px; width: 560px; max-height: 88vh;
  display: flex; flex-direction: column;
  border: 1px solid var(--border-2); box-shadow: 0 24px 64px rgba(0,0,0,.22);
}
.dialog__head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; border-bottom: 1px solid var(--border);
}
.dialog__title { font-size: 14px; font-weight: 600; }
.dialog__head button { background: none; border: none; cursor: pointer; color: var(--text-3); }
.dialog__body { padding: 18px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 14px; }
.dialog__foot { display: flex; justify-content: flex-end; gap: 8px; padding: 12px 18px; border-top: 1px solid var(--border); }

.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-size: 11.5px; color: var(--text-3); font-weight: 500; }
.req { color: var(--danger); }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.ep-input {
  padding: 7px 9px; border: 1px solid var(--border-2); border-radius: 6px;
  font-size: 12.5px; font-family: inherit; background: var(--panel-2); color: var(--text);
  width: 100%;
}
.ep-input:focus { outline: none; border-color: var(--accent); }
textarea.ep-input { resize: vertical; }

.user-drop {
  position: absolute; top: 100%; left: 0; right: 0;
  background: var(--panel); border: 1px solid var(--border-2);
  border-radius: 7px; box-shadow: 0 8px 24px rgba(0,0,0,.15);
  z-index: 10; overflow: hidden; margin-top: 2px;
}
.user-drop__item {
  display: flex; flex-direction: column; padding: 8px 12px;
  cursor: pointer; background: none; border: none; width: 100%; text-align: left;
  font-family: inherit; font-size: 12.5px;
}
.user-drop__item:hover { background: var(--row-hover); }
.user-drop__email { font-size: 11px; color: var(--text-3); margin-top: 1px; }

.subtask-list { display: flex; flex-direction: column; gap: 4px; margin-bottom: 6px; }
.subtask-item { display: flex; align-items: center; gap: 8px; font-size: 12.5px; }
.subtask-dot { color: var(--text-3); }
.subtask-rm { background: none; border: none; cursor: pointer; color: var(--text-3); margin-left: auto; }
.subtask-add { display: flex; gap: 6px; align-items: center; }
.subtask-add .ep-input { flex: 1; }
</style>
