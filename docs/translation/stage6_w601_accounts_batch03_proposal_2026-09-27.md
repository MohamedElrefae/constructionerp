# Stage 6 — W6-1 Accounts Batch 03 Proposal

**Status: proposal only; owner approval pending.** This package contains an
offline deterministic cut, test-site reconciliation, and candidate proposal only.
No reviewer quorum, import, catalog/decision update, evidence re-pin, commit, or push has been performed
for this Accounts Batch 03 scope.

## Exact batch proposed

- Scope CSV: `docs/translation/stage6_w601_accounts_batch03_rows_2026-09-27.csv`
- Rows: **250**
- SHA-256: `dfa6de55bb986c5e7b6fc845ad9b3de7de2a0f6c38c441cf4cf2c8427713d1cb`
- Proposal CSV: `docs/translation/stage6_w601_accounts_batch03_proposal_2026-09-27.csv`
- Proposal SHA-256: `3b0a3ee8d6c9b6a1c59d925aea5c2ed71059c07698e1935c9c65b385c464ef3f`
- Deterministic cut builder: `scripts/stage6_w601_accounts_batch03_cut_2026-09-27.py`
- Proposal builder: `docs/translation/stage6_w601_accounts_batch03_ai_proposal_build_2026-09-27.py`
- Domain: ERPNext Accounts (`W6-1` continuation; Batch 03 of **5** batches covering the 1,056-row fresh-accounts gap — 4 x 250 + a 56-row remainder; 306 fresh rows remain after Batch 03).

## Reconciliation and Dispositions Partition

Reconciled against `v16.localhost` via `docs/translation/stage6_w601_accounts_batch03_site_recon_2026-09-27.py` (JSON output: `docs/translation/stage6_w601_accounts_batch03_site_recon_2026-09-27.json`):

| Disposition | Rows | Treatment |
|---|---:|---|
| `preserved-site-override` | 128 | Match live test-site `tabTranslation` verbatim; preserve unchanged (plan §12); not imported |
| `PROPOSED-payload` | 121 | Candidate translations authored for missing runtime keys; require independent A1/A2/A3 review |
| `EXCEPTION-technical` | 1 | Un-normalized developer column label (`Period_from_date`), technical identifier; preserved untranslated |
| **Total** | **250** | **128 + 121 + 1** |

## Quality & Formatting Invariants
- 0 catalog duplicates (0 rows in `approved_ar_overrides.csv`).
- 0 strip collisions against live Site Overrides.
- 0 edge-whitespace violations (exact whitespace affix parity maintained across all rows).
- Multi-placeholders multiset parity strictly verified: `{0}`, `{1}`, `{}` match exactly between source and translation.
- No blank translations in payload.
- No control characters, no newlines/CRs.
- No source-equal (untranslated) payload rows.

## Boundaries

The proposal is strictly non-production and proposal-only. No mutation has been made to `v16.localhost` `tabTranslation` or to the git catalog/release-decision state: 0 of these 250 rows appear in `construction/data/translations/approved_ar_overrides.csv` or `release_decisions.json`. Stage 8 and production remain untouched.

## Owner decision requested

To authorize the governed cycle for this scope on `v16.localhost`, confirm:
"Approve `stage6_w601_accounts_batch03_rows_2026-09-27.csv`, SHA-256 `dfa6de55bb986c5e7b6fc845ad9b3de7de2a0f6c38c441cf4cf2c8427713d1cb`, and proposal `stage6_w601_accounts_batch03_proposal_2026-09-27.csv`, SHA-256 `3b0a3ee8d6c9b6a1c59d925aea5c2ed71059c07698e1935c9c65b385c464ef3f`, for the test site only. Proceed with independent A1/A2/A3 reviews, AI-R verification, and the governed cycle. Leave Stage 8 and production untouched."
