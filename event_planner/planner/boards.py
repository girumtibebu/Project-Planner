"""Saved boards: a project's structure kept as a template, and laid onto new projects.

A board is the categories, the work items (as a checklist: no dates, people or comments),
the pages with their content, the BOQ lines (the warehouse columns start empty), the
project's own views, the lists it shows and the sidebar order. A template made before
boards existed holds only a list of parts.
"""

import frappe
from frappe import _

from event_planner.planner import parts

PAGE_FIELDS = ["name", "title", "icon", "parent_page", "page_kind", "department", "content", "sort_order", "is_locked"]
VIEW_FIELDS = ["name", "title", "layout", "filters", "group_by", "order_by", "display", "sort_order", "part", "is_locked"]
ITEM_FIELDS = ["name", "subject", "type", "description", "priority", "ep_action_category", "parent_task", "is_group", "is_milestone", "ep_sort_order"]
LINE_FIELDS = ["item", "qty", "unit", "note", "sort_order"]


def check_project(project, ptype="read"):
	from event_planner.planner.api import check_project

	check_project(project, ptype)


def needs_setup(project):
	"""Made in the desk and still empty: no parts chosen, no pages, views or work items yet.
	A project that already has planner content is used as it is (a template would duplicate it)."""
	if frappe.db.get_value("Project", project, "ep_parts"):
		return False
	return not any(frappe.db.exists(dt, {"project": project}) for dt in ("Planner Page", "Planner View", "Task"))


def sidebar(project):
	return frappe.parse_json(frappe.db.get_value("Project", project, "ep_sidebar") or "{}") or {}


def set_sidebar(project, value):
	frappe.db.set_value("Project", project, "ep_sidebar", frappe.as_json(value, indent=None))


# ── API ───────────────────────────────────────────────────────────────────────


@frappe.whitelist(methods=["POST"])
def save_as_template(project, title, description=None):
	"""Keep this project's board as a template new projects can start from."""
	check_project(project)
	frappe.has_permission("Project", "create", throw=True)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the template a title."))
	if frappe.db.exists("Planner Template", title):
		frappe.throw(_("A template called {0} already exists.").format(frappe.bold(title)))
	board = take(project)
	return frappe.get_doc(
		{
			"doctype": "Planner Template",
			"template_name": title,
			"description": (description or "").strip(),
			"project_type": frappe.db.get_value("Project", project, "project_type"),
			"parts": frappe.as_json(board["parts"], indent=None),
			"snapshot": frappe.as_json(board, indent=None),
		}
	).insert().name


@frappe.whitelist(methods=["POST"])
def setup_project(project, template=None, blank=0):
	"""Set up a project made in the desk (e.g. from a Sales Order): from a template, blank, or as it is."""
	check_project(project, "write")
	if not needs_setup(project):
		frappe.throw(_("This project is already set up."))
	if template:
		apply(project, template_board(template))
	elif frappe.utils.cint(blank):
		apply(project, {"parts": []})
	else:
		parts.set_view_parts(project, parts.VIEW_PARTS)  # keep everything as it shows today


@frappe.whitelist(methods=["POST"])
def set_sidebar_order(project, names):
	check_project(project, "write")
	set_sidebar(project, {**sidebar(project), "order": [str(n) for n in frappe.parse_json(names) or []][:500]})


@frappe.whitelist(methods=["POST"])
def hide_view(project, view):
	"""Take a shared view off this project's sidebar; other projects keep it."""
	check_project(project, "write")
	part, project_type = frappe.db.get_value("Planner View", view, ["part", "project_type"]) or (None, None)
	if not project_type:
		frappe.throw(_("Only shared views are hidden. Delete this project's own view instead."))
	if part in parts.VIEW_PARTS:
		parts.set_view_parts(project, [p for p in parts.stored_view_parts(project) if p != part])
		return
	value = sidebar(project)
	set_sidebar(project, {**value, "hidden": list(dict.fromkeys([*value.get("hidden", []), view]))})


@frappe.whitelist(methods=["POST"])
def show_view(project, view):
	check_project(project, "write")
	value = sidebar(project)
	set_sidebar(project, {**value, "hidden": [v for v in value.get("hidden", []) if v != view]})


# ── take and apply ────────────────────────────────────────────────────────────


def template_board(template):
	doc = frappe.get_doc("Planner Template", template)
	doc.check_permission("read")
	return frappe.parse_json(doc.snapshot) if doc.snapshot else {"parts": frappe.parse_json(doc.parts) or []}


def take(project):
	from event_planner.planner.api import property_fieldnames

	props = property_fieldnames()
	pages = frappe.get_all("Planner Page", filters={"project": project}, fields=PAGE_FIELDS, order_by="sort_order asc, creation asc")
	for page in pages:
		if page.page_kind == "BOQ":
			page["lines"] = frappe.get_all("Planner BOQ Line", filters={"page": page.name}, fields=LINE_FIELDS, order_by="sort_order asc, creation asc")
	items = frappe.get_all(
		"Task",
		filters={"project": project, "status": ["!=", "Cancelled"]},
		fields=[*ITEM_FIELDS, *props],
		order_by="lft asc",  # parents before their sub-items
	)
	return {
		"parts": parts.stored_view_parts(project),
		"categories": frappe.get_all("Action Category", filters={"project": project}, fields=["name", "title", "color", "sort_order"], order_by="sort_order asc, creation asc"),
		"pages": pages,
		"views": frappe.get_all("Planner View", filters={"project": project, "is_personal": 0}, fields=VIEW_FIELDS, order_by="sort_order asc, creation asc"),
		"items": [{k: v for k, v in item.items() if v not in (None, "")} for item in items],
		"sidebar": sidebar(project),
	}


def apply(project, board):
	"""Lay a board onto a project. Names in the board are the source project's; new ones are mapped."""
	# what the project already has is kept and reused, never added twice
	view_parts = [p for p in board.get("parts") or [] if p in parts.VIEW_PARTS]
	if frappe.db.get_value("Project", project, "ep_parts"):
		view_parts = [*parts.stored_view_parts(project), *view_parts]
	parts.set_view_parts(project, view_parts)
	names = {}

	for cat in board.get("categories") or []:
		names[cat["name"]] = frappe.db.get_value("Action Category", {"project": project, "title": cat["title"]}) or frappe.get_doc(
			{"doctype": "Action Category", "project": project, "title": cat["title"], "color": cat.get("color"), "sort_order": cat.get("sort_order") or 0}
		).insert().name

	if "pages" in board:
		apply_pages(project, board["pages"], names)
	else:  # a template that only lists parts
		have = parts.enabled_parts(project)
		for part in board.get("parts") or []:
			if part in parts.BY_KEY and parts.BY_KEY[part]["kind"] != "view" and part not in have:
				parts.add_page_part(project, part)

	for view in board.get("views") or []:
		values = {k: view.get(k) for k in VIEW_FIELDS if k != "name"}
		names[view["name"]] = frappe.db.get_value("Planner View", {"project": project, "title": view["title"]}) or frappe.get_doc(
			{"doctype": "Planner View", "project": project, **values}
		).insert().name

	apply_items(project, board.get("items") or [], names)

	value = board.get("sidebar") or {}
	if value:
		set_sidebar(project, {**value, "order": [names.get(n, n) for n in value.get("order", [])]})


def apply_pages(project, pages, names):
	for page in pages:
		same = {"project": project, "page_kind": page.get("page_kind"), "department": page.get("department") or "", "title": page.get("title")}
		if existing := frappe.db.get_value("Planner Page", same):
			names[page["name"]] = existing
			continue
		values = {k: page.get(k) for k in PAGE_FIELDS if k not in ("name", "parent_page")}
		doc = frappe.get_doc({"doctype": "Planner Page", "project": project, **values, "boq_status": "Draft"}).insert()
		names[page["name"]] = doc.name
		for line in page.get("lines") or []:
			frappe.get_doc({"doctype": "Planner BOQ Line", "page": doc.name, **{k: line.get(k) for k in LINE_FIELDS}}).insert()
	for page in pages:  # parents may come after their children in sort order
		if page.get("parent_page") in names:
			frappe.db.set_value("Planner Page", names[page["name"]], "parent_page", names[page["parent_page"]])


def apply_items(project, items, names):
	from event_planner.planner.api import property_fieldnames

	allowed = set(ITEM_FIELDS) | set(property_fieldnames())
	types = set(frappe.get_all("Task Type", pluck="name"))
	for item in items:
		values = {k: v for k, v in item.items() if k in allowed and k not in ("name", "parent_task", "ep_action_category", "type")}
		doc = frappe.get_doc(
			{
				"doctype": "Task",
				"project": project,
				**values,
				"type": item.get("type") if item.get("type") in types else None,
				"ep_action_category": names.get(item.get("ep_action_category")),
				"parent_task": names.get(item.get("parent_task")),
			}
		).insert()
		names[item["name"]] = doc.name
