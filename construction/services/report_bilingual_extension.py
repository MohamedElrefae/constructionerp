"""Stage 4 report extension-point spike (engineering-only, read-only).

Construction-side extension for ERPNext financial reports. It proves that
Arabic / English / Both account-name rendering can be added for the General
Ledger, Trial Balance, Balance Sheet, and Profit & Loss reports WITHOUT
editing any vendor report file and WITHOUT mutating Account or translation
data.

Approach (the supported extension point): a Construction-side wrapper runs
the vendor report `execute` (a read-only function) and post-processes ONLY
the returned `columns`/`data` for the current session language — swapping
the account label cell for the account's Arabic name (from the governed
`Account.account_name_ar`) in Arabic/Both modes and leaving the English
identity for English mode. The source lists are never mutated (new
structures are returned).

No Report DocType, no vendor file, no Account/translation write occurs.
"""

from copy import deepcopy

# Per-report account-label boundary. GL/TB expose the account name under the
# `account` column; the financial statements (BS / P&L) surface it under
# `account` and `account_name`.
REPORT_LABEL_FIELDS = {
    "General Ledger": ["account"],
    "Trial Balance": ["account"],
    "Balance Sheet": ["account", "account_name"],
    "Profit and Loss Statement": ["account", "account_name"],
}

MODES = ("ar", "en", "both")


def normalize_mode(lang):
    text = str(lang or "").lower()
    if text == "both":
        return "both"
    return "ar" if text.startswith("ar") else "en"


def resolve_label(fieldname, columns):
    """Map a dict row's field key to a display column's label semantics."""
    return fieldname


def _translate_cell(value, mapping, mode):
    if mode == "en":
        return value
    arabic = mapping.get(str(value))
    if not arabic:
        return value
    if mode == "both":
        return "%s — %s" % (str(value), arabic)
    return arabic


def transform_report(columns, data, lang, mapping, label_fields):
    """Return (columns, data) with account labels localized for the mode.

    Pure: source `columns`/`data` are untouched; new structures returned.
    `mapping`: {english account_name: account_name_ar} from live metadata.
    """
    mode = normalize_mode(lang)
    label_fields = set(label_fields or [])
    new_columns = deepcopy(columns)
    new_data = deepcopy(data)

    for row in new_data:
        if isinstance(row, dict):
            for field in label_fields:
                if field in row and row.get(field) is not None:
                    row[field] = _translate_cell(row[field], mapping, mode)
        elif isinstance(row, (list, tuple)):
            # Columnar rows: translate the account column index, if known
            # (index resolved from columns fieldname == first label field).
            idx = None
            for i, col in enumerate(new_columns or []):
                if not isinstance(col, dict):
                    continue
                if (col.get("fieldname") or "").lower() in label_fields or (
                    str(col.get("label") or "").lower() in label_fields
                ):
                    idx = i
                    break
            if idx is not None and idx < len(row) and row[idx] is not None:
                row[idx] = _translate_cell(row[idx], mapping, mode)
    return new_columns, new_data


def load_account_arabic_mapping(company=None):
    """Read-only Account.account_name -> account_name_ar mapping (none yet)."""
    import frappe

    filters = {}
    if company:
        filters["company"] = company
    rows = frappe.get_all(
        "Account",
        filters=filters,
        fields=["account_name", "account_name_ar"],
        limit_page_length=0,
    )
    return {r.account_name: r.account_name_ar for r in rows if r.account_name_ar}


def bilingualize_report(execute, filters, lang, report_name, mapping=None):
    """Run a vendor report `execute` (read-only) and localize the account
    labels for `lang`. Returns (columns, data) — vendor data unchanged on
    disk; only the returned structures are localized."""
    columns, data = execute(filters=filters)
    label_fields = REPORT_LABEL_FIELDS.get(report_name) or ["account", "account_name"]
    mapping = mapping if mapping is not None else load_account_arabic_mapping(
        (filters or {}).get("company") if isinstance(filters, dict) else None
    )
    return transform_report(columns, data, lang, mapping, label_fields)


def rollback_note():
    """Engineering-only spike: revert by removing this module + its test
    module and running `git checkout --`/deleting the two new files. No
    Report DocType, vendor file, Account or translation data was changed, so
    there is nothing to migrate back."""
    return (
        "Report extension-point spike. No vendor report file edited; no "
        "Report DocType created; no Account or translation data mutated. "
        "Rollback = remove construction/services/report_bilingual_extension.py "
        "and construction/tests/test_stage4_report_extension.py (files are "
        "new/untracked). Nothing to reverse in the database."
    )
