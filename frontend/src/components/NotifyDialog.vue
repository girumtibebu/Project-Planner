<template>
  <!-- Send the at-a-glance summary to n8n (Discord / Telegram), with an optional note -->
  <Dialog :model-value="modelValue" title="Notify team" :options="{ size: 'xl' }" @update:model-value="(v) => emit('update:modelValue', v)">
    <div class="flex flex-col gap-3">
      <FormControl v-model="note" type="textarea" label="Note (optional)" placeholder="What changed, e.g. Load-in moved to 7am" @change="preview" />
      <div>
        <div class="mb-1.5 text-xs text-ink-gray-5">Message</div>
        <pre class="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-surface-gray-1 p-3 font-sans text-sm text-ink-gray-8">{{ text || '…' }}</pre>
      </div>
    </div>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button label="Cancel" @click="emit('update:modelValue', false)" />
        <Button variant="solid" icon-left="lucide-send" label="Send" :loading="sending" @click="send" />
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
const note = ref('')
const text = ref('')
const sending = ref(false)

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    note.value = ''
    preview()
  },
)

async function preview() {
  try {
    text.value = (await api.notifyTeam(ctx.project.name, note.value, true)).text
  } catch (err) {
    fail(err)
  }
}

async function send() {
  sending.value = true
  try {
    await api.notifyTeam(ctx.project.name, note.value, false)
    emit('update:modelValue', false)
    toast.success('Sent to the team')
  } catch (err) {
    fail(err)
  } finally {
    sending.value = false
  }
}
</script>
