import re

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.model.document import Document

# property type -> Task Custom Field definition
FIELD_TYPES = {
	"Text": {"fieldtype": "Data"},
	"Number": {"fieldtype": "Float"},
	"Dropdown": {"fieldtype": "Select"},
	"Date": {"fieldtype": "Date"},
	"Member": {"fieldtype": "Link", "options": "User"},
	"Checkbox": {"fieldtype": "Check"},
	"URL": {"fieldtype": "Data", "options": "URL"},
}


class PlannerProperty(Document):
	"""A field of one work item type, stored as a real Custom Field on Task so it can be filtered and reported."""

	def validate(self):
		if self.property_type == "Dropdown":
			options = [line.strip() for line in (self.options or "").splitlines() if line.strip()]
			if not options:
				frappe.throw(_("Add at least one option, one per line."))
			self.options = "\n".join(options)
		if self.is_new() or not self.fieldname:
			self.fieldname = self.unique_fieldname()
		elif self.has_value_changed("property_type") and self.has_values():
			frappe.throw(_("The property type cannot change while work items have a value for it."))

	def unique_fieldname(self):
		base = "ep_p_" + (re.sub(r"[^a-z0-9]+", "_", (self.label or "").lower()).strip("_") or "property")[:40]
		fieldname, n = base, 1
		while frappe.db.exists("Custom Field", {"dt": "Task", "fieldname": fieldname}):
			n += 1
			fieldname = f"{base}_{n}"
		return fieldname

	def has_values(self):
		return frappe.db.has_column("Task", self.fieldname) and frappe.db.sql(
			f"select 1 from `tabTask` where ifnull(`{self.fieldname}`, '') not in ('', '0') limit 1"
		)

	def on_update(self):
		definition = {
			**FIELD_TYPES[self.property_type],
			"fieldname": self.fieldname,
			"label": self.label,
			"insert_after": "ep_sequence",
			"depends_on": f"eval:doc.type=={frappe.as_json(self.task_type)}",
			"hidden": 0,
		}
		if self.property_type == "Dropdown":
			definition["options"] = "\n" + self.options
		existing = frappe.db.get_value("Custom Field", {"dt": "Task", "fieldname": self.fieldname})
		if existing:
			field = frappe.get_doc("Custom Field", existing)
			field.update(definition)
			field.save(ignore_permissions=True)
		else:
			create_custom_field("Task", definition)

	def on_trash(self):
		# keep the column and its data; only hide the field
		frappe.db.set_value("Custom Field", {"dt": "Task", "fieldname": self.fieldname}, "hidden", 1)
		frappe.clear_cache(doctype="Task")
