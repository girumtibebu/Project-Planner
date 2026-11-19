<template>
  <!-- Keep this project's board (categories, checklist, pages, BOQ lines, views, sidebar order) as a template -->
  <Dialog :model-value="modelValue" title="Save as template" @update:model-value="(v) => emit('update:modelValue', v)">
    <div class="flex flex-col gap-3">
      <FormControl v-model="title" label="Title" placeholder="e.g. Corporate launch, full production" />
      <FormControl v-model="description" type="textarea" label="Description" placeholder="When to use it. Shown on the template card." />
      <p class="text-xs text-ink-gray-5">
        Keeps categories, work items as a checklist (no dates or people), pages, BOQ lines (warehouse columns empty), views and the sidebar order.
      </p>
    </div>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button label="Cancel" @click="emit('update:modelValue', false)" />
        <Button variant="solid" label="Save template" :loading="saving" :disabled="!title.trim()" @click="save" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Button, Dialog, FormControl, toast } from 'frappe-ui'
import { api } from '../api'
import { ctx, fail } from '../store'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])
const title = ref('')
const description = ref('')
const saving = ref(false)

watch(
  () => props.modelValue,
  (open) => open && ((title.value = ''), (description.value = '')),
)

async function save() {
  saving.value = true
  try {
    await api.saveAsTemplate(ctx.project.name, title.value.trim(), description.value.trim())
    emit('update:modelValue', false)
    toast.success('Template saved')
  } catch (err) {
    fail(err)
  } finally {
    saving.value = false
  }
}
</script>
