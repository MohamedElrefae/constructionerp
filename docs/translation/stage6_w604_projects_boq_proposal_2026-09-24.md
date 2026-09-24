# Stage 6 — W6-4 Projects + BOQ adjacency scope and proposal (2026-09-24)

## Scope result

The matrix estimate is 151 raw first-location candidates: 61 Projects and 90 Subcontracting. Applying the existing proposal-cut rules produces an exact **147-row bounded scope**:

- CSV: `docs/translation/stage6_w604_projects_boq_rows_2026-09-24.csv`
- Rows: **147** data rows, 60 Projects + 87 Subcontracting
- SHA-256: `93fbf16b14940ce2d477f346c1777865bf008b22df943625e7de84f27e8f4abe`
- Serialization: UTF-8, LF line endings, no BOM, sorted by `(area, source_text)`

This document records the original scope proposal. Owner approval and the
governed cycle outcome are recorded in the appended closure addendum below;
the exact scope CSV and SHA above remain unchanged.

## Raw accounting and exclusions

| Bucket | Rows | Treatment |
|---|---:|---|
| Raw first-location candidates | 151 | Matrix estimate: 61 Projects + 90 Subcontracting |
| `skip=yes` | 1 | Exclude before scope cut: `{0}%` |
| HTML/template | 1 | Exclude: `<span class="h4"><b>Subcontracting Inward and Outward</b></span>` |
| Embedded newline/CR | 1 | Exclude: `Row {0}: Consumed Qty {1} {2} must be less than or equal to Available Qty For Consumption...` |
| Length > 120 | 1 | Exclude: `Click this button if you encounter a negative stock error...` |
| Released catalog / decisions / prior scopes / shared exclusions | 0 | No overlap |
| **Proposal scope** | **147** | 60 Projects + 87 Subcontracting |

The 147 rows contain 96 ledger-prefilled suggestions and 51 unfilled rows requiring later AI proposal work if approved. The proposal-cut technical-token heuristic identifies zero technical rows. Site-override preservation is intentionally unassessed because no live-site inspection was performed.

## Proposed disposition at proposal stage

| Disposition | Rows | Meaning |
|---|---:|---|
| `PROPOSED-payload` | 147 | Candidate rows for later independent review; not Released |
| `preserved-site-override` | Unknown | Requires authorized read-only site recon after approval |
| `EXCEPTION-technical` | 0 at cut stage | No technical-token candidate identified |
| `DEFERRED-source-defect` | 0 at cut stage | Requires later source review if found |
| Already released | 0 | No scope key is in the current Released catalog |

## Overlap checks

All checks are repository-read-only and use the committed inputs at branch HEAD `eaadb01`.

| Check | Result |
|---|---:|
| Current Released catalog, exact source | 0 / 147 |
| Current Released catalog, edge-whitespace normalized | 0 / 147 |
| Current release decisions | 0 / 147 |
| W6-0a desk shell (362 keys) | 0 |
| W6-0b short UI (1,915 keys) | 0 |
| W6-1 accounting subset (147 keys) | 0 |
| W6-2 batch 01 (270 keys) | 0 |
| W6-2 batch 02 (48 keys) | 0 |
| W6-3 batches 01–03 (734 keys) | 0 |
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

`python3 scripts/stage6_w604_projects_boq_cut_2026-09-24.py` reproduces the exact CSV and hash. The script reads repository inputs and writes only the proposal CSV; it does not access the site or modify the catalog, decisions, manifests, evidence, or gates.

Branch state: `develop` at `eaadb01`, synchronized with `origin/develop`; the existing untracked `v16.localhost/` directory was not touched.

**Proposal-stage boundary (superseded by the closure addendum below):** owner
approval was required before any W6-4 quorum, site recon, import,
catalog/decision write, or evidence re-pin. Stage 8 and production remain
separately gated.

## Owner approval and cycle outcome

The owner approved this exact 147-row scope, CSV SHA
`93fbf16b14940ce2d477f346c1777865bf008b22df943625e7de84f27e8f4abe`, for a
governed run on `v16.localhost` only. The cycle is closed with 48 payload rows
released, 96 Site Overrides preserved, and 3 runtime/format rows deferred.
See [`stage6-w604-cycle-executed-2026-09-24.md`](stage6-w604-cycle-executed-2026-09-24.md)
for live verification, evidence, and boundaries. Stage 8 and production remain
on hold.
