import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

TECH_FIELDS = ("item", "qty", "unit", "note")


class PlannerBOQLine(Document):
	"""One line of a department's tech BOQ: what the tech team asks for and what the warehouse booked."""

	def validate(self):
		project, kind = frappe.db.get_value("Planner Page", self.page, ["project", "page_kind"]) or (None, None)
		if kind != "BOQ":
			frappe.throw(_("BOQ lines belong on a BOQ page."))
		self.project = project
		if self.is_new() or any(self.has_value_changed(f) for f in TECH_FIELDS):
			self.tech_modified = now_datetime()

	def on_trash(self):
		# the warehouse cannot see a deleted line, so the page remembers that lines went away
		frappe.db.set_value("Planner Page", self.page, "lines_removed_at", now_datetime(), update_modified=False)


def has_permission(doc, ptype=None, user=None):
	project = doc.project or frappe.db.get_value("Planner Page", doc.page, "project")
	if not project:
		return False
	return frappe.has_permission("Project", "read" if ptype in ("read", "print") else "write", project, user=user)
