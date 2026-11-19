/** Group-by definitions shared by List and Kanban: key of an item, ordered keys, label and icon of a key. */

import { ctx, groupIndex, memberName, stateIndex, stateOf } from './store'
import { PRIORITIES, PRIORITY_COLOR, PRIORITY_ICON, STATE_GROUPS, dayKey, formatDate, withDay } from './utils'

/** Group-by choices: the fixed ones plus every Dropdown property (e.g. Booking status). */
export function groupByOptions() {
  const props = ctx.properties.filter((p) => p.property_type === 'Dropdown').map((p) => ({ value: p.fieldname, label: `${p.label} (${p.task_type})` }))
  return [...GROUP_BY, ...props]
}

export const GROUP_BY = [
  { value: 'day', label: 'Day' },
  { value: 'state', label: 'State' },
  { value: 'state_group', label: 'State group' },
  { value: 'priority', label: 'Priority' },
  { value: 'assignee', label: 'Assignee' },
  { value: 'type', label: 'Type' },
  { value: 'group', label: 'Category' },
  { value: 'created_by', label: 'Created by' },
  { value: 'none', label: 'None' },
]

export const ORDER_BY = [
  { value: 'manual', label: 'Manual' },
  { value: 'sequence', label: 'ID' },
  { value: 'priority', label: 'Priority' },
  { value: 'due_date', label: 'Due date' },
  { value: 'start_date', label: 'Start date' },
  { value: 'updated_on', label: 'Last updated' },
  { value: 'created_on', label: 'Created' },
]

export function grouper(by) {
  const property = ctx.properties.find((p) => p.fieldname === by)
  if (property) {
    return {
      keyOf: (item) => item[by] || '',
      keys: () => [...(property.options || '').split('\n').filter(Boolean), ''],
      label: (k) => k || `No ${property.label.toLowerCase()}`,
      iconClass: () => 'lucide-tag',
      patch: (k) => ({ [by]: k || null }),
    }
  }
  switch (by) {
    case 'day':
      return {
        keyOf: (item) => dayKey(item.exp_start_date),
        keys: () => [],
        label: (k) => (k ? formatDate(k, { weekday: 'long', day: 'numeric', month: 'short' }) : 'No date'),
        iconClass: () => 'lucide-calendar-days',
        // moving to another day keeps the time of day; quick add on a day starts at 09:00
        patch: (k, item) => (k ? { exp_start_date: item?.exp_start_date ? withDay(k, item.exp_start_date) : `${k} 09:00:00` } : null),
      }
    case 'state':
      return {
        keyOf: (item) => stateOf(item).name,
        keys: () => ctx.states.map((s) => s.name),
        label: (k) => stateIndex.value[k]?.title || k,
        state: (k) => stateIndex.value[k],
        // dropping an item in this column sets…
        patch: (k) => ({ ep_state: k }),
      }
    case 'state_group':
      return {
        keyOf: (item) => stateOf(item).state_group,
        keys: () => STATE_GROUPS,
        label: (k) => k,
        state: (k) => ({ state_group: k, color: ctx.states.find((s) => s.state_group === k)?.color }),
        patch: (k) => {
          const first = ctx.states.find((s) => s.state_group === k)
          return first ? { ep_state: first.name } : null
        },
      }
    case 'priority':
      return {
        keyOf: (item) => item.priority || '',
        keys: () => [...PRIORITIES, ''],
        label: (k) => k || 'No priority',
        iconClass: (k) => `${PRIORITY_ICON[k] || 'lucide-minus'} ${PRIORITY_COLOR[k] || ''}`,
        patch: (k) => ({ priority: k || null }),
      }
    case 'assignee':
      return {
        keyOf: (item) => item.assignees,
        keys: () => [],
        label: (k) => (k ? memberName(k) : 'Unassigned'),
        user: (k) => k,
        // moving from one assignee's column to another swaps that assignee
        patch: (k, item, from) => ({
          assignees: [...new Set([...(item.assignees || []).filter((u) => u !== from), ...(k ? [k] : [])])],
        }),
      }
    case 'type':
      return {
        keyOf: (item) => item.type || '',
        keys: () => [...ctx.types.map((t) => t.name), ''],
        label: (k) => k || 'No type',
        iconClass: (k) => ctx.types.find((t) => t.name === k)?.ep_icon || 'lucide-square-check',
        patch: (k) => ({ type: k || null }),
      }
    case 'group':
      return {
        keyOf: (item) => item.ep_action_category || '',
        keys: () => [...ctx.groups.map((g) => g.name), ''],
        label: (k) => groupIndex.value[k]?.title || 'No category',
        iconClass: () => 'lucide-boxes',
        color: (k) => groupIndex.value[k]?.color,
        patch: (k) => ({ ep_action_category: k || null }),
      }
    case 'created_by':
      return {
        keyOf: (item) => item.owner,
        keys: () => [],
        label: (k) => memberName(k),
        user: (k) => k,
        patch: () => null,
      }
    default:
      return { keyOf: () => 'all', keys: () => ['all'], label: () => 'All work items', patch: () => ({}) }
  }
}
