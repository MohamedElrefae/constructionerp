# Stage 6 W6-0b batch-2 — AI-R verification record (2026-09-22)

Canonical session: `/root/stage6_w60b_ai_r_batch2`
Agent/role: independent release verifier (AI-R) — not Builder/A-proposer.

## Scope under verification

| Item | Value |
|---|---|
| Owner-approved batch CSV | `docs/translation/stage6_w60b_batch02_rows_2026-09-22.csv` |
| Batch sha256 | `187361ab36ea2ab75f32355bce0b2b1c274b52bebd339b0c19ea3822436895db` |
| Batch rows | **271** |
| Technical exclusions (prior package) | `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` (21) — **outside** this runtime cycle |
| Site | `v16.localhost` only |

## Disposition of all 271 approved rows (fail-closed)

| Disposition | Rows | Imported? |
|---|---:|---|
| Released payload (governed import candidates) | **243** | yes (test site) |
| `EXCEPTION-technical` — source==translation format/identifier tokens; keep vendor rendering | **26** | no |
| `preserved-site-override` — plan §12 drift contract (Country, Not Permitted) | **2** | no |
| **Σ** | **271** | |

Paper trail: `docs/translation/stage6_w60b_payload_applied_rows_batch02_2026-09-22.csv` (all 271 dispositions, tab-separated).

## Technical exclusions confirmed (26) — AI-R suppress-check

Symbols/identifiers/paper-sizes/font-names/code-language names with **no distinct Arabic form** (source-equal under `csv-source-equal`). Classification: `EXCEPTION-technical`.

Confirmed sources:

```text
A7, A8, A9, B0, B1, B2, B3, B4, B5, B6, B7, B8, B9, B10,
C5E, Comm10E, CSS, DLE, BCC, XMLHttpRequest Error, Inter,
Folio, Tabloid, vscode, Doctype, Ar
```

Rationale: keep vendor code/symbol/markup/format content untouched — technical fragment, no translation. These rows are **not** Released and **not** in `approved_ar_overrides.csv`.

## Site-override preserves (2) — AI-R drift contract (plan §12)

Existing runtime `Site Override` rows (case-insensitive source match) are **not** rewritten:

| source_text | preserved runtime Arabic (site) |
|---|---|
| Country | البلد |
| Not Permitted | غير مسموح |

Importer must report `drift=0` when the 2 are omitted from the payload CSV.

Site recon (non-empty, non-Site-Origin) also found 7 keys already carrying vendor/packaged Arabic (ESC, Reset To Default, This Month, Blue, Green, Current status, LinkedIn). Those are Released as managed catalog rows (genuine state for exact batch-key identity); only Site Override origins are preserved.

## Released payload (243) — AI-R proposal checks

- Every Released row has distinct Arabic ≠ source (`csv-source-equal` clean).
- Placeholder parity (`{N}` / `{}`) enforced programmatically at proposal build — zero mismatches on 25 placeholder rows.
- Unicode + affix + unsafe-HTML checks: zero errors on the 243.
- `decision_ref` binds each row to `content:docs/translation/stage6_w60b_payload_applied_rows_batch02_2026-09-22.csv` (source+translation both present).
- Quorum columns: `AI-A1/AI-A2/AI-A3 (recorded review run)` + `2026-09-22 00:00:00`.
- `release_version 1.2`, `ct_app=frappe`, `domain=desk-short-ui`.
- Glossary v2.0 + vendor ledger gap report + plan D5 references on every row.
- Batch-1 payload file left intact — batch-1 decision bindings unchanged.

## AI-R verdict

**PASS (conditional on post-import gates)** — batch-2 dispositions complete; technical + site-override rows correctly excluded; Released set is decision-bound and quorum-complete.

Post-import conditions (must hold before commit):

1. DRY_RUN twice: final idempotent state `total=925 / created=0 / updated=0 / skipped=925 / drift=0` (pre-import first dry shows created=243).
2. IMPORT on `v16.localhost` only: `created=243`, `drift=0`.
3. `release_decisions.json` records 925 decisions with intact `csv-decision-identity` / dataset binding.
4. Freshness + manifest re-recorded (`packaged_rows=925`).
5. `EXPECTED_DRYRUN` / decision-count test / evidence envelopes updated; standalone suite green.

## Boundaries

- Batches 03–07: not approved, not translated, not imported.
- Stage 8 / production: not authorized (`production_mutation_authorized: false`).
- No restore/overwrite of `v16.localhost`.
