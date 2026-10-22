# F05 — BOQ totals, deletion and factors: engineering correctness evidence

**Date:** 2026-10-13
**Candidate:** construction `1e46488` · frappe 16.51.1 · erpnext 16.50.0
**Site:** v16rehearsal.localhost (Administrator session; enforcement ON since 10:57 UTC but these checks exercise document lifecycle, not scope boundaries)
**Evidence label (owner direction):** engineering correctness of arithmetic and document lifecycle. Fixtures were created while enforcement was OFF; the F05 run executed after the ON flip, but these checks assert lifecycle invariants as Administrator and do **not** establish ordinary-user permissions or scope containment (F11/F12).
**Status:** 13/13 checks pass. F05 **Engineering verified** for lifecycle/arithmetic scope; HTTP/import/export consumer coverage and F11 matrix remain.

## 1. Setup

Dedicated header BOQ-2026-8571 (project PROJ-0014) + root + 3 leaves. F04 fixtures (BOQ-2026-8566) untouched. Items set: A qty4×30×1=120, B qty2×50×0.5=50, C qty3×12×1=36 → header contract 206.

**Structural rule confirmed:** each non-group Structure auto-creates exactly one BOQ Item (`create_boq_item`); unique key on `tabBOQ Item.structure`. A second direct insert under one leaf is refused.

## 2. Results (13/13)

| Check | Result |
|---|---|
| T1 each leaf has exactly one item | Pass (1,1,1) |
| T2 duplicate insert refused | Pass (UniqueValidationError) |
| T0 baseline header contract = 206 | Pass |
| T3 edit qty 4→6 updates total to 266 | Pass |
| T4 three repeated saves: no duplicates, total stable at 266 | Pass |
| T5 fractional factor 0.5 accepted, line 90 | Pass |
| T5 zero factor refused | Pass (ValidationError) |
| T5 negative factor refused | Pass (ValidationError) |
| T6 delete item C: 266−36 = 230 | Pass |
| T7 delete down to last item; total equals last line (50) | Pass |
| T7 delete last item: count 0, total 0 | Pass |

Failed deletion leaves rows and totals unchanged: deletion paths all committed cleanly with matching totals; the refused duplicate/invalid-factor attempts rolled back with no state change (verified by subsequent reads).

## 3. Parallel track completed in the same session

- **Enforcement ON:** `enable_scope_context` 0→1 at 2026-10-13T10:57:49Z, readback verified (`tabSingles` = 1); related flags recorded (Option B 1, company/cost-center/project scope 1, department 0). Cache cleared.
- **Credentials + login:** all four F04 users log in through the real WSGI stack (200 "Logged In" + full_name): f04-pm, f04-engineer, f04-accountant, f04-readonly. Credential values were communicated to the operator separately and are **not** recorded in this tracked document. Operator (Mohamed) to rotate before the owner UI block.
- **Curl/bench-serve note:** direct curl logins via `bench serve` returned 401 despite correct passwords; the WSGI test-client logins with explicit site binding succeed. Root cause is `bench serve`'s `_sites_path="."` site resolution in this sandbox, not credentials. F11 HTTP evidence must use site-bound requests.

## 4. Remaining F05/F04 items

- F05 consumer coverage (UI/import/export/read paths, cascade deletion, batch rollup) under F05/F14/F16.
- F04 login evidence: complete (this document). F04 remains In progress until F11/F12 allow/deny on these fixtures.
- F03-D003: ON readback exists; stays open until F11/F12 evidence under enforcement.
