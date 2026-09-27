# Stage 6 — W6-1 Accounts Batch 05 Proposal (Final Batch)

**Status: proposal only; owner approval recorded in plan.** This package contains an
offline deterministic cut, test-site reconciliation, and candidate proposal.

## Exact batch proposed

- Scope CSV: `docs/translation/stage6_w601_accounts_batch05_rows_2026-09-27.csv`
- Rows: **56**
- SHA-256: `10c2f94face1a476350e386dd0d176045a13fc8b800f3fb90cd5806cf41353c7`
- Proposal CSV: `docs/translation/stage6_w601_accounts_batch05_proposal_2026-09-27.csv`
- Proposal SHA-256: `74fedcf4313d4dff102755cc054cd1cfc3d28ce45705a6e686a9380f47c51c70`
- Deterministic cut builder: `scripts/stage6_w601_accounts_batch05_cut_2026-09-27.py`
- Proposal builder: `docs/translation/stage6_w601_accounts_batch05_ai_proposal_build_2026-09-27.py`
- Domain: ERPNext Accounts (`W6-1` continuation; Batch 05 of **5** batches covering the final 56 rows of the 1,056-row fresh-accounts gap; 0 fresh rows remain after Batch 05).

## Reconciliation and Dispositions Partition

Reconciled against `v16.localhost` via `docs/translation/stage6_w601_accounts_batch05_site_recon_2026-09-27.py` (JSON output: `docs/translation/stage6_w601_accounts_batch05_site_recon_2026-09-27.json`):

| Disposition | Rows | Treatment |
|---|---:|---|
| `preserved-site-override` | 14 | Match live test-site `tabTranslation` verbatim; preserve unchanged (plan §12); not imported |
| `PROPOSED-payload` | 40 | Candidate translations authored for missing runtime keys; require independent A1/A2/A3 review |
| `EXCEPTION-technical` | 2 | External currency rate API hostnames (`exchangerate.host`, `frankfurter.dev`), technical identifiers; preserved untranslated |
| **Total** | **56** | **14 + 40 + 2** |

## Quality & Formatting Invariants
- 0 catalog duplicates (0 rows in `approved_ar_overrides.csv`).
- 0 edge-whitespace violations (exact whitespace affix parity maintained across all rows).
- Multi-placeholders multiset parity strictly verified: `{0}`, `{1}`, `{}` match exactly between source and translation.
- No blank translations in payload.
- No control characters, no newlines/CRs.
- No source-equal (untranslated) payload rows.

## Boundaries

The proposal is strictly non-production and tested on `v16.localhost`. Stage 8 and production remain untouched.
