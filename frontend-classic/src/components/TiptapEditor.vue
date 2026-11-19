<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useEditor, EditorContent } from "@tiptap/vue-3";
import { BubbleMenu } from "@tiptap/vue-3/menus";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import TaskList from "@tiptap/extension-task-list";
import TaskItem from "@tiptap/extension-task-item";
import Underline from "@tiptap/extension-underline";
import Highlight from "@tiptap/extension-highlight";
import Typography from "@tiptap/extension-typography";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import CharacterCount from "@tiptap/extension-character-count";
import Mention from "@tiptap/extension-mention";
import { Table } from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableHeader from "@tiptap/extension-table-header";
import TableCell from "@tiptap/extension-table-cell";
import { Markdown } from "tiptap-markdown";
import { frappeList, requireCsrfToken } from "../composables/useFrappe";

// ── Props / emits ─────────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    modelValue: string;
    placeholder?: string;
    editable?: boolean;
    /** ISO datetime string; shown in the bottom bar when present */
    lastModified?: string;
    lastModifiedBy?: string;
  }>(),
  { placeholder: "Start writing…", editable: true }
);

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

// ── Slash menu ────────────────────────────────────────────────────────────────

const showSlashMenu = ref(false);
const slashQuery = ref("");
const slashMenuCoords = ref({ top: 0, left: 0 });
const skipNextUpdate = ref(false);

// ── Mention suggestion state ──────────────────────────────────────────────────

const mentionUsers = ref<any[]>([]);
const showMentionDrop = ref(false);
const mentionCoords = ref({ top: 0, left: 0 });
let mentionCommand: ((props: any) => void) | null = null;

async function fetchMentionUsers(query: string) {
  try {
    mentionUsers.value = await frappeList("User", {
      filters: [
        ["full_name", "like", `%${query}%`],
        ["enabled", "=", 1],
        ["user_type", "=", "System User"],
      ],
      fields: ["name", "full_name"],
      limit: 8,
    });
  } catch { mentionUsers.value = []; }
}

function pickMentionUser(u: any) {
  if (mentionCommand) {
    mentionCommand({ id: u.name, label: u.full_name || u.name });
  }
  showMentionDrop.value = false;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getMarkdownSafe(e: any): string {
  if (!e) return "";
  try { return e.storage?.markdown?.getMarkdown() ?? e.getHTML(); }
  catch { return e.getHTML?.() ?? ""; }
}

function getBodyEl(): HTMLElement { return document.body; }

function promptLink() {
  const e = editor.value;
  if (!e) return;
  const url = window.prompt("Enter URL");
  if (url) run("link", url);
}

function updateSlashMenuPosition() {
  const e = editor.value;
  if (!e) return;
  const pos = e.state.selection.$from.pos;
  const coords = e.view.coordsAtPos(pos);
  slashMenuCoords.value = {
    top: coords.bottom + 4,
    left: Math.min(coords.left, window.innerWidth - 290),
  };
}

// ── Image upload ──────────────────────────────────────────────────────────────

async function uploadImage(file: File): Promise<string | null> {
  try {
    const token = await requireCsrfToken();
    const fd = new FormData();
    fd.append("file", file);
    fd.append("is_private", "0");
    const res = await fetch("/api/method/upload_file", {
      method: "POST",
      credentials: "include",
      headers: { "X-Frappe-CSRF-Token": token },
      body: fd,
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.message?.file_url || null;
  } catch { return null; }
}

async function insertImageFromFile(file: File) {
  const url = await uploadImage(file);
  if (url && editor.value) {
    editor.value.chain().focus().setImage({ src: url }).run();
  }
}

function triggerImagePicker() {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.onchange = async (e) => {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) await insertImageFromFile(file);
  };
  input.click();
}

// ── Editor setup ──────────────────────────────────────────────────────────────

const editor = useEditor({
  content: props.modelValue,
  editable: props.editable,
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      code: {},
      codeBlock: { languageClassPrefix: "language-" },
    }),
    Placeholder.configure({
      placeholder: props.placeholder,
      showOnlyWhenEditable: true,
      showOnlyCurrent: true,
    }),
    TaskList,
    TaskItem.configure({ nested: true }),
    Underline,
    Highlight.configure({ multicolor: false }),
    Typography,
    Link.configure({ openOnClick: false, autolink: true }),
    Image.configure({ inline: false, allowBase64: false }),
    CharacterCount,
    Table.configure({ resizable: true }),
    TableRow,
    TableHeader,
    TableCell,
    Mention.configure({
      HTMLAttributes: { class: "ep-mention" },
      suggestion: {
        items: ({ query }) => {
          fetchMentionUsers(query);
          return [];
        },
        render: () => ({
          onStart: (props) => {
            mentionCommand = props.command;
            const coords = props.clientRect?.();
            if (coords) {
              mentionCoords.value = { top: coords.bottom + 4, left: coords.left };
            }
            showMentionDrop.value = true;
          },
          onUpdate: (props) => {
            mentionCommand = props.command;
            fetchMentionUsers(props.query);
          },
          onKeyDown: ({ event }) => {
            if (event.key === "Escape") { showMentionDrop.value = false; return true; }
            return false;
          },
          onExit: () => { showMentionDrop.value = false; mentionCommand = null; },
        }),
      },
    }),
    Markdown.configure({
      html: true,
      transformCopiedText: true,
      transformPastedText: true,
    }),
  ],
  editorProps: {
    handleKeyDown(_view, event) {
      if (event.key === "Escape" && showSlashMenu.value) {
        showSlashMenu.value = false;
        slashQuery.value = "";
        return true;
      }
      return false;
    },
    handleDrop(_view, event) {
      const files = event.dataTransfer?.files;
      if (files?.length) {
        const img = Array.from(files).find(f => f.type.startsWith("image/"));
        if (img) { insertImageFromFile(img); return true; }
      }
      return false;
    },
    handlePaste(_view, event) {
      const items = event.clipboardData?.items;
      if (items) {
        for (const item of items) {
          if (item.type.startsWith("image/")) {
            const file = item.getAsFile();
            if (file) { insertImageFromFile(file); return true; }
          }
        }
      }
      return false;
    },
  },
  onUpdate({ editor }) {
    if (skipNextUpdate.value) { skipNextUpdate.value = false; return; }
    emit("update:modelValue", getMarkdownSafe(editor));

    const { selection } = editor.state;
    if (selection.empty && selection.$from.parent.type.name === "paragraph") {
      const textBefore = editor.state.doc.textBetween(
        selection.$from.start(), selection.$from.pos, ""
      );
      const match = textBefore.match(/^\/(\w*)$/);
      if (match) {
        slashQuery.value = match[1];
        if (!showSlashMenu.value) { updateSlashMenuPosition(); showSlashMenu.value = true; }
        return;
      }
    }
    showSlashMenu.value = false;
    slashQuery.value = "";
  },
});

watch(() => props.modelValue, (newVal) => {
  const e = editor.value;
  if (!e) return;
  const current = getMarkdownSafe(e);
  if (current !== newVal) { skipNextUpdate.value = true; e.commands.setContent(newVal ?? ""); }
});

watch(() => props.editable, (val) => editor.value?.setEditable(val ?? true));

onBeforeUnmount(() => editor.value?.destroy());

// ── Toolbar helpers ───────────────────────────────────────────────────────────

function isActive(name: string, attrs?: Record<string, unknown>) {
  return editor.value?.isActive(name, attrs) ?? false;
}

function run(cmd: string, value?: any) {
  const e = editor.value;
  if (!e) return;
  const c = e.chain().focus();
  switch (cmd) {
    case "h1":           c.toggleHeading({ level: 1 }).run(); break;
    case "h2":           c.toggleHeading({ level: 2 }).run(); break;
    case "h3":           c.toggleHeading({ level: 3 }).run(); break;
    case "bold":         c.toggleBold().run(); break;
    case "italic":       c.toggleItalic().run(); break;
    case "underline":    c.toggleUnderline().run(); break;
    case "strike":       c.toggleStrike().run(); break;
    case "code":         c.toggleCode().run(); break;
    case "highlight":    c.toggleHighlight().run(); break;
    case "bulletList":   c.toggleBulletList().run(); break;
    case "orderedList":  c.toggleOrderedList().run(); break;
    case "taskList":     c.toggleTaskList().run(); break;
    case "blockquote":   c.toggleBlockquote().run(); break;
    case "codeBlock":    c.toggleCodeBlock().run(); break;
    case "hr":           c.setHorizontalRule().run(); break;
    case "clear":        c.clearNodes().unsetAllMarks().run(); break;
    case "undo":         c.undo().run(); break;
    case "redo":         c.redo().run(); break;
    case "table":        c.insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(); break;
    case "image":        triggerImagePicker(); break;
    case "link":
      if (value) c.toggleLink({ href: value }).run();
      else { promptLink(); return; }
      break;
  }
}

// ── Stats ─────────────────────────────────────────────────────────────────────

const wordCount = computed(() => {
  const text = editor.value?.getText() ?? "";
  return text.trim() ? text.trim().split(/\s+/).length : 0;
});

const charCount = computed(() => {
  return (editor.value?.storage.characterCount as any)?.characters?.() ?? 0;
});

// ── Slash commands ────────────────────────────────────────────────────────────

const slashCommands = [
  { id: "h1",       label: "Heading 1",      icon: "H1",    shortcut: "#",    action: () => run("h1") },
  { id: "h2",       label: "Heading 2",      icon: "H2",    shortcut: "##",   action: () => run("h2") },
  { id: "h3",       label: "Heading 3",      icon: "H3",    shortcut: "###",  action: () => run("h3") },
  { id: "bullet",   label: "Bullet list",    icon: "•",     shortcut: "-",    action: () => run("bulletList") },
  { id: "numbered", label: "Numbered list",  icon: "1.",    shortcut: "1.",   action: () => run("orderedList") },
  { id: "task",     label: "Task list",      icon: "[ ]",   shortcut: "[]",   action: () => run("taskList") },
  { id: "quote",    label: "Quote",          icon: '"',     shortcut: ">",    action: () => run("blockquote") },
  { id: "code",     label: "Code block",     icon: "</>",   shortcut: "```",  action: () => run("codeBlock") },
  { id: "table",    label: "Table",          icon: "⊞",     shortcut: "/tbl", action: () => run("table") },
  { id: "image",    label: "Image",          icon: "IMG",   shortcut: "/img", action: () => run("image") },
  { id: "divider",  label: "Divider",        icon: "—",     shortcut: "---",  action: () => run("hr") },
];

const filteredSlashCommands = computed(() => {
  if (!slashQuery.value) return slashCommands;
  const q = slashQuery.value.toLowerCase();
  return slashCommands.filter(c =>
    c.label.toLowerCase().includes(q) || c.id.toLowerCase().includes(q)
  );
});

function onSlashSelect(cmd: (typeof slashCommands)[0]) {
  const e = editor.value;
  if (e) {
    const { selection } = e.state;
    const from = selection.$from.start();
    const to = selection.$from.pos;
    e.chain().focus().deleteRange({ from, to }).run();
  }
  cmd.action();
  showSlashMenu.value = false;
  slashQuery.value = "";
}

// ── Last-modified display ─────────────────────────────────────────────────────

function fmtRelative(iso?: string) {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

defineExpose({ editor, run, isActive });
</script>

<template>
  <div class="notion-editor" :class="{ 'notion-editor--readonly': !editable }">

    <!-- ── Floating bubble toolbar (on text selection) ──────────────────── -->
    <BubbleMenu
      v-if="editor && editable"
      :editor="(editor as any)"
      :options="{ placement: 'top', offset: 8, flip: true, shift: true }"
      :append-to="getBodyEl"
    >
      <div class="bubble-toolbar">
        <div class="tb-group">
          <button class="tb-btn" :class="{ active: isActive('bold') }"      @mousedown.prevent="run('bold')"      title="Bold">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/><path d="M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/></svg>
          </button>
          <button class="tb-btn" :class="{ active: isActive('italic') }"    @mousedown.prevent="run('italic')"    title="Italic">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="4" x2="10" y2="4"/><line x1="14" y1="20" x2="5" y2="20"/><line x1="15" y1="4" x2="9" y2="20"/></svg>
          </button>
          <button class="tb-btn" :class="{ active: isActive('underline') }" @mousedown.prevent="run('underline')" title="Underline">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3v7a6 6 0 0 0 6 6 6 6 0 0 0 6-6V3"/><line x1="4" y1="21" x2="20" y2="21"/></svg>
          </button>
          <button class="tb-btn" :class="{ active: isActive('strike') }"    @mousedown.prevent="run('strike')"    title="Strikethrough">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><path d="M16 6c0 0-1.5-2-4-2s-5 1.5-5 4c0 2 2 3 5 4"/><path d="M8 18c0 0 1.5 2 4 2 2.5 0 5-1.5 5-4 0-2-2-3-5-4"/></svg>
          </button>
          <button class="tb-btn" :class="{ active: isActive('highlight') }" @mousedown.prevent="run('highlight')" title="Highlight">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 11-6 6v3h9l3-3"/><path d="m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4"/></svg>
          </button>
          <button class="tb-btn" :class="{ active: isActive('code') }"      @mousedown.prevent="run('code')"      title="Inline code">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          </button>
        </div>
        <div class="tb-sep" />
        <div class="tb-group">
          <button class="tb-btn tb-label" :class="{ active: isActive('heading', { level: 1 }) }" @mousedown.prevent="run('h1')">H1</button>
          <button class="tb-btn tb-label" :class="{ active: isActive('heading', { level: 2 }) }" @mousedown.prevent="run('h2')">H2</button>
          <button class="tb-btn tb-label" :class="{ active: isActive('heading', { level: 3 }) }" @mousedown.prevent="run('h3')">H3</button>
        </div>
        <div class="tb-sep" />
        <div class="tb-group">
          <button class="tb-btn" :class="{ active: isActive('bulletList') }"  @mousedown.prevent="run('bulletList')"  title="Bullet list">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="9" y1="6" x2="20" y2="6"/><line x1="9" y1="12" x2="20" y2="12"/><line x1="9" y1="18" x2="20" y2="18"/><circle cx="4" cy="6" r="1.2" fill="currentColor" stroke="none"/><circle cx="4" cy="12" r="1.2" fill="currentColor" stroke="none"/><circle cx="4" cy="18" r="1.2" fill="currentColor" stroke="none"/></svg>
          </button>
          <button class="tb-btn" :class="{ active: isActive('blockquote') }" @mousedown.prevent="run('blockquote')" title="Quote">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z"/></svg>
          </button>
          <button class="tb-btn" :class="{ active: isActive('link') }" @mousedown.prevent="promptLink" title="Link">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          </button>
        </div>
      </div>
    </BubbleMenu>

    <!-- ── Editor body ───────────────────────────────────────────────────── -->
    <EditorContent :editor="editor" class="editor-content" />

    <!-- ── Slash command menu ────────────────────────────────────────────── -->
    <Teleport to="body">
      <div
        v-if="showSlashMenu && editable"
        class="ep-slash-menu"
        :style="{ top: slashMenuCoords.top + 'px', left: slashMenuCoords.left + 'px' }"
      >
        <div class="ep-slash-header">Insert block</div>
        <template v-if="filteredSlashCommands.length">
          <button
            v-for="cmd in filteredSlashCommands"
            :key="cmd.id"
            class="ep-slash-item"
            @mousedown.prevent="onSlashSelect(cmd)"
          >
            <span class="ep-slash-icon">{{ cmd.icon }}</span>
            <span class="ep-slash-label">{{ cmd.label }}</span>
            <span class="ep-slash-shortcut">{{ cmd.shortcut }}</span>
          </button>
        </template>
        <div v-else class="ep-slash-empty">No results</div>
      </div>
    </Teleport>

    <!-- ── Mention dropdown ──────────────────────────────────────────────── -->
    <Teleport to="body">
      <div
        v-if="showMentionDrop && editable"
        class="ep-mention-drop"
        :style="{ top: mentionCoords.top + 'px', left: mentionCoords.left + 'px' }"
      >
        <div v-if="!mentionUsers.length" class="ep-mention-empty">No users found</div>
        <button
          v-for="u in mentionUsers"
          :key="u.name"
          class="ep-mention-item"
          @mousedown.prevent="pickMentionUser(u)"
        >
          <span class="ep-mention-name">{{ u.full_name || u.name }}</span>
          <span class="ep-mention-email">{{ u.name }}</span>
        </button>
      </div>
    </Teleport>

    <!-- ── Footer stats ──────────────────────────────────────────────────── -->
    <div v-if="editable" class="editor-footer">
      <span class="ef-stat">{{ wordCount }} {{ wordCount === 1 ? "word" : "words" }}</span>
      <span class="ef-stat">{{ charCount }} chars</span>
      <template v-if="lastModified">
        <span class="ef-sep">·</span>
        <span class="ef-meta">
          Last edited
          <template v-if="lastModifiedBy"> by <strong>{{ lastModifiedBy }}</strong></template>
          {{ fmtRelative(lastModified) }}
        </span>
      </template>
    </div>
  </div>
</template>

<style scoped>
.notion-editor {
  position: relative;
  background: var(--panel);
  border-radius: 8px;
}
.notion-editor--readonly { background: transparent; }

/* ── Bubble toolbar ──────────────────────────────────────────────────────── */
.bubble-toolbar {
  display: flex; align-items: center; gap: 2px; padding: 5px 8px;
  background: #1A1915; border: 1px solid rgba(255,255,255,.08); border-radius: 8px;
  box-shadow: 0 4px 20px rgba(26,25,21,.25), 0 1px 4px rgba(26,25,21,.12);
}
.tb-group { display: flex; gap: 1px; }
.tb-sep { width: 1px; height: 16px; background: rgba(255,255,255,.12); margin: 0 4px; flex-shrink: 0; }
.tb-btn {
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; padding: 0; border: none; border-radius: 4px;
  background: transparent; color: rgba(255,255,255,.65); cursor: pointer;
  transition: background 100ms, color 100ms; flex-shrink: 0;
}
.tb-btn:hover { background: rgba(255,255,255,.1); color: rgba(255,255,255,.95); }
.tb-btn.active { background: var(--accent); color: white; }
.tb-label { font-size: 10.5px; font-weight: 700; font-family: var(--font-sans); letter-spacing: -.01em; }

/* ── Editor content ──────────────────────────────────────────────────────── */
.editor-content :deep(.ProseMirror) {
  outline: none; padding: 16px 20px 28px; min-height: 120px;
  font-size: 14px; line-height: 1.72; color: var(--text);
  letter-spacing: -0.008em; font-family: var(--font-sans); caret-color: var(--accent);
}
.editor-content :deep(.ProseMirror > *:first-child) { margin-top: 0; }
.editor-content :deep(.ProseMirror p) { margin: 0.4em 0; }
.editor-content :deep(.ProseMirror p:first-child) { margin-top: 0; }
.editor-content :deep(.ProseMirror h1) {
  font-size: 21px; font-weight: 700; letter-spacing: -0.03em;
  margin: 1.4em 0 0.35em; line-height: 1.2; color: var(--text);
}
.editor-content :deep(.ProseMirror h2) {
  font-size: 16.5px; font-weight: 600; letter-spacing: -0.02em;
  margin: 1.2em 0 0.35em; line-height: 1.3; color: var(--text);
}
.editor-content :deep(.ProseMirror h3) {
  font-size: 14.5px; font-weight: 600; letter-spacing: -0.01em;
  margin: 1em 0 0.25em; line-height: 1.35; color: var(--text);
}
.editor-content :deep(.ProseMirror strong)    { font-weight: 600; }
.editor-content :deep(.ProseMirror em)        { font-style: italic; color: var(--text-2); }
.editor-content :deep(.ProseMirror u)         { text-decoration: underline; text-decoration-color: var(--accent); text-underline-offset: 3px; }
.editor-content :deep(.ProseMirror s)         { text-decoration: line-through; color: var(--text-3); }
.editor-content :deep(.ProseMirror code) {
  font-family: var(--font-mono); font-size: 12.5px;
  background: var(--bg-2); border: 1px solid var(--border); border-radius: 4px;
  padding: 1px 5px; color: var(--accent-2); letter-spacing: 0;
}
.editor-content :deep(.ProseMirror mark)      { background: rgba(202,138,4,.18); border-radius: 2px; padding: 1px 1px; }
.editor-content :deep(.ProseMirror a)         { color: var(--accent); text-decoration: underline; text-underline-offset: 2px; cursor: pointer; }
.editor-content :deep(.ProseMirror ul),
.editor-content :deep(.ProseMirror ol)        { padding-left: 1.4em; margin: 0.4em 0; }
.editor-content :deep(.ProseMirror li)        { margin: 0.2em 0; padding-left: 0.2em; }
.editor-content :deep(.ProseMirror li > p)    { margin: 0; }
/* Task list */
.editor-content :deep(.ProseMirror ul[data-type="taskList"]) { list-style: none; padding-left: 0; }
.editor-content :deep(.ProseMirror ul[data-type="taskList"] > li) { display: flex; align-items: flex-start; gap: 8px; margin: 0.25em 0; }
.editor-content :deep(.ProseMirror ul[data-type="taskList"] > li > label) { flex-shrink: 0; margin-top: 3px; }
.editor-content :deep(.ProseMirror ul[data-type="taskList"] input[type="checkbox"]) { width: 14px; height: 14px; cursor: pointer; accent-color: var(--accent); border-radius: 3px; }
.editor-content :deep(.ProseMirror ul[data-type="taskList"] li[data-checked="true"] > div) { text-decoration: line-through; color: var(--text-3); }
/* Quote */
.editor-content :deep(.ProseMirror blockquote) { border-left: 2px solid var(--accent); margin: 0.8em 0; padding: 0.35em 0 0.35em 14px; color: var(--text-2); font-style: italic; }
/* Code block */
.editor-content :deep(.ProseMirror pre) { background: var(--bg-2); border: 1px solid var(--border); border-radius: 6px; padding: 12px 16px; margin: 0.7em 0; overflow-x: auto; }
.editor-content :deep(.ProseMirror pre code) { background: none; border: none; padding: 0; color: var(--text); font-size: 12.5px; line-height: 1.6; letter-spacing: 0; }
/* HR */
.editor-content :deep(.ProseMirror hr) { border: none; border-top: 1px solid var(--border-2); margin: 1.4em 0; }
/* Placeholder */
.editor-content :deep(.ProseMirror p.is-editor-empty:first-child::before) { content: attr(data-placeholder); float: left; color: var(--text-3); pointer-events: none; height: 0; font-style: normal; }
/* Image */
.editor-content :deep(.ProseMirror img) { max-width: 100%; border-radius: 6px; margin: 0.5em 0; display: block; }
.editor-content :deep(.ProseMirror img.ProseMirror-selectednode) { outline: 2px solid var(--accent); }
/* Mention chip */
.editor-content :deep(.ep-mention) {
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  color: var(--accent-2); border-radius: 4px; padding: 1px 4px;
  font-weight: 500; font-size: 13px;
}
/* Table */
.editor-content :deep(.ProseMirror table) {
  border-collapse: collapse; width: 100%; margin: 0.8em 0;
  font-size: 13px; border-radius: 6px; overflow: hidden;
}
.editor-content :deep(.ProseMirror th) {
  background: var(--panel-2); font-weight: 600; padding: 6px 10px;
  border: 1px solid var(--border); text-align: left; font-size: 12px;
}
.editor-content :deep(.ProseMirror td) {
  padding: 6px 10px; border: 1px solid var(--border);
  vertical-align: top; min-width: 60px;
}
.editor-content :deep(.ProseMirror .selectedCell) { background: var(--accent-soft); }
.editor-content :deep(.ProseMirror .column-resize-handle) {
  position: absolute; right: -2px; top: 0; bottom: 0; width: 4px;
  background: var(--accent); pointer-events: none;
}

/* ── Footer ──────────────────────────────────────────────────────────────── */
.editor-footer {
  display: flex; align-items: center; gap: 8px; padding: 6px 20px;
  border-top: 1px solid var(--border); background: var(--panel-2);
  border-radius: 0 0 8px 8px; flex-wrap: wrap;
}
.ef-stat  { font-size: 10.5px; color: var(--text-3); font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.ef-sep   { font-size: 10.5px; color: var(--border-2); }
.ef-meta  { font-size: 10.5px; color: var(--text-3); }
.ef-meta strong { font-weight: 600; color: var(--text-2); }
</style>

<!-- Global styles for teleported menus -->
<style>
/* ── Slash menu ── */
.ep-slash-menu {
  position: fixed; z-index: 9999; width: 270px;
  background: var(--panel); border: 1px solid var(--border-2); border-radius: 8px;
  box-shadow: 0 8px 32px rgba(26,25,21,.12), 0 2px 6px rgba(26,25,21,.06);
  overflow: hidden; animation: epMenuEnter 100ms ease-out; padding: 4px;
}
.ep-slash-header {
  padding: 7px 12px 5px; font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-3);
  background: var(--panel-2); border-bottom: 1px solid var(--border);
  margin: -4px -4px 4px; border-radius: 8px 8px 0 0;
}
.ep-slash-item {
  display: flex; align-items: center; gap: 10px; padding: 7px 10px;
  cursor: pointer; width: 100%; border: none; background: transparent;
  text-align: left; border-radius: 5px; transition: background 100ms;
}
.ep-slash-item:hover { background: var(--accent-softer); }
.ep-slash-icon {
  width: 26px; height: 26px; display: flex; align-items: center; justify-content: center;
  background: var(--bg-2); border: 1px solid var(--border); border-radius: 5px;
  font-size: 10.5px; color: var(--text-2); font-family: var(--font-mono); font-weight: 600; flex-shrink: 0;
}
.ep-slash-label   { flex: 1; font-size: 13px; color: var(--text); font-weight: 450; }
.ep-slash-shortcut { font-size: 10.5px; color: var(--text-3); font-family: var(--font-mono); }
.ep-slash-empty   { padding: 12px; font-size: 12px; color: var(--text-3); text-align: center; }

/* ── Mention dropdown ── */
.ep-mention-drop {
  position: fixed; z-index: 9999; min-width: 220px;
  background: var(--panel); border: 1px solid var(--border-2); border-radius: 8px;
  box-shadow: 0 8px 32px rgba(26,25,21,.12); overflow: hidden;
  animation: epMenuEnter 100ms ease-out; padding: 4px;
}
.ep-mention-item {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px; width: 100%; padding: 7px 10px; background: none; border: none;
  cursor: pointer; font-family: inherit; font-size: 12.5px;
  text-align: left; border-radius: 5px; color: var(--text);
}
.ep-mention-item:hover { background: var(--row-hover); }
.ep-mention-name  { font-weight: 500; }
.ep-mention-email { font-size: 11px; color: var(--text-3); }
.ep-mention-empty { padding: 10px 12px; font-size: 12px; color: var(--text-3); text-align: center; }

@keyframes epMenuEnter {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Mobile bubble toolbar: anchor to bottom as a sheet ───────────────────── */
@media (max-width: 767px) {
  /* Tiptap renders BubbleMenu via a teleport; we target the tippy box */
  .tippy-box[data-theme~="bubble"] { width: 100% !important; max-width: 100vw !important; }
  .bubble-toolbar {
    flex-wrap: wrap; gap: 4px; padding: 8px 12px;
    border-radius: 0; border-left: none; border-right: none;
    width: 100%; box-sizing: border-box;
  }
  .tb-btn { width: 32px; height: 32px; }
}
</style>
