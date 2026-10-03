# Scope Descriptor — transactional-link-resolution

**Work item:** `transactional-link-resolution`
**Branch:** `feature/transactional-link-resolution`
**Status:** `DESIGN_APPROVED` — RFC approved by owner (2026-10-03); decisions D1 (Option C), D2 (Journal Entry excluded in v1), D3 (four replacement directional properties) ratified
**Base commit:** `ab5dcdf` (develop clean; hook-matrix Scope B closed)
**Date:** 2026-10-03
**Authority:** owner directive in session; prerequisites stipulated by `docs/ai/work-items/bilingual-wave2b-transactions/SCOPE.md` §7
**Scope:** documentation only at this stage — RFC + scope descriptor. Design ratified; ready for implementation planning.

---

## 1. Background & Context

Wave 2b deferred transactional bilingual search and preserved three prerequisites
(`bilingual-wave2b-transactions/SCOPE.md` §7): an RFC renegotiating the zero-service-edit
invariant, a deliberate `RANK_WINDOW` design with an overflow contract, and a matched-set
equivalence proof. `Asset`, `Brand`, and `Terms and Conditions` were deferred contingent on
this work.

This item discharges prerequisite 1 (and redesigns prerequisite 3, which is unachievable as
literally written — see RFC §7.1). Prerequisite 2 is discharged in RFC §4 against the verified
contract: `RANK_WINDOW = 5000` (`bilingual_service.py:75`) with a `+1` overflow probe and
loud, never-silent, truncation (`search.py:171`).

---

## 2. Verified Facts the RFC Rests On

Established by direct inspection, not assertion:

1. `searchable_link_search` declares `link_fieldname` and `reference_doctype`
   (`search.py:21–22`) and **never reads them** — Frappe already delivers the cross-table
   context and discards it.
2. `get_mapping` returns `None` **silently** for doctypes absent from the registry
   (`bilingual_service.py:144–146`); it raises only for `active`/`schema_installed` mappings
   with missing fields (`:159–160`). The unmodified function therefore serves an unregistered
   transactional doctype today.
3. A blank-query path already exists: `if search_txt:` (`search.py:124`) guards all
   `or_filters`; the empty branch (`:148–154`) is bounded pagination with `filters` applied
   and `page_length` clamped to `≤ 200` (`:145`).
4. `filters` is applied on both branches (`search.py:153`, `:168`), so a server-side
   `{"customer": ("in", ids)}` tuple works with no JSON round-trip.
5. The client route is `setCustomQuery()` in
   `construction/public/js/searchable_dropdown/searchable_dropdown.js`, loaded via
   `hooks.py:152` — **outside** the invariant triad.
6. `Journal Entry` has **no parent-level party Link**; its account references live in
   `tabJournal Entry Account` (live metadata).
7. Live row counts: Sales Invoice 3,977 · Stock Entry 1,991 · Journal Entry 1,493 ·
   Purchase Invoice 994 · Material Request 670 · Sales Order 497 · Purchase Receipt 497 ·
   Purchase Order / Timesheet / Payment Entry 0.

---

## 3. Decisions Ratified by the Owner

All three required design decisions ratified on 2026-10-03:

| # | Decision | Ratified Resolution |
|---|---|---|
| **D1** | **Invariant outcome.** | **Option C APPROVED.** The zero-service-edit invariant does not end; triad `{bilingual_service.py, search.py, bilingual_registry.json}` remains at **0 diff** via the sidecar architecture. |
| **D2** | **`Journal Entry`.** | **Exclude in v1 APPROVED.** Scope is strictly parent-level party links. `Journal Entry` account references live in child table `tabJournal Entry Account` and are recorded as deferred. |
| **D3** | **Matched-set equivalence (§7.3).** | **Replacement properties APPROVED.** The four directional properties (no phantom rows, bounded recall, native agreement on Latin/ASCII, determinism) adopted in place of literal set equality. |

---

## 4. Deliverables (post-approval)

1. Sidecar endpoint `construction/services/transaction_link_search.py` — allow-list
   validation, Option B pre-resolution, delegation to the unmodified `searchable_link_search`
   with `txt=""`, Arabic label enrichment.
2. Client route in `searchable_dropdown.js` `setCustomQuery()` branching on the allow-list.
3. Pre-resolution top-K cap by master-side relevance (RFC §4.3) as a declared constant.
4. Tests: **the `txt` trap** (must be asserted, not documented), boundary tests for K and for
   `page_length`, allow-list rejection, and the §7.1 directional properties.
5. New module added to `scripts/run_bilingual_regression_matrix.sh` (canonical matrix grows
   from 12 modules / 153 tests).
6. Measurement run → evidence logs → `MANIFEST.json`, per the causal order.

---

## 5. Invariants Preserved

- `construction/services/bilingual_service.py` — 0 modified lines
- `construction/searchable_dropdown/api/search.py` — 0 modified lines
- `construction/data/bilingual/bilingual_registry.json` — 0 modified lines (**no
  `link_resolution_fields`; RFC §5 explicitly declines the registry extension**)
- `apps/frappe`, `apps/erpnext` — 0 modified lines
- Canonical regression matrix — 153/153 green at entry (12 modules)
- ADR reconciliation — 19/19 OK at entry
- Transactional resolution fields are **never** added to any registry `search.fields`

---

## 6. Current State

| Artefact | State |
|---|---|
| `RFC.md` | `APPROVED` (owner decision, 2026-10-03) |
| `SCOPE.md` | this file — `DESIGN_APPROVED` |
| Decisions D1–D3 | ratified 2026-10-03 (SCOPE §3) |
| Implementation | not started; **authorised** to begin per ratified design |
| Evidence / manifests | none yet — created only after implementation |
