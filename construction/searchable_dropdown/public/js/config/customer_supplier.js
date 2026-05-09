/**
 * Customer & Supplier - Searchable Dropdown Enhancement
 * Enhances the Customer and Supplier fields in transaction forms
 * 
 * Features:
 * - Multi-field search (customer_code/customer_name, or name)
 * - Code-Name display format
 * - Clear option ("— بلا —")
 * - Company-specific filtering
 */

// ============================================
// Customer Enhancement
// ============================================

frappe.ui.form.on('Customer', {
    onload: function(frm) {
        if (!frm._searchableDropdowns) {
            frm._searchableDropdowns = [];
        }
    },

    refresh: function(frm) {
        frm.events.enhance_customer_fields(frm);
    },

    enhance_customer_fields: function(frm) {
        // Enhance any Link fields to Customer in this form
        // Typically used in transaction forms (Quotation, Sales Order, etc.)
        // This script is for the Customer form itself if it has self-references
    }
});

// ============================================
// Supplier Enhancement  
// ============================================

frappe.ui.form.on('Supplier', {
    onload: function(frm) {
        if (!frm._searchableDropdowns) {
            frm._searchableDropdowns = [];
        }
    },

    refresh: function(frm) {
        frm.events.enhance_supplier_fields(frm);
    },

    enhance_supplier_fields: function(frm) {
        // Enhance any Link fields to Supplier in this form
    }
});

// ============================================
// Transaction Forms - Apply to Customer/Supplier fields
// ============================================

/**
 * Helper to enhance Customer field in any transaction form
 * Usage: Call from any form's refresh event
 */
construction.searchable_dropdown.enhanceCustomerField = function(frm, fieldname) {
    const field = frm.fields_dict[fieldname];
    if (!field || field._searchableDropdown) return;

    const enhancer = new SearchableDropdownEnhancer({
        field: field,
        doctype: 'Customer',
        display_format: '{customer_code} - {customer_name}',
        search_fields: ['customer_code', 'customer_name', 'customer_name_ar', 'mobile_no', 'email_id'],
        filters: {
            docstatus: 0  // Active customers
        },
        clear_option: true
    });

    if (!frm._searchableDropdowns) {
        frm._searchableDropdowns = [];
    }
    frm._searchableDropdowns.push(enhancer);
    console.log(`[${frm.doctype}] Customer field "${fieldname}" enhanced`);
};

/**
 * Helper to enhance Supplier field in any transaction form
 */
construction.searchable_dropdown.enhanceSupplierField = function(frm, fieldname) {
    const field = frm.fields_dict[fieldname];
    if (!field || field._searchableDropdown) return;

    const enhancer = new SearchableDropdownEnhancer({
        field: field,
        doctype: 'Supplier',
        display_format: '{supplier_code} - {supplier_name}',
        search_fields: ['supplier_code', 'supplier_name', 'supplier_name_ar', 'mobile_no', 'email_id'],
        filters: {
            docstatus: 0  // Active suppliers
        },
        clear_option: true
    });

    if (!frm._searchableDropdowns) {
        frm._searchableDropdowns = [];
    }
    frm._searchableDropdowns.push(enhancer);
    console.log(`[${frm.doctype}] Supplier field "${fieldname}" enhanced`);
};

// ============================================
// Example: Quotation Form (Customer field)
// ============================================

frappe.ui.form.on('Quotation', {
    refresh: function(frm) {
        // Enhance Customer field
        if (frm.fields_dict.party_name) {
            construction.searchable_dropdown.enhanceCustomerField(frm, 'party_name');
        }
    }
});

// ============================================
// Example: Purchase Order Form (Supplier field)
// ============================================

frappe.ui.form.on('Purchase Order', {
    refresh: function(frm) {
        // Enhance Supplier field
        if (frm.fields_dict.supplier) {
            construction.searchable_dropdown.enhanceSupplierField(frm, 'supplier');
        }
    }
});
