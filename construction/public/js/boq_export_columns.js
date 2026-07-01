/**
 * BOQ Export Column Definitions — Shared Module
 *
 * Single source of truth for BOQ_FULL_COLUMNS and BOQ_HEADER_COLUMNS.
 * Referenced by boq_header.js, boq_structure.js, boq_structure_tree.js.
 *
 * Exported as window.BOQ_EXPORT_COLUMNS.  Functions are used instead of plain
 * arrays because column labels call __() (Frappe's translation helper) which
 * must be invoked at runtime, not at module load time.
 *
 * Usage:
 *   var BOQ_FULL_COLUMNS   = window.BOQ_EXPORT_COLUMNS.full();
 *   var BOQ_HEADER_COLUMNS = window.BOQ_EXPORT_COLUMNS.header();
 */

(function () {
	"use strict";

	window.BOQ_EXPORT_COLUMNS = {

		/**
		 * Full BOQ structure columns (wbs_code … file_ref).
		 * Used for Full BOQ Excel / PDF exports from BOQ Header, BOQ Structure form,
		 * and BOQ Structure Tree.
		 *
		 * @returns {ColumnDescriptor[]}
		 */
		full: function () {
			return [
				{ field_key: "wbs_code",            label: __("WBS Code"),    default_width: 12, default_visible: true,  default_sort_order: 0 },
				{ field_key: "title",               label: __("Title"),       default_width: 30, default_visible: true,  default_sort_order: 1 },
				{ field_key: "type",                label: __("Type"),        default_width: 6,  default_visible: true,  default_sort_order: 2 },
				{ field_key: "unit",                label: __("Unit"),        default_width: 5,  default_visible: true,  default_sort_order: 3 },
				{ field_key: "quantity",            label: __("Quantity"),    default_width: 8,  default_visible: true,  default_sort_order: 4 },
				{ field_key: "contract_unit_price", label: __("Unit Price"),  default_width: 10, default_visible: true,  default_sort_order: 5 },
				{ field_key: "factor",              label: __("Factor"),      default_width: 5,  default_visible: true,  default_sort_order: 6 },
				{ field_key: "line_total",          label: __("Line Total"),  default_width: 10, default_visible: true,  default_sort_order: 7 },
				{ field_key: "owner_ref_no",        label: __("Ref"),         default_width: 9,  default_visible: true,  default_sort_order: 8 },
				{ field_key: "owner_page",          label: __("Owner Page"),  default_width: 5,  default_visible: false, default_sort_order: 9 },
				{ field_key: "owner_file_ref",      label: __("File Ref"),    default_width: 5,  default_visible: false, default_sort_order: 10 },
			];
		},

		/**
		 * BOQ Header summary columns (header metadata only, not structure rows).
		 * Used for Header-only Excel / PDF exports from BOQ Header form.
		 *
		 * @returns {ColumnDescriptor[]}
		 */
		header: function () {
			return [
				{ field_key: "name",                 label: __("BOQ ID"),               default_width: 15, default_visible: true,  default_sort_order: 0 },
				{ field_key: "title",                label: __("Title"),                default_width: 20, default_visible: true,  default_sort_order: 1 },
				{ field_key: "project_name",         label: __("Project"),              default_width: 20, default_visible: true,  default_sort_order: 2 },
				{ field_key: "boq_type",             label: __("BOQ Type"),             default_width: 10, default_visible: true,  default_sort_order: 3 },
				{ field_key: "status",               label: __("Status"),               default_width: 10, default_visible: true,  default_sort_order: 4 },
				{ field_key: "version",              label: __("Version"),              default_width: 8,  default_visible: true,  default_sort_order: 5 },
				{ field_key: "total_contract_value", label: __("Total Contract Value"), default_width: 15, default_visible: true,  default_sort_order: 6 },
				{ field_key: "total_budgeted_cost",  label: __("Total Budgeted Cost"),  default_width: 15, default_visible: true,  default_sort_order: 7 },
				{ field_key: "created_on",           label: __("Created On"),           default_width: 12, default_visible: false, default_sort_order: 8 },
				{ field_key: "modified_on",          label: __("Modified On"),          default_width: 12, default_visible: false, default_sort_order: 9 },
			];
		},
	};
})();
