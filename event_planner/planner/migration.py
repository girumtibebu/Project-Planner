"""Manual, idempotent data steps for planner v2. Run one at a time, staging first:

    bench --site <site> execute event_planner.planner.migration.<function>

Each step can run again and gives the same result.
"""

import frappe

from event_planner.planner.api import to_html
from event_planner.planner.work_items import get_states, state_for_status

DEFAULT_STATES = [
	("Backlog", "Backlog", "#9CA3AF", 0, 0),
	("Todo", "Unstarted", "#6B7280", 1, 0),
	("In Progress", "Started", "#F59E0B", 0, 0),
	("In Review", "Started", "#8B5CF6", 0, 1),
	("Done", "Completed", "#10B981", 0, 0),
	("Cancelled", "Cancelled", "#EF4444", 0, 0),
]


def seed_states(project_types=None):
	"""Give every Project Type (or the ones named) the default states, when it has none."""
	project_types = frappe.parse_json(project_types) if project_types else frappe.get_all("Project Type", pluck="name")
	created = 0
	for project_type in project_types:
		if frappe.db.exists("Planner State", {"project_type": project_type}):
			continue
		for order, (title, group, color, is_default, is_review) in enumerate(DEFAULT_STATES):
			frappe.get_doc(
				{
					"doctype": "Planner State",
					"title": title,
					"project_type": project_type,
					"state_group": group,
					"color": color,
					"is_default": is_default,
					"is_review": is_review,
					"sort_order": order,
				}
			).insert(ignore_permissions=True)
			created += 1
	frappe.db.commit()
	return {"states_created": created}


def set_states():
	"""Set ep_state on tasks from their ERPNext status, for projects whose type has states."""
	updated = 0
	for project in frappe.get_all("Project", filters={"project_type": ["is", "set"]}, fields=["name", "project_type"]):
		states = get_states(project.project_type)
		if states[0]["name"].startswith("status:"):
			continue
		for task in frappe.get_all("Task", filters={"project": project.name, "ep_state": ["is", "not set"]}, fields=["name", "status"]):
			frappe.db.set_value("Task", task.name, "ep_state", state_for_status(states, task.status)["name"], update_modified=False)
			updated += 1
	frappe.db.commit()
	return {"tasks_updated": updated}


def number_items():
	"""Number existing tasks per project in creation order, after any numbers already given."""
	numbered = 0
	for project in frappe.get_all("Project", pluck="name"):
		last = frappe.db.sql("select ifnull(max(ep_sequence), 0) from `tabTask` where project = %s", project)[0][0]
		for task in frappe.get_all(
			"Task", filters={"project": project, "ep_sequence": ["in", [0, None]]}, pluck="name", order_by="creation asc"
		):
			last += 1
			frappe.db.set_value("Task", task, "ep_sequence", last, update_modified=False)
			numbered += 1
		frappe.db.set_value("Project", project, "ep_next_sequence", last, update_modified=False)
	frappe.db.commit()
	return {"tasks_numbered": numbered}


def migrate_pages():
	"""Copy each Event Brief and Event Debrief into a Planner Page (once)."""
	copied = 0
	for doctype, kind in (("Event Brief", "Brief"), ("Event Debrief", "Debrief")):
		for row in frappe.get_all(doctype, fields=["name", "project", "title", "template", "content", "version"]):
			if frappe.db.exists("Planner Page", {"project": row.project, "page_kind": kind, "title": row.title or kind}):
				continue
			frappe.get_doc(
				{
					"doctype": "Planner Page",
					"project": row.project,
					"title": row.title or kind,
					"page_kind": kind,
					"template": row.template,
					"content": to_html(row.content),
					"version": row.version or 1,
				}
			).insert(ignore_permissions=True)
			copied += 1
	frappe.db.commit()
	return {"pages_copied": copied}


def run_all():
	"""All steps in order, for a local or staging site."""
	return {**seed_states(), **set_states(), **number_items(), **migrate_pages()}
