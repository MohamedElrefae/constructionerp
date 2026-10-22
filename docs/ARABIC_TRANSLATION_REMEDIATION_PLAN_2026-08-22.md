# Arabic Localization Remediation — Sign-off & Implementation Record

**Date:** 2026-08-22
**Site:** `v16.localhost` (Frappe / ERPNext v16)
**Scope:** Arabic end-user translations — Construction app + its ERPNext integration layer
**Status:** Decisions approved; P1–P3 implemented & verified; P4–P6 scheduled.

---

## 1. Approved Decisions

| # | Decision | Position |
|---|----------|----------|
| D1 | Localization scope | **Tiered** — seed high-frequency construction/ERP terms now; reviewed upstream catalogs imported on demand. Not a full monolith of ~7,300 strings. |
| D2 | Terminology standard | **Egyptian construction & accounting Arabic** (single glossary). Subcontractor = مقاول الباطن (never التصنيع بالعقد); Retention = محتجزات ضمان (never الاحتفاظ الأسهم); Payment Entry = سند قبض / سند صرف (never قيد دفع). |
| D3 | Migrate safety | **Insert-only** seeding with drift reporting. Existing rows are never overwritten by `after_install` / `after_migrate`. Placeholder seeder converted to report-only. |
| D4 | Language rollout | User-driven per-user language; site default unchanged. Translation maintenance gated to System Manager / Translator. |

---

## 2. What Was Done

### P1 — Egyptian Glossary (single source of truth)
`construction/data/glossary/egyptian_construction_glossary.json` — 38 terms + rules. Covers subcontracting, retention, vouchers, BOQ, site, and core actions.

### P2a — Non-destructive seeding (the fragility fix)
`construction/insert_translations.py`:
- `execute()` now **insert-only** — missing rows created, existing rows **never** overwritten at migrate.
- Added `get_arabic_translation_drift()` (whitelisted) so the team can review reviewed-vs-DB disagreements instead of losing edits.

### P2b — Removed the junk-row generator
`construction/api/translation_tools.py`: `seed_missing_arabic_translations` no longer creates rows with `translated_text = source_text` (English masquerading as Arabic). Replaced with report-only `get_missing_arabic_translation_sources` + `get_placeholder_arabic_translation_sources`.

### P2c — CSV relocation status
Deferred (see §4). The insert-only change already prevents `docs/*.csv` from overwriting live edits; physical relocation is cosmetic.

### P3 — Domain terminology remediation (applied to live site)
`construction/patches/v8_3/fix_arabic_domain_terminology.py` (registered in `patches.txt`): fixes the subcontractor family (التصنيع بالعقد → مقاولات الباطن / من الباطن), accounting registers (Payment Entry, Journal Entry, Mobilization Cost), and seeds the highest-priority absent terms (Retention, Advance, Subcontractor, Variation Order, Bill of Quantities, …).

### Documentation
- `docs/USER_GUIDE.md` v1.5 draft — new **§14 Arabic & Translations** (setting language, glossary table, correcting & surviving migrate, cache clearing).
- `construction/hooks.py` — bumped `translation_list_tools.js?v=2` (cache-bust for edited JS).

---

## 3. Verification (fresh, on `v16.localhost`)

| Check | Result |
|---|---|
| `py_compile` of edited modules | PASS |
| Glossary JSON integrity (38 terms) | PASS |
| Patch execution | `fixed=46 created=11 deduped=2` |
| Rows still using التصنيع بالعقد / مصنع بالعقد | **0** |
| Canonical terms present (Subcontractor=مقاول باطن, Retention=محتجزات ضمان, Payment Entry=سند قبض / سند صرف, …) | PASS |
| Drift report (protected rows) | 46 surfaced → **1 after seed reconciliation** (remaining = pre-existing cosmetic HTML quote-style diff) |

**Seed reconciliation (2026-08-22):** `docs/arabic_db_translation_review.csv`, `docs/arabic_po_review.csv`, and `docs/erpnext_ar_missing_review_filled.csv` were updated from the live DB canonical values (45 rows). The seed baselines are now authoritative, so fresh installs seed correct Egyptian Arabic, and the next `bench migrate` no longer reports these as drift. The single remaining drift entry is the `<span class='h4'><b>Construction ERP</b></span>` single-vs-double-quote HTML artifact — cosmetic, pre-existing, not a terminology issue.

**Note:** The 46 drift rows are expected — they are the rows the patch corrected whose seed CSV baseline still holds the old value. They are reported, not overwritten, so the next `bench migrate` keeps the corrected values.

---

## 4. Deferred Follow-ups

| ID | Item | Why deferred | Recommendation |
|---|---|---|---|
| P2c | Relocate seed CSVs to `construction/data/translations/` | Cosmetic; insert-only already prevents overwrite | Do in a cleanup pass; update `REVIEW_FILES` paths in `insert_translations.py` |
| P4 | Coverage fill — remaining ~2,280 ERPNext + ~3,000 Frappe empty strings | Bulk effort; needs domain review | Generate index, pre-fill via glossary, import into a **review queue** (add status on Translation) — scheduled, not shipped |
| P5 | Translation Workbench UX | Larger UI task | Replace one-by-one CRUD with side-by-side editor + glossary suggestion + bulk apply + export/import round-trip (reuse `translation_list_tools.js`) |
| P6 | CI verification + RTL visual pass | Needs CI wiring | Add coverage lint (fail if `ar.po` gaps grow), RTL screenshot suite, re-run full regression |
| — | Upstream catalogs (erpnext/frappe `ar.po`) | Out of reach from this app (v16.18.3) | Patch upstream via PR or maintain DB overrides for high-frequency terms only (D1) |

---

## 5. How To Re-Apply / Re-Run

```bash
# Apply the terminology remediation again (idempotent)
bench --site v16.localhost execute construction.patches.v8_3.fix_arabic_domain_terminology.execute

# See protected (non-overwritten) drift rows
bench --site v16.localhost execute construction.insert_translations.get_arabic_translation_drift

# Clear translation cache after edits
bench --site v16.localhost clear-cache
```

### P5 (partial) — Glossary-driven correction from the UI
`construction/api/translation_tools.py` adds whitelisted `apply_glossary_corrections(dry_run)` — bulk-corrects Arabic rows to the canonical glossary, idempotent and explicit. `translation_list_tools.js` (v=3) adds **Preview Glossary Corrections** (dry-run) and **Apply Glossary Corrections** (confirm-gated) menu items on the Translation list. Dry-run returns an empty preview → all 44 glossary terms already match after P3 + reconciliation.

### P4 (partial) — Coverage-gap index + review queue
True runtime gap computed as `catalog universe (15,007 msgids) − PO-translated (7,716) − DB-covered (2,688) = 5,169`.

- `docs/arabic_coverage_gap_report_2026-08-22.csv` — **5,167** gaps tagged by app: `erpnext` 2,305 · `frappe` 2,861 · `construction` 1. Columns `app, source_text, suggested_ar, status`.
- `construction/data/translations/review_queue.csv` — the **approval queue**: rows with a filled `suggested_ar`. Only **4** common terms were genuinely missing and safely pre-fillable (`City`, `Country`, `Phone`, `Postal Code`) — the rest of the common terms were already covered by DB/PO.
- **Long-tail backlog ≈ 5,163** strings with no translation anywhere. These are NOT auto-filled — the `translation_tools.import_review_queue` pattern is the pipeline for a translator/MT pass to fill `suggested_ar` and import.
- Tooling: `apply_glossary_corrections(dry_run)` + `import_review_queue(dry_run)` (whitelisted), UI menu items on the Translation list. Dry-run returns `{total:4, preview[4 create]}`.

---

*Companion docs: `docs/arabic_localization_execution_plan.md`, `docs/translation_ui_analysis.md`, `docs/arabic_ui_i18n_guidelines.md`, `docs/USER_GUIDE.md` §14.*
