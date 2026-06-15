/* eslint-disable */
frappe.treeview_settings["BOQ Structure"] = {
	breadcrumb: "Construction",
	get_tree_root: false,
	root_label: "BOQ Structure",
	filters: [
		{
			fieldname: "scope_project",
			fieldtype: "Data",
			label: __("Project"),
		},
		{
			fieldname: "boq_header",
			fieldtype: "Link",
			options: "BOQ Header",
			label: __("Select BOQ Header"),
			placeholder: __("Choose a BOQ to view its structure..."),
			reqd: true,
			get_query: function () {
				var filters = {};
				var project = null;
				if (window.scopeContext && window.scopeContext.enabled) {
					project = window.scopeContext.getValidatedCurrentScope().project;
				} else {
					try {
						var page = cur_page && cur_page.page;
						if (page && page.fields_dict && page.fields_dict.scope_project) {
							project = page.fields_dict.scope_project.get_value();
						}
					} catch (e) {}
				}
				if (project) {
					filters.project = project;
				}
				return { filters: filters };
			},
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
		if (node.is_root) {
			return;
		}

		if (node.$tree_link) {
			var base_label =
				(node.data && (node.data.title || node.data.label || node.data.value)) ||
				node.label ||
				"";
			var item_count =
				node.data && node.data.item_count ? parseInt(node.data.item_count, 10) : 0;
			var total_contract_value =
				node.data && node.data.total_contract_value
					? flt(node.data.total_contract_value)
					: 0;
			var total_budgeted_cost =
				node.data && node.data.total_budgeted_cost
					? flt(node.data.total_budgeted_cost)
					: 0;
			var metrics = [];
			if (item_count) {
				metrics.push(item_count + " " + __("items"));
			}
			if (total_contract_value) {
				metrics.push(format_currency(total_contract_value));
			}
			if (total_budgeted_cost) {
				metrics.push(format_currency(total_budgeted_cost));
			}
			var label_html =
				'<span class="ct-boq-tree-title">' +
				$("<div>").text(base_label).html() +
				"</span>";
			if (metrics.length) {
				label_html +=
					' <span class="ct-boq-tree-meta" style="color: var(--text-muted); font-size: 11px;">(' +
					$("<div>").text(metrics.join(" · ")).html() +
					")</span>";
			}
			node.$tree_link.find(".tree-label").html(label_html);
		}
	},
	onload: function (treeview) {
		console.info("[BOQ Structure Tree] canonical script loaded");
		window.cur_tree = treeview;

		// Add CSS to head to guarantee that scope_project is completely hidden in all browsers
		if (!$("#hide-scope-project-style").length) {
			$('<style id="hide-scope-project-style">')
				.prop("type", "text/css")
				.html('.page-form [data-fieldname="scope_project"] { display: none !important; }')
				.appendTo("head");
		}

		function get_boq_header() {
			return treeview.page.fields_dict.boq_header.get_value();
		}

		function get_scope_project() {
			if (window.scopeContext && window.scopeContext.enabled) {
				return window.scopeContext.getValidatedCurrentScope().project || null;
			}
			return null;
		}

		// Sync local project filter with Scope Context (hide the filter, sync value under the hood)
		var hide_project = function () {
			let proj_field =
				treeview.page &&
				treeview.page.fields_dict &&
				treeview.page.fields_dict.scope_project;
			if (proj_field) {
				proj_field.$wrapper.hide();
				let scope_project = get_scope_project();
				if (scope_project && proj_field.get_value() !== scope_project) {
					proj_field.set_value(scope_project);
				}
			}
		};
		hide_project();
		setTimeout(hide_project, 50);
		setTimeout(hide_project, 150);
		setTimeout(hide_project, 400);
		setTimeout(hide_project, 800);
		setTimeout(hide_project, 1500);

		// Sync with global scope context changes
		$(document)
			.off("scope:changed.boqStructureTree")
			.on("scope:changed.boqStructureTree", function () {
				if (treeview.page && treeview.page.fields_dict) {
					var proj_field = treeview.page.fields_dict.scope_project;
					var boq_field = treeview.page.fields_dict.boq_header;
					var project = get_scope_project();
					var company =
						window.scopeContext &&
						window.scopeContext.enabled &&
						window.scopeContext.getValidatedCurrentScope().company;

					if (proj_field && project && proj_field.get_value() !== project) {
						proj_field.set_value(project);
					}

					var boq = boq_field ? boq_field.get_value() : null;
					if (boq && boq_field) {
						frappe.db
							.get_value("BOQ Header", boq, ["project", "company"])
							.then(function (r) {
								if (r && r.message) {
									var boq_project = r.message.project;
									var boq_company = r.message.company;
									if (project && boq_project !== project) {
										boq_field.set_value("").then(function () {
											boq_field.$input.val("");
											boq_field.$input.trigger("change");
										});
									} else if (company && boq_company !== company) {
										boq_field.set_value("").then(function () {
											boq_field.$input.val("");
											boq_field.$input.trigger("change");
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
