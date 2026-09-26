# Stage 6 — W6-1 Accounts Batch 02 Proposal

**Status: proposal only; owner approval pending.** This package contains an
offline deterministic cut, test-site reconciliation, and candidate proposal only.
No reviewer quorum, import, catalog/decision update, evidence re-pin, commit, or push has been performed
for this Accounts Batch 02 scope.

## Exact batch proposed

- Scope CSV: `docs/translation/stage6_w601_accounts_batch02_rows_2026-09-24.csv`
- Rows: **250**
- SHA-256: `dc9b6c022c01a5cfcad5c6934c58a3ba74cc091f17676b607d50a96ab0d60e4e`
- Proposal CSV: `docs/translation/stage6_w601_accounts_batch02_proposal_2026-09-26.csv`
- Proposal SHA-256: `e0fac4c67787aba3c5ac50b52a9f21625360da0693f7b17e77dbf7a315e7567e`
- Deterministic cut builder: `scripts/stage6_w601_accounts_batch02_cut_2026-09-24.py`
- Proposal builder: `docs/translation/stage6_w601_accounts_batch02_ai_proposal_build_2026-09-26.py`
- Domain: ERPNext Accounts (`W6-1` continuation; Batch 02 of **5** batches covering the 1,056-row fresh-accounts gap — 4 x 250 + a 56-row remainder; 556 fresh rows remain after Batch 02).

## Reconciliation and Dispositions Partition

Reconciled against `v16.localhost` via `docs/translation/stage6_w601_accounts_batch02_site_recon_2026-09-26.py` (JSON output: `docs/translation/stage6_w601_accounts_batch02_site_recon_2026-09-26.json`):

| Disposition | Rows | Treatment |
|---|---:|---|
| `preserved-site-override` | 160 | Match live test-site `tabTranslation` verbatim; preserve unchanged (plan §12); not imported |
| `PROPOSED-payload` | 89 | Candidate translations authored for missing runtime keys; require independent A1/A2/A3 review |
| `EXCEPTION-technical` | 1 | NestedSet tree column name (`Lft`), internal database column name; preserved untranslated |
| **Total** | **250** | **160 + 89 + 1** |

## Quality & Formatting Invariants
- 0 catalog duplicates (0 rows in `approved_ar_overrides.csv`).
- 0 strip collisions against live Site Overrides.
- 0 edge-whitespace violations.
- Multi-placeholders multiset parity strictly verified: `{0}`, `{1}`, `{}` match exactly between source and translation.
- No blank translations in payload.
- No control characters, no newlines/CRs.
- No source-equal (untranslated) payload rows.

## Boundaries

The proposal is strictly non-production and proposal-only. No mutation has been made to `v16.localhost` `tabTranslation` or to the git catalog/release-decision state: 0 of these 250 rows appear in `construction/data/translations/approved_ar_overrides.csv` or `release_decisions.json`. Stage 8 and production remain untouched.

## Owner decision requested

To authorize the governed cycle for this scope on `v16.localhost`, confirm:
"Approve `stage6_w601_accounts_batch02_rows_2026-09-24.csv`, SHA-256 `dc9b6c022c01a5cfcad5c6934c58a3ba74cc091f17676b607d50a96ab0d60e4e`, for the test site only. Proceed with independent A1/A2/A3 reviews, AI-R verification, and the governed cycle. Leave Stage 8 and production untouched."
