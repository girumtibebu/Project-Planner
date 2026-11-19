/**
 * Task list view customisation:
 *   - Defaults group_by to Action Category
 *   - Colours the indicator dot using the Action Category's colour field
 */
frappe.listview_settings["Task"] = frappe.listview_settings["Task"] || {};

Object.assign(frappe.listview_settings["Task"], {
	// Default grouping when the list is first opened
	onload(listview) {
		if (!listview.list_renderer.group_by) {
			listview.list_renderer.group_by = "ep_action_category";
		}
	},

	get_indicator(doc) {
		const STATUS_COLOR = {
			Open: "blue",
			"Working": "yellow",
			"Pending Review": "orange",
			Overdue: "red",
			Completed: "green",
			Cancelled: "gray",
		};
		return [
			__(doc.status),
			STATUS_COLOR[doc.status] || "blue",
			"status,=," + doc.status,
		];
	},

	/**
	 * After category colour is loaded we tint the group header.
	 * frappe.listview_settings formatters run on each row; we hook
	 * the group label formatting here by overriding get_group_by_html.
	 */
	before_render() {
		// Prefetch Action Category colours into a local map
		frappe.db
			.get_list("Action Category", {
				fields: ["title", "color"],
				limit: 500,
			})
			.then((rows) => {
				window._epCategoryColors = {};
				rows.forEach((r) => {
					if (r.color) window._epCategoryColors[r.title] = r.color;
				});
			});
	},

	formatters: {
		ep_action_category(value) {
			if (!value) return "";
			const color =
				(window._epCategoryColors && window._epCategoryColors[value]) ||
				"#8F8A7E";
			return `<span style="display:inline-flex;align-items:center;gap:5px;">
				<span style="width:8px;height:8px;border-radius:999px;background:${frappe.utils.escape_html(color)};flex-shrink:0;"></span>
				${frappe.utils.escape_html(value)}
			</span>`;
		},
	},
});
