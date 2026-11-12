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
  1. Personal override: for_user matches current user
  2. Role match: for_role matches a role the user has (highest priority wins)
  3. Default profile: is_default=1 for this doctype
  4. None — JS falls back to native Frappe rendering
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

    user = frappe.session.user
    user_roles = set(frappe.get_roles(user))

    # Check if for_user column exists (migration safety — column may not exist pre-migrate)
    has_for_user = frappe.db.has_column("Form Layout Profile", "for_user")

    # Fetch all enabled profiles for this doctype, ordered by priority desc
    fields = [
        "name",
        "profile_name",
        "for_role",
        "priority",
        "is_default",
        "layout_version",
        "sections_json",
    ]
    if has_for_user:
        fields.append("for_user")

    # Personal layouts contain the user's private section configuration. Keep
    # foreign personal rows out of every resolver candidate set, including for
    # administrators, so they cannot win role/default fallback by priority.
    filters = {"reference_doctype": doctype, "enabled": 1}
    or_filters = _personal_profile_or_filters(user) if has_for_user else None

    profiles = frappe.get_all(
        "Form Layout Profile",
        filters=filters,
        or_filters=or_filters,
        fields=fields,
        order_by="priority desc",
    )

    if not profiles:
        return None

    # Step 1: personal override (highest priority, only if column exists)
    if has_for_user:
        for profile in profiles:
            if profile.for_user and profile.for_user == user:
                return _profile_response(profile)

    # Step 2: match by role
    for profile in profiles:
        if profile.for_role and profile.for_role in user_roles:
            return _profile_response(profile)

    # Step 3: fallback to default
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
        "unassigned_column_count": sections_data.get("unassigned_column_count", 2),
    }


# ──────────────────────────────────────────────────────────────────────
# save_layout
# ──────────────────────────────────────────────────────────────────────


@frappe.whitelist(methods=["POST"])
def save_layout(
    doctype: str,
    profile_name: str,
    sections_json: str | dict,
    for_role: str = None,
    for_user: str = None,
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

    # Check if for_user column exists (migration safety)
    has_for_user = frappe.db.has_column("Form Layout Profile", "for_user")

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
        if has_for_user:
            doc.for_user = for_user
        doc.is_default = is_default
        doc.priority = priority
        doc.save(ignore_permissions=True)
        return {"status": "updated", "name": doc.name}
    else:
        doc = frappe.new_doc("Form Layout Profile")
        doc.reference_doctype = doctype
        doc.profile_name = profile_name
        doc.sections_json = sections_json
        doc.for_role = for_role
        if has_for_user:
            doc.for_user = for_user
        doc.is_default = is_default
        doc.priority = priority
        doc.layout_version = 1
        doc.enabled = 1
        doc.insert(ignore_permissions=True)
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

    fields = ["name", "profile_name", "for_role", "is_default", "priority", "is_system", "layout_version"]
    has_for_user = frappe.db.has_column("Form Layout Profile", "for_user")
    if has_for_user:
        fields.append("for_user")

    user = frappe.session.user
    filters = {"reference_doctype": doctype, "enabled": 1}
    or_filters = None
    if has_for_user and not _may_inspect_foreign_personal_profiles(user):
        or_filters = _personal_profile_or_filters(user)

    return frappe.get_all(
        "Form Layout Profile",
        filters=filters,
        or_filters=or_filters,
        fields=fields,
        order_by="priority desc",
    )


# ──────────────────────────────────────────────────────────────────────
# delete_layout
# ──────────────────────────────────────────────────────────────────────


@frappe.whitelist(methods=["POST"])
def delete_my_personal_layout(doctype: str) -> dict:
    """
    Delete the current user's personal for_user profile for a doctype.
    No System Manager permission required — any user can remove their own
    personal layout override.
    """
    user = frappe.session.user
    existing = frappe.db.get_value(
        "Form Layout Profile",
        {"reference_doctype": doctype, "for_user": user, "enabled": 1},
        "name",
    )
    if not existing:
        return {"status": "not_found", "name": None}

    doc = frappe.get_doc("Form Layout Profile", existing)
    if doc.is_system:
        frappe.throw(
            _("System-seeded profiles cannot be deleted. Disable them instead."),
            frappe.PermissionError,
        )

    frappe.delete_doc("Form Layout Profile", existing, ignore_permissions=True)
    return {"status": "deleted", "name": existing}


@frappe.whitelist(methods=["POST"])
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
    return {"status": "deleted", "name": name}


# ──────────────────────────────────────────────────────────────────────
# save_my_native_layout — narrow, per-user revert to native
# ──────────────────────────────────────────────────────────────────────

NATIVE_PROFILE_PREFIX = "__native__"
# Step 1 of the resolver returns the first personal match in priority-desc
# order, so the sentinel must outrank any other personal row for this user.
NATIVE_PROFILE_PRIORITY = 1000


def _native_sections_json() -> str:
    """The sentinel payload: a valid v1 structure containing zero sections."""
    return json.dumps(
        {
            "version": 1,
            "unassigned_policy": "append",
            "unassigned_column_count": 2,
            "sections": [],
        }
    )


@frappe.whitelist(methods=["POST"])
def save_my_native_layout(doctype: str) -> dict:
    """
    Pin the CURRENT user's layout for ``doctype`` to the native Frappe layout.

    Deliberately narrow, in contrast to ``save_layout`` which stays
    System Manager only:

    * the target is always ``frappe.session.user`` — a caller cannot name
      another user, a role, or a default profile;
    * the payload is fixed to the empty-sections sentinel — there is no
      caller-supplied JSON to validate or to smuggle fields through;
    * the doctype must exist and the caller must hold read permission on it.

    An empty-sections profile wins resolution at Step 1 (personal), which is
    what displaces an active role/default profile, while the engine renders
    nothing for it — so the form is left exactly as Frappe built it.

    ``profile_name`` carries the user because the DocType autonames rows as
    ``{reference_doctype}-{profile_name}``; a bare ``__native__`` would collide
    on the primary key as soon as a second user reverted the same doctype.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    if not doctype or not frappe.db.exists("DocType", doctype):
        frappe.throw(_("Invalid document type."), frappe.ValidationError)

    if not frappe.has_permission(doctype, "read"):
        frappe.throw(
            _("You cannot set a layout for a document type you cannot read."),
            frappe.PermissionError,
        )

    if not frappe.db.has_column("Form Layout Profile", "for_user"):
        frappe.throw(
            _("Personal layouts are not available on this site yet."),
            frappe.ValidationError,
        )

    profile_name = f"{NATIVE_PROFILE_PREFIX}:{user}"

    # Revert means the user's own custom arrangement goes away: remove any
    # other personal row for this doctype so no stale sections can survive
    # alongside the sentinel. System-seeded rows are skipped — the shared
    # deletion guard forbids removing them and they were never this user's.
    for old_name in frappe.get_all(
        "Form Layout Profile",
        filters={
            "reference_doctype": doctype,
            "for_user": user,
            "profile_name": ("!=", profile_name),
        },
        pluck="name",
    ):
        if frappe.db.get_value("Form Layout Profile", old_name, "is_system"):
            continue
        frappe.delete_doc("Form Layout Profile", old_name, ignore_permissions=True)

    payload = _native_sections_json()
    existing = frappe.db.get_value(
        "Form Layout Profile",
        {
            "reference_doctype": doctype,
            "profile_name": profile_name,
            "for_user": user,
        },
        "name",
    )

    if existing:
        doc = frappe.get_doc("Form Layout Profile", existing)
        doc.sections_json = payload
        doc.enabled = 1
        doc.priority = NATIVE_PROFILE_PRIORITY
        doc.save(ignore_permissions=True)
        action = "updated"
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Form Layout Profile",
                "reference_doctype": doctype,
                "profile_name": profile_name,
                "for_user": user,
                "enabled": 1,
                "is_default": 0,
                "is_system": 0,
                "priority": NATIVE_PROFILE_PRIORITY,
                "layout_version": 1,
                "sections_json": payload,
            }
        )
        doc.insert(ignore_permissions=True)
        action = "created"

    return {"status": action, "name": doc.name, "profile_name": profile_name}


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


def _personal_profile_or_filters(user: str) -> list[list]:
    """Return explicit own-or-shared filters for privileged ``get_all`` reads."""
    return [
        ["for_user", "=", user],
        ["for_user", "is", "not set"],
        ["for_user", "=", ""],
    ]


def _may_inspect_foreign_personal_profiles(user: str) -> bool:
    """System managers may inspect profiles; this never changes resolver scope."""
    return user == "Administrator" or "System Manager" in frappe.get_roles(user)
