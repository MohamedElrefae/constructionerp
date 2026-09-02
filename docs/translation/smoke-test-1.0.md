# Smoke Test 1.0 — Fresh Arabic Session

**Date:** 2026-09-02 12:50 Africa/Cairo
**Tester:** Technical Owner — Construction ERP
**Environment:** v16.localhost, Frappe 16.18.1 (81aadb9), ERPNext 16.18.3, Construction a21b587
**User:** Arabic user `test_arabic@example.com` (language `ar`, role System Manager for verification, then restricted user)

## Pre-Conditions
- `bench --site v16.localhost clear-cache` — translation, boot, website, site caches cleared
- `bench --site v16.localhost clear-website-cache`
- `bench --site v16.localhost restart` (web and worker restarted, Redis 13000/11000 active)
- Browser: new incognito session, language `ar`, hard refresh Ctrl+F5

## Health Verification
```bash
bench --site v16.localhost execute construction.translation_service.assert_translation_health
# Result: OK — loader true, no duplicates/nulls, constraint_present true (ct_translation_key_digest UNIQUE), has_drift false, last_drift_checked_at 2026-09-02 12:35:56
bench --site v16.localhost execute construction.translation_service.import_released_overrides --kwargs '{"dry_run": true}'
# Result: total 28, created 0, updated 0, skipped 28, drift 0
```

## Screen Verification (screenshots on file, described)

### Frappe
- **Login / Desk:** `تسجيل الدخول` renders correctly, no `طفل`
- **Treeview (Cost Center):** `إضافة فرع` appears for Add Child, not `إضافة طفل`
- **List View:** `حفظ وترحيل` for Save and Submit, `ترحيل` for Submit (generic, flagged for context review)

### ERPNext
- **Chart of Accounts:** `دليل الحسابات` (singular, not `مخطط الحسابات`)
- **Cost Center:** `مركز التكلفة`
- **Payment Entry:** List `سند قبض / سند صرف` (dual voucher), detail shows `سند قبض` / `سند صرف` as applicable
- **Journal Entry:** `قيد يومية` (singular)

### Construction
- **BOQ Header/Structure/Item:** `جدول الكميات`, `أمر تغيير` (Variation Order), `تكلفة تجهيز الموقع` (Mobilization)
- **Retention:** `محتجزات ضمان` appears for retention fields, not `الاحتفاظ`
- **Subcontracting:** `مقاول باطن`, `مقاولات الباطن`, `عقد مقاولات باطن` — no `التصنيع بالعقد`
- **Progress Billing:** `مستخلص جاري`, `مستخلص` (Payment Certificate)
- **WIP:** Construction WIP `أعمال تحت التنفيذ` vs Manufacturing WIP `إنتاج تحت التشغيل` (verified via glossary)

## Cache Verification
- After import, `bench --site v16.localhost execute "frappe.cache.hget('user_translations', 'ar')"` returns 28 packaged keys
- `bootinfo` contains Arabic translations without catalog mirrors
- New browser session after hard refresh shows same values (no stale boot cache)

## Result
**PASS** — All representative screens show approved Arabic without forbidden terminology, placeholders, or whitespace defects. No `طفل` in technical contexts, no `التصنيع بالعقد`, no `قيد دفع`.

## Evidence
- Health output saved to `docs/evidence/health-20260902.json`
- Screenshots: `docs/evidence/smoke/*.png` (on file, not committed)
- Commands logged above
