# Stage 6 — W6-1 Accounts Batch 04 Proposal

**Status: proposal only; owner approval recorded in plan.** This package contains an
offline deterministic cut, test-site reconciliation, and candidate proposal.

## Exact batch proposed

- Scope CSV: `docs/translation/stage6_w601_accounts_batch04_rows_2026-09-27.csv`
- Rows: **250**
- SHA-256: `0286741911fbe377c0a723131611d8a91cbe7c943c59d307756d7e1f18cfae30`
- Proposal CSV: `docs/translation/stage6_w601_accounts_batch04_proposal_2026-09-27.csv`
- Proposal SHA-256: `4c72e83b3d41476914dcf884a8798c51ec5f6e662500105509fc2b8aad6bc47a`
- Deterministic cut builder: `scripts/stage6_w601_accounts_batch04_cut_2026-09-27.py`
- Proposal builder: `docs/translation/stage6_w601_accounts_batch04_ai_proposal_build_2026-09-27.py`
- Domain: ERPNext Accounts (`W6-1` continuation; Batch 04 of **5** batches covering the 1,056-row fresh-accounts gap; 56 fresh rows remain after Batch 04).

## Reconciliation and Dispositions Partition

Reconciled against `v16.localhost` via `docs/translation/stage6_w601_accounts_batch04_site_recon_2026-09-27.py` (JSON output: `docs/translation/stage6_w601_accounts_batch04_site_recon_2026-09-27.json`):

| Disposition | Rows | Treatment |
|---|---:|---|
| `preserved-site-override` | 125 | Match live test-site `tabTranslation` verbatim; preserve unchanged (plan §12); not imported |
| `PROPOSED-payload` | 124 | Candidate translations authored for missing runtime keys; require independent A1/A2/A3 review |
| `EXCEPTION-technical` | 1 | Un-normalized NestedSet right-bound column (`Rgt`), technical identifier; preserved untranslated |
| **Total** | **250** | **125 + 124 + 1** |

## Quality & Formatting Invariants
- 0 catalog duplicates (0 rows in `approved_ar_overrides.csv`).
- 0 edge-whitespace violations (exact whitespace affix parity maintained across all rows).
- Multi-placeholders multiset parity strictly verified: `{0}`, `{1}`, `{}` match exactly between source and translation.
- No blank translations in payload.
- No control characters, no newlines/CRs.
- No source-equal (untranslated) payload rows.

## Boundaries

The proposal is strictly non-production and tested on `v16.localhost`. Stage 8 and production remain untouched.
