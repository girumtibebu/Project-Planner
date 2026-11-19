<template>
  <div class="flex h-full min-h-0 flex-col">
    <!-- new page: blank or from a template -->
    <template v-if="!route.params.page">
      <header class="flex h-12 items-center gap-2 border-b border-outline-gray-1 px-4">
        <span class="lucide-file-plus size-4 text-ink-gray-5" />
        <h1 class="text-base font-semibold text-ink-gray-9">New page</h1>
      </header>
      <div class="mx-auto w-full max-w-3xl p-6">
        <div class="grid gap-3 md:grid-cols-2">
          <button class="tile" :disabled="!ctx.can.write" @click="create()">
            <span class="text-2xl">📄</span>
            <span class="font-medium text-ink-gray-8">Blank page</span>
            <span class="text-sm text-ink-gray-5">Notes, a run sheet or a call sheet from scratch.</span>
          </button>
          <button v-for="t in templates" :key="t.name" class="tile" :disabled="!ctx.can.write" @click="create(t.name)">
            <span class="text-2xl">{{ t.kind === 'debrief' ? '✅' : '📝' }}</span>
            <span class="font-medium text-ink-gray-8">{{ t.template_name }}</span>
            <span class="line-clamp-2 text-sm text-ink-gray-5">{{ t.description }}</span>
          </button>
        </div>
      </div>
    </template>

    <!-- one page, wiki style -->
    <template v-else-if="page">
      <header class="flex h-12 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-4">
        <Breadcrumbs :items="crumbs" />
        <div class="ml-auto flex items-center gap-3">
          <span class="hidden text-xs text-ink-gray-4 md:inline">
            <template v-if="saving">Saving…</template>
            <template v-else>Edited {{ timeAgo(page.modified) }} by {{ memberName(page.modified_by) }}</template>
          </span>
          <Badge v-if="page.is_locked" label="Locked" theme="orange" size="sm" />
          <Button size="sm" :variant="historyOpen ? 'subtle' : 'ghost'" icon="lucide-history" title="History: who changed what" @click="toggleHistory" />
          <Button size="sm" variant="ghost" icon="lucide-printer" title="Print" @click="print" />
          <Dropdown v-if="ctx.can.write" :options="menu"><Button size="sm" variant="ghost" icon="lucide-ellipsis" /></Dropdown>
        </div>
      </header>

      <TextEditor
        :key="page.name"
        ref="textEditor"
        class="page-editor flex min-h-0 flex-1 flex-col"
        :extensions="EXTENSIONS"
        :content="page.content"
        :editable="!readOnly"
        editor-class="wiki-content prose prose-gray max-w-none"
        :placeholder="isBoq ? 'Notes for the warehouse: delivery, spares, cases…' : 'Start writing. Markdown works: # heading, - list, [] checklist, > quote'"
        :fixed-menu="false"
        :bubble-menu="readOnly ? false : BUBBLE"
        :floating-menu="false"
        :mentions="mentions"
        :upload-args="{ doctype: 'Planner Page', docname: page.name, private: true }"
        @change="onContent"
      >
      <template #top="{ editor }">
        <EditorToolbar v-if="!readOnly" :editor="editor" :outline-open="outlineOpen" @toggle-outline="toggleOutline" />
      </template>
      <template #editor="{ editor }">
      <div class="flex min-h-0 flex-1">
      <div ref="scrollEl" class="relative min-h-0 min-w-0 flex-1 overflow-y-auto">
        <div class="mx-auto flex max-w-6xl gap-10 px-6">
          <article class="wiki mx-auto min-w-0 flex-1 py-12" :class="isBoq ? 'max-w-6xl' : 'max-w-3xl'">
            <!-- icon -->
            <Popover v-if="!readOnly" align="start">
              <template #trigger>
                <button class="mb-3 rounded-lg px-1 text-5xl leading-none hover:bg-surface-gray-2" :title="page.icon ? 'Change icon' : 'Add icon'">
                  {{ page.icon || '📄' }}
                </button>
              </template>
              <template #default="{ close }">
                <div class="grid w-72 grid-cols-8 gap-1 p-2">
                  <button v-for="e in EMOJIS" :key="e" class="rounded p-1 text-xl hover:bg-surface-gray-2" @click="setIcon(e); close()">{{ e }}</button>
                  <button class="col-span-8 mt-1 rounded py-1 text-xs text-ink-gray-5 hover:bg-surface-gray-2" @click="setIcon(''); close()">Remove icon</button>
                </div>
              </template>
            </Popover>
            <div v-else class="mb-3 text-5xl leading-none">{{ page.icon || '📄' }}</div>

            <textarea
              v-model="page.title"
              rows="1"
              class="w-full resize-none border-0 bg-transparent p-0 text-4xl font-bold leading-tight tracking-tight text-ink-gray-9 placeholder:text-ink-gray-3 focus:ring-0"
              placeholder="Untitled"
              :disabled="readOnly"
              @input="grow"
              @change="saveField('title', page.title)"
              @keydown.enter.prevent="$event.target.blur()"
            />
            <div class="mb-8 mt-3 flex flex-wrap items-center gap-2 text-sm text-ink-gray-5">
              <span v-if="isBoq" class="inline-flex items-center gap-1 rounded-full border border-outline-gray-2 px-2.5 py-0.5 text-xs">
                <span class="lucide-package size-3.5" /> {{ page.department }} BOQ
              </span>
              <Dropdown v-else-if="ctx.can.write" :options="kindOptions">
                <button class="inline-flex items-center gap-1 rounded-full border border-outline-gray-2 px-2.5 py-0.5 text-xs hover:bg-surface-gray-2">
                  <span :class="KIND_ICON[page.page_kind]" class="size-3.5" /> {{ page.page_kind }}
                </button>
              </Dropdown>
              <span v-if="!isBoq">{{ words }} words · {{ Math.max(1, Math.round(words / 200)) }} min read · v{{ page.version }}</span>
            </div>

            <BoqGrid v-if="isBoq" :page="page" />
            <div v-if="isBoq" class="mb-2 text-xs font-medium uppercase tracking-wide text-ink-gray-5">Notes</div>
            <div class="relative">
              <DragHandle v-if="!readOnly" :editor="editor" class="block-handle" title="Drag to move this block">
                <span class="lucide-grip-vertical size-4" />
              </DragHandle>
              <EditorContent :editor="editor" />
            </div>

            <!-- sub-pages -->
            <section v-if="children.length || ctx.can.write" class="mt-16 border-t border-outline-gray-1 pt-6">
              <div class="mb-3 text-xs font-medium uppercase tracking-wide text-ink-gray-5">Sub-pages</div>
              <div class="grid gap-2 sm:grid-cols-2">
                <router-link
                  v-for="child in children"
                  :key="child.name"
                  :to="{ name: 'pages', params: { project: ctx.project.name, page: child.name } }"
                  class="flex items-center gap-2 rounded-lg border border-outline-gray-1 px-3 py-2.5 text-sm hover:border-outline-gray-3 hover:bg-surface-gray-1"
                >
                  <span class="text-lg">{{ child.icon || '📄' }}</span>
                  <span class="truncate text-ink-gray-8">{{ child.title }}</span>
                </router-link>
                <button
                  v-if="ctx.can.write"
                  class="flex items-center gap-2 rounded-lg border border-dashed border-outline-gray-2 px-3 py-2.5 text-sm text-ink-gray-5 hover:border-outline-gray-4 hover:text-ink-gray-8"
                  @click="create(null, page.name)"
                >
                  <span class="lucide-plus size-4" /> Add sub-page
                </button>
              </div>
            </section>
          </article>

          <!-- on this page -->
          <PageOutline :toc="toc" :active="active" :open="outlineOpen || readOnly" @jump="jump" />
        </div>
        <TableControls v-if="!readOnly && scrollEl" :editor="editor" :container="scrollEl" />
      </div>
      <PageHistory v-if="historyOpen" :page="page.name" :stamp="String(page.modified)" @close="historyOpen = false" />
      </div>
      </template>
      </TextEditor>
    </template>
    <div v-else class="flex h-full items-center justify-center"><LoadingIndicator class="size-5" /></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Badge, Breadcrumbs, Button, Dropdown, LoadingIndicator, Popover, TextEditor, toast } from 'frappe-ui'
import { EditorContent } from '@tiptap/vue-3'
import { DragHandle } from '@tiptap/extension-drag-handle-vue-3'
import { Markdown } from '@tiptap/markdown'
import { TableCellBackground } from '../editor/tableCells'
import BoqGrid from '../components/BoqGrid.vue'
import EditorToolbar from '../components/EditorToolbar.vue'
import PageOutline from '../components/PageOutline.vue'
import TableControls from '../components/TableControls.vue'
import PageHistory from '../components/PageHistory.vue'
import { confirmAction } from '../confirm'
import { api } from '../api'
import { ctx, fail, loadProject, memberName } from '../store'
import { timeAgo } from '../utils'

const route = useRoute()
const router = useRouter()
const templates = ref([])
const page = ref(null)
const saving = ref(false)
const html = ref('')
const scrollEl = ref(null)
const active = ref(0)

const KINDS = ['Notes', 'Brief', 'Debrief', 'Call Sheet', 'Run Sheet']
const KIND_ICON = {
  Notes: 'lucide-file-text',
  Brief: 'lucide-notebook-pen',
  Debrief: 'lucide-clipboard-check',
  'Call Sheet': 'lucide-phone-call',
  'Run Sheet': 'lucide-list-ordered',
}
const EMOJIS = ['📄', '📝', '✅', '📋', '🎬', '🎤', '🎵', '💡', '🎨', '📸', '🚚', '🗺️', '📍', '🗓️', '⏰', '🎯', '📦', '🛠️', '💰', '📊', '🤝', '⭐', '🔥', '🚀', '🎉', '🏛️', '🍽️', '🎭', '📢', '🧾', '🔒', '❓']

onMounted(async () => {
  try {
    templates.value = await api.pageTemplates()
  } catch (err) {
    fail(err)
  }
})

watch(
  () => route.params.page,
  async (name) => {
    page.value = null
    if (!name) return
    try {
      page.value = await api.get('Planner Page', name)
      html.value = page.value.content || ''
      await nextTick()
      document.querySelectorAll('.wiki textarea').forEach((el) => grow({ target: el }))
    } catch (err) {
      fail(err)
    }
  },
  { immediate: true },
)

const readOnly = computed(() => !ctx.can.write || Boolean(page.value?.is_locked))
const isBoq = computed(() => page.value?.page_kind === 'BOQ')

// cell colours for tables; Markdown so a page can be copied or downloaded as .md (pasting Markdown already works)
const EXTENSIONS = [TableCellBackground, Markdown]
const textEditor = ref(null)

function pageMarkdown() {
  const editor = textEditor.value?.editor
  return `# ${page.value.title}

${editor?.getMarkdown?.() || ''}`
}
async function copyMarkdown() {
  try {
    await navigator.clipboard.writeText(pageMarkdown())
    toast.success('Copied as Markdown')
  } catch (err) {
    fail(err)
  }
}
function downloadMarkdown() {
  const url = URL.createObjectURL(new Blob([pageMarkdown()], { type: 'text/markdown' }))
  const a = Object.assign(document.createElement('a'), { href: url, download: `${(page.value.title || 'page').replace(/[\/:*?"<>|]+/g, '-')}.md` })
  a.click()
  URL.revokeObjectURL(url)
}

// a small menu on selected text; the menu bar is EditorToolbar
const BUBBLE = ['Bold', 'Italic', 'Strikethrough', 'Link', 'Separator', 'Bullet List', 'Task List']

// history panel stays open from page to page while the user wants it
const historyOpen = ref(
  (() => {
    try {
      return localStorage.getItem('planner.pageHistory') === '1'
    } catch {
      return false
    }
  })(),
)
const outlineOpen = ref(
  (() => {
    try {
      return localStorage.getItem('planner.pageOutline') !== '0'
    } catch {
      return true
    }
  })(),
)
function toggleOutline() {
  outlineOpen.value = !outlineOpen.value
  try {
    localStorage.setItem('planner.pageOutline', outlineOpen.value ? '1' : '0')
  } catch {
    // private mode: not remembered
  }
}

function toggleHistory() {
  historyOpen.value = !historyOpen.value
  try {
    localStorage.setItem('planner.pageHistory', historyOpen.value ? '1' : '0')
  } catch {
    // private mode: not remembered
  }
}
const children = computed(() => ctx.pages.filter((p) => p.parent_page === page.value?.name))
const mentions = computed(() => ctx.members.map((m) => ({ label: m.full_name || m.name, value: m.name })))
const crumbs = computed(() => {
  const chain = []
  let current = page.value
  while (current) {
    chain.unshift({ label: `${current.icon ? current.icon + ' ' : ''}${current.title}`, route: { name: 'pages', params: { project: ctx.project.name, page: current.name } } })
    current = ctx.pages.find((p) => p.name === current.parent_page)
  }
  return [{ label: 'Pages', route: { name: 'pages', params: { project: ctx.project.name } } }, ...chain]
})

// headings and word count from the current HTML
const toc = computed(() => {
  const out = []
  const re = /<h([1-3])[^>]*>(.*?)<\/h\1>/gis
  let m
  while ((m = re.exec(html.value))) {
    // strip tags and decode entities (&amp; -> &)
    const text = new DOMParser().parseFromString(m[2], 'text/html').body.textContent.trim()
    if (text) out.push({ level: Number(m[1]), text })
  }
  return out
})
const words = computed(() => (html.value.replace(/<[^>]+>/g, ' ').match(/\S+/g) || []).length)

function headingEls() {
  return [...(scrollEl.value?.querySelectorAll('.ProseMirror h1, .ProseMirror h2, .ProseMirror h3') || [])].filter((el) => el.textContent.trim())
}
function jump(i) {
  headingEls()[i]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function onScroll() {
  const top = scrollEl.value?.getBoundingClientRect().top || 0
  let current = 0
  headingEls().forEach((el, i) => {
    if (el.getBoundingClientRect().top - top < 120) current = i
  })
  active.value = current
}
watch(scrollEl, (el, old) => {
  old?.removeEventListener('scroll', onScroll)
  el?.addEventListener('scroll', onScroll, { passive: true })
})
onBeforeUnmount(() => scrollEl.value?.removeEventListener('scroll', onScroll))

function grow(event) {
  const el = event.target
  el.style.height = 'auto'
  el.style.height = `${el.scrollHeight}px`
}

async function create(template = null, parent = null) {
  try {
    const doc = await api.createPage({ project: ctx.project.name, template, parent_page: parent })
    await loadProject(ctx.project.name)
    router.push({ name: 'pages', params: { project: ctx.project.name, page: doc.name } })
  } catch (err) {
    fail(err)
  }
}

async function saveField(field, value) {
  saving.value = true
  try {
    const doc = await api.setValue('Planner Page', page.value.name, field, value)
    page.value.version = doc.version
    page.value.modified = doc.modified
    page.value.modified_by = doc.modified_by
    if (['title', 'is_locked', 'page_kind', 'icon'].includes(field)) loadProject(ctx.project.name)
  } catch (err) {
    fail(err)
  } finally {
    saving.value = false
  }
}

let timer = null
function onContent(value) {
  html.value = value
  clearTimeout(timer)
  timer = setTimeout(() => {
    if (value !== page.value.content) {
      page.value.content = value
      saveField('content', value)
    }
  }, 900)
}

function setIcon(icon) {
  page.value.icon = icon
  saveField('icon', icon)
}

const kindOptions = computed(() =>
  KINDS.map((kind) => ({
    label: kind,
    icon: KIND_ICON[kind],
    onClick: () => {
      page.value.page_kind = kind
      saveField('page_kind', kind)
    },
  })),
)

// only the page's owner (or a manager) locks, unlocks or deletes a locked page
const isOwner = computed(() => page.value?.owner === ctx.user || ctx.can.manage)
const menu = computed(() => [
  { label: 'Add sub-page', icon: 'lucide-file-plus', onClick: () => create(null, page.value.name) },
  { label: 'Copy as Markdown', icon: 'lucide-clipboard-copy', onClick: copyMarkdown },
  { label: 'Download as Markdown', icon: 'lucide-file-down', onClick: downloadMarkdown },
  ...(isOwner.value
    ? [
        {
          label: page.value?.is_locked ? 'Unlock page' : 'Lock page',
          icon: page.value?.is_locked ? 'lucide-lock-open' : 'lucide-lock',
          onClick: async () => {
            const lock = !page.value.is_locked
            const ok = await confirmAction(
              lock
                ? { title: `Lock "${page.value.title}"?`, message: 'Others can still read the page, but only you can change, unlock or delete it.', action: 'Lock' }
                : { title: `Unlock "${page.value.title}"?`, message: 'Everyone who can edit this project can change or delete the page again.', action: 'Unlock' },
            )
            if (!ok) return
            page.value.is_locked = lock ? 1 : 0
            saveField('is_locked', page.value.is_locked)
          },
        },
      ]
    : []),
  {
    hidden: page.value?.is_locked && !isOwner.value,
    label: 'Delete page',
    icon: 'lucide-trash-2',
    theme: 'red',
    onClick: async () => {
      const ok = await confirmAction({
        title: `Delete "${page.value.title}"?`,
        message: `The page${isBoq.value ? ' and all its BOQ lines' : ''} will be deleted.${children.value.length ? ' Its sub-pages move up one level.' : ''} This cannot be undone.`,
        action: 'Delete',
        danger: true,
      })
      if (!ok) return
      try {
        await api.remove('Planner Page', page.value.name)
        await loadProject(ctx.project.name)
        router.push({ name: 'pages', params: { project: ctx.project.name } })
      } catch (err) {
        fail(err)
      }
    },
  },
].filter((option) => !option.hidden))

function print() {
  window.open(`/printview?doctype=Planner%20Page&name=${encodeURIComponent(page.value.name)}&trigger_print=1`, '_blank')
}
</script>

<style scoped>
.tile {
  @apply flex flex-col items-start gap-1.5 rounded-lg border border-outline-gray-2 p-4 text-left hover:border-outline-gray-4 hover:bg-surface-gray-1 disabled:opacity-50;
}
</style>

<style>
/* drag handle beside each block (TipTap DragHandle) */
.block-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.5rem;
  margin-right: 0.25rem;
  border-radius: 0.375rem;
  color: var(--ink-gray-4, #9ca3af);
  cursor: grab;
  transition: background 0.1s;
}
.block-handle:hover {
  background: var(--surface-gray-2, #f3f4f6);
  color: var(--ink-gray-7, #374151);
}
.block-handle:active {
  cursor: grabbing;
}

/* tables: as wide as their columns (scroll sideways when wider than the page); text wraps in a cell */
.wiki .ProseMirror .tableWrapper {
  overflow-x: auto;
  margin: 1.25rem 0;
  padding: 0 0 6px;
}
.wiki .ProseMirror .tableWrapper::-webkit-scrollbar {
  height: 6px;
}
.wiki .ProseMirror .tableWrapper::-webkit-scrollbar-thumb {
  background: var(--surface-gray-4, #d1d5db);
  border-radius: 3px;
}
.wiki .ProseMirror table {
  table-layout: fixed;
  width: max-content;
  min-width: 100% !important;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid var(--outline-gray-2, #e5e7eb);
  border-radius: 0.5rem;
  overflow: hidden;
  font-size: 0.9em;
}
.wiki .ProseMirror th,
.wiki .ProseMirror td {
  border: 0;
  border-right: 1px solid var(--outline-gray-1, #f0f0f0);
  border-bottom: 1px solid var(--outline-gray-1, #f0f0f0);
  padding: 0.55em 0.8em;
  vertical-align: top;
  overflow-wrap: anywhere;
  position: relative;
}
.wiki .ProseMirror tr > :last-child {
  border-right: 0;
}
.wiki .ProseMirror tr:last-child > * {
  border-bottom: 0;
}
.wiki .ProseMirror th {
  background: var(--surface-gray-1, #f9fafb);
  font-weight: 600;
  text-align: left;
  color: var(--ink-gray-8, #1f2937);
}
/* a column nobody resized yet gets a usable width; drag a border to resize */
.wiki .ProseMirror col:not([style^='width']):not([style*=' width:']):not([style*=';width:']) {
  width: 12rem;
}
.wiki .ProseMirror td p,
.wiki .ProseMirror th p {
  margin: 0;
}
.wiki .ProseMirror .selectedCell::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgb(59 130 246 / 0.08);
  pointer-events: none;
}
.wiki .ProseMirror .column-resize-handle {
  position: absolute;
  right: -1px;
  top: 0;
  bottom: 0;
  width: 3px;
  background: rgb(59 130 246 / 0.5);
  pointer-events: none;
}

/* wiki typography for the page editor */
.wiki .ProseMirror {
  min-height: 50vh;
  outline: none;
  font-size: 15.5px;
  line-height: 1.75;
}
.wiki .ProseMirror > * + * {
  margin-top: 0.75em;
}
.wiki .ProseMirror h1 {
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  margin-top: 2em;
  padding-bottom: 0.3em;
  border-bottom: 1px solid var(--outline-gray-1, #edeef0);
}
.wiki .ProseMirror h2 {
  font-size: 1.35rem;
  font-weight: 650;
  margin-top: 1.8em;
}
.wiki .ProseMirror h3 {
  font-size: 1.1rem;
  font-weight: 600;
  margin-top: 1.5em;
}
.wiki .ProseMirror h1,
.wiki .ProseMirror h2,
.wiki .ProseMirror h3 {
  scroll-margin-top: 1rem;
}
.wiki .ProseMirror > :first-child {
  margin-top: 0;
}
.wiki .ProseMirror blockquote {
  border-left: 3px solid var(--outline-gray-3, #d1d5db);
  padding: 0.25em 0 0.25em 1em;
  font-style: normal;
}
.wiki .ProseMirror pre {
  border-radius: 8px;
  padding: 0.9em 1.1em;
}
.wiki .ProseMirror img {
  border-radius: 8px;
}
.wiki .ProseMirror hr {
  margin: 2em 0;
}
</style>
