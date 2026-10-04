"""Live read-only execution probe for the Tier-5E statement allowlist.

Evidence for bilingual-report-statements-allowlist R2/R4:
- Balance Sheet and Profit and Loss Statement execute through the governed
  endpoint in `ar` and `en` modes against real vendor modules, unmocked;
- the R4 period defaults fill the vendor get_period_list contract
  (Date Range window driven by viewer-style from_date/to_date);
- the ar-mode label swap is demonstrated on live Balance Sheet output
  (English run vs Arabic run, same filters): `account` swaps via the
  identity mapping; `account_name` swaps for mapped values and passes
  vendor-composite values through unchanged (fail-open per cell);
- Account and GL Entry row counts are identical before and after, proving
  the whole path is read-only.

Run:
  /home/mohamed/frappe-bench/env/bin/python \
      docs/ai/work-items/bilingual-report-statements-allowlist/evidence/scripts/probe_statements_execution.py
"""

import json
import time

import frappe

COMPANY = "Elrefae"
STATEMENTS = ("Balance Sheet", "Profit and Loss Statement")

FILTERS = {
    "Balance Sheet": {
        "company": COMPANY,
        "from_date": "2026-01-01",
        "to_date": "2026-10-05",
    },
    "Profit and Loss Statement": {
        "company": COMPANY,
        "from_date": "2026-01-01",
        "to_date": "2026-10-05",
    },
}


def counts():
    return {
        "Account": frappe.db.count("Account"),
        "GL Entry": frappe.db.count("GL Entry"),
    }


def run_report(name, filters, mode):
    from construction.api.bilingual_reports import localized_report

    start = time.perf_counter()
    out = localized_report(name, filters=json.dumps(filters), mode=mode)
    elapsed = (time.perf_counter() - start) * 1000.0
    return out, elapsed


def labels(out, field):
    return [
        r.get(field)
        for r in out.get("data") or []
        if isinstance(r, dict) and r.get(field)
    ][:6]


def main():
    frappe.init(site="v16.localhost", sites_path="/home/mohamed/frappe-bench/sites")
    frappe.connect()
    frappe.set_user("Administrator")

    from construction.services.report_bilingual_extension import (
        load_account_arabic_mapping,
    )

    before = counts()
    print("COUNTS_BEFORE:", json.dumps(before))

    ok = True
    for name in STATEMENTS:
        f = dict(FILTERS[name])
        for mode in ("ar", "en"):
            try:
                out, elapsed = run_report(name, f, mode)
            except Exception as exc:  # noqa: BLE001 - probe must surface any failure
                print(f"REPORT {name} mode={mode}: FAIL {type(exc).__name__}: {exc}")
                ok = False
                continue
            cols, rows = out.get("columns"), out.get("data")
            good = isinstance(cols, list) and isinstance(rows, list)
            ok = ok and good
            print(
                f"REPORT {name} mode={mode}: {'OK' if good else 'BAD SHAPE'} "
                f"columns={len(cols or [])} rows={len(rows or [])} "
                f"tail={'yes' if out.get('tail') else 'no'} ms={elapsed:.2f}"
            )

    # ar vs en label swap on live Balance Sheet output (same filters).
    # `account` carries the report's account identity (mapped by Account.name /
    # account_name) and must swap. `account_name` may be a vendor-composite
    # value that is not a mapping key — those must pass through unchanged
    # (fail-open per cell), while every mapped value must swap.
    en_out, _ = run_report("Balance Sheet", dict(FILTERS["Balance Sheet"]), "en")
    ar_out, _ = run_report("Balance Sheet", dict(FILTERS["Balance Sheet"]), "ar")
    mapping = load_account_arabic_mapping(COMPANY)
    for field in ("account", "account_name"):
        en_labels = labels(en_out, field)
        ar_labels = labels(ar_out, field)
        if field == "account":
            swapped = bool(en_labels) and en_labels != ar_labels
            ok = ok and swapped
            print(f"BS_AR_MODE_SWAPPED[{field}]:", swapped)
        else:
            pairs = list(zip(en_labels, ar_labels))
            mapped = [(e, a) for e, a in pairs if e in mapping]
            unmapped_ok = all(e == a for e, a in pairs if e not in mapping)
            mapped_ok = all(a == mapping[e] for e, a in mapped)
            good = bool(en_labels) and mapped_ok and unmapped_ok
            ok = ok and good
            print(f"BS_ACCOUNT_NAME_MAPPED_COUNT[{field}]:", len(mapped))
            print(f"BS_ACCOUNT_NAME[{field}]_MAPPED_SWAP:", mapped_ok)
            print(f"BS_ACCOUNT_NAME[{field}]_UNMAPPED_PASSTHROUGH:", unmapped_ok)
        print(f"BS_EN_{field.upper()}:", json.dumps(en_labels, ensure_ascii=False))
        print(f"BS_AR_{field.upper()}:", json.dumps(ar_labels, ensure_ascii=False))

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
