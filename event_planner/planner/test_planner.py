"""Planner v2: work items on ERPNext Task.

Run: bench --site <site> run-tests --module event_planner.planner.test_planner
"""

import json

import frappe
from frappe.tests import IntegrationTestCase

from event_planner.planner import api
from event_planner.planner.migration import seed_states
from event_planner.planner.work_items import get_states, propose_key

TYPE = "_Planner Test Type"


def make_project(name="_Planner Test Project", project_type=TYPE):
	if not frappe.db.exists("Project Type", project_type):
		frappe.get_doc({"doctype": "Project Type", "project_type": project_type}).insert()
	seed_states(json.dumps([project_type]))
	existing = frappe.db.get_value("Project", {"project_name": name})
	if existing:
		frappe.delete_doc("Project", existing, force=True)
		frappe.db.delete("Task", {"project": existing})
	return frappe.get_doc({"doctype": "Project", "project_name": name, "project_type": project_type, "ep_key": None}).insert()


def state(title):
	return frappe.db.get_value("Planner State", {"project_type": TYPE, "title": title})


class TestPlanner(IntegrationTestCase):
	def setUp(self):
		self.project = make_project()

	def task(self, subject="Item", **values):
		return frappe.get_doc({"doctype": "Task", "subject": subject, "project": self.project.name, **values}).insert()

	def test_new_item_gets_default_state_and_number(self):
		first = self.task("First")
		second = self.task("Second")
		self.assertEqual(first.ep_state, state("Todo"))
		self.assertEqual(first.status, "Open")
		self.assertEqual(second.ep_sequence, first.ep_sequence + 1)

	def test_state_sets_status(self):
		task = self.task()
		for title, status in (("In Progress", "Working"), ("In Review", "Pending Review"), ("Done", "Completed")):
			task.ep_state = state(title)
			task.save()
			self.assertEqual(task.status, status, title)

	def test_desk_status_change_sets_state(self):
		task = self.task()
		task.status = "Working"
		task.save()
		self.assertEqual(task.ep_state, state("In Progress"))
		task.status = "Pending Review"
		task.save()
		self.assertEqual(task.ep_state, state("In Review"))

	def test_state_of_another_type_is_refused(self):
		other = make_project("_Planner Other Project", "_Planner Other Type")
		foreign = frappe.db.get_value("Planner State", {"project_type": other.project_type, "title": "Done"})
		task = self.task()
		task.ep_state = foreign
		self.assertRaises(frappe.ValidationError, task.save)

	def test_completed_state_respects_dependencies(self):
		blocker = self.task("Blocker")
		task = self.task("Blocked", depends_on=[{"task": blocker.name}])
		task.ep_state = state("Done")
		self.assertRaises(frappe.ValidationError, task.save)

	def test_project_without_type_uses_statuses(self):
		self.assertEqual(get_states(None)[0]["name"], "status:Open")

	def test_key(self):
		self.project.ep_key = "ev"
		self.project.save()
		self.assertEqual(self.project.ep_key, "EV")
		self.project.ep_key = "1BAD"
		self.assertRaises(frappe.ValidationError, self.project.save)
		self.assertTrue(propose_key("Coca Cola Launch Event"))

	def test_filters_reject_unknown_attributes(self):
		self.assertRaises(frappe.ValidationError, api.list_items, self.project.name, json.dumps([["password", "=", "x"]]))
		self.assertRaises(frappe.ValidationError, api.list_items, self.project.name, None, "subject; drop table")

	def test_filter_by_state_group_and_assignee(self):
		done = self.task("Done one", ep_state=state("Done"))
		open_ = self.task("Open one")
		api.update_item(open_.name, json.dumps({"assignees": ["Administrator"]}))
		names = lambda filters: {r.name for r in api.list_items(self.project.name, json.dumps(filters))}  # noqa: E731
		self.assertEqual(names([["state_group", "in", ["Completed"]]]), {done.name})
		self.assertEqual(names([["assignee", "=", "@me"]]), {open_.name})
		self.assertEqual(names([["assignee", "is", "not set"]]), {done.name})

	def test_sub_item_makes_parent_a_group(self):
		parent = self.task("Parent")
		child = api.create_item(self.project.name, json.dumps({"subject": "Child", "parent_task": parent.name}))
		self.assertEqual(child.parent_task, parent.name)
		self.assertEqual(frappe.db.get_value("Task", parent.name, "is_group"), 1)

	def test_update_rejects_unknown_fields(self):
		task = self.task()
		self.assertRaises(frappe.ValidationError, api.update_item, task.name, json.dumps({"owner": "Guest"}))

	def test_property_becomes_task_field_and_blocks_completion(self):
		if not frappe.db.exists("Task Type", "_Planner Shot"):
			frappe.get_doc({"doctype": "Task Type", "__newname": "_Planner Shot"}).insert()
		# adding a Custom Field alters the table, which commits; so reuse the property of an earlier run
		existing = frappe.db.get_value("Planner Property", {"label": "Lens", "task_type": "_Planner Shot"})
		prop = frappe.get_doc("Planner Property", existing) if existing else frappe.get_doc(
			{"doctype": "Planner Property", "label": "Lens", "task_type": "_Planner Shot", "property_type": "Text", "is_required": 1}
		).insert()
		frappe.db.delete("Planner Property", {"task_type": "_Planner Shot", "name": ["!=", prop.name]})
		self.assertTrue(frappe.get_meta("Task").has_field(prop.fieldname))
		task = self.task("Shot 1", type="_Planner Shot")
		task.ep_state = state("Done")
		self.assertRaises(frappe.ValidationError, task.save)
		task.reload()
		task.set(prop.fieldname, "35mm")
		task.ep_state = state("Done")
		task.save()
		self.assertEqual(task.status, "Completed")

	def test_personal_view_is_hidden_from_others(self):
		view = frappe.get_doc(
			{"doctype": "Planner View", "title": "Mine", "project": self.project.name, "layout": "List", "is_personal": 1}
		).insert()
		self.assertTrue(frappe.has_permission("Planner View", "read", view))
		self.assertFalse(frappe.has_permission("Planner View", "read", view, user="Guest"))

	def test_view_with_bad_filter_is_refused(self):
		doc = frappe.get_doc(
			{"doctype": "Planner View", "title": "Bad", "project": self.project.name, "layout": "List", "filters": json.dumps([["x", "=", 1]])}
		)
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_page_from_markdown_template(self):
		template = frappe.get_doc(
			{"doctype": "Event Brief Template", "template_name": "_Planner Tpl", "kind": "brief", "is_active": 1, "content": "# Hello\n\n- one"}
		)
		if not frappe.db.exists("Event Brief Template", "_Planner Tpl"):
			template.insert()
		page = api.create_page(self.project.name, template="_Planner Tpl")
		self.assertIn("<h1", page["content"])
		self.assertEqual(page["page_kind"], "Brief")

	def test_old_api_checks_project_permission(self):
		from event_planner import api as old_api

		user = "planner-noaccess@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc({"doctype": "User", "email": user, "first_name": "No Access", "send_welcome_email": 0}).insert()
		frappe.set_user(user)
		try:
			self.assertRaises(frappe.PermissionError, old_api.create_category, self.project.name, "X")
		finally:
			frappe.set_user("Administrator")

	def test_home_lists_my_open_work_and_complete_item(self):
		mine = self.task("Mine")
		api.update_item(mine.name, json.dumps({"assignees": ["Administrator"]}))
		self.task("Not mine")
		home = api.get_home()
		self.assertIn(mine.name, [i.name for i in home["items"]])
		project = next(p for p in home["projects"] if p["name"] == self.project.name)
		self.assertTrue(project["is_mine"])
		self.assertEqual(project["mine"], 1)
		done = api.complete_item(mine.name)
		self.assertEqual(done.status, "Completed")
		self.assertNotIn(mine.name, [i.name for i in api.get_home()["items"]])

	def test_relative_date_filters(self):
		from frappe.utils import add_days, today

		self.task("Late", exp_end_date=f"{add_days(today(), -3)} 10:00:00", exp_start_date=f"{add_days(today(), -4)} 10:00:00")
		self.task("Later", exp_end_date=f"{add_days(today(), 40)} 10:00:00", exp_start_date=f"{add_days(today(), 39)} 10:00:00")
		self.project.db_set({"expected_start_date": None, "expected_end_date": None})
		late = api.list_items(self.project.name, json.dumps([["due_date", "<", "@today"]]))
		self.assertEqual([r.subject for r in late], ["Late"])
		this_month = api.list_items(self.project.name, json.dumps([["due_date", "<", "@month_end"], ["due_date", ">", "@month_start"]]))
		self.assertNotIn("Later", [r.subject for r in this_month])
