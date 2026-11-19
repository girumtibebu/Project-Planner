<template>
  <!-- A group's label; for a category it also renames, recolours and deletes it in place -->
  <span v-if="!editable" class="min-w-0"><GroupLabel :grouper="grouper" :k="k" :count="count" /></span>
  <span v-else class="group/cat flex min-w-0 items-center gap-1.5">
    <ColorPicker :model-value="cat.color" :label="cat.title" @change="(color) => updateCategory(k, { color })">
      <template #default="{ toggle }">
        <button class="flex size-6 items-center justify-center rounded hover:bg-surface-gray-2" title="Colour" @click.stop="toggle">
          <span class="lucide-boxes size-4" :style="{ color: cat.color }" />
        </button>
      </template>
    </ColorPicker>
    <input
      v-if="renaming"
      ref="input"
      v-model="title"
      class="h-7 w-48 rounded-md border-0 bg-surface-gray-2 px-2 text-sm font-medium focus:ring-1 focus:ring-outline-gray-3"
      @keydown.enter="rename"
      @keydown.esc="renaming = false"
      @blur="rename"
    />
    <button v-else class="truncate text-sm font-medium text-ink-gray-8" title="Rename" @dblclick="startRename">{{ cat.title }}</button>
    <span class="text-sm text-ink-gray-4">{{ count }}</span>
    <Dropdown :options="menu">
      <button class="rounded p-0.5 text-ink-gray-4 opacity-0 hover:bg-surface-gray-2 hover:text-ink-gray-8 group-hover/cat:opacity-100" title="Category options">
        <span class="lucide-ellipsis block size-4" />
      </button>
    </Dropdown>
  </span>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { Dropdown } from 'frappe-ui'
import ColorPicker from './ColorPicker.vue'
import GroupLabel from './GroupLabel.vue'
import { ctx, deleteCategory, groupIndex, updateCategory } from '../store'

const props = defineProps({ grouper: Object, groupBy: String, k: [String, Number], count: Number })
const cat = computed(() => groupIndex.value[props.k])
const editable = computed(() => props.groupBy === 'group' && cat.value && ctx.can.write)

const renaming = ref(false)
const title = ref('')
const input = ref(null)
async function startRename() {
  title.value = cat.value.title
  renaming.value = true
  await nextTick()
  input.value?.select()
}
function rename() {
  if (!renaming.value) return
  renaming.value = false
  const value = title.value.trim()
  if (value && value !== cat.value.title) updateCategory(props.k, { title: value })
}

const menu = [
  { label: 'Rename', icon: 'lucide-pencil', onClick: startRename },
  { label: 'Delete category', icon: 'lucide-trash-2', theme: 'red', onClick: () => deleteCategory(props.k) },
]
</script>
