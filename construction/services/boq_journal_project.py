"""Journal Entry BOQ project propagation (bounded F44 correction).

A Journal Entry Account row that carries a BOQ attribution (``boq_item``)
belongs to the project of the selected BOQ Header, but the native ERPNext
controller copies the ROW's ``project`` into the General Ledger entry
(``erpnext/accounts/doctype/journal_entry/journal_entry.py``: ``"project":
d.project``). A BOQ expense row saved with a blank row project therefore
produced a posted GL entry with ``project = NULL``: the cost was invisible in
the project-scoped General Ledger while the voucher itself stayed balanced
(100 debit / 100 credit).

This module derives the row project from the AUTHORITATIVE BOQ chain
(BOQ Item -> BOQ Header -> Project) during the save lifecycle, before the
General Ledger is built, and applies the company/scope boundary that the
wildcard scope hook applies to a parent ``project`` field. A Journal Entry has
NO parent ``project`` field, so ``construction/overrides/scope_enforcement.validate``
never saw the row project; this module performs that boundary check itself.

Deliberate limits of this correction:

* **Journal Entry only.** The shared BOQ validator
  (``construction/services/boq_transaction_validation.py``) and the other seven
  registered transaction DocTypes are untouched; every other doctype returns
  immediately.
* **Server only.** No client asset, endpoint, schema, report, role or
  permission change, and no new cash/expense allocation policy.
* **No history rewrite, no backfill of a stored NULL.** The historical
  exception is bound to the PERSISTED state of the row, never to the incoming
  client value (see "Which project wins" below).
* **The attribution predicate is a non-empty ``boq_item``.** The Journal Entry
  Direct/Indirect gate is NOT enforced by this module (it is not enforced
  server-side today), so a crafted row labelled ``Indirect`` that carries a BOQ
  item is attributed exactly like any other BOQ-bearing row. No Direct/Indirect
  gate is claimed to be added here.
* **The scope comparison reuses the existing scope semantics.** The active
  company/project boundary, the privileged/server lifecycle exemptions and the
  fail-closed configuration read come from
  ``construction/overrides/scope_enforcement.py`` and
  ``construction/services/scope_resolution.py``; no new scope semantics, no new
  bypass flag and no new role exemption are introduced.
* **No new translatable message.** Every message raised here is an existing
  entry of ``construction/locale/ar.po`` (the localization gate
  ``scripts/check_localization_gates.py`` requires every ``_()`` literal to be
  catalogued), so the correction adds no translation debt.

The scope-context setting (``enable_scope_context``) is INDEPENDENT of the BOQ
cascade setting: the cascade flag is a query-filter rollout switch and is never
used here as a document authorization decision.

Which project wins
------------------

The rule of this module is: **a BOQ-bearing Journal Entry row carries the
project of its BOQ Header**. The only question is what happens to a row that
already exists, and the answer is decided by the PERSISTED row, never by the
incoming client value alone:

* **A NEW or re-attributed row** (a new child row, a changed ``boq_item``, a
  copied or a foreign child identity): a blank incoming project is DERIVED
  from the authoritative BOQ project; an explicit matching value is kept; an
  explicit mismatching value is REFUSED.
* **An UNCHANGED, parent-bound historical row** (established by the real
  ``is_new_or_changed_attribution`` predicate, so a foreign or copied identity
  can never qualify):

  - the persisted project is NULL/empty: the row KEEPS its blank project. A
    pre-fix historical row is never silently backfilled: only an explicit
    client value equal to the authoritative project is kept, and a blank
    incoming value keeps the stored blank.
  - the persisted project equals the authoritative BOQ project and the
    incoming value is blank: the persisted project is RESTORED. A later draft
    save must never lose an already assigned project. The restored value is
    byte-identical to the stored one, so the stored row does not change.
  - the persisted project equals the authoritative BOQ project and the incoming
    value matches it: nothing changes.
  - the persisted project CONTRADICTS the authoritative BOQ project: the save
    is REFUSED with the project-mismatch message. A stale stored project is
    never silently cleared and never silently overwritten; an explicit
    incoming value that equals the authoritative project is accepted as an
    explicit (not silent) repair.
"""

import frappe
from frappe import _

from construction.overrides.scope_enforcement import (
    _enforce_referenced_project_scope,
    _in_system_install,
    _scope_enabled_or_fail_closed,
)
from construction.services.boq_accounting import is_new_or_changed_attribution
from construction.services.boq_lookups import get_header_for_item, get_project_for_header
from construction.services.boq_scope_registry import CHILD_TABLE_BY_DOCTYPE
from construction.services.scope_resolution import resolve_user_scope

JOURNAL_ENTRY_DOCTYPE = "Journal Entry"


def validate_document(doc, method=None):
    """Derive and validate the project of every BOQ-bearing Journal Entry row.

    Bound to the Journal Entry ``validate`` event AFTER
    ``construction.services.boq_transaction_validation.validate_document``, so
    the BOQ chain (``boq_header`` / ``boq_structure``) and the BOQ Header
    status are already normalized and validated by the shared validator, and
    BEFORE the wildcard scope hook, which never sees a Journal Entry row
    project.
    """
    if not doc or getattr(doc, "doctype", None) != JOURNAL_ENTRY_DOCTYPE:
        return

    table_field = CHILD_TABLE_BY_DOCTYPE.get(JOURNAL_ENTRY_DOCTYPE)
    if not table_field:
        return

    rows = _child_rows(doc, table_field)
    if not rows:
        return

    doc_company = _value(doc, "company")

    for row in rows:
        boq_item = _value(row, "boq_item")
        if not boq_item:
            # No BOQ attribution: the row keeps the native project behaviour
            # (for example the cash counterpart of a BOQ expense row).
            continue
        _apply_boq_project(row, doc, table_field, doc_company, boq_item)


def _apply_boq_project(row, doc, table_field, doc_company, boq_item):
    """Validate the authoritative BOQ project of one row and derive it when allowed."""
    idx = _value(row, "idx")

    boq_header = get_header_for_item(boq_item)
    # The header is read defensively: a BOQ Item without a header has no
    # authoritative project, and reading the project of an unnamed header would
    # pick an unrelated BOQ Header.
    boq_project = get_project_for_header(boq_header) if boq_header else None
    if not boq_project:
        frappe.throw(
            _("Row {0}: BOQ attribution is incomplete. Select a BOQ Item or clear the BOQ fields.").format(
                idx
            )
        )

    project_company = frappe.db.get_value("Project", boq_project, "company")
    if not doc_company:
        frappe.throw(_("Company is required."))
    if not project_company or project_company != doc_company:
        # An unreadable Project company is refused as well: the authority
        # cannot be verified, so the row is not attributed (fail closed).
        frappe.throw(_("Project '{0}' does not belong to Company '{1}'").format(boq_project, doc_company))

    row_project = _value(row, "project")
    if row_project and row_project != boq_project:
        frappe.throw(
            _("Row {0}: Project mismatch. Transaction: {1}, BOQ: {2}").format(idx, row_project, boq_project)
        )

    _enforce_active_scope(boq_project)

    if is_new_or_changed_attribution(row, doc, table_field):
        # A NEW or re-attributed row may receive the authoritative project.
        # A copied or a foreign child identity never reaches this branch as an
        # unchanged historical row.
        if not row_project:
            row.project = boq_project
        return

    # The row is an UNCHANGED, parent-bound historical row. From here the
    # PERSISTED project decides; the incoming client value is only accepted
    # when it matches the authoritative project.
    stored_project = _stored_row_project(row)

    if stored_project and stored_project != boq_project:
        # The persisted project contradicts the authoritative BOQ project (for
        # example the BOQ Header's project changed after the row was written).
        # The stale value is neither silently cleared nor silently overwritten:
        # the save is refused, unless the client explicitly supplied the
        # authoritative project, which is an explicit repair.
        if not (row_project and row_project == boq_project):
            frappe.throw(
                _("Row {0}: Project mismatch. Transaction: {1}, BOQ: {2}").format(
                    idx, stored_project, boq_project
                )
            )
        return

    if not stored_project:
        # A pre-fix historical row with a NULL project keeps it: no backfill,
        # no history rewrite. An explicit matching client value is kept.
        return

    if not row_project:
        # The stored project equals the authoritative one, but the incoming
        # value is blank: the assigned project is restored instead of being
        # lost. The restored value is the value that is already stored, so the
        # persisted row is not rewritten.
        row.project = stored_project


def _stored_row_project(row):
    """The PERSISTED project of an unchanged historical row.

    This read happens ONLY after ``is_new_or_changed_attribution`` established
    that the row is an unchanged, parent-bound historical row of THIS
    document: the stored row must exist, must belong to this parent and must
    carry the same BOQ Item. A client-supplied name, a caller-supplied flag or
    a foreign child identity therefore can never reach this read.
    """
    row_doctype = _value(row, "doctype")
    row_name = _value(row, "name")
    if not row_doctype or not row_name:
        return None
    return frappe.db.get_value(row_doctype, row_name, "project")


def _enforce_active_scope(boq_project):
    """Apply the active company/project boundary to the authoritative BOQ project.

    Mirrors ``construction.overrides.scope_enforcement.validate``:

    * a configuration read failure fails CLOSED;
    * the scope comparison is skipped for a system install/migration/patch, for
      the service-only bypass token, for a disabled scope context, for
      ``Administrator`` and for a ``System Manager`` (the existing privileged
      and server-lifecycle exemptions);
    * a ``Guest`` session and an ordinary user without an active scope context
      (or without an active scope company) are refused;
    * a project-scoped active scope requires the BOQ project to EQUAL the scope
      project, and a company-only active scope requires the Project's own
      authoritative company to match the scope company.

    The document-company integrity rule is NOT part of this comparison: it is
    enforced for every caller in ``_apply_boq_project`` and is never skipped.
    """
    if _in_system_install():
        return

    if getattr(frappe.flags, "construction_scope_bypass", False):
        return

    if not _scope_enabled_or_fail_closed():
        return

    user = frappe.session.user
    if user == "Administrator":
        return

    if user == "Guest":
        frappe.throw(
            _("Scope enforcement is active: Guest sessions cannot modify scoped documents."),
            frappe.PermissionError,
        )

    if "System Manager" in frappe.get_roles():
        return

    scope = resolve_user_scope(user)
    if not scope or not scope.company:
        frappe.throw(
            _(
                "Scope enforcement is active: An active User Scope Context is required to create or modify scoped documents."
            ),
            frappe.PermissionError,
        )

    _enforce_referenced_project_scope(scope, [boq_project])


def _child_rows(doc, table_field):
    """The child rows of the document (Frappe ``get`` semantics)."""
    return _value(doc, table_field) or []


def _value(container, key):
    """Read a field from a Frappe document/row or from a plain mapping."""
    if hasattr(container, "get"):
        return container.get(key)
    return getattr(container, key, None)
