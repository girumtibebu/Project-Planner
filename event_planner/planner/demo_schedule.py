"""Demo lists for three projects: run of show, crew calls, logistics and equipment requests. Local testing only.

Run: bench --site <site> execute event_planner.planner.demo_schedule.create
Safe to run again: a work item with the same project, type and title is left alone.
"""

import frappe

from event_planner.planner import lists
from event_planner.planner.api import sync_assignees

ABEL, DAWIT, GIRUM, HANNA, MERON = (
	"abel@example.com",
	"dawit@example.com",
	"girum@eternal-media.com",
	"hanna@example.com",
	"meron@example.com",
)
RUN, CREW, LOGISTICS = "Run of Show", "Crew Call", "Logistics"


def create():
	lists.ensure()
	coca_cola = [
		# event day is 21 Nov: build on the 20th, show on the 21st, load out on the 22nd
		(RUN, "Load in and stage build", "2026-11-20", "08:00", "16:00", [ABEL], {"Location": "Meskel Square", "Tag": "Ops"}),
		(RUN, "Sound and light check", "2026-11-21", "10:00", "13:00", [DAWIT], {"Location": "Main stage", "Tag": "Ops"}),
		(RUN, "Doors open", "2026-11-21", "17:30", "18:00", [HANNA], {"Location": "Gate A", "Tag": "Guest"}),
		(RUN, "Welcome speech", "2026-11-21", "18:00", "18:20", [MERON], {"Location": "Main stage", "Tag": "Program"}),
		(RUN, "Product reveal", "2026-11-21", "18:20", "18:45", [GIRUM], {"Location": "Main stage", "Tag": "Program"}),
		(RUN, "Dinner service", "2026-11-21", "19:00", "20:30", [HANNA], {"Location": "Dining area", "Tag": "Guest"}),
		(RUN, "Live band", "2026-11-21", "20:30", "22:00", [MERON], {"Location": "Main stage", "Tag": "Talent"}),
		(RUN, "Load out", "2026-11-22", "08:00", "12:00", [ABEL], {"Location": "Meskel Square", "Tag": "Ops"}),
		(CREW, "Production manager", "2026-11-21", "07:00", "23:00", [ABEL], {"Role": "Production manager", "Vehicle": "AA-2-34567"}),
		(CREW, "Sound crew", "2026-11-21", "09:00", "23:00", [DAWIT], {"Role": "Sound engineer", "Vehicle": "AA-3-12345"}),
		(CREW, "Show crew", "2026-11-21", "15:00", "23:00", [MERON, HANNA], {"Role": "Stage and guest team"}),
		(LOGISTICS, "Stage and truss from warehouse", "2026-11-20", "06:00", "09:00", [ABEL], {"Vehicle": "AA-3-23456", "Pickup": "Main warehouse", "Drop-off": "Meskel Square"}),
		(LOGISTICS, "Load out to warehouse", "2026-11-22", "08:00", "13:00", [ABEL], {"Vehicle": "AA-3-23456", "Pickup": "Meskel Square", "Drop-off": "Main warehouse"}),
	]
	ethio = [
		(RUN, "Crew call and breakfast", "2026-10-25", "06:00", "07:00", [GIRUM], {"Location": "Entoto studio", "Tag": "Ops"}),
		(RUN, "Scenes 1-3", "2026-10-25", "07:00", "12:00", [GIRUM], {"Location": "Entoto studio", "Tag": "Program"}),
		(RUN, "Scenes 4-6 exterior", "2026-10-25", "13:00", "18:00", [GIRUM], {"Location": "Entoto park", "Tag": "Program"}),
		(CREW, "Director", "2026-10-25", "06:00", "19:00", [GIRUM], {"Role": "Director", "Vehicle": "AA-2-34567"}),
		(CREW, "Gaffer", "2026-10-25", "06:00", "19:00", [DAWIT], {"Role": "Gaffer", "Vehicle": "AA-3-12345"}),
	]
	hilton = [
		(RUN, "Hall decor set-up", "2026-10-25", "10:00", "16:00", [HANNA], {"Location": "Hilton ballroom", "Tag": "Ops"}),
		(RUN, "Gala dinner", "2026-10-25", "19:30", "22:30", [MERON], {"Location": "Hilton ballroom", "Tag": "Program"}),
		# Dawit is also the gaffer on the TVC shoot that day: shows a clash
		(CREW, "Lighting tech", "2026-10-25", "15:00", "23:00", [DAWIT], {"Role": "Lighting tech"}),
		(LOGISTICS, "Decor delivery", "2026-10-25", "08:00", "11:00", [HANNA], {"Vehicle": "AA-3-23456", "Pickup": "Decor store", "Drop-off": "Hilton"}),
	]
	for project_name, rows in (("Coca-Cola Summer Launch", coca_cola), ("Ethio Telecom TVC Shoot", ethio), ("Hilton Gala Dinner Decor", hilton)):
		project = frappe.db.get_value("Project", {"project_name": project_name})
		if not project:
			print(f"skipped: no project {project_name}")
			continue
		clear_old_schedule(project)
		# equipment requests are tech BOQ pages now (demo_boq)
		for name in frappe.get_all("Task", filters={"project": project, "type": "Equipment Request"}, pluck="name"):
			frappe.delete_doc("Task", name, ignore_permissions=True)
		for row in rows:
			add(project, *row)
		retype_planning_todos(project)  # after add(), which fixes the times of older items it reuses
	frappe.db.commit()
	return "demo lists created"


def add(project, task_type, subject, day, start, end, people, values):
	"""Create the work item, or move an existing one with the same title to these times and values."""
	name = frappe.db.get_value("Task", {"project": project, "type": task_type, "subject": subject})
	doc = frappe.get_doc("Task", name) if name else frappe.new_doc("Task")
	doc.update(
		{
			"project": project,
			"type": task_type,
			"subject": subject,
			"exp_start_date": f"{day} {start}:00",
			"exp_end_date": f"{end}:00" if " " in end else f"{day} {end}:00",
		}
	)
	for label, value in values.items():
		doc.set(lists.property_fieldname(task_type, label), value)
	doc.save(ignore_permissions=True)
	sync_assignees(doc, people)


def retype_planning_todos(project):
	"""Older demo data typed planning to-dos ("Book LED wall", Mon–Fri) as Logistics or Run of Show.
	Those are action items; only runs and slots of a day or less belong in the lists."""
	from frappe.utils import time_diff_in_hours

	default_type = frappe.db.get_value("Task Type", {"ep_is_default": 1}) or "Task"
	for task in frappe.get_all(
		"Task",
		filters={"project": project, "type": ["in", ["Logistics", "Run of Show"]]},
		fields=["name", "exp_start_date", "exp_end_date"],
	):
		if not (task.exp_start_date and task.exp_end_date) or time_diff_in_hours(task.exp_end_date, task.exp_start_date) > 24:
			frappe.db.set_value("Task", task.name, "type", default_type)


def clear_old_schedule(project):
	"""The Schedule page and its Project tables are replaced by these lists."""
	doc = frappe.get_doc("Project", project)
	for table in ("ep_time_schedule", "ep_crew_schedule", "ep_equipment_schedule", "ep_vehicle_schedule"):
		doc.set(table, [])
	doc.save(ignore_permissions=True)
