import { call } from 'frappe-ui'

const P = 'event_planner.planner.api.'
const PARTS = 'event_planner.planner.parts.'
const BOARDS = 'event_planner.planner.boards.'
const json = (value) => (value == null ? undefined : JSON.stringify(value))

export const api = {
  projects: (search) =>
    call('frappe.client.get_list', {
      doctype: 'Project',
      fields: ['name', 'project_name', 'status', 'ep_key', 'expected_start_date', 'expected_end_date', 'percent_complete', 'modified'],
      filters: search ? [['project_name', 'like', `%${search}%`]] : [],
      order_by: 'modified desc',
      limit_page_length: 50,
    }),
  project: (project) => call(P + 'get_project', { project }),
  home: () => call(P + 'get_home'),
  completeItem: (name) => call(P + 'complete_item', { name }),
  items: (project, filters, orderBy) => call(P + 'list_items', { project, filters: json(filters), order_by: orderBy }),
  item: (name) => call(P + 'get_item', { name }),
  createItem: (project, data) => call(P + 'create_item', { project, data: json(data) }),
  updateItem: (name, data) => call(P + 'update_item', { name, data: json(data) }),
  bulkUpdate: (names, data) => call(P + 'bulk_update', { names: json(names), data: json(data) }),
  reorder: (names) => call(P + 'reorder', { names: json(names) }),
  deleteItem: (name) => call(P + 'delete_item', { name }),
  comment: (name, content) => call(P + 'add_comment', { name, content }),
  saveView: (data) => call(P + 'save_view', { data: json(data) }),
  deleteCategory: (name) => call(P + 'delete_category', { name }),
  pageTemplates: () => call(P + 'page_templates'),
  createPage: (values) => call(P + 'create_page', values),

  clashes: (project) => call('event_planner.planner.clashes.get_clashes', { project }),

  newProjectOptions: () => call(PARTS + 'new_project_options'),
  searchSalesOrders: (txt) => call(PARTS + 'search_sales_orders', { txt }),
  createProject: (data, template) => call(PARTS + 'create_project', { data: json(data), template }),
  addPart: (project, part) => call(PARTS + 'add_part', { project, part }),
  markReviewed: (page) => call(PARTS + 'mark_reviewed', { page }),
  saveAsTemplate: (project, title, description) => call(BOARDS + 'save_as_template', { project, title, description }),
  setupProject: (project, template, blank) => call(BOARDS + 'setup_project', { project, template, blank: blank ? 1 : 0 }),
  setSidebarOrder: (project, names) => call(BOARDS + 'set_sidebar_order', { project, names: json(names) }),
  hideView: (project, view) => call(BOARDS + 'hide_view', { project, view }),
  showView: (project, view) => call(BOARDS + 'show_view', { project, view }),
  notifyTeam: (project, note, preview) => call('event_planner.planner.notify.notify_team', { project, note, preview: preview ? 1 : 0 }),

  // standard document calls (DocType permissions apply)
  get: (doctype, name) => call('frappe.client.get', { doctype, name }),
  insert: (doc) => call('frappe.client.insert', { doc }),
  setValue: (doctype, name, fieldname, value) =>
    call('frappe.client.set_value', { doctype, name, fieldname: typeof fieldname === 'string' ? fieldname : json(fieldname), value }),
  remove: (doctype, name) => call('frappe.client.delete', { doctype, name }),
  list: (doctype, fields, filters, orderBy = 'creation asc') =>
    call('frappe.client.get_list', { doctype, fields, filters, order_by: orderBy, limit_page_length: 500 }),
}
