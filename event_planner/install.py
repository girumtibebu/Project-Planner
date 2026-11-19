"""after_install / before_uninstall hooks for the Event Planner app."""

import os
import subprocess
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from event_planner.custom_fields import CUSTOM_FIELDS, PROJECT_FIELDNAMES, TASK_FIELDNAMES, TASK_TYPE_FIELDNAMES

# ---------------------------------------------------------------------------
# Seed template content (Markdown)
# ---------------------------------------------------------------------------

_PRODUCTION_BRIEF_MD = """\
# Event Overview

Write a brief overview of the event — vision, theme, and purpose.

## Objectives

- Objective 1
- Objective 2
- Objective 3

## Target Audience

Describe the primary audience for this event.

## Date & Venue

- **Date:**
- **Venue:**
- **Capacity:**
- **Load-in time:**
- **Show time:**

## Programme

- **Opening:**
- **Main Programme:**
- **Closing:**

## Key Contacts

- **Event Director:**
- **Production Manager:**
- **Client Contact:**
- **On-site Coordinator:**

## AV & Technical Requirements

List any special AV or technical requirements here.

## Logistics Checklist

- [ ] Venue confirmed
- [ ] Catering arranged
- [ ] Equipment booked
- [ ] Crew briefed
- [ ] Run-of-show finalised

## Additional Notes

Any other notes, special instructions, or considerations.
"""

_MARKETING_BRIEF_MD = """\
# Campaign Overview

Summarise the marketing event — brand context and campaign goals.

## Brand Positioning

Describe where this event sits within the overall brand strategy.

## Target Segments

- **Primary:**
- **Secondary:**
- **Influencer / media:**

## Key Messages

1. Message 1
2. Message 2
3. Message 3

## Deliverables

- [ ] Event concept deck
- [ ] Social media plan
- [ ] Press release
- [ ] Photography / videography brief
- [ ] Post-event report

## Budget Overview

- **Total budget:**
- **Venue & logistics:**
- **Marketing & comms:**
- **Contingency:**

## Timeline

- **Brief sign-off:**
- **Concept approval:**
- **Event date:**
- **Post-event wrap-up:**

## Approvals

- **Client sign-off by:**
- **Creative approved by:**
"""

_CONFERENCE_BRIEF_MD = """\
# Conference Overview

Theme and objectives of the conference/summit.

## Day 1 Programme

- **09:00** — Registration & Welcome
- **10:00** — Opening Keynote
- **11:00** — Session 1
- **12:30** — Lunch
- **13:30** — Session 2
- **15:00** — Panel Discussion
- **16:30** — Networking

## Day 2 Programme

- **09:00** — Morning Keynote
- **10:00** — Workshop A
- **11:30** — Workshop B
- **12:30** — Lunch & Sponsor Showcase
- **14:00** — Closing Session
- **15:00** — End

## Speakers

- **Name** — Topic
- **Name** — Topic

## Sponsors

- **Platinum:**
- **Gold:**
- **Silver:**

## AV & Technical Requirements

- Stage configuration:
- Screen / projection:
- Microphones:
- Live streaming:

## Logistics Checklist

- [ ] Venue confirmed
- [ ] Catering arranged
- [ ] AV equipment booked
- [ ] Speaker briefing packs sent
- [ ] Registration system live
- [ ] Signage and branding ready
- [ ] On-site team briefed

## Emergency Contacts

- **Venue manager:**
- **Technical director:**
- **First aid:**
"""


_PRODUCTION_DEBRIEF_MD = """\
# Event Debrief — Summary

A short summary of how the event went: dates, scale, headline outcome.

## What Went Well

- Highlight 1
- Highlight 2
- Highlight 3

## What Didn't Go Well

- Issue 1 — what happened
- Issue 2 — what happened
- Issue 3 — what happened

## Metrics & KPIs

- **Attendance (target / actual):**
- **Budget (planned / spent):**
- **On-time delivery:**
- **Incidents reported:**
- **Client satisfaction:**

## Lessons Learned

1. Lesson 1
2. Lesson 2
3. Lesson 3

## Action Items For Next Time

- [ ] Owner — Action
- [ ] Owner — Action
- [ ] Owner — Action

## Crew & Vendor Feedback

- **Crew highlights:**
- **Crew issues:**
- **Vendors to keep:**
- **Vendors to drop:**

## Attendee & Client Feedback

Pasted survey responses, NPS scores, or qualitative quotes go here.

## Sign-off

- **Debriefed by:**
- **Date:**
"""

_MARKETING_DEBRIEF_MD = """\
# Marketing Event Debrief — Summary

Quick summary of the campaign / activation outcome.

## Reach & Engagement

- **Total impressions:**
- **Engagement rate:**
- **Earned media value:**
- **Top-performing channel:**
- **Press mentions:**

## What Worked

- Win 1
- Win 2
- Win 3

## What Didn't Work

- Miss 1
- Miss 2
- Miss 3

## Brand & Creative Review

How well the activation reflected the brand. Anything off-brand to flag.

## Audience Feedback

Survey insights, comments from the floor, social listening highlights.

## Budget Review

- **Planned vs. spent:**
- **Largest variance:**
- **ROI estimate:**

## Lessons Learned

1. Lesson 1
2. Lesson 2
3. Lesson 3

## Action Items

- [ ] Owner — Action
- [ ] Owner — Action

## Sign-off

- **Marketing lead:**
- **Date:**
"""

_CONFERENCE_DEBRIEF_MD = """\
# Conference Debrief — Summary

Headline outcome of the conference / summit.

## Attendance & Reach

- **Registered:**
- **Showed up:**
- **No-show rate:**
- **Online viewers:**

## Programme Review

- **Best-rated session:**
- **Worst-rated session:**
- **Speaker highlights:**
- **Speaker issues:**

## Sponsor & Partner Outcomes

- **Sponsor satisfaction:**
- **Renewals expected:**
- **Leads generated:**

## Operational Performance

- **Registration flow:**
- **AV / streaming:**
- **Catering:**
- **Wayfinding & signage:**
- **On-site team performance:**

## Issues & Incidents

- Issue 1 — resolution
- Issue 2 — resolution

## Lessons Learned

1. Lesson 1
2. Lesson 2
3. Lesson 3

## Action Items For Next Edition

- [ ] Owner — Action
- [ ] Owner — Action
- [ ] Owner — Action

## Sign-off

- **Conference director:**
- **Date:**
"""


def after_install():
    """Run after `bench install-app event_planner`."""
    _create_custom_fields()
    seed_default_templates()
    _build_frontend()
    frappe.db.commit()


def _build_frontend():
    """Install npm dependencies and build the Vue SPA if not already built."""
    app_path = os.path.dirname(os.path.dirname(__file__))
    frontend_dir = os.path.join(app_path, "frontend")
    out_dir = os.path.join(os.path.dirname(__file__), "public", "planner", "assets")

    if not os.path.isdir(frontend_dir):
        return

    if os.path.isdir(out_dir):
        return  # already built

    try:
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True, timeout=300)
        subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True, timeout=120)
        frappe.msgprint("Event Planner: frontend assets built successfully.")
    except Exception as e:
        frappe.log_error(str(e), "Event Planner: frontend build failed")
        frappe.msgprint(
            f"Event Planner: could not build frontend automatically ({e}). "
            "Run 'npm install && npm run build' inside apps/event_planner/frontend/ manually.",
            alert=True,
        )


def before_uninstall():
    """Run before `bench uninstall-app event_planner`."""
    _remove_custom_fields()
    _remove_seeded_templates()
    frappe.db.commit()


def after_migrate():
    """Re-apply ``CUSTOM_FIELDS`` on every migrate (safe with ``update=True``).

    ``after_install`` runs only once. When we add fields (e.g. Task ``assigned_to``)
    after the app is already installed, migrate must recreate them — this hook does that.

    Also runs the template-kind backfill so existing sites self-tag pre-existing
    Event Brief Templates as ``kind='brief'`` after the new field is added,
    and seeds any missing default templates (e.g. the new debrief seeds).
    """
    _create_custom_fields()
    backfill_template_kind()
    seed_default_templates()
    from event_planner.planner import lists, parts

    lists.ensure()  # list types, properties and template views; adds only what is missing
    parts.ensure_brief_template()
    parts.ensure_starter_templates()
    frappe.db.commit()


# ---------------------------------------------------------------------------
# Custom fields
# ---------------------------------------------------------------------------

def _create_custom_fields():
    """Create (or update) all custom fields owned by this app."""
    create_custom_fields(CUSTOM_FIELDS, update=True)
    # the planner's activity feed shows Task field changes, which needs Version records
    if not frappe.get_meta("Task").track_changes:
        from frappe.custom.doctype.property_setter.property_setter import make_property_setter

        make_property_setter("Task", None, "track_changes", 1, "Check", for_doctype=True, validate_fields_for_doctype=False)


def _remove_custom_fields():
    """Delete the custom fields this app added to Project and Task."""
    for fieldname in PROJECT_FIELDNAMES:
        frappe.db.delete("Custom Field", {"dt": "Project", "fieldname": fieldname})
    for fieldname in TASK_FIELDNAMES:
        frappe.db.delete("Custom Field", {"dt": "Task", "fieldname": fieldname})
    for fieldname in TASK_TYPE_FIELDNAMES:
        frappe.db.delete("Custom Field", {"dt": "Task Type", "fieldname": fieldname})


# ---------------------------------------------------------------------------
# Starter Event Brief Templates
# ---------------------------------------------------------------------------

SEED_TEMPLATES = [
    {
        "template_name": "Production Brief",
        "kind": "brief",
        "category": "Production",
        "description": "A comprehensive production brief with objectives, audience, venue details, programme, and a logistics checklist.",
        "is_default": 1,
        "content": _PRODUCTION_BRIEF_MD,
    },
    {
        "template_name": "Marketing Event Brief",
        "kind": "brief",
        "category": "Marketing",
        "description": "Marketing-focused brief covering brand positioning, target segments, campaign goals, and activation checklist.",
        "is_default": 1,
        "content": _MARKETING_BRIEF_MD,
    },
    {
        "template_name": "Conference Brief",
        "kind": "brief",
        "category": "Conference",
        "description": "Conference/summit brief covering programme, speakers, sponsors, logistics checklist, and AV requirements.",
        "is_default": 1,
        "content": _CONFERENCE_BRIEF_MD,
    },
    {
        "template_name": "Production Debrief",
        "kind": "debrief",
        "category": "Production",
        "description": "Post-event debrief: highlights, issues, metrics, lessons learned, and action items for production events.",
        "is_default": 1,
        "content": _PRODUCTION_DEBRIEF_MD,
    },
    {
        "template_name": "Marketing Event Debrief",
        "kind": "debrief",
        "category": "Marketing",
        "description": "Marketing debrief: reach, engagement, brand review, budget vs. spend, audience feedback, and lessons learned.",
        "is_default": 1,
        "content": _MARKETING_DEBRIEF_MD,
    },
    {
        "template_name": "Conference Debrief",
        "kind": "debrief",
        "category": "Conference",
        "description": "Conference debrief: attendance, programme review, sponsor outcomes, operational performance, and action items.",
        "is_default": 1,
        "content": _CONFERENCE_DEBRIEF_MD,
    },
]


def seed_default_templates():
    """Insert starter Event Brief Templates (Markdown) if they don't already exist."""
    for tpl in SEED_TEMPLATES:
        if frappe.db.exists("Event Brief Template", tpl["template_name"]):
            continue

        doc = frappe.get_doc(
            {
                "doctype": "Event Brief Template",
                "template_name": tpl["template_name"],
                "kind": tpl.get("kind", "brief"),
                "category": tpl["category"],
                "description": tpl["description"],
                "is_default": tpl["is_default"],
                "is_active": 1,
                "seeded": 1,
                "content": tpl["content"],
            }
        )
        doc.insert(ignore_permissions=True)


def backfill_template_kind():
    """Set ``kind='brief'`` on any pre-existing Event Brief Template rows where kind is NULL/empty.

    Idempotent: safe to run on every migrate.
    """
    if not frappe.db.has_column("Event Brief Template", "kind"):
        return  # Migration hasn't run yet

    rows = frappe.db.sql(
        """
        SELECT name FROM `tabEvent Brief Template`
        WHERE kind IS NULL OR kind = ''
        """,
        as_dict=True,
    )
    for row in rows:
        frappe.db.set_value(
            "Event Brief Template", row["name"], "kind", "brief", update_modified=False
        )


def _remove_seeded_templates():
    """Remove only the auto-seeded templates (seeded=1) on uninstall."""
    seeded = frappe.get_all("Event Brief Template", filters={"seeded": 1}, pluck="name")
    for name in seeded:
        frappe.delete_doc("Event Brief Template", name, ignore_permissions=True, force=True)
