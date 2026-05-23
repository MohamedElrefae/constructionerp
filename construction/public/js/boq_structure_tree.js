// BOQ Structure Tree View
// Follows the standard Frappe treeview pattern (like Cost Center)

frappe.treeview_settings["BOQ Structure"] = {
	breadcrumb: "Construction",
	title: __("BOQ Structure"),
	get_tree_nodes: "construction.api.boq_api.get_children",
	add_tree_node: "construction.api.boq_api.add_node",
	filters: [
		{
			fieldname: "boq_header",
			fieldtype: "Link",
			options: "BOQ Header",
			label: __("BOQ Header"),
			reqd: 1,
			get_query: function() {
				var filters = {};
				if (window.scopeContext && window.scopeContext.current && window.scopeContext.current.project) {
					filters.project = window.scopeContext.current.project;
				} else if (window.scopeContext && window.scopeContext.current && window.scopeContext.current.company) {
					filters.company = window.scopeContext.current.company;
				}
				return { filters: filters };
			}
		},
	],
	fields: [
		{
			fieldname: "title",
			fieldtype: "Data",
			label: __("Title"),
			reqd: 1,
		},
		{
			fieldname: "is_group",
			fieldtype: "Check",
			label: __("Is Group (Section)"),
			default: "0",
		},
	],
	root_label: "BOQ Structure",
	get_tree_root: false,
	show_expand_all: true,
	get_label: function (node) {
		if (node.data && node.data.wbs_code) {
			return node.data.wbs_code + " — " + (node.data.title || node.data.value);
		}
		return node.title || node.value;
	},
	onrender: function (node) {
		if (node.data && node.data.is_group == 1) {
			$(node.parent)
				.find(".tree-label")
				.first()
				.append(' <span class="badge badge-info" style="font-size:10px;">Section</span>');
		}
	},
	onload: function(treeview) {
		// Sync with global scope context changes
		$(document).off("scope:changed.boqStructureTreePublic").on("scope:changed.boqStructureTreePublic", function() {
			if (treeview.page && treeview.page.fields_dict && treeview.page.fields_dict.boq_header) {
				var field = treeview.page.fields_dict.boq_header;
				var boq = field.get_value();
				if (boq) {
					var project = window.scopeContext && window.scopeContext.current && window.scopeContext.current.project;
					var company = window.scopeContext && window.scopeContext.current && window.scopeContext.current.company;
					
					frappe.db.get_value("BOQ Header", boq, ["project", "company"]).then(function(r) {
						if (r && r.message) {
							var match = true;
							if (project && r.message.project !== project) match = false;
							if (company && r.message.company !== company) match = false;
							
							if (!match) {
								field.set_value("").then(function() {
									field.$input.val("");
									field.$input.trigger("change");
								});
							}
						}
					});
				}
			}
		});
	},
	toolbar: [
		{
			label: __("Open"),
			click: function (node) {
				frappe.set_route("Form", "BOQ Structure", node.data.value);
			},
			btnClass: "hidden-xs",
		},
	],
	extend_toolbar: true,
};
