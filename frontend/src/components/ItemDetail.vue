<template>
  <div v-if="!data" class="flex h-full items-center justify-center"><LoadingIndicator class="size-5" /></div>
  <div v-else class="flex h-full min-h-0 flex-col">
    <!-- header -->
    <div class="flex h-11 shrink-0 items-center gap-2 border-b border-outline-gray-1 px-4">
      <span :class="typeIndex[item.type]?.ep_icon || 'lucide-square-check'" class="size-4" :style="{ color: typeIndex[item.type]?.ep_color }" />
      <span class="text-sm text-ink-gray-5">{{ itemId(ctx.project, item) }}</span>
      <span v-if="item.parent_task" class="text-sm text-ink-gray-4">
        · sub-item of
        <button class="hover:underline" @click="emit('navigate', item.parent_task)">{{ parentLabel }}</button>
      </span>
      <div class="ml-auto flex items-center gap-1">
        <Tooltip text="Copy link"><Button variant="ghost" icon="lucide-link" @click="copyLink" /></Tooltip>
        <Tooltip v-if="mode !== 'page'" text="Open as page"><Button variant="ghost" icon="lucide-maximize-2" @click="emit('expand', item)" /></Tooltip>
        <Tooltip text="Open in desk"><Button variant="ghost" icon="lucide-external-link" @click="openDesk" /></Tooltip>
        <Dropdown v-if="data.can.write" :options="moreMenu">
          <Button variant="ghost" icon="lucide-ellipsis" />
        </Dropdown>
        <Button v-if="mode !== 'page'" variant="ghost" icon="lucide-x" @click="emit('close')" />
      </div>
    </div>

    <div class="flex min-h-0 flex-1" :class="mode === 'peek' ? 'flex-col overflow-y-auto' : ''">
      <!-- main column -->
      <div class="min-w-0 flex-1 px-6 py-5" :class="mode !== 'peek' && 'overflow-y-auto'">
        <textarea
          v-model="title"
          rows="1"
          class="w-full resize-none border-0 bg-transparent p-0 text-xl font-semibold text-ink-gray-9 focus:ring-0"
          :disabled="!data.can.write"
          @input="autoGrow"
          @blur="saveTitle"
          @keydown.enter.prevent="$event.target.blur()"
        />
        <TextEditor
          :key="item.name"
          class="mt-2"
          editor-class="prose-sm min-h-[6rem] max-w-none"
          :content="data.item.description"
          :editable="data.can.write"
          placeholder="Add a description…"
          :bubble-menu="true"
          @change="saveDescription"
        />

        <!-- sub-items -->
        <section class="mt-6">
          <div class="mb-1 flex items-center gap-2 text-sm font-medium text-ink-gray-7">
            <span class="lucide-list-tree size-4" /> Sub-work items
            <span class="text-ink-gray-4">{{ doneSubs }}/{{ data.sub_items.length }}</span>
          </div>
          <div
            v-for="sub in data.sub_items"
            :key="sub.name"
            class="flex h-9 cursor-pointer items-center gap-2 rounded px-2 hover:bg-surface-gray-1"
            @click="emit('navigate', sub.name)"
          >
            <span class="w-14 text-xs text-ink-gray-5">{{ itemId(ctx.project, sub) }}</span>
            <span class="min-w-0 flex-1 truncate text-sm">{{ sub.subject }}</span>
            <ItemProps :item="sub" :fields="['state', 'assignees', 'due_date']" @save="(d) => saveOther(sub, d)" />
          </div>
          <QuickAdd :defaults="{ parent_task: item.name, ep_action_category: item.ep_action_category }" @created="onSubCreated" />
        </section>

        <!-- relations -->
        <section class="mt-6">
          <div class="mb-1 flex items-center gap-2 text-sm font-medium text-ink-gray-7">
            <span class="lucide-git-branch size-4" /> Blocked by
          </div>
          <div v-for="dep in item.depends_on" :key="dep" class="group flex h-8 items-center gap-2 rounded px-2 hover:bg-surface-gray-1">
            <StateIcon :state="stateOf(lookup(dep))" />
            <button class="min-w-0 flex-1 truncate text-left text-sm" @click="emit('navigate', dep)">
              {{ itemId(ctx.project, lookup(dep)) }} {{ lookup(dep).subject || dep }}
            </button>
            <button v-if="data.can.write" class="lucide-x size-4 text-ink-gray-4 opacity-0 group-hover:opacity-100" @click="removeDep(dep)" />
          </div>
          <Picker v-if="data.can.write" :model-value="null" :options="depOptions" label="Work items" @change="addDep">
            <template #default="{ toggle }">
              <button class="flex items-center gap-2 rounded px-2 py-1.5 text-sm text-ink-gray-5 hover:bg-surface-gray-2" @click="toggle">
                <span class="lucide-plus size-4" /> Add blocking work item
              </button>
            </template>
          </Picker>
        </section>

        <!-- attachments -->
        <section class="mt-6">
          <div class="mb-1 flex items-center gap-2 text-sm font-medium text-ink-gray-7">
            <span class="lucide-paperclip size-4" /> Attachments
            <span class="text-ink-gray-4">{{ data.attachments.length }}</span>
          </div>
          <a
            v-for="file in data.attachments"
            :key="file.name"
            :href="file.file_url"
            target="_blank"
            class="flex h-8 items-center gap-2 rounded-lg px-2 text-sm text-ink-gray-7 hover:bg-surface-gray-1"
          ><span class="lucide-file size-4 text-ink-gray-5" /> {{ file.file_name }}</a>
          <FileUploader
            v-if="data.can.write"
            :upload-args="{ doctype: 'Task', docname: item.name, private: true }"
            @success="load"
          >
            <template #default="{ openFileSelector, uploading, progress }">
              <button class="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-ink-gray-5 hover:bg-surface-gray-2" :disabled="uploading" @click="openFileSelector">
                <span class="lucide-upload size-4" /> {{ uploading ? `Uploading ${progress}%` : 'Attach a file' }}
              </button>
            </template>
          </FileUploader>
        </section>

        <!-- activity -->
        <section class="mt-8">
          <div class="mb-3 text-sm font-medium text-ink-gray-7">Activity</div>
          <div class="flex flex-col gap-3">
            <div v-for="event in data.activity" :key="event.name" class="flex gap-2 text-sm">
              <Avatar :label="memberName(event.user)" :image="memberIndex[event.user]?.user_image" size="sm" />
              <div class="min-w-0 flex-1">
                <div class="text-ink-gray-5">
                  <span class="font-medium text-ink-gray-8">{{ memberName(event.user) }}</span>
                  <template v-if="event.kind === 'change'">
                    <span v-for="(c, i) in event.changes" :key="i">
                      {{ i ? ',' : '' }} set {{ c.field }} to <span class="text-ink-gray-8">{{ changeValue(c) }}</span>
                    </span>
                  </template>
                  <template v-else-if="event.kind === 'event'"> {{ stripHtml(event.content) }}</template>
                  <span class="ml-1 text-xs text-ink-gray-4">{{ timeAgo(event.at) }}</span>
                </div>
                <div v-if="event.kind === 'comment'" class="prose-sm mt-1 rounded-md border border-outline-gray-1 bg-surface-gray-1 px-3 py-2" v-html="event.content" />
              </div>
            </div>
          </div>
          <div class="mt-4 rounded-md border border-outline-gray-2">
            <TextEditor
              ref="commentEditor"
              :key="commentKey"
              editor-class="prose-sm min-h-[3rem] max-w-none px-3 py-2"
              placeholder="Add a comment…"
              :content="''"
              @change="(html) => (comment = html)"
            />
            <div class="flex justify-end border-t border-outline-gray-1 p-1.5">
              <Button variant="solid" size="sm" label="Comment" :loading="posting" :disabled="!hasComment" @click="postComment" />
            </div>
          </div>
        </section>
      </div>

      <!-- properties -->
      <aside
        class="shrink-0 px-4 py-5"
        :class="mode === 'peek' ? 'border-t border-outline-gray-1' : 'w-80 overflow-y-auto border-l border-outline-gray-1'"
      >
        <div class="mb-2 text-sm font-medium text-ink-gray-7">Properties</div>
        <ItemProps :item="item" vertical @save="save" />
        <div class="mt-4 text-xs text-ink-gray-4">
          Created by {{ memberName(item.owner) }} · {{ timeAgo(item.creation) }}<br />
          Updated {{ timeAgo(item.modified) }}
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Avatar, Button, Dropdown, FileUploader, LoadingIndicator, TextEditor, Tooltip, toast } from 'frappe-ui'
import ItemProps from './ItemProps.vue'
import Picker from './Picker.vue'
import QuickAdd from './QuickAdd.vue'
import StateIcon from './StateIcon.vue'
import { api } from '../api'
import { ctx, fail, memberIndex, memberName, stateIndex, stateOf, typeIndex } from '../store'
import { confirmAction } from '../confirm'
import { formatDate, itemId, timeAgo } from '../utils'

const props = defineProps({
  name: { type: String, required: true },
  items: { type: Array, default: () => [] }, // the project's loaded items, for relation labels
  mode: { type: String, default: 'peek' }, // peek | page
})
const emit = defineEmits(['close', 'expand', 'navigate', 'changed', 'deleted'])

const data = ref(null)
const title = ref('')
const comment = ref('')
const commentKey = ref(0)
const posting = ref(false)
const item = computed(() => data.value.item)

async function load() {
  try {
    data.value = await api.item(props.name)
    title.value = data.value.item.subject
  } catch (err) {
    fail(err)
    emit('close')
  }
}
watch(() => props.name, load, { immediate: true })

const lookup = (name) => props.items.find((i) => i.name === name) || data.value.sub_items.find((i) => i.name === name) || { name }
const parentLabel = computed(() => {
  const parent = lookup(item.value.parent_task)
  return parent.subject ? `${itemId(ctx.project, parent)} ${parent.subject}` : item.value.parent_task
})
const doneSubs = computed(() => data.value.sub_items.filter((s) => s.status === 'Completed').length)
const depOptions = computed(() =>
  props.items
    .filter((i) => i.name !== item.value.name && !item.value.depends_on.includes(i.name))
    .map((i) => ({ value: i.name, label: `${itemId(ctx.project, i)} ${i.subject}` })),
)
const hasComment = computed(() => stripHtml(comment.value).trim().length > 0)

async function save(patch) {
  try {
    const updated = await api.updateItem(item.value.name, patch)
    data.value.item = { ...data.value.item, ...updated }
    emit('changed', updated)
    if (!('description' in patch)) refreshActivity()
  } catch (err) {
    fail(err)
    load()
  }
}

async function saveOther(sub, patch) {
  try {
    const updated = await api.updateItem(sub.name, patch)
    Object.assign(sub, updated)
    emit('changed', updated)
  } catch (err) {
    fail(err)
  }
}

async function refreshActivity() {
  const fresh = await api.item(props.name)
  data.value.activity = fresh.activity
}

function saveTitle() {
  const subject = title.value.trim()
  if (!subject) title.value = item.value.subject
  else if (subject !== item.value.subject) save({ subject })
}

let descTimer = null
function saveDescription(html) {
  clearTimeout(descTimer)
  descTimer = setTimeout(() => {
    if (html !== item.value.description) save({ description: html })
  }, 800)
}

function autoGrow(event) {
  event.target.style.height = 'auto'
  event.target.style.height = `${event.target.scrollHeight}px`
}

function onSubCreated(sub) {
  data.value.sub_items.push(sub)
  emit('changed', sub)
  load()
}

const addDep = (name) => name && save({ depends_on: [...item.value.depends_on, name] })
const removeDep = (name) => save({ depends_on: item.value.depends_on.filter((d) => d !== name) })

async function postComment() {
  posting.value = true
  try {
    await api.comment(item.value.name, comment.value)
    comment.value = ''
    commentKey.value++
    await refreshActivity()
  } catch (err) {
    fail(err)
  } finally {
    posting.value = false
  }
}

const moreMenu = [
  {
    label: 'Delete work item',
    icon: 'lucide-trash-2',
    theme: 'red',
    onClick: async () => {
      const ok = await confirmAction({
        title: `Delete "${item.value.subject}"?`,
        message: 'The work item, its comments and attachments will be deleted. This cannot be undone.',
        action: 'Delete',
        danger: true,
      })
      if (!ok) return
      try {
        await api.deleteItem(item.value.name)
        emit('deleted', item.value.name)
      } catch (err) {
        fail(err)
      }
    },
  },
]

function copyLink() {
  const url = `${window.location.origin}/planner/${encodeURIComponent(ctx.project.name)}/item/${itemId(ctx.project, item.value)}`
  navigator.clipboard?.writeText(url)
  toast.success('Link copied')
}

function openDesk() {
  window.open(`/app/task/${encodeURIComponent(item.value.name)}`, '_blank')
}

function stripHtml(html) {
  return String(html || '').replace(/<[^>]+>/g, '')
}

function changeValue(change) {
  if (change.field === 'state') return stateIndex.value[change.to]?.title || change.to || 'none'
  if (['start date', 'due date'].includes(change.field)) return formatDate(change.to) || 'none'
  if (change.field === 'milestone') return change.to ? 'yes' : 'no'
  return change.to ?? 'none'
}
</script>
