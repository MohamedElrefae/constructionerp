"""Scope context resolution helpers for BOQ cascade filtering."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

import frappe


@dataclass(frozen=True)
class ScopeContext:
    user: str
    company: Optional[str] = None
    cost_center: Optional[str] = None
    project: Optional[str] = None
    modified: Optional[str] = None

    @property
    def is_empty(self):
        return not any((self.company, self.cost_center, self.project))

    @property
    def scope_type(self):
        if self.project:
            return "Project-Scoped"
        if self.company or self.cost_center:
            return "Company-CostCenter-Scoped"
        return None


def get_boq_cascade_mode():
    """Return BOQ cascade rollout mode; fail closed to Off during migrations."""
    try:
        return frappe.db.get_single_value("Construction Settings", "enable_boq_cascade_filtering") or "Off"
    except Exception:
        return "Off"


def is_boq_cascade_enabled(mode=None):
    return (mode or get_boq_cascade_mode()) in {"On", "Strict"}


def resolve_user_scope(user=None):
    """Read the active user scope context as a small immutable object."""
    user = user or frappe.session.user
    if not frappe.db.exists("DocType", "User Scope Context"):
        return ScopeContext(user=user)

    scope = frappe.db.get_value(
        "User Scope Context",
        {"user": user},
        ["company", "cost_center", "project", "modified"],
        as_dict=True,
    )
    if not scope:
        return ScopeContext(user=user)

    return ScopeContext(
        user=user,
        company=scope.company,
        cost_center=scope.cost_center,
        project=scope.project,
        modified=str(scope.modified) if scope.modified else None,
    )


def get_scope_token(user=None):
    """Return a deterministic token representing the user's active scope."""
    scope = resolve_user_scope(user)
    if scope.is_empty and not scope.modified:
        return None

    payload = "|".join(
        [
            scope.company or "",
            scope.cost_center or "",
            scope.project or "",
            scope.modified or "",
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def get_cost_center_descendants(cost_center):
    """Return selected cost center plus descendants for nested-set filtering."""
    if not cost_center or not frappe.db.exists("DocType", "Cost Center"):
        return []
    if not frappe.db.exists("Cost Center", cost_center):
        return [cost_center]

    bounds = frappe.db.get_value("Cost Center", cost_center, ["lft", "rgt"], as_dict=True)
    if not bounds or bounds.lft is None or bounds.rgt is None:
        return [cost_center]

    return frappe.get_all(
        "Cost Center",
        filters={"lft": [">=", bounds.lft], "rgt": ["<=", bounds.rgt]},
        pluck="name",
        order_by="lft asc",
    )


def should_enforce_scope(enforce_scope=None):
    """Resolve caller override against rollout mode."""
    if isinstance(enforce_scope, str):
        enforce_scope = enforce_scope.lower() not in {"0", "false", "no", "off"}
    if enforce_scope is not None:
        if enforce_scope is False and is_boq_cascade_enabled():
            frappe.logger("boq_scope").warning(
                {
                    "event": "boq_scope_enforcement_bypassed",
                    "user": frappe.session.user,
                    "mode": get_boq_cascade_mode(),
                }
            )
        return bool(enforce_scope)
    return is_boq_cascade_enabled()
