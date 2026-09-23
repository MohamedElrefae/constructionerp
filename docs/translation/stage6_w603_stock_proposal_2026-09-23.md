# Stage 6 — W6-3 **Stock** proposal (2026-09-23)

**Status: PROPOSAL ONLY — owner mark-up pending. No quorum, no import, no catalog change, no evidence re-pin, no production, no Stage-8.**

**Proposal only. No quorum, no import, no evidence re-pin, no catalog mutation. Awaiting owner approval of exact scope + checksum. Stage 8 and production remain gated.**

W6-2 is **exhausted** after batch 02 (batch 01 closed `073458e`, batch 02
governed cycle `b3b0681`; raw identity `337 = 268 + 48 + 21`; catalog at
**2,319 Released** rows). This note proposes the **next bounded** Stage 6
workflow-matrix scope: matrix row **W6-3 — Stock** (Warehouse, Receipts,
Stock Entry, valuation reports; vendor area token `stock`) only.

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
`erpnext/stock/`. Explicit exclusions the matrix already implies for this row:
every other matrix row (W6-0/1/2/4/5/6/7) and every non-`stock` vendor area.

## Exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w603_stock_scope_2026-09-23.csv` |
| Rows | **736** translation-candidates |
| sha256 | `54e86438f0e453872b5a5399c9e62cccf35046a417d08a5b01732071ae02bed2` |
| Source ledger | `docs/erpnext_ar_missing_review_filled.csv` (4,342 rows; W6-3 raw first-location `stock` = **789**, matching the matrix row count) |
| Matrix row | W6-3 in `stage6_workflow_matrix_proposal_2026-09-21.md` (Owner decision box ☐ until this approval) |
| Site (if approved to run) | `v16.localhost` test site only |

CSV columns = W6-2 structure + disposition:
`source_text,suggested_ar,locations,area,has_pre_filled,disposition`.
Sorted by `area`, `source_text`. All 736 rows carry `area=stock`.

Row count = **736 CSV records** (739 physical lines: 1 header + 736 records
+ 2 extra line-breaks from RFC-4180-quoted embedded newlines in 2
`source_text` values). The checksum above is over the exact file bytes.

### Disposition breakdown (proposal recommendations; quorum still decides)

| Disposition | Rows | Meaning |
|---|---:|---|
| `APPROVE` | **720** | net-new stock-desk string — recommend forward to A1/A2/A3 quorum if owner approves this CSV |
| `REVIEW` | **16** | still in scope, flagged for explicit quorum disposition — 14 barcode/identifier tokens + 2 embedded-newline anomalies |
| `EXCLUDE` | **0 in CSV** | residual exclusions (HTML / `len>120`) are **not** in the CSV (see raw accounting) |
| `already-released` | **0 in CSV** | no raw-789 key is in the released catalog |
| **Total CSV rows** | **736** | |

`REVIEW` detail (retained for visibility, not pre-excluded):
14 barcode/identifier tokens (`CODE-39`, `EAN`, `EAN-8`, `EAN-12`, `GS1`,
`GTIN`, `ISBN`, `ISBN-10`, `ISBN-13`, `ISSN`, `JAN`, `PZN`, `UPC`, `UPC-A`)
+ 2 embedded-newline formatting anomalies
(`If enabled, do not update serial / batch values in the stock transactions on cre…`, `Per Day
Shift Time (In Hours) * No of Workstations * No of S…`).

### Composition

| Attribute | Value |
|---|---|
| Area split | **736 stock** (single matrix row; no other area) |
| Disposition | **720 APPROVE** + **16 REVIEW** (0 EXCLUDE / 0 already-released inside CSV) |
| Pre-filled `msgstr` from vendor review ledger | **379** (baseline Arabic carried into proposal panel) |
| Unfilled (AI proposal required at cycle time) | **357** |
| Placeholder rows (`{…}`) | **136** (format tokens retained as-is) |
| `length` range | 3–120 (360 rows ≤ 25; all ≤ 120) |
| HTML/template rows | **0** (excluded by cut rule) |
| Overlap with released catalog (`approved_ar_overrides.csv`, 2,319 Released) | **0** |
| Overlap with `release_decisions.json` (2,319 decisions) | **0** |
| Overlap with prior W6-0a / W6-0b / W6-1 / W6-2 scope ∪ payload ∪ released-list keys (29 files, union **2,891**) | **0** |
| Overlap with W6-2 batch 01 (270) / batch 02 (48) | **0 / 0** |
| Overlap with W6-1 accounting subset (`msgid`) | **0** |
| Overlap with 21 technical exclusions | **0** |
| Overlap with 302 a1/a2 dedup exclusions | **0** |
| Duplicates within the proposal itself | **0** |

### Cut rules (deterministic; same pipeline as W6-2)

1. Ledger rows with `skip` not yes; non-empty `msgid`.
2. First location path under `erpnext/stock/`
   (yields raw **789** unique msgids — exactly the matrix W6-3 count).
3. Deduplicate by `msgid` (first-wins; raw is already unique at 789).
4. Bound: `len(msgid) ≤ 120`; drop HTML/template (`<…>`).
5. Drop rows in released catalog, `release_decisions.json`, any prior
   Stage-6 scope/payload/released keys (W6-0a, W6-0b, W6-1, W6-2),
   technical exclusions (21), and a1/a2 dedup exclusions (302).
6. Classify disposition: `REVIEW` for barcode/identifier tokens and
   embedded-newline anomalies, else `APPROVE`.
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
| 2 | Non-`stock` vendor areas in the ledger (accounts, setup, manufacturing, projects, …) | outside matrix row W6-3 |
| 3 | Already-released catalog keys (`approved_ar_overrides.csv`, 2,319 Released; `release_decisions.json`, 2,319) | **0 keys from the raw 789 are in the catalog** — nothing removed on this ground |
| 4 | Prior Stage-6 scope/payload/released keys (W6-0a desk shell, W6-0b batches 01–07 + short-UI plan, W6-1 subset, W6-2 batches 01–02; 29 files, union 2,891) | intersection with raw = **0**; with scope = **0** |
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
the `source_text` key column; also join against `release_decisions.json`,
the shared exclusion files, and the prior Stage-6 scope/payload/released key
union; count duplicates inside the proposal.

| Check | Set A | Set B | \|A ∩ B\| |
|---|---|---|---:|
| Released catalog | scope (736) | `approved_ar_overrides.csv` Released (2,319) | **0** |
| Release decisions | scope (736) | `release_decisions.json` decisions (2,319) | **0** |
| Prior scopes union | scope (736) | 29 prior stage6 scope/payload/released files (2,891) | **0** |
| W6-2 batch 01 | scope (736) | batch-01 CSV (270) | **0** |
| W6-2 batch 02 | scope (736) | batch-02 CSV (48) | **0** |
| W6-1 subset | scope (736) | accounting subset `msgid` | **0** |
| Technical exclusions | scope (736) | 21 technical keys | **0** |
| Dedup exclusions | scope (736) | 302 dedup keys | **0** |
| HTML / long residuals | scope (736) | 13 HTML ∪ 40 only-long | **0** |
| Duplicates within proposal | scope (736) | scope (736) | **0** |
| Raw vs prior work | raw stock (789) | catalog ∪ release_decisions ∪ prior scopes ∪ tech ∪ dedup | **0** |

Also verified: scope `source_text` unique = 736; row count on read-back = 736;
scope `len ≤ 120`; no HTML matches in scope; `area` values = `{stock}` only;
disposition values = `{APPROVE: 720, REVIEW: 16}`
with no `EXCLUDE` / `already-released` rows inside the CSV.

**Headline result: `proposed_total=736, already_released_overlap=0,
net_new=736, duplicates_within_proposal=0`.**

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

### Site-override / catalog note (plan §12)

At cycle time a live test-site probe will detect existing `ar` Translation
rows whose `source_text` matches a batch key with non-empty text. Genuine
site overrides are preserved; import only applies genuine state changes.
**No rows are pre-removed from the 736-row CSV.**

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

## Boundary

- Proposal-only: approving this scope authorizes **only** the 736-row CSV
  above (sha256 above) to enter the governed cycle (site recon → AI proposal
  → quorum → AI-R → DRY_RUN → IMPORT → browser evidence → evidence re-pin)
  **on the test site** when you say go.
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
      sha256 `54e86438f0e453872b5a5399c9e62cccf35046a417d08a5b01732071ae02bed2`)
      as the exact next Stage 6 translation scope.
- [ ] Acknowledge disposition split **720 APPROVE + 16 REVIEW**
      (14 barcode tokens + 2 embedded-newline anomalies stay in scope for
      quorum to disposition).
- [ ] Acknowledge shared **21** technical + **302** dedup exclusions remain
      unchanged (0 overlap with this scope).
- [ ] Acknowledge the **53** raw residual exclusions stay out of scope
      (**13 HTML + 40 `len>120`**; mutually exclusive under cut priority).
- [ ] Acknowledge **0** already-released / prior-scope keys were found in the
      raw 789 (nothing dropped as a prior-work duplicate).
- [ ] Leave W6-4…W6-7 unapproved until a later proposal.
- [ ] Any direct term overrides for batch strings → terminology sheet before
      a future quorum panel.
