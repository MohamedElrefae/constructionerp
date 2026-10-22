# Stage 6 — W6-0b **batch 1** proposal (2026-09-22)

**Status: PROPOSAL for owner approval of this exact batch only — no quorum, no import, no production, no Stage-8.**

Supersedes treating the 1,915-row W6-0b cut as one governed import batch
(Owner directive, same day). The full cut remains a **proposal inventory**
(commit `ab92075`); translation work proceeds only in bounded batches of
~200–300 candidates after per-batch approval.

## Batch 1 — exact scope (presenting for approval)

| Item | Value |
|---|---|
| File | `docs/translation/stage6_w60b_batch01_rows_2026-09-22.csv` |
| Rows | **271** translation-candidates (all `app=frappe`, `length ≤ 40`) |
| sha256 | `8916118e82e23a4bc23c338b958090463bc4538d560b954697b33130e73171d3` |
| Priority basis | Most-used **Desk** chrome/actions + remaining **accounting workflow** short UI |
| Batch index | `01` of `07` in `stage6_w60b_batch_plan_2026-09-22.csv` (sha256 `12625007de564d363fc88842c5af3ef8cc7325bc0aec56bc513acecc9a65a97d`) |

Composition inside batch 1 (ranking only; classification unchanged):

| Tier | Rows | Meaning |
|---|---|---|
| 0 — accounting workflow | 13 | tight GL/payment/currency/period terms still in the short-UI cut (Ledger, On Payment *, Select Currency, Posting Timestamp, …) — the rest of heavy accounting report copy already shipped in W6-1 |
| 1 — core Desk chrome | 66 | toolbar/list/form actions and phrases (Reset sorting, Clear All, Show Preview, Notification Settings, Expand/Collapse All, …) |
| 2 — high desk-surface use | 192 | remaining short labels ranked by quoted hits in Frappe/Construction desk JS/HTML, then text |

## Batch plan (all 1,894 candidates — not for approval now)

Deterministic split via `docs/translation/stage6_w60b_batch_split_2026-09-22.py`
(byte-stable on re-run):

| Batch | Rows | Status |
|---|---|---|
| **01** | **271** | **presented for approval** |
| 02 | 271 | deferred — no approval requested |
| 03 | 271 | deferred |
| 04 | 271 | deferred |
| 05 | 270 | deferred |
| 06 | 270 | deferred |
| 07 | 270 | deferred |
| **Σ** | **1,894** | every candidate in exactly one batch |

Later batches are ordinary Desk/list/form strings without batch-1 priority;
they are **not** part of this approval.

## Documented technical exclusions (not translated)

| File | Rows | sha256 |
|---|---|---|
| `docs/translation/stage6_w60b_technical_exclusions_2026-09-22.csv` | **21** | `6400f6d3bc73aa290c09d442f7158d167df5369ac810c9b4e67796bb3f9b6095` |

These stay `EXCEPTION-technical` from the original cut (symbols-only, HTML
tag, newline, or JS `${…}`) — **keep vendor rendering; no translation**.
Retained as documented exclusions for AI-R suppress-check whenever a batch
cycle runs; they are not in any translation batch.

Prior-approved a1/a2 exclusions (302 rows) remain outside the 1,894
candidates entirely (`stage6_w60b_dedup_exclusions_2026-09-22.csv`).

## Boundary

- Proposal-only: approving batch 1 authorizes **only** the 271-row CSV above
  to enter the governed cycle (AI proposal → quorum → AI-R → DRY_RUN →
  IMPORT → browser evidence → re-pin) **on the test site** when you say go.
- **No** quorum, import, catalog change, production mutation, or Stage-8 work
  is started by this note.
- Batches 02–07 require separate approval later; expanding batch 1 beyond
  271 rows requires a new exact CSV + sha.

## Owner mark-up requested

- [ ] **Approve batch 1 only** — the 271-row CSV (sha256 above) as the exact
      W6-0b batch-1 translation scope.
- [ ] Acknowledge the 21 technical rows as permanent non-translation
      exclusions for W6-0b.
- [ ] Leave batches 02–07 unapproved until a later proposal.
- [ ] Any direct term overrides for batch-1 strings → terminology sheet before
      a future quorum panel.
