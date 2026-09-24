# Stage 6 — W6-6 Assets domain proposal only (2026-09-24)

## Scope result

The committed ERPNext ledger (`docs/erpnext_ar_missing_review_filled.csv`) contains **220 unique** first-location `erpnext/assets/` msgids.

Applying the governed proposal-cut rules produces an exact **211-row bounded scope**:

- CSV: `docs/translation/stage6_w606_assets_rows_2026-09-24.csv`
- Rows: **211** data rows
- SHA-256: `6f142646ae55cf147751e8d751f10638c79420dfa184855985ecd6068ee63a40`
- Serialization: UTF-8, LF line endings, no BOM, sorted by `source_text`

This is proposal-only. It is not an import approval and does not perform live-site mutations.

## Raw accounting and exclusions

| Bucket | Rows | Treatment |
|---|---:|---|
| Unique ledger candidates | 220 | Deterministic first-location Assets rows |
| `skip=yes` in ledger | 1 | Excluded (`{}` format placeholder token) |
| HTML tags | 5 | Excluded from scope (rich formatting / HTML fragments) |
| Embedded newline/CR | 1 | Excluded from scope (multi-line error string) |
| Length > 120 (non-HTML, non-newline) | 2 | Excluded from scope (>120 char policy) |
| Released catalog / decisions / prior scopes / shared exclusions | 0 | No overlap (100% fresh candidates) |
| **Proposal scope** | **211** | **Assets domain candidates** |

The 211 rows contain 98 ledger-prefilled suggestions and 113 unfilled rows. There are 45 rows with brace-style placeholders (`{0}`, `{1}`, etc.) and 6 rows with multiple source locations; these remain subject to later independent review upon scope approval.

## Proposed preliminary disposition

| Disposition | Rows | Meaning |
|---|---:|---|
| `PROPOSED-payload` | 113 | Candidate rows for later A1/A2/A3 review and catalog release |
| `preserved-site-override` | 98 | Live Site Overrides identified in read-only test-site reconciliation |
| `EXCEPTION-technical` | 0 | Zero compound unit/acronym tokens identified |
| `DEFERRED-source-defect` | 0 at cut stage | Requires later review if any defect discovered |
| Already released | 0 | No scope key is in the current Released catalog |
| **Total** | **211** | **Exact 1-to-1 scope reconciliation** |

The 98 live Site Overrides already exist on `v16.localhost` with non-empty translations and will be preserved verbatim without replacement. The 113 payload rows are empty on `v16.localhost` and will undergo independent A1/A2/A3 quorum review once this scope is approved.

## Excluded rows detail

1. **HTML rows (5):**
   - `<b>Cannot create asset.</b><br><br>You're trying to create <b>{0} asset(s)</b> from {2} {3}.<br>However, only <b>{1} item(s)</b> were purchased and <b>{4} asset(s)</b> already exist against {5}.` (194 chars)
   - `<span class="h4"><b>Reports & Masters</b></span>` (48 chars)
   - `<span class="h4"><b>Your Shortcuts</b></span>` (45 chars)
   - `Asset Depreciation Schedules created/updated:<br>{0}<br><br>Please check, edit if needed, and submit the Asset.` (111 chars)
   - `Net Purchase Amount should be <b>equal</b> to purchase amount of one single Asset.` (82 chars)
2. **Newline / overlong rows (1):**
   - `Error: This asset already has {0} depreciation periods booked.\n\t\t\t\t\tThe \`depreciation start\` date must be at least {1} periods after the \`available for use\` date.\n\t\t\t\t\tPlease correct the dates accordingly.` (205 chars)
3. **Overlong >120 chars rows (2):**
   - `Row #{0}: Expense account {1} is not valid for Purchase Invoice {2}. Only expense accounts from non-stock items are allowed.` (124 chars)
   - `This asset category is marked as non-depreciable. Please disable depreciation calculation or choose a different category.` (121 chars)
4. **Skipped ledger token (1):**
   - `{}` (empty format string marked `skip=yes` in ledger)

## Overlap checks

All checks are repository-read-only and use committed inputs at branch HEAD `64abce7`.

| Check | Result |
|---|---:|
| Current Released catalog (3,048 rows), exact source | 0 / 211 |
| Current Released catalog, edge-whitespace normalized | 0 / 211 |
| Current release decisions (3,048 decisions) | 0 / 211 |
| Prior scopes W6-0a through W6-5 | 0 / 211 |
| Shared technical exclusions | 0 / 211 |
| Shared dedup exclusions | 0 / 211 |
| Internal duplicate source keys | 0 |

## Input fingerprints

| Artifact | SHA-256 |
|---|---|
| `docs/erpnext_ar_missing_review_filled.csv` | `7e72ed615fc75a0e82497d415fb4d9e19c3c9ba1e86fafca47ae08b580ae94e5` |
| `construction/data/translations/approved_ar_overrides.csv` | `fbc40cdc4e4fb36d7ac94c1c08b14a584198e6668c3554caf58a4f2f854073a2` |
| `construction/data/translations/release_decisions.json` | `e77fb439c4f009c5056fd6065fced2ee77598b5374da9868145b46efda374102` |
| `stage6_w60b_technical_exclusions_2026-09-22.csv` | `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` |
| `stage6_w60b_dedup_exclusions_2026-09-22.csv` | `ee24f18fdfd451204e18e26c17c8d9e2fc6a7539efa634087f5f7de4848fe37b` |

## Reproduction and boundary

`python3 scripts/stage6_w606_assets_cut_2026-09-24.py` reproduces the exact CSV and hash. It reads repository inputs and writes only the proposal CSV; it does not modify the catalog, decisions, manifests, evidence, or gates.

Branch state: `develop` at `64abce7`, matching `origin/develop`. The existing untracked `v16.localhost/` directory was not touched.

**Owner approval of the exact CSV and SHA is required before any W6-6 quorum review, test-site import, catalog/decision write, evidence re-pin, Stage 8 action, or production action.**
