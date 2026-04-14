frappe.treeview_settings["BOQ Structure"] = {
	breadcrumb: "Construction",
	get_tree_root: false,
	filters: [
		{
			fieldname: "boq_header",
			fieldtype: "Link",
			options: "BOQ Header",
			label: __("BOQ Header"),
			reqd: true,
		},
	],
	root_label: "BOQ Structure",
	get_tree_nodes: "construction.api.boq_api.get_children",
	add_tree_node: "construction.api.boq_api.add_node",
	fields: [
		{
			fieldtype: "Data",
			fieldname: "title",
			label: __("Title"),
			reqd: true,
		},
		{
			fieldtype: "Check",
			fieldname: "is_group",
			label: __("Is Group"),
			description: __("Groups contain child nodes. Non-groups are leaf items for pricing."),
		},
	],
	ignore_fields: ["parent_structure"],
	get_label: function (node) {
		if (node.title && node.title !== node.label) {
			return node.title;
		}
		return node.title || node.label;
	},
	onload: function (treeview) {
		function get_boq_header() {
			return treeview.page.fields_dict.boq_header.get_value();
		}

		treeview.page.add_inner_button(
			__("BOQ Header"),
			function () {
				var boq = get_boq_header();
				if (boq) {
					frappe.set_route("Form", "BOQ Header", boq);
				}
			},
			__("View"),
		);

		treeview.page.add_inner_button(
			__("BOQ Items"),
			function () {
				frappe.set_route("List", "BOQ Item", {
					boq_header: get_boq_header(),
				});
			},
			__("View"),
		);
	},
};
