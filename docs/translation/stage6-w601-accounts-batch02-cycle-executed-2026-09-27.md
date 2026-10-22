# W6-1 Accounts Batch 02 — governed cycle closed (2026-09-27)

## Scope and Review

Owner approval applied only to `stage6_w601_accounts_batch02_rows_2026-09-24.csv` (250 rows; SHA-256 `dc9b6c022c01a5cfcad5c6934c58a3ba74cc091f17676b607d50a96ab0d60e4e`) on the non-production test site `v16.localhost`. The proposal CSV is `stage6_w601_accounts_batch02_proposal_2026-09-26.csv` (SHA-256 `e0fac4c67787aba3c5ac50b52a9f21625360da0693f7b17e77dbf7a315e7567e`). Independent A1/A2/A3 reviews and final AI-R all reported PASS.

| Disposition | Rows | Treatment |
| --- | ---: | --- |
| Released payload | 89 | Imported as release v1.12 |
| Preserved Site Override (exact) | 160 | Left unchanged; not imported (plan §12) |
| Technical exception | 1 | `Lft` — Frappe NestedSet tree traversal boundary column; untranslated |
| **Total** | **250** | **89 + 160 + 1** |

## Test-Site Execution and Verification

- Import: **89 created**, 0 updated; 160 site overrides and 1 technical exception (`Lft`) were not imported.
- Post-import dry-run: `total=3549 created=0 updated=0 skipped=3549 drift=0`.
- Translation health: loader installed, no fallback, no duplicates, no null digests, zero drift (`has_drift: false`, `drift_details: []`), no orphan overrides.
- Arabic Desk UAT preflight: PASS; Redis 13000/11000, `/ping` 200, fresh `ar` boot with 13,851 messages, session logged out, language restored to `en`.
- Browser evidence: `ar`, RTL, Arabic DOM visible, **89/89 released matches**, **249/249 batch keys matched** (250 minus 1 technical exception `Lft`), 0 mismatches.
- Tests: standalone **92/92**, module suite **271/271** across 11 modules.
- Scoped gate, vendor audit, scope/translation lints, and `git diff --check`: PASS; catalog sync: 0 created, 0 updated (`0/0`).
- Inventory: **21,966 rows**, Merkle `5829b33f481d9ae9ef7c07cc597311128d23edae40e26ed8a0c5dc7d37fbec22`, `LIVE_MATCH`.
- Ten Stage-2 evidence envelopes and index were atomically assembled on candidate HEAD `7b2a81cea0e1bcfd876590e431f6c53e5ee035b2`; evidence-inclusive gate exits **0** with `errors=0`, `csv_rows=3549`.
- Final independent AI-R: **PASS**; see `docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-r-accounts-batch02-final-2026-09-27.md`.

## Boundaries

Execution was restricted strictly to `v16.localhost`. Production and Stage 8 remain untouched and gated. The untracked `v16.localhost/` directory was left alone. No push was performed.
