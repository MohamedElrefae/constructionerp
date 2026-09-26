# Stage 6 — W6-1 Accounts Batch 01 Proposal

**Status: proposal only; owner approval pending.** This package contains an
offline deterministic cut, test-site reconciliation, and candidate proposal only.
No reviewer quorum, import, catalog/decision update, evidence re-pin, commit, or push was performed
for this Accounts Batch 01 scope.

## Exact batch proposed

- Scope CSV: `docs/translation/stage6_w601_accounts_batch01_rows_2026-09-24.csv`
- Rows: **250**
- SHA-256: `4910a9e4a0e5f8dd0105d484171ac1dc68e173220a0bed27520fbfc5e8c090fd`
- Proposal CSV: `docs/translation/stage6_w601_accounts_batch01_proposal_2026-09-24.csv`
- Proposal SHA-256: `226ff8b158a4a17bca77209d2e452fff9eff75fd6479324f3e020e6b24ab2b4e`
- Deterministic cut builder: `scripts/stage6_w601_accounts_batch01_cut_2026-09-24.py`
- Proposal builder: `docs/translation/stage6_w601_accounts_batch01_ai_proposal_build_2026-09-24.py`
- Domain: ERPNext Accounts (`W6-1` continuation; Batch 01 of **5** batches covering the 1,056-row fresh-accounts gap — 4 x 250 + a 56-row remainder).
- Provenance of the 1,056 figure: the deterministic cut (1,198 eligible ledger rows from `docs/erpnext_ar_missing_review_filled.csv` minus 142 already covered) as asserted by the cut scripts. The Stage-6 matrix row W6-1 still reads "1,265 (subset: ~250 user-visible flow strings)" and is superseded by this finer cut.
- Related artifact, **not** part of this approval: `docs/translation/stage6_w601_accounts_batch02_rows_2026-09-24.csv` (250 rows, SHA-256 `dc9b6c022c01a5cfcad5c6934c58a3ba74cc091f17676b607d50a96ab0d60e4e`) is a **cut-only** slice with no reconciliation, no proposal, and no translations. Its row set is disjoint from Batch 01 (0 overlap); 556 rows remain after Batch 02.

## Reconciliation and Dispositions Partition

Reconciled against `v16.localhost` via `docs/translation/stage6_w601_accounts_batch01_site_recon_2026-09-24.py` (JSON output: `docs/translation/stage6_w601_accounts_batch01_site_recon_2026-09-24.json`):

| Disposition | Rows | Treatment |
|---|---:|---|
| `preserved-site-override` | 147 | Match live test-site `tabTranslation` verbatim; preserve unchanged (plan §12); not imported |
| `PROPOSED-payload` | 103 | Candidate translations authored for missing runtime keys; require independent A1/A2/A3 review |
| `EXCEPTION-technical` | 0 | None in this batch |
| **Total** | **250** | **147 + 103** |

## Whitespace and Formatting Governance

All edge-whitespace entries are strictly validated with whitespace affix parity
(3 leading-space rows, 7 trailing-space rows; 0 violations, verified 2026-09-25):
- Leading spaces preserved verbatim: `' Amount'` -> `' المبلغ'`, `' Name'` -> `' الاسم'`, `' Rate'` -> `' السعر'`.
- Trailing spaces preserved verbatim (5 of the 7 shown): `'All Parties '` -> `'كل الجهات '`, `'Customer '` -> `'العميل '`, `'Customer Name: '` -> `'اسم العميل: '`, `'Customer: '` -> `'العميل: '`, `'Closing [Opening + Total] '` -> `'الإغلاق [الافتتاحي + الإجمالي] '`. Two further trailing-space rows, `'Allow multi-currency invoices against single party account '` and `'Apply Tax Withholding Amount '`, are also preserved verbatim.
- Multi-placeholders multiset parity strictly verified (e.g. `{0}`, `{1}`, `{2}`, `{3}`, `{}`): 11 rows carry two or more placeholders, 0 mismatches.
- No blank translations and no source-equal (untranslated) payloads.

## Known limitations (recorded 2026-09-25)

- `stage6_w601_accounts_batch01_site_recon_2026-09-24.json` carries no
  `generated_utc` and no app-commit pin, so the live reconciliation cannot be
  re-verified against a known site state.
- The builders are offline generators, but they are not write-free: each writes
  its own artifact (scope CSV, proposal CSV, recon JSON). The recon script also
  performs a read-only `frappe.get_all` against `v16.localhost` and hard-codes
  its repo root.
- Both cut scripts are **no longer re-runnable as-is**: their `prior` set is an
  unpinned `docs/translation/stage6_*rows*.csv` glob that has since grown to 392
  prior rows, so the hard-coded `overlap == 142` / `fresh == 1056` asserts now
  fail. The shipped CSVs are the correct historical slices; pin the prior-file
  list or relax the asserts before regenerating.

## Boundaries

The proposal is strictly non-production and proposal-only. No mutation has been made to `v16.localhost` `tabTranslation` or to the git catalog/release-decision state: 0 of these 250 rows appear in `construction/data/translations/approved_ar_overrides.csv` or `release_decisions.json` (verified 2026-09-25). Stage 8 and production remain untouched.

## Owner decision requested

To authorize the governed cycle for this scope on `v16.localhost`, confirm:
"Approve `stage6_w601_accounts_batch01_rows_2026-09-24.csv`, SHA-256 `4910a9e4a0e5f8dd0105d484171ac1dc68e173220a0bed27520fbfc5e8c090fd`, for the test site only. Proceed with independent A1/A2/A3 reviews, AI-R verification, and the governed cycle. Leave Stage 8 and production untouched."
