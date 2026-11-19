<template>
  <div class="flex h-full overflow-hidden bg-surface-base text-ink-gray-8">
    <aside class="flex h-full shrink-0 border-r border-outline-gray-1">
      <Sidebar v-model:collapsed="collapsed">
        <div class="px-2">
          <SidebarHeader
            :title="ctx.project?.project_name || route.params.project"
            :subtitle="subtitle"
            :logo="LOGO"
            :menu-items="menu"
          />
        </div>

        <div class="scroll-auto-hide flex-1 overflow-y-auto overflow-x-hidden px-2 pt-1">
          <nav class="flex flex-col gap-0.5">
            <SidebarRow v-for="row in navRows" :key="row.name" :row="row" :collapsed="collapsed" />
          </nav>

          <!-- sections; drag a row to reorder it inside its section (pages: among their siblings) -->
          <template v-for="section in sections" :key="section.key">
            <div v-if="section.rows.length || section.empty" class="mt-4 flex flex-col gap-0.5">
              <SidebarLabel divider>{{ section.label }}</SidebarLabel>
              <div
                v-for="row in section.rows"
                :key="row.name"
                data-row
                class="relative"
                @dragover="(e) => canDrop(section.key, row) && (e.preventDefault(), (over = row.name))"
                @dragleave="over === row.name && (over = null)"
                @drop.prevent="drop(row)"
              >
                <!-- where the row lands -->
                <div v-if="over === row.name" class="pointer-events-none absolute inset-x-1 z-10 h-0.5 rounded bg-ink-gray-7" :class="dropBelow(row) ? '-bottom-px' : '-top-px'" />
                <SidebarRow
                  :row="row"
                  :menu="rowMenu(row)"
                  :collapsed="collapsed"
                  :can-drag="ctx.can.write"
                  :dragging="dragging?.name === row.name"
                  @dragstart="(e) => startDrag(section.key, row, e)"
                  @dragend="dragging = over = null"
                />
              </div>
              <div v-if="!section.rows.length" class="px-2 py-1 text-sm text-ink-gray-4">{{ section.empty }}</div>
              <SidebarRow
                v-if="section.key === 'pages'"
                :row="{ name: 'new-page', label: 'New page', icon: 'lucide-plus', to: link('pages'), active: route.name === 'pages' && !route.params.page }"
                :collapsed="collapsed"
              />
            </div>
          </template>

          <div v-if="ctx.can.write && addMenu.length" class="mt-4 px-0.5">
            <Dropdown :options="addMenu" placement="left">
              <button class="flex h-7 w-full items-center gap-2 rounded px-2 text-sm text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8">
                <span class="lucide-circle-plus size-4" /> <span v-if="!collapsed">Add to project</span>
              </button>
            </Dropdown>
          </div>
        </div>

        <div class="mt-auto flex flex-col gap-0.5 px-2 pb-2">
          <SidebarRow
            v-if="ctx.can.manage"
            :row="{ name: 'settings', label: 'Settings', icon: 'lucide-settings', to: link('settings'), active: route.name === 'settings' }"
            :collapsed="collapsed"
          />
          <SidebarRow :row="{ name: 'desk', label: 'Open in desk', icon: 'lucide-external-link', onClick: openDesk }" :collapsed="collapsed" />
          <SidebarCollapseToggle />
        </div>
      </Sidebar>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col">
      <div v-if="ctx.error" class="m-6 rounded border border-outline-red-2 bg-surface-red-1 p-4 text-ink-red-4">
        {{ ctx.error }}
      </div>
      <div v-else-if="!ctx.project" class="flex flex-1 items-center justify-center"><LoadingIndicator class="size-6" /></div>
      <slot v-else />
    </div>

    <SetupDialog v-model="setupOpen" />
    <SaveTemplateDialog v-model="templateOpen" />
    <NotifyDialog v-model="notifyOpen" />
    <ConfirmDialog />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Dropdown, LoadingIndicator, Sidebar, SidebarCollapseToggle, SidebarHeader, SidebarLabel } from 'frappe-ui'
import ConfirmDialog from './ConfirmDialog.vue'
import NotifyDialog from './NotifyDialog.vue'
import SidebarRow from './SidebarRow.vue'
import { confirmAction } from '../confirm'
import SaveTemplateDialog from './SaveTemplateDialog.vue'
import SetupDialog from './SetupDialog.vue'
import { api } from '../api'
import { ctx, fail, loadProject } from '../store'

const route = useRoute()
const router = useRouter()
const collapsed = ref(window.innerWidth < 1100)
const LOGO = '/assets/frappe/images/frappe-framework-logo.svg'
const LAYOUT_ICON = { List: 'lucide-list', Table: 'lucide-table', Kanban: 'lucide-square-kanban', Gantt: 'lucide-chart-gantt', Calendar: 'lucide-calendar' }
const PAGE_ICON = {
  Brief: 'lucide-notebook-pen',
  Debrief: 'lucide-clipboard-check',
  'Call Sheet': 'lucide-phone-call',
  'Run Sheet': 'lucide-list-ordered',
  Notes: 'lucide-file-text',
}

// ── dialogs ───────────────────────────────────────────────────────────────────
const setupOpen = ref(false)
const templateOpen = ref(false)
const notifyOpen = ref(false)
// a project made in the desk asks once how to set it up
watch(
  () => ctx.project && ctx.needs_setup && ctx.can.write,
  (needs) => (setupOpen.value = Boolean(needs)),
  { immediate: true },
)

const subtitle = computed(() => [ctx.project?.key, ctx.project?.status].filter(Boolean).join(' · '))
const deskLink = computed(() => `/app/project/${encodeURIComponent(route.params.project)}`)
const openDesk = () => (window.location.href = deskLink.value)
const menu = computed(() => [
  ...(ctx.can.write ? [{ label: 'Notify team', icon: 'lucide-send', onClick: () => (notifyOpen.value = true) }] : []),
  { label: 'Save as template', icon: 'lucide-layout-template', onClick: () => (templateOpen.value = true) },
  { label: 'All projects', icon: 'lucide-folder-kanban', onClick: () => (window.location.href = '/planner') },
  { label: 'Back to desk', icon: 'lucide-arrow-left', onClick: openDesk },
])

function link(name) {
  return { name, params: { project: route.params.project } }
}

// ── sections, in the project's own order ──────────────────────────────────────
const order = computed(() => ctx.sidebar?.order || [])
const rank = (name) => {
  const i = order.value.indexOf(name)
  return i === -1 ? 1e6 : i
}
const byRank = (rows) => [...rows].sort((a, b) => rank(a.name) - rank(b.name)) // stable: unranked keep their order

// a list is a list or table view that picks work items by type (Action plan, Run of show, Crew call sheet…)
const typeFilter = (view) => {
  try {
    const filters = typeof view.filters === 'string' ? JSON.parse(view.filters || '[]') : view.filters
    return (filters || []).find((f) => f[0] === 'type')
  } catch {
    return null
  }
}
const isList = (view) => ['List', 'Table'].includes(view.layout) && Boolean(typeFilter(view))
function listIcon(view) {
  const [, operator, value] = typeFilter(view)
  const type = operator === 'in' && value?.length === 1 ? value[0] : operator === '=' ? value : null
  return ctx.types.find((t) => t.name === type)?.ep_icon || 'lucide-list-todo'
}

const navRows = computed(() => [
  { name: 'home', label: 'Home', icon: 'lucide-house', to: { name: 'home' } },
  { name: 'overview', label: 'Overview', icon: 'lucide-layout-dashboard', to: link('overview'), active: route.name === 'overview' },
  { name: 'items', label: 'Work items', icon: 'lucide-list-checks', to: link('items'), active: ['items', 'item'].includes(route.name) && !route.query.view },
])

const viewRow = (view, icon) => ({
  kind: 'view',
  source: view,
  name: view.name,
  label: view.title,
  icon,
  is_locked: view.is_locked,
  to: { name: 'items', params: { project: route.params.project }, query: { view: view.name } },
  active: route.query.view === view.name,
})
const pageRow = (page, label, icon, emoji) => ({
  kind: 'page',
  source: page,
  name: page.name,
  parent: page.parent_page || '',
  depth: page.depth || 0,
  label,
  icon,
  emoji,
  is_locked: page.is_locked,
  to: { name: 'pages', params: { project: route.params.project, page: page.name } },
  active: route.params.page === page.name,
})

/** Pages as a tree, siblings in the project's order, flattened with a depth for indentation. */
const pageTree = computed(() => {
  const children = new Map()
  for (const page of byRank(ctx.pages)) {
    if (page.page_kind === 'BOQ') continue // in the Tech BOQ section
    const key = page.parent_page || ''
    children.set(key, [...(children.get(key) || []), page])
  }
  const out = []
  const walk = (parent, depth) => {
    for (const page of children.get(parent) || []) {
      out.push({ ...page, depth })
      if (depth < 5) walk(page.name, depth + 1)
    }
  }
  walk('', 0)
  return out
})

const sections = computed(() => [
  { key: 'lists', label: 'Lists', rows: byRank(ctx.views.filter(isList)).map((v) => viewRow(v, listIcon(v))) },
  { key: 'boq', label: 'Tech BOQ', rows: byRank(ctx.pages.filter((p) => p.page_kind === 'BOQ')).map((p) => pageRow(p, p.title, 'lucide-package', p.icon)) },
  { key: 'views', label: 'Views', empty: 'Save a view from Work items', rows: byRank(ctx.views.filter((v) => !isList(v))).map((v) => viewRow(v, LAYOUT_ICON[v.layout])) },
  { key: 'pages', label: 'Pages', empty: ' ', rows: pageTree.value.map((p) => pageRow(p, p.title, PAGE_ICON[p.page_kind] || 'lucide-file-text')) },
])

// ── row menu: lock, remove, delete — each asks first ─────────────────────────
// the owner (or a manager) locks and unlocks; a locked row is deleted only by them
const canLock = (row) => row.source.owner === ctx.user || ctx.can.manage
function rowMenu(row) {
  if (!ctx.can.write) return []
  const { kind, source, is_locked } = row
  const shared = kind === 'view' && source.project_type
  const out = []
  if (canLock(row) && !shared) {
    out.push({ label: is_locked ? 'Unlock' : 'Lock', icon: is_locked ? 'lucide-lock-open' : 'lucide-lock', onClick: () => setLock(row, !is_locked) })
  }
  if (shared) out.push({ label: 'Remove from this project', icon: 'lucide-eye-off', onClick: () => removeView(row) })
  else if (!is_locked || canLock(row)) out.push({ label: kind === 'view' ? 'Delete view' : 'Delete page', icon: 'lucide-trash-2', theme: 'red', onClick: () => remove(row) })
  return out
}

async function setLock(row, lock) {
  const what = row.kind === 'view' ? 'view' : 'page'
  const ok = await confirmAction(
    lock
      ? { title: `Lock "${row.label}"?`, message: `Others can still open the ${what}, but only you can change, unlock or delete it.`, action: 'Lock' }
      : { title: `Unlock "${row.label}"?`, message: `Everyone who can edit this project can change or delete the ${what} again.`, action: 'Unlock' },
  )
  if (!ok) return
  try {
    if (row.kind === 'view') await api.saveView({ name: row.name, is_locked: lock ? 1 : 0 })
    else await api.setValue('Planner Page', row.name, 'is_locked', lock ? 1 : 0)
    await loadProject(ctx.project.name)
  } catch (err) {
    fail(err)
  }
}

async function removeView(row) {
  const ok = await confirmAction({
    title: `Remove "${row.label}" from this project?`,
    message: 'Its work items stay, and other projects keep the view. Add it back from "Add to project".',
    action: 'Remove',
  })
  if (!ok) return
  try {
    await api.hideView(ctx.project.name, row.name)
    await loadProject(ctx.project.name)
    if (row.active) router.push(link('items'))
  } catch (err) {
    fail(err)
  }
}

async function remove(row) {
  const page = row.kind === 'page'
  const children = page && ctx.pages.some((p) => p.parent_page === row.name)
  const ok = await confirmAction({
    title: `Delete "${row.label}"?`,
    message: page
      ? `The page${row.source.page_kind === 'BOQ' ? ' and all its BOQ lines' : ''} will be deleted.${children ? ' Its sub-pages move up one level.' : ''} This cannot be undone.`
      : 'The view will be deleted. Its work items stay. This cannot be undone.',
    action: 'Delete',
    danger: true,
  })
  if (!ok) return
  try {
    await api.remove(page ? 'Planner Page' : 'Planner View', row.name)
    await loadProject(ctx.project.name)
    if (row.active) router.push(link(page ? 'pages' : 'items'))
  } catch (err) {
    fail(err)
  }
}

// ── drag to reorder ───────────────────────────────────────────────────────────
const dragging = ref(null) // { section, name, parent }
const over = ref(null)
function startDrag(section, row, event) {
  if (!ctx.can.write) return
  dragging.value = { section, name: row.name, parent: row.parent }
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', row.label)
  const el = event.target.closest('[data-row]') // drag the whole row, not just the grip
  if (el) event.dataTransfer.setDragImage(el, 16, el.offsetHeight / 2)
}
const shownNames = computed(() => sections.value.flatMap((s) => s.rows.map((r) => r.name)))
// dropped below the target when moving down, above it when moving up
const dropBelow = (row) => shownNames.value.indexOf(dragging.value?.name) < shownNames.value.indexOf(row.name)
const canDrop = (section, row) => dragging.value && dragging.value.section === section && dragging.value.parent === row.parent && dragging.value.name !== row.name

async function drop(target) {
  const moved = dragging.value?.name
  dragging.value = over.value = null
  if (!moved || moved === target.name) return
  // the whole sidebar in its shown order, with the moved row put where it was dropped
  const names = [...shownNames.value]
  const from = names.indexOf(moved)
  names.splice(from, 1)
  const to = names.indexOf(target.name)
  names.splice(from <= to ? to + 1 : to, 0, moved)
  ctx.sidebar = { ...(ctx.sidebar || {}), order: names }
  try {
    await api.setSidebarOrder(ctx.project.name, names)
  } catch (err) {
    fail(err)
  }
}

// ── add to project: missing parts and hidden shared views ─────────────────────
const PART_ICON = { page: 'lucide-notebook-pen', boq: 'lucide-package', view: 'lucide-table' }
const addMenu = computed(() => {
  const groups = new Map()
  for (const p of ctx.part_options || []) {
    if ((ctx.parts || []).includes(p.key)) continue
    groups.set(p.group, [...(groups.get(p.group) || []), { label: p.label, icon: PART_ICON[p.kind], onClick: () => addPart(p.key) }])
  }
  const hidden = (ctx.hidden_views || []).map((v) => ({ label: v.title, icon: 'lucide-eye', onClick: () => showView(v.name) }))
  if (hidden.length) groups.set('Hidden views', hidden)
  return [...groups.entries()].map(([group, items]) => ({ group, items }))
})
async function addPart(part) {
  try {
    const { page } = await api.addPart(ctx.project.name, part)
    await loadProject(ctx.project.name)
    if (page) router.push({ name: 'pages', params: { project: ctx.project.name, page } })
  } catch (err) {
    fail(err)
  }
}
async function showView(view) {
  try {
    await api.showView(ctx.project.name, view)
    await loadProject(ctx.project.name)
  } catch (err) {
    fail(err)
  }
}
</script>
