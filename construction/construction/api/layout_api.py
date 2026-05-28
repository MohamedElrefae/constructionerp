"""
construction/api/layout_api.py
================================
Whitelisted REST endpoints for the Form Layout Engine.
Called by the JS engine (vfc_layout_engine.js) on every form refresh
and by the Sections editor (vfc_sections_tab.js) when saving profiles.

Endpoints
---------
  get_active_layout(doctype)          → returns the best matching profile JSON
  save_layout(doctype, ...)           → create / update a named profile
  list_layouts(doctype)               → list all enabled profiles for doctype
  delete_layout(name)                 → delete (System Manager only, no is_system)
  validate_layout(doctype, sections_json) → pre-save structural check

Resolver priority (get_active_layout)
--------------------------------------
  1. Profile matching user's HIGHEST-priority role (for_role) for this doctype
  2. Default profile (is_default=1) for this doctype
  3. None — JS falls back to native Frappe rendering
"""

import json
import frappe
from frappe import _


# ──────────────────────────────────────────────────────────────────────
# get_active_layout
# ──────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_active_layout(doctype: str) -> dict | None:
    """
    Return the best active Form Layout Profile for the current user.
    Returns None if no profile is configured → JS renders natively.
    """
    if not doctype:
        return None

    user_roles = set(frappe.get_roles(frappe.session.user))

    # Fetch all enabled profiles for this doctype, ordered by priority desc
    profiles = frappe.get_all(
        "Form Layout Profile",
        filters={"reference_doctype": doctype, "enabled": 1},
        fields=["name", "profile_name", "for_role", "priority", "is_default",
                "layout_version", "sections_json"],
        order_by="priority desc",
    )

    if not profiles:
        return None

    # Step 1: match by role
    for profile in profiles:
        if profile.for_role and profile.for_role in user_roles:
            return _profile_response(profile)

    # Step 2: fallback to default
    for profile in profiles:
        if profile.is_default:
            return _profile_response(profile)

    return None


def _profile_response(profile: dict) -> dict:
    """Deserialise sections_json and return a clean response dict."""
    sections_data = profile.get("sections_json") or {}
    if isinstance(sections_data, str):
        try:
            sections_data = json.loads(sections_data)
        except json.JSONDecodeError:
            sections_data = {}

    return {
        "name": profile.name,
        "profile_name": profile.profile_name,
        "layout_version": profile.layout_version,
        "sections": sections_data.get("sections", []),
        "unassigned_policy": sections_data.get("unassigned_policy", "append"),
    }


# ──────────────────────────────────────────────────────────────────────
# save_layout
# ──────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def save_layout(
    doctype: str,
    profile_name: str,
    sections_json: str | dict,
    for_role: str = None,
    is_default: int = 0,
    priority: int = 10,
) -> dict:
    """
    Create or update a Form Layout Profile.
    System Manager only.

    sections_json must be a valid JSON string conforming to the v1 schema:
    {
      "version": 1,
      "unassigned_policy": "append",
      "sections": [ ... ]
    }
    """
    _require_system_manager()

    # Normalise sections_json to string for storage
    if isinstance(sections_json, dict):
        sections_json = json.dumps(sections_json)

    # Check if profile already exists
    existing = frappe.db.get_value(
        "Form Layout Profile",
        {"reference_doctype": doctype, "profile_name": profile_name},
        "name",
    )

    if existing:
        doc = frappe.get_doc("Form Layout Profile", existing)
        doc.sections_json = sections_json
        doc.for_role = for_role
        doc.is_default = is_default
        doc.priority = priority
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "updated", "name": doc.name}
    else:
        doc = frappe.new_doc("Form Layout Profile")
        doc.reference_doctype = doctype
        doc.profile_name = profile_name
        doc.sections_json = sections_json
        doc.for_role = for_role
        doc.is_default = is_default
        doc.priority = priority
        doc.layout_version = 1
        doc.enabled = 1
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "created", "name": doc.name}


# ──────────────────────────────────────────────────────────────────────
# list_layouts
# ──────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_layouts(doctype: str) -> list[dict]:
    """
    Return all enabled Form Layout Profiles for a DocType.
    All users can call this (read permission on the DocType covers it).
    """
    if not doctype:
        return []

    return frappe.get_all(
        "Form Layout Profile",
        filters={"reference_doctype": doctype, "enabled": 1},
        fields=["name", "profile_name", "for_role", "is_default",
                "priority", "is_system", "layout_version"],
        order_by="priority desc",
    )


# ──────────────────────────────────────────────────────────────────────
# delete_layout
# ──────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def delete_layout(name: str) -> dict:
    """
    Delete a Form Layout Profile by name.
    System Manager only. is_system profiles cannot be deleted.
    """
    _require_system_manager()

    doc = frappe.get_doc("Form Layout Profile", name)
    if doc.is_system:
        frappe.throw(
            _("System-seeded profiles cannot be deleted. Disable them instead."),
            frappe.PermissionError,
        )

    frappe.delete_doc("Form Layout Profile", name, ignore_permissions=True)
    frappe.db.commit()
    return {"status": "deleted", "name": name}


# ──────────────────────────────────────────────────────────────────────
# validate_layout
# ──────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def validate_layout(doctype: str, sections_json: str | dict) -> dict:
    """
    Pre-save structural check for a sections_json blob.
    Returns {"valid": true} or {"valid": false, "errors": [...], "warnings": [...]}.
    Does NOT save anything.
    """
    if isinstance(sections_json, str):
        try:
            data = json.loads(sections_json)
        except json.JSONDecodeError as exc:
            return {"valid": False, "errors": [f"Invalid JSON: {exc}"], "warnings": []}
    else:
        data = sections_json

    sections = data.get("sections", [])
    meta = frappe.get_meta(doctype)
    known = {f.fieldname for f in meta.fields}
    required = {f.fieldname for f in meta.fields if f.reqd}

    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()

    for sec in sections:
        col_count = sec.get("column_count", 2)
        if col_count not in (1, 2, 3):
            errors.append(
                f"Section '{sec.get('label', '?')}': column_count must be 1, 2, or 3 (got {col_count})."
            )

        for fld in sec.get("fields", []):
            fn = fld.get("fieldname")
            if not fn:
                errors.append(f"A field in section '{sec.get('label', '?')}' is missing 'fieldname'.")
                continue

            if fn not in known:
                warnings.append(
                    f"Unknown fieldname '{fn}' in section '{sec.get('label', '?')}' — will be skipped at runtime."
                )
                continue

            if fn in seen:
                errors.append(f"Fieldname '{fn}' appears more than once in the layout.")
                continue
            seen.add(fn)

            if not fld.get("visible", True) and fn in required:
                errors.append(f"Required field '{fn}' cannot be hidden.")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


# ──────────────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────────────

def _require_system_manager():
    if frappe.session.user == "Administrator":
        return
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw(
            _("Only System Manager can modify Form Layout Profiles."),
            frappe.PermissionError,
        )
