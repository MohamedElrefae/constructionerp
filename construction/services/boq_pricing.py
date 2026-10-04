"""Owner-approved tender pricing: percentages share the direct-cost base."""

import math

import frappe
from frappe import _

PRICING_RULE = "additive-direct-cost/v1"
PERCENT_FIELDS = ("overhead_pct", "profit_pct", "tender_tax_pct")


def number(value, label, *, minimum=0, maximum=None, positive=False):
    try:
        result = float(value if value not in (None, "") else 0)
    except (TypeError, ValueError, OverflowError):
        frappe.throw(_("{0} must be a valid number.").format(label))
    if not math.isfinite(result) or result < minimum or (positive and result <= 0):
        frappe.throw(
            _("{0} must be finite and {1}.").format(
                label, _("greater than zero") if positive else _("non-negative")
            )
        )
    if maximum is not None and result > maximum:
        frappe.throw(_("{0} must not exceed {1}.").format(label, maximum))
    return result


def positive_factor(value):
    # Only missing factors use the documented default; explicit zero is invalid.
    return number(1 if value in (None, "") else value, _("Factor"), positive=True)


def tender_amounts(cost, overhead=0, profit=0, tax=0):
    cost = number(cost, _("Direct unit cost"))
    rates = [
        number(v, label, maximum=100)
        for v, label in (
            (overhead, _("Overhead percentage")),
            (profit, _("Profit percentage")),
            (tax, _("Tender tax allowance percentage")),
        )
    ]
    amounts = [cost * rate / 100 for rate in rates]
    sell = number(cost + sum(amounts), _("Suggested selling rate"))
    return (*amounts, sell)
