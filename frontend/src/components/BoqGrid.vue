<template>
  <!-- A department's tech BOQ: the tech team fills the left columns, the warehouse the right ones -->
  <div class="mb-10">
    <div class="mb-3 flex flex-wrap items-center gap-3">
      <select :value="page.boq_status" :disabled="!canWrite" class="h-8 rounded-md border border-outline-gray-2 bg-surface-base px-2 text-sm" @change="setStatus($event.target.value)">
        <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
      </select>
      <span class="text-sm text-ink-gray-5">{{ lines.length }} lines<template v-if="booked"> · {{ booked }} booked</template></span>

      <div class="ml-auto flex items-center gap-2 rounded-md px-2.5 py-1 text-sm" :class="pending ? 'bg-surface-amber-1 text-ink-amber-8' : 'text-ink-gray-5'">
        <span :class="pending ? 'lucide-bell-dot' : 'lucide-check-check'" class="size-4" />
        <span>{{ reviewText }}</span>
        <Button v-if="pending && canWrite" size="sm" label="Mark reviewed" @click="markReviewed" />
      </div>
    </div>

    <div class="overflow-x-auto rounded-lg border border-outline-gray-1">
      <table class="w-full border-separate border-spacing-0 text-sm">
        <thead class="text-left text-xs text-ink-gray-5">
          <tr>
            <th class="w-8" />
            <th colspan="4" class="border-b border-outline-gray-1 px-2 pt-2 font-medium uppercase tracking-wide">Tech team</th>
            <th colspan="3" class="border-b border-l border-outline-gray-1 px-2 pt-2 font-medium uppercase tracking-wide">Warehouse</th>
            <th class="w-8" />
          </tr>
          <tr>
            <th class="border-b border-outline-gray-1" />
            <th class="min-w-[300px] border-b border-outline-gray-1 px-2 py-1.5 font-medium">Item</th>
            <th class="w-20 border-b border-outline-gray-1 px-2 py-1.5 text-right font-medium">Qty</th>
            <th class="w-20 border-b border-outline-gray-1 px-2 py-1.5 font-medium">Unit</th>
            <th class="min-w-[160px] border-b border-outline-gray-1 px-2 py-1.5 font-medium">Note</th>
            <th class="w-20 border-b border-l border-outline-gray-1 px-2 py-1.5 text-right font-medium">Booked</th>
            <th class="w-32 border-b border-outline-gray-1 px-2 py-1.5 font-medium">Status</th>
            <th class="min-w-[160px] border-b border-outline-gray-1 px-2 py-1.5 font-medium">Warehouse note</th>
            <th class="border-b border-outline-gray-1" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="(line, i) in lines" :key="line.name" class="group" :class="isChanged(line) ? 'bg-surface-amber-1' : 'hover:bg-surface-gray-1'">
            <td class="border-b border-outline-gray-1 pl-2 text-xs text-ink-gray-4">
              <span v-if="isChanged(line)" class="lucide-dot block size-4 text-ink-amber-6" title="Changed since the warehouse reviewed" />
              <template v-else>{{ i + 1 }}</template>
            </td>
            <td class="border-b border-outline-gray-1 px-1 py-0.5"><input :value="line.item" :disabled="!canWrite" class="cell" @change="save(line, 'item', $event.target.value.trim())" /></td>
            <td class="border-b border-outline-gray-1 px-1 py-0.5"><input type="number" min="0" step="any" :value="line.qty" :disabled="!canWrite" class="cell text-right" @change="save(line, 'qty', num($event.target.value))" /></td>
            <td class="border-b border-outline-gray-1 px-1 py-0.5">
              <select :value="line.unit" :disabled="!canWrite" class="cell" @change="save(line, 'unit', $event.target.value)">
                <option v-for="u in UNITS" :key="u" :value="u">{{ u }}</option>
              </select>
            </td>
            <td class="border-b border-outline-gray-1 px-1 py-0.5"><input :value="line.note" :disabled="!canWrite" class="cell" @change="save(line, 'note', $event.target.value)" /></td>
            <td class="border-b border-l border-outline-gray-1 px-1 py-0.5"><input type="number" min="0" step="any" :value="line.qty_booked || ''" :disabled="!canWrite" class="cell text-right" @change="save(line, 'qty_booked', num($event.target.value))" /></td>
            <td class="border-b border-outline-gray-1 px-1 py-0.5">
              <select :value="line.line_status" :disabled="!canWrite" class="cell" :class="STATUS_COLOR[line.line_status]" @change="save(line, 'line_status', $event.target.value)">
                <option v-for="s in LINE_STATUSES" :key="s" :value="s">{{ s }}</option>
              </select>
            </td>
            <td class="border-b border-outline-gray-1 px-1 py-0.5"><input :value="line.warehouse_note" :disabled="!canWrite" class="cell" @change="save(line, 'warehouse_note', $event.target.value)" /></td>
            <td class="border-b border-outline-gray-1 pr-1 text-right">
              <button v-if="canWrite" class="rounded p-1 text-ink-gray-4 opacity-0 hover:bg-surface-gray-2 hover:text-ink-red-5 group-hover:opacity-100" title="Remove line" @click="remove(line)">
                <span class="lucide-x block size-4" />
              </button>
            </td>
          </tr>
          <tr v-if="canWrite">
            <td />
            <td colspan="8" class="px-1 py-1">
              <input v-model="draft" class="cell" placeholder="+ Add item, e.g. 30 sqm LED screen, then Enter" @keydown.enter="add" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Button } from 'frappe-ui'
import { api } from '../api'
import { ctx, fail, loadProject, memberName } from '../store'
import { timeAgo } from '../utils'

const props = defineProps({ page: { type: Object, required: true } })

const STATUSES = ['Draft', 'Sent to warehouse', 'Booked', 'Checked out', 'Returned']
const LINE_STATUSES = ['Requested', 'Booked', 'Partly booked', 'Not available']
const UNITS = ['pcs', 'sqm', 'm', 'pair', 'set', 'kit', 'lot']
const STATUS_COLOR = { Booked: 'text-ink-green-6', 'Partly booked': 'text-ink-amber-7', 'Not available': 'text-ink-red-6' }
const FIELDS = ['name', 'item', 'qty', 'unit', 'note', 'qty_booked', 'line_status', 'warehouse_note', 'tech_modified', 'sort_order']

const lines = ref([])
const draft = ref('')
const canWrite = computed(() => ctx.can.write)

watch(
  () => props.page.name,
  async (page) => {
    try {
      lines.value = await api.list('Planner BOQ Line', FIELDS, [['page', '=', page]], 'sort_order asc, creation asc')
    } catch (err) {
      fail(err)
    }
  },
  { immediate: true },
)

// Frappe datetimes ("2026-11-19 10:00:00.123456") compare correctly as strings
const reviewed = computed(() => props.page.reviewed_at)
const isChanged = (line) => Boolean(reviewed.value && line.tech_modified > reviewed.value)
const changed = computed(() => lines.value.filter(isChanged).length)
const removed = computed(() => Boolean(reviewed.value && props.page.lines_removed_at > reviewed.value))
const pending = computed(() => !reviewed.value ? lines.value.length > 0 : changed.value > 0 || removed.value)
const booked = computed(() => lines.value.filter((l) => l.line_status === 'Booked').length)
const reviewText = computed(() => {
  if (!reviewed.value) return 'The warehouse has not reviewed this BOQ yet'
  const since = `since the warehouse reviewed it ${timeAgo(reviewed.value)}`
  if (!pending.value) return `Reviewed by ${memberName(props.page.reviewed_by)} ${timeAgo(reviewed.value)}`
  const parts = [changed.value && `${changed.value} ${changed.value === 1 ? 'line' : 'lines'} changed`, removed.value && 'lines removed'].filter(Boolean)
  return `${parts.join(', ')} ${since}`
})

const num = (v) => (v === '' ? 0 : Number(v))

async function save(line, field, value) {
  if (field === 'item' && !value) return
  if ((line[field] ?? '') === value) return
  try {
    const doc = await api.setValue('Planner BOQ Line', line.name, field, value)
    Object.assign(line, { [field]: doc[field], tech_modified: doc.tech_modified })
  } catch (err) {
    fail(err)
  }
}

async function add() {
  const item = draft.value.trim()
  if (!item) return
  try {
    const doc = await api.insert({ doctype: 'Planner BOQ Line', page: props.page.name, item, qty: 1, unit: 'pcs', sort_order: lines.value.length })
    lines.value.push(doc)
    draft.value = ''
  } catch (err) {
    fail(err)
  }
}

async function remove(line) {
  try {
    await api.remove('Planner BOQ Line', line.name)
    lines.value = lines.value.filter((l) => l !== line)
    // eslint-disable-next-line vue/no-mutating-props -- the page object is the parent's working copy
    props.page.lines_removed_at = await serverNow()
  } catch (err) {
    fail(err)
  }
}
const serverNow = async () => (await api.get('Planner Page', props.page.name)).lines_removed_at

async function setStatus(status) {
  try {
    await api.setValue('Planner Page', props.page.name, 'boq_status', status)
    props.page.boq_status = status // eslint-disable-line vue/no-mutating-props
    loadProject(ctx.project.name)
  } catch (err) {
    fail(err)
  }
}

async function markReviewed() {
  try {
    Object.assign(props.page, await api.markReviewed(props.page.name))
  } catch (err) {
    fail(err)
  }
}
</script>

<style scoped>
.cell {
  @apply h-8 w-full min-w-0 rounded-md border border-transparent bg-transparent px-2 text-sm text-ink-gray-8 hover:border-outline-gray-2 focus:border-outline-gray-4 focus:bg-surface-base focus:outline-none disabled:opacity-80;
}
</style>
