import frappe
from frappe import _
from frappe.model.document import Document


class PlannerTemplate(Document):
	"""A set of project parts (brief, tech BOQs, lists) that a new project starts with."""

	def validate(self):
		from event_planner.planner.parts import PART_KEYS

		parts = frappe.parse_json(self.parts) or []
		unknown = [p for p in parts if p not in PART_KEYS]
		if unknown:
			frappe.throw(_("Unknown parts: {0}").format(", ".join(map(str, unknown))))
		self.parts = frappe.as_json(parts, indent=None)
