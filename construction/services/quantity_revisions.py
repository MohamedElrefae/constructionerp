from contextlib import contextmanager
from contextvars import ContextVar

import frappe
from frappe import _
from frappe.utils import flt

from construction.services.boq_transactions import (
    current_boq_sql,
    lock_boq_header,
    lock_boq_item_header,
    read_boq_totals,
)

APPROVED_STATUS = "Approved"
_baseline_header = ContextVar("boq_baseline_header", default=None)
_new_projection = ContextVar("boq_new_approval_projection", default=None)


@contextmanager
def _baseline_creation(boq_header):
    token = _baseline_header.set(boq_header)
    try:
        yield
    finally:
        _baseline_header.reset(token)


def _is_baseline_creation(boq_header):
    return _baseline_header.get() == boq_header


def _project_new_approval(revision):
    """Called only by the document's first approval lifecycle, never an RPC."""
    token = _new_projection.set(revision.name)
    try:
        apply_approved_revision(revision)
    finally:
        _new_projection.reset(token)


def create_lock_baseline(boq_header):
    """Create baseline quantity revisions for all BOQ Items under a header.

    Idempotent: skips if Original Lock revisions already exist.
    """
    lock_boq_header(boq_header)
    # Check if baseline already exists by checking if any BOQ Item has last_quantity_revision
    existing = current_boq_sql(
        "SELECT name FROM `tabBOQ Item` WHERE boq_header = %s AND last_quantity_revision IS NOT NULL AND last_quantity_revision != '' LIMIT 1 FOR UPDATE NOWAIT",
        boq_header,
        as_dict=True,
    )

    if existing:
        return {"success": True, "message": "Baseline already exists.", "created": 0}

    items = current_boq_sql(
        "SELECT name, structure, quantity, contract_unit_price FROM `tabBOQ Item` WHERE boq_header = %s ORDER BY name FOR UPDATE NOWAIT",
        boq_header,
        as_dict=True,
    )

    if not items:
        frappe.log_error(f"No BOQ Items found for header {boq_header}", "create_lock_baseline")
        return {"success": False, "message": "No BOQ Items found", "created": 0}

    created = 0
    for item in items:
        # Check if this item already has a baseline revision
        existing = current_boq_sql(
            "SELECT name FROM `tabBOQ Quantity Revision` WHERE boq_item = %s AND revision_type = 'Original Lock' LIMIT 1 FOR UPDATE NOWAIT",
            item.name,
            as_dict=True,
        )
        if existing:
            continue

        # Set original and current quantities
        current_boq_sql(
            "UPDATE `tabBOQ Item` SET original_qty = %s, current_revised_qty = %s, current_revised_unit_price = %s WHERE name = %s",
            (item.quantity, item.quantity, item.contract_unit_price, item.name),
        )

        # Create baseline revision
        revision = frappe.get_doc(
            {
                "doctype": "BOQ Quantity Revision",
                "boq_header": boq_header,
                "boq_structure": item.structure,
                "boq_item": item.name,
                "revision_date": frappe.utils.nowdate(),
                "revision_type": "Original Lock",
                "previous_qty": 0,
                "revised_qty": item.quantity,
                "contract_unit_price": item.contract_unit_price,
                "revised_unit_price": item.contract_unit_price,
                "status": "Approved",
                "approved_by": frappe.session.user,
                "approved_on": frappe.utils.now(),
            }
        )
        with _baseline_creation(boq_header):
            revision.insert(ignore_permissions=True)

        # Link to BOQ Item
        current_boq_sql(
            "UPDATE `tabBOQ Item` SET last_quantity_revision = %s WHERE name = %s",
            (revision.name, item.name),
        )

        created += 1

    # Update BOQ Header totals
    update_boq_header_totals(boq_header)

    return {"success": True, "created": created}


def get_current_qty(boq_item):
    """Return the current approved quantity for a BOQ Item."""
    return flt(frappe.db.get_value("BOQ Item", boq_item, "current_revised_qty"))


def get_current_unit_price(boq_item):
    """Return the current approved unit price for a BOQ Item."""
    return flt(frappe.db.get_value("BOQ Item", boq_item, "current_revised_unit_price"))


def create_quantity_revision(
    boq_item,
    previous_qty,
    revised_qty,
    contract_unit_price,
    revised_unit_price,
    variation_order=None,
    reason=None,
    rate_change_justification=None,
    owner_refs=None,
    status="Draft",
):
    """Create a new BOQ Quantity Revision record.

    Returns the revision document.
    """
    item = frappe.db.get_value("BOQ Item", boq_item, ["boq_header", "structure"], as_dict=True)
    if not item:
        frappe.throw(_("BOQ Item {0} does not exist.").format(boq_item))

    revision = frappe.get_doc(
        {
            "doctype": "BOQ Quantity Revision",
            "boq_header": item.boq_header,
            "boq_structure": item.structure,
            "boq_item": boq_item,
            "variation_order": variation_order,
            "revision_date": frappe.utils.nowdate(),
            "revision_type": "Increase Within 25%",  # placeholder; compute_revision_type will overwrite
            "previous_qty": previous_qty,
            "revised_qty": revised_qty,
            "contract_unit_price": contract_unit_price,
            "revised_unit_price": revised_unit_price,
            "status": status,
            "reason": reason,
            "rate_change_justification": rate_change_justification,
        }
    )

    if owner_refs:
        revision.owner_page = owner_refs.get("owner_page")
        revision.owner_ref_no = owner_refs.get("owner_ref_no")
        revision.owner_file_ref = owner_refs.get("owner_file_ref")

    revision.insert(ignore_permissions=True)
    return revision


def approve_quantity_revision(revision_name):
    """Approve a quantity revision and apply it to the BOQ Item."""
    revision = frappe.get_doc("BOQ Quantity Revision", revision_name, for_update=True)

    if revision.status == "Approved":
        return {"success": True, "message": "Already approved."}

    revision.status = "Approved"
    revision.approved_by = frappe.session.user
    revision.approved_on = frappe.utils.now()
    revision.save(ignore_permissions=True)

    apply_approved_revision(revision)

    return {"success": True, "revision": revision.name}


def apply_approved_revision(revision):
    """Apply an approved revision to update BOQ Item current quantities.

    Uses DB row locking to prevent race conditions.
    """
    actual_header = lock_boq_item_header(revision.boq_item)
    if actual_header != revision.boq_header:
        frappe.throw(_("Revision BOQ Header does not match its item."))

    stored = current_boq_sql(
        """SELECT status, boq_item, boq_header, revised_qty, revised_unit_price
        FROM `tabBOQ Quantity Revision` WHERE name = %s FOR UPDATE NOWAIT""",
        revision.name,
        as_dict=True,
    )
    if not stored or stored[0].status != APPROVED_STATUS:
        frappe.throw(_("Only an approved revision can change current BOQ quantities."))
    evidence = stored[0]
    if evidence.boq_item != revision.boq_item or evidence.boq_header != actual_header:
        frappe.throw(_("Revision identity does not match its stored approval."))
    pointer = current_boq_sql(
        "SELECT last_quantity_revision FROM `tabBOQ Item` WHERE name = %s FOR UPDATE NOWAIT",
        revision.boq_item,
    )[0][0]
    if _new_projection.get() != revision.name:
        if pointer != revision.name:
            frappe.throw(_("Historical approval cannot be reapplied. Create a new correction revision."))
        return  # repeating the current approval is an idempotent no-op

    # Update current quantities
    frappe.db.set_value(
        "BOQ Item",
        revision.boq_item,
        {
            "current_revised_qty": evidence.revised_qty,
            "current_revised_unit_price": evidence.revised_unit_price,
            "last_quantity_revision": revision.name,
        },
        update_modified=False,
    )

    # Update BOQ Header totals
    update_boq_header_totals(revision.boq_header)


def create_variation_item_revision(
    boq_item, quantity, unit_price, variation_order, owner_refs=None, rate_change_justification=None
):
    """Shortcut for creating a New Variation Item revision.

    Creates an approved revision with previous_qty = 0.
    """
    return create_quantity_revision(
        boq_item=boq_item,
        previous_qty=0,
        revised_qty=quantity,
        contract_unit_price=0,
        revised_unit_price=unit_price,
        variation_order=variation_order,
        owner_refs=owner_refs,
        status="Approved",
        rate_change_justification=rate_change_justification,
    )


def update_boq_header_totals(boq_header):
    """Recompute BOQ Header total_revised_value from current items."""
    total_revised = read_boq_totals(boq_header)[3]
    frappe.db.set_value("BOQ Header", boq_header, "total_revised_value", total_revised, update_modified=False)


def process_approved_vo_lines(vo):
    """Process all VO lines atomically on Client Approval.

    Idempotent: skips lines that already have created_quantity_revision.
    Two-pass design + savepoint ensures NO partial approval survives an error.
    """
    from construction.construction.doctype.variation_order.variation_order import (
        create_variation_structure_and_item,
    )

    if frappe.session.user != "Administrator":
        frappe.has_permission("Variation Order", "write", doc=vo, throw=True)

    lock_boq_header(vo.boq_header)

    # Validate in display order, then lock distinct existing items by name.
    # Mutation order below still follows the approved lines.
    existing_items = set()
    for line in vo.lines:
        if line.created_quantity_revision:
            continue
        if line.line_type in ("Quantity Change", "Omission"):
            if not line.boq_item:
                frappe.throw(
                    _("Row {0}: Linked BOQ Item is required for {1}.").format(line.idx, line.line_type)
                )
            existing_items.add(line.boq_item)
    for item_name in sorted(existing_items):
        locked = current_boq_sql(
            "SELECT name, boq_header FROM `tabBOQ Item` WHERE name = %s FOR UPDATE NOWAIT",
            item_name,
            as_dict=True,
        )
        if not locked:
            frappe.throw(_("BOQ Item {0} not found.").format(item_name))
        if locked[0].boq_header != vo.boq_header:
            frappe.throw(_("Variation Order item belongs to another BOQ Header."))

    # --- PASS 2: Apply mutations inside savepoint ---
    save_point = f"vo_approval_{frappe.generate_hash(length=8)}"
    frappe.db.savepoint(save_point)

    try:
        for line in vo.lines:
            if line.created_quantity_revision:
                continue

            if line.line_type == "New Item":
                if line.created_quantity_revision:
                    continue

                if line.created_boq_item:
                    existing_rev = frappe.db.get_value(
                        "BOQ Quantity Revision",
                        {"variation_order": vo.name, "boq_item": line.created_boq_item},
                    )
                    if existing_rev:
                        line.db_set("created_quantity_revision", existing_rev, update_modified=False)
                        continue

                structure = create_variation_structure_and_item(vo, line)
                item_name = frappe.db.get_value("BOQ Item", {"structure": structure.name}, "name")

                frappe.db.set_value(
                    "BOQ Item",
                    item_name,
                    {
                        "original_qty": 0,
                        "current_revised_qty": line.revised_qty,
                        "current_revised_unit_price": line.revised_unit_price,
                    },
                    update_modified=False,
                )

                revision = create_variation_item_revision(
                    boq_item=item_name,
                    quantity=line.revised_qty,
                    unit_price=line.revised_unit_price,
                    variation_order=vo.name,
                    owner_refs={
                        "owner_page": line.owner_page,
                        "owner_ref_no": line.owner_ref_no,
                        "owner_file_ref": line.owner_file_ref,
                    },
                    rate_change_justification=line.rate_change_justification,
                )

                line.db_set("created_boq_structure", structure.name, update_modified=False)
                line.db_set("created_boq_item", item_name, update_modified=False)
                line.db_set("created_quantity_revision", revision.name, update_modified=False)

            elif line.line_type in ("Quantity Change", "Omission"):
                existing_rev = frappe.db.get_value(
                    "BOQ Quantity Revision", {"variation_order": vo.name, "boq_item": line.boq_item}
                )
                if existing_rev:
                    line.db_set("created_quantity_revision", existing_rev, update_modified=False)
                    continue

                actual = frappe.db.sql(
                    "SELECT current_revised_qty, current_revised_unit_price, original_qty FROM `tabBOQ Item` WHERE name = %s FOR UPDATE",
                    line.boq_item,
                    as_dict=True,
                )[0]

                revision = create_quantity_revision(
                    boq_item=line.boq_item,
                    previous_qty=actual.current_revised_qty,
                    revised_qty=line.revised_qty,
                    contract_unit_price=actual.current_revised_unit_price,
                    revised_unit_price=line.revised_unit_price,
                    variation_order=vo.name,
                    reason=line.notes,
                    rate_change_justification=line.rate_change_justification,
                    status="Approved",
                )

                apply_approved_revision(revision)
                line.db_set("created_quantity_revision", revision.name, update_modified=False)

        # Update BOQ Header totals for all line types
        update_boq_header_totals(vo.boq_header)

    except Exception as exc:
        frappe.db.rollback(save_point=save_point)
        frappe.log_error(f"VO approval aborted and rolled back: {str(exc)}", "VO Approval")
        raise

    return {"success": True}
