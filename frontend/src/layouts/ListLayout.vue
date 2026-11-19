<template>
  <div class="h-full overflow-y-auto px-3 pb-6">
    <section v-for="[key, rows] in groups" :key="key" class="mt-3">
      <header class="sticky top-0 z-10 flex h-9 items-center gap-2 bg-surface-base/95 px-2 backdrop-blur">
        <button class="text-ink-gray-4 hover:text-ink-gray-7" @click="toggle(key)">
          <span :class="collapsed.has(key) ? 'lucide-chevron-right' : 'lucide-chevron-down'" class="size-4" />
        </button>
        <GroupHeader :grouper="g" :group-by="groupBy" :k="key" :count="rows.length" />
      </header>
      <template v-if="!collapsed.has(key)">
        <div
          v-for="item in rows"
          :key="item.name"
          data-row
          class="group relative flex h-10 cursor-pointer items-center gap-2.5 rounded-lg pl-0.5 pr-2 hover:bg-surface-gray-1"
          :class="[selected.includes(item.name) && 'bg-surface-gray-2', dragging?.name === item.name && 'opacity-40']"
          @click="emit('open', item)"
          @dragover="(e) => canDrop(key, item) && (e.preventDefault(), (over = item.name))"
          @dragleave="over === item.name && (over = null)"
          @drop.prevent="drop(item)"
        >
          <!-- where the row lands -->
          <div v-if="over === item.name" class="pointer-events-none absolute inset-x-2 z-10 h-0.5 rounded bg-surface-gray-7" :class="dropBelow(item) ? '-bottom-px' : '-top-px'" />
          <span
            :draggable="ctx.can.write"
            class="flex h-6 w-3.5 shrink-0 items-center justify-center rounded text-ink-gray-4"
            :class="ctx.can.write ? 'cursor-grab opacity-0 hover:bg-surface-gray-3 hover:text-ink-gray-7 active:cursor-grabbing group-hover:opacity-100' : 'invisible'"
            title="Drag to reorder; sub-items move with their parent"
            @click.stop
            @dragstart="(e) => startDrag(key, item, e)"
            @dragend="dragging = over = null"
          ><span class="lucide-grip-vertical size-3.5" /></span>
          <Checkbox
            v-if="ctx.can.write"
            class="opacity-0 group-hover:opacity-100"
            :class="selected.includes(item.name) && 'opacity-100'"
            :model-value="selected.includes(item.name)"
            @click.stop
            @update:model-value="(v) => emit('select', item.name, v)"
          />
          <span v-if="show('id')" class="w-16 shrink-0 text-xs text-ink-gray-5">{{ itemId(ctx.project, item) }}</span>
          <span v-if="depth.get(item.name)" class="shrink-0" :style="{ width: `${(depth.get(item.name) - 1) * 18}px` }" />
          <span v-if="item.parent_task" class="lucide-corner-down-right size-3.5 shrink-0 text-ink-gray-4" title="Sub-item" />
          <span
            v-if="show('type')"
            :class="typeIndex[item.type]?.ep_icon || 'lucide-square-check'"
            class="size-4 shrink-0"
            :style="{ color: typeIndex[item.type]?.ep_color || 'var(--ink-gray-5)' }"
          />
          <span class="min-w-0 flex-1 truncate text-sm text-ink-gray-8">{{ item.subject }}</span>
          <span v-if="item.is_milestone" class="lucide-diamond size-3.5 text-ink-amber-3" title="Milestone" />
          <template v-if="show('labels')">
            <span
              v-for="label in item.labels.slice(0, 2)"
              :key="label"
              class="hidden rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-6 lg:inline"
            >{{ label }}</span>
          </template>
          <span v-if="show('group') && item.ep_action_category" class="hidden items-center gap-1 text-xs text-ink-gray-5 md:inline-flex">
            <span class="size-2 rounded-full" :style="{ background: groupIndex[item.ep_action_category]?.color || '#9CA3AF' }" />
            {{ groupIndex[item.ep_action_category]?.title }}
          </span>
          <span v-if="show('estimate') && item.expected_time" class="text-xs text-ink-gray-5">{{ item.expected_time }}h</span>
          <span v-if="show('start_date') && item.exp_start_date" class="text-xs text-ink-gray-5">{{ formatDate(item.exp_start_date) }} →</span>
          <ItemProps :item="item" :fields="propFields" @save="(data) => emit('save', item, data)" />
        </div>
        <div class="px-1 pt-0.5">
          <QuickAdd :defaults="g.patch(key, {}, null) || {}" @created="(item) => emit('created', item)" />
        </div>
      </template>
    </section>
    <div v-if="groupBy === 'group' && ctx.can.write" class="mt-4 px-2">
      <input
        v-model="newGroup"
        class="h-8 w-72 rounded-md border border-dashed border-outline-gray-2 bg-transparent px-2 text-sm placeholder:text-ink-gray-4 focus:border-outline-gray-4 focus:outline-none"
        placeholder="+ New category, e.g. Pre-production"
        @keydown.enter="addGroup"
      />
    </div>
    <div v-else-if="!items.length" class="p-10 text-center text-sm text-ink-gray-5">No work items match this view.</div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { Checkbox } from 'frappe-ui'
import GroupHeader from '../components/GroupHeader.vue'
import ItemProps from '../components/ItemProps.vue'
import QuickAdd from '../components/QuickAdd.vue'
import { grouper } from '../grouping'
import { createCategory, ctx, groupIndex, typeIndex } from '../store'
import { formatDate, groupItems, itemId, treeOrder } from '../utils'

const props = defineProps({
  items: { type: Array, default: () => [] },
  groupBy: { type: String, default: 'state' },
  selected: { type: Array, default: () => [] },
  cardFields: { type: Array, default: () => ['id', 'type', 'state', 'priority', 'assignees', 'due_date', 'labels'] },
})
const emit = defineEmits(['open', 'save', 'created', 'select', 'reorder'])

// sub-item depth for indenting (items come in tree order from WorkItems)
const depth = computed(() => treeOrder(props.items).depth)

// drag a row among its siblings in the same group; its sub-items follow it
const dragging = ref(null) // { key, name, parent }
const over = ref(null)
function startDrag(key, item, event) {
  dragging.value = { key, name: item.name, parent: item.parent_task || '' }
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', item.subject)
  const el = event.target.closest('[data-row]')
  if (el) event.dataTransfer.setDragImage(el, 16, el.offsetHeight / 2)
}
const canDrop = (key, item) => dragging.value && dragging.value.key === key && dragging.value.parent === (item.parent_task || '') && dragging.value.name !== item.name
const order = computed(() => props.items.map((i) => i.name))
const dropBelow = (item) => order.value.indexOf(dragging.value?.name) < order.value.indexOf(item.name)
function drop(target) {
  const moved = dragging.value?.name
  dragging.value = over.value = null
  if (!moved || moved === target.name) return
  const names = [...order.value]
  const from = names.indexOf(moved)
  names.splice(from, 1)
  const to = names.indexOf(target.name)
  names.splice(from <= to ? to + 1 : to, 0, moved)
  emit('reorder', names)
}
defineOptions({ inheritAttrs: false })

const show = (field) => props.cardFields.includes(field)
const propFields = computed(() => ['state', 'priority', 'assignees', 'due_date'].filter(show))

const g = computed(() => grouper(props.groupBy))
const groups = computed(() => {
  const all = groupItems(props.items, g.value.keyOf, g.value.keys())
  // hide empty groups, but keep one so quick add stays reachable
  // categories stay visible while empty, so a new one can get its first item
  const entries = [...all.entries()].filter(([key, rows]) => rows.length || (props.groupBy === 'group' && key))
  return entries.length ? entries : [...all.entries()].slice(0, 1)
})

const newGroup = ref('')
async function addGroup() {
  const title = newGroup.value.trim()
  if (title && (await createCategory(title))) newGroup.value = ''
}

const collapsed = reactive(new Set())
const toggle = (key) => (collapsed.has(key) ? collapsed.delete(key) : collapsed.add(key))
</script>
