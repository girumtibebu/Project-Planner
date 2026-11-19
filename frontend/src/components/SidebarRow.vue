<template>
  <!-- One sidebar entry: drag grip, icon, title, lock, and a menu, all inside the row so the active style holds them -->
  <div
    class="group/row relative flex h-8 cursor-pointer select-none items-center gap-1 rounded-md pr-1 text-sm transition-colors"
    :class="[row.active ? 'bg-surface-gray-3 font-medium text-ink-gray-9' : 'text-ink-gray-7 hover:bg-surface-gray-2', dragging && 'opacity-40']"
    :style="{ paddingLeft: `${(collapsed ? 6 : 2) + (collapsed ? 0 : row.depth || 0) * 12}px` }"
    :title="collapsed ? row.label : undefined"
    @click="row.onClick ? row.onClick() : router.push(row.to)"
  >
    <!-- active marker -->
    <span v-if="row.active" class="absolute inset-y-1.5 left-0 w-[3px] rounded-full bg-surface-gray-7" />
    <span
      v-if="!collapsed"
      :draggable="canDrag"
      class="flex h-6 w-3.5 shrink-0 items-center justify-center rounded text-ink-gray-4"
      :class="canDrag ? 'cursor-grab opacity-0 hover:bg-surface-gray-4 hover:text-ink-gray-7 active:cursor-grabbing group-hover/row:opacity-100' : 'invisible'"
      title="Drag to reorder"
      @click.stop
      @dragstart="(e) => emit('dragstart', e)"
      @dragend="emit('dragend')"
    >
      <span class="lucide-grip-vertical size-3.5" />
    </span>
    <span v-if="row.emoji" class="flex size-4 shrink-0 items-center justify-center text-sm leading-none">{{ row.emoji }}</span>
    <span v-else :class="row.icon" class="size-4 shrink-0" :style="{ color: row.active ? undefined : 'var(--ink-gray-5, #6b7280)' }" />
    <template v-if="!collapsed">
      <span class="ml-1 min-w-0 flex-1 truncate">{{ row.label }}</span>
      <span v-if="row.is_locked" class="lucide-lock size-3 shrink-0 text-ink-gray-4" title="Locked: only its owner can change it" />
      <Dropdown v-if="menu.length" :options="menu" placement="right">
        <button
          class="flex size-6 shrink-0 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-4 hover:text-ink-gray-8"
          :class="row.active ? 'opacity-100' : 'opacity-0 group-hover/row:opacity-100'"
          title="Options"
          @click.stop
        >
          <span class="lucide-ellipsis size-4" />
        </button>
      </Dropdown>
    </template>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Dropdown } from 'frappe-ui'

defineProps({
  row: { type: Object, required: true }, // { name, label, icon | emoji, to, active, depth, is_locked }
  menu: { type: Array, default: () => [] },
  collapsed: Boolean,
  canDrag: Boolean,
  dragging: Boolean,
})
const emit = defineEmits(['dragstart', 'dragend'])
const router = useRouter()
</script>
