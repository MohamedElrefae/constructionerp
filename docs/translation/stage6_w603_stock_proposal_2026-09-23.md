# Stage 6 — W6-3 **Stock** proposal (2026-09-23)

**Status: PROPOSAL ONLY — owner mark-up pending.**

PROPOSAL ONLY. No quorum, no import, no catalog mutation, no evidence re-pin. Awaiting owner approval of exact scope. Stage 8 and production remain gated.

W6-2 is **exhausted** after batch 02 (batch 01 closed `073458e`, batch 02
governed cycle `b3b0681`; raw identity `337 = 268 + 48 + 21`). This note
proposes the **next bounded** Stage 6 workflow-matrix scope: matrix row
**W6-3 — Stock** only.

## Scope definition (matrix row W6-3)

From `docs/translation/stage6_workflow_matrix_proposal_2026-09-21.md`:

> | W6-3 | Stock — Warehouse, Receipts, Stock Entry, valuation reports (`stock`) | 789 | Warehouse/stock desk | P2 | ☐ |

Scope = vendor ledger rows whose **first location** path is under
`erpnext/stock/` (Warehouse, Receipts — Purchase Receipt / Delivery Note /
Stock Reconciliation / Packing Slip — Stock Entry, and valuation reports
under `erpnext/stock/report/`), matching the matrix area token `stock` and
the raw count **789**.

## Exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w603_stock_scope_2026-09-23.csv` |
| Rows | **736** translation-candidates (CSV records) |
| sha256 | `c927ddf23e7311d5b9737108f13086a393a17c0c250bac3c3f16741606546452` |
| Physical lines | 739 (`wc -l`; 2 records carry RFC-4180-quoted embedded newlines in `source_text`; checksum is over exact file bytes) |
| Source ledger | `docs/erpnext_ar_missing_review_filled.csv` (4,342 rows; W6-3 raw first-location `stock` = **789**) |
| Matrix row | W6-3 in `stage6_workflow_matrix_proposal_2026-09-21.md` (owner box ☐ until this approval) |
| Site (if approved to run) | `v16.localhost` test site only |

CSV columns (same as W6-2 batch-02): `source_text,suggested_ar,locations,area,has_pre_filled`.
Sorted by `area`, `source_text`. All 736 rows carry `area=stock`.
Unfilled rows leave `suggested_ar` blank (AI proposal at cycle time), matching
the batch-02 convention for rows awaiting quorum.

### Composition

| Attribute | Value |
|---|---|
| Area split | **736 stock** (single matrix row) |
| Pre-filled `msgstr` from vendor review ledger | **379** |
| Unfilled (AI proposal required at cycle time) | **357** |
| Placeholder rows (`{…}`) | **136** (format tokens retained as-is) |
| `length` range | 3–120 (360 rows ≤ 25; all ≤ 120) |
| HTML/template rows in scope | **0** (excluded by cut rule) |
| Internal duplicates in CSV | **0** (736 unique `source_text`) |

### Cut rules (deterministic; same pipeline as W6-2)

1. Ledger rows with `skip` not yes; non-empty `msgid`.
2. First location path under `erpnext/stock/`
   (yields raw **789** unique msgids — exactly the matrix W6-3 count).
3. Deduplicate by `msgid` (first-wins; raw already unique at 789).
4. Bound: `len(msgid) ≤ 120`; drop HTML/template (`<…>`).
5. Drop rows in released catalog, any prior Stage-6 scope/payload/released
   keys (W6-0a, W6-0b, W6-1, W6-2), technical exclusions (21), and a1/a2
   dedup exclusions (302).
6. Write CSV sorted by `area`, `source_text`.

### Full W6-3 raw accounting (789 unique first-location msgids)

Mutually exclusive buckets under cut priority
(`already-released` → `prior scope` → `tech` → `dedup` → `HTML` →
`len>120` → scope):

| Bucket | Rows | In scope? |
|---|---:|---|
| Already in released catalog | **0** | no — excluded (none found) |
| Prior W6-0a/0b/W6-1/W6-2 scope ∪ payload ∪ released keys | **0** | no — excluded (none found) |
| Technical exclusions (21) ∩ raw | **0** | no — excluded (none found) |
| a1/a2 dedup exclusions (302) ∩ raw | **0** | no — excluded (none found) |
| HTML/template residual | **13** | **no — excluded** |
| `len > 120` residual (outside bound) | **40** | **no — excluded** |
| **W6-3 scope candidates (this proposal)** | **736** | **yes** |
| **Total raw unique** | **789** | |

**Identity:** `0 + 0 + 0 + 0 + 13 + 40 + 736 = 789`.

Independent flag checks on the raw 789 **before** priority assignment:

| Pair | Rows | How counted |
|---|---:|---|
| HTML **and** `len>120` | **7** | Once only — HTML bucket: raw `len>120` flag = 47 = 7 (also HTML) + 40 (only-long); raw HTML flag = 13 |
| Already-released ∩ raw | **0** | — |
| prior-scope ∩ raw | **0** | — |
| tech ∩ raw / dedup ∩ raw | **0 / 0** | — |
| scope ∩ any exclusion set | **0** | — |

Listed residual exclusions `13 + 40 = 53` are mutually exclusive under the
priority order. **No already-released / prior-scope keys exist in this raw set.**

### Exclusions summary (explicitly out of scope)

| # | Exclusion | Count / status |
|---|---|---|
| 1 | Other matrix rows — W6-0 desk shell, W6-1 accounting, W6-2 buying/selling (closed), W6-4 projects/BOQ, W6-5 setup, W6-6 deferred modules, W6-7 frappe remainder | untouched; 0 key overlap with this CSV |
| 2 | Non-`stock` vendor areas in the ledger (accounts, setup, manufacturing, …) | outside matrix row W6-3 |
| 3 | First-location **not** under `erpnext/stock/` but mentioning stock in secondary locations | belongs to the first-location matrix row; out of W6-3 |
| 4 | Already-released catalog keys (`approved_ar_overrides.csv`, 2,319 Released; `release_decisions.json`, 2,319) | **0 keys from the raw 789** |
| 5 | Prior Stage-6 scope/payload/released keys (W6-0a, W6-0b 01–07, W6-1, W6-2 01–02) | ∩ raw = **0**; ∩ scope = **0** |
| 6 | Technical exclusions — `stage6_w60b_technical_exclusions_2026-09-22.csv`, **21** rows, sha256 `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` | ∩ raw = **0** |
| 7 | a1/a2 dedup exclusions — `stage6_w60b_dedup_exclusions_2026-09-22.csv`, **302** rows, sha256 `ee24f18fdfd451204e18e26c17c8d9e2fc6a7539efa634087f5f7de4848fe37b` | ∩ raw = **0** |
| 8 | HTML/template rows in the raw 789 | **13** — not proposed |
| 9 | `len > 120` (after HTML priority; raw independent flag 47) | **40** — not proposed |
| 10 | Production-only items, Stage-8, evidence re-pin, site import/quorum | gated; not part of this proposal |
| 11 | Cycle-time site-override rows (plan §12) | none pre-removed; preserved at import if found |

**Residual not proposed:** `53 = 13 HTML + 40 len>120`.

## Overlap proof (concrete set checks)

Run on exact `source_text` keys after writing the CSV (read-back):

| Check | Set A | Set B | \|A ∩ B\| |
|---|---|---|---:|
| Released catalog | scope (736) | `approved_ar_overrides.csv` Released (2,319) | **0** |
| Release decisions | scope (736) | `release_decisions.json` decision `source_text` (2,319) | **0** |
| Prior scopes union | scope (736) | 32 prior stage6 scope/payload/released files (union 2751) | **0** |
| W6-2 batch 01 | scope (736) | batch-01 CSV (270) | **0** |
| W6-2 batch 02 | scope (736) | batch-02 CSV (48) | **0** |
| W6-1 subset | scope (736) | accounting subset `msgid` (147) | **0** |
| Technical exclusions | scope (736) | 21 technical keys | **0** |
| Dedup exclusions | scope (736) | 302 dedup keys | **0** |
| HTML / long residuals | scope (736) | 13 HTML ∪ 40 only-long | **0** |
| Internal duplicates | scope (736) | unique `source_text` | **0 dups** (736 unique) |

Also verified on read-back: row count = 736; all `len ≤ 120`; no HTML
matches; `area` = `{stock}` only; pre-filled/unfilled = 379/357.

### Screens inside scope (first-location under `erpnext/stock/`)

| Bucket | Rows (scope) | Notes |
|---|---:|---|
| Reports (valuation / ledger / stock balance / ageing, …) | **98** | incl. `stock_ledger_invariant_check`, `fifo_queue_vs_qty…`, `stock_balance`, `warehouse_wise_stock_balance`, … |
| `stock_settings` + repost/valuation plumbing | **58 + 33 + 11** | settings, `repost_item_valuation`, `stock_reposting_settings` |
| Stock Entry (+ detail/type) | **46 + 5 + 1** | Receipt / Issue / Transfer / Manufacture UI |
| Receipts: Purchase Receipt (+item), Delivery Note (+item), Stock Reconciliation (+item), Packing Slip (+item) | **19 + 20 + 15 + 11** | warehouse inbound/outbound + reconciliation |
| Warehouse (+ Bin, Putaway) | **11 + 4 + 12** | warehouse master & putaway |
| Shipment / Pick List / Serial-Batch bundle | **40 + 22 + 31** | stock desk operational docs |
| Item-adjacent stock masters, other stock doctypes, page/workspace/dashboard, root `.py` helpers | balance | still inside `stock` first-location |

### Sample rows (not exhaustive)

Pre-filled:
`% Occupied` → `نسبة الإشغال`,
`Accounting Entry for LCV in Stock Entry {0}` → `قيد محاسبي لسند التكلفة الإضافية في قيد المخزون {0}`,
`Action If Quality Inspection Is Rejected` → `الإجراء عند رفض فحص الجودة`.

Unfilled (AI proposal at cycle time): stock-ledger invariant messages,
warehouse availability validations, Stock Entry / Pick List / Serial-Batch
workflow strings, and report column labels (full set in CSV).

### Batch source tokens flagged for quorum (not pre-excluded)

Technical/identifier tokens inside the stock area are retained in the scope
CSV for full visibility; disposition stays with A1/A2/A3 + AI-R after
approval. This proposal does **not** move any row out of scope unilaterally.

### Site-override / catalog note (plan §12)

At cycle time a live test-site probe will detect existing `ar` Translation
rows whose `source_text` matches a batch key with non-empty text. Genuine
site overrides are preserved; import only applies genuine state changes.
**No rows are pre-removed from the 736-row CSV.**

## Remaining plan (not for approval now)

| Scope | Rows | Status |
|---|---:|---|
| W6-0a / W6-0b short-UI | 1,894 + desk shell | **closed** (batch 7 accepted `a0f01cb`) |
| W6-1 accounting subset | 147 applied | **closed** (pre-matrix pilot) |
| W6-2 batch 01 / 02 | 270 / 48 | **closed** (`073458e`, `b3b0681`) |
| **W6-3 Stock (this proposal)** | **736** (raw 789) | **presented for approval** |
| W6-3 residual exclusions (raw) | **53** | **13 HTML + 40 `len>120`** — not proposed |
| W6-4 Projects + BOQ | 61 + 90 | not proposed |
| W6-5 Setup | 484 | not proposed |
| W6-6 Deferred modules | ~849 | not proposed |
| W6-7 Frappe framework remainder | per frappe ledger | not proposed |

Raw identity for this matrix row:

**`789 = 736 (scope) + 13 (HTML) + 40 (len>120)`**
with `0` already-released, `0` prior-scope, `0` tech, `0` dedup hits in raw.

## Boundary / next step on approval

PROPOSAL ONLY. No quorum, no import, no catalog mutation, no evidence re-pin.
Awaiting owner approval of exact scope. Stage 8 and production remain gated.

On approval of this exact CSV + checksum, the governed cycle
(recon → quorum → import → gates → evidence re-pin) will be executed only
after explicit owner approval of this exact CSV + checksum — **on the test
site** (`v16.localhost`) when you say go.

- **Quorum and import will NOT start until the owner approves this exact
  scope** (CSV path + sha256 above). No AI proposal panel, quorum, import,
  catalog change, decisions/manifest/pin mutation, evidence re-pin,
  production mutation, or Stage-8 work is started by this note.
- Expanding beyond 736 rows (e.g. pulling the 53 residual rows) requires a
  new exact CSV + sha256.
- Matrix row W6-3 owner box stays ☐ until you mark it.

## Owner mark-up requested

- [ ] **Approve W6-3 Stock only** — the 736-row CSV
      (`docs/translation/stage6_w603_stock_scope_2026-09-23.csv`,
      sha256 `c927ddf23e7311d5b9737108f13086a393a17c0c250bac3c3f16741606546452`)
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
