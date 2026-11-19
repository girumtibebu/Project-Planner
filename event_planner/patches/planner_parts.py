import frappe


def execute():
	"""Tag the template list views with their part, and drop the Equipment requests list (now tech BOQ pages)."""
	from event_planner.planner import lists, parts

	lists.ensure()
	parts.ensure_brief_template()
	parts.ensure_starter_templates()
	for name in frappe.get_all("Planner View", filters={"project_type": ["is", "set"], "title": "Equipment requests"}, pluck="name"):
		frappe.delete_doc("Planner View", name, ignore_permissions=True)
