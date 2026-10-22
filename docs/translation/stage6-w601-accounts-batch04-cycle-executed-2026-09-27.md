# W6-1 Accounts Batch 04 — governed cycle closed (2026-09-27)

## Scope and Review

Owner approval applied to `stage6_w601_accounts_batch04_rows_2026-09-27.csv` (250 rows; SHA-256 `0286741911fbe377c0a723131611d8a91cbe7c943c59d307756d7e1f18cfae30`) on the non-production test site `v16.localhost`. The proposal CSV is `stage6_w601_accounts_batch04_proposal_2026-09-27.csv` (SHA-256 `4c72e83b3d41476914dcf884a8798c51ec5f6e662500105509fc2b8aad6bc47a`). Independent A1/A2/A3 reviews and final AI-R all reported PASS.

| Disposition | Rows | Treatment |
| --- | ---: | --- |
| Released payload | 121 | Imported as release v1.14 |
| Preserved Site Override (exact) | 125 | Left unchanged; not imported (plan §12) |
| Preserved Site Override (strip-collision) | 3 | `Role Allowed to Over Bill `, `Sales Partner `, `Select Dispatch Address ` — preserved live site overrides; not imported (plan §12) |
| Technical exception | 1 | `Rgt` — internal NestedSet right bound column; untranslated |
| **Total** | **250** | **121 + 125 + 3 + 1** |

### Strip-Collision Amendment (Plan §12)
- Three candidate payload rows (`"Role Allowed to Over Bill "`, `"Sales Partner "`, `"Select Dispatch Address "`) have runtime lookup strip-collisions with pre-existing Site Overrides (`"Role Allowed to Over Bill"`, `"Sales Partner"`, `"Select Dispatch Address"`). Per Plan §12, existing Site Overrides are strictly protected from catalog overwrites. These entries were reclassified to `preserved-site-override (strip-collision)` and excluded from the catalog release to prevent runtime drift.

## Test-Site Execution and Verification

- Import: **121 created**, 0 updated; 125 site overrides, 3 strip-collisions, and 1 technical exception (`Rgt`) were not imported.
- Post-import dry-run: `total=3790 created=0 updated=0 skipped=3790 drift=0`.
- Translation health: loader installed, no fallback, no duplicates, no null digests, zero drift (`has_drift: false`, `drift_details: []`), no orphan overrides.
- Arabic Desk UAT preflight: PASS; Redis 13000/11000, `/ping` 200, fresh `ar` boot with 14,092 messages, session logged out, language restored to `en`.
- Browser evidence: `ar`, RTL, Arabic DOM visible, **121/121 released matches**, **249/249 batch keys matched** (250 minus 1 technical exception `Rgt`), 0 mismatches.
- Tests: standalone **92/92**, module suite **271/271** across 11 modules.
- Scoped gate, vendor audit, scope/translation lints, and `git diff --check`: PASS; catalog sync: 0 created, 0 updated (`0/0`).
- Inventory: **22,207 rows**, Merkle `a6432de6a030b2bf4883b721a9a515d9a12bf526764461307c53de235db332cb`, `LIVE_MATCH`.
- Ten Stage-2 evidence envelopes and index were atomically assembled on candidate HEAD `84919dd4ff11ed31b604ba43d1770d51405b4841`; evidence-inclusive gate exits **0** with `errors=0`, `csv_rows=3790`.
- Final independent AI-R: **PASS**; see `docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-r-accounts-batch04-final-2026-09-27.md`.

## Boundaries

Execution was restricted strictly to `v16.localhost`. Production and Stage 8 remain untouched and gated. The untracked `v16.localhost/` directory was left alone. No push was performed.
