/**
 * Searchable Dropdown Utilities
 */

frappe.provide('construction.searchable_dropdown.utils');

/**
 * Format a label using a display format template
 * @param {Object} doc - Document with field values
 * @param {String} format - Format string e.g. '{code} - {name}'
 * @returns {String} Formatted label
 */
construction.searchable_dropdown.utils.formatLabel = function(doc, format) {
    if (!format) return doc.name || '';
    
    try {
        let label = format;
        
        // Replace each {field} with value
        for (const [key, value] of Object.entries(doc)) {
            label = label.replace(new RegExp(`{${key}}`, 'g'), value || '');
        }
        
        // Clean up empty placeholders and extra separators
        label = label.replace(/\{\w+\}/g, ''); // Remove unmatched placeholders
        label = label.replace(/\s*-\s*$/g, ''); // Remove trailing separator
        label = label.replace(/^\s*-\s*/g, ''); // Remove leading separator
        label = label.trim();
        
        // Fallback to name if empty
        if (!label && doc.name) {
            return doc.name;
        }
        
        return label;
    } catch (e) {
        return doc.name || '';
    }
};

/**
 * Build search fields array from meta
 * @param {String} doctype - DocType name
 * @returns {Array} Array of fieldnames to search
 */
construction.searchable_dropdown.utils.getSearchFields = function(doctype) {
    const fields = ['name'];
    const meta = frappe.get_meta(doctype);
    
    if (!meta) return fields;
    
    // Check for common code/name fields
    const commonFields = ['code', 'item_code', 'account_code', 'customer_code'];
    const nameFields = ['name_ar', 'item_name', 'account_name', 'customer_name'];
    
    for (const f of commonFields) {
        if (meta.fields.find(df => df.fieldname === f)) {
            fields.push(f);
        }
    }
    
    for (const f of nameFields) {
        if (meta.fields.find(df => df.fieldname === f)) {
            fields.push(f);
        }
    }
    
    return fields;
};

/**
 * Get default display format for a doctype
 * @param {String} doctype - DocType name
 * @returns {String} Default format string
 */
construction.searchable_dropdown.utils.getDefaultFormat = function(doctype) {
    const meta = frappe.get_meta(doctype);
    
    if (!meta) return '{name}';
    
    // Check for code field
    const codeField = meta.fields.find(f => 
        f.fieldname.includes('code') || f.fieldname.includes('_code')
    );
    
    // Check for name field
    const nameField = meta.fields.find(f => 
        f.fieldname.includes('name') && f.fieldname !== 'name'
    );
    
    if (codeField && nameField) {
        return `{${codeField.fieldname}} - {${nameField.fieldname}}`;
    } else if (codeField) {
        return `{${codeField.fieldname}} - {name}`;
    } else if (nameField) {
        return `{${nameField.fieldname}}`;
    }
    
    return '{name}';
};
