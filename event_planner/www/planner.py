import frappe
from frappe import _

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + frappe.utils.quote(frappe.request.path)
		raise frappe.Redirect
	if not frappe.has_permission("Project", "read"):
		frappe.throw(_("You do not have access to Projects"), frappe.PermissionError)
	frappe.db.commit()
	context.boot = frappe._dict(
		{
			"csrf_token": frappe.sessions.get_csrf_token(),
			"site_name": frappe.local.site,
			"socketio_port": frappe.conf.socketio_port,
			"user": frappe.session.user,
			"user_fullname": frappe.utils.get_fullname(),
			"user_image": frappe.db.get_value("User", frappe.session.user, "user_image"),
			"desk_theme": frappe.db.get_value("User", frappe.session.user, "desk_theme") or "Light",
		}
	)
	return context
