"""Demo data for a local or staging site (never production):

    bench --site <site> execute event_planner.planner.demo.create
"""

import json

import frappe
from frappe.utils import add_days, getdate, today

from event_planner.planner.api import create_page, sync_assignees

EVENT_STATES = [
	("Idea", "Backlog", "#9CA3AF", 0, 0),
	("Planned", "Unstarted", "#6B7280", 1, 0),
	("Booked", "Started", "#3B82F6", 0, 0),
	("In prep", "Started", "#F59E0B", 0, 0),
	("Client review", "Started", "#8B5CF6", 0, 1),
	("Done", "Completed", "#10B981", 0, 0),
	("Dropped", "Cancelled", "#EF4444", 0, 0),
]
TYPES = [
	("Task", "lucide-square-check", "#6B7280", 1),
	("Milestone", "lucide-flag", "#F59E0B", 0),
	("Logistics", "lucide-truck", "#3B82F6", 0),
	("Run of Show", "lucide-calendar-clock", "#8B5CF6", 0),
	("Site Visit", "lucide-map-pin", "#10B981", 0),
]


def create():
	if not frappe.db.exists("Project Type", "Event"):
		frappe.get_doc({"doctype": "Project Type", "project_type": "Event"}).insert()
	if not frappe.db.exists("Planner State", {"project_type": "Event"}):
		for order, (title, group, color, default, review) in enumerate(EVENT_STATES):
			frappe.get_doc(
				{"doctype": "Planner State", "project_type": "Event", "title": title, "state_group": group, "color": color, "is_default": default, "is_review": review, "sort_order": order}
			).insert()
	for name, icon, color, default in TYPES:
		if not frappe.db.exists("Task Type", name):
			frappe.get_doc({"doctype": "Task Type", "__newname": name}).insert()
		frappe.db.set_value("Task Type", name, {"ep_icon": icon, "ep_color": color, "ep_is_default": default})
	if not frappe.db.exists("Planner Property", {"task_type": "Logistics", "label": "Supplier"}):
		frappe.get_doc({"doctype": "Planner Property", "task_type": "Logistics", "label": "Supplier", "property_type": "Text"}).insert()
	if not frappe.db.exists("Planner Property", {"task_type": "Site Visit", "label": "Venue zone"}):
		frappe.get_doc(
			{"doctype": "Planner Property", "task_type": "Site Visit", "label": "Venue zone", "property_type": "Dropdown", "options": "Main hall\nFoyer\nOutdoor\nBackstage"}
		).insert()

	name = frappe.db.get_value("Project", {"project_name": "Demo Launch Event"})
	if name:
		return {"project": name, "note": "already there"}
	start = getdate(add_days(today(), -10))
	project = frappe.get_doc(
		{
			"doctype": "Project",
			"project_name": "Demo Launch Event",
			"project_type": "Event",
			"ep_key": "DLE",
			"expected_start_date": start,
			"expected_end_date": add_days(start, 40),
			"ep_location": "Skylight Hotel, Addis Ababa",
		}
	).insert()

	groups = {}
	for order, (title, color) in enumerate([("Logistics", "#3B82F6"), ("Creative", "#EC4899"), ("Production", "#F59E0B")]):
		doc = frappe.get_doc({"doctype": "Action Category", "title": title, "project": project.name, "color": color, "sort_order": order}).insert()
		groups[title] = doc.name

	def state(title):
		return frappe.db.get_value("Planner State", {"project_type": "Event", "title": title})

	plan = [
		("Kick-off with client", "Milestone", "Done", "High", 0, 0, "Production", True),
		("Venue recce", "Site Visit", "Done", "Medium", 2, 3, "Logistics", False),
		("Book LED wall and sound", "Logistics", "Booked", "High", 4, 8, "Logistics", False),
		("Stage design", "Task", "Client review", "High", 3, 12, "Creative", False),
		("Brand assets and screens content", "Task", "In prep", "Medium", 8, 20, "Creative", False),
		("Transport for crew", "Logistics", "Planned", "Low", 18, 24, "Logistics", False),
		("Run of show draft", "Run of Show", "Planned", "Medium", 15, 22, "Production", False),
		("Rehearsal", "Run of Show", "Planned", "High", 26, 27, "Production", False),
		("Event day", "Milestone", "Planned", "Urgent", 28, 28, "Production", True),
		("Photographer shortlist", "Task", "Idea", "Low", None, None, "Creative", False),
	]
	tasks = {}
	for subject, type_, st, priority, s, e, group, milestone in plan:
		doc = frappe.get_doc(
			{
				"doctype": "Task",
				"project": project.name,
				"subject": subject,
				"type": type_,
				"ep_state": state(st),
				"priority": priority,
				"exp_start_date": f"{add_days(start, s)} 09:00:00" if s is not None else None,
				"exp_end_date": f"{add_days(start, e)} 18:00:00" if e is not None else None,
				"ep_action_category": groups[group],
				"is_milestone": 1 if milestone else 0,
			}
		)
		if st == "Done":
			doc.completed_on = add_days(start, e)
		doc.insert()
		tasks[subject] = doc
	sync_assignees(tasks["Stage design"], ["Administrator"])
	sync_assignees(tasks["Book LED wall and sound"], ["Administrator"])

	for blocked, blocker in (("Rehearsal", "Run of show draft"), ("Event day", "Rehearsal"), ("Book LED wall and sound", "Venue recce")):
		doc = frappe.get_doc("Task", tasks[blocked].name)
		doc.append("depends_on", {"task": tasks[blocker].name})
		doc.save()

	frappe.get_doc(
		{"doctype": "Planner View", "title": "Logistics board", "project": project.name, "layout": "Kanban", "group_by": "state", "filters": json.dumps([["group", "in", [groups["Logistics"]]]])}
	).insert()
	frappe.get_doc({"doctype": "Planner View", "title": "Timeline", "project_type": "Event", "layout": "Gantt", "order_by": "start_date asc"}).insert()
	template = frappe.db.get_value("Event Brief Template", {"kind": "brief"})
	if template:
		create_page(project.name, template=template)
	frappe.db.commit()
	return {"project": project.name}
