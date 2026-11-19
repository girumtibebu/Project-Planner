"""Work items are ERPNext Tasks. This module keeps the planner fields in step with ERPNext's own.

- `ep_state` (Planner State of the project's type) sets the fixed Task `status`.
- A status changed in desk moves the item to the first state of the matching group.
- `ep_sequence` numbers items per project, shown as <Project.ep_key>-<n>.
"""

import re

import frappe
from frappe import _

GROUPS = ("Backlog", "Unstarted", "Started", "Completed", "Cancelled")
GROUP_STATUS = {"Backlog": "Open", "Unstarted": "Open", "Started": "Working", "Completed": "Completed", "Cancelled": "Cancelled"}
STATUS_GROUP = {"Open": "Unstarted", "Working": "Started", "Pending Review": "Started", "Overdue": "Started", "Completed": "Completed", "Cancelled": "Cancelled"}
# used when a project has no type, or its type has no states: the ERPNext statuses themselves
FALLBACK_STATES = [
	{"name": "status:Open", "title": "Open", "state_group": "Unstarted", "color": "#6B7280", "is_default": 1, "is_review": 0, "status": "Open"},
	{"name": "status:Working", "title": "Working", "state_group": "Started", "color": "#F59E0B", "is_default": 0, "is_review": 0, "status": "Working"},
	{"name": "status:Pending Review", "title": "Pending Review", "state_group": "Started", "color": "#8B5CF6", "is_default": 0, "is_review": 1, "status": "Pending Review"},
	{"name": "status:Completed", "title": "Completed", "state_group": "Completed", "color": "#10B981", "is_default": 0, "is_review": 0, "status": "Completed"},
	{"name": "status:Cancelled", "title": "Cancelled", "state_group": "Cancelled", "color": "#9CA3AF", "is_default": 0, "is_review": 0, "status": "Cancelled"},
]
STATE_FIELDS = ["name", "title", "state_group", "color", "is_default", "is_review", "sort_order"]


def state_status(state):
	if state.get("status"):
		return state["status"]
	if state["state_group"] == "Started" and state.get("is_review"):
		return "Pending Review"
	return GROUP_STATUS[state["state_group"]]


def get_states(project_type):
	"""States of a Project Type in board order, or the fallback ERPNext statuses."""
	if project_type:
		rows = frappe.get_all(
			"Planner State",
			filters={"project_type": project_type},
			fields=STATE_FIELDS,
			order_by="sort_order asc, creation asc",
		)
		if rows:
			rows.sort(key=lambda row: GROUPS.index(row.state_group))
			for row in rows:
				row["status"] = state_status(row)
			return rows
	return [frappe._dict(state) for state in FALLBACK_STATES]


def project_type_of(project):
	return project and frappe.get_cached_value("Project", project, "project_type")


def before_validate_task(doc, method=None):
	"""Task before_validate: runs before ERPNext's own checks, so a state move is checked like a status change."""
	if not doc.project:
		return
	states = get_states(project_type_of(doc.project))
	if states[0]["name"].startswith("status:"):
		doc.ep_state = None
		return
	by_name = {state["name"]: state for state in states}
	if doc.ep_state and doc.ep_state not in by_name:
		frappe.throw(_("State {0} does not belong to this project's type.").format(frappe.bold(doc.ep_state)))

	state_changed = doc.is_new() or doc.has_value_changed("ep_state")
	status_changed = not doc.is_new() and doc.has_value_changed("status")
	if doc.ep_state and state_changed:
		apply_state(doc, by_name[doc.ep_state])
	elif status_changed or not doc.ep_state:
		doc.ep_state = state_for_status(states, doc.status)["name"]


def apply_state(doc, state):
	status = state_status(state)
	# ERPNext keeps Overdue on open items itself
	if doc.status == "Overdue" and status in ("Open", "Working"):
		return
	doc.status = status
	if state["state_group"] == "Completed":
		check_required_properties(doc)


def state_for_status(states, status):
	group = STATUS_GROUP.get(status, "Unstarted")
	if status == "Pending Review":
		review = [s for s in states if s["state_group"] == "Started" and s.get("is_review")]
		if review:
			return review[0]
	in_group = [s for s in states if s["state_group"] == group]
	if group == "Unstarted":
		defaults = [s for s in states if s.get("is_default")]
		if defaults and defaults[0]["state_group"] in ("Backlog", "Unstarted"):
			return defaults[0]
	return (in_group or states)[0]


def check_required_properties(doc):
	if not doc.type:
		return
	for prop in frappe.get_all(
		"Planner Property", filters={"task_type": doc.type, "is_required": 1}, fields=["label", "fieldname"]
	):
		if doc.get(prop.fieldname) in (None, "", 0):
			frappe.throw(_("{0} is required before this work item can be completed.").format(frappe.bold(prop.label)))


def before_insert_task(doc, method=None):
	"""Give the new work item the next number of its project."""
	if not doc.project or doc.ep_sequence:
		return
	current = frappe.db.get_value("Project", doc.project, "ep_next_sequence", for_update=True) or 0
	if not current:
		current = frappe.db.sql("select ifnull(max(ep_sequence), 0) from `tabTask` where project = %s", doc.project)[0][0]
	doc.ep_sequence = current + 1
	frappe.db.set_value("Project", doc.project, "ep_next_sequence", doc.ep_sequence, update_modified=False)


def validate_project(doc, method=None):
	if not doc.ep_key:
		return
	doc.ep_key = doc.ep_key.strip().upper()
	if not re.fullmatch(r"[A-Z][A-Z0-9]{1,5}", doc.ep_key):
		frappe.throw(_("The planner key is 2 to 6 letters or digits and starts with a letter, e.g. EVT."))
	if frappe.db.exists("Project", {"ep_key": doc.ep_key, "name": ["!=", doc.name]}):
		frappe.throw(_("The planner key {0} is already used by another project.").format(frappe.bold(doc.ep_key)))


def propose_key(project_name):
	"""A free key from the project's name: initials, else the first letters, plus a number when taken."""
	words = re.findall(r"[A-Za-z0-9]+", project_name or "") or ["PRJ"]
	base = "".join(w[0] for w in words[:4]).upper() if len(words) > 1 else words[0][:3].upper()
	base = base if re.match(r"[A-Z]", base) else "P" + base
	base = (base + "XX")[: max(2, min(len(base), 4))]
	key, n = base, 1
	while frappe.db.exists("Project", {"ep_key": key}):
		n += 1
		key = f"{base[:4]}{n}"
	return key


def ensure_key(project):
	key = frappe.db.get_value("Project", project, "ep_key")
	if key:
		return key
	key = propose_key(frappe.db.get_value("Project", project, "project_name"))
	frappe.db.set_value("Project", project, "ep_key", key, update_modified=False)
	return key
