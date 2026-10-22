# Stage 3 Browser Regression — ar/en Sessions (2026-09-20)

**Target:** non-production test site `v16.localhost`, headless Chromium, real desk sessions.

## Arabic session (`ar`, user `ct-browser-ar@example.com`, since removed)

- `boot.lang = ar` — PASS
- Chart of Accounts tree rendered 6 top labels; 5 contain Arabic, **zero** leak the
  English docname (`(... - E)` pattern absent) — PASS
  - e.g. `استخدامات الأموال (الأصول)`, `مصادر الأموال (الالتزامات)`, `حقوق الملكية`,
    `الإيرادات`, `المصروفات`
- Account form `GST - E`: identity section present, `en=GST`, `ar=ضريبة السلع والخدمات` —
  PASS
- Identity cells contain no element children (text-only, no HTML injection) — PASS

## English session (same account, language switched to `en`)

- `boot.lang = en` — PASS
- All tree labels English, **zero** Arabic leak — PASS
- Identity section still renders both names — PASS
- Cells text-only — PASS

## Notes

- The form `completeness` cell reports "code missing" for `GST - E` because that account
  has no `account_number`; this is an honest data-driven signal, not a rendering defect.
- The temporary `ct-browser-ar@example.com` user was deleted after the run.

**Result: 8 checks, 0 failed.** Browser UI is covered; automated backend suites
(38 service + 5 schema + 53 pilot) were already green.
