#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://v16.localhost:8000"
OUT = Path(__file__).resolve().parent
PASSWORD = "ct-w60x-evidence-1"
PROBES = {
    "% of materials delivered against this Pick List": "% o نسبة المواد المسلمة مقابل قائمة الانتقاء هذه",
    "A Packing Slip can only be created for Draft Delivery Note.": "يمكن إنشاء سند التعبئة فقط لإذن التسليم المبدئي.",
    "A Price List is a collection of Item Prices either Selling, Buying, or both": "قائمة الأسعار هي مجموعة أسعار أصناف للبيع أو الشراء أو كليهما",
    "A driver must be set to submit.": "يجب تحديد السائق قبل الإرسال.",
    "All items have already been received": "تم استلام جميع الأصناف بالفعل",
    "At least one warehouse is mandatory": "مستودع واحد على الأقل إلزامي",
    "Batch Nos are created successfully": "تم إنشاء أرقام الدفعات بنجاح",
    "Distinct Item and Warehouse": "صنف ومستودع مميزين",
    "Get stops from": "الحصول على المحطات من",
    "Have Default Naming Series for Batch ID?": "هل توجد سلسلة تسمية افتراضية لمعرف الدفعة؟",
    "Here are the options to proceed:": "هذه خيارات المتابعة:",
    "In Transit Warehouse": "مستودع قيد العبور",
}
PLACEHOLDER_SRC = "Finished Item {0} does not match with Work Order {1}"
PLACEHOLDER_EXP = "الصنف النهائي X لا يتطابق بأمر العمل Y"
results = {
    "batch": "stage6-w603-batch01",
    "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "site": "v16.localhost",
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
    for key, expected in PROBES.items():
        got = resolved.get(key)
        ok = got == expected
        all_ok = all_ok and ok
        add("translate:" + key, ok, {"expected": expected, "got": got})
    add(
        "all-probe-translations",
        all_ok,
        f"{sum(1 for key in PROBES if resolved.get(key) == PROBES[key])}/{len(PROBES)}",
    )

    placeholder = page.evaluate(
        """(src)=>{try{return __(src,['X','Y']);}catch(e){return 'ERR:'+e.message;}}""",
        PLACEHOLDER_SRC,
    )
    add("translate-placeholder", placeholder == PLACEHOLDER_EXP, {"expected": PLACEHOLDER_EXP, "got": placeholder})

    boot_lookup = page.evaluate(
        """(keys)=>{const m=(frappe.boot&&frappe.boot.__messages)||{};const o={};for(const k of keys)o[k]=m[k];return o;}""",
        list(PROBES.keys()),
    )
    add(
        "boot-messages-lookup",
        all(boot_lookup.get(key) == value for key, value in PROBES.items()),
        {key: boot_lookup.get(key) for key in list(PROBES)[:4]},
    )

    page.wait_for_timeout(1500)
    body = page.locator("body").inner_text()
    words = sorted(set(re.findall(r"[؀-ۿ]{2,}", body)))
    add("rendered-dom-arabic-words", len(words) >= 5, {"count": len(words), "sample": words[:20]})
    modules = [word for word in ["الأدوات", "المحاسبة", "المشتريات", "المشاريع", "المخزون", "البيع"] if word in body]
    add("rendered-workspace-modules", len(modules) >= 3, modules)
    try:
        sidebar = [
            text.strip()
            for text in page.locator(".standard-sidebar-item").all_inner_texts()
            if text and any("؀" <= char <= "ۿ" for char in text)
        ]
    except Exception:
        sidebar = []
    add("sidebar-arabic-items", len(sidebar) >= 1, sidebar[:8])
    page.screenshot(path=str(OUT / "browser-ar-desk-w603-batch01.png"), full_page=False)
    add("desk-title-captured", bool(page.title()), page.title())

    results["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results["summary"] = {
        "pass": sum(1 for check in results["checks"] if check["ok"]),
        "fail": sum(1 for check in results["checks"] if not check["ok"]),
    }
    browser.close()

(OUT / "browser_evidence_w603_batch01.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
)
print("SUMMARY", results["summary"])
sys.exit(0 if results["summary"]["fail"] == 0 else 1)
