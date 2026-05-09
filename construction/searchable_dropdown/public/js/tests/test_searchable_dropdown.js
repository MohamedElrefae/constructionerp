/**
 * JavaScript Tests for SearchableDropdownEnhancer
 * Run in browser console or with QUnit/Jest
 */

// Mock Frappe environment for testing
if (typeof frappe === 'undefined') {
    frappe = {
        provide: function(path) {
            const parts = path.split('.');
            let current = window;
            for (const part of parts) {
                current[part] = current[part] || {};
                current = current[part];
            }
            return current;
        },
        get_meta: function(doctype) {
            return {
                fields: [
                    { fieldname: 'name' },
                    { fieldname: 'account_code' },
                    { fieldname: 'account_name' },
                    { fieldname: 'account_name_ar' }
                ]
            };
        }
    };
}

// Test Suite
const SearchableDropdownTests = {
    results: [],
    
    // ============================================
    // Test Utilities
    // ============================================
    assert: function(condition, message) {
        if (condition) {
            this.results.push({ status: 'PASS', message });
            console.log('✓ PASS: ' + message);
        } else {
            this.results.push({ status: 'FAIL', message });
            console.error('✗ FAIL: ' + message);
        }
    },
    
    assertEqual: function(actual, expected, message) {
        const condition = actual === expected;
        const fullMessage = message + ` (expected: "${expected}", got: "${actual}")`;
        this.assert(condition, fullMessage);
    },
    
    assertTrue: function(value, message) {
        this.assert(value === true, message);
    },
    
    assertFalse: function(value, message) {
        this.assert(value === false, message);
    },
    
    assertExists: function(value, message) {
        this.assert(value !== null && value !== undefined, message);
    },
    
    // ============================================
    // Test: formatLabel
    // ============================================
    test_formatLabel_basic: function() {
        console.log('\n--- Test: formatLabel (basic) ---');
        
        const doc = { name: 'ACC-001', code: '1000', name_en: 'Cash' };
        const format = '{code} - {name_en}';
        
        const result = construction.searchable_dropdown.utils.formatLabel(doc, format);
        
        this.assertEqual(result, '1000 - Cash', 'Format with code and name');
    },
    
    test_formatLabel_with_arabic: function() {
        console.log('\n--- Test: formatLabel (Arabic) ---');
        
        const doc = { 
            name: 'ACC-002', 
            account_code: '1100', 
            account_name: 'Bank Account',
            account_name_ar: 'حساب البنك'
        };
        const format = '{account_code} - {account_name_ar}';
        
        const result = construction.searchable_dropdown.utils.formatLabel(doc, format);
        
        this.assertEqual(result, '1100 - حساب البنك', 'Format with Arabic name');
    },
    
    test_formatLabel_fallback: function() {
        console.log('\n--- Test: formatLabel (fallback) ---');
        
        const doc = { name: 'ACC-003' };
        const format = '{nonexistent_field}';
        
        const result = construction.searchable_dropdown.utils.formatLabel(doc, format);
        
        // Should fall back to empty or name
        this.assertTrue(result.length > 0, 'Format fallback returns non-empty string');
    },
    
    test_formatLabel_empty_doc: function() {
        console.log('\n--- Test: formatLabel (empty doc) ---');
        
        const doc = {};
        const format = '{code} - {name}';
        
        const result = construction.searchable_dropdown.utils.formatLabel(doc, format);
        
        this.assertTrue(typeof result === 'string', 'Handles empty doc gracefully');
    },
    
    // ============================================
    // Test: getSearchFields
    // ============================================
    test_getSearchFields: function() {
        console.log('\n--- Test: getSearchFields ---');
        
        const fields = construction.searchable_dropdown.utils.getSearchFields('Account');
        
        this.assertTrue(Array.isArray(fields), 'Returns array');
        this.assertTrue(fields.includes('name'), 'Always includes name field');
        this.assertTrue(fields.length > 1, 'Includes additional search fields');
    },
    
    // ============================================
    // Test: getDefaultFormat
    // ============================================
    test_getDefaultFormat: function() {
        console.log('\n--- Test: getDefaultFormat ---');
        
        const format = construction.searchable_dropdown.utils.getDefaultFormat('Account');
        
        this.assertTrue(typeof format === 'string', 'Returns string format');
        this.assertTrue(format.includes('{') && format.includes('}'), 'Contains placeholders');
    },
    
    // ============================================
    // Test: SearchableDropdownEnhancer
    // ============================================
    test_enhancer_constructor: function() {
        console.log('\n--- Test: SearchableDropdownEnhancer (constructor) ---');
        
        // Mock field object
        const mockField = {
            $input_area: $('<div>'),
            $wrapper: $('<div>'),
            $input: $('<input>'),
            set_value: function() {},
            get_query: null
        };
        
        const enhancer = new SearchableDropdownEnhancer({
            field: mockField,
            doctype: 'Account',
            display_format: '{account_code} - {account_name}',
            search_fields: ['account_code', 'account_name']
        });
        
        this.assertExists(enhancer, 'Enhancer created');
        this.assertEqual(enhancer.doctype, 'Account', 'Doctype stored correctly');
        this.assertTrue(mockField.$input_area.hasClass('searchable-dropdown'), 'CSS class applied');
    },
    
    test_enhancer_setCustomQuery: function() {
        console.log('\n--- Test: SearchableDropdownEnhancer (setCustomQuery) ---');
        
        const mockField = {
            $input_area: $('<div>'),
            $wrapper: $('<div>'),
            $input: $('<input>'),
            set_value: function() {},
            get_query: null
        };
        
        const enhancer = new SearchableDropdownEnhancer({
            field: mockField,
            doctype: 'Account',
            search_fields: ['account_code', 'account_name']
        });
        
        this.assertTrue(typeof mockField.get_query === 'function', 'get_query is function');
        
        const queryResult = mockField.get_query();
        this.assertExists(queryResult.query, 'Query path set');
        this.assertExists(queryResult.filters, 'Filters set');
        this.assertEqual(queryResult.filters.doctype, 'Account', 'Doctype in filters');
    },
    
    test_enhancer_destroy: function() {
        console.log('\n--- Test: SearchableDropdownEnhancer (destroy) ---');
        
        const mockField = {
            $input_area: $('<div>').addClass('searchable-dropdown'),
            $wrapper: $('<div>').addClass('searchable-dropdown-wrapper'),
            $input: $('<input>'),
            set_value: function() {},
            get_query: function() {},
            _searchableDropdown: null,
            off: function() { this._eventsCleared = true; }
        };
        
        const enhancer = new SearchableDropdownEnhancer({
            field: mockField,
            doctype: 'Account'
        });
        
        enhancer.destroy();
        
        this.assertFalse(mockField.$input_area.hasClass('searchable-dropdown'), 'CSS class removed');
        this.assertFalse(mockField.$wrapper.hasClass('searchable-dropdown-wrapper'), 'Wrapper class removed');
        this.assertEqual(mockField.get_query, null, 'get_query reset to null');
    },
    
    // ============================================
    // Run All Tests
    // ============================================
    runAll: function() {
        console.clear();
        console.log('========================================');
        console.log('Searchable Dropdown Enhancer Tests');
        console.log('========================================\n');
        
        this.results = [];
        
        // Run all tests
        this.test_formatLabel_basic();
        this.test_formatLabel_with_arabic();
        this.test_formatLabel_fallback();
        this.test_formatLabel_empty_doc();
        this.test_getSearchFields();
        this.test_getDefaultFormat();
        this.test_enhancer_constructor();
        this.test_enhancer_setCustomQuery();
        this.test_enhancer_destroy();
        
        // Summary
        console.log('\n========================================');
        console.log('Test Summary');
        console.log('========================================');
        
        const passed = this.results.filter(r => r.status === 'PASS').length;
        const failed = this.results.filter(r => r.status === 'FAIL').length;
        const total = this.results.length;
        
        console.log(`Total: ${total}, Passed: ${passed}, Failed: ${failed}`);
        
        if (failed > 0) {
            console.log('\nFailed Tests:');
            this.results
                .filter(r => r.status === 'FAIL')
                .forEach(r => console.log(`  - ${r.message}`));
        }
        
        console.log('\n========================================');
        
        return { passed, failed, total };
    }
};

// Auto-run if in browser console
if (typeof window !== 'undefined') {
    window.SearchableDropdownTests = SearchableDropdownTests;
    
    // Add to global for easy access
    window.runDropdownTests = function() {
        return SearchableDropdownTests.runAll();
    };
    
    console.log('Test suite loaded. Run tests with: runDropdownTests()');
}
