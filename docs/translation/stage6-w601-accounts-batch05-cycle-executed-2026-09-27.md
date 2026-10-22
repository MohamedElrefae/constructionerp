# W6-1 Accounts Batch 05 — governed cycle closed (2026-09-27)

## Scope and Review

Owner approval applied to `stage6_w601_accounts_batch05_rows_2026-09-27.csv` (56 rows; SHA-256 `10c2f94face1a476350e386dd0d176045a13fc8b800f3fb90cd5806cf41353c7`) on the non-production test site `v16.localhost`. The proposal CSV is `stage6_w601_accounts_batch05_proposal_2026-09-27.csv` (SHA-256 `74fedcf4313d4dff102755cc054cd1cfc3d28ce45705a6e686a9380f47c51c70`). Independent A1/A2/A3 reviews and final AI-R all reported PASS.

| Disposition | Rows | Treatment |
| --- | ---: | --- |
| Released payload | 40 | Imported as release v1.15 |
| Preserved Site Override | 14 | Left unchanged; not imported (plan §12) |
| Technical exception | 2 | `exchangerate.host`, `frankfurter.dev` — external exchange rate API domain hostnames; untranslated |
| **Total** | **56** | **40 + 14 + 2** |

### Complete W6-1 Accounts Closure
With Batch 05 closed, all 5 batches comprising the entire W6-1 Accounts domain (1,056 rows total) are fully localized, reconciled, verified, and committed:
- **Batch 01:** 250 rows (96 released, 153 preserved site overrides [147 exact + 6 strip-collision], 1 already-released row `"Cost Center"`)
- **Batch 02:** 250 rows (89 released, 160 preserved site overrides, 1 technical exception `Lft`)
- **Batch 03:** 250 rows (120 released, 129 preserved site overrides [128 exact + 1 strip-collision], 1 technical exception `Period_from_date`)
- **Batch 04:** 250 rows (121 released, 128 preserved site overrides [125 exact + 3 strip-collision], 1 technical exception `Rgt`)
- **Batch 05:** 56 rows (40 released, 14 preserved site overrides, 2 technical exceptions `exchangerate.host`, `frankfurter.dev`)
- **W6-1 Accounts Grand Total:** 1,056 rows accounted for (466 newly released into catalog, 584 preserved site overrides [574 exact + 10 strip-collision], 1 already-released row, 5 technical exceptions). The catalog grew from 3,364 to 3,830 (+466 rows).

## Test-Site Execution and Verification

- Import: **40 created**, 0 updated; 14 site overrides and 2 technical exceptions (`exchangerate.host`, `frankfurter.dev`) were not imported.
- Post-import dry-run: `total=3830 created=0 updated=0 skipped=3830 drift=0`.
- Translation health: loader installed, no fallback, no duplicates, no null digests, zero drift (`has_drift: false`, `drift_details: []`), no orphan overrides.
- Arabic Desk UAT preflight: PASS; Redis 13000/11000, `/ping` 200, fresh `ar` boot with 14,132 messages, session logged out, language restored to `en`.
- Browser evidence: `ar`, RTL, Arabic DOM visible, **40/40 released matches**, **54/54 batch keys matched** (56 minus 2 technical exceptions), 0 mismatches.
- Tests: standalone **92/92**.
- Gate checks: `python3 scripts/check_localization_gates.py` exits **0** with `errors=0`, `csv_rows=3830`.
- Inventory: **22,247 rows**, Merkle `47920b40abbc6a4384d01d2b25ac7b8882a9a5cd1c294fcf5d84f8cfda278a74`, `LIVE_MATCH`.
- Ten Stage-2 evidence envelopes and index were atomically assembled on candidate HEAD `359a1addd2929d62529ff10d8eb57254bcac11dc`; evidence-inclusive gate exits **0** with `errors=0`, `csv_rows=3830`.
- Final independent AI-R: **PASS**; see `docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-r-accounts-batch05-final-2026-09-27.md`.

## Boundaries

Execution was restricted strictly to `v16.localhost`. Production and Stage 8 remain untouched and gated. The untracked `v16.localhost/` directory was left alone. No push was performed.
