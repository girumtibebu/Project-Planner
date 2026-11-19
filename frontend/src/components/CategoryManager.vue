<template>
  <!-- The project's categories, managed from Work items: add, rename, recolour, delete -->
  <Popover align="end">
    <template #trigger>
      <Button size="sm" icon-left="lucide-boxes" :label="`Categories${ctx.groups.length ? ` ${ctx.groups.length}` : ''}`" />
    </template>
    <template #default>
      <div class="w-80 p-2" @click.stop>
        <div class="mb-1 flex items-center justify-between px-1">
          <span class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">Categories</span>
          <button v-if="ctx.groups.length" class="text-xs text-ink-gray-5 hover:text-ink-gray-8 hover:underline" @click="emit('group-by')">Group list by category</button>
        </div>
        <p v-if="!ctx.groups.length" class="px-1 pb-2 text-sm text-ink-gray-5">
          Sort work items by area, e.g. Pre-production, Logistics, On site. Each item is in one.
        </p>
        <div class="max-h-72 overflow-y-auto">
          <div v-for="cat in ctx.groups" :key="cat.name" class="group/cat flex items-center gap-1 rounded-md pr-1 hover:bg-surface-gray-1">
            <ColorPicker :model-value="cat.color" :label="cat.title" @change="(color) => updateCategory(cat.name, { color })">
              <template #default>
                <button class="flex size-7 shrink-0 items-center justify-center rounded" :disabled="!ctx.can.write" title="Colour">
                  <span class="lucide-boxes size-4" :style="{ color: cat.color }" />
                </button>
              </template>
            </ColorPicker>
            <input
              :value="cat.title"
              :disabled="!ctx.can.write"
              class="h-7 min-w-0 flex-1 rounded border-0 bg-transparent px-1 text-sm focus:bg-surface-base focus:ring-1 focus:ring-outline-gray-3"
              @keydown.enter="$event.target.blur()"
              @change="(e) => rename(cat, e.target)"
            />
            <span class="w-6 text-right text-xs text-ink-gray-4" title="Work items">{{ counts[cat.name] || 0 }}</span>
            <button
              v-if="ctx.can.write"
              class="flex size-6 items-center justify-center rounded text-ink-gray-4 opacity-0 hover:bg-surface-gray-3 hover:text-ink-red-5 group-hover/cat:opacity-100"
              title="Delete category"
              @click="deleteCategory(cat.name)"
            >
              <span class="lucide-trash-2 size-3.5" />
            </button>
          </div>
        </div>
        <div v-if="ctx.can.write" class="mt-1 border-t border-outline-gray-1 pt-2">
          <input
            v-model="title"
            class="h-8 w-full rounded-md border-0 bg-surface-gray-2 px-2 text-sm placeholder:text-ink-gray-4 focus:ring-1 focus:ring-outline-gray-3"
            placeholder="+ New category, then Enter"
            @keydown.enter="add"
          />
        </div>
      </div>
    </template>
  </Popover>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Button, Popover } from 'frappe-ui'
import ColorPicker from './ColorPicker.vue'
import { createCategory, ctx, deleteCategory, updateCategory } from '../store'

const props = defineProps({ items: { type: Array, default: () => [] } })
const emit = defineEmits(['group-by'])
const title = ref('')

const counts = computed(() => {
  const out = {}
  for (const item of props.items) if (item.ep_action_category) out[item.ep_action_category] = (out[item.ep_action_category] || 0) + 1
  return out
})

async function add() {
  const value = title.value.trim()
  if (value && (await createCategory(value))) title.value = ''
}
function rename(cat, input) {
  const value = input.value.trim()
  if (!value) input.value = cat.title
  else if (value !== cat.title) updateCategory(cat.name, { title: value })
}
</script>
