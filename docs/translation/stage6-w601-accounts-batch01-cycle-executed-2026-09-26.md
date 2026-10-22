# W6-1 Accounts Batch 01 — governed cycle closed (2026-09-26)

## Scope and Review

Owner approval applied only to `stage6_w601_accounts_batch01_rows_2026-09-24.csv` (250 rows; SHA-256 `4910a9e4a0e5f8dd0105d484171ac1dc68e173220a0bed27520fbfc5e8c090fd`) on the non-production test site `v16.localhost`. The proposal CSV is `stage6_w601_accounts_batch01_proposal_2026-09-24.csv` (SHA-256 `226ff8b158a4a17bca77209d2e452fff9eff75fd6479324f3e020e6b24ab2b4e`). Independent A1/A2/A3 reviews and final AI-R all reported PASS.

| Disposition | Rows | Treatment |
| --- | ---: | --- |
| Released payload | 96 | Imported as release v1.11 |
| Preserved Site Override (exact) | 147 | Left unchanged; not imported (plan §12) |
| Preserved Site Override (strip-collision) | 6 | Reclassified out of Released catalog per plan §12; strip-collision with runtime Site Override |
| Already-released | 1 | `Closing [Opening + Total] `; retained from catalog line 52 (v1.2); not re-appended |
| Technical exception | 0 | None in this batch |
| **Total** | **250** | **96 + 147 + 6 + 1** |

### Strip-Collision & Duplicate Amendments (Plan §12)
- Six candidate payload rows (`" Amount"`, `" Name"`, `" Rate"`, `"All Parties "`, `"Apply Tax Withholding Amount "`, `"Customer "`) have runtime lookup strip-collisions with pre-existing Site Overrides (`Amount`, `Name`, `Rate`, `All Parties`, `Apply Tax Withholding Amount`, `Customer`). Per Plan §12, existing Site Overrides are strictly protected from catalog overwrites. These 6 entries were reclassified to `preserved-site-override (strip-collision)` and excluded from the catalog release to prevent runtime drift.
- One candidate row (`"Closing [Opening + Total] "`) was recognized as already present in the catalog as line 52 (`Closing [Opening + Total]`, version 1.2). It was classified as `already-released` and retained without duplication.
- Edge whitespace on the 3 remaining uncollided candidate rows with trailing spaces was normalized on both source and translation sides (`Allow multi-currency invoices against single party account`, `Customer Name:`, `Customer:`) following the W6-2 convention to ensure exact 1:1 runtime digest and zero drift.

## Test-Site Execution and Verification

- Import: **96 created**, 0 updated; 147 site overrides, 6 strip-collisions, and 1 already-released row were not imported.
- Post-import dry-run: `total=3460 created=0 updated=0 skipped=3460 drift=0`.
- Translation health: loader installed, no fallback, no duplicates, no null digests, zero drift (`has_drift: false`, `drift_details: []`), no orphan overrides.
- Arabic Desk UAT preflight: PASS; Redis 13000/11000, `/ping` 200, fresh `ar` boot with 13,762 messages, session logged out, language restored to `en`.
- Browser evidence: `ar`, RTL, Arabic DOM visible, **96/96 released matches**, **250/250 batch keys matched**, 0 mismatches.
- Tests: standalone **92/92**, module suite **271/271** across 11 modules.
- Scoped gate, vendor audit, scope/translation lints, and `git diff --check`: PASS; catalog sync: 0 created, 0 updated (`0/0`).
- Inventory: **21,877 rows**, Merkle `38e7217d69f2913e1bbaf25964f40f269a84594c9bb98b82fe7f79a0ebf356eb`, `LIVE_MATCH`.
- Ten Stage-2 evidence envelopes and index were atomically assembled on candidate HEAD `1a494eb71cdb2b7cafe81ca98e9c33bccf7059e4`; evidence-inclusive gate exits **0** with `errors=0`, `csv_rows=3460`.
- Final independent AI-R: **PASS**; see `docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-r-accounts-batch01-final-2026-09-26.md`.

## Boundaries

Execution was restricted strictly to `v16.localhost`. Production and Stage 8 remain untouched and gated. The untracked `v16.localhost/` directory was left alone. No push was performed.
