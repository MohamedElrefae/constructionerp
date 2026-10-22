# W6-1 Accounts Batch 03 — governed cycle closed (2026-09-27)

## Scope and Review

Owner approval applied only to `stage6_w601_accounts_batch03_rows_2026-09-27.csv` (250 rows; SHA-256 `dfa6de55bb986c5e7b6fc845ad9b3de7de2a0f6c38c441cf4cf2c8427713d1cb`) on the non-production test site `v16.localhost`. The proposal CSV is `stage6_w601_accounts_batch03_proposal_2026-09-27.csv` (SHA-256 `3b0a3ee8d6c9b6a1c59d925aea5c2ed71059c07698e1935c9c65b385c464ef3f`). Independent A1/A2/A3 reviews and final AI-R all reported PASS.

| Disposition | Rows | Treatment |
| --- | ---: | --- |
| Released payload | 120 | Imported as release v1.13 |
| Preserved Site Override (exact) | 128 | Left unchanged; not imported (plan §12) |
| Preserved Site Override (strip-collision) | 1 | `Only Deduct Tax On Excess Amount ` — preserved live site override; not imported (plan §12) |
| Technical exception | 1 | `Period_from_date` — internal bisect node traversal column label; untranslated |
| **Total** | **250** | **120 + 128 + 1 + 1** |

### Strip-Collision Amendment (Plan §12)
- One candidate payload row (`"Only Deduct Tax On Excess Amount "`) has a runtime lookup strip-collision with the pre-existing Site Override (`"Only Deduct Tax On Excess Amount"`). Per Plan §12, existing Site Overrides are strictly protected from catalog overwrites. This entry was reclassified to `preserved-site-override (strip-collision)` and excluded from the catalog release to prevent runtime drift.
- Edge whitespace on candidate row `"New fiscal year created :- "` was normalized on both source and translation sides following the W6-2 convention to ensure exact 1:1 runtime digest and zero drift.

## Test-Site Execution and Verification

- Import: **120 created**, 0 updated; 128 site overrides, 1 strip-collision, and 1 technical exception (`Period_from_date`) were not imported.
- Post-import dry-run: `total=3669 created=0 updated=0 skipped=3669 drift=0`.
- Translation health: loader installed, no fallback, no duplicates, no null digests, zero drift (`has_drift: false`, `drift_details: []`), no orphan overrides.
- Arabic Desk UAT preflight: PASS; Redis 13000/11000, `/ping` 200, fresh `ar` boot with 13,971 messages, session logged out, language restored to `en`.
- Browser evidence: `ar`, RTL, Arabic DOM visible, **120/120 released matches**, **249/249 batch keys matched** (250 minus 1 technical exception `Period_from_date`), 0 mismatches.
- Tests: standalone **92/92**, module suite **271/271** across 11 modules.
- Scoped gate, vendor audit, scope/translation lints, and `git diff --check`: PASS; catalog sync: 0 created, 0 updated (`0/0`).
- Inventory: **22,086 rows**, Merkle `b8889b90f566810af4f7a3cbea3f33ee49e190fe0b14dc2076960cbd578cb2a1`, `LIVE_MATCH`.
- Ten Stage-2 evidence envelopes and index were atomically assembled on candidate HEAD `7ff9290aaab110f424e8e16dd4a5e5fda8bf2bf5`; evidence-inclusive gate exits **0** with `errors=0`, `csv_rows=3669`.
- Final independent AI-R: **PASS**; see `docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-r-accounts-batch03-final-2026-09-27.md`.

## Boundaries

Execution was restricted strictly to `v16.localhost`. Production and Stage 8 remain untouched and gated. The untracked `v16.localhost/` directory was left alone. No push was performed.
