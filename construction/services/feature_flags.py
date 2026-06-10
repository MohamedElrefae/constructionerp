import frappe


IMPROVE_NOW_FLAGS = frozenset(
    {
        "enable_boq_excel_import_preview",
        "enable_boq_excel_import_commit",
        "enable_boq_wbs_resequence",
        "enable_stage_measurement_ui",
        "enable_boq_scope_registry",
        "enable_bilingual_boq_print",
        "enable_variation_orders",
    }
)


def is_enabled(flag_name: str) -> bool:
    """Return whether a known Construction Settings rollout flag is enabled."""
    if flag_name not in IMPROVE_NOW_FLAGS:
        frappe.throw(f"Unknown Construction Settings rollout flag: {flag_name}")

    return bool(frappe.db.get_single_value("Construction Settings", flag_name) or 0)


def set_flag(flag_name: str, value, *, commit: bool = False) -> None:
    """Set a known Construction Settings rollout flag to ``value`` (bool/int).

    Used by tests and smoke scripts that need to temporarily toggle a flag
    and restore it later. The caller manages the transaction boundary; pass
    ``commit=True`` only in smoke scripts that are not in a wrapped
    transaction.
    """
    if flag_name not in IMPROVE_NOW_FLAGS:
        frappe.throw(f"Unknown Construction Settings rollout flag: {flag_name}")

    frappe.db.set_single_value("Construction Settings", flag_name, 1 if value else 0)
    if commit:
        frappe.db.commit()


def get_flags() -> dict[str, bool]:
    """Return all Improve Now rollout flags as booleans."""
    return {flag_name: is_enabled(flag_name) for flag_name in sorted(IMPROVE_NOW_FLAGS)}
