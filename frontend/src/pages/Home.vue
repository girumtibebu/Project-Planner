<template>
  <div class="h-full overflow-y-auto bg-surface-base">
    <div class="mx-auto max-w-6xl px-6 py-10">
      <!-- greeting -->
      <div class="mb-8 flex flex-wrap items-end gap-4">
        <div>
          <div class="text-sm text-ink-gray-5">{{ todayLabel }}</div>
          <h1 class="mt-1 text-2xl font-semibold tracking-tight text-ink-gray-9">{{ greeting }}, {{ firstName }}</h1>
        </div>
        <div class="ml-auto flex items-center gap-2">
          <Button v-if="home?.can_create_project" icon-left="lucide-plus" label="New project" class="hidden sm:flex" @click="newOpen = true" />
          <a href="/app/project"><Button variant="ghost" icon-left="lucide-external-link" label="Projects in desk" /></a>
        </div>
      </div>

      <div v-if="!home" class="flex h-64 items-center justify-center"><LoadingIndicator class="size-6" /></div>

      <template v-else>
        <!-- stats -->
        <div class="mb-8 grid grid-cols-2 gap-3 md:grid-cols-4">
          <button v-for="s in stats" :key="s.key" class="tile text-left" @click="s.tab && (tab = s.tab)">
            <div class="flex items-center gap-2 text-sm text-ink-gray-5">
              <span :class="s.icon" class="size-4" :style="{ color: s.color }" /> {{ s.label }}
            </div>
            <div class="mt-2 text-3xl font-semibold tracking-tight text-ink-gray-9">{{ s.value }}</div>
          </button>
        </div>

        <div class="grid gap-8 lg:grid-cols-3">
          <!-- my work -->
          <section class="lg:col-span-2">
            <div class="mb-3 flex items-center gap-3">
              <h2 class="text-base font-semibold text-ink-gray-9">My work</h2>
              <TabButtons v-model="tab" :buttons="tabs" />
            </div>
            <div class="rounded-2xl border border-outline-gray-1 p-1.5">
              <div
                v-for="item in tabItems"
                :key="item.name"
                class="group flex h-11 cursor-pointer items-center gap-3 rounded-xl px-2.5 hover:bg-surface-gray-1"
                @click="openItem(item)"
              >
                <Tooltip text="Mark done">
                  <button
                    class="flex size-5 shrink-0 items-center justify-center rounded-full border-[1.5px] border-outline-gray-3 text-transparent hover:border-ink-green-3 hover:text-ink-green-3"
                    @click.stop="complete(item)"
                  ><span class="lucide-check size-3" /></button>
                </Tooltip>
                <StateIcon :state="home.states[item.ep_state] || home.states[`status:${item.status}`]" />
                <span class="w-16 shrink-0 text-xs text-ink-gray-5">{{ id(item) }}</span>
                <span class="min-w-0 flex-1 truncate text-sm text-ink-gray-8">{{ item.subject }}</span>
                <span class="hidden shrink-0 truncate rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-6 sm:inline max-w-[10rem]">{{ projectName(item.project) }}</span>
                <span v-if="item.priority === 'Urgent' || item.priority === 'High'" :class="[PRIORITY_ICON[item.priority], PRIORITY_COLOR[item.priority]]" class="size-4 shrink-0" />
                <span class="w-16 shrink-0 text-right text-xs" :class="isOverdue(item) ? 'text-ink-red-4' : 'text-ink-gray-5'">{{ formatDate(item.exp_end_date) || '—' }}</span>
              </div>
              <div v-if="!tabItems.length" class="flex flex-col items-center gap-2 py-12 text-sm text-ink-gray-5">
                <span class="lucide-party-popper size-6 text-ink-gray-4" />
                {{ tab === 'overdue' ? 'Nothing overdue. Nice.' : 'Nothing here.' }}
              </div>
            </div>
          </section>

          <!-- activity -->
          <section>
            <h2 class="mb-3 text-base font-semibold text-ink-gray-9">On your work</h2>
            <div class="flex flex-col gap-1">
              <button
                v-for="(e, i) in home.activity"
                :key="i"
                class="flex gap-2.5 rounded-xl p-2 text-left hover:bg-surface-gray-1"
                @click="openItem({ name: e.task, project: e.project })"
              >
                <Avatar :label="userName(e.user)" size="sm" />
                <div class="min-w-0 flex-1 text-sm">
                  <div class="text-ink-gray-6">
                    <span class="font-medium text-ink-gray-8">{{ userName(e.user) }}</span>
                    {{ e.kind === 'comment' ? 'commented on' : `changed ${e.fields.join(', ')} of` }}
                  </div>
                  <div class="truncate text-ink-gray-8">{{ e.subject }}</div>
                  <div v-if="e.kind === 'comment'" class="mt-0.5 line-clamp-2 text-xs text-ink-gray-5">{{ strip(e.content) }}</div>
                  <div class="mt-0.5 text-xs text-ink-gray-4">{{ timeAgo(e.at) }}</div>
                </div>
              </button>
              <div v-if="!home.activity.length" class="rounded-xl p-4 text-sm text-ink-gray-5">No news on your work in the last two weeks.</div>
            </div>
          </section>
        </div>

        <!-- projects -->
        <section class="mt-10">
          <div class="mb-3 flex flex-wrap items-center gap-2">
            <h2 class="mr-1 text-base font-semibold text-ink-gray-9">Projects</h2>
            <TabButtons v-model="projectTab" :buttons="[{ label: 'Mine', value: 'mine' }, { label: 'All open', value: 'all' }]" />
            <div class="ml-auto flex items-center gap-2">
              <select v-model="owner" class="ctl" title="Created by">
                <option value="">Anyone</option>
                <option v-for="o in owners" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
              <select v-model="sort" class="ctl" title="Sort">
                <option v-for="s in SORTS" :key="s.value" :value="s.value">{{ s.label }}</option>
              </select>
              <TabButtons
                v-model="layout"
                :buttons="[
                  { value: 'cards', icon: 'lucide-layout-grid', label: '' },
                  { value: 'list', icon: 'lucide-list', label: '' },
                ]"
              />
              <TextInput v-model="search" placeholder="Search…" class="w-52">
                <template #prefix><span class="lucide-search size-4 text-ink-gray-4" /></template>
              </TextInput>
            </div>
          </div>

          <!-- list -->
          <div v-if="layout === 'list'" class="overflow-x-auto rounded-2xl border border-outline-gray-1">
            <table class="w-full text-sm">
              <thead class="text-left text-xs text-ink-gray-5">
                <tr class="border-b border-outline-gray-1">
                  <th class="px-3 py-2 font-medium">Project</th>
                  <th class="px-3 py-2 font-medium">Type</th>
                  <th class="px-3 py-2 font-medium">Dates</th>
                  <th class="w-44 px-3 py-2 font-medium">Progress</th>
                  <th class="px-3 py-2 font-medium">Created by</th>
                  <th class="px-3 py-2 font-medium">Created</th>
                  <th class="px-3 py-2 font-medium">Updated</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in shownProjects" :key="p.name" class="cursor-pointer border-b border-outline-gray-1 last:border-0 hover:bg-surface-gray-1" @click="openProject(p)">
                  <td class="px-3 py-2">
                    <div class="flex items-center gap-2">
                      <span class="rounded-md bg-surface-gray-2 px-1.5 py-0.5 text-xs font-medium text-ink-gray-6">{{ p.key || '—' }}</span>
                      <span class="truncate font-medium text-ink-gray-9">{{ p.project_name }}</span>
                      <span v-if="p.overdue" class="shrink-0 rounded-full bg-surface-red-1 px-2 py-0.5 text-xs text-ink-red-4">{{ p.overdue }} overdue</span>
                    </div>
                  </td>
                  <td class="px-3 py-2 text-ink-gray-6">{{ p.project_type || '—' }}</td>
                  <td class="whitespace-nowrap px-3 py-2 text-ink-gray-6">{{ p.start || p.end ? `${formatDate(p.start)} – ${formatDate(p.end)}` : '—' }}</td>
                  <td class="px-3 py-2">
                    <div class="flex items-center gap-2">
                      <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-gray-2"><div class="h-full rounded-full bg-surface-gray-7" :style="{ width: `${p.progress}%` }" /></div>
                      <span class="w-12 text-right text-xs text-ink-gray-5">{{ p.done }}/{{ p.total }}</span>
                    </div>
                  </td>
                  <td class="px-3 py-2 text-ink-gray-6">{{ p.owner_name }}</td>
                  <td class="whitespace-nowrap px-3 py-2 text-ink-gray-5">{{ timeAgo(p.created) }}</td>
                  <td class="whitespace-nowrap px-3 py-2 text-ink-gray-5">{{ timeAgo(p.modified) }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="!shownProjects.length" class="p-8 text-center text-sm text-ink-gray-5">{{ projectTab === 'mine' ? 'No projects with work for you yet.' : 'No projects match.' }}</div>
          </div>

          <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <router-link
              v-for="p in shownProjects"
              :key="p.name"
              :to="{ name: 'items', params: { project: p.name } }"
              class="tile flex flex-col gap-3"
            >
              <div class="flex items-start gap-2">
                <span class="rounded-md bg-surface-gray-2 px-1.5 py-0.5 text-xs font-medium text-ink-gray-6">{{ p.key || '—' }}</span>
                <span class="min-w-0 flex-1 truncate text-sm font-medium text-ink-gray-9">{{ p.project_name }}</span>
                <span v-if="p.overdue" class="shrink-0 rounded-full bg-surface-red-1 px-2 py-0.5 text-xs text-ink-red-4">{{ p.overdue }} overdue</span>
              </div>
              <div class="text-xs text-ink-gray-5">
                {{ p.project_type || 'No type' }}<template v-if="p.start || p.end"> · {{ formatDate(p.start) }} – {{ formatDate(p.end) }}</template>
              </div>
              <div class="text-xs text-ink-gray-4">{{ p.owner_name }} · created {{ timeAgo(p.created) }}</div>
              <div>
                <div class="mb-1 flex justify-between text-xs text-ink-gray-5">
                  <span>{{ p.done }}/{{ p.total }} done</span>
                  <span v-if="p.mine">{{ p.mine }} for you</span>
                </div>
                <div class="h-1.5 overflow-hidden rounded-full bg-surface-gray-2">
                  <div class="h-full rounded-full bg-surface-gray-7" :style="{ width: `${p.progress}%` }" />
                </div>
              </div>
            </router-link>
            <div v-if="!shownProjects.length" class="col-span-full rounded-2xl border border-dashed border-outline-gray-2 p-8 text-center text-sm text-ink-gray-5">
              {{ projectTab === 'mine' ? 'No projects with work for you yet.' : 'No projects match.' }}
            </div>
          </div>
        </section>
      </template>
    </div>
    <NewProjectDialog v-model="newOpen" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Avatar, Button, LoadingIndicator, TabButtons, TextInput, Tooltip, toast } from 'frappe-ui'
import NewProjectDialog from '../components/NewProjectDialog.vue'
import StateIcon from '../components/StateIcon.vue'
import { api } from '../api'
import { fail } from '../store'
import { PRIORITY_COLOR, PRIORITY_ICON, addDays, dayKey, formatDate, isOverdue, timeAgo } from '../utils'

const router = useRouter()
const home = ref(null)
const tab = ref('today')
const projectTab = ref('mine')
const search = ref('')
const newOpen = ref(false)

async function load() {
  try {
    home.value = await api.home()
    // open on the first tab that has something
    tab.value = ['today', 'overdue', 'week', 'later', 'none'].find((t) => bucket(t).length) || 'today'
    if (!home.value.projects.some((p) => p.is_mine)) projectTab.value = 'all'
  } catch (err) {
    fail(err)
  }
}
onMounted(load)

const hour = new Date().getHours()
const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
const firstName = computed(() => (home.value?.full_name || window.user_fullname || '').split(' ')[0])
const todayLabel = new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })

const todayKey = dayKey(new Date())
const weekEnd = dayKey(addDays(new Date(), 6 - ((new Date().getDay() + 6) % 7)))
function bucket(name) {
  const items = home.value?.items || []
  const due = (i) => dayKey(i.exp_end_date)
  return {
    overdue: items.filter((i) => i.exp_end_date && due(i) < todayKey),
    today: items.filter((i) => due(i) === todayKey || (i.exp_start_date && dayKey(i.exp_start_date) <= todayKey && due(i) >= todayKey)),
    week: items.filter((i) => due(i) > todayKey && due(i) <= weekEnd),
    later: items.filter((i) => due(i) > weekEnd),
    none: items.filter((i) => !i.exp_end_date),
  }[name]
}
const tabs = computed(() =>
  [
    ['overdue', 'Overdue'],
    ['today', 'Today'],
    ['week', 'This week'],
    ['later', 'Later'],
    ['none', 'No date'],
  ].map(([value, label]) => ({ value, label: `${label} ${bucket(value).length}` })),
)
const tabItems = computed(() => bucket(tab.value))

const stats = computed(() => [
  { key: 'open', label: 'Assigned to you', value: home.value.items.length, icon: 'lucide-circle-dot', tab: 'today' },
  { key: 'overdue', label: 'Overdue', value: bucket('overdue').length, icon: 'lucide-alarm-clock', color: '#EF4444', tab: 'overdue' },
  { key: 'week', label: 'Due this week', value: bucket('week').length + bucket('today').length, icon: 'lucide-calendar-days', tab: 'week' },
  { key: 'done', label: 'Done in 7 days', value: home.value.completed_this_week, icon: 'lucide-circle-check', color: '#10B981' },
])

// project list: layout, sort and owner are remembered in this browser
const remembered = (key, fallback) => {
  try {
    return localStorage.getItem(`planner.home.${key}`) || fallback
  } catch {
    return fallback
  }
}
const remember = (key) => (value) => {
  try {
    localStorage.setItem(`planner.home.${key}`, value)
  } catch {
    // private mode: not remembered
  }
}
const layout = ref(remembered('layout', 'cards'))
const sort = ref(remembered('sort', 'mine'))
const owner = ref('')
watch(layout, remember('layout'))
watch(sort, remember('sort'))

const SORTS = [
  { value: 'mine', label: 'My work first' },
  { value: 'modified', label: 'Last updated' },
  { value: 'created', label: 'Last created' },
  { value: 'start', label: 'Start date' },
  { value: 'name', label: 'Name' },
]
const by = (field, desc = false) => (a, b) => (String(a[field] || '') < String(b[field] || '') ? -1 : String(a[field] || '') > String(b[field] || '') ? 1 : 0) * (desc ? -1 : 1)
const SORTERS = {
  mine: null, // as the server sends them
  modified: by('modified', true),
  created: by('created', true),
  start: (a, b) => (!a.start) - (!b.start) || by('start')(a, b), // undated last
  name: (a, b) => a.project_name.localeCompare(b.project_name),
}
const owners = computed(() => {
  const seen = new Map((home.value?.projects || []).map((p) => [p.owner, p.owner_name]))
  return [...seen.entries()].map(([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label))
})

const shownProjects = computed(() => {
  const q = search.value.trim().toLowerCase()
  const rows = (home.value?.projects || [])
    .filter((p) => projectTab.value === 'all' || p.is_mine)
    .filter((p) => !owner.value || p.owner === owner.value)
    .filter((p) => !q || `${p.project_name} ${p.key} ${p.customer || ''}`.toLowerCase().includes(q))
  return SORTERS[sort.value] ? [...rows].sort(SORTERS[sort.value]) : rows
})
const openProject = (p) => router.push({ name: 'items', params: { project: p.name } })

const id = (item) => (home.value.keys[item.project] && item.ep_sequence ? `${home.value.keys[item.project]}-${item.ep_sequence}` : item.name)
const projectName = (name) => home.value.projects.find((p) => p.name === name)?.project_name || name
const userName = (user) => user?.split('@')[0].replace(/^\w/, (c) => c.toUpperCase())
const strip = (html) => String(html || '').replace(/<[^>]+>/g, '')

function openItem(item) {
  router.push({ name: 'items', params: { project: item.project }, query: { item: item.name } })
}

async function complete(item) {
  try {
    await api.completeItem(item.name)
    home.value.items = home.value.items.filter((i) => i.name !== item.name)
    home.value.completed_this_week++
    toast.success(`Done: ${item.subject}`)
  } catch (err) {
    fail(err)
  }
}
</script>

<style scoped>
.tile {
  @apply rounded-2xl border border-outline-gray-1 bg-surface-base p-4 transition hover:border-outline-gray-2 hover:shadow-sm;
}
.ctl {
  @apply h-7 rounded-md border-0 bg-surface-gray-2 py-0 pl-2 pr-7 text-sm text-ink-gray-7 focus:ring-1 focus:ring-outline-gray-3;
}
</style>
