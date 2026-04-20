"""
Modern Form API for Hybrid CRUD Operations
Bridges Frappe backend with custom React frontend
"""
import frappe
from frappe import _
from frappe.model.document import Document


@frappe.whitelist()
def get_form_config(doctype):
    """
    Get form configuration for a DocType
    Returns field definitions, layout info, and validation rules
    
    Args:
        doctype: str - The DocType name
    
    Returns:
        dict: Form configuration
    """
    try:
        meta = frappe.get_meta(doctype)
        
        fields = []
        for field in meta.fields:
            if field.hidden:
                continue
                
            field_config = {
                "id": field.fieldname,
                "type": map_field_type(field.fieldtype),
                "label": field.label,
                "placeholder": field.description,
                "required": field.reqd,
                "read_only": field.read_only,
                "default": field.default,
                "help_text": field.description,
                "depends_on": field.depends_on,
                "mandatory_depends_on": field.mandatory_depends_on,
                "read_only_depends_on": field.read_only_depends_on,
            }
            
            # Add options for select/link fields
            if field.fieldtype in ["Select", "Link", "Table MultiSelect"]:
                if field.fieldtype == "Select" and field.options:
                    field_config["options"] = [
                        {"value": opt, "label": opt}
                        for opt in field.options.split("\n")
                    ]
                elif field.fieldtype == "Link":
                    field_config["link_doctype"] = field.options
                    field_config["searchable"] = True
            
            # Add validation rules
            field_config["validation"] = build_validation_rules(field)
            
            fields.append(field_config)
        
        return {
            "success": True,
            "doctype": doctype,
            "title": meta.title_field or "name",
            "fields": fields,
            "is_submittable": meta.is_submittable,
            "is_tree": hasattr(meta, 'is_tree') and meta.is_tree,
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting form config for {doctype}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_document(doctype, name):
    """
    Get a single document by name
    
    Args:
        doctype: str
        name: str
    
    Returns:
        dict: Document data
    """
    try:
        doc = frappe.get_doc(doctype, name)
        
        # Build response
        data = {}
        meta = frappe.get_meta(doctype)
        
        for field in meta.fields:
            if not field.hidden:
                data[field.fieldname] = doc.get(field.fieldname)
        
        # Add standard fields
        data["name"] = doc.name
        data["owner"] = doc.owner
        data["creation"] = str(doc.creation) if doc.creation else None
        data["modified"] = str(doc.modified) if doc.modified else None
        data["modified_by"] = doc.modified_by
        data["docstatus"] = doc.docstatus
        
        return {
            "success": True,
            "data": data
        }
        
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "error": f"{doctype} '{name}' not found"
        }
    except Exception as e:
        frappe.log_error(f"Error getting document {doctype}/{name}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def create_document(doctype, data):
    """
    Create a new document
    
    Args:
        doctype: str
        data: dict - Field values
    
    Returns:
        dict: Created document or errors
    """
    try:
        # Validate before creation
        validation_result = validate_document_data(doctype, data, is_new=True)
        if not validation_result["valid"]:
            return {
                "success": False,
                "validation_errors": validation_result["errors"]
            }
        
        # Create document
        doc = frappe.new_doc(doctype)
        
        # Set field values
        for fieldname, value in data.items():
            if hasattr(doc, fieldname):
                doc.set(fieldname, value)
        
        # Save
        doc.insert()
        frappe.db.commit()
        
        return {
            "success": True,
            "data": {
                "name": doc.name,
                "message": _(f"{doctype} created successfully")
            }
        }
        
    except frappe.ValidationError as e:
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        frappe.log_error(f"Error creating {doctype}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def update_document(doctype, name, data):
    """
    Update an existing document
    
    Args:
        doctype: str
        name: str
        data: dict - Field values to update
    
    Returns:
        dict: Updated document or errors
    """
    try:
        doc = frappe.get_doc(doctype, name)
        
        # Check permissions
        if not doc.has_permission("write"):
            return {
                "success": False,
                "error": _("Not permitted to update this document")
            }
        
        # Validate before update
        validation_result = validate_document_data(doctype, data, is_new=False)
        if not validation_result["valid"]:
            return {
                "success": False,
                "validation_errors": validation_result["errors"]
            }
        
        # Update field values
        for fieldname, value in data.items():
            if hasattr(doc, fieldname):
                doc.set(fieldname, value)
        
        # Save
        doc.save()
        frappe.db.commit()
        
        return {
            "success": True,
            "data": {
                "name": doc.name,
                "message": _(f"{doctype} updated successfully")
            }
        }
        
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "error": f"{doctype} '{name}' not found"
        }
    except frappe.ValidationError as e:
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        frappe.log_error(f"Error updating {doctype}/{name}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def delete_document(doctype, name):
    """
    Delete a document
    
    Args:
        doctype: str
        name: str
    
    Returns:
        dict: Success or error
    """
    try:
        doc = frappe.get_doc(doctype, name)
        
        # Check permissions
        if not doc.has_permission("delete"):
            return {
                "success": False,
                "error": _("Not permitted to delete this document")
            }
        
        doc.delete()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _(f"{doctype} '{name}' deleted successfully")
        }
        
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "error": f"{doctype} '{name}' not found"
        }
    except Exception as e:
        frappe.log_error(f"Error deleting {doctype}/{name}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def validate_field(doctype, fieldname, value, context=None):
    """
    Validate a single field value
    
    Args:
        doctype: str
        fieldname: str
        value: any
        context: dict - Other field values for conditional validation
    
    Returns:
        dict: Validation result
    """
    try:
        meta = frappe.get_meta(doctype)
        field = meta.get_field(fieldname)
        
        if not field:
            return {
                "valid": False,
                "error": f"Field '{fieldname}' not found"
            }
        
        errors = []
        
        # Required check
        if field.reqd and not value:
            errors.append(_("{0} is required").format(field.label))
        
        # Data type validation
        if value:
            if field.fieldtype in ["Int", "Float", "Currency"]:
                try:
                    float(value)
                except ValueError:
                    errors.append(_("{0} must be a number").format(field.label))
            
            elif field.fieldtype == "Date":
                if not is_valid_date(value):
                    errors.append(_("{0} must be a valid date").format(field.label))
            
            elif field.fieldtype == "Email":
                if not is_valid_email(value):
                    errors.append(_("{0} must be a valid email").format(field.label))
        
        # Custom validation (if any)
        # Could call hooks here for custom validation logic
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
        
    except Exception as e:
        frappe.log_error(f"Error validating field {doctype}.{fieldname}: {str(e)}")
        return {
            "valid": False,
            "error": str(e)
        }


@frappe.whitelist()
def search_link(doctype, txt, filters=None, page_length=20):
    """
    Search for link field values
    
    Args:
        doctype: str - Target DocType
        txt: str - Search text
        filters: dict - Additional filters
        page_length: int
    
    Returns:
        list: Matching documents
    """
    try:
        # Use Frappe's built-in link search
        results = frappe.get_list(
            doctype,
            fields=["name", "title"] if frappe.get_meta(doctype).get_field("title") else ["name"],
            filters=filters or {},
            or_filters={
                "name": ["like", f"%{txt}%"],
                "title": ["like", f"%{txt}%"] if frappe.get_meta(doctype).get_field("title") else None
            },
            limit_page_length=page_length
        )
        
        return {
            "success": True,
            "results": [
                {
                    "value": r.name,
                    "label": r.get("title") or r.name
                }
                for r in results
            ]
        }
        
    except Exception as e:
        frappe.log_error(f"Error searching link {doctype}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# ==================== Helper Functions ====================

def map_field_type(frappe_fieldtype):
    """Map Frappe field types to form field types"""
    mapping = {
        "Data": "text",
        "Int": "number",
        "Float": "number",
        "Currency": "number",
        "Check": "checkbox",
        "Select": "select",
        "Link": "searchable-select",
        "Dynamic Link": "text",
        "Text": "textarea",
        "Text Editor": "textarea",
        "Date": "date",
        "Datetime": "datetime",
        "Time": "time",
        "Password": "password",
        "Attach": "file",
        "Attach Image": "file",
        "Color": "text",
        "Barcode": "text",
        "Geolocation": "text",
        "Phone": "tel",
        "Rating": "number",
        "Signature": "text",
        "JSON": "textarea",
        "Code": "textarea",
        "Markdown Editor": "textarea",
        "HTML Editor": "textarea",
        "Table": "table",
        "Table MultiSelect": "multi-select",
        "Autocomplete": "searchable-select",
        "Read Only": "text",
        "Button": "button",
        "HTML": "html",
        "Image": "image",
        "Fold": "section",
        "Column Break": "column-break",
        "Section Break": "section-break",
        "Tab Break": "tab-break",
        "Heading": "heading",
    }
    
    return mapping.get(frappe_fieldtype, "text")


def build_validation_rules(field):
    """Build validation rules for a field"""
    rules = {}
    
    if field.fieldtype in ["Int", "Float", "Currency"]:
        rules["type"] = "number"
        if field.fieldtype == "Int":
            rules["integer"] = True
    
    if field.fieldtype == "Date":
        rules["type"] = "date"
    
    if field.fieldtype == "Email":
        rules["type"] = "email"
    
    if field.fieldtype in ["Data", "Text"]:
        if field.length:
            rules["maxLength"] = field.length
    
    return rules


def validate_document_data(doctype, data, is_new=True):
    """Validate all document data before save"""
    errors = {}
    meta = frappe.get_meta(doctype)
    
    for field in meta.fields:
        if field.hidden or field.read_only:
            continue
        
        fieldname = field.fieldname
        value = data.get(fieldname)
        
        # Required check
        if field.reqd and not value:
            errors[fieldname] = _("{0} is required").format(field.label)
            continue
        
        # Field type validation
        if value and field.fieldtype in ["Int", "Float", "Currency"]:
            try:
                float(value)
            except ValueError:
                errors[fieldname] = _("{0} must be a number").format(field.label)
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def is_valid_date(value):
    """Check if value is a valid date"""
    try:
        frappe.utils.getdate(value)
        return True
    except:
        return False


def is_valid_email(value):
    """Check if value is a valid email"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, str(value)) is not None
