"""
One-time patch: rename any hand-made Customize Form fields on Project / Task
that were created before this app existed, migrating them into the app-owned
`ep_*` fieldnames so no column data is lost.

Maps are: old_fieldname -> new_fieldname.
If a field with old_fieldname exists AND the new_fieldname does NOT yet exist,
we do an SQL rename.  The new Custom Field rows are then created (or updated)
by calling install.after_install() which is idempotent.
"""

import frappe
from event_planner.install import _create_custom_fields

# Adjust these to match whatever was actually entered in Customize Form before
# the app was installed.
PROJECT_FIELD_MAP = {
    # old fieldname : new fieldname
    "event_details_tab":      "ep_event_details_tab",
    "schedule_status":        "ep_schedule_status",
    "location":               "ep_location",
    "time_schedule":          "ep_time_schedule",
    "equipment_schedule":     "ep_equipment_schedule",
    "crew_schedule":          "ep_crew_schedule",
    "vehicle_schedule":       "ep_vehicle_schedule",
    "additional_remarks":     "ep_additional_remarks",
}

TASK_FIELD_MAP = {
    "action_category": "ep_action_category",
}


def execute():
    _rename_fields("Project", PROJECT_FIELD_MAP)
    _rename_fields("Task", TASK_FIELD_MAP)
    # Re-create / update custom fields so labels/options are in sync
    _create_custom_fields()
    frappe.db.commit()


def _rename_fields(doctype: str, field_map: dict):
    table = f"tab{doctype}"
    for old, new in field_map.items():
        old_exists = frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": old})
        new_exists  = frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": new})
        if not old_exists:
            continue
        if new_exists:
            # New field already exists — just delete the old orphan row
            frappe.db.delete("Custom Field", {"dt": doctype, "fieldname": old})
            continue

        # Rename the Custom Field row
        frappe.db.sql(
            "UPDATE `tabCustom Field` SET fieldname=%s WHERE dt=%s AND fieldname=%s",
            (new, doctype, old),
        )

        # Rename the actual column in the database table if both exist
        try:
            col_info = frappe.db.sql(
                f"SHOW COLUMNS FROM `{table}` LIKE %s", (old,), as_dict=True
            )
            if col_info:
                col_type = col_info[0].get("Type", "text")
                frappe.db.sql(
                    f"ALTER TABLE `{table}` RENAME COLUMN `{old}` TO `{new}`"
                )
        except Exception:
            pass
