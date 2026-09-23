# Stage 6 — W6-2 **Buying + Selling batch 02** proposal (2026-09-23)

**Status: PROPOSAL ONLY — owner mark-up pending. No quorum, no import, no catalog change, no evidence re-pin, no production, no Stage-8.**

W6-2 batch 01 is **closed** (owner-approved exact 270-row CSV sha
`b017df47…`, governed cycle complete on `v16.localhost`, commit `073458e`).
This note proposes the **next bounded** Stage 6 scope: matrix row **W6-2**
remainder only — batch 02.

Evidence re-pin is **deferred** to the next catalog cycle that actually
changes the packaged catalog (owner directive: re-pin rides that cycle).

## Exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w602_batch02_rows_2026-09-23.csv` |
| Rows | **48** translation-candidates |
| sha256 | `9a096273f2f7ef05a403edffbb4b75604b73ce7f854382c8fd570f5c329e44ce` |
| Source ledger | `docs/erpnext_ar_missing_review_filled.csv` (4,342 rows; W6-2 raw first-location = 143 buying + 194 selling = 337) |
| Matrix row | W6-2 in `stage6_workflow_matrix_proposal_2026-09-21.md` (remainder after batch 01) |
| Site (if approved to run) | `v16.localhost` test site only |

### Composition

| Attribute | Value |
|---|---|
| Area split | **0 buying** + **48 selling** |
| Pre-filled `msgstr` from vendor review ledger | **1** (`Address` → `العنوان`) |
| Unfilled (AI proposal required at cycle time) | **47** |
| Placeholder rows (`{…}`) | **17** |
| `length` range | 7–119 (all ≤ 120) |
| HTML/template rows | **0** (excluded by same cut rule as batch 01) |
| Overlap with released catalog (2,275) | **0** |
| Overlap with W6-2 batch 01 (270) | **0** |
| Overlap with all prior W6-0b batch rows / payloads / released lists (26 files) | **0** |
| Overlap with 21 technical exclusions | **0** |
| Overlap with 302 a1/a2 dedup exclusions | **0** |

### Cut rules (deterministic; same pipeline as batch 01)

1. Ledger rows with `skip` not yes; non-empty `msgid`.
2. First location path under `erpnext/buying/` or `erpnext/selling/`
   (yields raw 143 + 194 = 337 unique msgids after first-wins dedup).
3. Deduplicate by `msgid`.
4. Bound: `len(msgid) ≤ 120`; drop HTML/template (`<…>`).
5. Drop rows in technical exclusions, a1/a2 dedup exclusions, current
   released catalog, and any prior W6-0b scope/payload/released keys.
6. Subtract the exact batch-01 scope CSV (all 270 keys, including the two
   cycle-fix forms `' Address'` and `'Could not find path for '`).
7. Write CSV sorted by `area`, `source_text`.

CSV columns: `source_text,suggested_ar,locations,area,has_pre_filled`.

### Full W6-2 raw accounting (337 unique first-location msgids)

| Bucket | Rows | In batch 02? |
|---|---:|---|
| Batch 01 scope keys (raw) | 268 | no — closed |
| Batch 02 candidates | **48** | **yes — this proposal** |
| `len > 120` residual (outside batch-01 short-UI bound) | 15 | **no — excluded** (same bound as batch 01) |
| HTML/template residual | 5 | **no — excluded** (same rule as batch 01) |
| Already in released catalog (`Could not find path for` — fixed/released in batch-01 cycle) | 1 | **no — excluded** |
| **Total** | **337** | |

Synthetic batch-01 keys not present as exact ledger msgids (kept in batch 01
only; not double-counted in the 337): `' Address'`, `'Could not find path for '`.
`Advance Payment` was already-released at batch-01 proposal time (in old
catalog at `e522739`).

### Sample rows (not exhaustive)

Pre-filled:
`Address` → `العنوان`.

Unfilled (AI proposal at cycle time): POS lifecycle
(`POS has been closed at {0}. Please refresh the page.`, `POS invoice {0}
created successfully`), delivery-schedule validations, sales-opportunity
labels (`Sales Pipeline by Stage`, `Sales Opportunities by Campaign`),
subcontracting/hold labels, plus remaining Selling desk strings (full set
in CSV).

### Batch source tokens flagged for quorum (not pre-excluded)

Technical/identifier tokens retained in the scope CSV for full visibility;
disposition stays with A1/A2/A3 + AI-R after approval, e.g. `doctype`,
`doc_type`, `quotation_item`, `discount applied`, `{}  To Deliver`,
`Total Only`, `Sold by`, `Reason for hold:`. This proposal does **not**
move them out of scope unilaterally.

### Site-override / catalog note (plan §12)

At cycle time a live test-site probe will detect existing `ar` Translation
rows whose `source_text` matches a batch key with non-empty text. Genuine
site overrides are preserved; import only applies genuine state changes.
**No rows are pre-removed from the 48-row CSV.**

Note: batch 01’s Address strip-collision used the leading-space form
`' Address'` (preserved, not catalogued). Batch 02’s key is the exact
ledger msgid `Address` (7 chars, no leading space) — different key,
**0 overlap** with batch 01 and with the released catalog.

## Documented technical exclusions (unchanged, not in this batch)

| File | Rows | sha256 |
|---|---|---|
| `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` | **21** | `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` |

Shared W6-0b a1/a2 dedup exclusions (302) remain outside candidates
(`stage6_w60b_dedup_exclusions_2026-09-22.csv`,
sha256 `ee24f18fdfd451204e18e26c17c8d9e2fc6a7539efa634087f5f7de4848fe37b`).
**0 overlap** with either set.

## Remaining plan (not for approval now)

| Scope | Rows | Status |
|---|---:|---|
| W6-0b batches 01–07 (short-UI) | 1,894 | **closed** (batch 7 accepted `a0f01cb`) |
| W6-2 batch 01 | 270 | **closed** (`073458e`) |
| **W6-2 batch 02 (this proposal)** | **48** | **presented for approval** |
| W6-2 >120 / HTML residual | 20 | excluded by cut bound — **not proposed** |
| W6-3 Stock | 789 raw / bounded TBD | not proposed |
| W6-4 Projects + BOQ | 61 + 90 | not proposed |
| W6-5 Setup | 484 | not proposed |
| W6-6 Deferred modules | ~849 | not proposed |
| W6-7 Frappe framework remainder | per frappe ledger | not proposed |

After batch 02, the W6-2 short-UI universe under these cut rules is
**exhausted** (337 raw = 270 batch 01 + 48 batch 02 + 20 excluded residual).

## Boundary

- Proposal-only: approving batch 02 authorizes **only** the 48-row CSV above
  (sha256 above) to enter the governed cycle (site recon → AI proposal →
  quorum → AI-R → DRY_RUN → IMPORT → browser evidence → evidence re-pin)
  **on the test site** when you say go.
- **No** AI proposal panel, quorum, import, catalog change, evidence
  re-pin, production mutation, Stage-8 work, or further batches is started
  by this note.
- Expanding beyond 48 rows requires a new exact CSV + sha256.
- Matrix row W6-2 owner box stays ☐ until you mark it.

## Owner mark-up requested

- [ ] **Approve W6-2 batch 02 only** — the 48-row CSV (sha256 above) as the
      exact next Stage 6 translation scope (Buying + Selling remainder).
- [ ] Acknowledge shared 21 technical rows remain permanent non-translation
      exclusions (unchanged).
- [ ] Acknowledge the 15 `len>120` + 5 HTML residuals stay out of scope
      under the batch-01 short-UI bound.
- [ ] Leave W6-3…W6-7 unapproved until a later proposal.
- [ ] Any direct term overrides for batch strings → terminology sheet before
      a future quorum panel.
