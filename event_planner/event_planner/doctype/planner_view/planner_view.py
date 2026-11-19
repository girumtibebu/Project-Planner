import frappe
from frappe import _
from frappe.model.document import Document

from event_planner.planner.filters import validate_filters, validate_group_by, validate_order_by


class PlannerView(Document):
	"""Saved filters, grouping and layout over the work items of one project (or of every project of a type)."""

	def validate(self):
		if bool(self.project) == bool(self.project_type):
			frappe.throw(_("Set either a Project or a Project Type."))
		validate_filters(frappe.parse_json(self.filters) or [])
		validate_group_by(self.group_by)
		validate_order_by(self.order_by)
		check_lock(self)

	def on_trash(self):
		if self.is_locked and not can_lock(self):
			frappe.throw(_("This view is locked. Only its owner can delete it."))


def can_lock(doc, user=None):
	"""The owner (or a Projects Manager) locks, unlocks and edits a locked view or page."""
	user = user or frappe.session.user
	return doc.owner == user or bool({"Projects Manager", "System Manager"} & set(frappe.get_roles(user)))


def check_lock(doc):
	if doc.is_new() or can_lock(doc):
		return
	before = doc.get_doc_before_save()
	if before and (before.is_locked or doc.is_locked != before.is_locked):
		frappe.throw(_("This view is locked. Only its owner can change or unlock it."))


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if doc.is_personal and doc.owner != user:
		return False
	if doc.project:
		return frappe.has_permission("Project", "read" if ptype == "read" else "write", doc.project, user=user)
	# template views are shared configuration
	return ptype == "read" or "Projects Manager" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user)


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	return f"(`tabPlanner View`.is_personal = 0 or `tabPlanner View`.owner = {frappe.db.escape(user)})"
