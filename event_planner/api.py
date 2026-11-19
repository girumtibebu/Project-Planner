"""
Whitelisted API endpoints consumed by the SPA.
All read-path methods use frappe.get_all / frappe.db;
write-path methods use frappe.get_doc + doc.save() so hooks fire.
"""

import frappe
from frappe import _
from frappe.utils import time_diff_in_seconds, now_datetime


def _require_project(project, ptype="write"):
	"""The old write paths below bypass DocType permissions, so check the project first."""
	frappe.has_permission("Project", ptype, project, throw=True)


def _category_project(name):
	project = frappe.db.get_value("Action Category", name, "project")
	_require_project(project)
	return project


@frappe.whitelist(methods=["GET"])
def get_planner_csrf_token():
	"""Expose CSRF token for the Event Planner SPA (same-origin session cookie required)."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.AuthenticationError)
	return frappe.sessions.get_csrf_token()


# ── Landing ───────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_landing_summary(project):
    """Return aggregated stats for the Landing page."""
    # Tasks
    task_counts = frappe.get_all(
        "Task",
        filters={"project": project},
        fields=["status", "count(*) as cnt"],
        group_by="status",
    )
    total = sum(r.cnt for r in task_counts)
    done  = next((r.cnt for r in task_counts if r.status in ("Completed",)), 0)
    open_ = next((r.cnt for r in task_counts if r.status in ("Open", "Working")), 0)

    # Project doc for dates
    proj = frappe.db.get_value(
        "Project",
        project,
        ["expected_end_date", "ep_time_schedule", "ep_equipment_schedule",
         "ep_crew_schedule", "ep_vehicle_schedule"],
        as_dict=True,
    ) or {}

    # Equipment / crew / vehicle counts
    equipment_lines = frappe.db.count("Equipment Schedule", {"parenttype": "Project", "parent": project})
    equipment_delivered = frappe.db.count(
        "Equipment Schedule", {"parenttype": "Project", "parent": project, "status": "Delivered"}
    )
    crew_members = frappe.db.count("Crew Schedule", {"parenttype": "Project", "parent": project})
    vehicle_assignments = frappe.db.count("Vehicle Schedule", {"parenttype": "Project", "parent": project})

    # Days remaining
    days_remaining = None
    if proj.get("expected_end_date"):
        import datetime
        delta = proj["expected_end_date"] - datetime.date.today()
        days_remaining = delta.days

    # Milestones: tasks with is_milestone=1 (ERPNext Task field)
    milestones = []
    try:
        ms_tasks = frappe.get_all(
            "Task",
            filters={"project": project, "is_milestone": 1},
            fields=["name", "subject", "exp_end_date", "status"],
            order_by="exp_end_date asc",
        )
        milestones = [
            {
                "label": t.subject,
                "date": str(t.exp_end_date) if t.exp_end_date else "",
                "done": t.status == "Completed",
            }
            for t in ms_tasks
        ]
    except Exception:
        pass

    return {
        "tasks_total": total,
        "tasks_open": open_,
        "tasks_done": done,
        "days_remaining": days_remaining,
        "equipment_lines": equipment_lines,
        "equipment_delivered": equipment_delivered,
        "crew_members": crew_members,
        "vehicle_assignments": vehicle_assignments,
        "milestones": milestones,
    }


# ── Recent Activity ───────────────────────────────────────────────────────────

@frappe.whitelist()
def get_recent_activity(project, limit=20):
    """Return a merged list of Comments and Versions for the project."""
    rows = []

    # Comments on the Project doc
    try:
        comments = frappe.get_all(
            "Comment",
            filters={"reference_doctype": "Project", "reference_name": project},
            fields=["owner", "comment_type", "content", "creation"],
            order_by="creation desc",
            limit=limit,
        )
        for c in comments:
            rows.append({
                "type": "comment",
                "owner": c.owner,
                "content": c.content or c.comment_type,
                "when": _relative_time(c.creation),
            })
    except Exception:
        pass

    # Versions (Activity log)
    try:
        versions = frappe.get_all(
            "Version",
            filters={"ref_doctype": "Project", "docname": project},
            fields=["owner", "creation", "data"],
            order_by="creation desc",
            limit=limit,
        )
        import json
        for v in versions:
            try:
                data = json.loads(v.data)
                changed = list(data.get("changed", {}).keys())[:2]
                label = "updated " + ", ".join(changed) if changed else "made a change"
            except Exception:
                label = "made a change"
            rows.append({
                "type": "task",
                "owner": v.owner,
                "content": label,
                "when": _relative_time(v.creation),
            })
    except Exception:
        pass

    rows.sort(key=lambda r: r.get("when_ts", 0), reverse=True)
    return rows[:limit]


def _relative_time(creation) -> str:
    from frappe.utils import get_datetime
    import time
    diff = time.time() - get_datetime(creation).timestamp()
    if diff < 60:
        return "just now"
    if diff < 3600:
        return f"{int(diff//60)} min ago"
    if diff < 86400:
        return f"{int(diff//3600)} hr ago"
    return f"{int(diff//86400)} days ago"


# ── Action Plan ───────────────────────────────────────────────────────────────

@frappe.whitelist()
def reorder_tasks_in_category(project, category, ordered_names):
    """Update ep_sort_order for a list of Task names within a category."""
    _require_project(project)
    if isinstance(ordered_names, str):
        import json
        ordered_names = json.loads(ordered_names)
    for i, name in enumerate(ordered_names):
        frappe.has_permission("Task", "write", name, throw=True)
        frappe.db.set_value("Task", name, {"ep_sort_order": i, "ep_action_category": category or None})
    frappe.db.commit()
    return {"ok": True}


# ── Event Brief ───────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_brief_from_template(project, template=None):
    """
    Create an Event Brief for this project, optionally cloning content
    from a named Event Brief Template (or another Event Brief if `template`
    looks like an EBR-* name).
    Returns the created/existing Event Brief as a dict.
    """
    _require_project(project)
    # Idempotent: return existing if already created
    existing = frappe.db.get_value(
        "Event Brief", {"project": project}, ["name", "project", "title", "content", "content_json", "version", "modified", "modified_by", "template"],
        as_dict=True,
    )
    if existing:
        return existing

    content      = ""
    content_json = ""
    tpl_name     = None

    if template:
        if frappe.db.exists("Event Brief Template", template):
            tpl = frappe.get_doc("Event Brief Template", template)
            # Reject templates intended for the Debrief gallery
            if (tpl.kind or "brief") != "brief":
                frappe.throw(_("Template '{0}' is a {1} template, not a brief template.").format(
                    tpl.template_name, tpl.kind))
            content      = tpl.content or ""
            content_json = tpl.content_json or ""
            tpl_name     = tpl.name
        elif frappe.db.exists("Event Brief", template):
            # "Start from previous brief" — clone another brief
            src = frappe.get_doc("Event Brief", template)
            content      = src.content or ""
            content_json = src.content_json or ""
        else:
            # Try by template_name field, scoped to brief-kind templates
            tpl_row = frappe.db.get_value(
                "Event Brief Template",
                {"template_name": template, "kind": "brief"},
                ["name", "content", "content_json"], as_dict=True,
            )
            if tpl_row:
                content      = tpl_row.content or ""
                content_json = tpl_row.content_json or ""
                tpl_name     = tpl_row.name

    doc = frappe.get_doc({
        "doctype": "Event Brief",
        "project": project,
        "title": f"{project} — Production Brief",
        "template": tpl_name,
        "content": content,
        "content_json": content_json,
        "version": 1,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.as_dict()


# ── Event Debrief ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_debrief_from_template(project, template=None):
    """
    Create an Event Debrief for this project, optionally cloning content
    from a named Event Brief Template (kind=debrief) or another Event Debrief.
    Returns the created/existing Event Debrief as a dict.
    Idempotent: returns the existing debrief if one already exists for this project.
    """
    _require_project(project)
    existing = frappe.db.get_value(
        "Event Debrief", {"project": project},
        ["name", "project", "title", "content", "content_json", "version", "modified", "modified_by", "template"],
        as_dict=True,
    )
    if existing:
        return existing

    content      = ""
    content_json = ""
    tpl_name     = None

    if template:
        if frappe.db.exists("Event Brief Template", template):
            tpl = frappe.get_doc("Event Brief Template", template)
            if (tpl.kind or "brief") != "debrief":
                frappe.throw(_("Template '{0}' is a {1} template, not a debrief template.").format(
                    tpl.template_name, tpl.kind))
            content      = tpl.content or ""
            content_json = tpl.content_json or ""
            tpl_name     = tpl.name
        elif frappe.db.exists("Event Debrief", template):
            # "Start from previous debrief" — clone another debrief
            src = frappe.get_doc("Event Debrief", template)
            content      = src.content or ""
            content_json = src.content_json or ""
        else:
            tpl_row = frappe.db.get_value(
                "Event Brief Template",
                {"template_name": template, "kind": "debrief"},
                ["name", "content", "content_json"], as_dict=True,
            )
            if tpl_row:
                content      = tpl_row.content or ""
                content_json = tpl_row.content_json or ""
                tpl_name     = tpl_row.name

    doc = frappe.get_doc({
        "doctype": "Event Debrief",
        "project": project,
        "title": f"{project} — Event Debrief",
        "template": tpl_name,
        "content": content,
        "content_json": content_json,
        "version": 1,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.as_dict()


# ── Activity log & document meta ─────────────────────────────────────────────

@frappe.whitelist()
def get_doc_meta(doctype, name):
    """Return creation/modification metadata for any document."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"), frappe.AuthenticationError)
    row = frappe.db.get_value(
        doctype, name,
        ["creation", "owner", "modified", "modified_by"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_(f"{doctype} {name} not found"))

    def _full_name(user):
        if not user:
            return user
        return frappe.db.get_value("User", user, "full_name") or user

    return {
        "creation": str(row.creation),
        "owner": row.owner,
        "owner_full_name": _full_name(row.owner),
        "modified": str(row.modified),
        "modified_by": row.modified_by,
        "modified_by_full_name": _full_name(row.modified_by),
    }


@frappe.whitelist()
def get_activity_log(doctype, name, limit=50):
    """
    Return a merged, time-sorted activity feed for any document.
    Merges: Version (field changes), Comment (comments / mentions), ToDo (assignments).
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"), frappe.AuthenticationError)

    limit = int(limit)
    import json
    from frappe.utils import get_datetime
    rows = []

    # ── Versions (field change history) ───────────────────────────────────
    try:
        versions = frappe.get_all(
            "Version",
            filters={"ref_doctype": doctype, "docname": name},
            fields=["name", "owner", "creation", "data"],
            order_by="creation desc",
            limit=limit,
        )
        for v in versions:
            try:
                data = json.loads(v.data or "{}")
                changed = data.get("changed", [])
                # changed is a list of [field, old, new]
                if isinstance(changed, list):
                    labels = [item[0] for item in changed if isinstance(item, list)]
                elif isinstance(changed, dict):
                    labels = list(changed.keys())
                else:
                    labels = []
                summary = "updated " + ", ".join(labels[:3]) if labels else "made a change"
                diff = changed[:5] if changed else []
            except Exception:
                summary, diff = "made a change", []
            rows.append({
                "id": f"v:{v.name}",
                "type": "version",
                "owner": v.owner,
                "owner_full_name": frappe.db.get_value("User", v.owner, "full_name") or v.owner,
                "content": summary,
                "diff": diff,
                "creation": str(v.creation),
                "ts": get_datetime(v.creation).timestamp(),
            })
    except Exception:
        pass

    # ── Comments ───────────────────────────────────────────────────────────
    try:
        comments = frappe.get_all(
            "Comment",
            filters={"reference_doctype": doctype, "reference_name": name},
            fields=["name", "owner", "creation", "comment_type", "content"],
            order_by="creation desc",
            limit=limit,
        )
        for c in comments:
            rows.append({
                "id": f"c:{c.name}",
                "type": "comment",
                "comment_type": c.comment_type or "Comment",
                "owner": c.owner,
                "owner_full_name": frappe.db.get_value("User", c.owner, "full_name") or c.owner,
                "content": c.content or "",
                "diff": [],
                "creation": str(c.creation),
                "ts": get_datetime(c.creation).timestamp(),
            })
    except Exception:
        pass

    # ── ToDo (assignments) ─────────────────────────────────────────────────
    try:
        todos = frappe.get_all(
            "ToDo",
            filters={"reference_type": doctype, "reference_name": name},
            fields=["name", "owner", "creation", "status", "allocated_to", "description"],
            order_by="creation desc",
            limit=limit,
        )
        for t in todos:
            assignee = t.allocated_to or t.owner
            fn = frappe.db.get_value("User", assignee, "full_name") or assignee
            verb = "closed task" if t.status == "Closed" else f"assigned to {fn}"
            rows.append({
                "id": f"t:{t.name}",
                "type": "todo",
                "owner": t.owner,
                "owner_full_name": frappe.db.get_value("User", t.owner, "full_name") or t.owner,
                "content": verb,
                "diff": [],
                "creation": str(t.creation),
                "ts": get_datetime(t.creation).timestamp(),
            })
    except Exception:
        pass

    rows.sort(key=lambda r: r["ts"], reverse=True)
    return rows[:limit]


# ── Task hierarchy ────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_tasks_with_hierarchy(project):
    """
    Return all tasks for a project as a flat list with `depth` and `child_count`
    pre-computed so the frontend can render collapsible sub-task trees.
    Also enriches each task with `category_color` from Action Category.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"), frappe.AuthenticationError)

    all_tasks = frappe.get_all(
        "Task",
        filters={"project": project},
        fields=[
            "name", "subject", "status", "priority",
            "_assign", "assigned_to",
            "exp_start_date", "exp_end_date",
            "ep_action_category", "ep_sort_order",
            "parent_task", "description",
        ],
        order_by="ep_sort_order asc, creation asc",
        limit=1000,
    )

    # Index by name
    by_name = {t.name: t for t in all_tasks}

    # Compute child_count for each task
    child_count = {t.name: 0 for t in all_tasks}
    for t in all_tasks:
        if t.get("parent_task") and t.parent_task in child_count:
            child_count[t.parent_task] += 1

    # Compute depth via BFS (guard against cycles)
    depth = {t.name: 0 for t in all_tasks}
    for t in all_tasks:
        p = t.get("parent_task")
        visited = set()
        while p and p in by_name and p not in visited:
            depth[t.name] += 1
            visited.add(p)
            p = by_name[p].get("parent_task")

    # Fetch category colors
    cat_names = list({t.ep_action_category for t in all_tasks if t.ep_action_category})
    cat_colors: dict = {}
    if cat_names:
        cats = frappe.get_all(
            "Action Category",
            filters=[["name", "in", cat_names]],
            fields=["name", "color"],
        )
        cat_colors = {c.name: (c.color or "") for c in cats}

    # Build output
    result = []
    for t in all_tasks:
        d = dict(t)
        d["depth"]          = depth.get(t.name, 0)
        d["child_count"]    = child_count.get(t.name, 0)
        d["category_color"] = cat_colors.get(t.ep_action_category, "")
        d["exp_start_date"] = str(t.exp_start_date) if t.exp_start_date else None
        d["exp_end_date"]   = str(t.exp_end_date)   if t.exp_end_date   else None
        result.append(d)

    return result


# ── Per-project Action Categories ─────────────────────────────────────────────

@frappe.whitelist()
def list_categories(project):
    """
    Return categories for this project merged with global presets.
    Project-specific categories come first (sorted by sort_order), then globals.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"), frappe.AuthenticationError)

    project_cats = frappe.get_all(
        "Action Category",
        filters={"project": project},
        fields=["name", "title", "color", "sort_order", "project"],
        order_by="sort_order asc",
    )
    global_cats = frappe.get_all(
        "Action Category",
        filters=[["project", "is", "not set"]],
        fields=["name", "title", "color", "sort_order", "project"],
        order_by="sort_order asc",
    )

    # Count tasks per category for this project (use raw SQL to avoid QBuilder
    # rejecting aggregate functions expressed as strings)
    task_counts_raw = frappe.db.sql(
        """
        SELECT ep_action_category, COUNT(*) AS cnt
        FROM `tabTask`
        WHERE project = %s AND ep_action_category IS NOT NULL
        GROUP BY ep_action_category
        """,
        (project,),
        as_dict=True,
    )
    task_counts = {r.ep_action_category: r.cnt for r in task_counts_raw}

    result = []
    for cat in project_cats:
        cat["task_count"] = task_counts.get(cat.name, 0)
        cat["is_global"] = False
        result.append(cat)
    for cat in global_cats:
        cat["task_count"] = task_counts.get(cat.name, 0)
        cat["is_global"] = True
        result.append(cat)

    return result


@frappe.whitelist()
def create_category(project, title, color=None, sort_order=0):
    """Create a new project-scoped Action Category."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"), frappe.AuthenticationError)
    _require_project(project)
    title = (title or "").strip()
    if not title:
        frappe.throw(_("Category title is required."))
    doc = frappe.get_doc({
        "doctype": "Action Category",
        "title": title,
        "project": project,
        "color": color or None,
        "sort_order": int(sort_order),
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.as_dict()


@frappe.whitelist()
def update_category(name, title=None, color=None, sort_order=None):
    """Update title, color, or sort_order on an Action Category."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"), frappe.AuthenticationError)
    _category_project(name)
    doc = frappe.get_doc("Action Category", name)
    if title is not None:
        doc.title = (title or "").strip()
    if color is not None:
        doc.color = color
    if sort_order is not None:
        doc.sort_order = int(sort_order)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return doc.as_dict()


@frappe.whitelist()
def delete_category(name):
    """
    Delete an Action Category.
    All Tasks referencing this category are reassigned to null (Uncategorised).
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"), frappe.AuthenticationError)

    _category_project(name)
    # Reassign tasks safely before deletion
    affected = frappe.get_all(
        "Task",
        filters={"ep_action_category": name},
        fields=["name"],
    )
    for t in affected:
        frappe.db.set_value("Task", t.name, "ep_action_category", None, update_modified=False)

    frappe.delete_doc("Action Category", name, ignore_permissions=True, force=True)
    frappe.db.commit()
    return {"ok": True, "reassigned": len(affected)}


@frappe.whitelist()
def reorder_categories(project, ordered_names):
    """Bulk-update sort_order for an ordered list of category names."""
    _require_project(project)
    if isinstance(ordered_names, str):
        import json
        ordered_names = json.loads(ordered_names)
    for i, name in enumerate(ordered_names):
        if frappe.db.get_value("Action Category", name, "project") != project:
            frappe.throw(_("Category {0} is not in project {1}").format(name, project))
        frappe.db.set_value("Action Category", name, "sort_order", i, update_modified=False)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def save_brief_as_template(brief, template_name, category="Production", description=""):
    """Snapshot the current Event Brief into a new Event Brief Template (kind=brief)."""
    b = frappe.get_doc("Event Brief", brief)
    b.check_permission("read")
    frappe.has_permission("Event Brief Template", "create", throw=True)

    tpl = frappe.get_doc({
        "doctype": "Event Brief Template",
        "template_name": template_name,
        "kind": "brief",
        "category": category,
        "description": description,
        "content": b.content,
        "content_json": b.content_json,
        "is_active": 1,
        "seeded": 0,
    })
    tpl.insert(ignore_permissions=True)
    frappe.db.commit()
    return tpl.as_dict()


@frappe.whitelist()
def save_debrief_as_template(debrief, template_name, category="Production", description=""):
    """Snapshot the current Event Debrief into a new Event Brief Template (kind=debrief)."""
    d = frappe.get_doc("Event Debrief", debrief)
    d.check_permission("read")
    frappe.has_permission("Event Brief Template", "create", throw=True)

    tpl = frappe.get_doc({
        "doctype": "Event Brief Template",
        "template_name": template_name,
        "kind": "debrief",
        "category": category,
        "description": description,
        "content": d.content,
        "content_json": d.content_json,
        "is_active": 1,
        "seeded": 0,
    })
    tpl.insert(ignore_permissions=True)
    frappe.db.commit()
    return tpl.as_dict()
