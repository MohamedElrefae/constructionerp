frappe.treeview_settings["BOQ Structure"] = {
	breadcrumb: "Construction",
	get_tree_root: false,
	root_label: "BOQ Structure",
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
			label: __("Select BOQ Header"),
			placeholder: __("Choose a BOQ to view its structure..."),
			reqd: true,
			get_query: function() {
				var filters = {};
				var project = null;
				try {
					var page = cur_page && cur_page.page;
					if (page && page.fields_dict && page.fields_dict.project) {
						project = page.fields_dict.project.get_value();
					}
				} catch (e) {}
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
	onrender: function (node) {
		// Replace root node label with project name + BOQ title
		if (node.is_root) {
			var boq = node.data ? node.data.value : null;
			if (!boq || boq === "BOQ Structure") {
				var page = cur_page && cur_page.page;
				if (page && page.fields_dict && page.fields_dict.boq_header) {
					boq = page.fields_dict.boq_header.get_value();
				}
			}
			if (boq && boq !== "BOQ Structure") {
				frappe.db
					.get_value("BOQ Header", boq, ["title", "project_name"])
					.then(function (r) {
						if (r && r.message) {
							var label = r.message.title || boq;
							if (r.message.project_name) {
								label = r.message.project_name + " \u2014 " + label;
							}
							if (node.$tree_link) {
								node.$tree_link.find(".tree-label").text(label);
							}
						}
					});
			}
		}
	},
	onload: function (treeview) {
		function get_boq_header() {
			return treeview.page.fields_dict.boq_header.get_value();
		}

		function get_scope_project() {
			if (window.scopeContext && window.scopeContext.current && window.scopeContext.current.project) {
				return window.scopeContext.current.project;
			}
			try {
				var saved = localStorage.getItem("scope_context_current");
				if (saved) {
					var parsed = JSON.parse(saved);
					return parsed && parsed.project ? parsed.project : null;
				}
			} catch (e) {}
			return null;
		}

		// Sync local project filter with Scope Context (without hiding it)
		setTimeout(function() {
			let proj_field = treeview.page.fields_dict.project;
			let boq_field = treeview.page.fields_dict.boq_header;
			let scope_project = get_scope_project();
			if (proj_field) {
				if (scope_project && !proj_field.get_value()) {
					proj_field.set_value(scope_project);
				}
				// Keep BOQ Header consistent when user changes project manually
				if (!proj_field.__boq_project_bound && boq_field) {
					proj_field.__boq_project_bound = true;
					proj_field.$input.on("change", function() {
						var current_project = proj_field.get_value();
						var current_boq = boq_field.get_value();
						if (!current_boq) return;
						frappe.db.get_value("BOQ Header", current_boq, "project").then(function(r) {
							var boq_project = r && r.message ? r.message.project : null;
							if (current_project && boq_project && current_project !== boq_project) {
								boq_field.set_value("");
							}
						});
					});
				}
			}
		}, 100);

		// Sync with global scope context changes
		$(document).off("scope:changed.boqStructureTree").on("scope:changed.boqStructureTree", function() {
			if (treeview.page && treeview.page.fields_dict) {
				var proj_field = treeview.page.fields_dict.project;
				var boq_field = treeview.page.fields_dict.boq_header;
				var project = get_scope_project();
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

		var boq_from_url = frappe.route_options && frappe.route_options.boq_header;
		if (!boq_from_url) {
			boq_from_url = get_boq_header();
		}
		if (boq_from_url && treeview.page.fields_dict.boq_header) {
			setTimeout(function () {
				var field = treeview.page.fields_dict.boq_header;
				field.set_value(boq_from_url).then(function () {
					field.$input.val(boq_from_url);
					field.$input.trigger("change");
				});
			}, 300);
		}
		if (frappe.route_options) {
			delete frappe.route_options.boq_header;
		}

		treeview.page.add_inner_button(
			__("BOQ Header"),
			function () {
				var boq = get_boq_header();
				if (boq) frappe.set_route("Form", "BOQ Header", boq);
			},
			__("View"),
		);

		treeview.page.add_inner_button(
			__("BOQ Items"),
			function () {
				frappe.set_route("List", "BOQ Item", { boq_header: get_boq_header() });
			},
			__("View"),
		);

		treeview.page.add_inner_button(
			__("Excel - Full BOQ"),
			function () {
				var boq = get_boq_header();
				if (!boq) {
					frappe.msgprint(__("Please select a BOQ Header first."));
					return;
				}
				frappe.call({
					method: "construction.api.boq_api.export_boq_excel",
					args: { boq_header: boq },
					callback: function (r) {
						if (r.message && r.message.file_url) {
							window.open(r.message.file_url);
							frappe.show_alert({ message: __("BOQ exported"), indicator: "green" });
						}
					},
				});
			},
			__("Export"),
		);

		treeview.page.add_inner_button(
			__("PDF - Full BOQ"),
			function () {
				var boq = get_boq_header();
				if (!boq) {
					frappe.msgprint(__("Please select a BOQ Header first."));
					return;
				}
				frappe.call({
					method: "construction.api.boq_api.export_boq_pdf",
					args: { boq_header: boq },
					callback: function (r) {
						if (r.message && r.message.file_url) {
							window.open(r.message.file_url);
							frappe.show_alert({
								message: __("BOQ PDF exported"),
								indicator: "green",
							});
						}
					},
				});
			},
			__("Export"),
		);
	},
};
