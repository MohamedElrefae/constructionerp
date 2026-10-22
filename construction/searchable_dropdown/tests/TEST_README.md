# Searchable Dropdown Test Suite

## Running Tests

### Python Unit Tests

```bash
# Run all tests
bench --site [your-site] run-tests --module construction.searchable_dropdown.tests.test_search_api

# Run integration tests
bench --site [your-site] run-tests --module construction.searchable_dropdown.tests.test_integration

# Run specific test class
bench --site [your-site] run-tests --test TestSearchableLinkSearch
```

### JavaScript Tests

```javascript
// In browser console (F12)
runDropdownTests();

// Or call directly
SearchableDropdownTests.runAll();
```

## Test Coverage

### API Tests (test_search_api.py)
- [x] Search by code
- [x] Search by name
- [x] Permission checking
- [x] Label formatting
- [x] Format fallback
- [x] Empty search handling
- [x] Page length limits
- [x] Special character handling

### Enhancer Tests (test_searchable_dropdown.js)
- [x] formatLabel basic
- [x] formatLabel with Arabic
- [x] formatLabel fallback
- [x] formatLabel empty doc
- [x] getSearchFields
- [x] getDefaultFormat
- [x] Enhancer constructor
- [x] setCustomQuery
- [x] destroy cleanup

### Integration Tests (test_integration.py)
- [x] End-to-end search flow
- [x] Company filter respect
- [x] Performance (< 500ms)
- [x] Concurrent searches
- [x] Empty results handling
- [x] Permission enforcement

## Manual Testing Checklist

Before marking Week 1 complete, manually verify:

1. **API Endpoint**
   ```python
   frappe.call({
       method: 'construction.searchable_dropdown.api.search.searchable_link_search',
       args: {
           doctype: 'Account',
           txt: 'cash',
           search_fields: ['account_name', 'account_name_ar'],
           display_format: '{account_code} - {account_name}'
       }
   })
   ```

2. **JS Enhancer**
   ```javascript
   // In browser console on Journal Entry page
   const field = cur_frm.fields_dict.accounts.grid.get_field('account');
   const enhancer = new SearchableDropdownEnhancer({
       field: field,
       doctype: 'Account',
       display_format: '{account_code} - {account_name}'
   });
   console.log('Enhancer created:', enhancer);
   ```

3. **CSS Styling**
   - Check hover effect (blue left border)
   - Check selected state (bold + checkmark)
   - Verify RTL layout if Arabic enabled

## Debugging

### Enable Debug Logging
```python
# In bench console
frappe.logger().setLevel('DEBUG')
```

### Check Asset Loading
```javascript
// In browser console
console.log('Utils loaded:', typeof construction.searchable_dropdown.utils);
console.log('Enhancer loaded:', typeof SearchableDropdownEnhancer);
```

### API Debug
```bash
# Watch API calls
bench --site [site] console
frappe.log_error('Debug: searchable_link_search called')
```
