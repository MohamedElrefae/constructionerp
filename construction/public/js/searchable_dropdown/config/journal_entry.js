/**
 * Journal Entry - Searchable Dropdown Enhancement
 * Enhances the Account field in Journal Entry Account child table
 */

/**
 * Set custom query for Account field in Journal Entry
 * Uses Frappe's native get_query mechanism with enhanced search
 */
function setJournalEntryAccountQuery(frm) {
	const grid = frm.fields_dict.accounts;
	if (!grid) return;

	const gridField = grid.grid;
	if (!gridField) return;

	const field = gridField.get_field("account");
	if (!field) return;

	if (field._searchableDropdownSet) return;

	// Use Frappe's standard get_query with filters
	// The filters restrict to leaf accounts (postable)
	field.get_query = function () {
		return {
			filters: {
				is_group: 0, // Only leaf accounts
			},
		};
	};

	field._searchableDropdownSet = true;

	// Add CSS class for styling
	if (field.$input_area) {
		field.$input_area.addClass("searchable-dropdown");
	}

	console.log("[Journal Entry] Account field enhanced");
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
