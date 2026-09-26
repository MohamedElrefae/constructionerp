#!/usr/bin/env python3
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://v16.localhost:8000"
ROOT = Path(__file__).resolve().parents[7]
SCOPE_CSV = ROOT / "docs/translation/stage6_w601_accounts_batch01_rows_2026-09-24.csv"
PROPOSAL = ROOT / "docs/translation/stage6_w601_accounts_batch01_proposal_2026-09-24.csv"
APPLIED = ROOT / "docs/translation/stage6_w601_accounts_batch01_payload_applied_rows_2026-09-26.csv"
RELEASED_TXT = ROOT / "docs/translation/stage6_w601_accounts_batch01_released_list_2026-09-26.txt"
OUT = Path(__file__).resolve().parent

PASSWORD = sys.stdin.readline().rstrip("\n")
assert PASSWORD, "UAT password is required on stdin"

with APPLIED.open(encoding="utf-8", newline="") as handle:
    applied = list(csv.DictReader(handle))

released_keys = set(RELEASED_TXT.read_text(encoding="utf-8").splitlines())

expected = {
    row["source_text"].strip(): row["translated_text"].strip()
    for row in applied
}

results = {
    "batch": "stage6-w601-accounts-batch01",
    "site": "v16.localhost",
    "scope_sha256": "4910a9e4a0e5f8dd0105d484171ac1dc68e173220a0bed27520fbfc5e8c090fd",
    "proposal_sha256": "226ff8b158a4a17bca77209d2e452fff9eff75fd6479324f3e020e6b24ab2b4e",
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

    # Check released payload keys
    rel_keys = list(released_keys)
    resolved_rel = page.evaluate(
        """(keys)=>{const o={};for(const k of keys){try{o[k]=__(k);}catch(e){o[k]='ERR:'+e.message;}}return o;}""",
        rel_keys,
    )
    rel_mismatches = [
        {"source": key, "expected": expected[key], "got": resolved_rel.get(key)}
        for key in rel_keys
        if resolved_rel.get(key) != expected[key]
    ]
    add(
        "all-released-payload-translations",
        not rel_mismatches,
        {"matched": len(rel_keys) - len(rel_mismatches), "total": len(rel_keys), "mismatches": rel_mismatches[:10]},
    )

    # Check all 250 batch keys in runtime
    all_keys = list(expected.keys())
    resolved_all = page.evaluate(
        """(keys)=>{const o={};for(const k of keys){try{o[k]=__(k);}catch(e){o[k]='ERR:'+e.message;}}return o;}""",
        all_keys,
    )
    all_mismatches = [
        {"source": key, "expected": expected[key], "got": resolved_all.get(key)}
        for key in all_keys
        if resolved_all.get(key) != expected[key]
    ]
    add(
        "all-batch-keys-translations",
        not all_mismatches,
        {"matched": len(all_keys) - len(all_mismatches), "total": len(all_keys), "mismatches": all_mismatches[:10]},
    )

    body = page.locator("body").inner_text()
    words = sorted(set(re.findall(r"[\u0600-\u06ff]{2,}", body)))
    add("rendered-dom-arabic", len(words) >= 5, {"count": len(words), "sample": words[:15]})
    add("no-page-errors", not page_errors, page_errors[:10])
    page.screenshot(path=str(OUT / "browser-ar-desk-w601-accounts-batch01.png"), full_page=False)
    add("desk-title-captured", bool(page.title()), page.title())
    page.goto(BASE + "/api/method/logout", wait_until="networkidle")
    add("logged-out", True, "logout endpoint hit")
    browser.close()

results["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
results["summary"] = {
    "pass": sum(1 for check in results["checks"] if check["ok"]),
    "fail": sum(1 for check in results["checks"] if not check["ok"]),
}
(OUT / "browser_evidence_w601_batch01.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("SUMMARY", results["summary"])
sys.exit(0 if results["summary"]["fail"] == 0 else 1)
