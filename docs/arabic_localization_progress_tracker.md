# Arabic Localization Progress Tracker

Date started: 2026-05-24
Plan source: `docs/arabic_localization_execution_plan.md`
Validation site: `v16.localhost`

## Status Legend

- Pending: not started
- In Progress: currently being worked
- Done: implemented and locally validated
- Partial: implemented partly; follow-up remains
- Blocked: cannot complete without external input or environment fix

## Phase Tracker

| Phase | Scope | Status | Notes |
|---|---|---|---|
| 0 | Baseline audit | Done | DB Arabic translations: 37. `ar.po` has bad plural formula and no non-header translated `msgstr`. Arabic Language locale fields are null. 10 app DocTypes found; 9 registered. |
| 1 | Translation seed script | Done | Cache keys fixed, commit made optional, hook-safe execution added, seed expanded. DB count increased 37 -> 74; second run processed 0 changes. |
| 2 | Hook registration | Done | Added `Construction Settings`; all 10 app DocTypes now covered. |
| 3 | Extractor coverage | Done | Added config/sidebar/fixture coverage and regenerated POT/PO. |
| 4 | PO header repair | Done | Arabic plural formula fixed; MO compiled with `bench compile-po-to-mo --app construction --locale ar --force`. |
| 5 | Construction catalog translation | Done | First-pass Arabic translations added for all extracted non-header PO messages. Business terminology review is still recommended. |
| 6 | Workspace sidebar localization | Done | Frappe boot translates sidebar item labels with `_()`; stored DB labels remain English canonical values. |
| 7 | Arabic Language record | Done | Set `date_format`, `time_format`, `number_format`, and `first_day_of_the_week` on `v16.localhost`. |
| 8 | RTL UI completion | Partial | Existing RTL CSS confirmed; added navbar brand RTL override. Full browser/PDF visual QA still required. |
| 9 | Automated checks | Done | Added `construction.scripts.check_arabic_localization.execute`; check passes on `v16.localhost`. |
| 10 | Manual Arabic QA | Blocked | Requires browser review with Arabic and English users; not completed in terminal-only execution. |
| 11 | Translation review workflow | Done | Added PO/DB review export/import helper, generated review CSVs, and added UI i18n guidelines for upcoming implementation. |

## Baseline Snapshot

- Worktree before execution: two untracked docs from this localization task.
- Arabic `Translation` records on `v16.localhost`: 37.
- Arabic `Language` record: enabled, but `date_format`, `time_format`, `number_format`, and `first_day_of_the_week` are null.
- `construction/locale/ar.po`: bad plural formula and no non-header translated `msgstr` entries.
- `babel_extractors.csv`: no coverage for `config/workspace_sidebar_items.json`; fixture coverage only includes `fixtures/custom_field.json`.
- Construction DocTypes found: 10.
- `translated_doctypes` entries found: 9; missing `Construction Settings`.

## Execution Log

| Time | Action | Result |
|---|---|---|
| 2026-05-24 | Created tracker | Pending baseline capture. |
| 2026-05-24 | Captured baseline | Phase 0 marked Done. |
| 2026-05-24 | Patched seed script | Fixed v16 cache invalidation, optional commit, permission flags, and expanded global Arabic terms. |
| 2026-05-24 | Patched hooks | Added translation seed to install/migrate hooks and added missing `Construction Settings`. |
| 2026-05-24 | Patched extractors | Added workspace sidebar config and fixture extraction; added Construction Theme fixture extractor. |
| 2026-05-24 | Regenerated POT/PO | `main.pot` and `ar.po` now include sidebar/config/fixture strings. |
| 2026-05-24 | Compiled MO | `bench compile-po-to-mo --app construction --locale ar --force` passed after sandbox escalation for multiprocessing. |
| 2026-05-24 | Validated seed idempotency | First run processed 41 changes and DB count reached 74; second run processed 0 changes. |
| 2026-05-24 | Filled Arabic PO | All extracted non-header messages received first-pass Arabic `msgstr` values. |
| 2026-05-24 | Set Arabic locale fields | `Language/ar`: `yyyy-mm-dd`, `HH:mm`, `#,###.##`, `Saturday`. |
| 2026-05-24 | Added automated check | `bench --site v16.localhost execute construction.scripts.check_arabic_localization.execute` returns `ok: true`. |
| 2026-05-24 | Verified workspace sidebar path | Frappe `boot.get_sidebar_items()` translates item labels with `_()` at runtime. |
| 2026-05-24 | Added RTL navbar override | Added `[dir="rtl"]` rules for `.navbar-brand-area` and `.navbar-brand-title`. |
| 2026-05-24 | Ran migration | `bench --site v16.localhost migrate` passed; after-migrate seed processed 0 translations. Residual warning: missing `fixtures/workspace_sidebar_construction.json`. |
| 2026-05-24 | Ran build | `bench build` passed and compiled translations/assets. |
| 2026-05-24 | Final automated validation | Arabic localization check passed; Arabic DB translation count remained 74; `construction.mo` exists at 29,407 bytes. |
| 2026-05-24 | Clarified scope | Full Arabic localization scope is Construction app only; ERPNext/Frappe English text remains separate unless explicitly approved as global DB overrides. |
| 2026-05-24 | Added UI i18n guidelines | `docs/arabic_ui_i18n_guidelines.md` documents rules for upcoming JS/Python/DocType/sidebar/fixture/RTL implementation. |
| 2026-05-24 | Added review tools | `construction.scripts.arabic_translation_review` can export/import PO and DB translations for correction. |
| 2026-05-24 | Exported review CSVs | `docs/arabic_po_review.csv` has 351 PO rows; `docs/arabic_db_translation_review.csv` has 74 DB rows. |
| 2026-05-24 | Expanded global scope | Added `docs/global_arabic_localization_tracker.md` for Frappe/ERPNext Arabic gaps. |
| 2026-05-24 | Exported global missing catalogs | Frappe has 2,997 empty Arabic PO rows; ERPNext has 4,342 empty Arabic PO rows. |
| 2026-05-24 | Expanded global DB overrides | Arabic DB Translation count increased to 294 for high-frequency ERPNext/Frappe terms. |

## Remaining Work

- Browser QA with Arabic user.
- English regression browser QA.
- PDF/print RTL visual QA.
- Business review and correction of first-pass Arabic construction terminology using `docs/arabic_po_review.csv`.
- Review and correction of global seed translations using `docs/arabic_db_translation_review.csv`; current row count is 294 and these affect all apps.
- Translate/review Frappe and ERPNext missing strings using `docs/frappe_ar_missing_review.csv` and `docs/erpnext_ar_missing_review.csv`.
- Investigate pre-existing migrate warning: `construction/fixtures/workspace_sidebar_construction.json missing`.
