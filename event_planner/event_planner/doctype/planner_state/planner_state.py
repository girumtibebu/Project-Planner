import frappe
from frappe import _
from frappe.model.document import Document


class PlannerState(Document):
	"""A Kanban column of one Project Type. Its group decides the ERPNext Task status."""

	def validate(self):
		if self.state_group != "Started":
			self.is_review = 0
		if self.is_default:
			frappe.db.set_value(
				"Planner State",
				{"project_type": self.project_type, "is_default": 1, "name": ["!=", self.name]},
				"is_default",
				0,
			)

	def on_trash(self):
		if frappe.db.exists("Task", {"ep_state": self.name}):
			frappe.throw(_("Move the work items in state {0} to another state first.").format(frappe.bold(self.title)))
