"""Live read-only execution probe for the bilingual financial report surface.

Evidence for bilingual-financial-reports R4:
- every pilot report (General Ledger, Trial Balance, Accounts Receivable)
  executes through the governed endpoint in `ar` mode against real vendor
  modules, unmocked;
- the ar-mode label swap is demonstrated on live Trial Balance output
  (English run vs Arabic run, same filters);
- Account and GL Entry row counts are identical before and after, proving
  the whole path is read-only (no fixtures are created either).

Run:
  /home/mohamed/frappe-bench/env/bin/python \
      docs/ai/work-items/bilingual-financial-reports/evidence/scripts/probe_report_execution.py
"""

import json
import time

import frappe

COMPANY = "Elrefae"

FILTERS = {
    "General Ledger": {
        "company": COMPANY,
        "from_date": "2000-01-01",
        "to_date": "2100-12-31",
    },
    "Trial Balance": {"company": COMPANY},
    "Accounts Receivable": {
        "company": COMPANY,
        "report_date": None,  # filled with today()
        "ageing_based_on": "Posting Date",
        "party_type": "Customer",
        "group_by_party": True,
    },
}


def counts():
    return {
        "Account": frappe.db.count("Account"),
        "GL Entry": frappe.db.count("GL Entry"),
    }


def run_report(name, filters, mode):
    from construction.api.bilingual_reports import localized_report

    filters = {k: v for k, v in filters.items() if v is not None}
    start = time.perf_counter()
    out = localized_report(name, filters=json.dumps(filters), mode=mode)
    elapsed = (time.perf_counter() - start) * 1000.0
    return out, elapsed


def main():
    frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
    frappe.connect()
    frappe.set_user("Administrator")

    from construction.services.report_bilingual_extension import (
        load_account_arabic_mapping,
    )

    before = counts()
    print("COUNTS_BEFORE:", json.dumps(before))
    print("MAPPING_SIZE:", len(load_account_arabic_mapping(COMPANY)))

    ok = True
    for name, filters in FILTERS.items():
        f = dict(filters)
        if name == "Accounts Receivable":
            f["report_date"] = frappe.utils.today()
            f["to_date"] = frappe.utils.today()
        try:
            out, elapsed = run_report(name, f, "ar")
        except Exception as exc:  # noqa: BLE001 - probe must surface any failure
            print(f"REPORT {name}: FAIL {type(exc).__name__}: {exc}")
            ok = False
            continue
        cols, rows = out.get("columns"), out.get("data")
        good = isinstance(cols, list) and isinstance(rows, list)
        ok = ok and good
        print(
            f"REPORT {name}: {'OK' if good else 'BAD SHAPE'} mode={out.get('mode')} "
            f"columns={len(cols or [])} rows={len(rows or [])} ms={elapsed:.2f}"
        )

    tb_filters = dict(FILTERS["Trial Balance"])
    en_out, _ = run_report("Trial Balance", tb_filters, "en")
    ar_out, _ = run_report("Trial Balance", tb_filters, "ar")
    en_labels = [
        r.get("account") for r in en_out["data"] if isinstance(r, dict)
    ][:6]
    ar_labels = [
        r.get("account") for r in ar_out["data"] if isinstance(r, dict)
    ][:6]
    swapped = en_labels != ar_labels
    ok = ok and swapped
    print("TB_EN_LABELS:", json.dumps(en_labels, ensure_ascii=False))
    print("TB_AR_LABELS:", json.dumps(ar_labels, ensure_ascii=False))
    print("TB_AR_MODE_SWAPPED:", swapped)

    after = counts()
    mutation_free = before == after
    ok = ok and mutation_free
    print("COUNTS_AFTER:", json.dumps(after))
    print("MUTATION_GUARD:", "PASS" if mutation_free else "FAIL")
    print("PROBE RESULT:", "PASS" if ok else "FAIL")
    frappe.destroy()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
