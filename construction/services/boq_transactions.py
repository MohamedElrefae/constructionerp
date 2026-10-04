"""Transaction guards for maintained BOQ aggregates on MariaDB.

Frappe can lock a document before its controller runs. Consequently waiting
for a header after locking a child can deadlock another child writer. Header
and aggregate locks after child acquisition never wait: contention aborts the
whole operation. New structure insertion locks the header first and may wait
at most five seconds, preserving serialized concurrent WBS generation.
FOR UPDATE also makes aggregate reads current under REPEATABLE READ; a parent
lock alone does not refresh a transaction's earlier consistent-read snapshot.
"""

import frappe
from frappe import _


def current_boq_sql(query, values, **kwargs):
    """Execute an explicit current locking read; prevent partial commits on failure."""
    try:
        return frappe.db.sql(query, values, **kwargs)
    except (frappe.QueryTimeoutError, frappe.QueryDeadlockError) as exc:
        database = frappe.db

        # Some older services catch errors and return a result. A savepoint
        # rollback is insufficient after a lock failure or server deadlock.
        # Keep refusing commit until the caller rolls back the whole transaction.
        # Register again because CallbackManager removes a callback before run.
        def refuse_partial_commit():
            database.before_commit.add(refuse_partial_commit)
            frappe.throw(
                _("BOQ changed concurrently. Roll back and retry the complete operation."),
                frappe.QueryTimeoutError,
            )

        database.before_commit.add(refuse_partial_commit)
        raise frappe.QueryTimeoutError(
            _("This BOQ is being changed by another user. Retry the complete operation.")
        ) from exc


def lock_boq_header(boq_header, *, before_insert=False):
    """Serialize writers of one BOQ; locks last until the caller commits/rolls back."""
    if not boq_header:
        return None
    query = "SELECT name, status FROM `tabBOQ Header` WHERE name = %s FOR UPDATE NOWAIT"
    if before_insert:
        # Fixed SQL, not a user-supplied wait clause. Called before a new
        # structure's naming, sibling locks, child creation and persistence.
        query = "SELECT name, status FROM `tabBOQ Header` WHERE name = %s FOR UPDATE WAIT 5"
    rows = current_boq_sql(
        query,
        boq_header,
        as_dict=True,
    )
    if not rows:
        frappe.throw(_("BOQ Header {0} does not exist.").format(boq_header), frappe.DoesNotExistError)
    return rows[0]


def lock_boq_item_header(boq_item):
    """Use the current item's actual header for lifecycle-bypassing service writes."""
    rows = current_boq_sql(
        "SELECT name, boq_header FROM `tabBOQ Item` WHERE name = %s FOR UPDATE NOWAIT",
        boq_item,
        as_dict=True,
    )
    if not rows:
        frappe.throw(_("BOQ Item {0} does not exist.").format(boq_item), frappe.DoesNotExistError)
    lock_boq_header(rows[0].boq_header)
    return rows[0].boq_header


def read_boq_totals(boq_header):
    """Read authoritative totals, including our own writes and current committed rows.

    The header guard excludes cooperating writers. The locking range read also
    protects the item set from phantoms until transaction end. SQL arithmetic and
    the existing variation/docstatus policy are preserved; G04/G06 need owner rules.
    """
    lock_boq_header(boq_header)
    return current_boq_sql(
        """
        SELECT
            COALESCE(SUM(CASE WHEN is_variation_item = 0 THEN line_total ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN is_variation_item = 0 THEN est_line_total ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN is_variation_item = 0
                THEN quantity * est_unit_cost * COALESCE(factor, 1.0) ELSE 0 END), 0),
            COALESCE(SUM(COALESCE(current_revised_qty, quantity) *
                COALESCE(current_revised_unit_price, contract_unit_price) * COALESCE(factor, 1.0)), 0)
        FROM `tabBOQ Item`
        WHERE boq_header = %s
        FOR UPDATE NOWAIT
        """,
        boq_header,
    )[0]
