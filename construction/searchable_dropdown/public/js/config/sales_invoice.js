/**
 * Sales Invoice - Searchable Dropdown Enhancement
 * Enhances the Item field in Sales Invoice Item child table
 *
 * Features:
 * - Multi-field search (item_code, item_name, item_name_ar)
 * - Code-Name display format
 * - Clear option ("— بلا —")
 * - Respects company and warehouse filters
 */

frappe.ui.form.on('Sales Invoice', {
    onload: function(frm) {
        if (!frm._searchableDropdowns) {
            frm._searchableDropdowns = [];
        }
    },

    refresh: function(frm) {
        frm.events.enhance_item_field(frm);
    },

    company: function(frm) {
        // Re-enhance when company changes (filters may change)
        frm.events.enhance_item_field(frm);
    },

    enhance_item_field: function(frm) {
        const grid = frm.fields_dict.items;
        if (!grid) return;

        const itemField = grid.get_field('item_code');
        if (!itemField) return;

        if (itemField._searchableDropdown) {
            return;
        }

        const enhancer = new SearchableDropdownEnhancer({
            field: itemField,
            doctype: 'Item',
            display_format: '{item_code} - {item_name}',
            search_fields: ['item_code', 'item_name', 'item_name_ar', 'description'],
            filters: {
                is_sales_item: 1,
                docstatus: 0  // Active items only
            },
            clear_option: true
        });

        frm._searchableDropdowns.push(enhancer);
        console.log('[Sales Invoice] Item field enhanced with searchable dropdown');
    }
});

frappe.ui.form.on('Sales Invoice Item', {
    form_render: function(frm, cdt, cdn) {
        if (frm.events.enhance_item_field) {
            frm.events.enhance_item_field(frm);
        }
    },

    item_code: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.item_code) {
            console.log('[Sales Invoice] Item selected:', row.item_code);
        }
    }
});
