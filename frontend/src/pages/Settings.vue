<template>
  <div class="h-full overflow-y-auto">
    <header class="flex h-12 items-center gap-2 border-b border-outline-gray-1 px-4">
      <span class="lucide-settings size-4 text-ink-gray-5" />
      <h1 class="text-base font-semibold text-ink-gray-9">Settings</h1>
      <span class="text-sm text-ink-gray-5">States and views belong to the project type; types and properties are shared by all projects.</span>
    </header>
    <div class="mx-auto flex max-w-4xl flex-col gap-8 p-6">
      <!-- project key -->
      <section>
        <h2 class="title">Project</h2>
        <div class="flex items-end gap-2">
          <FormControl v-model="key" label="Work item key" class="w-40" placeholder="EVT" />
          <Button label="Save key" @click="saveKey" />
          <span class="pb-1.5 text-sm text-ink-gray-5">Items show as {{ key || 'KEY' }}-12.</span>
        </div>
      </section>

      <!-- states -->
      <section>
        <h2 class="title">States of {{ type || 'this project' }}</h2>
        <div v-if="!type" class="rounded border border-outline-amber-2 bg-surface-amber-1 p-3 text-sm text-ink-amber-4">
          This project has no Project Type, so it uses the ERPNext task statuses. Set a Project Type on the project in desk to use your own states.
        </div>
        <template v-else>
          <div v-for="group in STATE_GROUPS" :key="group" class="mb-3">
            <div class="mb-1 flex items-center gap-2 text-sm text-ink-gray-6">
              <StateIcon :state="{ state_group: group, color: '#6B7280' }" /> {{ group }}
              <Button size="sm" variant="ghost" icon="lucide-plus" @click="addState(group)" />
            </div>
            <div v-for="(s, i) in statesIn(group)" :key="s.name" class="row">
              <div class="flex flex-col">
                <button class="lucide-chevron-up size-3.5 text-ink-gray-4 hover:text-ink-gray-8 disabled:opacity-30" :disabled="i === 0" title="Move up" @click="moveState(group, i, -1)" />
                <button class="lucide-chevron-down size-3.5 text-ink-gray-4 hover:text-ink-gray-8 disabled:opacity-30" :disabled="i === statesIn(group).length - 1" title="Move down" @click="moveState(group, i, 1)" />
              </div>
              <StateIcon :state="s" />
              <input v-model="s.title" class="h-7 flex-1 rounded border-0 bg-transparent px-1 text-sm focus:bg-surface-gray-2 focus:ring-0" @change="saveState(s, 'title', s.title)" />
              <ColorPicker :model-value="s.color" :label="s.title" icon="lucide-circle-dot" @change="(c) => saveState(s, 'color', (s.color = c))" />
              <label v-if="group === 'Started'" class="flex items-center gap-1 text-xs text-ink-gray-6">
                <Checkbox :model-value="Boolean(s.is_review)" @update:model-value="(v) => saveState(s, 'is_review', v ? 1 : 0)" /> review
              </label>
              <label class="flex items-center gap-1 text-xs text-ink-gray-6">
                <Checkbox :model-value="Boolean(s.is_default)" @update:model-value="(v) => saveState(s, 'is_default', v ? 1 : 0)" /> default
              </label>
              <Button size="sm" variant="ghost" icon="lucide-trash-2" @click="removeDoc('Planner State', s.name)" />
            </div>
          </div>
        </template>
      </section>

      <!-- groups of this project -->
      <section>
        <h2 class="title">Categories in this project</h2>
        <p class="mb-2 text-sm text-ink-gray-5">
          Categories sort work items by area (Pre-production, Logistics, Creative…). Each item is in one. You can also create one from an item's Category field, and rename,
          recolour or delete one from its header when Work items are grouped by Category.
        </p>
        <div v-for="grp in ctx.groups" :key="grp.name" class="row mb-1">
          <ColorPicker :model-value="grp.color" :label="grp.title" @change="(color) => updateCategory(grp.name, { color })" />
          <input
            :value="grp.title"
            class="h-7 flex-1 rounded-md border-0 bg-transparent px-1 text-sm focus:bg-surface-gray-2 focus:ring-0"
            @change="(e) => e.target.value.trim() && updateCategory(grp.name, { title: e.target.value.trim() })"
          />
          <Button size="sm" variant="ghost" icon="lucide-trash-2" @click="deleteCategory(grp.name)" />
        </div>
        <div class="mt-2 flex items-center gap-2">
          <TextInput v-model="newGroup" placeholder="New category, e.g. Pre-production" class="w-64" @keydown.enter="addGroup" />
          <Button label="Add category" :disabled="!newGroup" @click="addGroup" />
        </div>
      </section>

      <!-- types -->
      <section>
        <h2 class="title">Work item types</h2>
        <div v-for="t in types" :key="t.name" class="row mb-1">
          <Picker :model-value="t.ep_icon" :options="iconOptions" label="Icon" @change="(v) => saveType(t, 'ep_icon', v)">
            <template #default="{ toggle }">
              <button class="flex size-7 items-center justify-center rounded hover:bg-surface-gray-2" @click="toggle">
                <span :class="t.ep_icon || 'lucide-square-check'" class="size-4" :style="{ color: t.ep_color }" />
              </button>
            </template>
          </Picker>
          <span class="flex-1 text-sm">{{ t.name }}</span>
          <ColorPicker :model-value="t.ep_color" :label="t.name" :icon="t.ep_icon || 'lucide-square-check'" clearable @change="(c) => saveType(t, 'ep_color', c)" />
          <span class="text-xs text-ink-gray-5">{{ propsOf(t.name).length }} properties</span>
        </div>
        <div class="mt-2 flex items-center gap-2">
          <TextInput v-model="newType" placeholder="New type, e.g. Site Visit" class="w-64" @keydown.enter="addType" />
          <Button label="Add type" :disabled="!newType" @click="addType" />
        </div>
      </section>

      <!-- properties -->
      <section>
        <h2 class="title">Properties per type</h2>
        <p class="mb-2 text-sm text-ink-gray-5">Each property becomes a real field on Task, so it can be filtered, grouped and reported in desk too.</p>
        <div v-for="p in properties" :key="p.name" class="row mb-1 text-sm">
          <span class="w-36 text-ink-gray-6">{{ p.task_type }}</span>
          <span class="flex-1">{{ p.label }}<span v-if="p.is_required" class="text-ink-red-4">*</span></span>
          <Badge :label="p.property_type" size="sm" />
          <span class="w-40 truncate text-xs text-ink-gray-4">{{ p.fieldname }}</span>
          <Button size="sm" variant="ghost" icon="lucide-trash-2" @click="removeDoc('Planner Property', p.name)" />
        </div>
        <div class="mt-2 grid grid-cols-6 items-end gap-2">
          <FormControl v-model="prop.task_type" type="select" label="Type" :options="types.map((t) => t.name)" class="col-span-2" />
          <FormControl v-model="prop.label" label="Label" class="col-span-2" />
          <FormControl v-model="prop.property_type" type="select" label="Kind" :options="PROPERTY_TYPES" />
          <Button label="Add" :disabled="!prop.task_type || !prop.label" @click="addProperty" />
          <FormControl v-if="prop.property_type === 'Dropdown'" v-model="prop.options" type="textarea" label="Options, one per line" class="col-span-4" />
          <FormControl v-model="prop.is_required" type="checkbox" label="Required to complete" class="col-span-2" />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Badge, Button, Checkbox, FormControl, TextInput, toast } from 'frappe-ui'
import ColorPicker from '../components/ColorPicker.vue'
import Picker from '../components/Picker.vue'
import StateIcon from '../components/StateIcon.vue'
import { api } from '../api'
import { createCategory, ctx, deleteCategory, fail, loadProject, updateCategory } from '../store'
import { confirmAction } from '../confirm'
import { COLORS, STATE_GROUPS, TYPE_ICONS } from '../utils'

const PROPERTY_TYPES = ['Text', 'Number', 'Dropdown', 'Date', 'Member', 'Checkbox', 'URL']
const type = computed(() => ctx.project.project_type)
const key = ref(ctx.project.key || '')
const states = ref([])
const types = ref([])
const properties = ref([])
const newType = ref('')
const prop = reactive({ task_type: '', label: '', property_type: 'Text', options: '', is_required: false })
const iconOptions = TYPE_ICONS.map((icon) => ({ value: icon, label: icon.replace('lucide-', ''), iconClass: icon }))

async function load() {
  try {
    const [s, t, p] = await Promise.all([
      type.value
        ? api.list('Planner State', ['name', 'title', 'state_group', 'color', 'is_default', 'is_review', 'sort_order'], { project_type: type.value }, 'sort_order asc')
        : [],
      api.list('Task Type', ['name', 'ep_icon', 'ep_color', 'ep_is_default'], {}, 'name asc'),
      api.list('Planner Property', ['name', 'label', 'task_type', 'property_type', 'is_required', 'fieldname'], {}, 'task_type asc, sort_order asc'),
    ])
    states.value = s
    types.value = t
    properties.value = p
  } catch (err) {
    fail(err)
  }
}
onMounted(load)

const statesIn = (group) => states.value.filter((s) => s.state_group === group)
const propsOf = (t) => properties.value.filter((p) => p.task_type === t)

async function refresh() {
  await Promise.all([load(), loadProject(ctx.project.name)])
}

async function saveKey() {
  try {
    await api.setValue('Project', ctx.project.name, 'ep_key', key.value.trim().toUpperCase())
    await refresh()
    toast.success('Key saved')
  } catch (err) {
    fail(err)
  }
}

async function addState(group) {
  try {
    await api.insert({ doctype: 'Planner State', project_type: type.value, state_group: group, title: 'New state', color: '#6B7280', sort_order: states.value.length })
    await refresh()
  } catch (err) {
    fail(err)
  }
}

async function saveState(s, field, value) {
  try {
    await api.setValue('Planner State', s.name, field, value)
    await refresh()
  } catch (err) {
    fail(err)
    load()
  }
}

/** Swap a state with its neighbour in the same group, then renumber the whole board order. */
async function moveState(group, index, step) {
  const list = statesIn(group)
  const other = list[index + step]
  if (!other) return
  const ordered = [...states.value]
  const a = ordered.indexOf(list[index])
  const b = ordered.indexOf(other)
  ;[ordered[a], ordered[b]] = [ordered[b], ordered[a]]
  try {
    await Promise.all(ordered.map((s, i) => (s.sort_order !== i ? api.setValue('Planner State', s.name, 'sort_order', i) : null)))
    await refresh()
  } catch (err) {
    fail(err)
  }
}

const newGroup = ref('')
async function addGroup() {
  if (newGroup.value.trim() && (await createCategory(newGroup.value))) newGroup.value = ''
}

async function saveType(t, field, value) {
  try {
    await api.setValue('Task Type', t.name, field, value)
    await refresh()
  } catch (err) {
    fail(err)
  }
}

async function addType() {
  try {
    await api.insert({ doctype: 'Task Type', name: newType.value.trim(), __newname: newType.value.trim(), ep_icon: 'lucide-square-check' })
    newType.value = ''
    await refresh()
  } catch (err) {
    fail(err)
  }
}

async function addProperty() {
  try {
    await api.insert({ doctype: 'Planner Property', ...prop, is_required: prop.is_required ? 1 : 0 })
    Object.assign(prop, { label: '', options: '', is_required: false })
    await refresh()
  } catch (err) {
    fail(err)
  }
}

async function removeDoc(doctype, name) {
  const what = { 'Planner State': 'state', 'Planner Property': 'property' }[doctype] || doctype
  const ok = await confirmAction({
    title: `Delete this ${what}?`,
    message: `It is shared: every project that uses it loses it. This cannot be undone.`,
    action: 'Delete',
    danger: true,
  })
  if (!ok) return
  try {
    await api.remove(doctype, name)
    await refresh()
  } catch (err) {
    fail(err)
  }
}
</script>

<style scoped>
.title {
  @apply mb-3 text-sm font-semibold text-ink-gray-8;
}
.ctl {
  @apply h-7 rounded-md border-0 bg-surface-gray-2 px-2 py-0 text-sm text-ink-gray-8 focus:ring-0;
}
.row {
  @apply flex items-center gap-2 rounded-xl border border-outline-gray-1 px-3 py-1.5;
}
</style>
