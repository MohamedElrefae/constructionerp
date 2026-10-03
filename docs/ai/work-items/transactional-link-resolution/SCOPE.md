# Scope Descriptor — transactional-link-resolution

**Work item:** `transactional-link-resolution`
**Branch:** `develop`
**Status:** `COMPLETE` — Sidecar implemented, verified against live site (18/18 unit, 171/171 matrix, 19/19 reconciliation), triad at 0 diff
**Base commit:** `28287e5` (RFC approved, decisions D1-D3 ratified)
**Date:** 2026-10-03
**Authority:** owner directive in session; prerequisites stipulated by `docs/ai/work-items/bilingual-wave2b-transactions/SCOPE.md` §7
**Scope:** Sidecar endpoint `transaction_link_search.py`, client hook in `searchable_dropdown.js`, regression suite `test_transaction_link_search.py`, and regression matrix expansion.

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
| `SCOPE.md` | this file — `COMPLETE` |
| Decisions D1–D3 | ratified 2026-10-03 (SCOPE §3) |
| Implementation | server complete (`transaction_link_search.py`); client route delivered but **NOT WIRED** (§8) |
| Tests & Matrix | 18/18 unit tests, 171/171 matrix tests across 13 modules, 19/19 reconciliation |
| Evidence / manifests | captured in `evidence/` with SHA-256 in `MANIFEST.json` |

---

## 7. Amendments (2026-10-03, post-`2e17df5` verification)

Independent verification of `2e17df5` passed every check but surfaced four defects,
each ratified by the owner before remediation:

| # | Defect | Remediation |
|---|---|---|
| 1 | `bilingual-narrative-sanitizer` manifest pinned `scripts/run_bilingual_regression_matrix.sh` at the 12-module byte state; this work item's matrix expansion broke a previously-passing pin (10/11) | re-pinned, with a §8 amendment note in that work item's `SCOPE.md` recording the completion-time digest |
| 2 | `bilingual-boq-title-ar-wiring` pinned `construction/hooks.py`, stale since `46aa201` (pre-existing) | re-pinned, with the same amendment pattern |
| 3 | `bilingual-wave1-masters` recorded `phase1_SCOPE.md` / `phase2_SCOPE.md`, which resolve nowhere; content digests match `bilingual-wave1-masters-phase1\|2/SCOPE.md` exactly | paths corrected to the real locations (content unchanged) |
| 4 | modified `searchable_dropdown.js` shipped without a cache buster (AGENTS.md §4.4) | `hooks.py:152` → `searchable_dropdown.js?v=1` |

Also added, beyond the original §4 deliverables:

- `_resolve_master_ids` now truncates with `[:TOP_K_MASTER_MATCHES]` so the
  bounded-recall property holds even if the callee over-returns.
- Two guard tests — `TestTopKBoundary` (RFC §7.2 K-boundary) and
  `TestClientServerAllowListDrift` (JS routing list must equal
  `TRANSACTION_LINK_CONFIG`) — giving 18/18 unit and 171/171 matrix.

Living artefacts (`hooks.py`, `scripts/run_bilingual_regression_matrix.sh`) are
pinned by three closed manifests. Every future change to either requires a re-pin;
that is recorded here rather than left to be discovered as a stale digest.

---

## 8. Client route status: NOT WIRED (2026-10-03)

The server endpoint `search_transactions` is live, whitelisted, and covered by 18/18 unit
tests. The **browser path is inert**:

- The routing branch lives in `searchable_dropdown.js` `setCustomQuery()`, on
  `SearchableDropdownEnhancer`.
- Nothing that `hooks.py` loads instantiates that class — see
  `docs/ai/work-items/search-query-convention/SCOPE.md` §2 and its wiring audit.
- Consequently no Link field in the UI currently reaches `search_transactions`.

The same work item records **D4** (positional-argument shift + tuple-shape mismatch) on the
`search_widget` custom-query path. The sidecar's *signature* already matches the canonical
order (it would not suffer D4a), but it returns dict rows and would suffer **D4b** if wired
through `search_link`. Wiring therefore requires the dispatcher preconditions in
`search-query-convention/SCOPE.md` §4.

`Implementation` in §6 above means **server complete**; the client route is delivered but
unwired, and §4 deliverable 2 is satisfied as code only.

## 9. Amendments (2026-10-03, post-`bilingual-brand-master`)

Two pinned artefacts moved because of D5 and the matrix expansion; digests are recorded
as `amendments[]` entries in `evidence/MANIFEST.json`.

| Artefact | Re-pinned from | Why it moved |
|---|---|---|
| `construction/tests/test_transaction_link_search.py` | `67c38024be722e41aba7f3bb44f2c746952b3692acb662728b342abc597fe054` | **D5 invariant split**: `TestTriadInvariantGuard` (1 test, registry byte-freeze) replaced by `TestInvariantGuard` (3 tests: code diad byte-identity, registry monotonic growth, doctype-set growth) → module 18 → **20 tests**; §1 docstring updated |
| `scripts/run_bilingual_regression_matrix.sh` | `0252438c3342d0093cfbd8c8be6e2c7270203d9569ac936e3b04d1449ca224e4` | shared runner expanded to **14 modules / 181 tests** by `bilingual-brand-master` |

This work item's RFC/SCOPE/evidence logs and `transaction_link_search.py` are untouched.


## 10. Amendments (2026-10-04, post-`bilingual-asset-master`)

Digests are recorded as `amendments[]` entries in `evidence/MANIFEST.json`;
this work item's own evidence logs are unchanged.

| Artefact | Why it moved |
|---|---|
| `scripts/run_bilingual_regression_matrix.sh` | shared runner expanded to **16 modules / 197 tests** |

## 11. Amendments (2026-10-04, canonical matrix integration)

| Artefact | Why it moved |
|---|---|
| `scripts/run_bilingual_regression_matrix.sh` | shared runner expanded to **17 modules / 209 tests** (`test_boq_link_queries` promoted into the runner) |
