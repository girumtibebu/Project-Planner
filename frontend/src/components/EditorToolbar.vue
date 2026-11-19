<template>
  <!-- Plane-style menu bar for a page: full width, text style and colour menus, then formatting buttons -->
  <div class="flex h-11 shrink-0 items-center gap-0.5 overflow-x-auto border-b border-outline-gray-1 bg-surface-base px-3">
    <Dropdown :options="textOptions">
      <button class="tb-menu" title="Text style">{{ textLabel }} <span class="lucide-chevron-down size-3.5 text-ink-gray-5" /></button>
    </Dropdown>

    <Popover align="start">
      <template #trigger>
        <button class="tb-menu" title="Colour">
          <span class="size-3.5 rounded-full ring-1 ring-black/10" :class="colorDot" />
          Color <span class="lucide-chevron-down size-3.5 text-ink-gray-5" />
        </button>
      </template>
      <template #default="{ close }">
        <div class="w-56 p-2.5">
          <div class="mb-1.5 text-xs text-ink-gray-5">Text</div>
          <div class="grid grid-cols-6 gap-1.5">
            <button class="swatch border border-outline-gray-2 bg-surface-base text-ink-gray-8" title="Default" @click="run((c) => c.unsetColor(), close)">A</button>
            <button v-for="c in COLORS" :key="c" class="swatch" :class="TEXT[c]" :title="c" @click="run((x) => x.setColorByName(c), close)">A</button>
          </div>
          <div class="mb-1.5 mt-3 text-xs text-ink-gray-5">Background</div>
          <div class="grid grid-cols-6 gap-1.5">
            <button class="swatch border border-outline-gray-2" title="None" @click="run((c) => c.unsetHighlight(), close)"><span class="lucide-ban size-3.5 text-ink-gray-4" /></button>
            <button v-for="c in COLORS" :key="c" class="swatch" :class="BG[c]" :title="c" @click="run((x) => x.setHighlightByName(c), close)" />
          </div>
        </div>
      </template>
    </Popover>

    <template v-for="(group, gi) in GROUPS" :key="gi">
      <span class="mx-1.5 h-5 w-px shrink-0 bg-outline-gray-2" />
      <button
        v-for="b in group"
        :key="b.icon"
        class="tb-btn"
        :class="active(b) && 'tb-on'"
        :title="b.title"
        @mousedown.prevent
        @click="b.run(editor.chain().focus())"
      >
        <span :class="b.icon" class="size-4" />
      </button>
    </template>

    <div class="ml-auto flex shrink-0 items-center gap-0.5 pl-2">
      <button class="tb-btn" title="Undo" :disabled="!editor.can().undo()" @click="editor.chain().focus().undo().run()"><span class="lucide-undo-2 size-4" /></button>
      <button class="tb-btn" title="Redo" :disabled="!editor.can().redo()" @click="editor.chain().focus().redo().run()"><span class="lucide-redo-2 size-4" /></button>
      <span class="mx-1.5 h-5 w-px bg-outline-gray-2" />
      <button class="tb-btn" :class="outlineOpen && 'tb-on'" title="On this page" @click="emit('toggle-outline')"><span class="lucide-panel-right size-4" /></button>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { Dropdown, Popover } from 'frappe-ui'

const props = defineProps({ editor: { type: Object, required: true }, outlineOpen: Boolean })
const emit = defineEmits(['toggle-outline'])

// the editor is not reactive: re-read active marks after every change
const tick = ref(0)
const bump = () => tick.value++
props.editor.on('transaction', bump)
onBeforeUnmount(() => props.editor.off('transaction', bump))

const run = (fn, close) => {
  fn(props.editor.chain().focus()).run()
  close?.()
}
const active = (b) => tick.value >= 0 && b.active?.(props.editor)

const TEXTS = [
  { label: 'Text', icon: 'lucide-pilcrow', run: (c) => c.setParagraph(), on: (e) => e.isActive('paragraph') },
  { label: 'Heading 1', icon: 'lucide-heading-1', run: (c) => c.setHeading({ level: 1 }), on: (e) => e.isActive('heading', { level: 1 }) },
  { label: 'Heading 2', icon: 'lucide-heading-2', run: (c) => c.setHeading({ level: 2 }), on: (e) => e.isActive('heading', { level: 2 }) },
  { label: 'Heading 3', icon: 'lucide-heading-3', run: (c) => c.setHeading({ level: 3 }), on: (e) => e.isActive('heading', { level: 3 }) },
]
const textLabel = computed(() => (tick.value >= 0 && TEXTS.find((t) => t.on(props.editor))?.label) || 'Text')
const textOptions = TEXTS.map((t) => ({ label: t.label, icon: t.icon, onClick: () => run(t.run) }))

const COLORS = ['red', 'orange', 'yellow', 'green', 'teal', 'cyan', 'blue', 'purple', 'pink', 'gray']
const TEXT = {
  red: 'text-red-600',
  orange: 'text-orange-600',
  yellow: 'text-yellow-600',
  green: 'text-green-600',
  teal: 'text-teal-600',
  cyan: 'text-cyan-600',
  blue: 'text-blue-600',
  purple: 'text-purple-600',
  pink: 'text-pink-600',
  gray: 'text-gray-600',
}
const BG = {
  red: 'bg-red-100',
  orange: 'bg-orange-100',
  yellow: 'bg-yellow-100',
  green: 'bg-green-100',
  teal: 'bg-teal-100',
  cyan: 'bg-cyan-100',
  blue: 'bg-blue-100',
  purple: 'bg-purple-100',
  pink: 'bg-pink-100',
  gray: 'bg-gray-100',
}
const colorDot = computed(() => {
  tick.value
  const name = props.editor.getAttributes('textStyle')?.color
  return name ? TEXT[name]?.replace('text-', 'bg-') : 'bg-ink-gray-8'
})

const GROUPS = [
  [
    { icon: 'lucide-bold', title: 'Bold (Ctrl+B)', run: (c) => c.toggleBold().run(), active: (e) => e.isActive('bold') },
    { icon: 'lucide-italic', title: 'Italic (Ctrl+I)', run: (c) => c.toggleItalic().run(), active: (e) => e.isActive('italic') },
    { icon: 'lucide-underline', title: 'Underline (Ctrl+U)', run: (c) => c.toggleUnderline().run(), active: (e) => e.isActive('underline') },
    { icon: 'lucide-strikethrough', title: 'Strikethrough', run: (c) => c.toggleStrike().run(), active: (e) => e.isActive('strike') },
  ],
  [
    { icon: 'lucide-text-align-start', title: 'Align left', run: (c) => c.setTextAlign('left').run(), active: (e) => e.isActive({ textAlign: 'left' }) },
    { icon: 'lucide-text-align-center', title: 'Align centre', run: (c) => c.setTextAlign('center').run(), active: (e) => e.isActive({ textAlign: 'center' }) },
    { icon: 'lucide-text-align-end', title: 'Align right', run: (c) => c.setTextAlign('right').run(), active: (e) => e.isActive({ textAlign: 'right' }) },
  ],
  [
    { icon: 'lucide-list-ordered', title: 'Numbered list', run: (c) => c.toggleOrderedList().run(), active: (e) => e.isActive('orderedList') },
    { icon: 'lucide-list', title: 'Bullet list', run: (c) => c.toggleBulletList().run(), active: (e) => e.isActive('bulletList') },
    { icon: 'lucide-list-checks', title: 'Checklist', run: (c) => c.toggleTaskList().run(), active: (e) => e.isActive('taskList') },
  ],
  [
    { icon: 'lucide-quote', title: 'Quote', run: (c) => c.toggleBlockquote().run(), active: (e) => e.isActive('blockquote') },
    { icon: 'lucide-code', title: 'Code block', run: (c) => c.toggleCodeBlock().run(), active: (e) => e.isActive('codeBlock') },
    { icon: 'lucide-link', title: 'Link', run: (c) => c.openLinkEditor().run(), active: (e) => e.isActive('link') },
  ],
  [
    { icon: 'lucide-table', title: 'Insert table', run: (c) => c.insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(), active: (e) => e.isActive('table') },
    { icon: 'lucide-image-plus', title: 'Insert image', run: (c) => c.selectAndUploadImage().run() },
    { icon: 'lucide-minus', title: 'Divider', run: (c) => c.setHorizontalRule().run() },
  ],
]
</script>

<style scoped>
.tb-menu {
  @apply flex h-8 shrink-0 items-center gap-1.5 rounded-md px-2 text-sm text-ink-gray-7 hover:bg-surface-gray-2;
}
.tb-btn {
  @apply flex size-8 shrink-0 items-center justify-center rounded-md text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-9 disabled:opacity-40 disabled:hover:bg-transparent;
}
.tb-on {
  @apply bg-surface-gray-3 text-ink-gray-9;
}
.swatch {
  @apply flex size-7 items-center justify-center rounded-md text-sm font-semibold hover:ring-2 hover:ring-outline-gray-3;
}
</style>
