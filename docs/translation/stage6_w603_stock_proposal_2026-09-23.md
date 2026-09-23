# Stage 6 — W6-3 **Stock** proposal (2026-09-23)

**Status: PROPOSAL ONLY — owner mark-up pending. No quorum, no import, no catalog change, no evidence re-pin, no production, no Stage-8.**

W6-2 is **exhausted** after batch 02 (batch 01 closed `073458e`, batch 02
governed cycle `b3b0681`; raw identity `337 = 268 + 48 + 21`; catalog at
**2,319 Released** rows). This note proposes the **next bounded** Stage 6
workflow-matrix scope: matrix row **W6-3 — Stock** only.

Evidence re-pin remains **deferred** to the next catalog cycle that actually
changes the packaged catalog (owner directive unchanged).

## Matrix scope (W6-3 boundaries)

From `docs/translation/stage6_workflow_matrix_proposal_2026-09-21.md`
(matrix row W6-3):

> **W6-3 | Stock — Warehouse, Receipts, Stock Entry, valuation reports
> (`stock`) | 789 | Warehouse/stock desk | P2**

Matrix notes applied here: rows are *candidate strings within the area, not
commitments* (the exact list is cut once the batch has owner approval); every
batch follows the governed review machine (proposal → quorum → import on the
test site); big-bang rollout is forbidden; Stage 8 stays deferred. Vendor
area token for this row is **`stock`** — first ledger location under
`erpnext/stock/`.

## Exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w603_stock_scope_2026-09-23.csv` |
| Rows | **736** translation-candidates |
| sha256 | `b995e74e4d0e1f30b49cdb10cb65829c6eada95daa7f016de8f6a2b088e056ff` |
| Source ledger | `docs/erpnext_ar_missing_review_filled.csv` (4,342 rows; W6-3 raw first-location `stock` = **789**, matching the matrix row count) |
| Matrix row | W6-3 in `stage6_workflow_matrix_proposal_2026-09-21.md` (Owner decision box ☐ until this approval) |
| Site (if approved to run) | `v16.localhost` test site only |

CSV columns: `source_text,suggested_ar,locations,area,has_pre_filled,doctype_context,suggested_disposition,reason`
(W6-2's five columns plus **`doctype_context`** (target DocType/report/page
context derived from the first location), **`suggested_disposition`**
(`approve` / `needs-review`), and **`reason`**). Sorted by `area`,
`source_text`. All 736 rows carry `area=stock`.

Row count = **736 CSV records**. Physical lines = **739** (`wc -l`): 1 header
+ 736 records + 2 extra line-breaks from RFC-4180-quoted embedded newlines in
2 `source_text` values. The checksum above is over the exact file bytes.

### Composition

| Attribute | Value |
|---|---|
| Area split | **736 stock** (single matrix row; no other area) |
| Pre-filled `msgstr` from vendor review ledger | **379** (baseline Arabic carried into proposal panel) |
| Unfilled (AI proposal required at cycle time) | **357** |
| Suggested disposition `approve` | **720** |
| Suggested disposition `needs-review` (flagged, not pre-excluded) | **16** — 14 barcode/GTIN technical tokens (`EAN`, `UPC`, `ISBN-13`, `CODE-39`, `GS1`, `GTIN`, `JAN`, `PZN`, …) + 2 embedded-newline formatting anomalies |
| Suggested disposition `exclude` | **0** (everything excluded by cut rules never enters the CSV) |
| Placeholder rows (`{…}`) | **136** (format tokens retained as-is) |
| `length` range | 3–120 (360 rows ≤ 25; all ≤ 120) |
| HTML/template rows | **0** (excluded by cut rule) |
| Overlap with released catalog (`approved_ar_overrides.csv`, 2,319 Released) | **0** |
| Overlap with `release_decisions.json` (2,319 decisions) | **0** |
| Overlap with prior W6-0a / W6-0b / W6-1 / W6-2 scope ∪ payload ∪ released-list keys (23 files, union **2,751**) | **0** |
| Overlap with W6-2 batch 01 (270) / batch 02 (48) | **0 / 0** (included in the 23-file union) |
| Overlap with 21 technical exclusions | **0** |
| Overlap with 302 a1/a2 dedup exclusions | **0** |
| Duplicates within the proposal itself | **0** |

### Screens inside scope (first location under `erpnext/stock/`)

Mutually exclusive classify buckets (736 total):

| Bucket | Rows | Notes |
|---|---:|---|
| Reports — valuation / ledger / balance / warehouse balance, … | **98** | incl. `stock_ledger_invariant_check` 17, `fifo_queue_vs_qty…` 12, `stock_ledger_variance` 5, `stock_balance` 3, `warehouse_wise_stock_balance` 3, `stock_ageing` 2, `stock_ledger` 1, `stock_projected_qty` 4, `incorrect_stock_value_report` 2, `incorrect_serial_no_valuation` 2, landed-cost / serial-batch traceability reports |
| Stock Settings + repost/valuation plumbing | **102** | `stock_settings` 58, `repost_item_valuation` 33, `stock_reposting_settings` 11 |
| Stock Entry (+ detail/type) | **52** | Receipt / Issue / Transfer / Manufacture / Unpack UI (DocType context `Stock Entry` = 46) |
| Receipts family (Purchase Receipt + item, Delivery Note + item, Stock Reconciliation + item, Packing Slip) | **65** | warehouse inbound/outbound + reconciliation (`Purchase Receipt` 11, `Delivery Note` 16, `Stock Reconciliation` 12, `Packing Slip` 10, + child rows) |
| Warehouse DocType | **11** | warehouse master (`Warehouse` context; plus `Putaway Rule` 12 sits in “other”) |
| Other stock-desk strings | **408** | Shipment 40, Serial & Batch Bundle 31, Pick List 22, Landed Cost Voucher 19, Item-adjacent stock masters, Material Request, Quality Inspection, workspace labels, `.py` runtime messages — all still first-location `stock` |

### Cut rules (deterministic; same pipeline as W6-2)

1. Ledger rows with `skip` not yes; non-empty `msgid`.
2. First location path under `erpnext/stock/`
   (yields raw **789** unique msgids — exactly the matrix W6-3 count).
3. Deduplicate by `msgid` (first-wins; raw is already unique at 789).
4. Bound: `len(msgid) ≤ 120`; drop HTML/template (`<…>`).
5. Drop rows in released catalog, `release_decisions.json`, any prior
   Stage-6 scope/payload/released keys (W6-0a, W6-0b, W6-1, W6-2),
   technical exclusions (21), and a1/a2 dedup exclusions (302).
6. Classify each remaining row: `doctype_context` from first location;
   `suggested_disposition` = `needs-review` for technical tokens /
   embedded-newline anomalies, else `approve`; write a brief `reason`.
7. Write CSV sorted by `area`, `source_text`.

### Full W6-3 raw accounting (789 unique first-location msgids)

Mutually exclusive buckets under cut priority
(`HTML` → `len>120` → `already-released` → `decisions` → `tech` → `dedup` →
`prior scope` → scope). Each raw msgid lands in **exactly one** row:

| Bucket | Rows | In scope? |
|---|---:|---|
| HTML/template residual | **13** | **no — excluded** |
| `len > 120` residual (after HTML priority) | **40** | **no — excluded** |
| Already in released catalog | **0** | no — excluded (none found) |
| In `release_decisions.json` | **0** | no — excluded (none found) |
| Technical exclusions (21) ∩ raw | **0** | no — excluded (none found) |
| a1/a2 dedup exclusions (302) ∩ raw | **0** | no — excluded (none found) |
| Prior W6-0a/0b/W6-1/W6-2 scope ∪ payload ∪ released keys ∩ raw | **0** | no — excluded (none found) |
| **W6-3 scope candidates (this proposal)** | **736** | **yes** |
| **Total raw unique** | **789** | |

**Identity:** `13 + 40 + 0 + 0 + 0 + 0 + 0 + 736 = 789`.

Independent flag checks on the raw 789 **before** priority assignment:

| Flag | Rows | How counted |
|---|---:|---|
| HTML match | **13** | — |
| `len > 120` | **47** raw flag | 7 are also HTML (counted once under HTML) + **40** only-long |
| HTML ∩ `len>120` | **7** | once only — HTML bucket |
| Already-released / decisions / tech / dedup / prior-scope ∩ raw | **0 / 0 / 0 / 0 / 0** | — |
| scope ∩ any exclusion set above | **0** | — |

So the listed exclusion counts `13 + 40 = 53` are mutually exclusive under
the priority order. **No already-released keys exist in this raw set** —
nothing was dropped as a duplicate of prior work.

### Exclusions summary (explicitly out of scope)

| # | Exclusion | Count / status |
|---|---|---|
| 1 | Other matrix rows — W6-0 desk shell, W6-1 accounting, W6-2 buying/selling (closed), W6-4 projects/BOQ, W6-5 setup, W6-6 deferred modules, W6-7 frappe remainder | untouched; 0 key overlap with this CSV |
| 2 | Non-`stock` vendor areas in the ledger (accounts 1,262, setup 483, manufacturing 480, …) | outside matrix row W6-3 |
| 3 | Already-released catalog keys (`approved_ar_overrides.csv`, 2,319 Released; `release_decisions.json`, 2,319) | **0 keys from the raw 789 are in the catalog** — nothing removed on this ground |
| 4 | Prior Stage-6 scope/payload/released keys (W6-0a desk shell, W6-0b batches 01–07 + short-UI plan, W6-1 subset, W6-2 batches 01–02; 23 files, union 2,751) | intersection with raw = **0**; with scope = **0** |
| 5 | Technical exclusions — `stage6_w60b_technical_exclusions_2026-09-22.csv`, **21** rows, sha256 `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` | ∩ raw = **0**; unchanged |
| 6 | a1/a2 dedup exclusions — `stage6_w60b_dedup_exclusions_2026-09-22.csv`, **302** rows, sha256 `ee24f18fdfd451204e18e26c17c8d9e2fc6a7539efa634087f5f7de4848fe37b` | ∩ raw = **0**; unchanged |
| 7 | HTML/template rows in the raw 789 | **13** — not proposed |
| 8 | `len > 120` (outside short/medium UI bound; long validations/templates) | **40** (after HTML priority; raw flag 47) — not proposed |
| 9 | Production-only concerns, Stage-8, evidence re-pin, site import | gated; not part of this proposal |
| 10 | Rows only discoverable at cycle-time site probe (plan §12 site overrides) | none pre-removed; preserved at import if found |

**Residual not proposed:** `53 = 13 HTML + 40 len>120`.

## Overlap proof (concrete set checks)

Method: load `construction/data/translations/approved_ar_overrides.csv`
(2,319 rows, all `Released`); load the proposed
`docs/translation/stage6_w603_stock_scope_2026-09-23.csv` (736 rows); join on
the `source_text` key column; also join against
`release_decisions.json`, the shared exclusion files, and the prior Stage-6
scope/payload/released key union; count duplicates inside the proposal.

| Check | Set A | Set B | \|A ∩ B\| |
|---|---|---|---:|
| Released catalog | scope (736) | `approved_ar_overrides.csv` Released (2,319) | **0** |
| Release decisions | scope (736) | `release_decisions.json` decisions (2,319) | **0** |
| Prior scopes union | scope (736) | 23 prior stage6 scope/payload/released files (2,751) | **0** |
| W6-2 batch 01 | scope (736) | batch-01 CSV (270) | **0** |
| W6-2 batch 02 | scope (736) | batch-02 CSV (48) | **0** |
| Technical exclusions | scope (736) | 21 technical keys | **0** |
| Dedup exclusions | scope (736) | 302 dedup keys | **0** |
| HTML / long residuals | scope (736) | 13 HTML ∪ 40 only-long | **0** |
| Duplicates within proposal | scope (736) | scope (736) | **0** |
| Stripped-form catalog collisions (batch-01 Address precedent) | scope keys with edge whitespace | catalog keys stripped | **0** |

Also verified: scope `source_text` unique = 736; row count on read-back = 736;
scope `len ≤ 120`; no HTML matches in scope; `area` values = `{stock}` only;
checksum re-verified byte-stable across two independent regenerations.

**Headline result: `proposed_rows=736, overlap_with_released=0,
duplicates_within_proposal=0`.**

### Sample rows (not exhaustive)

Pre-filled:
`% Occupied` → `نسبة الإشغال`,
`Accounting Entry for LCV in Stock Entry {0}` → `قيد محاسبي لسند التكلفة الإضافية في قيد المخزون {0}`,
`Action If Quality Inspection Is Rejected` → `الإجراء عند رفض فحص الجودة`,
plus Warehouse / Stock Entry / Receipt / valuation-report labels (full set in CSV).

Unfilled (AI proposal at cycle time): stock-ledger invariant messages,
warehouse availability validations (`{0} units of Item {1} is not available in any of the warehouses.`),
Stock Entry / Pick List / Serial-Batch workflow strings, and report column
labels (full set in CSV).

### Needs-review rows flagged for quorum (not pre-excluded)

The 16 `needs-review` rows stay in the CSV for full visibility; disposition
stays with A1/A2/A3 + AI-R after approval: 14 barcode/identifier tokens
(`CODE-39`, `EAN`, `EAN-8`, `EAN-12`, `GS1`, `GTIN`, `ISBN`, `ISBN-10`,
`ISBN-13`, `ISSN`, `JAN`, `PZN`, `UPC`, `UPC-A`) and 2 embedded-newline
formatting anomalies (Stock Settings / Item Lead Time descriptions). This
proposal does **not** move any row out of scope unilaterally.

### Site-override / catalog note (plan §12)

At cycle time a live test-site probe will detect existing `ar` Translation
rows whose `source_text` matches a batch key with non-empty text. Genuine
site overrides are preserved; import only applies genuine state changes.
**No rows are pre-removed from the 736-row CSV.**

## Proposal-only boundary

**PROPOSAL ONLY. No quorum, no import, no catalog mutation, no evidence
re-pin performed. Awaiting owner approval of the exact scope. Stage 8 and
production remain gated.**

Next step on approval: the governed cycle (recon → proposal approved →
quorum → import → gates → evidence re-pin) will run **only** after explicit
owner approval of this exact CSV + checksum, and only on the `v16.localhost`
test site.

- Approving this scope authorizes **only** the 736-row CSV above (sha256
  above) to enter that governed cycle when you say go.
- **Quorum and import will NOT start until the owner approves this exact
  scope** (CSV path + sha256 above). No AI proposal panel, quorum, import,
  catalog change, decisions/manifest/pin mutation, evidence re-pin,
  production mutation, or Stage-8 work is started by this note.
- Expanding beyond 736 rows (e.g. pulling the 53 residual rows) requires a
  new exact CSV + sha256.
- Matrix row W6-3 owner box stays ☐ until you mark it.

## Remaining plan (not for approval now)

| Scope | Rows | Status |
|---|---:|---|
| W6-0a / W6-0b short-UI | 1,894 + desk shell | **closed** (batch 7 accepted `a0f01cb`) |
| W6-1 accounting subset | pre-matrix pilot | **closed** |
| W6-2 batch 01 / 02 | 270 / 48 | **closed** (`073458e`, `b3b0681`) |
| **W6-3 Stock (this proposal)** | **736** (raw 789) | **presented for approval** |
| W6-3 residual exclusions (raw) | **53** | **13 HTML + 40 `len>120`** — not proposed |
| W6-4 Projects + BOQ | 61 + 90 | not proposed |
| W6-5 Setup | 484 | not proposed |
| W6-6 Deferred modules | ~849 | not proposed |
| W6-7 Frappe framework remainder | per frappe ledger | not proposed |

Raw identity for this matrix row:

**`789 = 736 (scope) + 13 (HTML) + 40 (len>120)`**
with `0` already-released, `0` decisions, `0` prior-scope, `0` tech,
`0` dedup hits in raw.

## Owner mark-up requested

- [ ] **Approve W6-3 Stock only** — the 736-row CSV
      (`docs/translation/stage6_w603_stock_scope_2026-09-23.csv`,
      sha256 `b995e74e4d0e1f30b49cdb10cb65829c6eada95daa7f016de8f6a2b088e056ff`)
      as the exact next Stage 6 translation scope.
- [ ] Acknowledge shared **21** technical + **302** dedup exclusions remain
      unchanged (0 overlap with this scope).
- [ ] Acknowledge the **53** raw residual exclusions stay out of scope
      (**13 HTML + 40 `len>120`**; mutually exclusive under cut priority).
- [ ] Acknowledge **0** already-released / prior-scope keys were found in the
      raw 789 (nothing dropped as a prior-work duplicate).
- [ ] Leave W6-4…W6-7 unapproved until a later proposal.
- [ ] Any direct term overrides for batch strings → terminology sheet before
      a future quorum panel.
