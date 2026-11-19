"""Single source of truth for all Custom Fields added to existing DocTypes."""

CUSTOM_FIELDS = {
    # ------------------------------------------------------------------
    # Project — Event Details tab (visible only when department == Events - EMC)
    # ------------------------------------------------------------------
    "Project": [
        {
            "fieldname": "ep_event_details_tab",
            "fieldtype": "Tab Break",
            "label": "Event Details",
            "insert_after": "notes",
            "depends_on": "eval:doc.department && doc.department.toLowerCase().includes('event')",
        },
        {
            "fieldname": "ep_schedule_status",
            "fieldtype": "Select",
            "label": "Schedule Status",
            "options": "Scheduled\nIn Progress\nOn Hold\nComplete\nCancelled",
            "default": "Scheduled",
            "insert_after": "ep_event_details_tab",
        },
        {
            "fieldname": "ep_location",
            "fieldtype": "Data",
            "label": "Location",
            "insert_after": "ep_schedule_status",
        },
        # ---- Time Schedule ----
        {
            "fieldname": "ep_time_sec",
            "fieldtype": "Section Break",
            "label": "Time Schedule",
            "collapsible": 1,
            "insert_after": "ep_location",
        },
        {
            "fieldname": "ep_time_schedule",
            "fieldtype": "Table",
            "label": "Time Schedule",
            "options": "Time Schedule",
            "insert_after": "ep_time_sec",
        },
        # ---- Equipment Schedule ----
        {
            "fieldname": "ep_equip_sec",
            "fieldtype": "Section Break",
            "label": "Equipment Schedule",
            "collapsible": 1,
            "insert_after": "ep_time_schedule",
        },
        {
            "fieldname": "ep_equipment_schedule",
            "fieldtype": "Table",
            "label": "Equipment Schedule",
            "options": "Equipment Schedule",
            "insert_after": "ep_equip_sec",
        },
        # ---- Crew Schedule ----
        {
            "fieldname": "ep_crew_sec",
            "fieldtype": "Section Break",
            "label": "Crew Schedule",
            "collapsible": 1,
            "insert_after": "ep_equipment_schedule",
        },
        {
            "fieldname": "ep_crew_schedule",
            "fieldtype": "Table",
            "label": "Crew Schedule",
            "options": "Crew Schedule",
            "insert_after": "ep_crew_sec",
        },
        # ---- Vehicle Schedule ----
        {
            "fieldname": "ep_veh_sec",
            "fieldtype": "Section Break",
            "label": "Vehicle Schedule",
            "collapsible": 1,
            "insert_after": "ep_crew_schedule",
        },
        {
            "fieldname": "ep_vehicle_schedule",
            "fieldtype": "Table",
            "label": "Vehicle Schedule",
            "options": "Vehicle Schedule",
            "insert_after": "ep_veh_sec",
        },
        # ---- Additional Remarks ----
        {
            "fieldname": "ep_note_sec",
            "fieldtype": "Section Break",
            "label": "Note",
            "collapsible": 1,
            "insert_after": "ep_vehicle_schedule",
        },
        {
            "fieldname": "ep_additional_remarks",
            "fieldtype": "Text Editor",
            "label": "Additional Remarks",
            "insert_after": "ep_note_sec",
        },
        # ---- Planner v2 ----
        {
            "fieldname": "ep_key",
            "fieldtype": "Data",
            "label": "Planner Key",
            "insert_after": "project_name",
            "unique": 1,
            "no_copy": 1,
            "description": "Prefix of work item IDs in the planner, e.g. EVT for EVT-12.",
        },
        {
            "fieldname": "ep_next_sequence",
            "fieldtype": "Int",
            "label": "Last Work Item Number",
            "insert_after": "ep_key",
            "read_only": 1,
            "hidden": 1,
            "no_copy": 1,
        },
        {
            "fieldname": "ep_parts",
            "fieldtype": "JSON",
            "label": "Planner Parts",
            "insert_after": "ep_next_sequence",
            "read_only": 1,
            "hidden": 1,
            "no_copy": 1,
            "description": "Parts this project uses (brief, tech BOQs, lists). Empty: not set up in the planner yet.",
        },
        {
            "fieldname": "ep_sidebar",
            "fieldtype": "JSON",
            "label": "Planner Sidebar",
            "insert_after": "ep_parts",
            "read_only": 1,
            "hidden": 1,
            "no_copy": 1,
            "description": "Sidebar order and the shared views hidden from this project.",
        },
        {
            "fieldname": "ep_notify_text",
            "fieldtype": "Long Text",
            "label": "Team Notification Text",
            "insert_after": "ep_additional_remarks",
            "read_only": 1,
            "no_copy": 1,
            "description": "At-a-glance summary sent to n8n (Discord/Telegram): status, dates, schedule, tech BOQ and the planner link.",
        },
    ],
    # ------------------------------------------------------------------
    # Task — Action Category + sort order for SPA drag-reorder
    # ------------------------------------------------------------------
    "Task": [
        {
            "fieldname": "ep_action_category",
            "fieldtype": "Link",
            "options": "Action Category",
            "label": "Action Category",
            "insert_after": "subject",
        },
        {
            "fieldname": "ep_sort_order",
            "fieldtype": "Int",
            "label": "EP Sort Order",
            "insert_after": "ep_action_category",
            "hidden": 1,
            "default": "0",
        },
        # Compatibility: many list views / prototypes request `assigned_to`; ERPNext Task stores
        # assignments in `_assign`. We mirror the first assigned user here (see hooks).
        {
            "fieldname": "assigned_to",
            "fieldtype": "Link",
            "options": "User",
            "label": "Assigned To",
            "insert_after": "ep_sort_order",
            "read_only": 1,
            "description": "Primary assignee — mirrored from Assign / _assign by Event Planner.",
        },
        # ---- Planner v2 ----
        {
            "fieldname": "ep_state",
            "fieldtype": "Link",
            "options": "Planner State",
            "label": "State",
            "insert_after": "status",
            "in_standard_filter": 1,
            "description": "Planner state. It sets Status.",
        },
        {
            "fieldname": "ep_sequence",
            "fieldtype": "Int",
            "label": "Work Item Number",
            "insert_after": "ep_state",
            "read_only": 1,
            "no_copy": 1,
        },
    ],
    "Task Type": [
        {"fieldname": "ep_icon", "fieldtype": "Data", "label": "Planner Icon", "insert_after": "description", "description": "A Lucide icon name, e.g. flag, video, truck."},
        {"fieldname": "ep_color", "fieldtype": "Color", "label": "Planner Color", "insert_after": "ep_icon"},
        {"fieldname": "ep_is_default", "fieldtype": "Check", "label": "Default Work Item Type", "insert_after": "ep_color"},
        {
            "fieldname": "ep_check_clashes",
            "fieldtype": "Check",
            "label": "Warn About Double Bookings",
            "insert_after": "ep_is_default",
            "description": "Flag assignees or vehicles booked on two timed work items of this type at once, across projects.",
        },
    ],
}

# Fieldnames that belong to this app — used in before_uninstall cleanup
PROJECT_FIELDNAMES = [f["fieldname"] for f in CUSTOM_FIELDS["Project"]]
TASK_FIELDNAMES = [f["fieldname"] for f in CUSTOM_FIELDS["Task"]]
TASK_TYPE_FIELDNAMES = [f["fieldname"] for f in CUSTOM_FIELDS["Task Type"]]
