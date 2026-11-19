"""Demo brief and tech BOQs for the Coca-Cola event. Local testing only.

Run: bench --site <site> execute event_planner.planner.demo_boq.create
Safe to run again: pages are found by department, lines by item.
"""

import frappe

from event_planner.planner import parts

PROJECT = "Coca-Cola Summer Launch"

COMMERCIAL = [
	("LED screen, 30 sqm", 1, "lot", "Main stage backdrop"),
	("Sound system for 1,500 guests", 1, "lot", "Speeches and live band"),
	("Stage lighting package", 1, "lot", ""),
	("Stage 12 x 8 m with truss roof", 1, "lot", ""),
	("Power and generator", 1, "lot", "No mains power at Meskel Square"),
]

BOQS = {
	"Video": ("Booked", [
		("LED screen P3.9 outdoor, with processor", 30, "sqm", "", 30, "Booked", "2 spare panels"),
		("Media server", 1, "set", "", 1, "Booked", ""),
		("Confidence monitor 55 inch", 2, "pcs", "Downstage, for speakers", 2, "Booked", ""),
		("Camera kit for IMAG", 2, "kit", "", 1, "Partly booked", "1 kit is on the TVC shoot"),
	]),
	"Audio": ("Sent to warehouse", [
		("Line array top", 8, "pcs", "Flown, 4 a side", 0, "Requested", ""),
		("Subwoofer 18 inch", 4, "pcs", "", 2, "Partly booked", "Only 2 free, renting 2"),
		("Digital mixer 48 ch", 1, "pcs", "FOH", 0, "Requested", ""),
		("Wireless handheld mic", 6, "pcs", "Speeches and MC", 0, "Requested", ""),
		("Stage monitor", 4, "pcs", "For the band", 0, "Requested", ""),
	]),
	"Lighting": ("Draft", [
		("Moving head spot", 12, "pcs", "", 0, "Requested", ""),
		("LED wash", 16, "pcs", "", 0, "Requested", ""),
		("Lighting console", 1, "pcs", "", 0, "Requested", ""),
		("Hazer", 2, "pcs", "", 0, "Requested", ""),
	]),
	"Rigging": ("Draft", [
		("Box truss 30 cm", 48, "m", "Roof and LED frame", 0, "Requested", ""),
		("Chain hoist 1 t", 8, "pcs", "", 0, "Requested", ""),
		("Ground support tower", 4, "pcs", "", 0, "Requested", ""),
	]),
	"Power": ("Draft", [
		("Generator 200 kVA", 1, "pcs", "With fuel for 2 days", 0, "Requested", ""),
		("Distro board 63 A", 3, "pcs", "", 0, "Requested", ""),
		("Power cable 63 A, 25 m", 6, "pcs", "", 0, "Requested", ""),
	]),
}


def create():
	project = frappe.db.get_value("Project", {"project_name": PROJECT})
	if not project:
		return f"skipped: no project {PROJECT}"
	parts.set_view_parts(project, parts.VIEW_PARTS)
	brief(project)
	for department, (status, lines) in BOQS.items():
		boq(project, department, status, lines)
	# the warehouse reviewed the video BOQ, then the tech team made the screen bigger: shows as changed
	video = frappe.db.get_value("Planner Page", {"project": project, "page_kind": "BOQ", "department": "Video"})
	parts.mark_reviewed(video)
	line = frappe.get_doc("Planner BOQ Line", {"page": video, "item": BOQS["Video"][1][0][0]})
	line.qty = 36
	line.note = "Client asked for wider screen"
	line.save()
	frappe.db.commit()
	return "demo brief and BOQs created"


def brief(project):
	if "brief" in parts.enabled_parts(project):
		return
	name = parts.add_page_part(project, "brief")
	rows = "".join(f"<tr><td>{i}</td><td>{q}</td><td>{u}</td><td>{n}</td></tr>" for i, q, u, n in COMMERCIAL)
	empty = "<tr><td></td><td></td><td></td><td></td></tr>" * 3
	content = frappe.db.get_value("Planner Page", name, "content").replace(empty, rows)
	frappe.db.set_value("Planner Page", name, "content", content)


def boq(project, department, status, lines):
	key = f"boq_{department.lower()}"
	page = frappe.db.get_value("Planner Page", {"project": project, "page_kind": "BOQ", "department": department})
	if not page:
		page = parts.add_page_part(project, key)
	frappe.db.set_value("Planner Page", page, "boq_status", status)
	for i, (item, qty, unit, note, qty_booked, line_status, warehouse_note) in enumerate(lines):
		if frappe.db.exists("Planner BOQ Line", {"page": page, "item": item}):
			continue
		frappe.get_doc(
			{
				"doctype": "Planner BOQ Line",
				"page": page,
				"sort_order": i,
				"item": item,
				"qty": qty,
				"unit": unit,
				"note": note,
				"qty_booked": qty_booked,
				"line_status": line_status,
				"warehouse_note": warehouse_note,
			}
		).insert()
