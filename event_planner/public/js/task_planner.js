frappe.ui.form.on("Task", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.project) return;
		frm.add_custom_button(__("Open in Planner"), () => {
			const project = encodeURIComponent(frm.doc.project);
			window.location.href = `/planner/${project}/items?item=${encodeURIComponent(frm.doc.name)}`;
		});
	},
});
