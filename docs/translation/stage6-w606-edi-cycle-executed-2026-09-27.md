# W6-6 EDI Remainder — governed cycle closed (2026-09-27)

## Scope and Review

Owner approval applied to `stage6_w606_edi_rows_2026-09-27.csv` (26 rows; SHA-256 `2b0cc9b46546aa36310f81738c72ff0d2b50ca35666110033976c424c149cef1`) on the non-production test site `v16.localhost`. The proposal CSV is `stage6_w606_edi_proposal_2026-09-27.csv` (SHA-256 `ea74475780980e95f13346db8aaf8beb7b56c3202336950ae9432f2d2eebb6b7`). Independent A1/A2/A3 reviews and final AI-R all reported PASS.

| Disposition | Rows | Treatment |
| --- | ---: | --- |
| Released payload | 17 | Imported as release v1.16 (domain `edi`) |
| Preserved Site Override | 9 | Left unchanged; not imported (plan §12) |
| Technical exception | 0 | None in this batch |
| **Total** | **26** | **17 + 9** |

### Complete W6-6 Domain Closure (Stage 6 Remains Open Pending W6-7)
With the EDI Remainder closed, all components of the W6-6 domain are fully localized, reconciled, verified, and committed:
- **Manufacturing Batch 01:** 150 rows
- **Manufacturing Batch 02:** 150 rows
- **Assets:** 120 rows
- **CRM / Support / Maintenance:** 220 rows
- **EDI Remainder:** 26 rows (17 released, 9 preserved site overrides)
- **Grand Catalog Progression:** The catalog grew by +17 rows from 3,830 to 3,847 rows.

**Stage 6 Status Note:** While W6-6 is closed, **Stage 6 overall remains open** because W6-7 remains unresolved in the master plan (`ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md`). Any further Stage-6 work requires a separate bounded proposal and owner approval.

## Test-Site Execution and Verification

- Import: **17 created**, 0 updated; 9 site overrides preserved without alteration.
- Post-import dry-run: `total=3847 created=0 updated=0 skipped=3847 drift=0`.
- Translation health: loader installed, no fallback, no duplicates, no null digests, zero drift (`has_drift: false`, `drift_details: []`), no orphan overrides.
- Arabic Desk UAT preflight: PASS; Redis 13000/11000, `/ping` 200, fresh `ar` boot with 14,149 messages, session logged out, language restored to `en`.
- Browser evidence: `ar`, RTL, Arabic DOM visible, **17/17 released matches**, **26/26 batch keys matched**, 0 mismatches.
- Tests & Gate checks: `python3 scripts/check_localization_gates.py` exits **0** with `errors=0`, `csv_rows=3847`.
- Inventory: **22,264 rows**, Merkle `fdc2edd0672d11f75d780fd22bdbcea2bca82abe2eeb3a906c96c978b2928bd1`.
- Ten Stage-2 evidence envelopes and index were atomically assembled on candidate HEAD `2ab9e86716bcadf94b245eb958f101ce56af221a`; evidence-inclusive gate exits **0** with `errors=0`, `csv_rows=3847`.
- Final independent AI-R: **PASS**; see `docs/ai/work-items/scope-context-portability/evidence/stage6-w606-ai-r-edi-final-2026-09-27.md`.

## Boundaries

Execution was restricted strictly to `v16.localhost`. Production and Stage 8 remain untouched and gated. The untracked `v16.localhost/` directory was left alone. No push was performed.
