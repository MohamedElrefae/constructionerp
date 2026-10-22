# Stage 6 W6-0b batch-6 — AI-R verification record (2026-09-22)

Canonical session: `/root/stage6_w60b_ai_r_batch6`
Agent/role: independent release verifier (AI-R) — not Builder/A-proposer.

## Scope under verification

| Item | Value |
|---|---|
| Owner-approved batch CSV | `docs/translation/stage6_w60b_batch06_rows_2026-09-22.csv` |
| Batch sha256 | `68500fae981aacec08e9841fc858dfd43e7473c7b12156ac8ca528b678d309e0` |
| Batch rows | **270** |
| Technical exclusions (prior package) | `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` (21) — **outside** this runtime cycle |
| Site | `v16.localhost` only |

## Disposition of all 270 approved rows (fail-closed)

| Disposition | Rows | Imported? |
|---|---:|---|
| Released payload (governed import candidates) | **258** | yes (test site) |
| `EXCEPTION-technical` — source==translation format/identifier tokens; keep vendor rendering | **11** | no |
| `preserved-site-override` — plan §12 drift contract | **1** | no |
| **Σ** | **270** | |

Paper trail: `docs/translation/stage6_w60b_payload_applied_rows_batch06_2026-09-22.csv` (all 270 dispositions, tab-separated).

## Technical exclusions confirmed (11) — AI-R suppress-check

Format/identifier/brand tokens with **no distinct Arabic form** (source-equal under `csv-source-equal`). Classification: `EXCEPTION-technical`.

Confirmed sources:

```text
InnoDB, Geoapify, Keycloak, Nomatim, DocShare, Awesomebar, Mx,
Code challenge method, Collapsible Depends On (JS),
Mandatory Depends On (JS), By \"Naming Series\" field
```

Rationale: keep vendor code/symbol/brand/format content untouched — technical fragment, no translation. These rows are **not** Released and **not** in `approved_ar_overrides.csv`.

## Site-override preserves (1) — AI-R drift contract (plan §12)

Existing runtime `Site Override` rows (case-insensitive source match) are **not** rewritten:

| source_text | preserved runtime Arabic (site) |
|---|---|
| City | المدينة |

Importer must report `drift=0` when the 1 is omitted from the payload CSV.

## Released payload (258) — AI-R proposal checks

- Every Released row has distinct Arabic ≠ source (`csv-source-equal` clean).
- Placeholder parity (`{N}` / `{}` / `{e}`) enforced programmatically at proposal build — zero mismatches on 54 placeholder rows.
- Unicode + affix + unsafe-HTML checks: zero errors on the 258.
- `decision_ref` binds each row to `content:docs/translation/stage6_w60b_payload_applied_rows_batch06_2026-09-22.csv` (source+translation both present).
- Quorum columns: `AI-A1/AI-A2/AI-A3 (recorded review run)` + `2026-09-22 00:00:00`.
