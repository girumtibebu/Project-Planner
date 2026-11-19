import frappe
from frappe.model.document import Document


class EventBrief(Document):
    def before_save(self):
        if not self.title and self.project:
            self.title = "{} — Production Brief".format(self.project)
        # content is plain Markdown — no HTML sanitization needed
        if not self.is_new():
            self.version = (self.version or 1) + 1
