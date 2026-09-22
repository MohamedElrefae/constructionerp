#!/usr/bin/env python3
"""W6-0b batch-3 Arabic browser evidence (headless, ar Desk session)."""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://v16.localhost:8000"
OUT = Path(__file__).resolve().parent
PASSWORD = "ct-w60b-evidence-1"

PROBES = {
    "Workspace Visibility": "ظهور مساحة العمل",
    "API Keys": "مفاتيح واجهة برمجة التطبيقات (API)",
    "Allow Bulk Editing": "السماح بالتحرير الجماعي",
    "Amended Documents": "المستندات المُعدَّلة",
    "Bad Cron Expression": "تعبير Cron غير صالح",
    "Workspace Settings": "إعدادات مساحة العمل",
    "Show sidebar": "إظهار الشريط الجانبي",
    "Workspace Manager": "مدير مساحة العمل",
    "Active Directory": "دليل Active Directory",
    "Module (for Export)": "الوحدة (للتصدير)",
}
PLACEHOLDER_SRC = "Cannot {0} {1}."
PLACEHOLDER_EXP = "لا يمكن delete item."

results = {
    "batch": "stage6-w60b-batch3",
    "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "site": "v16.localhost",
    "checks": [],
}

def add(name, ok, detail):
    results["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + ": " + str(detail)[:220], flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(BASE + "/login", wait_until="networkidle")
    page.fill("#login_email", "Administrator")
    page.fill("#login_password", PASSWORD)
    page.click(".btn-login")
    page.wait_for_timeout(3500)
    page.goto(BASE + "/app", wait_until="networkidle")
    page.wait_for_timeout(3000)

    boot = page.evaluate(
        """() => { const b=window.frappe&&frappe.boot?frappe.boot:{}; return {lang:b.lang, messages_len:b.__messages?Object.keys(b.__messages).length:0}; }"""
    )
    add("boot-lang-ar", boot.get("lang") == "ar", boot.get("lang"))
    add("boot-messages-ge-1000", (boot.get("messages_len") or 0) >= 1000, boot.get("messages_len"))

    resolved = page.evaluate(
        """(keys)=>{const o={};for(const k of keys){try{o[k]=__(k);}catch(e){o[k]='ERR:'+e.message;}}return o;}""",
        list(PROBES.keys()),
    )
    all_ok = True
    for k, exp in PROBES.items():
        got = resolved.get(k)
        ok = (got == exp)
        all_ok = all_ok and ok
        add("translate:" + k, ok, {"expected": exp, "got": got})
    add(
        "all-probe-translations",
        all_ok,
        f"{sum(1 for k in PROBES if resolved.get(k) == PROBES[k])}/{len(PROBES)}",
    )

    ph_got = page.evaluate(
        """(src)=>{try{return __(src,['delete', 'item']);}catch(e){return 'ERR:'+e.message;}}""",
        PLACEHOLDER_SRC,
    )
    add("translate-placeholder", ph_got == PLACEHOLDER_EXP, {"expected": PLACEHOLDER_EXP, "got": ph_got})

    boot_lookup = page.evaluate(
        """(keys)=>{const m=(frappe.boot&&frappe.boot.__messages)||{};const o={};for(const k of keys)o[k]=m[k];return o;}""",
        list(PROBES.keys()),
    )
    add(
        "boot-messages-lookup",
        all(boot_lookup.get(k) == v for k, v in PROBES.items()),
        {k: boot_lookup.get(k) for k in list(PROBES)[:4]},
    )

    page.wait_for_timeout(1500)
    body = page.locator("body").inner_text()
    uniq = sorted(set(re.findall(r"[\u0600-\u06FF]{2,}", body)))
    add("rendered-dom-arabic-words", len(uniq) >= 5, {"count": len(uniq), "sample": uniq[:20]})
    module_hits = [w for w in ["الأدوات", "المحاسبة", "المشتريات", "المشاريع", "المخزون", "البيع"] if w in body]
    add("rendered-workspace-modules", len(module_hits) >= 3, module_hits)
    try:
        side = [
            t.strip()
            for t in page.locator(".standard-sidebar-item").all_inner_texts()
            if t and any("\u0600" <= ch <= "\u06FF" for ch in t)
        ]
    except Exception:
        side = []
    add("sidebar-arabic-items", len(side) >= 1, side[:8])
    page.screenshot(path=str(OUT / "browser-ar-desk-batch03.png"), full_page=False)
    add("desk-title-captured", bool(page.title()), page.title())

    results["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results["summary"] = {
        "pass": sum(1 for c in results["checks"] if c["ok"]),
        "fail": sum(1 for c in results["checks"] if not c["ok"]),
    }
    browser.close()

(OUT / "browser_evidence_batch03.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
)
print("SUMMARY", results["summary"])
sys.exit(0 if results["summary"]["fail"] == 0 else 1)
