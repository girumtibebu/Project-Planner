<template>
  <!-- A project made in the desk (e.g. from a Sales Order) opens here for the first time: pick its board -->
  <Dialog :model-value="modelValue" :title="`Set up ${ctx.project?.project_name || 'this project'}`" :options="{ size: '3xl' }" @update:model-value="(v) => emit('update:modelValue', v)">
    <div class="flex flex-col gap-3">
      <p class="text-sm text-ink-gray-6">This project was made in the desk. Start it from a saved board, or keep it as it is.</p>
      <TemplateCards v-if="templates" v-model="template" :templates="templates" />
      <div v-else class="flex h-24 items-center justify-center"><LoadingIndicator class="size-5" /></div>
    </div>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button label="Keep as it is" :loading="busy === 'keep'" @click="setup(null)" />
        <Button variant="solid" :label="template ? 'Use this template' : 'Start blank'" :loading="busy === 'use'" @click="setup(template || null, 'use')" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Button, Dialog, LoadingIndicator } from 'frappe-ui'
import TemplateCards from './TemplateCards.vue'
import { api } from '../api'
import { ctx, fail, loadProject } from '../store'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])
const templates = ref(null)
const template = ref('')
const busy = ref('')

watch(
  () => props.modelValue,
  async (open) => {
    if (!open || templates.value) return
    try {
      templates.value = (await api.newProjectOptions()).templates
      template.value = templates.value[0]?.name || ''
    } catch (err) {
      fail(err)
    }
  },
  { immediate: true },
)

async function setup(name, mode = 'keep') {
  busy.value = mode
  try {
    await api.setupProject(ctx.project.name, name, mode === 'use' && !name)
    emit('update:modelValue', false)
    await loadProject(ctx.project.name)
  } catch (err) {
    fail(err)
  } finally {
    busy.value = ''
  }
}
</script>
