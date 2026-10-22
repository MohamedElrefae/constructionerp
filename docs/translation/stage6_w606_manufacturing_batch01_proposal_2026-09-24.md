# Stage 6 — W6-6 Manufacturing batch 01 proposal

**Status: proposal only; owner approval pending.** This package contains an
offline deterministic cut only. No reviewer quorum, test-site reconciliation,
import, catalog/decision update, evidence re-pin, commit, or push was performed
for this Manufacturing scope.

## Exact batch proposed

- Scope CSV: `docs/translation/stage6_w606_manufacturing_batch01_rows_2026-09-24.csv`
- Rows: **250**
- SHA-256: `0d5098f61e2f97d26fa40e4e8b5d3b90ab1ec22e9dafd543564cb07ec8d39286`
- Deterministic builder: `scripts/stage6_w606_manufacturing_batch01_cut_2026-09-24.py`
- Domain: ERPNext Manufacturing, first-location classification from the
  committed ERPNext Arabic gap ledger.

Batch 01 is the first 250 fresh source keys in lexical `source_text` order.
There are **200** additional fresh Manufacturing keys after this cut; they are
not included or approved by this proposal.

## Reconciliation and boundaries

| Bucket | Rows | Treatment |
|---|---:|---|
| Raw ledger rows | 481 | Manufacturing first-location rows |
| Unique source keys | 480 | One duplicate source key collapsed |
| `skip=yes` | 1 | Excluded |
| HTML | 6 | Excluded (checked before line/length rules) |
| Embedded newline/CR | 3 | Excluded after HTML filtering |
| Over 120 characters | 19 | Excluded after HTML/newline filtering |
| Already covered by catalog/decisions | 1 | Excluded: `Subcontracting` |
| Fresh remaining candidates | 450 | 250 in this proposal + 200 held back |
| **Batch 01** | **250** | **167 prefilled suggestions + 83 blank rows** |

Batch 01 has zero overlap with prior Stage-6 scope CSVs, the shared technical
exclusions, or the shared dedup exclusions. No Arabic proposals have been
authored for the 83 blank rows; any cycle after approval must run independent
A1/A2/A3 review and AI-R before test-site import.

## Reproducibility inputs

The builder validates the raw/unique/exclusion counts, current Released
catalog and decision coverage, all prior `stage6_*rows*.csv` scopes, and the
exact fresh candidate count before writing the CSV.

| Input | SHA-256 |
|---|---|
| `docs/erpnext_ar_missing_review_filled.csv` | `7e72ed615fc75a0e82497d415fb4d9e19c3c9ba1e86fafca47ae08b580ae94e5` |
| `construction/data/translations/approved_ar_overrides.csv` | `b68f75eaee334edde2a8173f459e33fad802578c236e9a5019deb26ebd5daf5a` |
| `construction/data/translations/release_decisions.json` | `72a633b8f2084dfdf0f5f986a7498a9769ec7eba10fc31742d90accdc588c8d7` |
| Proposed batch CSV | `0d5098f61e2f97d26fa40e4e8b5d3b90ab1ec22e9dafd543564cb07ec8d39286` |

The proposal is based on `develop` at `30c6277` (now pushed to
`origin/develop`). Stage 8 and production remain held. This package does not
authorize a site change or the other 200 candidate rows.

## Owner decision requested

Approve or revise only this exact 250-row scope by referring to its path and
SHA-256 above. Until then, no quorum, test-site mutation, or import will run.
