"""Whitelisted API for the planner SPA. Every call checks the user's permission on the Project or Task."""

import json

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as add_assignment
from frappe.desk.form.assign_to import remove as remove_assignment
from frappe.query_builder.functions import Max
from frappe.utils import cint

from event_planner.planner import boards, parts
from event_planner.planner.filters import to_list_filters, to_order_by, validate_order_by
from event_planner.planner.work_items import ensure_key, get_states

ITEM_FIELDS = [
	"name",
	"subject",
	"status",
	"ep_state",
	"ep_sequence",
	"priority",
	"type",
	"ep_action_category",
	"parent_task",
	"is_group",
	"is_milestone",
	"exp_start_date",
	"exp_end_date",
	"progress",
	"expected_time",
	"color",
	"_assign",
	"_user_tags",
	"ep_sort_order",
	"owner",
	"creation",
	"modified",
]
# fields the SPA may set on a work item (properties are added per type)
EDITABLE = {
	"subject",
	"ep_state",
	"status",
	"priority",
	"type",
	"ep_action_category",
	"parent_task",
	"is_group",
	"is_milestone",
	"exp_start_date",
	"exp_end_date",
	"progress",
	"expected_time",
	"description",
	"ep_sort_order",
}
MAX_ITEMS = 2000


def check_project(project, ptype="read"):
	if not project or not frappe.db.exists("Project", project):
		frappe.throw(_("Project {0} not found").format(project), frappe.DoesNotExistError)
	frappe.has_permission("Project", ptype, project, throw=True)


def properties():
	return frappe.get_all(
		"Planner Property",
		fields=["name", "label", "task_type", "property_type", "options", "is_required", "fieldname", "sort_order"],
		order_by="sort_order asc, creation asc",
	)


def property_fieldnames():
	meta = frappe.get_meta("Task")
	return [p.fieldname for p in properties() if meta.has_field(p.fieldname)]


@frappe.whitelist()
def get_project(project):
	"""Everything the planner needs to draw one project."""
	check_project(project)
	can_write = bool(frappe.has_permission("Project", "write", project))
	if can_write:
		ensure_key(project)
	doc = frappe.get_doc("Project", project)
	roles = set(frappe.get_roles())
	return {
		"project": {
			"name": doc.name,
			"project_name": doc.project_name,
			"status": doc.status,
			"project_type": doc.project_type,
			"key": doc.ep_key,
			"customer": doc.customer,
			"sales_order": doc.sales_order,
			"cost_center": doc.cost_center,
			"company": doc.company,
			"expected_start_date": doc.expected_start_date,
			"expected_end_date": doc.expected_end_date,
			"percent_complete": doc.percent_complete,
			"priority": doc.priority,
			"location": doc.get("ep_location"),
		},
		"states": get_states(doc.project_type),
		"types": frappe.get_all("Task Type", fields=["name", "ep_icon", "ep_color", "description"], order_by="name asc"),
		"properties": properties(),
		"groups": frappe.get_all(
			"Action Category",
			filters={"project": project},
			fields=["name", "title", "color", "sort_order"],
			order_by="sort_order asc, creation asc",
		),
		"members": frappe.get_all(
			"User",
			filters={"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]},
			fields=["name", "full_name", "user_image"],
			order_by="full_name asc",
			limit=500,
		),
		"views": get_views(project, doc.project_type),
		"pages": frappe.get_all(
			"Planner Page",
			filters={"project": project},
			fields=["name", "title", "icon", "parent_page", "page_kind", "department", "boq_status", "sort_order", "is_locked", "owner", "modified"],
			order_by="sort_order asc, creation asc",
		),
		"parts": parts.enabled_parts(project),
		"part_options": parts.PARTS,
		"sidebar": frappe.parse_json(doc.get("ep_sidebar") or "{}") or {},
		"hidden_views": hidden_views(doc),
		# made in the desk (e.g. from a Sales Order) and never opened in the planner
		"needs_setup": boards.needs_setup(project),
		"can": {
			"write": can_write,
			"manage": bool(roles & {"Projects Manager", "System Manager"}),
		},
		"user": frappe.session.user,
	}


def get_views(project, project_type):
	or_filters = [["project", "=", project]]
	if project_type:
		or_filters.append(["project_type", "=", project_type])
	views = frappe.get_list(
		"Planner View",
		or_filters=or_filters,
		fields=["name", "title", "project", "project_type", "layout", "filters", "group_by", "order_by", "display", "is_personal", "owner", "sort_order", "part", "is_locked"],
		order_by="sort_order asc, creation asc",
	)
	# a template view shows when the project has its part, unless the project keeps its own copy
	enabled = set(parts.stored_view_parts(project))
	copied = {v.part for v in views if v.project and v.part}
	hidden = set((frappe.parse_json(frappe.db.get_value("Project", project, "ep_sidebar") or "{}") or {}).get("hidden", []))
	return [
		v
		for v in views
		if v.name not in hidden and not (v.project_type and v.part and (v.part not in enabled or v.part in copied))
	]


def hidden_views(doc):
	"""Shared views (without a part) this project hid, so the sidebar can offer them back."""
	names = (frappe.parse_json(doc.get("ep_sidebar") or "{}") or {}).get("hidden", [])
	return frappe.get_all("Planner View", filters={"name": ["in", names or [""]]}, fields=["name", "title"])


def states_by_group(project):
	groups = {}
	for state in get_states(frappe.db.get_value("Project", project, "project_type")):
		groups.setdefault(state["state_group"], []).append(state["name"])
	return groups


@frappe.whitelist()
def list_items(project, filters=None, order_by=None):
	"""Work items of one project, filtered by a view."""
	check_project(project)
	filters = frappe.parse_json(filters) or []
	validate_order_by(order_by)
	extra = property_fieldnames()
	rows = frappe.get_list(
		"Task",
		filters=to_list_filters(project, filters, states_by_group(project)),
		fields=ITEM_FIELDS + extra,
		order_by=to_order_by(order_by),
		limit_page_length=MAX_ITEMS,
	)
	return describe(rows)


def describe(rows):
	names = [row.name for row in rows]
	depends = {}
	if names:
		for dep in frappe.get_all(
			"Task Depends On", filters={"parent": ["in", names], "parenttype": "Task"}, fields=["parent", "task"]
		):
			depends.setdefault(dep.parent, []).append(dep.task)
	for row in rows:
		row["assignees"] = json.loads(row.pop("_assign") or "[]")
		row["labels"] = [tag for tag in (row.pop("_user_tags") or "").split(",") if tag]
		row["depends_on"] = depends.get(row.name, [])
	return rows


def load_item(name):
	extra = property_fieldnames()
	row = frappe.db.get_value("Task", name, ITEM_FIELDS + extra, as_dict=True)
	return describe([row])[0]


def apply_changes(doc, data):
	# projects without planner states use ERPNext statuses, sent as "status:Open"
	if (data.get("ep_state") or "").startswith("status:"):
		data = {**data, "status": data["ep_state"].split(":", 1)[1], "ep_state": None}
	allowed = EDITABLE | set(property_fieldnames())
	for field, value in data.items():
		if field in allowed:
			doc.set(field, value)
		elif field not in ("assignees", "labels", "depends_on"):
			frappe.throw(_("Field {0} cannot be set from the planner").format(frappe.bold(field)))
	if "depends_on" in data:
		doc.set("depends_on", [{"task": task} for task in data["depends_on"] or []])
	if doc.parent_task:
		make_group(doc.parent_task)


def make_group(task):
	"""ERPNext only accepts a parent that is a group task."""
	if not frappe.db.get_value("Task", task, "is_group"):
		parent = frappe.get_doc("Task", task)
		parent.check_permission("write")
		parent.is_group = 1
		parent.save()


def sync_assignees(doc, users):
	current = set(json.loads(doc.get("_assign") or "[]"))
	wanted = set(users or [])
	for user in wanted - current:
		add_assignment({"assign_to": [user], "doctype": "Task", "name": doc.name})
	for user in current - wanted:
		remove_assignment("Task", doc.name, user)


def sync_labels(doc, labels):
	from frappe.desk.doctype.tag.tag import add_tag, remove_tag

	current = {tag for tag in (doc.get("_user_tags") or "").split(",") if tag}
	wanted = {label.strip() for label in labels or [] if label.strip()}
	for tag in wanted - current:
		add_tag(tag, "Task", doc.name)
	for tag in current - wanted:
		remove_tag(tag, "Task", doc.name)


@frappe.whitelist(methods=["POST"])
def create_item(project, data):
	check_project(project, "read")
	frappe.has_permission("Task", "create", throw=True)
	data = frappe.parse_json(data) or {}
	if not (data.get("subject") or "").strip():
		frappe.throw(_("Give the work item a title"))
	doc = frappe.new_doc("Task")
	doc.project = project
	apply_changes(doc, data)
	if not data.get("type"):
		doc.type = frappe.db.get_value("Task Type", {"ep_is_default": 1})
	if "ep_sort_order" not in data:  # a new item goes to the end of a hand-ordered list
		task = frappe.qb.DocType("Task")
		last = frappe.qb.from_(task).select(Max(task.ep_sort_order)).where(task.project == project).run()
		doc.ep_sort_order = cint(last[0][0] if last else 0) + 1
	doc.insert()
	if data.get("assignees"):
		sync_assignees(doc, data["assignees"])
	if data.get("labels"):
		sync_labels(doc, data["labels"])
	return load_item(doc.name)


@frappe.whitelist(methods=["POST"])
def update_item(name, data):
	doc = frappe.get_doc("Task", name)
	doc.check_permission("write")
	data = frappe.parse_json(data) or {}
	fields ={k: v for k, v in data.items() if k not in ("assignees", "labels")}
	if fields:
		apply_changes(doc, fields)
		doc.save()
	if "assignees" in data:
		sync_assignees(doc.reload() or doc, data["assignees"])
	if "labels" in data:
		sync_labels(doc.reload() or doc, data["labels"])
	return load_item(name)


@frappe.whitelist(methods=["POST"])
def bulk_update(names, data):
	names = frappe.parse_json(names) or []
	if len(names) > 200:
		frappe.throw(_("Update at most 200 work items at once"))
	return [update_item(name, data) for name in names]


@frappe.whitelist(methods=["POST"])
def reorder(names):
	"""Manual order inside a list group or Kanban column."""
	for index, name in enumerate(frappe.parse_json(names) or []):
		frappe.has_permission("Task", "write", name, throw=True)
		frappe.db.set_value("Task", name, "ep_sort_order", index, update_modified=False)


@frappe.whitelist(methods=["POST"])
def delete_item(name):
	frappe.delete_doc("Task", name)


@frappe.whitelist()
def get_item(name):
	"""One work item with description, sub-items, attachments and activity."""
	doc = frappe.get_doc("Task", name)
	doc.check_permission("read")
	item = load_item(name)
	item["description"] = doc.description
	item["project"] = doc.project
	sub = frappe.get_list("Task", filters={"parent_task": name}, fields=ITEM_FIELDS, order_by="ep_sort_order asc, ep_sequence asc")  # as in the list
	return {
		"item": item,
		"sub_items": describe(sub),
		"attachments": frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Task", "attached_to_name": name},
			fields=["name", "file_name", "file_url", "file_size", "creation"],
			order_by="creation asc",
		),
		"activity": activity(name),
		"can": {"write": bool(doc.has_permission("write"))},
	}


TRACKED = {
	"subject": "title",
	"status": "status",
	"ep_state": "state",
	"priority": "priority",
	"type": "type",
	"exp_start_date": "start date",
	"exp_end_date": "due date",
	"parent_task": "parent",
	"ep_action_category": "group",
	"progress": "progress",
	"is_milestone": "milestone",
}


def activity(name):
	"""Comments and field changes, oldest first."""
	events = []
	for comment in frappe.get_all(
		"Comment",
		filters={"reference_doctype": "Task", "reference_name": name, "comment_type": ["in", ["Comment", "Assigned", "Assignment Completed", "Attachment"]]},
		fields=["name", "comment_type", "content", "owner", "comment_email", "creation"],
		order_by="creation asc",
		limit=200,
	):
		events.append(
			{
				"kind": "comment" if comment.comment_type == "Comment" else "event",
				"name": comment.name,
				"type": comment.comment_type,
				"content": comment.content,
				"user": comment.comment_email or comment.owner,
				"at": comment.creation,
			}
		)
	for version in frappe.get_all(
		"Version",
		filters={"ref_doctype": "Task", "docname": name},
		fields=["name", "data", "owner", "creation"],
		order_by="creation asc",
		limit=200,
	):
		data = frappe.parse_json(version.data) or {}
		changes = [
			{"field": TRACKED[row[0]], "from": row[1], "to": row[2]}
			for row in data.get("changed", [])
			if row[0] in TRACKED
		]
		# the state already says what the derived ERPNext status says
		if any(c["field"] == "state" for c in changes):
			changes = [c for c in changes if c["field"] != "status"]
		if changes:
			events.append({"kind": "change", "name": version.name, "changes": changes, "user": version.owner, "at": version.creation})
	events.sort(key=lambda event: str(event["at"]))
	return events


@frappe.whitelist(methods=["POST"])
def add_comment(name, content):
	doc = frappe.get_doc("Task", name)
	doc.check_permission("read")
	if not (content or "").strip():
		frappe.throw(_("Write a comment first"))
	comment = doc.add_comment("Comment", content)
	return {"name": comment.name}


@frappe.whitelist(methods=["POST"])
def delete_category(name):
	"""Delete a category of a project; its work items stay, without a category."""
	project = frappe.db.get_value("Action Category", name, "project")
	check_project(project, "write")
	frappe.db.set_value("Task", {"ep_action_category": name, "project": project}, "ep_action_category", None)
	frappe.delete_doc("Action Category", name)


@frappe.whitelist(methods=["POST"])
def save_view(data):
	"""Insert or update a saved view; the view's own validation checks filters and permissions."""
	data = frappe.parse_json(data) or {}
	for field in ("filters", "display"):
		if field in data and not isinstance(data[field], str):
			data[field] = json.dumps(data[field])
	allowed = {"title", "project", "project_type", "layout", "filters", "group_by", "order_by", "display", "is_personal", "sort_order", "part", "is_locked"}
	values = {k: v for k, v in data.items() if k in allowed}
	if data.get("name"):
		doc = frappe.get_doc("Planner View", data["name"])
		doc.update(values)
		doc.save()
	else:
		doc = frappe.get_doc({"doctype": "Planner View", **values})
		doc.insert()
	return doc.as_dict()


@frappe.whitelist(methods=["POST"])
def create_page(project, title=None, parent_page=None, template=None, page_kind="Notes"):
	check_project(project, "write")
	content, kind = "", page_kind
	if template:
		tpl = frappe.get_doc("Event Brief Template", template)
		content = to_html(tpl.content)
		kind = "Debrief" if tpl.kind == "debrief" else "Brief"
		title = title or tpl.template_name
	doc = frappe.get_doc(
		{
			"doctype": "Planner Page",
			"project": project,
			"title": (title or "").strip() or _("Untitled"),
			"parent_page": parent_page,
			"page_kind": kind,
			"template": template,
			"content": content,
			"sort_order": cint(frappe.db.count("Planner Page", {"project": project})),
		}
	)
	doc.insert()
	return doc.as_dict()


def to_html(text):
	"""Old templates and briefs are Markdown; pages store HTML."""
	if not text or text.lstrip().startswith("<"):
		return text or ""
	from frappe.utils import md_to_html

	return md_to_html(text)


@frappe.whitelist()
def page_templates():
	return frappe.get_all(
		"Event Brief Template",
		filters={"is_active": 1},
		fields=["name", "template_name", "kind", "category", "description"],
		order_by="kind asc, template_name asc",
	)


# ── Home dashboard ─────────────────────────────────────────────────────────────

HOME_ITEM_FIELDS = [
	"name",
	"subject",
	"project",
	"status",
	"ep_state",
	"ep_sequence",
	"priority",
	"type",
	"exp_start_date",
	"exp_end_date",
	"is_milestone",
	"_assign",
	"_user_tags",
	"modified",
]


@frappe.whitelist()
def get_home():
	"""The signed-in user's dashboard: open work assigned to them, their projects, recent activity."""
	user = frappe.session.user
	mine = frappe.get_list(
		"Task",
		filters=[["_assign", "like", f'%"{user}"%'], ["status", "not in", ["Completed", "Cancelled", "Template"]], ["project", "is", "set"]],
		fields=HOME_ITEM_FIELDS,
		order_by="exp_end_date asc",
		limit_page_length=300,
	)
	mine = describe(mine)

	projects = projects_overview(user, {i.project for i in mine})
	keys = {p["name"]: p["key"] for p in projects}
	states = {}
	for p in projects:
		for state in get_states(p["project_type"]):
			states[state["name"]] = {"title": state["title"], "state_group": state["state_group"], "color": state["color"]}
	for state in get_states(None):
		states[state["name"]] = {"title": state["title"], "state_group": state["state_group"], "color": state["color"]}

	week_ago = frappe.utils.add_days(frappe.utils.today(), -7)
	return {
		"user": user,
		"full_name": frappe.utils.get_fullname(user),
		"items": mine,
		"projects": projects,
		"keys": keys,
		"states": states,
		"completed_this_week": frappe.db.count(
			"Task", {"completed_by": user, "status": "Completed", "completed_on": [">=", week_ago]}
		),
		"activity": home_activity(user, [i.name for i in mine]),
		"can_create_project": bool(frappe.has_permission("Project", "create")),
	}


def projects_overview(user, with_my_items):
	"""Open projects the user can read: theirs first (items assigned or a project member), then recent ones."""
	member_of = set(frappe.get_all("Project User", filters={"user": user}, pluck="parent"))
	rows = frappe.get_list(
		"Project",
		filters={"status": ["in", ["Open", "On hold"]]},
		fields=["name", "project_name", "ep_key", "project_type", "status", "expected_start_date", "expected_end_date", "percent_complete", "customer", "modified", "creation", "owner"],
		order_by="modified desc",
		limit_page_length=200,  # shortcut: the 200 last touched open projects; page on the server when there are more
	)
	owners = {u.name: u.full_name for u in frappe.get_all("User", filters={"name": ["in", list({r.owner for r in rows}) or [""]]}, fields=["name", "full_name"])}
	names = [r.name for r in rows]
	counts = {}
	if names:
		for row in frappe.db.sql(
			"""
			select project,
				count(*) total,
				sum(status in ('Completed', 'Cancelled')) closed,
				sum(status not in ('Completed', 'Cancelled') and exp_end_date < curdate()) overdue,
				sum(status not in ('Completed', 'Cancelled') and _assign like %(me)s) mine
			from `tabTask` where project in %(names)s group by project
			""",
			{"names": names, "me": f'%"{user}"%'},
			as_dict=True,
		):
			counts[row.project] = row
	out = []
	for r in rows:
		c = counts.get(r.name) or {}
		total = int(c.get("total") or 0)
		closed = int(c.get("closed") or 0)
		out.append(
			{
				"name": r.name,
				"project_name": r.project_name,
				"key": r.ep_key,
				"project_type": r.project_type,
				"status": r.status,
				"start": r.expected_start_date,
				"end": r.expected_end_date,
				"customer": r.customer,
				"total": total,
				"done": closed,
				"progress": round(closed * 100 / total) if total else round(r.percent_complete or 0),
				"overdue": int(c.get("overdue") or 0),
				"mine": int(c.get("mine") or 0),
				"is_mine": r.name in with_my_items or r.name in member_of,
				"modified": r.modified,
				"created": r.creation,
				"owner": r.owner,
				"owner_name": owners.get(r.owner) or r.owner,
			}
		)
	out.sort(key=lambda p: (not p["is_mine"], -p["mine"]))
	return out


def home_activity(user, my_tasks):
	"""Recent comments and changes by others on the user's work items."""
	if not my_tasks:
		return []
	since = frappe.utils.add_days(frappe.utils.now_datetime(), -14)
	events = []
	for c in frappe.get_all(
		"Comment",
		filters={"reference_doctype": "Task", "reference_name": ["in", my_tasks], "comment_type": "Comment", "creation": [">=", since], "owner": ["!=", user]},
		fields=["reference_name", "content", "owner", "creation"],
		order_by="creation desc",
		limit=15,
	):
		events.append({"kind": "comment", "task": c.reference_name, "user": c.owner, "content": c.content, "at": c.creation})
	for v in frappe.get_all(
		"Version",
		filters={"ref_doctype": "Task", "docname": ["in", my_tasks], "creation": [">=", since], "owner": ["!=", user]},
		fields=["docname", "data", "owner", "creation"],
		order_by="creation desc",
		limit=15,
	):
		changed = [row[0] for row in (frappe.parse_json(v.data) or {}).get("changed", []) if row[0] in TRACKED]
		if changed:
			events.append({"kind": "change", "task": v.docname, "user": v.owner, "fields": [TRACKED[f] for f in changed if f != "status"] or ["status"], "at": v.creation})
	subjects = dict(frappe.get_all("Task", filters={"name": ["in", list({e["task"] for e in events}) or ["-"]]}, fields=["name", "subject"], as_list=True))
	projects = dict(frappe.get_all("Task", filters={"name": ["in", list({e["task"] for e in events}) or ["-"]]}, fields=["name", "project"], as_list=True))
	for e in events:
		e["subject"] = subjects.get(e["task"])
		e["project"] = projects.get(e["task"])
	events.sort(key=lambda e: str(e["at"]), reverse=True)
	return events[:20]


@frappe.whitelist(methods=["POST"])
def complete_item(name):
	"""Mark a work item done: the first Completed state of its project's type, or status Completed."""
	doc = frappe.get_doc("Task", name)
	doc.check_permission("write")
	states = get_states(frappe.db.get_value("Project", doc.project, "project_type"))
	done = next((s for s in states if s["state_group"] == "Completed"), None)
	if done and not done["name"].startswith("status:"):
		doc.ep_state = done["name"]
	else:
		doc.status = "Completed"
	doc.save()
	return load_item(name)
