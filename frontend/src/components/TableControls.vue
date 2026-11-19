<template>
  <!-- Plane-style table menus: a ••• pill on the current column (top edge) and row (left edge) -->
  <div v-if="editor.isEditable && cell" class="pointer-events-none absolute inset-0 z-10">
    <div v-for="kind in ['column', 'row']" :key="kind" class="pointer-events-auto absolute" :style="pillStyle(kind)">
      <Popover :align="kind === 'column' ? 'center' : 'start'" @update:open="(open) => (open ? openMenu(kind) : closeMenu())">
        <template #trigger>
          <button class="tc-pill" :class="kind === 'column' ? 'h-4 w-7' : 'h-7 w-4'" :title="`${kind === 'column' ? 'Column' : 'Row'} options`" @mousedown.prevent>
            <span :class="kind === 'column' ? 'lucide-ellipsis' : 'lucide-ellipsis-vertical'" class="size-3.5" />
          </button>
        </template>
        <template #default="{ close }">
          <div class="w-64 p-1.5" @mousedown.prevent>
            <div class="px-2 pb-1.5 pt-1 text-xs text-ink-gray-5">Background colors</div>
            <div class="flex flex-wrap gap-1.5 px-2 pb-2">
              <button
                v-for="c in CELL_COLORS"
                :key="c.value"
                class="size-6 rounded-md ring-1 ring-black/10 transition hover:scale-110"
                :style="{ background: c.value }"
                :title="c.name"
                @click="act(close, () => colorLine(editor, menuCell, kind, c.value))"
              />
              <button class="flex size-6 items-center justify-center rounded-md ring-1 ring-outline-gray-3 hover:bg-surface-gray-2" title="No colour" @click="act(close, () => colorLine(editor, menuCell, kind, null))">
                <span class="lucide-ban size-3.5 text-ink-gray-5" />
              </button>
            </div>
            <div class="my-1 h-px bg-outline-gray-1" />
            <button v-for="item in items(kind)" :key="item.label" class="tc-item" :class="item.danger && 'text-ink-red-5'" @click="act(close, item.run)">
              <span :class="item.icon" class="size-4" /> {{ item.label }}
            </button>
          </div>
        </template>
      </Popover>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Popover } from 'frappe-ui'
import { CELL_COLORS, atCell, backToCell, cellPosAt, clearLine, colorLine, duplicateLine, highlightLine } from '../editor/tableCells'

const props = defineProps({
  editor: { type: Object, required: true },
  container: { type: Object, default: null }, // the scrolling element the menus are placed in
})

const cell = ref(null) // the cell with the cursor, its row and its table, in container coordinates
let queued = false

function box(el) {
  const r = el.getBoundingClientRect()
  const c = props.container.getBoundingClientRect()
  const top = r.top - c.top + props.container.scrollTop
  const left = r.left - c.left + props.container.scrollLeft
  return { top, left, width: r.width, height: r.height }
}

function currentCell() {
  if (!props.editor.isActive('table')) return null
  const { selection } = props.editor.state
  // a row/column selection anchors on a cell node; a cursor sits inside one
  if (selection.$anchorCell) return props.editor.view.nodeDOM(selection.$anchorCell.pos)?.closest?.('td, th')
  const { node } = props.editor.view.domAtPos(selection.anchor)
  return (node.nodeType === 1 ? node : node.parentElement)?.closest('td, th')
}

// once per burst of events, after ProseMirror has updated the DOM (a microtask: also runs in background tabs)
function place() {
  if (queued || menuCell.value != null) return
  queued = true
  queueMicrotask(() => {
    queued = false
    const td = props.container && !props.editor.isDestroyed && currentCell()
    if (!td) return (cell.value = null)
    // the table scrolls sideways in its own wrapper: keep the pills inside its visible part
    const wrapper = box(td.closest('.tableWrapper') || td.closest('table'))
    const c = box(td)
    cell.value = {
      top: c.top,
      height: c.height,
      center: Math.min(Math.max(c.left + c.width / 2, wrapper.left + 14), wrapper.left + wrapper.width - 14),
      tableTop: box(td.closest('table')).top,
      tableLeft: wrapper.left,
    }
  })
}

function pillStyle(kind) {
  const c = cell.value
  return kind === 'column' ? { left: `${c.center - 14}px`, top: `${c.tableTop - 8}px` } : { left: `${c.tableLeft - 8}px`, top: `${c.top + c.height / 2 - 14}px` }
}

// a menu works on the cell the user was in when it opened; the pills stay put while it is open
const menuCell = ref(null)
let acted = false
function openMenu(kind) {
  menuCell.value = cellPosAt(props.editor.state)
  if (menuCell.value == null) return
  acted = false
  highlightLine(props.editor, menuCell.value, kind)
}
function closeMenu() {
  if (!acted && menuCell.value != null && !props.editor.isDestroyed) backToCell(props.editor, menuCell.value)
  menuCell.value = null
  place()
}

const at = (command) => () => atCell(props.editor, menuCell.value, command)
function items(kind) {
  const column = kind === 'column'
  return [
    { label: column ? 'Insert left' : 'Insert above', icon: column ? 'lucide-arrow-left' : 'lucide-arrow-up', run: at(column ? 'addColumnBefore' : 'addRowBefore') },
    { label: column ? 'Insert right' : 'Insert below', icon: column ? 'lucide-arrow-right' : 'lucide-arrow-down', run: at(column ? 'addColumnAfter' : 'addRowAfter') },
    { label: 'Duplicate', icon: 'lucide-copy', run: () => duplicateLine(props.editor, menuCell.value, kind) },
    { label: column ? 'Header column' : 'Header row', icon: 'lucide-heading', run: at(column ? 'toggleHeaderColumn' : 'toggleHeaderRow') },
    { label: 'Clear contents', icon: 'lucide-x', run: () => clearLine(props.editor, menuCell.value, kind) },
    { label: 'Delete', icon: 'lucide-trash-2', danger: true, run: at(column ? 'deleteColumn' : 'deleteRow') },
    ...(column ? [{ label: 'Delete table', icon: 'lucide-table', danger: true, run: at('deleteTable') }] : []),
  ]
}
function act(close, run) {
  if (menuCell.value == null) return close()
  acted = true
  run()
  close()
}

onMounted(() => {
  props.container?.addEventListener('scroll', place, { passive: true, capture: true }) // also the table's own sideways scroll
  window.addEventListener('resize', place)
  props.editor.on('transaction', place)
  place()
})
onBeforeUnmount(() => {
  props.container?.removeEventListener('scroll', place, { capture: true })
  window.removeEventListener('resize', place)
  props.editor.off('transaction', place)
})
</script>

<style scoped>
.tc-pill {
  @apply flex items-center justify-center rounded-full border border-outline-gray-2 bg-surface-base text-ink-gray-6 shadow-sm hover:border-blue-500 hover:bg-blue-600 hover:text-white;
}
.tc-item {
  @apply flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-sm text-ink-gray-8 hover:bg-surface-gray-2;
}
</style>
