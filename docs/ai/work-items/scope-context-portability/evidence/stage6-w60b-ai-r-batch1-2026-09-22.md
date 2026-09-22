# Stage 6 W6-0b batch-1 — AI-R verification record (2026-09-22)

Canonical session: `/root/stage6_w60b_ai_r_batch1`
Agent/role: independent release verifier (AI-R) — not Builder/A-proposer.

## Scope under verification

| Item | Value |
|---|---|
| Owner-approved batch CSV | `docs/translation/stage6_w60b_batch01_rows_2026-09-22.csv` |
| Batch sha256 | `8916118e82e23a4bc23c338b958090463bc4538d560b954697b33130e73171d3` |
| Batch rows | **271** |
| Technical exclusions (prior package) | `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` (21) — **outside** this runtime cycle |
| Site | `v16.localhost` only |

## Disposition of all 271 approved rows (fail-closed)

| Disposition | Rows | Imported? |
|---|---:|---|
| Released payload (governed import candidates) | **232** | yes (test site) |
| `EXCEPTION-technical` — source==translation format/identifier tokens; keep vendor rendering | **32** | no |
| `preserved-site-override` — plan §12 drift contract (Collapse All, Expand All, Dark, Light, DELETE, email, Phone) | **7** | no |
| **Σ** | **271** | |

Paper trail: `docs/translation/stage6_w60b_payload_applied_rows_2026-09-22.csv` (all 271 dispositions, tab-separated).

## Technical exclusions confirmed (32) — AI-R suppress-check

Symbols/identifiers/date-formats/HTTP verbs/paper-sizes/keyboard chords/font names/code-language names with **no distinct Arabic form** (source-equal under `csv-source-equal`). Classification: `EXCEPTION-technical` (same contract as the 21-row package exclusions).

Confirmed sources:

```text
CSV, PDF, HTML, L, DocType, M, GET, POST, K, yyyy-mm-dd, JSON, dd.mm.yyyy,
B, DocField, T, Python, JS, Helvetica Neue, HEAD, Kh, DocPerm, Meta, SQL,
chrome, Ctrl + Down, Ctrl + Up, A0, A1, A2, A3, A5, A6
```

Rationale: keep vendor code/symbol/markup/format content untouched — technical fragment, no translation. These rows are **not** Released and **not** in `approved_ar_overrides.csv`.

## Site-override preserves (7) — AI-R drift contract (plan §12)

Existing runtime `Site Override` rows (case-insensitive source match) are **not** rewritten:

| source_text | preserved runtime Arabic (site) |
|---|---|
| Collapse All | طيّ الكل |
| Expand All | توسيع الكل |
| Dark | داكن |
| Light | فاتح |
| DELETE | حذف |
| email | البريد الإلكتروني |
| Phone | الهاتف |

Importer must report `drift=0` when the 7 are omitted from the payload CSV.

## Released payload (232) — AI-R proposal checks

- Every Released row has distinct Arabic ≠ source (`csv-source-equal` clean).
- Placeholder parity (`{N}` / `{}`) enforced programmatically at proposal build — zero mismatches.
- Unicode + affix + unsafe-HTML checks: zero errors on the 232.
- `decision_ref` binds each row to `content:docs/translation/stage6_w60b_payload_applied_rows_2026-09-22.csv` (source+translation both present).
- Quorum columns: `AI-A1/AI-A2/AI-A3 (recorded review run)` + `2026-09-22 00:00:00`.
- `release_version 1.2`, `ct_app=frappe`, `domain=desk-short-ui`.
- Glossary v2.0 + vendor ledger gap report + plan D5 references on every row.

## AI-R verdict

**PASS (conditional on post-import gates)** — batch-1 dispositions complete; technical + site-override rows correctly excluded; Released set is decision-bound and quorum-complete.

Post-import conditions (must hold before commit):

1. DRY_RUN twice: final idempotent state `total=682 / created=0 / updated=0 / skipped=682 / drift=0` (and pre-import first dry may show created=232).
2. IMPORT on `v16.localhost` only: `created=232`, `drift=0`.
3. `release_decisions.json` records 682 decisions with intact `csv-decision-identity` / dataset binding.
4. Freshness + manifest re-recorded (`packaged_rows=682`).
5. `EXPECTED_DRYRUN` / decision-count test / evidence envelopes updated; standalone suite green.

## Boundaries

- Batches 02–07: not approved, not translated, not imported.
- Stage 8 / production: not authorized (`production_mutation_authorized: false`).
- No restore/overwrite of `v16.localhost`.
