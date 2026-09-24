#!/usr/bin/env python3
"""Headless Arabic Desk verification for W6-6 Manufacturing Batch 01; password via stdin."""
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
PROPOSAL = ROOT / "docs/translation/stage6_w606_manufacturing_batch01_proposal_2026-09-24.csv"
OUT = Path(__file__).resolve().parent
PASSWORD = sys.stdin.readline().rstrip("\n")
assert PASSWORD, "UAT password is required on stdin"

with PROPOSAL.open(encoding="utf-8", newline="") as fh:
    expected = {
        row["source_text"].strip(): row["proposed_ar"]
        for row in csv.DictReader(fh)
        if row["proposed_disposition"] in {"PROPOSED-payload", "preserved-site-override"}
    }
assert len(expected) == 250, len(expected)

results = {
    "batch": "stage6-w606-manufacturing-batch01",
    "site": "v16.localhost",
    "scope_sha256": "0d5098f61e2f97d26fa40e4e8b5d3b90ab1ec22e9dafd543564cb07ec8d39286",
    "proposal_sha256": "d64adaa6f9d6d201623dfbd4156dd414c000abd389d3864643994aba3bbfdfb9",
    "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "lookup_note": "Runtime import strips only edge whitespace from source keys; translated values retain exact reviewed edge whitespace.",
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

    boot_lang = page.evaluate("() => (window.frappe && frappe.boot && frappe.boot.lang) || ''")
    add("boot-lang-ar", boot_lang == "ar", boot_lang)

    msg_count = page.evaluate(
        "() => (window.frappe && frappe.boot && frappe.boot.__messages && Object.keys(frappe.boot.__messages).length) || 0"
    )
    add("boot-messages-ge-1000", msg_count >= 1000, msg_count)

    boot_messages = page.evaluate(
        "() => (window.frappe && frappe.boot && frappe.boot.__messages) || {}"
    )
    exact_matches: list[str] = []
    mismatches: list[dict[str, str]] = []
    for src, expected_ar in expected.items():
        actual = boot_messages.get(src)
        if actual == expected_ar:
            exact_matches.append(src)
        else:
            mismatches.append({"source": src, "expected": expected_ar, "actual": actual or ""})

    add(
        "all-payload-and-preserve-translations",
        len(mismatches) == 0,
        {"total": len(expected), "matched": len(exact_matches), "mismatches": mismatches},
    )
    add(
        "boot-message-payload-exact",
        len(exact_matches) == len(expected),
        {"total": len(expected), "matched": len(exact_matches), "mismatches": mismatches[:5]},
    )

    page.screenshot(path=str(OUT / "browser-ar-desk-w606-mfg-batch01.png"))
    dom_text = page.inner_text("body")
    arabic_words = sorted({w for w in re.findall(r"[\u0600-\u06FF]{3,}", dom_text)})
    add(
        "rendered-dom-arabic",
        len(arabic_words) >= 5,
        {"count": len(arabic_words), "sample": arabic_words[:15]},
    )
    add("no-page-errors", len(page_errors) == 0, page_errors)

    title = page.title()
    add("desk-title-captured", bool(title), title)

    page.goto(BASE + "/api/method/logout", wait_until="networkidle")
    add("logged-out", True, "logout endpoint hit")

    browser.close()

results["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
(OUT / "browser_evidence_w606_mfg_batch01.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print("Saved browser evidence JSON to", OUT / "browser_evidence_w606_mfg_batch01.json")
