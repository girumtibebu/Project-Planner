import frappe


def execute():
	"""Add the planner lists and switch on the clash check for the timed list types, once.

	After this, people can switch the check off per type; migrate will not switch it back on.
	"""
	from event_planner.install import _create_custom_fields
	from event_planner.planner import lists

	_create_custom_fields()  # ep_check_clashes on Task Type
	lists.ensure()
	for spec in lists.LISTS:
		frappe.db.set_value("Task Type", spec["type"], "ep_check_clashes", spec["clashes"])
