"""Double bookings: a person or vehicle on timed work items of two projects at once.

People count on types with "Warn about double bookings" (run of show, crew calls); a to-do
with a due window does not book its assignee. Vehicles count on any type with a Vehicle
property. Inside one project overlaps are normal (an MC on an umbrella slot and a reveal
slot, a van carrying its crew), so only other projects are checked.
"""

import json

import frappe
from frappe import _
from frappe.utils import get_datetime

from event_planner.planner.api import check_project

VEHICLE = "Vehicle"  # properties with this label are matched as vehicles


@frappe.whitelist()
def get_clashes(project):
	"""{task name: [message]} for this project's work items."""
	check_project(project)
	people_types = set(frappe.get_all("Task Type", filters={"ep_check_clashes": 1}, pluck="name"))
	vehicle_fields = vehicle_fieldnames()
	if not people_types and not vehicle_fields:
		return {}
	timed = {"exp_start_date": ["is", "set"], "exp_end_date": ["is", "set"]}
	result = {}
	for task in frappe.get_all(
		"Task",
		filters={"project": project, **timed},
		fields=["name", "type", "exp_start_date", "exp_end_date", "_assign", *vehicle_fields],
	):
		others = {"project": ["!=", project], "exp_start_date": ["<", task.exp_end_date], "exp_end_date": [">", task.exp_start_date]}
		checks = []
		if task.type in people_types:
			for user in json.loads(task._assign or "[]"):
				checks.append((user, {"type": ["in", list(people_types)], "_assign": ["like", f'%"{user}"%']}))
		for field in vehicle_fields:
			if task.get(field):
				checks += [(task[field], {other: task[field]}) for other in vehicle_fields]
		for resource, condition in checks:
			for other in frappe.get_all(
				"Task",
				filters={**timed, **others, **condition},
				fields=["subject", "type", "project", "exp_start_date", "exp_end_date"],
			):
				result.setdefault(task.name, []).append(describe(resource, other))
	return {name: sorted(set(lines)) for name, lines in result.items()}


def vehicle_fieldnames():
	meta = frappe.get_meta("Task")
	names = frappe.get_all("Planner Property", filters={"label": VEHICLE}, pluck="fieldname")
	return [n for n in names if meta.has_field(n)]


def describe(resource, other):
	who = (frappe.db.get_value("User", resource, "full_name") if "@" in resource else None) or resource
	if not frappe.has_permission("Project", "read", other.project):
		return _("{0} is booked on another project at the same time").format(who)
	where = frappe.db.get_value("Project", other.project, "project_name") or other.project
	start, end = get_datetime(other.exp_start_date), get_datetime(other.exp_end_date)
	span = f"{start:%d %b %H:%M} – {end:%H:%M}" if start.date() == end.date() else f"{start:%d %b %H:%M} – {end:%d %b %H:%M}"
	return _("{0} is also on “{1}” ({2}) in {3}, {4}").format(who, other.subject, other.type, where, span)
