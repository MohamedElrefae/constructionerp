#!/usr/bin/env python3
"""Playwright headless browser verification for Stage 6 W6-7 Frappe Framework Remainder Batch 02."""
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://v16.localhost:8000"
ROOT = Path(__file__).resolve().parents[7]
SCOPE_CSV = ROOT / "docs/translation/stage6_w607_frappe_batch02_rows_2026-09-27.csv"
PROPOSAL = ROOT / "docs/translation/stage6_w607_frappe_batch02_proposal_2026-09-27.csv"
APPLIED = ROOT / "docs/translation/stage6_w607_frappe_batch02_payload_applied_rows_2026-09-27.csv"
RELEASED_TXT = ROOT / "docs/translation/stage6_w607_frappe_batch02_released_list_2026-09-27.txt"
OUT = Path(__file__).resolve().parent

PASSWORD = sys.stdin.readline().rstrip("\n")
assert PASSWORD, "UAT password is required on stdin"

with APPLIED.open(encoding="utf-8", newline="") as handle:
    applied = list(csv.DictReader(handle))

released_keys = set(RELEASED_TXT.read_text(encoding="utf-8").splitlines())

expected = {
    row["source_text"].strip(): {
        "translation": row["final_translation"].strip(),
        "context": (row.get("context") or "").strip(),
    }
    for row in applied
    if row.get("final_translation", "").strip()
}

results = {
    "batch": "stage6-w607-frappe-batch02",
    "site": "v16.localhost",
    "scope_sha256": "cd6536bc0cb0b9db14214e55500ebadf3a525b2a1250147b9ad9b402e1e70be3",
    "proposal_sha256": "ec58c9c43f6708ae821e1eee404fd2207d4b5d65d323c14f14d93a7c69555b4a",
    "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "checks": [],
}


def add(name, ok, detail):
    results["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + ": " + str(detail)[:220], flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(
        viewport={"width": 1400, "height": 900},
        locale="ar-SA",
        extra_http_headers={
            "Accept-Language": "ar-SA,ar;q=0.9,en;q=0.5",
        },
    )
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    page.goto(BASE + "/login", wait_until="networkidle")
    page.fill("#login_email", "Administrator")
    page.fill("#login_password", PASSWORD)
    page.click(".btn-login")
    page.wait_for_timeout(2500)
    page.goto(BASE + "/app", wait_until="networkidle")
    page.wait_for_timeout(2500)

    boot = page.evaluate(
        """() => { const b=window.frappe&&frappe.boot?frappe.boot:{}; return {lang:b.lang, messages_len:b.__messages?Object.keys(b.__messages).length:0}; }"""
    )
    add("boot-lang-ar", boot.get("lang") == "ar", boot.get("lang"))
    add("boot-messages-ge-1000", (boot.get("messages_len") or 0) >= 1000, boot.get("messages_len"))

    # Check released payload keys (243 keys)
    rel_items = [
        {"source": key, "context": expected[key]["context"]}
        for key in released_keys
    ]
    resolved_rel = page.evaluate(
        """(items)=>{const o={};for(const it of items){try{o[it.source]=it.context ? __(it.source, null, it.context) : __(it.source);}catch(e){o[it.source]='ERR:'+e.message;}}return o;}""",
        rel_items,
    )
    rel_mismatches = [
        {"source": item["source"], "expected": expected[item["source"]]["translation"], "got": resolved_rel.get(item["source"])}
        for item in rel_items
        if resolved_rel.get(item["source"]) != expected[item["source"]]["translation"]
    ]
    add(
        "all-released-payload-translations",
        not rel_mismatches,
        {"matched": len(rel_items) - len(rel_mismatches), "total": len(rel_items), "mismatches": rel_mismatches[:10]},
    )

    # Check all translated batch keys in runtime (243 keys, excluding 1 technical exception)
    all_items = [
        {"source": key, "context": expected[key]["context"]}
        for key in expected.keys()
    ]
    resolved_all = page.evaluate(
        """(items)=>{const o={};for(const it of items){try{o[it.source]=it.context ? __(it.source, null, it.context) : __(it.source);}catch(e){o[it.source]='ERR:'+e.message;}}return o;}""",
        all_items,
    )
    all_mismatches = [
        {"source": item["source"], "expected": expected[item["source"]]["translation"], "got": resolved_all.get(item["source"])}
        for item in all_items
        if resolved_all.get(item["source"]) != expected[item["source"]]["translation"]
    ]
    add(
        "all-batch-keys-resolved",
        not all_mismatches,
        {"matched": len(all_items) - len(all_mismatches), "total": len(all_items), "mismatches": all_mismatches[:10]},
    )

    # Check that technical exception rows are NOT in released list
    tech_keys = [
        '{0} ${skip_list ? "" : type}',
    ]
    tech_absent = all(k not in released_keys for k in tech_keys)
    add("technical-exceptions-excluded-from-released", tech_absent, {"tech_keys": tech_keys})

    # Page errors
    add("no-page-errors", len(page_errors) == 0, {"errors": page_errors})

    # Screenshot
    png_path = OUT / "browser-ar-desk-w607-frappe-batch02.png"
    page.screenshot(path=str(png_path), full_page=False)
    add("screenshot-captured", png_path.exists(), str(png_path))

    browser.close()

results["ended_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
results["all_passed"] = all(c["ok"] for c in results["checks"])

json_path = OUT / "browser_evidence_w607_batch02.json"
json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote browser evidence to {json_path}")
print(f"Overall status: {'PASS' if results['all_passed'] else 'FAIL'}")
if not results["all_passed"]:
    sys.exit(1)
