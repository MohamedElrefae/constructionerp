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
PROPOSAL = ROOT / "docs/translation/stage6_w606_crm_support_maintenance_proposal_2026-09-24.csv"
OUT = Path(__file__).resolve().parent
PASSWORD = sys.stdin.readline().rstrip("\n")
assert PASSWORD, "UAT password is required on stdin"
with PROPOSAL.open(encoding="utf-8", newline="") as handle:
    proposal = list(csv.DictReader(handle))
expected = {
    row["source_text"].strip(): row["proposed_ar"]
    for row in proposal
    if row["proposed_disposition"] in {"PROPOSED-payload", "preserved-site-override"}
}
excluded = [
    row["source_text"].strip()
    for row in proposal
    if row["proposed_disposition"] in {"DEFERRED-source-defect", "EXCEPTION-technical"}
]
assert len(expected) == 114
assert len(excluded) == 5
results = {
    "batch": "stage6-w606-crm-support-maintenance",
    "site": "v16.localhost",
    "scope_sha256": "a77b43a908859c0aea3e2c58525ec3765772c09af8617f1f17fb8c8bf12833f9",
    "proposal_sha256": "d8a2a8df2c040434b82d4d813f96e510e454b0f11114a31cf709db62bf60f266",
    "reviewed_proposal_sha256": "3d80277b516663b00f2240ed2d9476eef7eeb62803df867dbd029d74f0dcd354",
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
        extra_http_headers={"Accept-Language": "ar-SA,ar;q=0.9,en;q=0.5"},
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

    keys = list(expected)
    resolved = page.evaluate(
        """(keys)=>{const o={};for(const k of keys){try{o[k]=__(k);}catch(e){o[k]='ERR:'+e.message;}}return o;}""",
        keys,
    )
    mismatches = [
        {"source": key, "expected": expected[key], "got": resolved.get(key)}
        for key in keys
        if resolved.get(key) != expected[key]
    ]
    add(
        "all-payload-and-preserve-translations",
        not mismatches,
        {"matched": len(keys) - len(mismatches), "total": len(keys), "mismatches": mismatches[:10]},
    )

    boot_messages = page.evaluate(
        """(keys)=>{const m=(frappe.boot&&frappe.boot.__messages)||{};const o={};for(const k of keys)o[k]=m[k];return o;}""",
        keys,
    )
    boot_mismatches = [key for key in keys if boot_messages.get(key) != expected[key]]
    add(
        "boot-message-payload-exact",
        not boot_mismatches,
        {"matched": len(keys) - len(boot_mismatches), "total": len(keys), "mismatches": boot_mismatches[:10]},
    )

    excluded_hits = page.evaluate(
        """(keys)=>keys.filter(k => Object.prototype.hasOwnProperty.call((frappe.boot&&frappe.boot.__messages)||{}, k));""",
        excluded,
    )
    add("deferred-and-technical-absent", not excluded_hits, {"excluded": len(excluded), "unexpected": excluded_hits})

    body = page.locator("body").inner_text()
    words = sorted(set(re.findall(r"[؀-ۿ]{2,}", body)))
    add("rendered-dom-arabic", len(words) >= 5, {"count": len(words), "sample": words[:15]})
    add("no-page-errors", not page_errors, page_errors[:10])
    page.screenshot(path=str(OUT / "browser-ar-desk-w606-crm-support-maintenance.png"), full_page=False)
    add("desk-title-captured", bool(page.title()), page.title())
    page.goto(BASE + "/api/method/logout", wait_until="networkidle")
    add("logged-out", True, "logout endpoint hit")
    browser.close()

results["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
results["summary"] = {
    "pass": sum(1 for check in results["checks"] if check["ok"]),
    "fail": sum(1 for check in results["checks"] if not check["ok"]),
}
(OUT / "browser_evidence_w606_crm_support_maintenance.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("SUMMARY", results["summary"])
sys.exit(0 if results["summary"]["fail"] == 0 else 1)
