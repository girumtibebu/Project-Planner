<template>
  <div class="flex h-full min-h-0">
    <div class="flex min-w-0 flex-1 flex-col">
      <!-- header -->
      <header class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-4">
        <span :class="LAYOUT_ICON[config.layout]" class="size-4 text-ink-gray-5" />
        <h1 class="truncate text-base font-semibold text-ink-gray-9">{{ view?.title || 'Work items' }}</h1>
        <Badge v-if="view?.project_type" label="Shared view" theme="blue" size="sm" />
        <Badge v-if="view?.is_locked" label="Locked" theme="gray" size="sm" />
        <Badge v-if="dirty" label="Unsaved" theme="orange" size="sm" />
        <div class="ml-4 hidden md:block">
          <TabButtons v-model="config.layout" :buttons="LAYOUTS" />
        </div>
        <div class="ml-auto flex items-center gap-2">
          <TextInput v-model="search" size="sm" placeholder="Search title or ID" class="hidden w-48 lg:block">
            <template #prefix><span class="lucide-search size-3.5 text-ink-gray-4" /></template>
          </TextInput>
          <FilterMenu v-model="config.filters" />
          <CategoryManager :items="items" @group-by="config.group_by = 'group'" />
          <Popover align="end">
            <template #trigger>
              <Button size="sm" icon-left="lucide-sliders-horizontal" label="Display" />
            </template>
            <template #default>
              <div class="flex w-72 flex-col gap-3 p-3 text-sm">
                <label v-if="config.layout !== 'Calendar'" class="flex items-center justify-between gap-2">
                  {{ { Kanban: 'Columns', Gantt: 'Lanes' }[config.layout] || 'Group by' }}
                  <select v-model="config.group_by" class="ctl">
                    <option v-for="g in groupOptions" :key="g.value" :value="g.value">{{ g.label }}</option>
                  </select>
                </label>
                <template v-if="config.layout === 'Kanban'">
                  <label class="flex items-center justify-between gap-2">
                    Swimlanes
                    <select v-model="config.display.swimlanes" class="ctl">
                      <option v-for="g in GROUP_BY" :key="g.value" :value="g.value">{{ g.label }}</option>
                    </select>
                  </label>
                  <label class="flex items-center justify-between">Hide empty columns <Switch v-model="config.display.hide_empty" /></label>
                </template>
                <label v-if="config.layout === 'Gantt'" class="flex items-center justify-between gap-2">
                  Bar colour
                  <select v-model="config.display.bar_color" class="ctl">
                    <option value="state">State</option>
                    <option value="group">Group</option>
                    <option value="type">Type</option>
                    <option value="priority">Priority</option>
                  </select>
                </label>
                <label class="flex items-center justify-between gap-2">
                  Order by
                  <select v-model="config.order_by" class="ctl">
                    <option v-for="o in ORDER_BY" :key="o.value" :value="`${o.value} ${o.value === 'updated_on' || o.value === 'created_on' ? 'desc' : 'asc'}`">{{ o.label }}</option>
                  </select>
                </label>
                <label class="flex items-center justify-between">Show completed <Switch v-model="config.display.show_completed" /></label>
                <label class="flex items-center justify-between">Show sub-work items <Switch v-model="config.display.show_sub" /></label>
                <div>
                  <div class="mb-1.5 text-ink-gray-6">{{ { List: 'Rows show', Table: 'Columns' }[config.layout] || 'Cards show' }}</div>
                  <div class="flex flex-wrap gap-1">
                    <button
                      v-for="f in CARD_FIELDS"
                      :key="f.value"
                      class="rounded-full border px-2 py-0.5 text-xs"
                      :class="cardFields.includes(f.value) ? 'border-outline-gray-5 bg-surface-gray-3 text-ink-gray-9' : 'border-outline-gray-2 text-ink-gray-5'"
                      @click="toggleCardField(f.value)"
                    >{{ f.label }}</button>
                  </div>
                </div>
              </div>
            </template>
          </Popover>
          <Dropdown :options="viewMenu">
            <Button size="sm" icon="lucide-bookmark" :variant="dirty ? 'subtle' : 'ghost'" />
          </Dropdown>
          <Button v-if="ctx.can.write" variant="solid" size="sm" icon-left="lucide-plus" label="New" @click="openCreate()" />
        </div>
      </header>

      <!-- bulk bar -->
      <div v-if="selected.length" class="flex h-10 shrink-0 items-center gap-2 border-b border-outline-gray-1 bg-surface-gray-1 px-4 text-sm">
        <span class="font-medium">{{ selected.length }} selected</span>
        <Picker :model-value="null" :options="stateOptions" label="State" @change="(v) => bulk({ ep_state: v })">
          <template #default="{ toggle }"><Button size="sm" label="Set state" @click="toggle" /></template>
        </Picker>
        <Picker :model-value="null" :options="priorityOptions" label="Priority" @change="(v) => bulk({ priority: v })">
          <template #default="{ toggle }"><Button size="sm" label="Set priority" @click="toggle" /></template>
        </Picker>
        <Picker :model-value="[]" :options="memberOptions" label="Members" @change="(v) => v && bulk({ assignees: [v] })">
          <template #default="{ toggle }"><Button size="sm" label="Assign" @click="toggle" /></template>
        </Picker>
        <Button size="sm" variant="ghost" label="Clear selection" @click="selected = []" />
      </div>

      <div class="min-h-0 flex-1">
        <div v-if="loading && !items.length" class="flex h-full items-center justify-center"><LoadingIndicator class="size-5" /></div>
        <component
          :is="LAYOUT_COMPONENT[config.layout]"
          v-else
          :items="visible"
          :group-by="config.group_by"
          :selected="selected"
          :display="config.display"
          :card-fields="cardFields"
          v-bind="config.layout === 'Table' ? { clashes, defaults: listDefaults } : {}"
          @open="openItem"
          @save="saveItem"
          @created="onCreated"
          @select="select"
          @create="openCreate"
          @display="(patch) => Object.assign(config.display, patch)"
          @reorder="reorder"
        />
      </div>
    </div>

    <!-- side peek -->
    <aside v-if="peek" class="w-[38rem] max-w-[60vw] shrink-0 border-l border-outline-gray-1 bg-surface-base shadow-xl">
      <ItemDetail
        :name="peek"
        :items="items"
        mode="peek"
        @close="closePeek"
        @navigate="openItemByName"
        @expand="expand"
        @changed="onChanged"
        @deleted="onDeleted"
      />
    </aside>

    <!-- create -->
    <CreateDialog v-model="createOpen" :defaults="createDefaults" @created="onCreatedFromDialog" />

    <!-- save view -->
    <Dialog v-model="saveOpen" title="Save view">
      <div class="flex flex-col gap-3">
        <FormControl v-model="saveForm.title" label="Name" placeholder="e.g. Logistics board" />
        <FormControl v-model="saveForm.is_personal" type="checkbox" label="Only for me" />
        <FormControl
          v-if="ctx.can.manage && ctx.project.project_type"
          v-model="saveForm.for_type"
          type="checkbox"
          :label="`Template view: show it on every ${ctx.project.project_type} project`"
        />
      </div>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button label="Cancel" @click="saveOpen = false" />
          <Button variant="solid" label="Save view" :disabled="!saveForm.title" @click="saveAsNew" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Badge, Button, Dialog, Dropdown, FormControl, LoadingIndicator, Popover, Switch, TabButtons, TextInput, toast } from 'frappe-ui'
import CreateDialog from '../components/CreateDialog.vue'
import FilterMenu from '../components/FilterMenu.vue'
import { CARD_FIELDS, DEFAULT_CARD_FIELDS, DEFAULT_LIST_FIELDS } from '../cardFields'
import CategoryManager from '../components/CategoryManager.vue'
import ItemDetail from '../components/ItemDetail.vue'
import Picker from '../components/Picker.vue'
import CalendarLayout from '../layouts/CalendarLayout.vue'
import GanttLayout from '../layouts/GanttLayout.vue'
import KanbanLayout from '../layouts/KanbanLayout.vue'
import ListLayout from '../layouts/ListLayout.vue'
import TableLayout from '../layouts/TableLayout.vue'
import { api } from '../api'
import { ORDER_BY, groupByOptions } from '../grouping'
import { ctx, fail, loadProject, stateOf } from '../store'
import { confirmAction } from '../confirm'
import { PRIORITIES, itemId, treeOrder } from '../utils'

const route = useRoute()
const router = useRouter()

const LAYOUTS = [
  { label: 'List', value: 'List', icon: 'lucide-list' },
  { label: 'Table', value: 'Table', icon: 'lucide-table' },
  { label: 'Kanban', value: 'Kanban', icon: 'lucide-square-kanban' },
  { label: 'Timeline', value: 'Gantt', icon: 'lucide-chart-gantt' },
  { label: 'Calendar', value: 'Calendar', icon: 'lucide-calendar' },
]
const LAYOUT_ICON = { List: 'lucide-list', Table: 'lucide-table', Kanban: 'lucide-square-kanban', Gantt: 'lucide-chart-gantt', Calendar: 'lucide-calendar' }
const LAYOUT_COMPONENT = { List: ListLayout, Table: TableLayout, Kanban: KanbanLayout, Gantt: GanttLayout, Calendar: CalendarLayout }
const groupOptions = computed(groupByOptions)
const DEFAULT = { layout: 'List', filters: [], group_by: 'state', order_by: 'manual asc', display: { show_completed: true, show_sub: true, swimlanes: 'none', hide_empty: false, bar_color: 'state', zoom: 'week', cal_mode: 'month' } }

const view = computed(() => ctx.views.find((v) => v.name === route.query.view) || null)
const config = reactive(structuredClone(DEFAULT))
let baseline = JSON.stringify(DEFAULT)

function parse(value, fallback) {
  if (!value) return fallback
  try {
    return typeof value === 'string' ? JSON.parse(value) : value
  } catch {
    return fallback
  }
}

function applyView() {
  const v = view.value
  const next = v
    ? {
        layout: v.layout || 'List',
        filters: parse(v.filters, []),
        group_by: v.group_by || 'state',
        order_by: v.order_by || 'manual asc',
        display: { ...DEFAULT.display, ...parse(v.display, {}) },
      }
    : structuredClone(DEFAULT)
  Object.assign(config, next)
  baseline = JSON.stringify(next)
}
watch(view, applyView, { immediate: true })
const dirty = computed(() => JSON.stringify(config) !== baseline)

// items
const items = ref([])
const loading = ref(false)
async function loadItems() {
  loading.value = true
  try {
    items.value = await api.items(ctx.project.name, config.filters, config.order_by)
  } catch (err) {
    fail(err)
  } finally {
    loading.value = false
  }
}
watch(() => [JSON.stringify(config.filters), config.order_by], loadItems, { immediate: true })

// double bookings, shown by the Table layout
const clashes = ref({})
async function loadClashes() {
  if (config.layout !== 'Table') return
  try {
    clashes.value = await api.clashes(ctx.project.name)
  } catch (err) {
    fail(err)
  }
}
watch(() => config.layout, loadClashes, { immediate: true })

// a list filtered on one type adds new rows of that type, so they stay in the list
const listDefaults = computed(() => {
  const row = config.filters.find(([attribute, operator, value]) => attribute === 'type' && (operator === '=' || (operator === 'in' && value?.length === 1)))
  return row ? { type: [].concat(row[2])[0] } : {}
})

const search = ref('')
const visible = computed(() => {
  const q = search.value.trim().toLowerCase()
  const list = items.value.filter((item) => {
    if (q && !`${item.subject} ${itemId(ctx.project, item)}`.toLowerCase().includes(q)) return false
    if (!config.display.show_completed && ['Completed', 'Cancelled'].includes(stateOf(item).state_group)) return false
    if (!config.display.show_sub && item.parent_task) return false
    return true
  })
  // keep a dragged row where it was dropped without reloading; ties keep the item number order
  if (config.order_by.startsWith('manual')) list.sort((a, b) => (a.ep_sort_order || 0) - (b.ep_sort_order || 0) || (a.ep_sequence || 0) - (b.ep_sequence || 0))
  // sub-items right under their parent, so they move with it
  return treeOrder(list).items
})

function upsert(item) {
  const i = items.value.findIndex((x) => x.name === item.name)
  if (i >= 0) items.value[i] = { ...items.value[i], ...item }
  else items.value.push(item)
}

async function saveItem(item, patch) {
  const before = { ...item }
  upsert({ ...item, ...patch }) // optimistic
  try {
    upsert(await api.updateItem(item.name, patch))
    loadClashes()
  } catch (err) {
    upsert(before)
    fail(err)
  }
}

const onCreated = (item) => upsert(item) || loadClashes()
const onChanged = (item) => upsert(item)
function onDeleted(name) {
  items.value = items.value.filter((i) => i.name !== name)
  closePeek()
}

// selection and bulk edit
const selected = ref([])
const select = (name, on) => (selected.value = on ? [...selected.value, name] : selected.value.filter((n) => n !== name))
async function bulk(patch) {
  try {
    for (const item of await api.bulkUpdate(selected.value, patch)) upsert(item)
    toast.success(`${selected.value.length} work items updated`)
    selected.value = []
  } catch (err) {
    fail(err)
    loadItems()
  }
}

// peek
const peek = computed(() => route.query.item || null)
function openItem(item) {
  openItemByName(item.name)
}
function openItemByName(name) {
  router.replace({ query: { ...route.query, item: name } })
}
function closePeek() {
  const { item, ...rest } = route.query
  router.replace({ query: rest })
}
function expand(item) {
  router.push({ name: 'item', params: { project: ctx.project.name, id: itemId(ctx.project, item) } })
}

// options
const stateOptions = computed(() => ctx.states.map((s) => ({ value: s.name, label: s.title })))
const priorityOptions = PRIORITIES.map((p) => ({ value: p, label: p }))
const typeOptions = computed(() => ctx.types.map((t) => ({ value: t.name, label: t.name })))
const memberOptions = computed(() => ctx.members.map((m) => ({ value: m.name, label: m.full_name || m.name })))

// create: views open the dialog with values from where you clicked (day, hours, column, lane)
const createOpen = ref(false)
const createDefaults = ref({})
function openCreate(defaults = {}) {
  if (!ctx.can.write) return
  createDefaults.value = { ...listDefaults.value, ...defaults }
  createOpen.value = true
}
function onCreatedFromDialog(item) {
  upsert(item)
  openItem(item)
}

// card fields and manual order
const cardFields = computed(() => config.display.card_fields || (config.layout === 'List' ? DEFAULT_LIST_FIELDS : DEFAULT_CARD_FIELDS))
function toggleCardField(field) {
  const current = cardFields.value
  config.display.card_fields = current.includes(field) ? current.filter((f) => f !== field) : [...current, field]
}
async function reorder(names) {
  names.forEach((name, i) => {
    const item = items.value.find((x) => x.name === name)
    if (item) item.ep_sort_order = i
  })
  if (!config.order_by.startsWith('manual')) config.order_by = 'manual asc'
  try {
    await api.reorder(names)
  } catch (err) {
    fail(err)
  }
}

// views
const saveOpen = ref(false)
const saveForm = reactive({ title: '', is_personal: false, for_type: false })
const canUpdateView = computed(() => view.value && (view.value.owner === ctx.user || ctx.can.manage))
const viewMenu = computed(() => [
  ...(canUpdateView.value && dirty.value ? [{ label: `Update "${view.value.title}"${view.value.project_type ? ' for every project' : ''}`, icon: 'lucide-save', onClick: updateView }] : []),
  // a template view edited here becomes this project's own copy; the template stays as it was
  ...(view.value?.project_type && dirty.value && ctx.can.write ? [{ label: 'Save for this project only', icon: 'lucide-copy', onClick: saveProjectCopy }] : []),
  { label: 'Save as new view', icon: 'lucide-bookmark-plus', onClick: () => Object.assign(saveForm, { title: '', is_personal: false, for_type: false }) && (saveOpen.value = true) },
  ...(dirty.value ? [{ label: 'Reset changes', icon: 'lucide-undo-2', onClick: applyView }] : []),
  // the owner locks a view so others only read it
  ...(canUpdateView.value ? [{ label: view.value.is_locked ? 'Unlock view' : 'Lock view', icon: view.value.is_locked ? 'lucide-lock-open' : 'lucide-lock', onClick: toggleLock }] : []),
  ...(view.value?.project_type && ctx.can.write ? [{ label: 'Remove from this project', icon: 'lucide-eye-off', onClick: hideView }] : []),
  ...(canUpdateView.value ? [{ label: view.value.project_type ? 'Delete for every project' : 'Delete view', icon: 'lucide-trash-2', theme: 'red', onClick: deleteView }] : []),
])

async function toggleLock() {
  const lock = !view.value.is_locked
  const ok = await confirmAction(
    lock
      ? { title: `Lock "${view.value.title}"?`, message: 'Others can still use the view, but only you can change, unlock or delete it.', action: 'Lock' }
      : { title: `Unlock "${view.value.title}"?`, message: 'Everyone who can edit this project can change or delete the view again.', action: 'Unlock' },
  )
  if (!ok) return
  try {
    await api.saveView({ name: view.value.name, is_locked: view.value.is_locked ? 0 : 1 })
    await loadProject(ctx.project.name)
  } catch (err) {
    fail(err)
  }
}

const payload = () => ({
  layout: config.layout,
  filters: config.filters,
  group_by: config.group_by,
  order_by: config.order_by,
  display: config.display,
})

async function saveAsNew() {
  try {
    const doc = await api.saveView({
      ...payload(),
      title: saveForm.title,
      is_personal: saveForm.is_personal ? 1 : 0,
      ...(saveForm.for_type ? { project_type: ctx.project.project_type } : { project: ctx.project.name }),
    })
    saveOpen.value = false
    await loadProject(ctx.project.name)
    router.replace({ query: { view: doc.name } })
    toast.success('View saved')
  } catch (err) {
    fail(err)
  }
}

async function saveProjectCopy() {
  try {
    const { name, title, part, sort_order } = view.value
    const doc = await api.saveView({ ...payload(), title, part, sort_order, project: ctx.project.name })
    if (!part) await api.hideView(ctx.project.name, name) // a copy with a part replaces the shared view by itself
    await loadProject(ctx.project.name)
    router.replace({ query: { view: doc.name } })
    toast.success('Saved for this project')
  } catch (err) {
    fail(err)
  }
}

async function hideView() {
  const ok = await confirmAction({
    title: `Remove "${view.value.title}" from this project?`,
    message: 'Its work items stay, and other projects keep the view. Add it back from "Add to project".',
    action: 'Remove',
  })
  if (!ok) return
  try {
    await api.hideView(ctx.project.name, view.value.name)
    await loadProject(ctx.project.name)
    router.replace({ query: {} })
  } catch (err) {
    fail(err)
  }
}

async function updateView() {
  try {
    await api.saveView({ name: view.value.name, ...payload() })
    await loadProject(ctx.project.name)
    applyView()
    toast.success('View updated')
  } catch (err) {
    fail(err)
  }
}

async function deleteView() {
  const ok = await confirmAction({
    title: `Delete the view "${view.value.title}"?`,
    message: view.value.project_type
      ? 'This is a shared view: it will be deleted from every project. Work items stay. This cannot be undone.'
      : 'Its work items stay. This cannot be undone.',
    action: 'Delete',
    danger: true,
  })
  if (!ok) return
  try {
    await api.remove('Planner View', view.value.name)
    await loadProject(ctx.project.name)
    router.replace({ query: {} })
  } catch (err) {
    fail(err)
  }
}

// keyboard: C creates, Esc closes the peek
function onKey(event) {
  const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName) || event.target.isContentEditable
  if (typing) return
  if (event.key === 'c' && ctx.can.write && !createOpen.value) {
    event.preventDefault()
    openCreate({})
  } else if (event.key === 'Escape' && peek.value) {
    closePeek()
  }
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.ctl {
  @apply h-7 rounded border-0 bg-surface-gray-2 px-2 py-0 text-sm text-ink-gray-8 focus:ring-1 focus:ring-outline-gray-3;
}
</style>
