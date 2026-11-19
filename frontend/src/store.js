/** The open project: its settings (states, types, members, views, pages) and its work items. */

import { computed, reactive } from 'vue'
import { toast } from 'frappe-ui'
import { api } from './api'
import { confirmAction } from './confirm'

export const ctx = reactive({
  project: null, // project fields
  states: [],
  types: [],
  properties: [],
  groups: [],
  members: [],
  views: [],
  parts: [], // part keys this project has
  part_options: [], // every part a project can have
  sidebar: {}, // { order: [view and page names], hidden: [shared view names] }
  hidden_views: [],
  needs_setup: false, // made in the desk, not set up in the planner yet
  pages: [],
  can: {},
  user: window.user,
  loading: false,
  error: null,
})

export async function loadProject(name) {
  ctx.loading = true
  ctx.error = null
  try {
    Object.assign(ctx, await api.project(name))
  } catch (err) {
    ctx.error = errorText(err)
  } finally {
    ctx.loading = false
  }
}

export const stateIndex = computed(() => Object.fromEntries(ctx.states.map((s) => [s.name, s])))
export const typeIndex = computed(() => Object.fromEntries(ctx.types.map((t) => [t.name, t])))
export const memberIndex = computed(() => Object.fromEntries(ctx.members.map((m) => [m.name, m])))
export const groupIndex = computed(() => Object.fromEntries(ctx.groups.map((g) => [g.name, g])))

/** The state an item shows: its Planner State, or the fallback state of its ERPNext status. */
export function stateOf(item) {
  return stateIndex.value[item.ep_state] || stateIndex.value[`status:${item.status}`] || ctx.states[0] || {}
}

// categories (Action Category) of the open project: created and removed where people use them
const CATEGORY_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444', '#14B8A6', '#EC4899', '#F97316', '#6366F1', '#84CC16']
export async function createCategory(title) {
  try {
    const doc = await api.insert({
      doctype: 'Action Category',
      title: title.trim(),
      project: ctx.project.name,
      color: CATEGORY_COLORS[ctx.groups.length % CATEGORY_COLORS.length],
      sort_order: ctx.groups.length,
    })
    ctx.groups = [...ctx.groups, doc]
    return doc.name
  } catch (err) {
    fail(err)
  }
}
export async function updateCategory(name, values) {
  try {
    await api.setValue('Action Category', name, values)
    ctx.groups = ctx.groups.map((g) => (g.name === name ? { ...g, ...values } : g))
  } catch (err) {
    fail(err)
  }
}
export async function deleteCategory(name) {
  const cat = ctx.groups.find((g) => g.name === name)
  const ok = await confirmAction({
    title: `Delete the category "${cat?.title}"?`,
    message: 'Its work items stay, without a category. This cannot be undone.',
    action: 'Delete',
    danger: true,
  })
  if (!ok) return false
  try {
    await api.deleteCategory(name)
    ctx.groups = ctx.groups.filter((g) => g.name !== name)
    return true
  } catch (err) {
    fail(err)
    return false
  }
}

export function propertiesOf(type) {
  return ctx.properties.filter((p) => p.task_type === type)
}

export function memberName(user) {
  return memberIndex.value[user]?.full_name || user
}

export function errorText(err) {
  const messages = err?.messages
  if (messages?.length) return messages.map((m) => String(m).replace(/<[^>]+>/g, '')).join(' ')
  return String(err?.message || err || 'Something went wrong').replace(/<[^>]+>/g, '')
}

export function fail(err) {
  toast.error(errorText(err))
}
