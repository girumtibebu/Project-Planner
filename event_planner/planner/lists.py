"""Lists: work item types with their own columns, shown as template views in the Table layout.

Run of show, crew call sheet, logistics and equipment requests are all work items (Task).
Each list is a work item type with its properties, plus a template view per project type
that filters on the type and groups by day. Safe to run on every migrate: it only adds
what is missing and never overwrites a type, property or view someone has edited.
"""

import json

import frappe

PROJECT_TYPES = ["Event", "Studio Shoot", "Decor Job"]

LISTS = [
	{
		"type": "Run of Show",
		"icon": "lucide-calendar-clock",
		"color": "#8B5CF6",
		"clashes": 1,
		"properties": [("Location", "Text", None), ("Tag", "Dropdown", "Ops\nTalent\nGuest\nProgram\nBreak\nOther")],
		"view": {"title": "Run of show", "group_by": "day", "fields": ["time", "assignees", "properties"]},
		"part": "run_of_show",
	},
	{
		"type": "Crew Call",
		"icon": "lucide-phone-call",
		"color": "#0EA5E9",
		"clashes": 1,
		"properties": [("Role", "Text", None), ("Vehicle", "Text", None)],
		"view": {"title": "Crew call sheet", "group_by": "day", "fields": ["time", "assignees", "properties"]},
		"part": "crew_call",
	},
	{
		"type": "Logistics",
		"icon": "lucide-truck",
		"color": "#3B82F6",
		"clashes": 0,  # its vehicle is checked; its assignee is often just the one who arranges it
		"properties": [("Vehicle", "Text", None), ("Pickup", "Text", None), ("Drop-off", "Text", None)],
		"view": {"title": "Logistics", "group_by": "day", "fields": ["state", "time", "assignees", "properties"]},
		"part": "logistics",
	},
]
# equipment requests moved to the tech BOQ pages (planner/parts.py)

ACTION_PLAN = "Action plan"


def ensure():
	for spec in LISTS:
		ensure_type(spec)
		for label, property_type, options in spec["properties"]:
			ensure_property(spec["type"], label, property_type, options)
	for project_type in PROJECT_TYPES:
		if frappe.db.exists("Project Type", project_type):
			ensure_views(project_type)


def ensure_type(spec):
	if not frappe.db.exists("Task Type", spec["type"]):
		frappe.get_doc(
			{"doctype": "Task Type", "name": spec["type"], "ep_icon": spec["icon"], "ep_color": spec["color"]}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Task Type", spec["type"], "ep_check_clashes", spec["clashes"])


def ensure_property(task_type, label, property_type, options):
	if frappe.db.exists("Planner Property", {"task_type": task_type, "label": label}):
		return
	frappe.get_doc(
		{
			"doctype": "Planner Property",
			"task_type": task_type,
			"label": label,
			"property_type": property_type,
			"options": options,
		}
	).insert(ignore_permissions=True)


def property_fieldname(task_type, label):
	return frappe.db.get_value("Planner Property", {"task_type": task_type, "label": label}, "fieldname")


def ensure_views(project_type):
	list_types = [spec["type"] for spec in LISTS]
	add_view(
		project_type,
		ACTION_PLAN,
		layout="List",
		filters=[["type", "not in", list_types]],
		group_by="state",
		order_by="manual asc",
		display={},
		sort_order=0,
		part="action_plan",
	)
	for i, spec in enumerate(LISTS, start=1):
		view = spec["view"]
		group_by = view["group_by"]
		if group_by != "day":  # a property label
			group_by = property_fieldname(spec["type"], group_by)
		add_view(
			project_type,
			view["title"],
			layout="Table",
			filters=[["type", "in", [spec["type"]]]],
			group_by=group_by,
			order_by="start_date asc",
			display={"card_fields": view["fields"], "show_completed": True, "show_sub": True},
			sort_order=i,
			part=spec["part"],
		)


def add_view(project_type, title, **values):
	existing = frappe.db.get_value("Planner View", {"project_type": project_type, "title": title}, ["name", "part"], as_dict=True)
	if existing:
		if not existing.part and values.get("part"):  # views made before parts existed
			frappe.db.set_value("Planner View", existing.name, "part", values["part"], update_modified=False)
		return
	frappe.get_doc(
		{
			"doctype": "Planner View",
			"title": title,
			"project_type": project_type,
			**{k: json.dumps(v) if k in ("filters", "display") else v for k, v in values.items()},
		}
	).insert(ignore_permissions=True)
