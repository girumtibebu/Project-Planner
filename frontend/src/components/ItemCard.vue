<template>
  <!-- One work item as a card; `fields` decides what it shows. `compact` is one line for calendar and timeline. -->
  <div v-if="compact" class="flex min-w-0 items-center gap-1 overflow-hidden whitespace-nowrap text-xs leading-5">
    <StateIcon v-if="has('state')" :state="stateOf(item)" :size="12" />
    <span v-if="has('type')" :class="typeIcon" class="size-3 shrink-0" :style="{ color: typeIndex[item.type]?.ep_color }" />
    <span v-if="has('time') && timeLabel" class="shrink-0 opacity-70">{{ timeLabel }}</span>
    <span v-if="has('id')" class="shrink-0 opacity-70">{{ itemId(ctx.project, item) }}</span>
    <span class="truncate font-medium">{{ item.subject }}</span>
    <span v-if="has('priority') && item.priority" :class="PRIORITY_ICON[item.priority]" class="size-3 shrink-0" />
    <Avatars v-if="has('assignees') && item.assignees.length" :users="item.assignees" :max="2" class="ml-auto shrink-0" />
  </div>

  <div v-else class="flex flex-col gap-1.5">
    <div v-if="has('id') || has('type') || item.is_milestone" class="flex items-center gap-1.5 text-xs text-ink-gray-5">
      <span v-if="has('type')" :class="typeIcon" class="size-3.5" :style="{ color: typeIndex[item.type]?.ep_color }" />
      <span v-if="has('id')">{{ itemId(ctx.project, item) }}</span>
      <span v-if="item.is_milestone" class="lucide-diamond size-3 text-ink-amber-3" title="Milestone" />
      <span v-if="has('type') && item.type" class="truncate">{{ item.type }}</span>
    </div>
    <div class="line-clamp-3 text-sm text-ink-gray-8">{{ item.subject }}</div>
    <div v-if="has('labels') && item.labels.length" class="flex flex-wrap gap-1">
      <span v-for="label in item.labels" :key="label" class="rounded-full border border-outline-gray-2 px-2 text-xs text-ink-gray-6">{{ label }}</span>
    </div>
    <div v-if="chips.length" class="flex flex-wrap gap-x-2 gap-y-0.5 text-xs text-ink-gray-5">
      <span v-for="chip in chips" :key="chip.key" class="inline-flex items-center gap-1" :title="chip.title">
        <span v-if="chip.icon" :class="chip.icon" class="size-3" :style="{ color: chip.color }" />{{ chip.text }}
      </span>
    </div>
    <ItemProps v-if="interactive.length" :item="item" :fields="interactive" @save="(d) => emit('save', d)" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import Avatars from './Avatars.vue'
import ItemProps from './ItemProps.vue'
import StateIcon from './StateIcon.vue'
import { ctx, groupIndex, propertiesOf, stateOf, typeIndex } from '../store'
import { PRIORITY_ICON, formatDate, itemId, toDate } from '../utils'

const props = defineProps({
  item: { type: Object, required: true },
  fields: { type: Array, default: () => [] },
  compact: Boolean,
  hide: { type: Array, default: () => [] }, // fields the layout already shows (e.g. the column's state)
})
const emit = defineEmits(['save'])

const has = (field) => props.fields.includes(field) && !props.hide.includes(field)
const typeIcon = computed(() => typeIndex.value[props.item.type]?.ep_icon || 'lucide-square-check')

const timeLabel = computed(() => {
  const d = toDate(props.item.exp_start_date || props.item.exp_end_date)
  if (!d || (d.getHours() === 0 && d.getMinutes() === 0)) return ''
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
})

// editable chips: state, priority, assignees, due date
const interactive = computed(() => ['state', 'priority', 'assignees', 'due_date'].filter(has))

// read-only chips
const chips = computed(() => {
  const out = []
  const item = props.item
  if (has('start_date') && item.exp_start_date) out.push({ key: 'start', icon: 'lucide-calendar-clock', text: formatDate(item.exp_start_date), title: 'Start date' })
  if (has('time') && timeLabel.value) out.push({ key: 'time', icon: 'lucide-clock', text: timeLabel.value })
  if (has('group') && item.ep_action_category) {
    const g = groupIndex.value[item.ep_action_category]
    out.push({ key: 'group', icon: 'lucide-boxes', text: g?.title || item.ep_action_category, color: g?.color })
  }
  if (has('estimate') && item.expected_time) out.push({ key: 'est', icon: 'lucide-hourglass', text: `${item.expected_time}h` })
  if (has('sub_items') && item.is_group) out.push({ key: 'sub', icon: 'lucide-list-tree', text: 'has sub-items' })
  if (has('properties')) {
    for (const p of propertiesOf(item.type)) {
      const v = item[p.fieldname]
      if (v !== null && v !== undefined && v !== '' && v !== 0) out.push({ key: p.fieldname, text: `${p.label}: ${p.property_type === 'Checkbox' ? 'yes' : v}` })
    }
  }
  return out
})
</script>
