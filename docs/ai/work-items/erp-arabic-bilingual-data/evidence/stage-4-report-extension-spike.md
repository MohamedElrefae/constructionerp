# Stage 4 — Report extension-point spike (builder record)

Date: 2026-09-09 · HEAD: `e7be48855bde540464ea302e53c9bfca62b7c462` (uncommitted)
Engineering-only. No vendor report-file edit; no Report DocType created; no
Account or translation data mutation.

## What was engineered

`construction/services/report_bilingual_extension.py` — a Construction-side
extension point for the four financial reports:

- `transform_report(columns, data, lang, mapping, label_fields)` — pure:
  localizes the account-label cells for the session language. **Arabic**
  mode swaps to `account_name_ar`, **Both** renders `English — Arabic`,
  **English** keeps the English identity. Source `columns`/`data` are never
  mutated (new structures returned).
- `bilingualize_report(execute, filters, lang, report_name, mapping=None)` —
  runs the vendor report `execute` **read-only** and returns the localized
  (columns, data). Nothing is written back.
- `REPORT_LABEL_FIELDS` — resolves the account-label boundary for
  `General Ledger`, `Trial Balance`, `Balance Sheet`, and
  `Profit and Loss Statement`.
- `load_account_arabic_mapping(company)` — read-only
  `Account.account_name -> account_name_ar`.

`construction/tests/test_stage4_report_extension.py` — 11 tests:
pure transformer (ar/en/both rendering, unknown-label identity, sources not
mutated, columnar row, field-config presence) + read-only integration runs
(GL and Trial Balance) proving the extension binds to real vendor output
without mutation, plus a rollback-note assertion.

## Rendering proven

| Report | Extension | ar / en / both evidence |
|---|---|---|
| General Ledger | `account` column | read-only vendor execute :: transform (all modes, no exception, row stability) + pure unit tests |
| Trial Balance | `account` column | read-only vendor execute :: transform (all modes) |
| Balance Sheet | `account` / `account_name` | field-config + pure unit tests |
| Profit and Loss Statement | `account` / `account_name` | field-config + pure unit tests |

Because no Account currently has an Arabic name, the ar/both swap is verified
unit-level with a synthetic `account_name_ar`; the integration runs prove the
extension binds to live vendor output and is non-mutating.

## Rollback note

`report_bilingual_extension.rollback_note()` — the spike added only two new
(untracked) files:
`construction/services/report_bilingual_extension.py` and
`construction/tests/test_stage4_report_extension.py`. No vendor report file
was edited, no Report DocType was created, and no Account or translation data
was changed, so rollback is simply deleting those two files (nothing to
reverse in the database).

## Validation

- `bench --site v16.localhost run-tests --module construction.tests.test_stage4_report_extension` → 11/11 OK.
- Aggregate now 232 (13+6+5+3+8+89+38+53+6+11) all green; standalone 89/89;
  catalog 805 / `664 + 21` / 0 missing; inventory 18,446 rows root
  `2e284695…` live-matched; evidence-enabled gate errors=0; lints +
  `git diff --check` clean.

## Still blocked / separate gates

Independent AI proposal generation, separate AI-A2 linguistic/accounting
review, owner approval of the reviewed payload, dry-run + explicitly
authorized test-site import, and post-import verification/rollback — all
remain separate and blocked.
