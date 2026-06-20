from __future__ import annotations

from dataclasses import dataclass

import frappe

from construction.services.boq_scope_filters import ALLOWED_TRANSACTION_BOQ_STATUSES
from construction.services.feature_flags import is_enabled


@dataclass(frozen=True)
class BOQTransactionScopeRule:
    doctype: str
    child_table: str
    child_doctype: str
    gate_field: str | None = None
    gate_value: object | None = None


SUPPORTED_TRANSACTION_RULES: tuple[BOQTransactionScopeRule, ...] = (
    BOQTransactionScopeRule("Purchase Order", "items", "Purchase Order Item", "expense_category", "Direct"),
    BOQTransactionScopeRule(
        "Purchase Receipt", "items", "Purchase Receipt Item", "expense_category", "Direct"
    ),
    BOQTransactionScopeRule(
        "Purchase Invoice", "items", "Purchase Invoice Item", "expense_category", "Direct"
    ),
    BOQTransactionScopeRule("Sales Invoice", "items", "Sales Invoice Item", "is_progress_billing", 1),
    BOQTransactionScopeRule("Stock Entry", "items", "Stock Entry Detail", "expense_category", "Direct"),
    BOQTransactionScopeRule("Timesheet", "time_logs", "Timesheet Detail", "designation"),
    BOQTransactionScopeRule(
        "Journal Entry", "accounts", "Journal Entry Account", "expense_category", "Direct"
    ),
    BOQTransactionScopeRule(
        "Material Request", "items", "Material Request Item", "expense_category", "Direct"
    ),
)

SUPPORTED_TRANSACTION_DOCTYPES = tuple(rule.doctype for rule in SUPPORTED_TRANSACTION_RULES)
CHILD_TABLE_BY_DOCTYPE = {rule.doctype: rule.child_table for rule in SUPPORTED_TRANSACTION_RULES}
CHILD_DOCTYPE_BY_PARENT = {rule.doctype: rule.child_doctype for rule in SUPPORTED_TRANSACTION_RULES}


def get_transaction_scope_rule(doctype: str) -> BOQTransactionScopeRule | None:
    for rule in SUPPORTED_TRANSACTION_RULES:
        if rule.doctype == doctype:
            return rule
    return None


def is_scope_registry_enabled() -> bool:
    return is_enabled("enable_boq_scope_registry")


def get_supported_transaction_matrix() -> list[dict]:
    return [
        {
            "doctype": rule.doctype,
            "child_table": rule.child_table,
            "child_doctype": rule.child_doctype,
            "gate_field": rule.gate_field,
            "gate_value": rule.gate_value,
            "allowed_boq_statuses": list(ALLOWED_TRANSACTION_BOQ_STATUSES),
        }
        for rule in SUPPORTED_TRANSACTION_RULES
    ]


def supports_boq_transaction_scope(doctype: str) -> bool:
    return get_transaction_scope_rule(doctype) is not None


def has_boq_scope_fields(doctype: str) -> bool:
    try:
        meta = frappe.get_meta(doctype, cached=False)
    except Exception:
        return False
    return all(meta.has_field(fieldname) for fieldname in _boq_scope_fieldnames())


def _boq_scope_fieldnames() -> tuple[str, ...]:
    return ("boq_header", "boq_structure", "boq_item", "boq_item_stage")
