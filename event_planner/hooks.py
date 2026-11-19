app_name = "event_planner"
app_title = "Planner"
app_publisher = "Tamirat Ayalew ( Bini )"
app_description = "Plane-style planner on ERPNext Projects, made for Eternal Media"
app_email = "binitechnology@gmail.com"
app_license = "mit"

required_apps = ["erpnext"]

# Installation / Uninstallation
after_install = "event_planner.install.after_install"
after_migrate = "event_planner.install.after_migrate"
before_uninstall = "event_planner.install.before_uninstall"

# Custom JS on desk doctypes
doctype_js = {
    "Project": "public/js/project_button.js",
    "Task": ["public/js/task_list.js", "public/js/task_planner.js"],
}

# the planner SPA: /planner/<project>/...
website_route_rules = [
    {"from_route": "/planner/<path:app_path>", "to_route": "planner"},
]

doc_events = {
	"Task": {
		"before_validate": "event_planner.planner.work_items.before_validate_task",
		"before_insert": "event_planner.planner.work_items.before_insert_task",
		"before_save": ["event_planner.task_hooks.sync_assigned_to_from_assign"],
	},
	"Project": {
		"validate": "event_planner.planner.work_items.validate_project",
		"on_update": "event_planner.planner.notify.on_project_update",
	},
}

has_permission = {
    "Planner Page": "event_planner.event_planner.doctype.planner_page.planner_page.has_permission",
    "Planner View": "event_planner.event_planner.doctype.planner_view.planner_view.has_permission",
    "Planner BOQ Line": "event_planner.event_planner.doctype.planner_boq_line.planner_boq_line.has_permission",
}

permission_query_conditions = {
    "Planner View": "event_planner.event_planner.doctype.planner_view.planner_view.get_permission_query_conditions",
}

# Fixtures: export print formats with the app
fixtures = [
    {
        "dt": "Print Format",
        "filters": [["name", "in", ["Event Brief", "Action Plan", "Event Debrief"]]],
    }
]
