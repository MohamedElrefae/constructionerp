"""
Searchable Dropdown API
Enhanced search for Link fields with multi-field search and custom formatting.
"""

import frappe
from frappe import _


@frappe.whitelist()
def searchable_link_search(
    doctype: str,
    txt: str,
    filters: dict = None,
    page_length: int = 20,
    search_fields: list = None,
    display_format: str = None
):
    """
    Enhanced search for searchable dropdown wrapper.
    
    Args:
        doctype: Target DocType (e.g., 'Account')
        txt: Search string
        filters: JSON dict of base filters
        page_length: Max results (default 20)
        search_fields: List of fields to search (default: ['name'])
        display_format: Format string, e.g. '{account_code} - {account_name}'
    
    Returns:
        List of dicts: [{value, label, description}, ...]
    """
    
    # Default values
    if not search_fields:
        search_fields = ['name']
    if not display_format:
        display_format = '{name}'
    if not filters:
        filters = {}
    
    # Build OR filters for search
    or_filters = []
    search_txt = txt.strip() if txt else ''
    
    if search_txt:
        for field in search_fields:
            if field != 'name' and frappe.get_meta(doctype).has_field(field):
                or_filters.append([field, 'like', f'%{search_txt}%'])
        # Always include name field
        or_filters.append(['name', 'like', f'%{search_txt}%'])
    
    try:
        # Use frappe.get_list for automatic permission checking
        results = frappe.get_list(
            doctype,
            filters=filters,
            or_filters=or_filters if or_filters else None,
            fields=['name'] + [f for f in search_fields if f != 'name'],
            limit_page_length=page_length,
            order_by='modified desc'
        )
        
        # Format output
        formatted_results = []
        for doc in results:
            label = _format_label(doc, display_format, search_fields)
            formatted_results.append({
                'value': doc.name,
                'label': label,
                'description': doc.get('description', '')
            })
        
        return formatted_results
        
    except frappe.PermissionError:
        # Return empty list if user lacks permissions
        return []
    except Exception as e:
        frappe.log_error(f'Searchable dropdown search error: {str(e)}')
        return []


def _format_label(doc: dict, display_format: str, search_fields: list) -> str:
    """
    Format label using display_format template.
    
    Args:
        doc: Document dict with field values
        display_format: Format string with {field_name} placeholders
        search_fields: Available fields for fallback
    
    Returns:
        Formatted label string
    """
    try:
        # Prepare format kwargs
        format_kwargs = {'name': doc.get('name', '')}
        
        for field in search_fields:
            format_kwargs[field] = doc.get(field, '')
        
        # Try to format with available fields
        label = display_format.format(**format_kwargs)
        
        # If result is empty or just separators, fallback to name
        clean_label = label.replace('-', '').strip()
        if not clean_label:
            return doc.get('name', '')
        
        return label
        
    except (KeyError, ValueError):
        # Fallback to name if format fails
        return doc.get('name', '')


@frappe.whitelist()
def get_recent_items(doctype: str, limit: int = 5):
    """
    Get recently used items for a doctype.
    Optional: for empty search state.
    
    Args:
        doctype: Target DocType
        limit: Number of items to return
    
    Returns:
        List of recent items
    """
    try:
        results = frappe.get_list(
            doctype,
            fields=['name'],
            limit_page_length=limit,
            order_by='modified desc'
        )
        
        return [{'value': d.name, 'label': d.name} for d in results]
        
    except frappe.PermissionError:
        return []
