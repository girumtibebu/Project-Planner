frappe.ui.form.on("Project", {
	refresh(frm) {
		if (frm.is_new()) return;
		const project = encodeURIComponent(frm.doc.name);
		frm.add_custom_button(__("Open in Planner"), () => {
			window.location.href = `/planner/${project}`;
		}).addClass("btn-primary");
		frm.add_custom_button(
			__("Classic planner"),
			() => window.open(`/planner-classic#/${project}/landing`, "_blank"),
			__("Planner")
		);
	},
});
