#!/usr/bin/env python3
"""Headless real Desk verification for W6-3 batch-02; password via stdin."""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://v16.localhost:8000"
ROOT = Path(__file__).resolve().parents[7]
PROPOSAL = ROOT / "docs/translation/stage6_w603_proposal_batch02_2026-09-23.csv"
OUT = Path(__file__).resolve().parent
PASSWORD = sys.stdin.readline().rstrip("\n")
assert PASSWORD, "UAT password is required on stdin"

with PROPOSAL.open(encoding="utf-8", newline="") as fh:
    expected = {
        row["source_text"]: row["proposed_ar"]
        for row in csv.DictReader(fh)
        if row["proposed_disposition"] in {"PROPOSED-payload", "preserved-site-override"}
    }
assert len(expected) == 246, len(expected)

results = {
    "batch": "stage6-w603-batch02",
    "site": "v16.localhost",
    "proposal_sha256": "aaac0e04b364f63e55dcfbd59bd72a19156952523f500226cb919aa387a8349e",
    "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "checks": [],
}


def add(name: str, ok: bool, detail: object) -> None:
    results["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + ": " + str(detail)[:200], flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(
        viewport={"width": 1400, "height": 900},
        locale="ar-SA",
        extra_http_headers={"Accept-Language": "ar-SA,ar;q=0.9,en;q=0.5"},
    )
    page_errors: list[str] = []
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
    add("all-payload-and-preserve-translations", not mismatches, {"matched": len(keys)-len(mismatches), "total": len(keys), "mismatches": mismatches[:10]})

    boot_messages = page.evaluate(
        """(keys)=>{const m=(frappe.boot&&frappe.boot.__messages)||{};const o={};for(const k of keys)o[k]=m[k];return o;}""",
        keys,
    )
    boot_mismatches = [key for key in keys if boot_messages.get(key) != expected[key]]
    add("boot-message-payload-exact", not boot_mismatches, {"matched": len(keys)-len(boot_mismatches), "total": len(keys), "mismatches": boot_mismatches[:10]})

    body = page.locator("body").inner_text()
    words = sorted(set(re.findall(r"[؀-ۿ]{2,}", body)))
    add("rendered-dom-arabic", len(words) >= 5, {"count": len(words), "sample": words[:15]})
    add("no-page-errors", not page_errors, page_errors[:10])
    page.screenshot(path=str(OUT / "browser-ar-desk-w603-batch02.png"), full_page=False)
    add("desk-title-captured", bool(page.title()), page.title())
    try:
        page.evaluate("fetch('/api/method/logout',{method:'POST',credentials:'same-origin'})")
    except Exception as exc:  # server session still expires if endpoint is unreachable
        add("logout-request", False, type(exc).__name__)
    else:
        add("logout-request", True, "POST /api/method/logout")
    browser.close()

results["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
results["summary"] = {
    "pass": sum(1 for check in results["checks"] if check["ok"]),
    "fail": sum(1 for check in results["checks"] if not check["ok"]),
}
(OUT / "browser_evidence_w603_batch02.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
)
print("SUMMARY", results["summary"])
sys.exit(0 if results["summary"]["fail"] == 0 else 1)
