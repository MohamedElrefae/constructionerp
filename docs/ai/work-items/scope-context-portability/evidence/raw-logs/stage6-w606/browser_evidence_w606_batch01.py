#!/usr/bin/env python3
"""Headless Arabic Desk verification for W6-6 assets batch; password via stdin."""
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
PROPOSAL = ROOT / "docs/translation/stage6_w606_proposal_2026-09-24.csv"
OUT = Path(__file__).resolve().parent
PASSWORD = sys.stdin.readline().rstrip("\n")
assert PASSWORD, "UAT password is required on stdin"

with PROPOSAL.open(encoding="utf-8", newline="") as fh:
    expected = {
        row["source_text"].strip(): row["proposed_ar"]
        for row in csv.DictReader(fh)
        if row["proposed_disposition"] in {"PROPOSED-payload", "preserved-site-override"}
    }
assert len(expected) == 211, len(expected)

results = {
    "batch": "stage6-w606-assets",
    "site": "v16.localhost",
    "scope_sha256": "6f142646ae55cf147751e8d751f10638c79420dfa184855985ecd6068ee63a40",
    "proposal_sha256": "521f1eb620b6c403f3cce91fd4ec280f86ad46f427ae6c1e194199c0242762ab",
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

    body = page.locator("body").inner_text()
    words = sorted(set(re.findall(r"[\u0600-\u06ff]{2,}", body)))
    add("rendered-dom-arabic", len(words) >= 5, {"count": len(words), "sample": words[:15]})
    add("no-page-errors", not page_errors, page_errors[:10])
    page.screenshot(path=str(OUT / "browser-ar-desk-w606-batch01.png"), full_page=False)
    add("desk-title-captured", bool(page.title()), page.title())

    page.goto(BASE + "/api/method/logout", wait_until="networkidle")
    add("logged-out", True, "logout endpoint hit")
    browser.close()

results["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
(OUT / "browser_evidence_w606_batch01.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print("browser evidence wrote:", OUT / "browser_evidence_w606_batch01.json")
