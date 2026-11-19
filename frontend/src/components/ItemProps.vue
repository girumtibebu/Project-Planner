<template>
  <!-- Compact property controls for one work item; used in list rows, cards and the detail panel -->
  <div class="flex items-center" :class="vertical ? 'flex-col items-stretch gap-1' : 'gap-1'">
    <Row v-if="show('state')" label="State" :vertical="vertical">
      <Picker :model-value="item.ep_state || `status:${item.status}`" :options="stateOptions" label="State" @change="(v) => save({ ep_state: v })">
        <template #default="{ toggle }">
          <button class="chip" :disabled="!canWrite" @click.stop="toggle">
            <StateIcon :state="state" />
            <span v-if="vertical || labels">{{ state.title }}</span>
          </button>
        </template>
        <template #option="{ option }"><StateIcon :state="stateIndex[option.value]" /></template>
      </Picker>
    </Row>

    <Row v-if="show('priority')" label="Priority" :vertical="vertical">
      <Picker :model-value="item.priority" :options="priorityOptions" label="Priority" @change="(v) => save({ priority: v })">
        <template #default="{ toggle }">
          <button class="chip" :disabled="!canWrite" @click.stop="toggle">
            <span :class="[PRIORITY_ICON[item.priority] || 'lucide-minus', PRIORITY_COLOR[item.priority]]" class="size-4" />
            <span v-if="vertical || labels">{{ item.priority || 'No priority' }}</span>
          </button>
        </template>
      </Picker>
    </Row>

    <Row v-if="show('assignees')" label="Assignees" :vertical="vertical">
      <Picker :model-value="item.assignees" :options="memberOptions" multiple label="Members" @change="(v) => save({ assignees: v })">
        <template #default="{ toggle }">
          <button class="chip" :disabled="!canWrite" @click.stop="toggle">
            <Avatars :users="item.assignees" placeholder />
            <span v-if="vertical && !item.assignees.length" class="text-ink-gray-4">Unassigned</span>
          </button>
        </template>
        <template #option="{ option }"><Avatar :label="option.label" :image="option.image" size="xs" /></template>
      </Picker>
    </Row>

    <Row v-if="show('due_date')" label="Due date" :vertical="vertical">
      <DateChip :value="item.exp_end_date" icon="lucide-calendar-check-2" :overdue="isOverdue(item)" :disabled="!canWrite" placeholder="Due date" @change="(v) => save({ exp_end_date: v })" />
    </Row>

    <template v-if="vertical">
      <Row label="Start date" vertical>
        <DateChip :value="item.exp_start_date" icon="lucide-calendar-clock" :disabled="!canWrite" placeholder="Start date" @change="(v) => save({ exp_start_date: v })" />
      </Row>
      <Row label="Type" vertical>
        <Picker :model-value="item.type" :options="typeOptions" clearable label="Type" @change="(v) => save({ type: v })">
          <template #default="{ toggle }">
            <button class="chip" :disabled="!canWrite" @click.stop="toggle">
              <span :class="typeIndex[item.type]?.ep_icon || 'lucide-square-check'" class="size-4" :style="{ color: typeIndex[item.type]?.ep_color }" />
              <span>{{ item.type || 'No type' }}</span>
            </button>
          </template>
        </Picker>
      </Row>
      <Row label="Category" vertical>
        <Picker
          :model-value="item.ep_action_category"
          :options="groupOptions"
          clearable
          creatable
          label="Category"
          @change="(v) => save({ ep_action_category: v })"
          @create="async (title) => save({ ep_action_category: await createCategory(title) })"
        >
          <template #default="{ toggle }">
            <button class="chip" :disabled="!canWrite" @click.stop="toggle">
              <span class="lucide-boxes size-4" :style="{ color: groupIndex[item.ep_action_category]?.color }" />
              <span>{{ groupIndex[item.ep_action_category]?.title || 'No category' }}</span>
            </button>
          </template>
        </Picker>
      </Row>
      <Row label="Labels" vertical>
        <LabelEditor :labels="item.labels" :disabled="!canWrite" @change="(v) => save({ labels: v })" />
      </Row>
      <Row label="Estimate" vertical>
        <input
          type="number"
          min="0"
          class="chip w-24 border-0 bg-transparent"
          :value="item.expected_time || ''"
          :disabled="!canWrite"
          placeholder="hours"
          @change="(e) => save({ expected_time: Number(e.target.value) || 0 })"
        />
      </Row>
      <Row label="Milestone" vertical>
        <Checkbox :model-value="Boolean(item.is_milestone)" :disabled="!canWrite" @update:model-value="(v) => save({ is_milestone: v ? 1 : 0 })" />
      </Row>
      <PropertyFields :item="item" :disabled="!canWrite" @change="save" />
    </template>
  </div>
</template>

<script setup>
import { computed, defineComponent, h } from 'vue'
import { Avatar, Checkbox } from 'frappe-ui'
import Avatars from './Avatars.vue'
import DateChip from './DateChip.vue'
import LabelEditor from './LabelEditor.vue'
import Picker from './Picker.vue'
import PropertyFields from './PropertyFields.vue'
import StateIcon from './StateIcon.vue'
import { createCategory, ctx, groupIndex, stateIndex, stateOf, typeIndex } from '../store'
import { PRIORITIES, PRIORITY_COLOR, PRIORITY_ICON, isOverdue } from '../utils'

const props = defineProps({
  item: { type: Object, required: true },
  fields: { type: Array, default: () => ['state', 'priority', 'assignees', 'due_date'] },
  vertical: { type: Boolean, default: false },
  labels: { type: Boolean, default: false },
})
const emit = defineEmits(['save'])

const Row = defineComponent({
  props: { label: String, vertical: Boolean },
  setup(p, { slots }) {
    return () =>
      p.vertical
        ? h('div', { class: 'flex min-h-8 items-center gap-2' }, [
            h('div', { class: 'w-24 shrink-0 text-sm text-ink-gray-5' }, p.label),
            h('div', { class: 'min-w-0 flex-1' }, slots.default?.()),
          ])
        : slots.default?.()
  },
})

const canWrite = computed(() => ctx.can.write)
const state = computed(() => stateOf(props.item))
const show = (field) => props.vertical || props.fields.includes(field)
const save = (data) => emit('save', data)

const stateOptions = computed(() => ctx.states.map((s) => ({ value: s.name, label: s.title })))
const priorityOptions = PRIORITIES.map((p) => ({ value: p, label: p, iconClass: `${PRIORITY_ICON[p]} ${PRIORITY_COLOR[p]}` }))
const memberOptions = computed(() => ctx.members.map((m) => ({ value: m.name, label: m.full_name || m.name, image: m.user_image })))
const typeOptions = computed(() => ctx.types.map((t) => ({ value: t.name, label: t.name, iconClass: t.ep_icon || 'lucide-square-check', color: t.ep_color })))
const groupOptions = computed(() => ctx.groups.map((g) => ({ value: g.name, label: g.title, iconClass: 'lucide-boxes', color: g.color })))
</script>

<style scoped>
.chip {
  @apply inline-flex h-7 items-center gap-1.5 rounded-md px-1.5 text-sm text-ink-gray-7 hover:bg-surface-gray-2 disabled:cursor-default disabled:hover:bg-transparent;
}
</style>
