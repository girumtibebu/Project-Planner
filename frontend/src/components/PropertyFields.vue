<template>
  <!-- The work item type's own properties (Planner Property → Task Custom Field) -->
  <div v-for="prop in props_" :key="prop.name" class="flex min-h-8 items-center gap-2">
    <div class="w-24 shrink-0 truncate text-sm text-ink-gray-5" :title="prop.label">
      {{ prop.label }}<span v-if="prop.is_required" class="text-ink-red-4">*</span>
    </div>
    <div class="min-w-0 flex-1">
      <Picker
        v-if="prop.property_type === 'Dropdown'"
        :model-value="item[prop.fieldname]"
        :options="options(prop)"
        clearable
        :label="prop.label"
        @change="(v) => set(prop, v)"
      >
        <template #default="{ toggle }">
          <button class="field" :disabled="disabled" @click.stop="toggle">{{ item[prop.fieldname] || 'Empty' }}</button>
        </template>
      </Picker>
      <Picker
        v-else-if="prop.property_type === 'Member'"
        :model-value="item[prop.fieldname]"
        :options="memberOptions"
        clearable
        :label="prop.label"
        @change="(v) => set(prop, v)"
      >
        <template #default="{ toggle }">
          <button class="field" :disabled="disabled" @click.stop="toggle">{{ item[prop.fieldname] ? memberName(item[prop.fieldname]) : 'Empty' }}</button>
        </template>
      </Picker>
      <Checkbox
        v-else-if="prop.property_type === 'Checkbox'"
        :model-value="Boolean(item[prop.fieldname])"
        :disabled="disabled"
        @update:model-value="(v) => set(prop, v ? 1 : 0)"
      />
      <input
        v-else
        :type="INPUT_TYPE[prop.property_type] || 'text'"
        class="field w-full border-0 bg-transparent"
        :value="item[prop.fieldname] ?? ''"
        :disabled="disabled"
        placeholder="Empty"
        @change="(e) => set(prop, e.target.value || null)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Checkbox } from 'frappe-ui'
import Picker from './Picker.vue'
import { ctx, memberName, propertiesOf } from '../store'

const props = defineProps({ item: { type: Object, required: true }, disabled: Boolean })
const emit = defineEmits(['change'])
const INPUT_TYPE = { Number: 'number', Date: 'date', URL: 'url' }

const props_ = computed(() => propertiesOf(props.item.type))
const memberOptions = computed(() => ctx.members.map((m) => ({ value: m.name, label: m.full_name || m.name })))
const options = (prop) => (prop.options || '').split('\n').filter(Boolean).map((o) => ({ value: o, label: o }))
const set = (prop, value) => emit('change', { [prop.fieldname]: prop.property_type === 'Number' && value != null ? Number(value) : value })
</script>

<style scoped>
.field {
  @apply inline-flex h-7 items-center rounded px-1.5 text-left text-sm text-ink-gray-7 hover:bg-surface-gray-2 focus:bg-surface-gray-2 focus:ring-0 disabled:hover:bg-transparent;
}
</style>
