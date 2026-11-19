<template>
  <!-- New work item; views open it with values already filled in (dates, state, group, assignee…) -->
  <Dialog :model-value="modelValue" title="New work item" :options="{ size: 'xl' }" @update:model-value="(v) => emit('update:modelValue', v)">
    <div class="flex flex-col gap-3">
      <FormControl ref="titleInput" v-model="draft.subject" label="Title" placeholder="What needs doing?" autofocus @keydown.enter="create" />
      <div class="grid grid-cols-2 gap-3">
        <FormControl v-model="draft.ep_state" type="select" label="State" :options="stateOptions" />
        <FormControl v-model="draft.type" type="select" label="Type" :options="[{ value: '', label: 'No type' }, ...typeOptions]" />
        <FormControl v-model="draft.priority" type="select" label="Priority" :options="priorityOptions" />
        <FormControl v-model="draft.ep_action_category" type="select" label="Category" :options="[{ value: '', label: 'No category' }, ...groupOptions]" />
        <FormControl v-model="draft.start" type="datetime-local" label="Start" />
        <FormControl v-model="draft.end" type="datetime-local" label="Due" />
      </div>
      <div>
        <div class="mb-1.5 text-xs text-ink-gray-5">Assignees</div>
        <Picker v-model="draft.assignees" :options="memberOptions" multiple label="Members">
          <template #default="{ toggle }">
            <button class="flex h-8 w-full items-center gap-2 rounded bg-surface-gray-2 px-2 text-left text-sm" @click="toggle">
              <Avatars :users="draft.assignees" placeholder />
              <span v-if="!draft.assignees.length" class="text-ink-gray-4">Nobody yet</span>
            </button>
          </template>
        </Picker>
      </div>
    </div>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button label="Cancel" @click="emit('update:modelValue', false)" />
        <Button variant="solid" label="Create" :loading="creating" :disabled="!draft.subject?.trim()" @click="create" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { Button, Dialog, FormControl } from 'frappe-ui'
import Avatars from './Avatars.vue'
import Picker from './Picker.vue'
import { api } from '../api'
import { ctx, fail } from '../store'
import { PRIORITIES } from '../utils'

const props = defineProps({ modelValue: Boolean, defaults: { type: Object, default: () => ({}) } })
const emit = defineEmits(['update:modelValue', 'created'])

const creating = ref(false)
const draft = reactive({ subject: '', ep_state: '', type: '', priority: 'Medium', ep_action_category: '', start: '', end: '', assignees: [] })

// "2026-11-06 09:00:00" <-> "2026-11-06T09:00"
const toInput = (v) => (v ? String(v).replace(' ', 'T').slice(0, 16) : '')
const fromInput = (v) => (v ? `${v.replace('T', ' ')}:00`.slice(0, 19) : null)

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    const d = props.defaults
    const def = ctx.states.find((s) => s.is_default) || ctx.states[0]
    Object.assign(draft, {
      subject: '',
      ep_state: d.ep_state || def?.name,
      type: d.type || '',
      priority: d.priority || 'Medium',
      ep_action_category: d.ep_action_category || '',
      start: toInput(d.exp_start_date),
      end: toInput(d.exp_end_date),
      assignees: [...(d.assignees || [])],
    })
  },
)

const stateOptions = computed(() => ctx.states.map((s) => ({ value: s.name, label: s.title })))
const typeOptions = computed(() => ctx.types.map((t) => ({ value: t.name, label: t.name })))
const groupOptions = computed(() => ctx.groups.map((g) => ({ value: g.name, label: g.title })))
const memberOptions = computed(() => ctx.members.map((m) => ({ value: m.name, label: m.full_name || m.name, image: m.user_image })))
const priorityOptions = PRIORITIES.map((p) => ({ value: p, label: p }))

async function create() {
  const subject = draft.subject?.trim()
  if (!subject || creating.value) return
  creating.value = true
  try {
    const data = {
      subject,
      ep_state: draft.ep_state,
      priority: draft.priority,
      assignees: draft.assignees,
      exp_start_date: fromInput(draft.start),
      exp_end_date: fromInput(draft.end),
    }
    if (draft.type) data.type = draft.type
    if (draft.ep_action_category) data.ep_action_category = draft.ep_action_category
    for (const [k, v] of Object.entries(props.defaults)) if (!(k in data) && !k.startsWith('exp_')) data[k] = v
    if (!data.exp_start_date) delete data.exp_start_date
    if (!data.exp_end_date) delete data.exp_end_date
    if ((data.ep_state || '').startsWith('status:')) data.status = data.ep_state.split(':')[1]
    if ((data.ep_state || '').startsWith('status:')) delete data.ep_state
    const item = await api.createItem(ctx.project.name, data)
    emit('created', item)
    emit('update:modelValue', false)
  } catch (err) {
    fail(err)
  } finally {
    creating.value = false
  }
}
</script>
