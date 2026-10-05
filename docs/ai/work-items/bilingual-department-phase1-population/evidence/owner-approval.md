# Owner Approval — bilingual-department-phase1-population

**Work item:** `bilingual-department-phase1-population`
**Base commit:** `9ccb4cd` · **Site:** `v16.localhost` (test only) · **Date:** 2026-10-05

## 1. What was approved

The owner approved, in-session, after reading the round-1 review outcome:

| # | Decision | Value |
|---|---|---|
| 1 | **Phase-1 proposal v2 — 14 rows** (company-less root `All Departments` + the 13 `Elrefae` departments) | sha256 `dba85a4ceba5826094c1c7b6e25117afe8e0a696bcb1c3564699b0d736bf64a4` |
| 2 | **Root-row save mechanism** (row 1 of 14): the disclosed 5D-R3b-style workaround — `flags.ignore_mandatory` (root has NULL company by design) + module-scoped `get_root_of → None` in try/finally, restored before commit; every other validation (bidi policy, NestedSet `on_update`, links) still runs | pre-proven in probe P3, rolled back |
| 3 | **Phasing** | 14 this cycle; the 262 test-company rows excluded (Phase 2+, default expectation: never) |
| 4 | **Review chain** | fresh non-author round 1: 13 approve / 1 revise (root, in-app `جميع …` precedent) → revision applied → v2 = effective **14/14** |

## 2. Bound artefacts (sha256)

| Artefact | sha256 |
|---|---|
| `proposal.json` **v2 (approved, binding)** | `dba85a4ceba5826094c1c7b6e25117afe8e0a696bcb1c3564699b0d736bf64a4` |
| `proposal-v1.json` (preserved round-1 input) | `cb0a10ee61e7bad14eb6847acc26530af6d351b5848781a80948a7307cee5c0a` |
| `review-ai-a2.json` (private verdict record) | `eaf0ec7174a24a71846f4ab23441c521b140e7894e779ec767038019f362f82d` |
| `evidence/review-ai-a2.md` (committed, redacted) | per MANIFEST |

Private paths: `sites/v16.localhost/private/department-phase1-population/`.

## 3. Authorized sequence (hard gates)

1. **Dry-run** — proposal sha must equal the v2 binding above (byte gate); 0 writes;
   live-row pre-checks; fail-closed otherwise.
2. **Apply** — plain `doc.save()` for the 13 company rows; row 1 (`All Departments`) via
   the §1-2 workaround; one transaction, fail-closed rollback on any error; norm keys
   derived **server-side** by the registered validate hook; `name`, `department_name`,
   `parent_department`, `company`, `is_group`, `disabled`, `lft`, `rgt` never edited.
3. **Post-verify** — 14/14 value + norm + frozen-field diffs; site Arabic total exactly
   14; all 262 excluded rows empty; PROBE residue 0; usage surface (scope selector root)
   shows Arabic; prior bilingual surfaces frozen (5D list); total 276 unchanged.
4. **Gates** — py_compile, `lint_scope_metadata`, `ai_context_check`,
   `lint_translation_writes`, `schema_drift_checker`, `bash -n`, ADR reconciler 19/19,
   canonical matrix 21 modules (redis 11000/13000 started → run → torn down).
5. **Evidence** — logs captured `2>&1`; `git add -f` the `.log`; digests; new
   `MANIFEST.json` (27th) + full verification (0 bad, zero re-pins); stage; owner verifies
   staged digests before commit.

## 4. Explicitly NOT authorized

- Any write to the 262 excluded Department rows or any other doctype's data.
- Edits to `bilingual_service.py`, `search.py`, `bilingual_registry.json`, `hooks.py`,
  patches, tests, JS, or any file under `apps/frappe` / `apps/erpnext`.
- `Translation` doctype writes; parent/name/company moves; Company Arabic population.
- Production (`production_mutation_authorized: false`).

Approval recorded in-session (question tool) at base `9ccb4cd`.
