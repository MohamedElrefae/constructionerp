// BOQ Structure Tree View
// Follows the standard Frappe treeview pattern (like Cost Center)

frappe.treeview_settings["BOQ Structure"] = {
	breadcrumb: "Construction",
	title: __("BOQ Structure"),
	get_tree_nodes: "construction.api.boq_api.get_children",
	add_tree_node: "construction.api.boq_api.add_node",
	filters: [
		{
			fieldname: "project",
			fieldtype: "Link",
			options: "Project",
			label: __("Project"),
		},
		{
			fieldname: "boq_header",
			fieldtype: "Link",
			options: "BOQ Header",
			label: __("BOQ Header"),
			reqd: 1,
			get_query: function() {
				var filters = {};
				var project = $('.page-form [data-fieldname="project"] input').val();
				if (!project && window.scopeContext && window.scopeContext.current && window.scopeContext.current.project) {
					project = window.scopeContext.current.project;
				}
				if (project) {
					filters.project = project;
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
		// Hide local project filter and sync with global Scope Context
		setTimeout(function() {
			let proj_field = treeview.page.fields_dict.project;
			if (proj_field) {
				proj_field.$wrapper.hide();
				if (window.scopeContext && window.scopeContext.current && window.scopeContext.current.project) {
					proj_field.set_value(window.scopeContext.current.project);
				}
			}
		}, 100);

		// Sync with global scope context changes
		$(document).off("scope:changed.boqStructureTreePublic").on("scope:changed.boqStructureTreePublic", function() {
			if (treeview.page && treeview.page.fields_dict) {
				var proj_field = treeview.page.fields_dict.project;
				var boq_field = treeview.page.fields_dict.boq_header;
				var project = window.scopeContext && window.scopeContext.current && window.scopeContext.current.project;
				var company = window.scopeContext && window.scopeContext.current && window.scopeContext.current.company;

				if (proj_field && project && proj_field.get_value() !== project) {
					proj_field.set_value(project);
				}

				var boq = boq_field ? boq_field.get_value() : null;
				if (boq && boq_field) {
					frappe.db.get_value("BOQ Header", boq, "project").then(function(r) {
						if (r && r.message) {
							var boq_project = r.message.project;
							if (project && boq_project !== project) {
								boq_field.set_value("").then(function() {
									boq_field.$input.val("");
									boq_field.$input.trigger("change");
								});
							} else if (company) {
								frappe.db.get_value("Project", boq_project, "company").then(function(p_res) {
									if (p_res && p_res.message && p_res.message.company !== company) {
										boq_field.set_value("").then(function() {
											boq_field.$input.val("");
											boq_field.$input.trigger("change");
										});
									}
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
