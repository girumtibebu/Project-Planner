"""Team notifications: an at-a-glance project summary sent to n8n, which posts it to Discord or Telegram.

The text is kept in Project.ep_notify_text, so a desk Webhook or n8n can also read it.
It is sent when the project status changes and when someone presses "Notify team".
n8n gets JSON: event, project, project_name, status, customer, url, note and text.
"""

import frappe
from frappe import _
from frappe.utils import get_datetime, get_url

SHOW_LINES = 6  # BOQ lines shown per department before "+ n more"


def build_text(project, note=None):
	doc = frappe.get_doc("Project", project)
	out = [f"🔔 Project update: {doc.status}", f"✅ Project: {doc.project_name}"]
	if doc.customer:
		out.append(f"👤 Client: {frappe.db.get_value('Customer', doc.customer, 'customer_name') or doc.customer}")
	if doc.get("ep_location"):
		out.append(f"📍 Venue: {doc.ep_location}")
	if doc.expected_start_date:
		end = f" → {fmt_day(doc.expected_end_date)}" if doc.expected_end_date and doc.expected_end_date != doc.expected_start_date else ""
		out.append(f"🗓️ Dates: {fmt_day(doc.expected_start_date)}{end}")
	if note and note.strip():
		out += ["", f"📝 {note.strip()}"]

	schedule = schedule_lines(project)
	if schedule:
		out += ["", "SCHEDULE:", *schedule]
	boq = boq_lines(project)
	if boq:
		out += ["", "EQUIPMENT (tech BOQ):", *boq]
	out += ["", f"🔗 Open project: {project_url(project)}"]
	return "\n".join(out)


def schedule_lines(project):
	"""One line per day of the run of show: first start, last end and how many slots."""
	days = {}
	for row in frappe.get_all(
		"Task",
		filters={"project": project, "type": "Run of Show", "exp_start_date": ["is", "set"], "status": ["!=", "Cancelled"]},
		fields=["subject", "exp_start_date", "exp_end_date"],
		order_by="exp_start_date asc",
	):
		start = get_datetime(row.exp_start_date)
		end = get_datetime(row.exp_end_date or row.exp_start_date)
		day = days.setdefault(start.date(), {"start": start, "end": end, "count": 0, "first": row.subject})
		day["end"] = max(day["end"], end)
		day["count"] += 1
	return [
		f"• {d['start']:%a %d %b}: {d['start']:%H:%M}–{d['end']:%H:%M}, {d['first']}" + (f" + {d['count'] - 1} more" if d["count"] > 1 else "")
		for d in days.values()
	]


def boq_lines(project):
	out = []
	for page in frappe.get_all(
		"Planner Page",
		filters={"project": project, "page_kind": "BOQ"},
		fields=["name", "department", "icon", "boq_status"],
		order_by="sort_order asc, creation asc",
	):
		lines = frappe.get_all("Planner BOQ Line", filters={"page": page.name}, fields=["item", "qty", "unit"], order_by="sort_order asc, creation asc")
		if not lines:
			continue
		out.append(f"{page.icon or '🔧'} {page.department} ({page.boq_status}):")
		out += [f"  • {line.item}: {qty(line.qty)} {line.unit}" for line in lines[:SHOW_LINES]]
		if len(lines) > SHOW_LINES:
			out.append(f"  • + {len(lines) - SHOW_LINES} more")
	return out


def qty(value):
	return f"{value:g}" if value is not None else ""


def fmt_day(value):
	return f"{get_datetime(value):%a %d %b %Y}"


def project_url(project):
	return get_url(f"/planner/{project}")


# ── sending ───────────────────────────────────────────────────────────────────


@frappe.whitelist(methods=["POST"])
def notify_team(project, note=None, preview=0):
	"""Refresh the summary and, unless previewing, send it to n8n."""
	from event_planner.planner.api import check_project

	check_project(project, "write")
	text = refresh(project, note)
	if frappe.utils.cint(preview):
		return {"text": text, "sent": False}
	if not webhook_url():
		frappe.throw(_("Set the n8n webhook URL in Planner Settings first."))
	send(project, "manual", text, note)
	return {"text": text, "sent": True}


def on_project_update(doc, method=None):
	"""Project hook: tell the team when the status changes."""
	if doc.flags.in_insert or not doc.has_value_changed("status"):
		return
	text = refresh(doc.name)
	if webhook_url() and frappe.db.get_single_value("Planner Settings", "notify_on_status_change"):
		send(doc.name, "status_change", text)


def refresh(project, note=None):
	text = build_text(project, note)
	frappe.db.set_value("Project", project, "ep_notify_text", text, update_modified=False)
	return text


def webhook_url():
	return frappe.db.get_single_value("Planner Settings", "n8n_webhook_url")


def send(project, event, text, note=None):
	doc = frappe.db.get_value("Project", project, ["project_name", "status", "customer"], as_dict=True)
	payload = {"event": event, "project": project, **doc, "url": project_url(project), "note": note, "text": text}
	frappe.enqueue(post, queue="short", url=webhook_url(), payload=payload, enqueue_after_commit=True)


def post(url, payload):
	import requests

	try:
		requests.post(url, json=payload, timeout=15).raise_for_status()
	except Exception:
		frappe.log_error(title="Planner: n8n notification failed", message=frappe.get_traceback())
