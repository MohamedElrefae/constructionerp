/**
 * Sales Invoice - Searchable Dropdown Enhancement
 * Enhances the Item field in Sales Invoice Item child table
 */

function setSalesInvoiceItemQuery(frm) {
	const grid = frm.fields_dict.items;
	if (!grid) return;

	const gridField = grid.grid;
	if (!gridField) return;

	const field = gridField.get_field("item_code");
	if (!field) return;

	if (field._searchableDropdownSet) return;

	field.get_query = function () {
		return {
			query: "construction.searchable_dropdown.api.search.searchable_link_search",
			filters: {
				doctype: "Item",
				search_fields: ["item_code", "item_name", "item_name_ar", "description"],
				display_format: "{item_code} - {item_name}",
				is_sales_item: 1,
				docstatus: 0,
			},
		};
	};

	field._searchableDropdownSet = true;

	if (field.$input_area) {
		field.$input_area.addClass("searchable-dropdown");
	}

	console.log("[Sales Invoice] Item field query set");
}

frappe.ui.form.on("Sales Invoice", {
	onload: function (frm) {
		if (!frm._searchableDropdowns) {
			frm._searchableDropdowns = [];
		}
	},

	refresh: function (frm) {
		setSalesInvoiceItemQuery(frm);
	},

	company: function (frm) {
		setSalesInvoiceItemQuery(frm);
	},
});

frappe.ui.form.on("Sales Invoice Item", {
	form_render: function (frm, cdt, cdn) {
		setSalesInvoiceItemQuery(frm);
	},

	item_code: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.item_code) {
			console.log("[Sales Invoice] Item selected:", row.item_code);
		}
	},
});
