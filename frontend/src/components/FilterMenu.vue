<template>
  <Popover align="start">
    <template #trigger>
      <Button size="sm" icon-left="lucide-list-filter">
        Filters<span v-if="modelValue.length" class="ml-1 rounded bg-surface-gray-3 px-1 text-xs">{{ modelValue.length }}</span>
      </Button>
    </template>
    <template #default>
      <div class="w-[30rem] p-3">
        <div v-if="!rows.length" class="mb-2 text-sm text-ink-gray-5">No filters. All work items of the project are shown.</div>
        <div v-for="(row, i) in rows" :key="i" class="mb-2 flex items-center gap-2">
          <select v-model="row.attribute" class="ctl w-32" @change="resetRow(row)">
            <option v-for="a in ATTRS" :key="a.value" :value="a.value">{{ a.label }}</option>
          </select>
          <select v-model="row.operator" class="ctl w-28">
            <option v-for="op in attr(row).ops" :key="op.value" :value="op.value">{{ op.label }}</option>
          </select>
          <div class="min-w-0 flex-1">
            <Picker
              v-if="attr(row).options && row.operator !== 'is'"
              v-model="row.value"
              :options="attr(row).options()"
              :multiple="attr(row).multiple"
              :label="attr(row).label"
            >
              <template #default="{ toggle }">
                <button class="ctl w-full truncate text-left" @click="toggle">{{ valueLabel(row) || 'Choose…' }}</button>
              </template>
            </Picker>
            <select v-else-if="row.operator === 'is'" v-model="row.value" class="ctl w-full">
              <option value="set">set</option>
              <option value="not set">not set</option>
            </select>
            <!-- dates: relative choices keep a saved view correct over time -->
            <div v-else-if="attr(row).input === 'date'" class="flex gap-1">
              <select
                class="ctl min-w-0 flex-1"
                :value="String(row.value || '').startsWith('@') ? row.value : 'pick'"
                @change="(e) => (row.value = e.target.value === 'pick' ? '' : e.target.value)"
              >
                <option v-for="t in DATE_TOKENS" :key="t.value" :value="t.value">{{ t.label }}</option>
                <option value="pick">Pick a date…</option>
              </select>
              <input v-if="!String(row.value || '').startsWith('@')" v-model="row.value" type="date" class="ctl w-36" />
            </div>
            <input v-else v-model="row.value" type="text" class="ctl w-full" />
          </div>
          <Button variant="ghost" icon="lucide-x" @click="rows.splice(i, 1)" />
        </div>
        <div class="flex items-center justify-between border-t border-outline-gray-1 pt-2">
          <Button size="sm" variant="ghost" icon-left="lucide-plus" label="Add filter" @click="addRow" />
          <div class="flex gap-2">
            <Button size="sm" label="Clear" @click="rows = []; apply()" />
            <Button size="sm" variant="solid" label="Apply" @click="apply" />
          </div>
        </div>
      </div>
    </template>
  </Popover>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Button, Popover } from 'frappe-ui'
import Picker from './Picker.vue'
import { ctx, memberName } from '../store'
import { PRIORITIES, STATE_GROUPS } from '../utils'

const props = defineProps({ modelValue: { type: Array, default: () => [] } })
const emit = defineEmits(['update:modelValue'])

const IS = [{ value: 'in', label: 'is' }, { value: 'not in', label: 'is not' }]
const members = () => [{ value: '@me', label: 'Me' }, ...ctx.members.map((m) => ({ value: m.name, label: m.full_name || m.name }))]
const DATE_TOKENS = [
  { value: '@today', label: 'Today' },
  { value: '@tomorrow', label: 'Tomorrow' },
  { value: '@week_start', label: 'Start of this week' },
  { value: '@week_end', label: 'End of this week' },
  { value: '@month_start', label: 'Start of this month' },
  { value: '@month_end', label: 'End of this month' },
]
const DATE_OPS = [
  { value: '<', label: 'before' },
  { value: '>', label: 'after' },
  { value: 'is', label: 'is' },
]
const ATTRS = [
  { value: 'state', label: 'State', ops: IS, multiple: true, options: () => ctx.states.map((s) => ({ value: s.name, label: s.title })) },
  { value: 'state_group', label: 'State group', ops: IS, multiple: true, options: () => STATE_GROUPS.map((g) => ({ value: g, label: g })) },
  { value: 'priority', label: 'Priority', ops: IS, multiple: true, options: () => PRIORITIES.map((p) => ({ value: p, label: p })) },
  { value: 'assignee', label: 'Assignee', ops: [...IS, { value: 'is', label: 'is' }], options: members },
  { value: 'type', label: 'Type', ops: IS, multiple: true, options: () => ctx.types.map((t) => ({ value: t.name, label: t.name })) },
  { value: 'group', label: 'Category', ops: IS, multiple: true, options: () => ctx.groups.map((g) => ({ value: g.name, label: g.title })) },
  { value: 'label', label: 'Label', ops: [{ value: 'like', label: 'has' }, { value: 'not like', label: 'has not' }] },
  { value: 'due_date', label: 'Due date', ops: DATE_OPS, input: 'date' },
  { value: 'start_date', label: 'Start date', ops: DATE_OPS, input: 'date' },
  { value: 'milestone', label: 'Milestone', ops: [{ value: '=', label: 'is' }], options: () => [{ value: 1, label: 'Yes' }, { value: 0, label: 'No' }] },
  { value: 'created_by', label: 'Created by', ops: [{ value: '=', label: 'is' }, { value: '!=', label: 'is not' }], options: members },
]
const attr = (row) => ATTRS.find((a) => a.value === row.attribute) || ATTRS[0]

const rows = ref([])
watch(
  () => props.modelValue,
  (filters) => (rows.value = filters.map(([attribute, operator, value]) => ({ attribute, operator, value }))),
  { immediate: true },
)

function resetRow(row) {
  row.operator = attr(row).ops[0].value
  row.value = attr(row).multiple ? [] : null
}

function addRow() {
  const row = { attribute: 'state' }
  resetRow(row)
  rows.value.push(row)
}

function valueLabel(row) {
  const options = attr(row).options?.() || []
  const values = [].concat(row.value ?? [])
  return values.map((v) => options.find((o) => o.value === v)?.label || memberName(v)).join(', ')
}

function apply() {
  const filters = rows.value
    .filter((r) => r.value !== null && r.value !== '' && !(Array.isArray(r.value) && !r.value.length))
    .map((r) => {
      let value = r.value
      // single-choice attributes use = / != on the server
      if (!attr(r).multiple && Array.isArray(value)) value = value[0]
      let operator = r.operator
      if (!attr(r).multiple && operator === 'in') operator = '='
      if (!attr(r).multiple && operator === 'not in') operator = '!='
      return [r.attribute, operator, value]
    })
  emit('update:modelValue', filters)
}
</script>

<style scoped>
.ctl {
  @apply h-7 rounded border-0 bg-surface-gray-2 px-2 py-0 text-sm text-ink-gray-8 focus:ring-1 focus:ring-outline-gray-3;
}
</style>
