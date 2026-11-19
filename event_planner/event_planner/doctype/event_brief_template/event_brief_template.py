import frappe
from frappe.model.document import Document


class EventBriefTemplate(Document):
    def validate(self):
        if not self.kind:
            self.kind = "brief"
        if self.is_default and self.category:
            existing = frappe.get_all(
                "Event Brief Template",
                filters={
                    "is_default": 1,
                    "category": self.category,
                    "kind": self.kind,
                    "name": ("!=", self.name),
                },
                pluck="name",
            )
            for name in existing:
                frappe.db.set_value("Event Brief Template", name, "is_default", 0)
