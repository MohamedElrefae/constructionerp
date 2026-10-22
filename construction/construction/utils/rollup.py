"""Nest-safe deferred BOQ rollup control.

For a large batch (import, bulk reprice, bulk item creation) the app must be
able to suppress the per-document header rollup that ``BOQ Item`` /
``BOQ Structure`` ``on_update`` triggers, and instead run ONE rollup at the end
of the batch. The old pattern toggled ``frappe.flags.defer_boq_rollups``
directly (``= True`` ... ``= False``), which is NOT nest-safe: an inner caller
that needs a live rollup cannot restore the outer state, and an exception can
leave the flag stuck.

This module provides a nest-safe context manager that saves the previous value,
sets the flag on entry and restores it in ``finally`` on exit.
"""

import contextlib

import frappe

FLAG = "defer_boq_rollups"


def rollups_deferred() -> bool:
    """True when the current request has deferred BOQ rollups."""
    return bool(getattr(frappe.flags, FLAG, False))


@contextlib.contextmanager
def defer_boq_rollups():
    """Context manager that defers BOQ rollups with nest-safe restoration.

    Usage::

        with defer_boq_rollups():
            ... bulk insert items/structures ...

        # rollup runs once, here, at transaction end
    """
    prev = getattr(frappe.flags, FLAG, False)
    frappe.flags[FLAG] = True
    try:
        yield
    finally:
        if prev:
            frappe.flags[FLAG] = True
        else:
            frappe.flags[FLAG] = False


__all__ = ["FLAG", "defer_boq_rollups", "rollups_deferred"]
