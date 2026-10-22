"""Test bootstrap guard for DocTypes owned by uninstalled apps.

Context: ERPNext v16 moved ``Payment Gateway`` (and related payment DocTypes)
into the standalone ``payments`` app. On sites that intentionally do NOT
install ``payments``, erpnext still ships ``Payment Gateway Account`` with a
Link field targeting the now-missing ``Payment Gateway`` DocType.

Frappe's test-record generator
(``frappe.tests.utils.generators.get_missing_records_doctypes``) walks Link
dependencies depth-first and raises ``DoesNotExistError`` when it reaches a
missing DocType, which aborts the WHOLE test bootstrap before any test runs.

This guard wraps the generator so missing DocTypes are skipped (with a
one-time warning) instead of crashing the run. It only patches test
infrastructure — the function is never called outside test runners — and is
applied from ``construction/tests/__init__.py``, which the standard runner
imports before preloading test records.

Explicitly NOT installed here (deliberate scope decision, 2026-08-19):
the ``payments`` app. Payment gateway functionality is out of scope for
this project; this guard exists purely so unrelated suites stay runnable.
"""

import frappe

_warned_missing_doctypes: set[str] = set()

_SKIP_HINT = (
    "construction.test_bootstrap_guard: skipping test-record generation for "
    "missing DocType {doctype!r} (owned by an app that is not installed on "
    "this site, e.g. 'payments'). This is a skip, not an error."
)


def apply_test_generator_guard():
    """Patch the test-record generator to skip missing DocTypes.

    Idempotent: safe to call multiple times.
    """
    from frappe.tests.utils import generators

    if getattr(generators.get_missing_records_doctypes, "_construction_guard", False):
        return

    original = generators.get_missing_records_doctypes

    def guarded_get_missing_records_doctypes(doctype, visited=None):
        try:
            return original(doctype, visited=visited)
        except frappe.DoesNotExistError:
            if doctype not in _warned_missing_doctypes:
                _warned_missing_doctypes.add(doctype)
                frappe.logger("tests").warning(_SKIP_HINT.format(doctype=doctype))
            return []

    guarded_get_missing_records_doctypes._construction_guard = True
    generators.get_missing_records_doctypes = guarded_get_missing_records_doctypes
