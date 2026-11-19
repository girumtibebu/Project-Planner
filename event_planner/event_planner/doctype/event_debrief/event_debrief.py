import frappe
from frappe.model.document import Document


class EventDebrief(Document):
    def before_save(self):
        if not (self.title or "").strip() and self.project:
            self.title = "{} — Event Debrief".format(self.project)
        # content is plain Markdown — no HTML sanitization needed
        if not self.is_new():
            self.version = (self.version or 1) + 1
