"""Project parts, templates and tech BOQ lines.

Run: bench --site <site> run-tests --module event_planner.planner.test_parts
"""

import json
import time

import frappe
from frappe.tests import IntegrationTestCase

from event_planner.planner import api, boards, history, lists, notify, parts
from event_planner.planner.test_planner import TYPE, make_project

NAME = "_Parts Test"


class TestParts(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_project("_Parts Setup")  # makes sure the test project type and its states exist
		lists.ensure_views(TYPE)
		parts.ensure_brief_template()

	def setUp(self):
		for name in frappe.get_all("Project", filters={"project_name": ["in", [NAME, "_Parts Source"]]}, pluck="name"):
			for table in ("Planner Page", "Planner View", "Action Category", "Task"):
				frappe.db.delete(table, {"project": name})
			frappe.delete_doc("Project", name, force=True)

	def create(self, keys=None, template=None, name=NAME):
		data = {"project_name": name, "project_type": TYPE}
		return parts.create_project(json.dumps(data), template=template, parts=json.dumps(keys or []))["name"]

	def view_titles(self, project):
		return {v.title for v in api.get_views(project, TYPE)}

	def test_project_gets_only_the_ticked_parts(self):
		project = self.create(["brief", "boq_audio", "logistics"])
		kinds = {(p.page_kind, p.department) for p in frappe.get_all("Planner Page", filters={"project": project}, fields=["page_kind", "department"])}
		self.assertEqual(kinds, {("Brief", ""), ("BOQ", "Audio")})
		self.assertIn("Logistics", self.view_titles(project))
		self.assertNotIn("Run of show", self.view_titles(project))
		self.assertEqual(set(parts.enabled_parts(project)), {"brief", "boq_audio", "logistics"})

	def test_blank_project_shows_no_lists(self):
		project = self.create([])
		self.assertFalse(self.view_titles(project) & {"Action plan", "Run of show", "Crew call sheet", "Logistics"})

	def test_older_project_shows_every_list(self):
		project = make_project(NAME).name
		self.assertTrue({"Action plan", "Run of show", "Crew call sheet", "Logistics"} <= self.view_titles(project))

	def test_add_and_hide_parts(self):
		project = self.create([])
		parts.add_part(project, "run_of_show")
		self.assertIn("Run of show", self.view_titles(project))
		run_of_show = next(v.name for v in api.get_views(project, TYPE) if v.part == "run_of_show")
		boards.hide_view(project, run_of_show)
		self.assertNotIn("Run of show", self.view_titles(project))
		page = parts.add_part(project, "boq_power")["page"]
		self.assertEqual(frappe.db.get_value("Planner Page", page, "department"), "Power")
		self.assertRaises(frappe.ValidationError, parts.add_part, project, "boq_power")

	def test_project_copy_replaces_the_template_view(self):
		project = self.create(["logistics"])
		template = next(v for v in api.get_views(project, TYPE) if v.part == "logistics")
		api.save_view(json.dumps({"title": "Logistics", "project": project, "part": "logistics", "layout": "Kanban", "filters": "[]"}))
		mine = [v for v in api.get_views(project, TYPE) if v.part == "logistics"]
		self.assertEqual([(v.project, v.layout) for v in mine], [(project, "Kanban")])
		self.assertTrue(frappe.db.exists("Planner View", template.name))  # other projects keep it

	def test_board_template_round_trip(self):
		source = self.create(["brief", "boq_video", "logistics"], name="_Parts Source")
		cat = frappe.get_doc({"doctype": "Action Category", "project": source, "title": "Pre-production"}).insert()
		parent = api.create_item(source, json.dumps({"subject": "Venue", "ep_action_category": cat.name, "is_group": 1}))
		api.create_item(source, json.dumps({"subject": "Site visit", "parent_task": parent["name"], "exp_end_date": "2031-05-01 10:00:00"}))
		video = frappe.db.get_value("Planner Page", {"project": source, "page_kind": "BOQ"})
		frappe.get_doc({"doctype": "Planner BOQ Line", "page": video, "item": "LED screen", "qty": 30, "unit": "sqm", "qty_booked": 30, "line_status": "Booked"}).insert()
		view = frappe.get_doc({"doctype": "Planner View", "project": source, "title": "Board", "layout": "Kanban", "filters": "[]"}).insert()
		boards.set_sidebar_order(source, json.dumps([view.name, video]))

		frappe.db.delete("Planner Template", {"template_name": "_Parts Board"})
		template = boards.save_as_template(source, "_Parts Board", "Test board")
		project = self.create(template=template)

		self.assertEqual(frappe.get_all("Action Category", filters={"project": project}, pluck="title"), ["Pre-production"])
		items = {t.subject: t for t in frappe.get_all("Task", filters={"project": project}, fields=["name", "subject", "parent_task", "ep_action_category", "exp_end_date"])}
		self.assertEqual(items["Site visit"].parent_task, items["Venue"].name)
		self.assertTrue(items["Venue"].ep_action_category)
		self.assertIsNone(items["Site visit"].exp_end_date)  # a checklist: no dates
		new_video = frappe.db.get_value("Planner Page", {"project": project, "page_kind": "BOQ"})
		line = frappe.get_all("Planner BOQ Line", filters={"page": new_video}, fields=["item", "qty", "qty_booked", "line_status"])[0]
		self.assertEqual((line.item, line.qty, line.qty_booked, line.line_status), ("LED screen", 30, 0, "Requested"))
		new_view = frappe.db.get_value("Planner View", {"project": project, "title": "Board"})
		self.assertEqual(boards.sidebar(project)["order"], [new_view, new_video])
		self.assertIn("Logistics", self.view_titles(project))
		frappe.delete_doc("Planner Template", template)

	def test_desk_project_is_set_up_once(self):
		project = frappe.get_doc({"doctype": "Project", "project_name": NAME, "project_type": TYPE}).insert().name
		self.assertTrue(api.get_project(project)["needs_setup"])
		boards.setup_project(project)  # keep as it is
		self.assertFalse(api.get_project(project)["needs_setup"])
		self.assertTrue({"Action plan", "Logistics"} <= self.view_titles(project))
		self.assertRaises(frappe.ValidationError, boards.setup_project, project)

	def test_project_with_content_is_not_offered_setup(self):
		project = frappe.get_doc({"doctype": "Project", "project_name": NAME, "project_type": TYPE}).insert().name
		frappe.get_doc({"doctype": "Planner Page", "project": project, "title": "Notes"}).insert()
		self.assertFalse(api.get_project(project)["needs_setup"])
		self.assertRaises(frappe.ValidationError, boards.setup_project, project, None, 1)

	def test_applying_a_board_twice_adds_nothing(self):
		project = self.create(["brief", "boq_audio", "logistics"])
		before = frappe.db.count("Planner Page", {"project": project})
		boards.apply(project, {"parts": ["brief", "boq_audio", "boq_video"]})
		self.assertEqual(frappe.db.count("Planner Page", {"project": project}), before + 1)  # only the new Video BOQ
		self.assertIn("Logistics", self.view_titles(project))  # lists it had stay

	def test_hide_and_show_a_shared_view_without_part(self):
		project = self.create(["logistics"])
		view = frappe.get_doc({"doctype": "Planner View", "project_type": TYPE, "title": "_Shared", "layout": "List", "filters": "[]"}).insert()
		self.assertIn("_Shared", self.view_titles(project))
		boards.hide_view(project, view.name)
		self.assertNotIn("_Shared", self.view_titles(project))
		boards.show_view(project, view.name)
		self.assertIn("_Shared", self.view_titles(project))
		view.delete()

	def test_page_history(self):
		# tests skip Frappe's change log unless asked
		project = self.create(["boq_audio"])
		page = frappe.get_doc("Planner Page", {"project": project, "page_kind": "BOQ"})
		line = frappe.get_doc({"doctype": "Planner BOQ Line", "page": page.name, "item": "Wireless mic", "qty": 6, "unit": "pcs"}).insert()
		line.qty = 8
		line.save(ignore_version=False)
		gone = frappe.get_doc({"doctype": "Planner BOQ Line", "page": page.name, "item": "Hazer", "qty": 1}).insert()
		gone.delete()
		page.reload()
		page.content = "<p>one</p>"
		page.save(ignore_version=False)
		page.content = "<p>two</p>"
		page.save(ignore_version=False)
		texts = [e["text"] for e in history.page_history(page.name)]
		self.assertIn("changed the qty of <b>Wireless mic</b> from <b>6</b> to <b>8</b>", texts)
		self.assertIn("removed <b>Hazer</b>", texts)
		self.assertIn("created the page", texts)
		self.assertEqual(texts.count("edited the text"), 1)  # two saves in a row fold into one

	def test_delete_category_keeps_items(self):
		project = self.create([])
		cat = frappe.get_doc({"doctype": "Action Category", "project": project, "title": "Pre-production"}).insert()
		item = api.create_item(project, json.dumps({"subject": "Book venue", "ep_action_category": cat.name}))
		api.delete_category(cat.name)
		self.assertFalse(frappe.db.exists("Action Category", cat.name))
		self.assertIsNone(frappe.db.get_value("Task", item["name"], "ep_action_category"))

	def test_notify_text(self):
		project = self.create(["boq_audio"])
		page = frappe.db.get_value("Planner Page", {"project": project, "page_kind": "BOQ"})
		frappe.get_doc({"doctype": "Planner BOQ Line", "page": page, "item": "Wireless mic", "qty": 6, "unit": "pcs"}).insert()
		text = notify.build_text(project, note="Load-in moved to 7am")
		self.assertIn("Wireless mic: 6 pcs", text)
		self.assertIn("Load-in moved to 7am", text)
		self.assertIn(f"/planner/{project}", text)

	def test_unknown_part_is_refused(self):
		self.assertRaises(frappe.ValidationError, self.create, ["brief", "nope"])

	def test_boq_line_changes_after_review(self):
		project = self.create(["boq_video"])
		page = frappe.db.get_value("Planner Page", {"project": project, "page_kind": "BOQ"})
		line = frappe.get_doc({"doctype": "Planner BOQ Line", "page": page, "item": "LED screen", "qty": 30, "unit": "sqm"}).insert()
		self.assertEqual(line.project, project)
		reviewed = parts.mark_reviewed(page)["reviewed_at"]
		time.sleep(0.01)

		line.qty_booked = 30  # the warehouse's own column: not a change for the warehouse
		line.save()
		self.assertLess(line.tech_modified, reviewed)

		line.qty = 36
		line.save()
		self.assertGreater(line.tech_modified, reviewed)

		line.delete()
		self.assertGreater(frappe.db.get_value("Planner Page", page, "lines_removed_at"), reviewed)

	def test_create_item_in_project_without_states(self):
		# no project type: the planner shows ERPNext statuses as states named "status:…"
		project = parts.create_project(json.dumps({"project_name": NAME}))["name"]
		item = api.create_item(project, json.dumps({"subject": "Check", "ep_state": "status:Working"}))
		self.assertEqual(frappe.db.get_value("Task", item["name"], "status"), "Working")

	def test_boq_lines_need_a_boq_page(self):
		project = self.create(["brief"])
		brief = frappe.db.get_value("Planner Page", {"project": project, "page_kind": "Brief"})
		self.assertRaises(frappe.ValidationError, frappe.get_doc({"doctype": "Planner BOQ Line", "page": brief, "item": "X"}).insert)
