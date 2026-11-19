"""Lists (work item types shown as tables) and the double-booking check.

Run: bench --site <site> run-tests --module event_planner.planner.test_lists
"""

import frappe
from frappe.tests import IntegrationTestCase

from event_planner.planner import clashes, lists
from event_planner.planner.api import sync_assignees
from event_planner.planner.test_planner import make_project


def task(project, task_type, start, end, people=(), subject="Booking", **values):
	doc = frappe.get_doc(
		{
			"doctype": "Task",
			"project": project.name,
			"type": task_type,
			"subject": subject,
			"exp_start_date": f"2031-05-01 {start}",
			"exp_end_date": f"2031-05-01 {end}",
			**values,
		}
	).insert()
	sync_assignees(doc, list(people))
	return doc


class TestLists(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		lists.ensure()
		for spec in lists.LISTS:
			frappe.db.set_value("Task Type", spec["type"], "ep_check_clashes", spec["clashes"])

	def setUp(self):
		self.first = make_project("_Lists Test A")
		self.second = make_project("_Lists Test B")

	def test_ensure_is_idempotent(self):
		count = frappe.db.count("Planner Property")
		lists.ensure()
		self.assertEqual(frappe.db.count("Planner Property"), count)
		self.assertTrue(lists.property_fieldname("Crew Call", "Role"))

	def test_person_on_two_projects_at_once_clashes(self):
		task(self.first, "Crew Call", "08:00:00", "18:00:00", ["Administrator"])
		mine = task(self.second, "Crew Call", "12:00:00", "20:00:00", ["Administrator"])
		self.assertIn(mine.name, clashes.get_clashes(self.second.name))

	def test_back_to_back_does_not_clash(self):
		task(self.first, "Crew Call", "08:00:00", "12:00:00", ["Administrator"])
		task(self.second, "Crew Call", "12:00:00", "20:00:00", ["Administrator"])
		self.assertEqual(clashes.get_clashes(self.second.name), {})

	def test_overlaps_inside_one_project_are_normal(self):
		task(self.first, "Crew Call", "08:00:00", "18:00:00", ["Administrator"])
		task(self.first, "Run of Show", "09:00:00", "12:00:00", ["Administrator"])
		task(self.first, "Run of Show", "09:30:00", "10:30:00", ["Administrator"])
		self.assertEqual(clashes.get_clashes(self.first.name), {})

	def test_vehicle_clashes_across_types_and_projects(self):
		run = lists.property_fieldname("Logistics", "Vehicle")
		call = lists.property_fieldname("Crew Call", "Vehicle")
		task(self.first, "Crew Call", "08:00:00", "12:00:00", **{call: "AA-TEST-1"})
		mine = task(self.second, "Logistics", "10:00:00", "14:00:00", **{run: "AA-TEST-1"})
		self.assertIn(mine.name, clashes.get_clashes(self.second.name))

	def test_logistics_assignee_is_not_booked(self):
		task(self.first, "Crew Call", "08:00:00", "18:00:00", ["Administrator"])
		mine = task(self.second, "Logistics", "09:00:00", "17:00:00", ["Administrator"])
		self.assertNotIn(mine.name, clashes.get_clashes(self.second.name))
