"""A fuller demo data set for a local or staging site (never production):

    bench --site <site> execute event_planner.planner.demo_rich.create

Three projects of different types around today's date, six team members, work item
types with properties, sub-items, dependencies, labels, comments, pages and views.
Running it again does nothing for projects that already exist.
"""

import json
import random

import frappe
from frappe.utils import add_days, getdate, today

from event_planner.planner.api import create_page, sync_assignees, sync_labels
from event_planner.planner.demo import create as create_basics

MEMBERS = [
	("selam@example.com", "Selam", "Tesfaye"),
	("dawit@example.com", "Dawit", "Bekele"),
	("hanna@example.com", "Hanna", "Girma"),
	("yonas@example.com", "Yonas", "Alemu"),
	("meron@example.com", "Meron", "Haile"),
	("abel@example.com", "Abel", "Tadesse"),
]

PROJECT_TYPES = {
	"Studio Shoot": [
		("Pre-production", "Unstarted", "#6B7280", 1, 0),
		("Scheduled", "Unstarted", "#3B82F6", 0, 0),
		("Shooting", "Started", "#F59E0B", 0, 0),
		("Post-production", "Started", "#8B5CF6", 0, 0),
		("Client review", "Started", "#EC4899", 0, 1),
		("Delivered", "Completed", "#10B981", 0, 0),
		("Dropped", "Cancelled", "#EF4444", 0, 0),
	],
	"Decor Job": [
		("Concept", "Backlog", "#9CA3AF", 0, 0),
		("Design", "Unstarted", "#6B7280", 1, 0),
		("Approved", "Unstarted", "#3B82F6", 0, 0),
		("In production", "Started", "#F59E0B", 0, 0),
		("On site", "Started", "#14B8A6", 0, 0),
		("Done", "Completed", "#10B981", 0, 0),
		("Cancelled", "Cancelled", "#EF4444", 0, 0),
	],
}

TYPES = [
	("Shot", "lucide-camera", "#EC4899"),
	("Deliverable", "lucide-clapperboard", "#8B5CF6"),
	("Design", "lucide-palette", "#F59E0B"),
	("Production", "lucide-hammer", "#6B7280"),
	("Setup", "lucide-package", "#14B8A6"),
	("Meeting", "lucide-users", "#3B82F6"),
]

PROPERTIES = [
	("Shot", "Shot type", "Dropdown", "Wide\nMedium\nClose-up\nDrone\nGimbal"),
	("Shot", "Lens", "Text", None),
	("Deliverable", "Format", "Dropdown", "16:9 Master\n9:16 Reel\n1:1 Square\nStills"),
	("Deliverable", "Client approved", "Checkbox", None),
	("Setup", "Crew size", "Number", None),
	("Site Visit", "Contact person", "Member", None),
	("Meeting", "Meeting link", "URL", None),
]

LABELS = ["client", "urgent", "vendor", "budget", "creative", "tech", "on-site", "approval"]

# (subject, type, group, start offset, length in days, priority, labels, time "HH:MM-HH:MM" on that day or None)
EVENT_PLAN = [
	("Client kick-off meeting", "Meeting", "Production", -24, 0, "High", ["client"], "10:00-11:30"),
	("Agree budget and scope", "Milestone", "Production", -21, 0, "Urgent", ["budget", "approval"], None),
	("Venue shortlist", "Site Visit", "Logistics", -20, 3, "Medium", ["vendor"], None),
	("Venue recce – Skylight", "Site Visit", "Logistics", -16, 0, "High", ["on-site"], "14:00-16:00"),
	("Venue contract signed", "Milestone", "Logistics", -12, 0, "Urgent", ["vendor", "approval"], None),
	("Creative concept", "Design", "Creative", -18, 8, "High", ["creative"], None),
	("Concept presentation", "Meeting", "Creative", -9, 0, "High", ["client", "creative"], "15:00-16:30"),
	("Stage design", "Design", "Creative", -8, 10, "High", ["creative"], None),
	("Screen content and animations", "Task", "Creative", -2, 14, "Medium", ["creative"], None),
	("Brand assets from client", "Task", "Creative", -6, 3, "Medium", ["client"], None),
	("Book LED wall", "Logistics", "Technical", -10, 4, "High", ["vendor", "tech"], None),
	("Book sound and lighting", "Logistics", "Technical", -9, 5, "High", ["vendor", "tech"], None),
	("Power and generator plan", "Task", "Technical", -1, 6, "Medium", ["tech"], None),
	("Tech rider to venue", "Task", "Technical", 3, 2, "Medium", ["tech", "vendor"], None),
	("Catering tasting", "Meeting", "Hospitality", 2, 0, "Medium", ["vendor"], "12:30-14:00"),
	("Catering order", "Logistics", "Hospitality", 4, 3, "Medium", ["vendor", "budget"], None),
	("Guest list and RSVPs", "Task", "Hospitality", -5, 18, "High", ["client"], None),
	("Invitations sent", "Milestone", "Hospitality", 1, 0, "High", ["client"], None),
	("Transport for crew and gear", "Logistics", "Logistics", 9, 4, "Low", ["vendor"], None),
	("Run of show draft", "Run of Show", "Production", 0, 7, "High", [], None),
	("Run of show sign-off", "Milestone", "Production", 8, 0, "Urgent", ["client", "approval"], None),
	("Weekly status call", "Meeting", "Production", -14, 0, "Low", ["client"], "09:00-09:30"),
	("Weekly status call", "Meeting", "Production", -7, 0, "Low", ["client"], "09:00-09:30"),
	("Weekly status call", "Meeting", "Production", 0, 0, "Low", ["client"], "09:00-09:30"),
	("Weekly status call", "Meeting", "Production", 7, 0, "Low", ["client"], "09:00-09:30"),
	("Load-in and stage build", "Setup", "Technical", 13, 1, "Urgent", ["on-site", "tech"], None),
	("Technical rehearsal", "Run of Show", "Technical", 14, 0, "High", ["on-site", "tech"], "14:00-18:00"),
	("Doors open", "Run of Show", "Production", 15, 0, "Urgent", ["on-site"], "17:30-18:00"),
	("Welcome speech", "Run of Show", "Production", 15, 0, "High", ["on-site"], "18:00-18:20"),
	("Product reveal", "Run of Show", "Production", 15, 0, "Urgent", ["on-site", "creative"], "18:20-18:45"),
	("Dinner service", "Run of Show", "Hospitality", 15, 0, "Medium", ["on-site"], "19:00-20:30"),
	("Live band", "Run of Show", "Production", 15, 0, "Medium", ["on-site"], "20:30-22:00"),
	("Event day", "Milestone", "Production", 15, 0, "Urgent", ["on-site"], None),
	("Load-out", "Setup", "Technical", 16, 0, "Medium", ["on-site"], "08:00-14:00"),
	("Photographer and videographer brief", "Task", "Creative", 6, 2, "Medium", ["creative"], None),
	("Post-event report", "Deliverable", "Production", 18, 4, "Medium", ["client"], None),
	("Final invoice", "Task", "Production", 20, 2, "High", ["budget"], None),
	("Merch and give-aways", "Logistics", "Hospitality", None, None, "Low", ["vendor"], None),
	("Backup MC", "Task", "Production", None, None, "Low", [], None),
]

SHOOT_PLAN = [
	("Script approval", "Milestone", "Pre-production", -12, 0, "Urgent", ["client", "approval"], None),
	("Storyboard", "Design", "Pre-production", -11, 5, "High", ["creative"], None),
	("Casting call", "Meeting", "Pre-production", -7, 0, "High", [], "10:00-15:00"),
	("Location scouting", "Site Visit", "Pre-production", -6, 2, "Medium", ["on-site"], None),
	("Shot list", "Task", "Pre-production", -4, 3, "High", ["creative"], None),
	("Gear list and rental request", "Logistics", "Pre-production", -3, 2, "High", ["tech", "vendor"], None),
	("Call sheet day 1", "Task", "Pre-production", 1, 0, "High", [], None),
	("Opening wide – city skyline", "Shot", "Shoot day 1", 3, 0, "High", [], "06:00-07:30"),
	("Family dinner scene", "Shot", "Shoot day 1", 3, 0, "Urgent", [], "09:00-12:00"),
	("Close-ups – phone screen", "Shot", "Shoot day 1", 3, 0, "Medium", [], "13:00-15:00"),
	("Drone – Entoto road", "Shot", "Shoot day 1", 3, 0, "Medium", ["on-site"], "16:00-17:30"),
	("Office scene", "Shot", "Shoot day 2", 4, 0, "High", [], "08:00-11:00"),
	("Street interviews", "Shot", "Shoot day 2", 4, 0, "Medium", ["on-site"], "11:30-14:00"),
	("Product hero shot", "Shot", "Shoot day 2", 4, 0, "Urgent", ["creative"], "15:00-18:00"),
	("Wrap and gear return", "Logistics", "Shoot day 2", 5, 0, "Medium", ["tech"], "09:00-11:00"),
	("Rough cut", "Deliverable", "Post", 6, 5, "High", ["creative"], None),
	("Colour grade", "Task", "Post", 11, 3, "Medium", ["creative"], None),
	("Sound mix and music", "Task", "Post", 11, 4, "Medium", ["creative"], None),
	("Client review round 1", "Meeting", "Post", 12, 0, "High", ["client", "approval"], "14:00-15:00"),
	("Master 60s TVC", "Deliverable", "Post", 15, 2, "Urgent", ["client"], None),
	("Social cut-downs", "Deliverable", "Post", 16, 3, "Medium", ["client"], None),
	("Stills selection", "Deliverable", "Post", 14, 2, "Low", [], None),
	("Delivery to broadcaster", "Milestone", "Post", 19, 0, "Urgent", ["client"], None),
]

DECOR_PLAN = [
	("Moodboard", "Design", "Design", -10, 3, "High", ["creative"], None),
	("Client design meeting", "Meeting", "Design", -6, 0, "High", ["client"], "11:00-12:00"),
	("Floor plan and table layout", "Design", "Design", -5, 4, "High", ["creative"], None),
	("Design sign-off", "Milestone", "Design", -1, 0, "Urgent", ["client", "approval"], None),
	("Fabric and florals order", "Logistics", "Sourcing", 0, 3, "High", ["vendor", "budget"], None),
	("Centrepieces x 40", "Production", "Workshop", 2, 6, "High", [], None),
	("Backdrop frame build", "Production", "Workshop", 3, 5, "Medium", [], None),
	("Lighting plan with Events", "Meeting", "Design", 4, 0, "Medium", ["tech"], "15:00-16:00"),
	("Chair covers and sashes", "Production", "Workshop", 5, 4, "Low", [], None),
	("Pack and load truck", "Logistics", "Setup", 10, 0, "High", ["on-site"], "06:00-09:00"),
	("Ballroom setup", "Setup", "Setup", 10, 0, "Urgent", ["on-site"], "09:00-17:00"),
	("Final walk-through", "Site Visit", "Setup", 10, 0, "High", ["client", "on-site"], "17:00-18:00"),
	("Gala night", "Milestone", "Setup", 11, 0, "Urgent", ["on-site"], None),
	("Breakdown and return", "Setup", "Setup", 12, 0, "Medium", ["on-site"], "07:00-12:00"),
	("Damage and stock check", "Task", "Setup", 13, 1, "Low", [], None),
]

SUB_ITEMS = {
	"Stage design": ["Stage floor plan", "Truss drawing", "Screen placement", "Client approval of renders"],
	"Guest list and RSVPs": ["Import client list", "Send save-the-date", "Chase RSVPs", "Final seating plan"],
	"Shot list": ["Day 1 shots", "Day 2 shots", "B-roll list"],
	"Centrepieces x 40": ["Prototype one", "Client check", "Produce remaining 39"],
}

DEPENDENCIES = [
	("Venue contract signed", "Venue recce – Skylight"),
	("Stage design", "Creative concept"),
	("Book LED wall", "Venue contract signed"),
	("Tech rider to venue", "Book sound and lighting"),
	("Run of show sign-off", "Run of show draft"),
	("Technical rehearsal", "Load-in and stage build"),
	("Event day", "Technical rehearsal"),
	("Post-event report", "Event day"),
	("Family dinner scene", "Casting call"),
	("Rough cut", "Product hero shot"),
	("Colour grade", "Rough cut"),
	("Master 60s TVC", "Client review round 1"),
	("Delivery to broadcaster", "Master 60s TVC"),
	("Centrepieces x 40", "Design sign-off"),
	("Ballroom setup", "Pack and load truck"),
]

COMMENTS = [
	"Can we confirm this with the client by Friday?",
	"Vendor quote attached in the shared drive.",
	"Done from my side, over to you.",
	"Moved one day later because of the venue.",
	"Need a second pair of hands here.",
	"Looks good 👍",
]

PAGE_RUN_SHEET = """<h1>Run of show</h1><p>Event day timings. The stage manager owns this sheet.</p>
<h2>Before doors</h2><table><tr><th>Time</th><th>What</th><th>Who</th></tr>
<tr><td>12:00</td><td>Crew call</td><td>All crew</td></tr><tr><td>14:00</td><td>Tech rehearsal</td><td>AV team</td></tr>
<tr><td>16:30</td><td>Final walk-through with client</td><td>Producer</td></tr></table>
<h2>Show</h2><table><tr><th>Time</th><th>What</th><th>Cue</th></tr>
<tr><td>17:30</td><td>Doors open</td><td>Walk-in music</td></tr><tr><td>18:00</td><td>Welcome speech</td><td>MC mic on</td></tr>
<tr><td>18:20</td><td>Product reveal</td><td>Lights down, video 1</td></tr><tr><td>19:00</td><td>Dinner</td><td>Background playlist</td></tr>
<tr><td>20:30</td><td>Live band</td><td>Stage lights full</td></tr></table>
<h2>After</h2><ul><li>Guests out by 22:30</li><li>Load-out starts 08:00 next day</li></ul>
<blockquote>Any change to timings goes through the producer.</blockquote>"""

PAGE_CALL_SHEET = """<h1>Call sheet</h1><h2>Day 1</h2><p><strong>Location:</strong> Bole, client office and Entoto road.</p>
<table><tr><th>Role</th><th>Name</th><th>Call</th></tr><tr><td>Director</td><td>Hanna</td><td>05:30</td></tr>
<tr><td>DOP</td><td>Yonas</td><td>05:30</td></tr><tr><td>Gaffer</td><td>Abel</td><td>05:00</td></tr><tr><td>Talent</td><td>Cast A, B</td><td>07:30</td></tr></table>
<h2>Day 2</h2><p>Office scene first; product hero shot last, studio B.</p><h3>Notes</h3>
<ul data-type="taskList"><li data-type="taskItem" data-checked="true">Permits printed</li><li data-type="taskItem" data-checked="false">Drone licence copy</li></ul>"""


def create():
	random.seed(7)
	create_basics()
	setup_members()
	setup_types()
	out = {}
	start = getdate(today())
	out["event"] = build_project(
		"Coca-Cola Summer Launch", "Event", "CCL", start, -28, 26, "Skylight Hotel",
		["Logistics", "Creative", "Production", "Technical", "Hospitality"], EVENT_PLAN,
		[("Run sheet", "Run Sheet", "🎤", PAGE_RUN_SHEET)],
		[("Run of show", "Gantt", "group", [["type", "in", ["Run of Show", "Milestone"]]], {"zoom": "day", "card_fields": ["time", "assignees"]}),
		 ("Team board", "Kanban", "assignee", [], {"swimlanes": "group", "card_fields": ["id", "type", "priority", "due_date", "labels"]}),
		 ("This month", "Calendar", "state", [], {"cal_mode": "month", "card_fields": ["type", "id"]})],
	)
	out["shoot"] = build_project(
		"Ethio Telecom TVC Shoot", "Studio Shoot", "ETS", start, -14, 22, "Bole studio B",
		["Pre-production", "Shoot day 1", "Shoot day 2", "Post"], SHOOT_PLAN,
		[("Call sheet", "Call Sheet", "🎬", PAGE_CALL_SHEET)],
		[("Shoot days", "Calendar", "state", [["type", "in", ["Shot"]]], {"cal_mode": "week", "card_fields": ["time", "properties"]}),
		 ("Post board", "Kanban", "state", [["group", "in", []]], {"card_fields": ["id", "type", "assignees", "properties"]})],
	)
	out["decor"] = build_project(
		"Hilton Gala Dinner Decor", "Decor Job", "HGD", start, -12, 15, "Hilton Addis, ballroom",
		["Design", "Sourcing", "Workshop", "Setup"], DECOR_PLAN, [],
		[("Workshop timeline", "Gantt", "group", [], {"zoom": "week", "bar_color": "group"})],
	)
	frappe.db.commit()
	return out


def setup_members():
	for email, first, last in MEMBERS:
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": first, "last_name": last, "send_welcome_email": 0, "user_type": "System User"}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", email).add_roles("Projects User")


def setup_types():
	for project_type, states in PROJECT_TYPES.items():
		if not frappe.db.exists("Project Type", project_type):
			frappe.get_doc({"doctype": "Project Type", "project_type": project_type}).insert()
		if not frappe.db.exists("Planner State", {"project_type": project_type}):
			for order, (title, group, color, default, review) in enumerate(states):
				frappe.get_doc(
					{"doctype": "Planner State", "project_type": project_type, "title": title, "state_group": group, "color": color, "is_default": default, "is_review": review, "sort_order": order}
				).insert()
	for name, icon, color in TYPES:
		if not frappe.db.exists("Task Type", name):
			frappe.get_doc({"doctype": "Task Type", "__newname": name}).insert()
		frappe.db.set_value("Task Type", name, {"ep_icon": icon, "ep_color": color})
	for task_type, label, kind, options in PROPERTIES:
		if not frappe.db.exists("Planner Property", {"task_type": task_type, "label": label}):
			frappe.get_doc({"doctype": "Planner Property", "task_type": task_type, "label": label, "property_type": kind, "options": options}).insert()


def pick_state(states, start, length, base):
	"""Past work is done, current work is started, future work is planned; a few are backlog or cancelled."""
	by_group = {}
	for s in states:
		by_group.setdefault(s.state_group, []).append(s.name)
	if start is None:
		return (by_group.get("Backlog") or by_group["Unstarted"])[0]
	end = start + (length or 0)
	if random.random() < 0.04 and by_group.get("Cancelled"):
		return by_group["Cancelled"][0]
	if end < 0:
		return random.choice(by_group["Completed"]) if random.random() < 0.85 else random.choice(by_group["Started"])
	if start <= 0 <= end:
		return random.choice(by_group["Started"])
	return random.choice(by_group["Unstarted"])


def build_project(name, project_type, key, base, first, last, location, groups, plan, pages, views):
	existing = frappe.db.get_value("Project", {"project_name": name})
	if existing:
		return existing
	project = frappe.get_doc(
		{
			"doctype": "Project",
			"project_name": name,
			"project_type": project_type,
			"ep_key": key,
			"expected_start_date": add_days(base, first),
			"expected_end_date": add_days(base, last),
			"ep_location": location,
			"priority": "High",
		}
	).insert()
	group_ids = {}
	palette = ["#3B82F6", "#EC4899", "#F59E0B", "#14B8A6", "#8B5CF6", "#6B7280"]
	for order, title in enumerate(groups):
		group_ids[title] = frappe.get_doc(
			{"doctype": "Action Category", "title": title, "project": project.name, "color": palette[order % len(palette)], "sort_order": order}
		).insert().name

	from event_planner.planner.work_items import get_states

	states = get_states(project_type)
	members = [m[0] for m in MEMBERS] + ["Administrator"]
	tasks = {}
	done_names = []
	for subject, type_, group, s, length, priority, labels, time in plan:
		values = {
			"doctype": "Task",
			"project": project.name,
			"subject": subject,
			"type": type_,
			"priority": priority,
			"ep_action_category": group_ids[group],
			"is_milestone": 1 if type_ == "Milestone" else 0,
			"is_group": 1 if subject in SUB_ITEMS else 0,
			"ep_state": pick_state(states, s, length, base),
			"description": f"<p>{subject} for {name}.</p>",
		}
		if s is not None:
			day = add_days(base, s)
			if time:
				a, b = time.split("-")
				values["exp_start_date"] = f"{day} {a}:00"
				values["exp_end_date"] = f"{day} {b}:00"
			else:
				values["exp_start_date"] = f"{day} 09:00:00"
				values["exp_end_date"] = f"{add_days(day, length or 0)} 18:00:00"
			values["expected_time"] = random.choice([1, 2, 4, 8, 16])
		set_properties(values, type_)
		doc = frappe.get_doc(values)
		if frappe.db.get_value("Planner State", doc.ep_state, "state_group") == "Completed":
			doc.completed_on = min(getdate(today()), getdate(values.get("exp_end_date", today())))
			done_names.append(subject)
		doc.insert()
		key_name = subject if subject not in tasks else f"{subject} #{len(tasks)}"
		tasks[key_name] = doc
		sync_assignees(doc, random.sample(members, random.choice([1, 1, 2, 2, 3])))
		if labels:
			sync_labels(doc, labels)

	for parent_subject, subs in SUB_ITEMS.items():
		parent = tasks.get(parent_subject)
		if not parent:
			continue
		parent_done = frappe.db.get_value("Planner State", parent.ep_state, "state_group") == "Completed"
		for i, sub in enumerate(subs):
			# ERPNext refuses an open sub-item under a completed parent; otherwise leave the last one open
			last_open = not parent_done and i == len(subs) - 1
			child = frappe.get_doc(
				{
					"doctype": "Task",
					"project": project.name,
					"subject": sub,
					"parent_task": parent.name,
					"type": "Task",
					"priority": parent.priority,
					"ep_action_category": parent.ep_action_category,
					"exp_start_date": parent.exp_start_date,
					"exp_end_date": parent.exp_end_date,
					"ep_state": next(s["name"] for s in states if s["state_group"] == "Unstarted") if last_open else parent.ep_state,
				}
			)
			if frappe.db.get_value("Planner State", child.ep_state, "state_group") == "Completed":
				child.completed_on = parent.completed_on or today()
			child.insert()
			sync_assignees(child, random.sample(members, 1))

	for blocked, blocker in DEPENDENCIES:
		if blocked in tasks and blocker in tasks:
			doc = frappe.get_doc("Task", tasks[blocked].name)
			doc.append("depends_on", {"task": tasks[blocker].name})
			doc.flags.ignore_validate = False
			try:
				doc.save()
			except frappe.ValidationError:
				frappe.clear_messages()

	add_comments(list(tasks.values()), members)

	template = frappe.db.get_value("Event Brief Template", {"kind": "brief", "category": "Production"}) or frappe.db.get_value("Event Brief Template", {"kind": "brief"})
	if template:
		brief = create_page(project.name, template=template)
		frappe.db.set_value("Planner Page", brief["name"], "icon", "📝")
	for title, kind, icon, html in pages:
		page = frappe.get_doc({"doctype": "Planner Page", "project": project.name, "title": title, "page_kind": kind, "icon": icon, "content": html}).insert()
		frappe.get_doc({"doctype": "Planner Page", "project": project.name, "title": "Open questions", "parent_page": page.name, "page_kind": "Notes", "icon": "❓",
			"content": "<h2>To confirm</h2><ul><li>Final guest count</li><li>Backup generator</li></ul>"}).insert()

	for title, layout, group_by, filters, display in views:
		if layout == "Kanban" and filters and filters[0][0] == "group":
			filters = [["group", "in", [group_ids.get("Post")]]] if "Post" in group_ids else []
		frappe.get_doc(
			{"doctype": "Planner View", "title": title, "project": project.name, "layout": layout, "group_by": group_by,
			 "filters": json.dumps(filters), "display": json.dumps(display), "order_by": "start_date asc" if layout == "Gantt" else "manual asc"}
		).insert()
	return project.name


def set_properties(values, type_):
	for prop in frappe.get_all("Planner Property", filters={"task_type": type_}, fields=["fieldname", "property_type", "options"]):
		if not frappe.get_meta("Task").has_field(prop.fieldname):
			continue
		if prop.property_type == "Dropdown":
			values[prop.fieldname] = random.choice(prop.options.split("\n"))
		elif prop.property_type == "Text":
			values[prop.fieldname] = random.choice(["24-70mm", "35mm", "50mm", "85mm", "16-35mm"])
		elif prop.property_type == "Number":
			values[prop.fieldname] = random.choice([4, 6, 8, 12])
		elif prop.property_type == "Checkbox":
			values[prop.fieldname] = random.choice([0, 1])
		elif prop.property_type == "Member":
			values[prop.fieldname] = random.choice(MEMBERS)[0]
		elif prop.property_type == "URL":
			values[prop.fieldname] = "https://meet.example.com/planner"


def add_comments(tasks, members):
	user = frappe.session.user
	try:
		for task in random.sample(tasks, min(12, len(tasks))):
			for _ in range(random.choice([1, 2])):
				frappe.set_user(random.choice(members))
				frappe.get_doc("Task", task.name).add_comment("Comment", f"<p>{random.choice(COMMENTS)}</p>")
	finally:
		frappe.set_user(user)
