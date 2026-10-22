# Stage 2 — Current Catalog Inventory + Continuous Gates (2026-09-05; refreshed)

> Supersedes the 2026-09-04 snapshot below where counts differ. Canonical
> machine-readable record: `construction/data/localization/stage2_inventory_manifest.json`
> (exact SQL predicates, PO hashes, merkle root `8d3701f7…`, UTC stamps).
> The Stage 2 gate is implemented by `scripts/check_localization_gates.py`
> (remediated round 2); this narrative alone is not the gate.

## Current inventory (2026-09-05, after triage adds)

| App | Total | Empty (Pending) | Notes |
|---|---|---:|---|
| frappe | 5,927 | 2,987 | vendor baseline pinned |
| erpnext | 9,014 | 4,335 | vendor baseline pinned |
| construction | 742 | 511 | 729 catalog (218 translated + 511 Pending triage) + 13 runtime; triage adds of 498 + 13 applied with 0 drift |
| untagged legacy runtime | 2,678 | 0 | pre-catalog provenance, untouched |

## Re-sync

`sync_translation_catalog(dry_run=False)` across frappe/erpnext/construction:
2 rows created (vendor PO drift since Stage 0). Catalog sync is current.

## Inventory (`tabTranslation`, lang=ar, 2026-09-05)

| App | Total | Empty (Pending) | Populated | Source-equal | Released |
|---|---|---:|---:|---:|---:|
| frappe | 5,927 | 2,987 | 2,934 | 6 | 25 |
| erpnext | 9,014 | 4,335 | 4,675 | 5 | 11 |
| construction | 231 | 0 | 231 | 0 | 13 |
| untagged legacy runtime | 2,678 | 0 | 2,678 | 0 | 0 |

Review-state totals: Pending 7,321; legacy Approved 7,780; Released 49; Deprecated 2;
2,696 legacy rows with no review status (pre-catalog runtime rows).

Category reading per plan §B1/B2:
- Empty 7,322 → need translation, priority per plan workstream B.
- Populated-unreviewed 7,780 (`Approved` = pre-v4 workflow value, NOT v4 quorum approval).
- Source-equal 11 → 8 legitimate technical tokens (lft, rgt, dd-mm-yyyy, A4, Idx,
  MyISAM, StartTLS, +1); 3 need A1 triage: `Produced`, `Prevdoc DocType`, `Fw: {0}`.
- Released 49 → governed payload rows incl. six Stage 1C labels.
- 2,678 untagged legacy runtime rows → pre-catalog provenance; leave untouched,
  flag for future catalog-attribution pass (not Stage 2).

## Continuous gates (new)

`scripts/check_localization_gates.py` (stdlib-only, deterministic, exit-coded):
PO placeholder parity + affix-mirror + bidi/NUL + duplicates; CSV same + Released
quorum columns + source-equal-vs-allowlist; JSON bidi/NUL scan; `--files` changed-file
mode. Wired into `.github/workflows/linter.yml`. Current result: 4 files, 0 errors.
During development it caught a real rule bug (since fixed): source trailing-space
affix must be mirrored, not flagged.

## Stage 2 gate

Reproducible coverage exists (counts + PO hashes in stage-0 + this file); new
Construction strings and vendor deltas route through catalog triage + gates.
Machine translation populates proposals only (no change in this stage).
