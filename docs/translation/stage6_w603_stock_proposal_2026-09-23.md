# Stage 6 — W6-3 **Stock** proposal (2026-09-23)

**Status: PROPOSAL ONLY — owner mark-up pending. No quorum, no import, no catalog change, no evidence re-pin, no production, no Stage-8.**

W6-2 is **exhausted** after batch 02 (batch 01 closed `073458e`, batch 02
governed cycle `b3b0681`; raw identity `337 = 268 + 48 + 21`). This note
proposes the **next bounded** Stage 6 workflow-matrix scope: matrix row
**W6-3 — Stock** (Warehouse, Receipts, Stock Entry, valuation reports;
vendor area token `stock`) only.

Evidence re-pin remains **deferred** to the next catalog cycle that actually
changes the packaged catalog (owner directive unchanged).

## Exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w603_stock_scope_2026-09-23.csv` |
| Rows | **734** translation-candidates (735 physical lines incl. header; no embedded newlines) |
| sha256 | `a60b1c8ec3bae8977826ed9101ee59a9206c699425e921da3f3d7341a7604535` |
| Source ledger | `docs/erpnext_ar_missing_review_filled.csv` (4,342 rows; W6-3 raw first-location `stock` = **789**, matching the matrix row count) |
| Matrix row | W6-3 in `stage6_workflow_matrix_proposal_2026-09-21.md` (Owner decision box ☐ until this approval) |
| Site (if approved to run) | `v16.localhost` test site only |

CSV columns (same as W6-2 batch 02): `source_text,suggested_ar,locations,area,has_pre_filled`.
Sorted by `area`, `source_text`. All 734 rows carry `area=stock`.

### Composition

| Attribute | Value |
|---|---|
| Area split | **734 stock** (single matrix row; no other area) |
| Pre-filled `msgstr` from vendor review ledger | **379** (baseline Arabic carried into proposal panel) |
| Unfilled (AI proposal required at cycle time) | **355** |
| Placeholder rows (`{…}`) | **136** (format tokens retained as-is) |
| `length` range | 3–120 (360 rows ≤ 25; all ≤ 120) |
| HTML/template rows | **0** (excluded by cut rule) |
| Embedded-newline rows | **0** (excluded by cut rule) |
| Overlap with released catalog (2,319 Released) | **0** |
| Overlap with `release_decisions.json` (2,319 decision keys) | **0** |
| Overlap with prior W6-0a / W6-0b / W6-1 / W6-2 scope ∪ payload ∪ released-list keys (union **2,746** across 40 files) | **0** |
| Overlap with W6-2 batch 01 (270) / batch 02 (48) | **0 / 0** |
| Overlap with W6-1 accounting subset (`msgid`) | **0** |
| Overlap with 21 technical exclusions | **0** |
| Overlap with 302 a1/a2 dedup exclusions | **0** |
| Duplicates within the proposal itself | **0** (734 unique `source_text`) |

### Screens inside scope (first-location under `erpnext/stock/`)

| Bucket | Rows (scope) | Notes |
|---|---:|---|
| Reports (valuation / ledger / ageing / stock balance, …) | **98** | incl. `stock_ledger_invariant_check` 17, `fifo_queue_vs_qty…` 12, `stock_balance`, `stock_ageing`, `warehouse_wise_stock_balance`, … |
| `stock_settings` + repost/valuation plumbing | **57 + 33 + 11** | settings, `repost_item_valuation`, `stock_reposting_settings`, `stock_ledger_entry` |
| Stock Entry (+ detail/type) | **46 + 5 + 1** | Receipt / Issue / Transfer / Manufacture UI |
| Receipts: Purchase Receipt (+item), Delivery Note (+item), Stock Reconciliation (+item), Packing Slip (+item) | **19 + 20 + 15 + 11** | warehouse inbound/outbound + reconciliation |
| Warehouse (+ Bin, Putaway) | **11 + 4 + 12** | warehouse master & putaway |
| Shipment / Pick List / Serial-Batch bundle | **40 + 22 + 31** | stock desk operational docs |
| Item-adjacent stock masters (item, barcode, lead time, …) | **~90** | stock-side item labels only |
| Landed cost / Quality inspection / Material request / stock `.py` modules | balance | still inside `stock` first-location |

### Cut rules (deterministic; same pipeline as W6-2)

1. Ledger rows with `skip` not yes; non-empty `msgid`.
2. First location path under `erpnext/stock/`
   (yields raw **789** unique msgids — exactly the matrix W6-3 count).
3. Deduplicate by `msgid` (first-wins; raw is already unique at 789).
4. Bound: `len(msgid) ≤ 120`.
5. Drop HTML/template rows (`<tag>` / JS `${…}`) **and** rows with an
   embedded newline/CR in `msgid` (W6-0b newline/template precedent; keeps
   the CSV single-line-per-record).
6. Drop rows in released catalog, any prior Stage-6 scope/payload/released
   keys (W6-0a, W6-0b, W6-1, W6-2), technical exclusions (21), and a1/a2
   dedup exclusions (302).
7. Write CSV sorted by `area`, `source_text`.

### Full W6-3 raw accounting (789 unique first-location msgids)

Mutually exclusive buckets under cut priority
(`HTML` → `newline` → `len>120` → `already-released` → `prior` → `tech` →
`dedup` → scope). Each raw msgid lands in **exactly one** row:

| Bucket | Rows | In scope? |
|---|---:|---|
| HTML/template residual | **13** | **no — excluded** (2 of these also contain newlines; counted here) |
| Embedded-newline residual (non-HTML) | **3** | **no — excluded** (1 of these is also `len>120`; counted here) |
| `len > 120` residual (outside short-UI bound) | **39** | **no — excluded** |
| Already in released catalog | **0** | no — excluded (none found) |
| Prior W6-0a/0b/W6-1/W6-2 scope ∪ payload ∪ released keys | **0** | no — excluded (none found) |
| Technical exclusions (21) ∩ raw | **0** | no — excluded (none found) |
| a1/a2 dedup exclusions (302) ∩ raw | **0** | no — excluded (none found) |
| **W6-3 scope candidates (this proposal)** | **734** | **yes** |
| **Total raw unique** | **789** | |

**Identity:** `13 + 3 + 39 + 0 + 0 + 0 + 0 + 734 = 789`
(residual not proposed: **55 = 13 HTML + 3 newline + 39 len>120**).

Independent flag checks on the raw 789 **before** priority assignment:

| Pair | Rows | How counted |
|---|---:|---|
| HTML **and** newline | **2** | Once only — HTML bucket |
| HTML **and** `len>120` | **7** | Once only — HTML bucket (raw `len>120` flag = 47) |
| newline **and** `len>120` (non-HTML) | **1** | Once only — newline bucket (`Example: ABCD.#####…`) |
| Already-released ∩ raw | **0** | — |
| prior-scope ∩ raw | **0** | — |
| tech ∩ raw / dedup ∩ raw | **0 / 0** | — |
| scope ∩ any exclusion set above | **0** | — |

Raw flag tallies (overlapping, pre-priority): HTML 13, newline 5
(2 already HTML), `len>120` 47 (7 already HTML + 1 already newline-only →
bucket residual 39). Under the priority order the exclusions
`13 + 3 + 39 = 55` are mutually exclusive. **No already-released keys exist
in this raw set** — nothing was dropped as a duplicate of prior work.

The 3 newline keys (for owner visibility, not proposed):

1. `Example: ABCD.#####…` (serial-numbering series help text; also >120)
2. `If enabled, do not update serial / batch values in the stock transactions on creation of auto Serial \n / Batch Bundle. ` (stock settings description; stray newline)
3. `Per Day\nShift Time (In Hours) * No of Workstations * No of Shift` (multi-line formula template)

### Exclusions summary (explicitly out of scope)

| # | Exclusion | Count / status |
|---|---|---|
| 1 | Other matrix rows — W6-0 desk shell, W6-1 accounting, W6-2 buying/selling (closed), W6-4 projects/BOQ, W6-5 setup, W6-6 deferred modules, W6-7 frappe remainder | untouched; 0 key overlap with this CSV |
| 2 | Non-`stock` vendor areas in the ledger (accounts 1,265, setup 484, manufacturing 481, …) | outside matrix row W6-3 |
| 3 | Already-released catalog keys (`approved_ar_overrides.csv`, 2,319 Released; `release_decisions.json`, 2,319 decisions) | **0 keys from the raw 789 are in the catalog/decisions** — noted separately, nothing removed on this ground |
| 4 | Prior Stage-6 scope/payload/released keys (W6-0a desk shell, W6-0b batches 01–07 + short-UI plan, W6-1 subset, W6-2 batches 01–02; union 2,746 across 40 files) | intersection with raw = **0**; with scope = **0** |
| 5 | Technical exclusions — `stage6_w60b_technical_exclusions_2026-09-22.csv`, **21** rows, sha256 `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` | ∩ raw = **0**; unchanged |
| 6 | a1/a2 dedup exclusions — `stage6_w60b_dedup_exclusions_2026-09-22.csv`, **302** rows, sha256 `ee24f18fdfd451204e18e26c17c8d9e2fc6a7539efa634087f5f7de4848fe37b` | ∩ raw = **0**; unchanged |
| 7 | HTML/template rows in the raw 789 | **13** — not proposed |
| 8 | Embedded-newline (non-HTML) rows in the raw 789 | **3** — not proposed (listed above) |
| 9 | `len > 120` (outside short/medium UI bound; long validations/templates) | **39** (after HTML + newline priority; raw flag 47) — not proposed |
| 10 | Production-only concerns, Stage-8, evidence re-pin, site import | gated; not part of this proposal |
| 11 | Rows only discoverable at cycle-time site probe (plan §12 site overrides) | none pre-removed; preserved at import if found |

**Residual not proposed:** `55 = 13 HTML + 3 newline + 39 len>120`.

## Overlap proof (concrete set checks)

Run on exact `source_text` / `msgid` keys after writing the CSV (read-back):

| Check | Set A | Set B | \|A ∩ B\| |
|---|---|---|---:|
| Released catalog | scope (734) | `approved_ar_overrides.csv` Released (2,319) | **0** |
| Release decisions | scope (734) | `release_decisions.json` decisions keys (2,319) | **0** |
| Prior scopes union | scope (734) | 40 prior stage6 scope/payload/released files (2,746) | **0** |
| W6-2 batch 01 | scope (734) | batch-01 CSV (270) | **0** |
| W6-2 batch 02 | scope (734) | batch-02 CSV (48) | **0** |
| W6-1 subset | scope (734) | accounting subset `msgid` (`stage6_w61_accounting_subset_rows_2026-09-21.csv`) | **0** |
| Technical exclusions | scope (734) | 21 technical keys | **0** |
| Dedup exclusions | scope (734) | 302 dedup keys | **0** |
| Cut-rule residuals | scope (734) | 13 HTML ∪ 3 newline ∪ 39 only-long | **0** |
| Internal duplicates | scope (734) | unique `source_text` | **0 dups** |
| Raw vs prior work | raw stock (789) | catalog ∪ release_decisions ∪ prior scopes ∪ tech ∪ dedup | **0** |

Also verified: scope `source_text` unique = 734; row count on read-back = 734;
`len ≤ 120`; no HTML and no embedded newline in scope; `area` values =
`{stock}` only; sha256 over the exact file bytes =
`a60b1c8ec3bae8977826ed9101ee59a9206c699425e921da3f3d7341a7604535`.

**Headline result: `proposed_total=734, already_released_overlap=0,
net_new=734, duplicates_within_proposal=0`.**

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

### Batch source tokens flagged for quorum (not pre-excluded)

Technical/identifier tokens inside the stock area are retained in the scope
CSV for full visibility; disposition stays with A1/A2/A3 + AI-R after
approval. This proposal does **not** move any row out of scope unilaterally.

### Site-override / catalog note (plan §12)

At cycle time a live test-site probe will detect existing `ar` Translation
rows whose `source_text` matches a batch key with non-empty text. Genuine
site overrides are preserved; import only applies genuine state changes.
**No rows are pre-removed from the 734-row CSV.**

## Remaining plan (not for approval now)

| Scope | Rows | Status |
|---|---:|---|
| W6-0a / W6-0b short-UI | 1,894 + desk shell | **closed** (batch 7 accepted `a0f01cb`) |
| W6-1 accounting subset | 147 applied | **closed** (pre-matrix pilot) |
| W6-2 batch 01 / 02 | 270 / 48 | **closed** (`073458e`, `b3b0681`) |
| **W6-3 Stock (this proposal)** | **734** (raw 789) | **presented for approval** |
| W6-3 residual exclusions (raw) | **55** | **13 HTML + 3 newline + 39 `len>120`** — not proposed |
| W6-4 Projects + BOQ | 61 + 90 | not proposed |
| W6-5 Setup | 484 | not proposed |
| W6-6 Deferred modules | ~849 | not proposed |
| W6-7 Frappe framework remainder | per frappe ledger | not proposed |

Raw identity for this matrix row:

**`789 = 734 (scope) + 13 (HTML) + 3 (newline) + 39 (len>120)`**
with `0` already-released, `0` prior-scope, `0` tech, `0` dedup hits in raw.

## Boundary

- Proposal-only: approving this scope authorizes **only** the 734-row CSV
  above (sha256 above) to enter the governed cycle (site recon → AI proposal
  → quorum → AI-R → DRY_RUN → IMPORT → browser evidence → evidence re-pin)
  **on the test site** when you say go.
- **Quorum and import will NOT start until the owner approves this exact
  scope** (CSV path + sha256 above). No AI proposal panel, quorum, import,
  catalog change, decisions/manifest/pin mutation, evidence re-pin,
  production mutation, or Stage-8 work is started by this note.
- Expanding beyond 734 rows (e.g. pulling the 55 residual rows) requires a
  new exact CSV + sha256.
- Matrix row W6-3 owner box stays ☐ until you mark it.

## Owner mark-up requested

- [ ] **Approve W6-3 Stock only** — the 734-row CSV
      (`docs/translation/stage6_w603_stock_scope_2026-09-23.csv`,
      sha256 `a60b1c8ec3bae8977826ed9101ee59a9206c699425e921da3f3d7341a7604535`)
      as the exact next Stage 6 translation scope.
- [ ] Acknowledge shared **21** technical + **302** dedup exclusions remain
      unchanged (0 overlap with this scope).
- [ ] Acknowledge the **55** raw residual exclusions stay out of scope
      (**13 HTML + 3 newline + 39 `len>120`**; mutually exclusive under cut
      priority).
- [ ] Acknowledge **0** already-released / prior-scope keys were found in the
      raw 789 (nothing dropped as a prior-work duplicate).
- [ ] Leave W6-4…W6-7 unapproved until a later proposal.
- [ ] Any direct term overrides for batch strings → terminology sheet before
      a future quorum panel.
