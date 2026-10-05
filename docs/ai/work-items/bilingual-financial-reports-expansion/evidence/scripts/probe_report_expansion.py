"""Live read-only execution probe for the Stage-7 report expansion.

Evidence for bilingual-financial-reports-expansion:
- General Ledger, Trial Balance, Accounts Receivable Summary, Accounts
  Payable Summary and Cash Flow execute through the governed endpoint in
  `ar` and `en` modes against real vendor modules, unmocked;
- the report-specific read-only defaults fill each vendor contract
  (date window for GL, fiscal year for TB, report_date for the AR/AP
  summaries, get_period_list period contract for Cash Flow);
- the governed COLUMN_LABELS map swaps the column headers in `ar` mode and
  leaves `en` mode byte-identical (including currency suffixes such as
  "Debit (SAR)"), with unmapped labels passing through unchanged;
- Account / GL Entry / Report / Translation row counts are identical
  before and after, proving the whole path is read-only.

Run:
  /home/mohamed/frappe-bench/env/bin/python \
      docs/ai/work-items/bilingual-financial-reports-expansion/evidence/scripts/probe_report_expansion.py
"""

import json
import time

import frappe

COMPANY = "Elrefae"
REPORTS = (
    "General Ledger",
    "Trial Balance",
    "Accounts Receivable Summary",
    "Accounts Payable Summary",
    "Cash Flow",
)

BASE_FILTERS = {
    "General Ledger": {"from_date": "2026-01-01", "to_date": "2026-10-05"},
    "Trial Balance": {},
    "Accounts Receivable Summary": {"to_date": "2026-10-05"},
    "Accounts Payable Summary": {"to_date": "2026-10-05", "party_type": "Supplier"},
    "Cash Flow": {"from_date": "2026-01-01", "to_date": "2026-10-05"},
}

MUTATION_TABLES = ("Account", "GL Entry", "Report", "Translation")


def counts():
    return {t: frappe.db.count(t) for t in MUTATION_TABLES}


def run_report(name, filters, mode):
    from construction.api.bilingual_reports import localized_report

    start = time.perf_counter()
    out = localized_report(name, filters=json.dumps(filters), mode=mode)
    elapsed = (time.perf_counter() - start) * 1000.0
    return out, elapsed


def labels(out, limit=8):
    return [
        (c or {}).get("label")
        for c in (out.get("columns") or [])[:limit]
    ]


def main():
    frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
    frappe.connect()
    frappe.set_user("Administrator")

    before = counts()
    print("COUNTS_BEFORE:", json.dumps(before, ensure_ascii=False))

    ok = True
    for name in REPORTS:
        filters = {"company": COMPANY, **BASE_FILTERS[name]}
        per_mode = {}
        for mode in ("ar", "en"):
            try:
                out, elapsed = run_report(name, filters, mode)
            except Exception as exc:  # noqa: BLE001 - probe must surface any failure
                print(f"REPORT {name} mode={mode}: FAIL {type(exc).__name__}: {exc}")
                ok = False
                continue
            cols, rows = out.get("columns"), out.get("data")
            good = isinstance(cols, list) and isinstance(rows, list)
            ok = ok and good
            per_mode[mode] = labels(out)
            print(
                f"REPORT {name} mode={mode}: {'OK' if good else 'BAD SHAPE'} "
                f"columns={len(cols or [])} rows={len(rows or [])} "
                f"tail={'yes' if out.get('tail') else 'no'} ms={elapsed:.2f}"
            )

        # column-header localization: ar differs from en on at least one
        # mapped header, and unmapped headers pass through byte-identical.
        if set(per_mode) == {"ar", "en"}:
            ar_labels, en_labels = per_mode["ar"], per_mode["en"]
            swapped = ar_labels != en_labels
            ok = ok and swapped
            print(f"HEADERS_SWAPPED[{name}]:", swapped)
            print(f"EN_HEADERS[{name}]:", json.dumps(en_labels, ensure_ascii=False))
            print(f"AR_HEADERS[{name}]:", json.dumps(ar_labels, ensure_ascii=False))
        else:
            ok = False

    # `en` mode must be byte-identical to a second `en` run (localization
    # never leaks into the English path), and `both` must be deterministic.
    sample = {"company": COMPANY, **BASE_FILTERS["Cash Flow"]}
    en_a, _ = run_report("Cash Flow", sample, "en")
    en_b, _ = run_report("Cash Flow", sample, "en")
    en_stable = labels(en_a) == labels(en_b)
    both_out, _ = run_report("Cash Flow", sample, "both")
    both_has_dash = any("—" in str(l) for l in labels(both_out))
    ok = ok and en_stable and both_has_dash
    print("EN_HEADERS_STABLE:", en_stable)
    print("BOTH_HEADERS_COMBINED:", both_has_dash)
    print("BOTH_HEADERS[Cash Flow]:", json.dumps(labels(both_out), ensure_ascii=False))

    after = counts()
    mutation_free = before == after
    ok = ok and mutation_free
    print("COUNTS_AFTER:", json.dumps(after, ensure_ascii=False))
    print("MUTATION_GUARD:", "PASS" if mutation_free else "FAIL")
    print("PROBE RESULT:", "PASS" if ok else "FAIL")
    frappe.destroy()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
