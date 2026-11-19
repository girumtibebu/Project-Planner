import frappe
from frappe import _
from frappe.model.document import Document

from event_planner.event_planner.doctype.planner_view.planner_view import can_lock


class PlannerPage(Document):
	"""A document page of a project: brief, debrief, call sheet, run sheet or notes."""

	def validate(self):
		if self.parent_page:
			self.validate_parent()
		if not self.is_new() and self.get_db_value("is_locked") and self.is_locked and self.has_value_changed("content"):
			frappe.throw(_("This page is locked. Unlock it to edit."))
		if not self.is_new() and self.has_value_changed("is_locked") and not can_lock(self):
			frappe.throw(_("Only the page's owner can lock or unlock it."))
		if not self.is_new() and self.has_value_changed("content"):
			self.version = (self.version or 1) + 1

	def validate_parent(self):
		parent = self.parent_page
		while parent:
			if parent == self.name:
				frappe.throw(_("A page cannot be inside itself."))
			project, parent = frappe.db.get_value("Planner Page", parent, ["project", "parent_page"])
			if project != self.project:
				frappe.throw(_("The parent page belongs to another project."))

	def on_trash(self):
		if self.is_locked and not can_lock(self):
			frappe.throw(_("This page is locked. Only its owner can delete it."))
		frappe.db.delete("Planner BOQ Line", {"page": self.name})
		frappe.db.set_value("Planner Page", {"parent_page": self.name}, "parent_page", self.parent_page)


def has_permission(doc, ptype=None, user=None):
	return frappe.has_permission("Project", "read" if ptype in ("read", "print") else "write", doc.project, user=user)
