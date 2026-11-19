"""
Ethio Telecom Sheraton Hotel Event — Demo Data
============================================================
Run via:
    bench --site dev.local execute event_planner.setup.demo_data.populate

Creates (skips if already present):
  · Department  — Events - EMC
  · Action Categories (5 pre-defined)
  · Event Activities (8 runsheet items)
  · Equipment Bundles (5 bundles)
  · Vehicles (5 Ethiopian-plate vehicles)
  · Demo Users (5 Ethiopian team members)
  · Project: "Ethio Telecom Sheraton Hotel Event 2025"
  · 15 Tasks with dates, categories, assignees
  · Time / Equipment / Crew / Vehicle schedule rows on the project
"""

from __future__ import annotations
import json
import frappe
from frappe.utils import add_days, getdate, now_datetime


# ── helpers ──────────────────────────────────────────────────────────────────

def _exists(doctype: str, name: str) -> bool:
    return bool(frappe.db.exists(doctype, name))


def _ensure_user(email: str, full_name: str, roles: list[str] | None = None):
    if _exists("User", email):
        return
    u = frappe.get_doc({
        "doctype":    "User",
        "email":      email,
        "first_name": full_name.split()[0],
        "last_name":  " ".join(full_name.split()[1:]),
        "full_name":  full_name,
        "send_welcome_email": 0,
        "user_type":  "System User",
        "roles": [{"role": r} for r in (roles or ["Event Planner User", "Employee"])],
    })
    try:
        u.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Demo user creation failed for {email}: {e}")


def _ensure_department(dept_name: str) -> str:
    """Create department if it doesn't exist; return the actual DocName."""
    existing = frappe.db.get_value("Department", {"department_name": dept_name}, "name")
    if existing:
        return existing
    company = frappe.db.get_single_value("Global Defaults", "default_company") or \
              frappe.db.get_value("Company", {}, "name")
    d = frappe.get_doc({"doctype": "Department", "department_name": dept_name, "company": company or ""})
    try:
        d.insert(ignore_permissions=True)
        frappe.db.commit()
        return frappe.db.get_value("Department", {"department_name": dept_name}, "name")
    except Exception as e:
        frappe.log_error(f"Department creation failed: {e}")
        return dept_name


def _ensure_action_category(name: str, title: str, color: str, sort_order: int):
    if _exists("Action Category", name):
        return
    d = frappe.get_doc({
        "doctype": "Action Category",
        "title":       title,
        "color":       color,
        "sort_order":  sort_order,
    })
    try:
        d.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Action Category creation failed for {name}: {e}")


def _ensure_event_activity(activity_name: str):
    if frappe.db.exists("Event Activity", {"activity_name": activity_name}):
        return
    d = frappe.get_doc({"doctype": "Event Activity", "activity_name": activity_name})
    try:
        d.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Event Activity creation failed for {activity_name}: {e}")
        print(f"  ✗ Event Activity failed: {activity_name} → {e}")


def _ensure_equipment_bundle(name: str, description: str):
    if _exists("Equipment Bundle", name):
        return
    d = frappe.get_doc({
        "doctype": "Equipment Bundle",
        "bundle_name": name,
        "description": description,
    })
    try:
        d.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Equipment Bundle creation failed for {name}: {e}")


def _ensure_vehicle(plate: str, make: str, model: str, color: str, fuel_type: str = "Diesel"):
    if _exists("Vehicle", plate):
        return
    v = frappe.get_doc({
        "doctype":       "Vehicle",
        "license_plate": plate,
        "make":          make,
        "model":         model,
        "color":         color,
        "fuel_type":     fuel_type,
        "last_odometer": 0,
        "uom":           "Kilometer",
    })
    try:
        v.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Vehicle creation failed for {plate}: {e}")
        print(f"  ✗ Vehicle failed: {plate} → {e}")


# ── main entry point ─────────────────────────────────────────────────────────

def populate():
    frappe.set_user("Administrator")

    # ── 1. Department ──────────────────────────────────────────────────────
    dept_name = _ensure_department("Events - EMC")
    frappe.db.commit()
    print(f"✓  Department: {dept_name}")

    # ── 2. Action Categories ───────────────────────────────────────────────
    CATEGORIES = [
        ("Pre-Production", "Pre-Production", "#2563EB", 10),
        ("Creative",       "Creative",       "#7C3AED", 20),
        ("Logistics",      "Logistics",      "#CA8A04", 30),
        ("On-Site",        "On-Site",        "#CC785C", 40),
        ("Post-Event",     "Post-Event",     "#15803D", 50),
    ]
    for name, title, color, sort_order in CATEGORIES:
        _ensure_action_category(name, title, color, sort_order)
    frappe.db.commit()
    print("✓  Action Categories (5)")

    # ── 3. Event Activities ────────────────────────────────────────────────
    ACTIVITIES = [
        "Opening Ceremony",
        "Keynote Presentation",
        "Panel Discussion",
        "Awards Ceremony",
        "Networking Lunch",
        "Site Walkthrough",
        "Technical Rehearsal",
        "Load-in",
        "Client Debrief",
        "Press Conference",
    ]
    for a in ACTIVITIES:
        _ensure_event_activity(a)
    frappe.db.commit()
    print(f"✓  Event Activities ({len(ACTIVITIES)})")

    # ── 4. Equipment Bundles ───────────────────────────────────────────────
    BUNDLES = [
        ("Sound System Package",    "Full PA system: line array, subwoofers, mixing desk, stage monitors"),
        ("LED Wall Panel Set 4x6m", "12 LED panels (600×337mm each) with controller and cabling"),
        ("Conference Lighting Kit", "Moving heads ×8, wash lights ×16, follow spots ×2, dimmer racks"),
        ("Photography Studio Set",  "Canon EOS R5 ×2, tripods, reflectors, wireless flash kit"),
        ("Stage Podium Bundle",     "Acrylic podium with gobo light, lapel mic, presentation screen 120\""),
    ]
    for bundle_name, desc in BUNDLES:
        _ensure_equipment_bundle(bundle_name, desc)
    frappe.db.commit()
    print(f"✓  Equipment Bundles ({len(BUNDLES)})")

    # ── 5. Vehicles ────────────────────────────────────────────────────────
    VEHICLES = [
        ("AA-1234 ET",  "Toyota",        "Land Cruiser 300",  "White"),
        ("AA-5678 ET",  "Isuzu",         "NPR 75L (Cargo)",   "Dark Blue"),
        ("AA-9012 ET",  "Toyota",        "HiAce",             "Silver"),
        ("AA-3456 ET",  "Mercedes-Benz", "Vito 116 CDI",      "Black"),
        ("AA-7890 ET",  "Mitsubishi",    "Fuso FK Truck",     "Yellow"),
    ]
    for plate, make, model, color in VEHICLES:
        _ensure_vehicle(plate, make, model, color)
    frappe.db.commit()
    print(f"✓  Vehicles ({len(VEHICLES)})")

    # ── 6. Demo Users ──────────────────────────────────────────────────────
    USERS = [
        ("biniyam.kassahun@demo.et",  "Biniyam Kassahun"),
        ("mikael.kebede@demo.et",     "Mikael Kebede"),
        ("tigist.chala@demo.et",      "Tigist Chala"),
        ("dawit.alemu@demo.et",       "Dawit Alemu"),
        ("hiwot.bekele@demo.et",      "Hiwot Bekele"),
    ]
    for email, full_name in USERS:
        _ensure_user(email, full_name, roles=["System Manager"])
    frappe.db.commit()
    print(f"✓  Demo Users ({len(USERS)})")

    # ── 7. Project ─────────────────────────────────────────────────────────
    PROJECT_NAME = "Ethio Telecom Sheraton Hotel Event 2025"
    if not frappe.db.exists("Project", {"project_name": PROJECT_NAME}):
        # Reference anchor: Apr 28, 2026
        BASE = getdate("2026-04-28")
        project = frappe.get_doc({
            "doctype":              "Project",
            "project_name":        PROJECT_NAME,
            "status":              "Open",
            "department":          dept_name,
            "expected_start_date": str(add_days(BASE, -14)),  # earliest task start
            "expected_end_date":   str(add_days(BASE, 12)),   # last task end + buffer
            "ep_schedule_status":  "Scheduled",
            "ep_location":         "Sheraton Addis Ababa Hotel, Taitu Street, Addis Ababa",
            "description":         (
                "Full-service corporate event for Ethio Telecom's 30th anniversary at the "
                "Sheraton Addis. 3-day program: opening ceremony, executive keynote, panel "
                "discussions, awards gala, and networking reception."
            ),
            "ep_time_schedule":    _time_schedule_rows(BASE),
            "ep_equipment_schedule": _equipment_schedule_rows(),
            "ep_crew_schedule":    _crew_schedule_rows(BASE, USERS, VEHICLES),
            "ep_vehicle_schedule": _vehicle_schedule_rows(BASE, USERS, VEHICLES),
        })
        try:
            project.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"✓  Project: {PROJECT_NAME}")
        except Exception as e:
            frappe.log_error(f"Project creation failed: {e}")
            print(f"✗  Project creation failed: {e}")
    else:
        print(f"·  Project already exists: {PROJECT_NAME}")

    # ── 8. Tasks ───────────────────────────────────────────────────────────
    _create_tasks(PROJECT_NAME, USERS)
    frappe.db.commit()
    print("✓  Tasks (15)")
    print("\n🎉  Demo data population complete.")


# ── schedule row builders ─────────────────────────────────────────────────────

def _get_activity_name(activity_name: str) -> str:
    """Resolve Event Activity name from activity_name field."""
    return frappe.db.get_value("Event Activity", {"activity_name": activity_name}, "name") or activity_name


def _time_schedule_rows(base):
    rows = [
        {"event_activity": _get_activity_name("Site Walkthrough"),     "from_datetime": f"{add_days(base, -2)} 08:00:00", "to_datetime": f"{add_days(base, -2)} 10:00:00", "location": "Sheraton Ballroom A",      "tag": "Ops",     "remark": "Full venue walkthrough with AV team"},
        {"event_activity": _get_activity_name("Technical Rehearsal"),  "from_datetime": f"{add_days(base,  0)} 14:00:00", "to_datetime": f"{add_days(base,  0)} 20:00:00", "location": "Main Stage",                "tag": "Ops",     "remark": "Cue-to-cue with all performers"},
        {"event_activity": _get_activity_name("Load-in"),              "from_datetime": f"{add_days(base,  1)} 06:00:00", "to_datetime": f"{add_days(base,  1)} 12:00:00", "location": "Loading Bay & Stage",       "tag": "Ops",     "remark": "Stage, AV, and lighting load-in"},
        {"event_activity": _get_activity_name("Opening Ceremony"),     "from_datetime": f"{add_days(base,  2)} 09:00:00", "to_datetime": f"{add_days(base,  2)} 10:30:00", "location": "Ballroom A — Main Stage",   "tag": "Program", "remark": "CEO address + ribbon cutting"},
        {"event_activity": _get_activity_name("Keynote Presentation"), "from_datetime": f"{add_days(base,  2)} 10:45:00", "to_datetime": f"{add_days(base,  2)} 12:00:00", "location": "Ballroom A — Main Stage",   "tag": "Program", "remark": "Chief Strategy Officer presentation"},
        {"event_activity": _get_activity_name("Networking Lunch"),     "from_datetime": f"{add_days(base,  2)} 13:00:00", "to_datetime": f"{add_days(base,  2)} 14:30:00", "location": "Garden Terrace",            "tag": "Break",   "remark": "Hosted by Sheraton catering"},
        {"event_activity": _get_activity_name("Panel Discussion"),     "from_datetime": f"{add_days(base,  3)} 09:00:00", "to_datetime": f"{add_days(base,  3)} 12:00:00", "location": "Ballroom B — Conference",   "tag": "Program", "remark": "Digital transformation & 5G panel"},
        {"event_activity": _get_activity_name("Awards Ceremony"),      "from_datetime": f"{add_days(base,  4)} 19:00:00", "to_datetime": f"{add_days(base,  4)} 22:30:00", "location": "Ballroom A — Gala Setup",   "tag": "Program", "remark": "Annual employee recognition awards"},
        {"event_activity": _get_activity_name("Press Conference"),     "from_datetime": f"{add_days(base,  5)} 09:00:00", "to_datetime": f"{add_days(base,  5)} 10:30:00", "location": "Media Room",                "tag": "Talent",  "remark": "Post-event media briefing"},
        {"event_activity": _get_activity_name("Client Debrief"),       "from_datetime": f"{add_days(base,  7)} 10:00:00", "to_datetime": f"{add_days(base,  7)} 12:00:00", "location": "Event Office",              "tag": "Ops",     "remark": "Lessons learned + final wrap report"},
    ]
    return rows


def _equipment_schedule_rows():
    rows = [
        {"equipment_bundle": "Sound System Package",    "quantity": 1, "status": "Reserved",   "cost": 85000},
        {"equipment_bundle": "LED Wall Panel Set 4x6m", "quantity": 1, "status": "Reserved",   "cost": 120000},
        {"equipment_bundle": "Conference Lighting Kit", "quantity": 1, "status": "In Transit", "cost": 60000},
        {"equipment_bundle": "Photography Studio Set",  "quantity": 2, "status": "Delivered",  "cost": 45000},
        {"equipment_bundle": "Stage Podium Bundle",     "quantity": 1, "status": "Reserved",   "cost": 25000},
    ]
    return rows


def _crew_schedule_rows(base, users, vehicles):
    u = {n.split("@")[0].split(".")[0]: e for e, n in [(u[0], u[1]) for u in users]}
    rows = [
        {"role": "Event Director",    "user": users[0][0], "call_time": f"{add_days(base, -2)} 07:00:00", "wrap_time": f"{add_days(base,  7)} 18:00:00"},
        {"role": "Creative Director", "user": users[1][0], "call_time": f"{add_days(base, -5)} 09:00:00", "wrap_time": f"{add_days(base,  5)} 18:00:00"},
        {"role": "Guest Relations",   "user": users[2][0], "call_time": f"{add_days(base, -1)} 08:00:00", "wrap_time": f"{add_days(base,  5)} 22:00:00"},
        {"role": "Technical Director","user": users[3][0], "call_time": f"{add_days(base,  0)} 06:00:00", "wrap_time": f"{add_days(base,  5)} 23:00:00"},
        {"role": "Logistics Manager", "user": users[4][0], "call_time": f"{add_days(base, -7)} 09:00:00", "wrap_time": f"{add_days(base,  7)} 18:00:00"},
    ]
    return rows


def _vehicle_schedule_rows(base, users, vehicles):
    plates = [v[0] for v in vehicles]
    rows = [
        {"vehicle": plates[0], "driver": users[0][0], "from_datetime": f"{add_days(base,  2)} 07:00:00", "to_datetime": f"{add_days(base,  5)} 23:00:00", "remark": "VIP shuttle — CEO & board"},
        {"vehicle": plates[1], "driver": users[3][0], "from_datetime": f"{add_days(base,  1)} 05:00:00", "to_datetime": f"{add_days(base,  1)} 14:00:00", "remark": "Equipment load-in truck"},
        {"vehicle": plates[2], "driver": users[4][0], "from_datetime": f"{add_days(base,  2)} 06:00:00", "to_datetime": f"{add_days(base,  5)} 22:00:00", "remark": "Crew van — general transport"},
        {"vehicle": plates[3], "driver": users[2][0], "from_datetime": f"{add_days(base,  2)} 07:00:00", "to_datetime": f"{add_days(base,  5)} 23:30:00", "remark": "VIP guest transport"},
        {"vehicle": plates[4], "driver": users[4][0], "from_datetime": f"{add_days(base,  5)} 08:00:00", "to_datetime": f"{add_days(base,  6)} 18:00:00", "remark": "Strike — equipment removal"},
    ]
    return rows


# ── task builder ──────────────────────────────────────────────────────────────

def _create_tasks(project_name: str, users: list):
    # Resolve actual Project name (naming series produces PROJ-XXXX)
    actual_name = frappe.db.get_value("Project", {"project_name": project_name}, "name")
    if not actual_name:
        print(f"  ✗ Could not find project by name: {project_name}")
        return
    project_name = actual_name

    BASE = getdate("2026-04-28")

    TASK_DEFS = [
        # (subject, start_offset, end_offset, category, user_idx, status)
        ("Venue contract — Sheraton Addis",              -14, -12,  "Pre-Production", 0, "Completed"),
        ("Brand brief + visual identity approval",       -12, -10,  "Creative",       1, "Completed"),
        ("Keynote deck v1 → v3 (30th anniversary)",      -10,  -3,  "Creative",       1, "Working"),
        ("Stage backdrop + modular set fabrication",      -8,  -2,  "Logistics",      4, "Working"),
        ("AV equipment — sourcing and confirmation",      -8,  -5,  "Logistics",      3, "Completed"),
        ("Media outreach + press invitations",            -10,  -1,  "Creative",       1, "Working"),
        ("VIP guest travel & accommodation",              -7,  -1,  "Logistics",      2, "Working"),
        ("Banners, signage, and branded collateral",      -6,   0,  "Creative",       1, "Working"),
        ("Technical rehearsal — cue to cue",               0,   1,  "On-Site",        3, "Open"),
        ("Load-in — stage, AV and lighting",               1,   2,  "On-Site",        3, "Open"),
        ("Day 1 — Opening ceremony + keynote",             2,   2,  "On-Site",        0, "Open"),
        ("Day 2 — Panel discussions + workshops",          3,   3,  "On-Site",        0, "Open"),
        ("Day 3 — Awards gala + closing reception",        4,   4,  "On-Site",        0, "Open"),
        ("Strike — inventory and venue clearance",         5,   6,  "Post-Event",     4, "Open"),
        ("Client debrief + wrap report",                   7,   9,  "Post-Event",     1, "Open"),
    ]

    for idx, (subject, s_off, e_off, category, u_idx, status) in enumerate(TASK_DEFS):
        if frappe.db.exists("Task", {"subject": subject, "project": actual_name}):
            continue
        task = frappe.get_doc({
            "doctype":          "Task",
            "subject":          subject,
            "project":          project_name,
            "status":           status,
            "ep_action_category": category,
            "ep_sort_order":    (idx + 1) * 10,
            "exp_start_date":   str(add_days(BASE, s_off)),
            "exp_end_date":     str(add_days(BASE, e_off)),
            "_assign":          json.dumps([users[u_idx][0]]),
            "assigned_to":      users[u_idx][0],
        })
        try:
            task.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Task creation failed for '{subject}': {e}")
            print(f"  ✗ Task failed: {subject} → {e}")
