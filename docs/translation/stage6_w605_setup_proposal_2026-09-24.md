# Stage 6 — W6-5 Setup/admin proposal only (2026-09-24)

## Scope result

The workflow matrix estimates **484** W6-5 candidates. The committed ERPNext ledger contains **483 unique** first-location `erpnext/setup/` msgids; the one-row difference is a matrix estimate variance, not an omitted ledger row.

Applying the existing proposal-cut rules produces an exact **469-row bounded scope**:

- CSV: `docs/translation/stage6_w605_setup_rows_2026-09-24.csv`
- Rows: **469** data rows
- SHA-256: `e2d672c4a1b479f9cd52c017f76a3c8a8b1b24dced24ed4b5f5c6d8113900a09`
- Serialization: UTF-8, LF line endings, no BOM, sorted by `source_text`

This is proposal-only. It is not an import approval and does not assert live-site preservation.

## Raw accounting and exclusions

| Bucket | Rows | Treatment |
|---|---:|---|
| Matrix estimate | 484 | Planning estimate only |
| Unique ledger candidates | 483 | Deterministic first-location Setup rows |
| `skip=yes` | 0 | None |
| HTML/template | 4 | Exclude from scope |
| Embedded newline/CR | 0 | None |
| Length > 120 | 10 | Exclude from scope |
| Released catalog / decisions / prior scopes / shared exclusions | 0 | No overlap |
| **Proposal scope** | **469** | Setup candidates |

The 469 rows contain 106 ledger-prefilled suggestions and 363 unfilled rows. There are 23 rows with brace-style placeholders and 22 rows with multiple locations; these remain subject to later independent review.

## Proposed disposition at proposal stage

| Disposition | Rows | Meaning |
|---|---:|---|
| `PROPOSED-payload` | 454 | Candidate rows for later A1/A2/A3 review; not Released |
| `PROPOSED-EXCEPTION-technical` | 15 | Unit/acronym/force-unit candidates requiring technical review |
| `preserved-site-override` | Unknown | Requires authorized read-only site recon after approval |
| `DEFERRED-source-defect` | 0 at cut stage | Requires later source review if found |
| Already released | 0 | No scope key is in the current Released catalog |

The 15 technical candidates are unit/force terms and the acronym keys `FIFO` and `LIFO`; the latter two have ledger-prefilled Arabic values and must not be auto-classified without A1/A2 review.

## Source-key and terminology risks

- `A Transaction Deletion Document: {0} is triggered for {0}` repeats the same positional placeholder; placeholder semantics require explicit review.
- Rows using `{}` versus `{0}`/`{1}` require placeholder multiset parity checks during review.
- 22 rows have multiple source locations; first-location ownership is deterministic, but cross-area terminology should be checked by A2.
- The 15 technical candidates include units such as `Ampere-Hour`, `Gram-Force`, `Litre-Atmosphere`, and `Watt-Hour`, plus `FIFO`/`LIFO`; source-equal technical handling must be decided explicitly.
- The 106 prefilled suggestions are not automatically approved payloads and require the normal independent review chain.

## Overlap checks

All checks are repository-read-only and use committed inputs at branch HEAD `51b8b73`.

| Check | Result |
|---|---:|
| Current Released catalog, exact source | 0 / 469 |
| Current Released catalog, edge-whitespace normalized | 0 / 469 |
| Current release decisions | 0 / 469 |
| W6-0a desk shell (362 keys) | 0 |
| W6-0b short UI (1,915 keys) | 0 |
| W6-1 accounting subset (147 keys) | 0 |
| W6-2 batches 01–02 (318 keys) | 0 |
| W6-3 batches 01–03 (734 keys) | 0 |
| W6-4 Projects + BOQ scope (147 keys) | 0 |
| Shared technical exclusions (21 keys) | 0 |
| Shared dedup exclusions (302 keys) | 0 |
| Internal duplicate source keys | 0 |

## Input fingerprints

| Artifact | SHA-256 |
|---|---|
| `docs/erpnext_ar_missing_review_filled.csv` | `7e72ed615fc75a0e82497d415fb4d9e19c3c9ba1e86fafca47ae08b580ae94e5` |
| `construction/data/translations/approved_ar_overrides.csv` | `78ee35b2c0ea322527ccbe6272244794cd8524dd86f5df84a0c4f34f262d0016` |
| `construction/data/translations/release_decisions.json` | `18d6dcecb373d955b759ddb5a4eb0aeb1e413889739851f509f20438232388ee` |
| `stage6_w60b_technical_exclusions_2026-09-22.csv` | `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` |
| `stage6_w60b_dedup_exclusions_2026-09-22.csv` | `ee24f18fdfd451204e18e26c17c8d9e2fc6a7539efa634087f5f7de4848fe37b` |

## Reproduction and boundary

`python3 scripts/stage6_w605_setup_cut_2026-09-24.py` reproduces the exact CSV and hash. It reads repository inputs and writes only the proposal CSV; it does not access the site or modify the catalog, decisions, manifests, evidence, or gates.

Branch state: `develop` at `51b8b73`, one commit ahead of `origin/develop`; the existing untracked `v16.localhost/` directory was not touched.

**Owner approval of the exact CSV and SHA is required before any W6-5 quorum, site recon, import, catalog/decision write, evidence re-pin, Stage 8 action, or production action.**
