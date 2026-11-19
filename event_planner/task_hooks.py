"""Task document hooks owned by Event Planner."""

import json

import frappe


def sync_assigned_to_from_assign(doc, method=None):
	"""
	Keep `_assign` (Frappe JSON list) and `assigned_to` (our custom Link) in sync.

	Priority:
	  - If _assign changed → reflect the first user into assigned_to.
	  - If assigned_to changed (e.g. set via REST API) → reflect into _assign
	    so Frappe's native assignment UX stays consistent.
	"""
	if not doc or doc.doctype != "Task":
		return

	meta = frappe.get_meta("Task")
	if not meta.has_field("assigned_to"):
		return

	# --- Read both fields ---
	raw_assign = doc.get("_assign") or ""
	assigned_to = doc.get("assigned_to") or ""

	users_from_assign = []
	if raw_assign:
		try:
			parsed = json.loads(raw_assign)
			if isinstance(parsed, list):
				users_from_assign = [u for u in parsed if u]
		except (TypeError, ValueError):
			pass

	first_from_assign = users_from_assign[0] if users_from_assign else None

	# Prefer _assign as source of truth if it's non-empty
	if first_from_assign:
		if assigned_to != first_from_assign:
			doc.set("assigned_to", first_from_assign)
	elif assigned_to:
		# _assign was empty / cleared; reflect assigned_to back into _assign
		new_assign_json = json.dumps([assigned_to])
		if doc.get("_assign") != new_assign_json:
			doc._assign = new_assign_json
	else:
		# Both empty — clear assigned_to
		if assigned_to:
			doc.set("assigned_to", None)
