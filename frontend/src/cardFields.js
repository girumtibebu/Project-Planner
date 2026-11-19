/** Which details a card shows. Chosen per view in Display, saved in the view's `display.card_fields`. */

export const CARD_FIELDS = [
  { value: 'id', label: 'ID' },
  { value: 'type', label: 'Type' },
  { value: 'state', label: 'State' },
  { value: 'priority', label: 'Priority' },
  { value: 'assignees', label: 'Assignees' },
  { value: 'start_date', label: 'Start date' },
  { value: 'due_date', label: 'Due date' },
  { value: 'time', label: 'Time' },
  { value: 'labels', label: 'Labels' },
  { value: 'group', label: 'Category' },
  { value: 'estimate', label: 'Estimate' },
  { value: 'sub_items', label: 'Sub-item count' },
  { value: 'properties', label: 'Type properties' },
]

export const DEFAULT_CARD_FIELDS = ['id', 'type', 'priority', 'assignees', 'due_date', 'labels', 'group']
export const DEFAULT_LIST_FIELDS = ['id', 'type', 'state', 'priority', 'assignees', 'due_date', 'labels', 'group']
