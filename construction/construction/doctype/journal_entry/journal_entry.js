/**
 * Journal Entry - Searchable Dropdown Enhancement
 * Enhances the Account field in Journal Entry Account child table
 */

/**
 * Set custom query for Account field in Journal Entry
 * Uses Frappe's native get_query mechanism
 */
function setJournalEntryAccountQuery(frm) {
	const grid = frm.fields_dict.accounts;
	if (!grid) return;

	// Get the grid's field definition for 'account'
	const gridField = grid.grid;
	if (!gridField) return;

	// Set get_query on the grid's account field
	// This affects all rows in the child table
	const field = gridField.get_field("account");
	if (!field) return;

	// Check if already set
	if (field._searchableDropdownSet) return;

	// Set custom query function
	field.get_query = function () {
		return {
			query: "construction.searchable_dropdown.api.search.searchable_link_search",
			filters: {
				doctype: "Account",
				search_fields: ["account_code", "account_name", "account_name_ar"],
				display_format: "{account_code} - {account_name}",
				is_group: 0, // Only leaf accounts
			},
		};
	};

	// Mark as set
	field._searchableDropdownSet = true;

	// Add CSS class for styling
	if (field.$input_area) {
		field.$input_area.addClass("searchable-dropdown");
	}

	console.log("[Journal Entry] Account field query set");
}

frappe.ui.form.on("Journal Entry", {
	onload: function (frm) {
		if (!frm._searchableDropdowns) {
			frm._searchableDropdowns = [];
		}
	},

	refresh: function (frm) {
		setJournalEntryAccountQuery(frm);
	},
});

frappe.ui.form.on("Journal Entry Account", {
	form_render: function (frm, cdt, cdn) {
		// Ensure query is set when new rows render
		setJournalEntryAccountQuery(frm);
	},

	account: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.account) {
			console.log("[Journal Entry] Account selected:", row.account);
		}
	},
});
