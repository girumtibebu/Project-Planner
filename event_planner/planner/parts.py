"""Project parts: what a project has in its sidebar (brief, tech BOQs, lists, debrief).

A part is either a page (brief, a department's BOQ, debrief) or a shared template view
(action plan, run of show, crew call sheet, logistics). Page parts are on when the page
exists. View parts are listed in Project.ep_parts; an older project with no list shows
every view, as before.

A new project is created from a Planner Template or blank, with the parts ticked.
"""

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

DEPARTMENTS = {"Audio": "🎤", "Video": "📺", "Lighting": "💡", "Rigging": "🪝", "Power": "⚡"}
BRIEF_TEMPLATE = "Events tech brief"

PARTS = [
	{"key": "brief", "label": "Brief", "group": "Docs", "kind": "page"},
	*[{"key": f"boq_{d.lower()}", "label": f"{d} BOQ", "group": "Tech BOQ", "kind": "boq", "department": d} for d in DEPARTMENTS],
	{"key": "action_plan", "label": "Action plan", "group": "Plan", "kind": "view"},
	{"key": "run_of_show", "label": "Run of show", "group": "Schedules", "kind": "view"},
	{"key": "crew_call", "label": "Crew call sheet", "group": "Schedules", "kind": "view"},
	{"key": "logistics", "label": "Logistics", "group": "Schedules", "kind": "view"},
	{"key": "debrief", "label": "Debrief", "group": "Docs", "kind": "page"},
]
PART_KEYS = {p["key"] for p in PARTS}
BY_KEY = {p["key"]: p for p in PARTS}
VIEW_PARTS = [p["key"] for p in PARTS if p["kind"] == "view"]


def page_part(page):
	"""The part a page stands for, if any."""
	if page.page_kind == "Brief":
		return "brief"
	if page.page_kind == "Debrief":
		return "debrief"
	if page.page_kind == "BOQ" and page.department:
		return f"boq_{page.department.lower()}"


def stored_view_parts(project):
	raw = frappe.db.get_value("Project", project, "ep_parts")
	return VIEW_PARTS[:] if not raw else [p for p in frappe.parse_json(raw) if p in VIEW_PARTS]


def enabled_parts(project):
	parts = stored_view_parts(project)
	for page in frappe.get_all("Planner Page", filters={"project": project}, fields=["page_kind", "department"]):
		key = page_part(page)
		if key and key not in parts:
			parts.append(key)
	return parts


def check_parts(parts):
	parts = list(dict.fromkeys(parts or []))
	unknown = [p for p in parts if p not in PART_KEYS]
	if unknown:
		frappe.throw(_("Unknown parts: {0}").format(", ".join(map(str, unknown))))
	return parts


# ── API ───────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def new_project_options():
	"""What the New project and Set up project dialogs offer."""
	return {
		"templates": frappe.get_all(
			"Planner Template", fields=["name", "template_name", "project_type", "description", "owner"], order_by="template_name asc"
		),
		"project_types": frappe.get_all("Project Type", pluck="name", order_by="name asc"),
		# shortcut: first 1000 clients; a client from a picked sales order is added in the dialog
		"customers": listed("Customer", fields=["name", "customer_name"], filters={"disabled": 0}, order_by="customer_name asc", limit=1000),
	}


@frappe.whitelist()
def search_sales_orders(txt=None):
	"""Submitted sales orders, not closed, with no project yet, matching the number or the client.
	A won order may already be billed before the event, so completed ones count."""
	txt = f"%{(txt or '').strip()}%"
	taken = set(frappe.get_all("Project", filters={"sales_order": ["is", "set"]}, pluck="sales_order"))
	rows = listed(
		"Sales Order",
		filters={"docstatus": 1, "status": ["!=", "Closed"]},
		or_filters=[["name", "like", txt], ["customer_name", "like", txt], ["customer", "like", txt]],
		fields=["name", "customer", "customer_name", "transaction_date", "delivery_date", "status"],
		order_by="transaction_date desc",
		limit=40,
	)
	return [r for r in rows if r.name not in taken][:20]


def listed(doctype, **kwargs):
	"""The rows this user may list, as in the desk; none when they may not list the doctype at all."""
	try:
		return frappe.get_list(doctype, **kwargs)
	except frappe.PermissionError:
		frappe.clear_messages()
		return []


@frappe.whitelist(methods=["POST"])
def create_project(data, template=None, parts=None):
	"""Create a project from a saved board (template), from a list of parts, or blank."""
	from event_planner.planner import boards

	frappe.has_permission("Project", "create", throw=True)
	data = frappe.parse_json(data) or {}
	name = (data.get("project_name") or "").strip()
	if not name:
		frappe.throw(_("Give the project a name."))
	board = boards.template_board(template) if template else {"parts": check_parts(frappe.parse_json(parts))}

	sales_order = data.get("sales_order") or None
	if sales_order and not listed("Sales Order", filters={"name": sales_order, "docstatus": 1}, limit=1):
		frappe.throw(_("Sales order {0} not found").format(sales_order), frappe.PermissionError)
	project = frappe.get_doc(
		{
			"doctype": "Project",
			"project_name": name,
			"project_type": data.get("project_type") or None,
			"expected_start_date": data.get("expected_start_date") or None,
			"expected_end_date": data.get("expected_end_date") or None,
			"customer": data.get("customer") or (frappe.db.get_value("Sales Order", sales_order, "customer") if sales_order else None),
			"sales_order": sales_order,
			"ep_location": (data.get("location") or "").strip() or None,
		}
	).insert()
	boards.apply(project.name, board)
	return {"name": project.name}


@frappe.whitelist(methods=["POST"])
def add_part(project, part):
	"""Add a part to an existing project: create its page, or show its list."""
	from event_planner.planner.api import check_project

	check_project(project, "write")
	(part,) = check_parts([part])
	if not frappe.db.get_value("Project", project, "ep_parts"):  # adding by hand counts as set up
		set_view_parts(project, stored_view_parts(project))
	if BY_KEY[part]["kind"] == "view":
		set_view_parts(project, [*stored_view_parts(project), part])
		return {"part": part}
	if part in enabled_parts(project):
		frappe.throw(_("This project already has a {0}.").format(BY_KEY[part]["label"]))
	return {"part": part, "page": add_page_part(project, part)}


@frappe.whitelist(methods=["POST"])
def mark_reviewed(page):
	"""The warehouse has seen this BOQ: lines changed before now stop showing as changed."""
	doc = frappe.get_doc("Planner Page", page)
	frappe.has_permission("Project", "write", doc.project, throw=True)
	values = {"reviewed_at": now_datetime(), "reviewed_by": frappe.session.user}
	frappe.db.set_value("Planner Page", page, values, update_modified=False)
	return values


# ── helpers ───────────────────────────────────────────────────────────────────


def set_view_parts(project, parts):
	frappe.db.set_value("Project", project, "ep_parts", frappe.as_json(list(dict.fromkeys(parts)), indent=None))


def add_page_part(project, part):
	from event_planner.planner.api import create_page

	spec = BY_KEY[part]
	if spec["kind"] == "boq":
		department = spec["department"]
		return (
			frappe.get_doc(
				{
					"doctype": "Planner Page",
					"project": project,
					"title": f"{department} BOQ",
					"icon": DEPARTMENTS[department],
					"page_kind": "BOQ",
					"department": department,
					"boq_status": "Draft",
					"sort_order": cint(frappe.db.count("Planner Page", {"project": project})),
				}
			)
			.insert()
			.name
		)
	if part == "brief":
		template = BRIEF_TEMPLATE if frappe.db.exists("Event Brief Template", BRIEF_TEMPLATE) else None
		return create_page(project, title=_("Event brief"), template=template, page_kind="Brief")["name"]
	template = frappe.db.get_value("Event Brief Template", {"kind": "debrief", "is_active": 1})
	return create_page(project, title=_("Debrief"), template=template, page_kind="Debrief")["name"]


STARTER_TEMPLATES = [
	(
		"Small rental",
		"Rental only: a short brief, the tech BOQs it needs and the delivery run.",
		["brief", "boq_audio", "boq_lighting", "boq_power", "logistics"],
	),
	("Full event", "A produced event: brief, every tech BOQ, action plan, schedules and debrief.", [p["key"] for p in PARTS]),
]


def ensure_starter_templates():
	"""Two starting points on a fresh site; after that, templates are the users' own."""
	if frappe.db.count("Planner Template"):
		return
	project_type = "Event" if frappe.db.exists("Project Type", "Event") else None
	for name, description, keys in STARTER_TEMPLATES:
		frappe.get_doc(
			{"doctype": "Planner Template", "template_name": name, "project_type": project_type, "description": description, "parts": frappe.as_json(keys, indent=None)}
		).insert(ignore_permissions=True)


def ensure_brief_template():
	if frappe.db.exists("Event Brief Template", BRIEF_TEMPLATE):
		return
	frappe.get_doc(
		{
			"doctype": "Event Brief Template",
			"template_name": BRIEF_TEMPLATE,
			"kind": "brief",
			"category": "Production",
			"is_active": 1,
			"seeded": 1,
			"description": "The producer's brief for the tech team: event facts, the client's items without prices, and notes per department.",
			"content": BRIEF_HTML,
		}
	).insert(ignore_permissions=True)


def _rows(labels):
	return "".join(f"<tr><th>{label}</th><td></td></tr>" for label in labels)


BRIEF_HTML = (
	"<h1>Event overview</h1>"
	"<p>Client, concept, audience and guest count.</p>"
	"<h2>Dates, venue and access</h2>"
	f"<table><tbody>{_rows(['Build day', 'Show day', 'Load-out', 'Venue', 'Site contact', 'Power at venue', 'Access and loading'])}</tbody></table>"
	"<h2>Schedule summary</h2>"
	"<p>Key times: doors, programme start, end of show.</p>"
	"<h2>Commercial BOQ and item requests</h2>"
	"<p>What the client bought, without prices. Each department builds its tech BOQ from this list.</p>"
	"<table><tbody><tr><th>Item</th><th>Qty</th><th>Unit</th><th>Notes</th></tr>"
	+ "<tr><td></td><td></td><td></td><td></td></tr>" * 3
	+ "</tbody></table>"
	"<h2>Department notes</h2>"
	+ "".join(f"<h3>{d}</h3><p>What {d.lower()} must deliver.</p>" for d in DEPARTMENTS)
)
