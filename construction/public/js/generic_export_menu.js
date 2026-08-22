/**
 * Generic Export Menu — Global Form Enhancer
 *
 * Automatically attaches an Export (Excel / PDF / Print) dropdown to every
 * Frappe form page across the entire application (Construction + ERPNext core).
 *
 * Skip logic
 * ----------
 * If a form sets  frm.__ct_has_manual_export = true  in its own refresh
 * handler, this script will not inject a second export button, letting the
 * manual menu take precedence (e.g. BOQ Header).
 *
 * The flag lives on the frm instance (not window) so it is isolated to each
 * form load and cannot bleed when the user navigates to a different DocType.
 *
 * Settings gate
 * -------------
 * Respects frappe.boot.construction_settings.enable_global_export_menu.
 * If that flag is explicitly set to 0 / false, no generic menus are added.
 * Individual manual overrides (BOQ Header) are NOT affected by this toggle.
 *
 * Column auto-generation
 * ----------------------
 * Reads frappe.meta.get_docfields(doctype) and excludes non-exportable
 * fieldtypes (Section Break, Table, HTML, etc.) and hidden fields.
 *
 * Endpoints
 * ---------
 * construction.api.export_api.export_doctype_excel
 * construction.api.export_api.export_doctype_pdf
 *
 * Requires:
 *   - print_settings_dialog.js  (PrintSettingsDialog, ColumnConfigManager)
 *   - construction_export_menu.js (ConstructionExportMenu)
 *   Both are loaded globally before this script via hooks.py.
 */

(function () {
	"use strict";

	// ── Non-exportable fieldtypes ─────────────────────────────────────────
	var NON_EXPORTABLE = [
		"Section Break", "Column Break", "Tab Break",
		"Table", "Table MultiSelect",
		"HTML", "HTML Editor",
		"Button", "Attach", "Attach Image",
		"Signature", "Barcode", "Geolocation",
		"Fold", "Heading",
	];

	// System fields hidden by default (user can still enable in dialog)
	var SYSTEM_FIELDS_HIDDEN = [
		"owner", "modified_by", "idx",
		"parent", "parenttype", "parentfield", "docstatus",
	];

	// ── Width estimation by fieldtype ─────────────────────────────────────
	function estimate_width(fieldtype) {
		switch (fieldtype) {
			case "Small Text":
			case "Text":
			case "Text Editor":
			case "Long Text":
				return 30;
			case "Date":
			case "Datetime":
				return 12;
			case "Currency":
			case "Float":
			case "Percent":
			case "Int":
				return 10;
			case "Check":
				return 6;
			default:
				return 15; // Data, Link, Select, etc.
		}
	}

	// ── Build column descriptors from frappe.meta ─────────────────────────
	function build_column_descriptors(doctype) {
		var fields;
		try {
			fields = frappe.meta.get_docfields(doctype);
		} catch (e) {
			return [];
		}
		if (!fields || !fields.length) return [];

		var descriptors = [];
		var sort_order = 0;
		fields.forEach(function (f) {
			if (!f.fieldname) return;
			if (NON_EXPORTABLE.indexOf(f.fieldtype) !== -1) return;
			if (f.hidden) return;

			var hidden_by_default = SYSTEM_FIELDS_HIDDEN.indexOf(f.fieldname) !== -1;

			descriptors.push({
				field_key: f.fieldname,
				label: __(f.label || f.fieldname),
				default_width: estimate_width(f.fieldtype),
				default_visible: !hidden_by_default,
				default_sort_order: sort_order++,
				// Pass fieldtype through so the dialog can display it
				fieldtype: f.fieldtype,
			});
		});
		return descriptors;
	}

	// ── Permission check ─────────────────────────────────────────────────
	function can_export(doctype) {
		try {
			return frappe.model.can_export(doctype) ||
				frappe.boot.user &&
				frappe.boot.user.roles &&
				frappe.boot.user.roles.indexOf("System Manager") !== -1;
		} catch (e) {
			return false;
		}
	}

	function can_print(doctype) {
		try {
			return frappe.model.can_print(doctype);
		} catch (e) {
			return false;
		}
	}

	// ── Export callback factory ──────────────────────────────────────────
	function make_export_callback(method, doctype, docname, success_msg) {
		return function (column_config) {
			return new Promise(function (resolve, reject) {
				frappe.call({
					method: method,
					args: {
						doctype: doctype,
						docname: docname,
						column_config: JSON.stringify(column_config),
					},
					callback: function (r) {
						if (r.message && r.message.file_url) {
							window.open(r.message.file_url);
							frappe.show_alert({ message: __(success_msg), indicator: "green" }, 4);
							resolve();
						} else if (r.message && r.message.error) {
							frappe.show_alert({ message: r.message.error, indicator: "red" }, 6);
							reject(new Error(r.message.error));
						} else {
							resolve();
						}
					},
					error: function (err) {
						reject(err);
					},
				});
			});
		};
	}

	// ── Global settings check ────────────────────────────────────────────
	function is_global_export_enabled() {
		try {
			var settings = frappe.boot && frappe.boot.construction_settings;
			if (settings && settings.enable_global_export_menu === 0) {
				return false;
			}
		} catch (e) {
			// settings not available — default to enabled
		}
		return true;
	}

	// ── Attach the export menu to a form ─────────────────────────────────
	function attach_generic_export_menu(frm) {
		// 1. Global toggle
		if (!is_global_export_enabled()) return;

		// 2. Manual override guard — frm-scoped so it cannot bleed to other forms
		if (frm.__ct_has_manual_export) return;

		// 3. Skip new (unsaved) docs — nothing to export yet
		if (frm.is_new()) return;

		// 4. Permission check
		if (!can_export(frm.doctype) && !can_print(frm.doctype)) return;

		// 5. Build columns from meta
		var descriptors = build_column_descriptors(frm.doctype);

		// 6. Build export menu items
		var items = [];

		if (can_export(frm.doctype) && descriptors.length) {
			items.push({
				label: __("Excel (XLSX)"),
				icon: "fa fa-file-excel-o",
				action: function () {
					new PrintSettingsDialog({
						report_type: "Generic_" + frm.doctype + "_Excel",
						columns: descriptors,
						sample_data: [],
						export_callback: make_export_callback(
							"construction.api.export_api.export_doctype_excel",
							frm.doctype,
							frm.doc.name,
							"Excel exported successfully"
						),
					}).show();
				},
			});

			items.push({
				label: __("PDF"),
				icon: "fa fa-file-pdf-o",
				action: function () {
					new PrintSettingsDialog({
						report_type: "Generic_" + frm.doctype + "_PDF",
						columns: descriptors,
						sample_data: [],
						export_callback: make_export_callback(
							"construction.api.export_api.export_doctype_pdf",
							frm.doctype,
							frm.doc.name,
							"PDF exported successfully"
						),
					}).show();
				},
			});
		}

		if (can_print(frm.doctype)) {
			items.push({
				label: __("Print"),
				icon: "fa fa-print",
				separator_before: items.length > 0,
				action: function () {
					frappe.set_route("print", frm.doctype, frm.doc.name);
				},
			});
		}

		if (!items.length) return;

		// 7. Render using the shared ConstructionExportMenu component
		new ConstructionExportMenu(frm, items);
	}

	// ── List View Export callback helper ──────────────────────────────────
	function make_list_export_callback(method, doctype, filters, column_config) {
		return new Promise(function (resolve, reject) {
			frappe.call({
				method: method,
				args: {
					doctype: doctype,
					filters: JSON.stringify(filters),
					column_config: JSON.stringify(column_config),
				},
				callback: function (r) {
					if (r.message && r.message.file_url) {
						window.open(r.message.file_url);
						frappe.show_alert({ message: __("Export completed successfully"), indicator: "green" }, 4);
						resolve();
					} else if (r.message && r.message.error) {
						frappe.show_alert({ message: r.message.error, indicator: "red" }, 6);
						reject(new Error(r.message.error));
					} else {
						resolve();
					}
				},
				error: function (err) {
					reject(err);
				},
			});
		});
	}

	// ── Attach the export menu to a List View ────────────────────────────
	function attach_to_list_view(list_view) {
		if (!is_global_export_enabled()) return;
		if (!can_export(list_view.doctype) && !can_print(list_view.doctype)) return;

		// Skip if already attached
		if (list_view.page.custom_actions.find(".construction-export-menu").length) return;

		var descriptors = build_column_descriptors(list_view.doctype);
		var items = [];

		if (can_export(list_view.doctype) && descriptors.length) {
			items.push({
				label: __("Excel (XLSX)"),
				icon: "fa fa-file-excel-o",
				action: function () {
					new PrintSettingsDialog({
						report_type: "List_" + list_view.doctype + "_Excel",
						columns: descriptors,
						sample_data: [],
						export_callback: function (column_config) {
							return make_list_export_callback(
								"construction.api.export_api.export_doctype_list_excel",
								list_view.doctype,
								list_view.get_filters_for_args(),
								column_config
							);
						}
					}).show();
				}
			});

			items.push({
				label: __("PDF"),
				icon: "fa fa-file-pdf-o",
				action: function () {
					new PrintSettingsDialog({
						report_type: "List_" + list_view.doctype + "_PDF",
						columns: descriptors,
						sample_data: [],
						export_callback: function (column_config) {
							return make_list_export_callback(
								"construction.api.export_api.export_doctype_list_pdf",
								list_view.doctype,
								list_view.get_filters_for_args(),
								column_config
							);
						}
					}).show();
				}
			});
		}

		if (can_print(list_view.doctype)) {
			items.push({
				label: __("Print"),
				icon: "fa fa-print",
				separator_before: items.length > 0,
				action: function () {
					window.print();
				}
			});
		}

		if (!items.length) return;

		new ConstructionExportMenu(list_view, items);
	}

	// ── Attach the export menu to a Tree View ────────────────────────────
	function attach_to_tree_view(tree_view) {
		if (!is_global_export_enabled()) return;

		// Overridden pages (like BOQ Structure Tree) register their own Export menus.
		// Skip if any export menu is already present in custom actions.
		if (tree_view.page.custom_actions.find(".construction-export-menu").length) return;

		if (!can_export(tree_view.doctype) && !can_print(tree_view.doctype)) return;

		var descriptors = build_column_descriptors(tree_view.doctype);
		var items = [];

		var get_tree_filters = function () {
			var filters = {};
			if (tree_view.args && typeof tree_view.args === "object") {
				for (var k in tree_view.args) {
					if (k !== "doctype" && k !== "cmd" && k !== "method" && Object.prototype.hasOwnProperty.call(tree_view.args, k)) {
						filters[k] = tree_view.args[k];
					}
				}
			}
			return filters;
		};

		if (can_export(tree_view.doctype) && descriptors.length) {
			items.push({
				label: __("Excel (XLSX)"),
				icon: "fa fa-file-excel-o",
				action: function () {
					new PrintSettingsDialog({
						report_type: "Tree_" + tree_view.doctype + "_Excel",
						columns: descriptors,
						sample_data: [],
						export_callback: function (column_config) {
							return make_list_export_callback(
								"construction.api.export_api.export_doctype_list_excel",
								tree_view.doctype,
								get_tree_filters(),
								column_config
							);
						}
					}).show();
				}
			});

			items.push({
				label: __("PDF"),
				icon: "fa fa-file-pdf-o",
				action: function () {
					new PrintSettingsDialog({
						report_type: "Tree_" + tree_view.doctype + "_PDF",
						columns: descriptors,
						sample_data: [],
						export_callback: function (column_config) {
							return make_list_export_callback(
								"construction.api.export_api.export_doctype_list_pdf",
								tree_view.doctype,
								get_tree_filters(),
								column_config
							);
						}
					}).show();
				}
			});
		}

		if (can_print(tree_view.doctype)) {
			items.push({
				label: __("Print"),
				icon: "fa fa-print",
				separator_before: items.length > 0,
				action: function () {
					tree_view.print_tree();
				}
			});
		}

		if (!items.length) return;

		new ConstructionExportMenu(tree_view, items);
	}

	// ── Hook into Form refresh ───────────────────────────────────────────
	frappe.ui.form.on("*", {
		refresh: function (frm) {
			attach_generic_export_menu(frm);
		},
	});

	// ── Hook into ListView refresh ───────────────────────────────────────
	if (frappe.views.ListView) {
		var original_list_refresh = frappe.views.ListView.prototype.refresh;
		frappe.views.ListView.prototype.refresh = function () {
			var self = this;
			var res = original_list_refresh.apply(this, arguments);
			if (res && typeof res.then === "function") {
				return res.then(function () {
					attach_to_list_view(self);
				});
			} else {
				attach_to_list_view(self);
				return res;
			}
		};
	}

	// ── Hook into TreeView post_render ───────────────────────────────────
	if (frappe.views.TreeView) {
		var original_tree_post_render = frappe.views.TreeView.prototype.post_render;
		frappe.views.TreeView.prototype.post_render = function () {
			original_tree_post_render.apply(this, arguments);
			attach_to_tree_view(this);
		};
	}

	// ── Expose for testability ────────────────────────────────────────────
	if (typeof module !== "undefined") {
		module.exports = {
			build_column_descriptors: build_column_descriptors,
			estimate_width: estimate_width,
			NON_EXPORTABLE: NON_EXPORTABLE,
			SYSTEM_FIELDS_HIDDEN: SYSTEM_FIELDS_HIDDEN,
		};
	}
})();
