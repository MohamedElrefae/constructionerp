# Global Arabic Localization Tracker

Date started: 2026-05-24
Scope: Frappe + ERPNext + Construction Arabic UI
Validation site: `v16.localhost`

## Scope Decision

This tracker covers end-to-end Arabic UI translation beyond the Construction app.

Ownership split:

- Construction app: handled in `docs/arabic_localization_progress_tracker.md`.
- Frappe core: Arabic gaps are in `apps/frappe/frappe/locale/ar.po`.
- ERPNext: Arabic gaps are in `apps/erpnext/erpnext/locale/ar.po`.
- Global DB Translation overrides: allowed for reviewed high-frequency UI strings that must render immediately across all apps.

## Current Status

Measured on 2026-05-24:

| App | Total PO Messages | Translated | Empty | Fuzzy |
|---|---:|---:|---:|---:|
| Frappe | 5,902 | 5,902 | 0 | 0 |
| ERPNext | 8,997 | 8,997 | 0 | 0 |
| Construction | 351 | 351 | 0 | 0 |

## Phase Tracker

| Phase | Scope | Status | Notes |
|---|---|---|---|
| 0 | Baseline stats | Done | Initial counts captured from PO catalogs. |
| 1 | Review/export tooling | Done | Added global PO review helper under Construction scripts. |
| 2 | Export missing translations | Done | Exported Frappe and ERPNext missing Arabic CSVs for review/correction. |
| 3 | Translate Frappe missing strings | Done | Filled 2,997 remaining entries through the end-to-end draft coverage pass. |
| 4 | Translate ERPNext missing strings | Done | Imported 2,064 reviewed exact-match entries, then filled 2,278 remaining entries through the end-to-end draft coverage pass. |
| 5 | Import reviewed translations | Done | Imported `docs/erpnext_ar_missing_review_filled.csv` and applied full PO coverage for Frappe/ERPNext. |
| 6 | Compile Frappe/ERPNext Arabic MO | Done | Frappe and ERPNext Arabic MO files compiled after imports/fill. |
| 7 | Global DB override review | Partial | Expanded reviewed high-frequency overrides. Arabic DB Translation count is now 294. Critical Submit/Journal Entry fixes applied. |
| 8 | Browser QA | Pending | Arabic user + English regression across Desk, ERPNext modules, Construction. |

## Coverage Notes

- End-to-end PO coverage is complete for Frappe, ERPNext, and Construction: no empty Arabic entries remain.
- Frappe and the final ERPNext long-tail pass used deterministic draft Arabic generation for strings that did not have reviewed exact translations.
- Exact reviewed glossary and DB override entries take precedence over draft generation.
- Placeholder set parity was checked after the fill pass. Entries with real missing placeholder sets were reverted to source text to avoid runtime formatting errors.

## Generated Review Files

- `docs/frappe_ar_missing_review.csv`
- `docs/erpnext_ar_missing_review.csv`
- `docs/erpnext_ar_missing_review_filled.csv`
- `docs/global_arabic_catalog_stats.csv`
- `docs/arabic_db_translation_review.csv`

Current generated row counts:

| File | Rows |
|---|---:|
| `frappe_ar_missing_review.csv` | 0 |
| `erpnext_ar_missing_review.csv` | 0 |
| `erpnext_ar_missing_review_filled.csv` | 4,342 |
| `arabic_db_translation_review.csv` | 294 |

## Commands

Export stats:

```bash
cd /home/mohamed/frappe-bench
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.export_stats
```

Export missing strings:

```bash
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.export_missing_reviews
```

Import reviewed Frappe translations:

```bash
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.import_review --kwargs "{'app': 'frappe', 'csv_path': 'apps/construction/docs/frappe_ar_missing_review.csv', 'dry_run': False}"
```

Import reviewed ERPNext translations:

```bash
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.import_review --kwargs "{'app': 'erpnext', 'csv_path': 'apps/construction/docs/erpnext_ar_missing_review_filled.csv', 'dry_run': False}"
```

Fill ERPNext review CSV from the reviewed glossary:

```bash
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.fill_review_from_glossary --kwargs "{'app': 'erpnext', 'csv_path': 'apps/construction/docs/erpnext_ar_missing_review.csv', 'output_path': 'apps/construction/docs/erpnext_ar_missing_review_filled.csv'}"
```

Fill all remaining PO entries after reviewed imports:

```bash
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.fill_remaining_po --kwargs "{'apps': 'frappe,erpnext', 'dry_run': False}"
```

Compile:

```bash
bench compile-po-to-mo --app frappe --locale ar --force
bench compile-po-to-mo --app erpnext --locale ar --force
bench --site v16.localhost clear-cache
```

## Review Rules

- Preserve placeholders: `{0}`, `{1}`, `{name}`, `%s`, `%(name)s`.
- Preserve HTML tags.
- Preserve technical identifiers when they are not user-facing words.
- Do not translate whitespace-only entries.
- Do not translate code operators such as `!=`.
- For ERP terminology, prefer consistent business Arabic over literal translation.
- Validate by compiling PO to MO after import.

## Remaining Work

- Human-review the draft-filled long-tail Frappe/ERPNext translations before final production sign-off.
- Continue reviewing the 294 global DB overrides in `docs/arabic_db_translation_review.csv` as business terminology evolves.
- Perform Arabic browser QA across:
  - Desk navigation
  - ERPNext Accounting
  - ERPNext Stock
  - ERPNext Buying/Selling
  - ERPNext HR/Projects if installed
  - Construction module
