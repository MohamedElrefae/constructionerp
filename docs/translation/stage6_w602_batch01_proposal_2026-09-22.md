# Stage 6 — W6-2 **Buying + Selling batch 01** proposal (2026-09-22)

**Status: PROPOSAL ONLY — owner mark-up pending. No quorum, no import, no catalog change, no production, no Stage-8.**

W6-0b short-UI cut is **exhausted** (batches 01–07 closed; batch-7 corrected
cycle accepted at `a0f01cb`; rejected attempt `8bfc23a` kept in history only).
This note proposes the **next bounded** Stage 6 workflow-matrix scope: matrix
row **W6-2** (Buying + Selling), first batch only.

## Exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w602_batch01_rows_2026-09-22.csv` |
| Rows | **270** translation-candidates |
| sha256 | `b017df4787ff8754be0bf43425151b748ba0aa019348fa29187f660130408fae` |
| Source ledger | `docs/erpnext_ar_missing_review_filled.csv` (4,342 rows; W6-2 raw = 143 buying + 194 selling = 337) |
| Matrix row | W6-2 in `stage6_workflow_matrix_proposal_2026-09-21.md` (Owner decision box ☐ until this approval) |
| Site (if approved to run) | `v16.localhost` test site only |

### Composition

| Attribute | Value |
|---|---|
| Area split | **133 buying** + **137 selling** |
| Pre-filled `msgstr` from vendor review ledger | **185** (baseline Arabic carried into proposal panel) |
| Unfilled (AI proposal required at cycle time) | **85** |
| `length` range | 3–111 (157 rows ≤ 25) |
| Placeholder rows (`{…}`) | **22** (format tokens retained as-is) |
| HTML/template rows | **0** excluded by cut rule (`<…>` / Jinja raw blocks not in this 270) |
| Overlap with released catalog | **0** |
| Overlap with W6-0b candidates / payloads / W6-0a / W6-1 | **0** |
| Overlap with 21 technical exclusions | **0** |
| Overlap with 302 a1/a2 dedup exclusions | **0** |

### Cut rules (deterministic, reproducible)

1. Ledger rows with `skip` not yes; non-empty `msgid`.
2. First location path under `erpnext/buying/` or `erpnext/selling/`.
3. Deduplicate by `msgid`.
4. Bound: `len(msgid) ≤ 120` (short/medium UI; drop >120-char HTML email templates and docs). Actual selected max = 111.
5. Drop rows whose msgid matches released catalog, any Stage-6 payload/W6-0b plan key, technical exclusions, or a1/a2 dedup exclusions.
6. Take **all 185 pre-filled** first, then **85 unfilled** by sorted order → 270.
7. Write CSV sorted by `area`, `source_text`.

CSV columns: `source_text,suggested_ar,locations,area,has_pre_filled`.

### Sample rows (not exhaustive)

Pre-filled:
`% Billed` → `نسبة المفوتر`,
`Advance Payment` → `دفعة مقدمة`,
`Action If Same Rate is Not Maintained` → `الإجراء إذا لم يتم الحفاظ على نفس السعر`,
plus remaining Buying/Selling settings, PO/SO lifecycle labels, and supplier/customer document strings from the review ledger.

Unfilled (AI proposal at cycle time):
`Allow Purchase Order with Zero Quantity`,
`Allow Request for Quotation with Zero Quantity`,
`Analysis Chart`,
`Billed, Received & Returned`,
plus remaining PO/RFQ/SO validation and settings labels (full set in CSV).

### Site-override / catalog note (plan §12)

At cycle time a live test-site probe will detect existing `ar` Translation rows
whose `source_text` matches a batch key with non-empty text. Genuine site
overrides are preserved; import only applies genuine state changes. **No rows
are pre-removed from the 270-row CSV.**

## Documented technical exclusions (unchanged, not in this batch)

| File | Rows | sha256 |
|---|---|---|
| `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` | **21** | `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` |

Shared W6-0b a1/a2 dedup exclusions (302) remain outside candidates
(`stage6_w60b_dedup_exclusions_2026-09-22.csv`,
sha256 `ee24f18fdfd451204e18e26c17c8d9e2fc6a7539efa634087f5f7de4848fe37b`).
**0 overlap** with either set.

### Batch source tokens flagged for quorum (not pre-excluded)

Technical/acronym/code tokens retained in the scope CSV for full visibility;
disposition stays with A1/A2/A3 + AI-R after approval, e.g. PO/RFQ/SO
abbreviations, `Billed`, `Returned`, `Analysis`, numeric/zero-quantity
settings labels. This proposal does **not** move them out of scope unilaterally.

## Remaining plan (not for approval now)

| Scope | Rows | Status |
|---|---:|---|
| W6-0b batches 01–07 (short-UI) | 1,894 | **closed** (batch 7 accepted `a0f01cb`) |
| **W6-2 batch 01 (this proposal)** | **270** | **presented for approval** |
| W6-2 remainder (bounded universe after cut ≈47 selling unfilled >120/HTML filter residual) | ~47 | later proposal if needed |
| W6-3 Stock | 789 raw / bounded TBD | not proposed |
| W6-4 Projects + BOQ | 61 + 90 | not proposed |
| W6-5 Setup | 484 | not proposed |
| W6-6 Deferred modules | ~849 | not proposed |
| W6-7 Frappe framework remainder | per frappe ledger | not proposed |

## Boundary

- Proposal-only: approving batch 01 authorizes **only** the 270-row CSV above
  (sha256 above) to enter the governed cycle (site recon → AI proposal →
  quorum → AI-R → DRY_RUN → IMPORT → browser evidence → evidence re-pin)
  **on the test site** when you say go.
- **No** AI proposal panel, quorum, import, catalog change, production
  mutation, Stage-8 work, or further batches is started by this note.
- Expanding beyond 270 rows requires a new exact CSV + sha256.
- Matrix row W6-2 owner box stays ☐ until you mark it.

## Owner mark-up requested

- [ ] **Approve W6-2 batch 01 only** — the 270-row CSV (sha256 above) as the
      exact next Stage 6 translation scope (Buying + Selling).
- [ ] Acknowledge shared 21 technical rows remain permanent non-translation
      exclusions (unchanged).
- [ ] Leave W6-3…W6-7 and any W6-2 remainder unapproved until a later proposal.
- [ ] Any direct term overrides for batch strings → terminology sheet before
      a future quorum panel.
