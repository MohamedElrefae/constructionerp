"""
Form Layout Profile — DocType Controller
=========================================
Stores named layout profiles for the Form Layout Engine.
Each record holds a sections_json blob that the JS engine reads on every
form refresh to re-parent field wrappers into custom sections.

Validation rules (per HoE approval):
  1. Reject duplicate fieldname assignments within the same section.
  2. Skip/warn on unknown fieldnames (never crash the form).
  3. Block hiding required fields (shared profiles only; is_system override allowed).
  4. Unassigned fields auto-append at bottom (enforced by JS engine, not here).
  5. layout_version is mandatory — default 1.
  6. Only one is_default profile per reference_doctype (enforced here).
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document


class FormLayoutProfile(Document):
    # ------------------------------------------------------------------
    # Frappe lifecycle hooks
    # ------------------------------------------------------------------

    def validate(self):
        self._ensure_layout_version()
        self._validate_single_default()
        if self.sections_json:
            self._validate_sections_json()

    def before_insert(self):
        # System Manager only — enforced by DocType permissions.
        # Extra guard in case API is called directly.
        if frappe.session.user != "Administrator":
            if "System Manager" not in frappe.get_roles(frappe.session.user):
                frappe.throw(
                    _("Only System Manager can create Form Layout Profiles."),
                    frappe.PermissionError,
                )

    def on_trash(self):
        if self.is_system:
            frappe.throw(
                _("System-seeded profiles cannot be deleted. Disable them instead."),
                frappe.ValidationError,
            )

    # ------------------------------------------------------------------
    # Private validators
    # ------------------------------------------------------------------

    def _ensure_layout_version(self):
        if not self.layout_version:
            self.layout_version = 1

    def _validate_single_default(self):
        """Only one is_default profile is allowed per reference_doctype."""
        if not self.is_default:
            return
        existing = frappe.db.get_value(
            "Form Layout Profile",
            {
                "reference_doctype": self.reference_doctype,
                "is_default": 1,
                "name": ("!=", self.name or "__new__"),
                "enabled": 1,
            },
            "name",
        )
        if existing:
            frappe.throw(
                _(
                    "A default profile ({0}) already exists for {1}. " "Disable the existing default first."
                ).format(existing, self.reference_doctype),
                frappe.ValidationError,
            )

    def _validate_sections_json(self):
        """
        Validate the sections_json blob.
        Raises ValidationError on structural problems.
        Logs warnings for recoverable issues (unknown fields, duplicate fieldnames).
        """
        try:
            data = (
                json.loads(self.sections_json) if isinstance(self.sections_json, str) else self.sections_json
            )
        except json.JSONDecodeError as exc:
            frappe.throw(_("sections_json is not valid JSON: {0}").format(str(exc)))

        if not isinstance(data, dict):
            frappe.throw(_("sections_json must be a JSON object, not an array."))

        sections = data.get("sections", [])
        if not isinstance(sections, list):
            frappe.throw(_("sections_json.sections must be an array."))

        # Fetch real field metadata for the target DocType
        meta = frappe.get_meta(self.reference_doctype)
        known_fieldnames = {f.fieldname for f in meta.fields}
        required_fieldnames = {f.fieldname for f in meta.fields if f.reqd}

        seen_fieldnames: set[str] = set()
        errors: list[str] = []
        warnings: list[str] = []

        for sec in sections:
            col_count = sec.get("column_count", 2)
            if col_count not in (1, 2, 3):
                errors.append(
                    _("Section '{0}': column_count must be 1, 2, or 3 (got {1}).").format(
                        sec.get("label", sec.get("id", "?")), col_count
                    )
                )

            for fld in sec.get("fields", []):
                fn = fld.get("fieldname")
                if not fn:
                    errors.append(
                        _("A field entry in section '{0}' is missing 'fieldname'.").format(
                            sec.get("label", "?")
                        )
                    )
                    continue

                # Unknown field: warn, don't block save
                if fn not in known_fieldnames:
                    warnings.append(
                        _("Unknown fieldname '{0}' in section '{1}' — will be skipped at runtime.").format(
                            fn, sec.get("label", "?")
                        )
                    )
                    continue

                # Duplicate within layout
                if fn in seen_fieldnames:
                    errors.append(_("Fieldname '{0}' appears more than once in the layout.").format(fn))
                    continue
                seen_fieldnames.add(fn)

                # Block hiding required fields (shared profiles)
                if not fld.get("visible", True) and fn in required_fieldnames:
                    if not self.is_system:
                        errors.append(
                            _("Required field '{0}' cannot be hidden by a shared profile.").format(fn)
                        )

        if warnings:
            frappe.msgprint(
                "<br>".join(warnings),
                title=_("Form Layout Profile — Warnings"),
                indicator="orange",
            )

        if errors:
            frappe.throw("<br>".join(errors), frappe.ValidationError)
