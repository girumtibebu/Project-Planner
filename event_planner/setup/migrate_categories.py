"""
Idempotent migration: ensure all Action Categories without a project value
remain as global presets (project = null).

Run once after migrating from the old schema:
  bench --site <site> execute event_planner.setup.migrate_categories.set_existing_categories_global
"""

import frappe


def set_existing_categories_global():
    """Set project = null on all existing Action Category records that have no project.
    This is safe to run multiple times (idempotent).
    """
    rows = frappe.get_all(
        "Action Category",
        filters=[["project", "is", "not set"]],
        fields=["name"],
    )
    count = 0
    for r in rows:
        # Ensure the project field is truly null (not empty string)
        frappe.db.set_value("Action Category", r.name, "project", None, update_modified=False)
        count += 1

    frappe.db.commit()
    print(f"[migrate_categories] Marked {count} categories as global presets (project=null).")
    return count
