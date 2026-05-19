/**
 * Journal Entry - Searchable Dropdown Enhancement
 * Enhances the Account field in Journal Entry Account child table
 *
 * Features:
 * - Multi-field search (account_code, account_name, account_name_ar)
 * - Code-Name display format
 * - Clear option ("— بلا —")
 * - Hover effects and RTL support
 */

frappe.ui.form.on('Journal Entry', {
    onload: function(frm) {
        // Initialize searchable dropdowns array for cleanup
        if (!frm._searchableDropdowns) {
            frm._searchableDropdowns = [];
        }
    },

    refresh: function(frm) {
        // Enhance Account field in the accounts grid
        frm.events.enhance_account_field(frm);
    },

    enhance_account_field: function(frm) {
        // Get the Account field from the child table
        const grid = frm.fields_dict.accounts;
        if (!grid) return;

        const accountField = grid.get_field('account');
        if (!accountField) return;

        // Check if already enhanced
        if (accountField._searchableDropdown) {
            return;
        }

        // Apply searchable dropdown enhancer
        const enhancer = new SearchableDropdownEnhancer({
            field: accountField,
            doctype: 'Account',
            display_format: '{account_code} - {account_name}',
            search_fields: ['account_code', 'account_name', 'account_name_ar'],
            filters: {
                is_group: 0  // Only leaf accounts (postable)
            },
            clear_option: true
        });

        // Track for cleanup
        frm._searchableDropdowns.push(enhancer);

        console.log('[Journal Entry] Account field enhanced with searchable dropdown');
    }
});

// Also enhance on row add in child table
frappe.ui.form.on('Journal Entry Account', {
    form_render: function(frm, cdt, cdn) {
        // The parent form's refresh handler will handle enhancement
        // This ensures newly added rows also get the enhancement
        if (frm.events.enhance_account_field) {
            frm.events.enhance_account_field(frm);
        }
    },

    account: function(frm, cdt, cdn) {
        // When account is selected, you can add additional logic here
        const row = locals[cdt][cdn];
        if (row.account) {
            console.log('[Journal Entry] Account selected:', row.account);
        }
    }
});
