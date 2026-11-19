/** Small pure helpers shared by the layouts. */

export const STATE_GROUPS = ['Backlog', 'Unstarted', 'Started', 'Completed', 'Cancelled']
export const PRIORITIES = ['Urgent', 'High', 'Medium', 'Low']
export const PRIORITY_ICON = {
  Urgent: 'lucide-circle-alert',
  High: 'lucide-signal-high',
  Medium: 'lucide-signal-medium',
  Low: 'lucide-signal-low',
}
export const PRIORITY_COLOR = { Urgent: 'text-ink-red-4', High: 'text-ink-amber-3', Medium: 'text-ink-gray-6', Low: 'text-ink-gray-4' }

// The icons a work item type may use. Listed here as literals so Tailwind builds their mask classes.
export const TYPE_ICONS = [
  'lucide-square-check', 'lucide-flag', 'lucide-milestone', 'lucide-calendar-clock', 'lucide-truck',
  'lucide-video', 'lucide-camera', 'lucide-clapperboard', 'lucide-mic', 'lucide-music', 'lucide-lightbulb',
  'lucide-palette', 'lucide-pen-tool', 'lucide-package', 'lucide-map-pin', 'lucide-users', 'lucide-phone',
  'lucide-file-text', 'lucide-receipt', 'lucide-hammer', 'lucide-wrench', 'lucide-sparkles', 'lucide-bug',
  'lucide-star', 'lucide-circle-dot', 'lucide-phone-call', 'lucide-package-search',
]

export const COLORS = ['#6B7280', '#EF4444', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#EC4899', '#14B8A6', '#9CA3AF']

export function itemId(project, item) {
  return project?.key && item?.ep_sequence ? `${project.key}-${item.ep_sequence}` : item?.name
}

export function toDate(value) {
  if (!value) return null
  if (value instanceof Date) return new Date(value.getTime())
  // date-only strings are local days, not UTC midnight
  const text = String(value)
  const d = new Date(text.length === 10 ? `${text}T00:00:00` : text.replace(' ', 'T'))
  return Number.isNaN(d.getTime()) ? null : d
}

export function dayKey(date) {
  const d = toDate(date)
  if (!d) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function addDays(date, days) {
  const d = new Date(toDate(date))
  d.setDate(d.getDate() + days)
  return d
}

export function diffDays(a, b) {
  const start = toDate(dayKey(a))
  const end = toDate(dayKey(b))
  return Math.round((end - start) / 86400000)
}

/** Datetime string ERPNext accepts, keeping the time of day of `original` when there is one. */
export function withDay(day, original) {
  const time = original && String(original).length > 10 ? String(original).slice(11, 19) : '00:00:00'
  return `${dayKey(day)} ${time}`
}

export function formatDate(value, opts = { day: 'numeric', month: 'short' }) {
  const d = toDate(value)
  return d ? d.toLocaleDateString(undefined, opts) : ''
}

export function isOverdue(item) {
  const end = toDate(item.exp_end_date)
  return Boolean(end) && !['Completed', 'Cancelled'].includes(item.status) && dayKey(end) < dayKey(new Date())
}

export function timeAgo(value) {
  const d = toDate(value)
  if (!d) return ''
  const s = Math.round((Date.now() - d.getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  if (s < 86400 * 30) return `${Math.floor(s / 86400)}d ago`
  return formatDate(d, { day: 'numeric', month: 'short', year: 'numeric' })
}

/**
 * Put each sub-item right after its parent (and its parent's earlier sub-items), keeping the
 * given order among siblings. A sub-item whose parent is not in the list stays where it is.
 * Returns the items in that order, and a Map of name -> depth for indenting.
 */
export function treeOrder(items) {
  const present = new Set(items.map((i) => i.name))
  const children = new Map()
  const roots = []
  for (const item of items) {
    if (item.parent_task && present.has(item.parent_task) && item.parent_task !== item.name) {
      if (!children.has(item.parent_task)) children.set(item.parent_task, [])
      children.get(item.parent_task).push(item)
    } else roots.push(item)
  }
  const out = []
  const depth = new Map()
  const seen = new Set()
  const walk = (item, level) => {
    if (seen.has(item.name)) return // a parent loop in bad data
    seen.add(item.name)
    out.push(item)
    depth.set(item.name, level)
    for (const child of children.get(item.name) || []) walk(child, level + 1)
  }
  roots.forEach((item) => walk(item, 0))
  items.forEach((item) => walk(item, 0)) // items in a parent loop have no root: list them flat
  return { items: out, depth }
}

/** Group items by a key function, keeping the order of `keys` and adding unknown keys at the end. */
export function groupItems(items, keyOf, keys = []) {
  const groups = new Map(keys.map((k) => [k, []]))
  for (const item of items) {
    const values = [].concat(keyOf(item))
    for (const value of values.length ? values : ['']) {
      if (!groups.has(value)) groups.set(value, [])
      groups.get(value).push(item)
    }
  }
  return groups
}

export function escapeHtml(text) {
  return String(text ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c])
}
