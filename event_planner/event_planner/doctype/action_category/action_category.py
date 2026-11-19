import frappe
from frappe.model.document import Document


class ActionCategory(Document):
    def autoname(self):
        """
        Naming rule:
        - Global preset (project IS NULL):  name = title
        - Project-scoped:                   name = title-PROJECT_NAME
        This allows "Logistics" to exist as both a global preset and
        per-project category without collision.
        """
        title = (self.title or "").strip()
        if self.project:
            self.name = f"{title}-{self.project}"
        else:
            self.name = title

    def validate(self):
        self.title = (self.title or "").strip()
        if not self.title:
            frappe.throw("Category title is required.")
