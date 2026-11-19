"""Who changed what on a page: from Frappe's change log (Version), line inserts and deletions.

Text autosaves every second while someone types, so edits of the text by the same person
within EDIT_WINDOW are shown as one entry.
"""

import json

import frappe
from frappe import _
from frappe.utils import get_datetime

EDIT_WINDOW = 15 * 60  # seconds
LIMIT = 300

PAGE_FIELDS = {
	"title": _("title"),
	"icon": _("icon"),
	"page_kind": _("kind"),
	"boq_status": _("BOQ status"),
	"department": _("department"),
	"parent_page": _("parent page"),
}
LINE_FIELDS = {
	"item": _("item"),
	"qty": _("qty"),
	"unit": _("unit"),
	"note": _("note"),
	"qty_booked": _("booked qty"),
	"line_status": _("status"),
	"warehouse_note": _("warehouse note"),
}


@frappe.whitelist()
def page_history(page):
	doc = frappe.get_doc("Planner Page", page)
	doc.check_permission("read")
	events = [event(doc.owner, doc.creation, _("created the page"))]
	if doc.reviewed_at:
		events.append(event(doc.reviewed_by, doc.reviewed_at, _("marked the BOQ as reviewed by the warehouse"), kind="review"))

	for version in versions("Planner Page", [page]):
		for field, old, new in version.changed:
			if field == "content":
				events.append(event(version.owner, version.creation, _("edited the text"), kind="text"))
			elif field == "is_locked":
				events.append(event(version.owner, version.creation, _("locked the page") if new else _("unlocked the page"), kind="lock"))
			elif field in PAGE_FIELDS:
				events.append(event(version.owner, version.creation, _("changed the {0} from {1} to {2}").format(PAGE_FIELDS[field], show(old), show(new))))

	if doc.page_kind == "BOQ":
		events += line_events(page)
	return merge_text_edits(sorted(events, key=lambda e: e["at"], reverse=True))[:LIMIT]


def line_events(page):
	lines = frappe.get_all("Planner BOQ Line", filters={"page": page}, fields=["name", "item", "owner", "creation"])
	items = {line.name: line.item for line in lines}
	out = [event(line.owner, line.creation, _("added {0}").format(bold(line.item)), kind="add") for line in lines]
	for version in versions("Planner BOQ Line", list(items)):
		for field, old, new in version.changed:
			if field in LINE_FIELDS and not (blank(old) and blank(new)):  # 0 -> empty is not a change
				what = _("{0} of {1}").format(LINE_FIELDS[field], bold(items[version.docname]))
				out.append(event(version.owner, version.creation, _("changed the {0} from {1} to {2}").format(what, show(old), show(new)), kind="line"))
	# deleted lines are kept in Deleted Document
	for deleted in frappe.get_all(
		"Deleted Document",
		filters={"deleted_doctype": "Planner BOQ Line", "data": ["like", f'%"page": "{page}"%']},
		fields=["owner", "creation", "data"],
		limit=LIMIT,
	):
		item = (json.loads(deleted.data or "{}") or {}).get("item")
		out.append(event(deleted.owner, deleted.creation, _("removed {0}").format(bold(item)), kind="remove"))
	return out


def versions(doctype, names):
	if not names:
		return []
	rows = frappe.get_all(
		"Version",
		filters={"ref_doctype": doctype, "docname": ["in", names]},
		fields=["docname", "owner", "creation", "data"],
		order_by="creation desc",
		limit=LIMIT * 3,
	)
	for row in rows:
		row.changed = (json.loads(row.data or "{}") or {}).get("changed") or []
	return rows


def merge_text_edits(events):
	"""Newest first: fold a run of text edits by one person into the newest of them."""
	out = []
	for e in events:
		last = out[-1] if out else None
		if (
			e["kind"] == "text"
			and last
			and last["kind"] == "text"
			and last["user"] == e["user"]
			and (get_datetime(last["first"]) - get_datetime(e["at"])).total_seconds() <= EDIT_WINDOW
		):
			last["first"] = e["at"]
			last["count"] += 1
			continue
		out.append(e)
	return out


def event(user, at, text, kind="page"):
	return {"user": user, "at": at, "first": at, "text": text, "kind": kind, "count": 1}


def bold(value):
	return f"<b>{frappe.utils.escape_html(str(value or ''))}</b>"


def number(value):
	"""The change log keeps numbers as text ("6.00"); show them as 6 or 6.5."""
	try:
		return f"{float(value):g}"
	except (TypeError, ValueError):
		return None


def blank(value):
	return value in (None, "") or number(value) == "0"


def show(value):
	if value in (None, ""):
		return _("empty")
	return bold(number(value) or value) if not isinstance(value, bool) else bold(value)
