<template>
  <Dialog :model-value="confirmState.open" :options="{ size: 'sm' }" @update:model-value="(v) => !v && settle(false)">
    <template #body-title>
      <div class="flex items-center gap-2">
        <span class="flex size-8 items-center justify-center rounded-full" :class="confirmState.danger ? 'bg-surface-red-2' : 'bg-surface-gray-2'">
          <span :class="confirmState.danger ? 'lucide-triangle-alert text-ink-red-5' : 'lucide-circle-help text-ink-gray-6'" class="size-4" />
        </span>
        <h3 class="text-lg font-semibold text-ink-gray-9">{{ confirmState.title }}</h3>
      </div>
    </template>
    <template #body-content>
      <p class="text-sm leading-relaxed text-ink-gray-6">{{ confirmState.message }}</p>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button label="Cancel" @click="settle(false)" />
        <Button variant="solid" :theme="confirmState.danger ? 'red' : 'gray'" :label="confirmState.action" @click="settle(true)" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { Button, Dialog } from 'frappe-ui'
import { confirmState, settle } from '../confirm'
</script>
