from frappe.model.document import Document


class PlannerSettings(Document):
	"""Where the planner sends team notifications (an n8n webhook that posts to Discord or Telegram)."""
