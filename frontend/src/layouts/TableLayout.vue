<template>
  <!-- Spreadsheet of work items: one row each, columns from the view's fields and the types' properties, edited in place -->
  <div class="h-full overflow-auto pb-6">
    <div v-if="clashLines.length" class="mx-3 mt-3 rounded-lg bg-surface-red-1 px-3 py-2 text-sm text-ink-red-6">
      <div v-for="line in clashLines" :key="line" class="flex items-center gap-2">
        <span class="lucide-triangle-alert size-4 shrink-0" />{{ line }}
      </div>
    </div>

    <table class="mt-1 w-full border-separate border-spacing-0 text-sm">
      <thead class="sticky top-0 z-20 bg-surface-base">
        <tr class="text-left text-xs text-ink-gray-5">
          <th class="w-8 border-b border-outline-gray-1" />
          <th v-for="col in columns" :key="col.key" class="border-b border-outline-gray-1 px-2 py-2 font-medium" :style="{ minWidth: col.width }">
            {{ col.label }}
          </th>
          <th class="w-8 border-b border-outline-gray-1" />
        </tr>
      </thead>
      <tbody v-for="[key, rows] in groups" :key="key">
        <tr v-if="groupBy !== 'none'">
          <td :colspan="columns.length + 2" class="px-3 pb-1 pt-4">
            <div class="sticky left-3 w-fit"><GroupHeader :grouper="g" :group-by="groupBy" :k="key" :count="rows.length" /></div>
          </td>
        </tr>
        <tr
          v-for="item in rows"
          :key="item.name"
          class="group"
          :class="clashes[item.name] ? 'bg-surface-red-1/50' : 'hover:bg-surface-gray-1'"
        >
          <td class="border-b border-outline-gray-1 pl-3">
            <Checkbox
              v-if="canWrite"
              class="opacity-0 group-hover:opacity-100"
              :class="selected.includes(item.name) && 'opacity-100'"
              :model-value="selected.includes(item.name)"
              @update:model-value="(v) => emit('select', item.name, v)"
            />
          </td>
          <td v-for="col in columns" :key="col.key" class="border-b border-outline-gray-1 px-1 py-0.5">
            <!-- id: opens the item -->
            <button v-if="col.key === 'id'" class="px-1 text-xs text-ink-gray-5 hover:text-ink-gray-8 hover:underline" @click="emit('open', item)">
              {{ itemId(ctx.project, item) }}
            </button>
            <div v-else-if="col.key === 'subject'" class="flex items-center gap-1">
              <input :value="item.subject" :disabled="!canWrite" class="cell font-medium" @change="(e) => e.target.value.trim() && save(item, { subject: e.target.value.trim() })" />
              <button class="rounded p-1 text-ink-gray-4 opacity-0 hover:bg-surface-gray-2 group-hover:opacity-100" title="Open" @click="emit('open', item)">
                <span class="lucide-panel-right-open block size-4" />
              </button>
            </div>
            <input
              v-else-if="col.kind === 'datetime'"
              type="datetime-local"
              :value="toInput(item[col.key])"
              :disabled="!canWrite"
              class="cell"
              @change="(e) => save(item, { [col.key]: fromInput(e.target.value) })"
            />
            <ItemProps v-else-if="col.kind === 'chip'" :item="item" :fields="[col.key]" labels @save="(d) => save(item, d)" />
            <template v-else-if="col.kind === 'property'">
              <span v-if="!col.types.includes(item.type)" class="px-2 text-ink-gray-3">—</span>
              <select
                v-else-if="col.prop.property_type === 'Dropdown' || col.prop.property_type === 'Member'"
                :value="item[col.key] || ''"
                :disabled="!canWrite"
                class="cell"
                @change="(e) => save(item, { [col.key]: e.target.value || null })"
              >
                <option value="">—</option>
                <option v-for="o in optionsOf(col.prop)" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
              <Checkbox
                v-else-if="col.prop.property_type === 'Checkbox'"
                class="ml-2"
                :model-value="Boolean(item[col.key])"
                :disabled="!canWrite"
                @update:model-value="(v) => save(item, { [col.key]: v ? 1 : 0 })"
              />
              <input
                v-else
                :type="{ Number: 'number', Date: 'date', URL: 'url' }[col.prop.property_type] || 'text'"
                :value="item[col.key] ?? ''"
                :disabled="!canWrite"
                class="cell"
                :class="col.prop.property_type === 'Number' && 'text-right'"
                @change="(e) => save(item, { [col.key]: value(col.prop, e.target.value) })"
              />
            </template>
          </td>
          <td class="border-b border-outline-gray-1 pr-2 text-right">
            <span v-if="clashes[item.name]" class="lucide-triangle-alert inline-block size-4 text-ink-red-5" :title="clashes[item.name].join('\n')" />
          </td>
        </tr>
        <tr v-if="canWrite">
          <td />
          <td :colspan="columns.length + 1" class="px-1 pt-0.5">
            <div class="sticky left-10 w-72"><QuickAdd :defaults="addDefaults(key)" @created="(item) => emit('created', item)" /></div>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="!items.length" class="p-10 text-center text-sm text-ink-gray-5">Nothing in this list yet. Add the first row above.</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Checkbox } from 'frappe-ui'
import GroupHeader from '../components/GroupHeader.vue'
import ItemProps from '../components/ItemProps.vue'
import QuickAdd from '../components/QuickAdd.vue'
import { grouper } from '../grouping'
import { ctx, memberName, propertiesOf } from '../store'
import { groupItems, itemId } from '../utils'

const props = defineProps({
  items: { type: Array, default: () => [] },
  groupBy: { type: String, default: 'day' },
  selected: { type: Array, default: () => [] },
  cardFields: { type: Array, default: () => ['time', 'assignees', 'properties'] },
  clashes: { type: Object, default: () => ({}) }, // { task name: [message] }
  defaults: { type: Object, default: () => ({}) }, // values every new row gets (e.g. the list's type)
})
const emit = defineEmits(['open', 'save', 'created', 'select'])
defineOptions({ inheritAttrs: false })

const canWrite = computed(() => ctx.can.write)
const show = (field) => props.cardFields.includes(field)

// types shown: the list's own type, else every type in the rows
const types = computed(() => [...new Set([props.defaults.type, ...props.items.map((i) => i.type)].filter(Boolean))])

const columns = computed(() => {
  const cols = []
  if (show('id')) cols.push({ key: 'id', label: 'ID', width: '80px' })
  cols.push({ key: 'subject', label: 'Title', width: '260px' })
  if (show('state')) cols.push({ key: 'state', label: 'State', kind: 'chip', width: '130px' })
  if (show('time') || show('start_date')) cols.push({ key: 'exp_start_date', label: 'Start', kind: 'datetime', width: '200px' })
  if (show('time') || show('due_date')) cols.push({ key: 'exp_end_date', label: 'End', kind: 'datetime', width: '200px' })
  if (show('assignees')) cols.push({ key: 'assignees', label: 'People', kind: 'chip', width: '110px' })
  if (show('priority')) cols.push({ key: 'priority', label: 'Priority', kind: 'chip', width: '110px' })
  if (show('properties')) {
    const byField = new Map()
    for (const type of types.value) {
      for (const prop of propertiesOf(type)) {
        const col = byField.get(prop.fieldname) || { key: prop.fieldname, label: prop.label, kind: 'property', prop, types: [], width: prop.property_type === 'Number' ? '90px' : '150px' }
        col.types.push(type)
        byField.set(prop.fieldname, col)
      }
    }
    cols.push(...byField.values())
  }
  return cols
})

const g = computed(() => grouper(props.groupBy))
const groups = computed(() => {
  const entries = [...groupItems(props.items, g.value.keyOf, g.value.keys()).entries()].filter(([, rows]) => rows.length)
  if (props.groupBy === 'day') entries.sort(([a], [b]) => (a || '9').localeCompare(b || '9')) // undated last
  return entries.length ? entries : [[props.groupBy === 'day' ? '' : g.value.keys()[0] ?? 'all', []]]
})

const clashLines = computed(() => [...new Set(props.items.flatMap((i) => props.clashes[i.name] || []))])

function addDefaults(key) {
  const patch = g.value.patch(key, {}, null) || {}
  const out = { ...props.defaults, ...patch }
  if (out.exp_start_date && !out.exp_end_date && show('time')) out.exp_end_date = plusHour(out.exp_start_date)
  return out
}

const save = (item, patch) => emit('save', item, patch)
const optionsOf = (prop) =>
  prop.property_type === 'Member'
    ? ctx.members.map((m) => ({ value: m.name, label: memberName(m.name) }))
    : (prop.options || '').split('\n').filter(Boolean).map((o) => ({ value: o, label: o }))
const value = (prop, v) => (v === '' ? null : prop.property_type === 'Number' ? Number(v) : v)

// Frappe "2026-05-01 09:00:00" <-> input "2026-05-01T09:00"
const toInput = (v) => (v ? String(v).slice(0, 16).replace(' ', 'T') : '')
const fromInput = (v) => (v ? `${v.replace('T', ' ')}:00` : null)
function plusHour(v) {
  const [day, time] = String(v).split(' ')
  const hour = Math.min(23, Number(time.slice(0, 2)) + 1)
  return `${day} ${String(hour).padStart(2, '0')}${time.slice(2)}`
}
</script>

<style scoped>
.cell {
  @apply h-8 w-full min-w-0 rounded-md border border-transparent bg-transparent px-2 text-sm text-ink-gray-8 hover:border-outline-gray-2 focus:border-outline-gray-4 focus:bg-surface-base focus:outline-none disabled:opacity-80;
}
</style>
