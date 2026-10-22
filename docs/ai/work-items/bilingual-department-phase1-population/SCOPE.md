# Scope Descriptor — bilingual-department-phase1-population

**Work item:** `bilingual-department-phase1-population`
**Branch:** `develop`
**Base commit:** `9ccb4cd`
**Date:** 2026-10-05
**Status:** `COMPLETE` — 276 rows classified; proposal v2 approved (review 13/14 + applied
revise; sha256 `dba85a4ceba5826094c1c7b6e25117afe8e0a696bcb1c3564699b0d736bf64a4`);
dry-run / apply (attempt 1 fail-closed → disclosed V2 → attempt 2 PASS) / post-verify all
PASS; gates green (matrix 21/21, reconciler 19/19, 5 lints). Full results in §8; evidence
under `evidence/`.
**Authority:** Owner's in-session choice after Tier 5F (`9ccb4cd`) closed: "Department
audit (Recommended)" — fixture inventory audit, extraction, governed translation review,
read-only until the population proposal is approved
**Scope:** Inventory and classify every Department row on `v16.localhost` under
deterministic rules (root / real-company / test-company noise / label noise), freeze a
Phase-1 allowlist (the company-less `All Departments` root + every row of the owner's
active company `Elrefae`), draft the governed Arabic proposal for that allowlist, and —
only after owner approval — run the standard dry-run → apply → verify cycle. The 262
test-company rows are audited and disclosed, **not** populated (separate future proposal
if ever needed).

---

## 1. The gap this closes

Department is a fully *enabled* bilingual surface with zero *data*:

- Registry `doctypes.Department` active since `bilingual-department-master` (wave era):
  `department_name` / `department_name_ar` / `department_name_ar_norm`, tree enabled,
  identity `name`, no code field.
- `enforce_bilingual_arabic_policy` bound to Department `validate` (`hooks.py:328`).
- Desk scope selector (`User Scope Context`) points its department at the root
  `All Departments` — the highest-visibility untranslated org surface.
- The owner's live company tree (`Elrefae`: 13 departments under the root) shows English
  only in tree views, pickers, and report filters.

## 2. Findings (from `inventory-export.log`, PASS)

| ID | Finding |
|---|---|
| **F-5G-1** | Site has **276** Department rows (not the 274 quoted off-hand during 5F §6 — stale figure; actual frozen by the export gate). 16 distinct `department_name` labels × 22 companies. |
| **F-5G-2** | Identity: company rows are named `'<label> - <abbr>'` (e.g. `Accounts - E`); root `name` == label. Canonical English = the `department_name` field; `name` must never change (registry `identity_field: name`; ERPNext `autoname`/`before_rename` own the suffix rule). |
| **F-5G-3** | Tree: single root `All Departments` (company NULL, `is_group=1`, lft1/rgt578); **all 275 children are flat under it** — no deeper nesting anywhere. NestedSet controller (`erpnext...department.py`: `class Department(NestedSet)`). |
| **F-5G-4** | Root save quirk (probed, §2.1): plain `save()` → `MandatoryError: company` (root deliberately has NULL company, field `reqd=1`); with `flags.ignore_mandatory` → `NestedSetRecursionError` because `Department.validate()` self-parents empty parents via `get_root_of` (returns the root's own name). Fix = 5D-R3b-style combined workaround, disclosed for approval. |
| **F-5G-5** | **No Department fixture JSON** exists (fixtures dir: uom.json, boq template, theme) → no sync-wipe risk of the 5F-F5 class; Arabic written by apply persists across `bench migrate` without any fixture edit. |
| **F-5G-6** | Glossary: 47 terms, **zero exact matches** on the 14 Phase-1 labels (substring noise only, e.g. "Subcontracting Purchase Order"). All values AI-proposed with rationale + alternates. |
| **F-5G-7** | Usage: only 3 references site-wide — root (1× `User Scope Context` scope selector, **in Phase 1**), `_Test Department - _TC` + `_Test Department 1 - _TC` (2× `Employee`, **excluded** as `_Test` label noise). `Elrefae`'s 13 are defined-but-unused (no employees/projects/GL yet); all transaction tables show 0 department references. |
| **F-5G-8** | Classification: root 1, `Elrefae` 13, test-company rows 260, `_Test`-label rows 2 → noise total 262 (21 test companies: `_Test Company*` family + ERPNext demo/test records `Best Test`, `Wind Power LLC`, `Trial Balance Company`, …). |
| **F-5G-9** | NSM bookkeeping: `old_parent` is stale (NULL) on 12 of the 14 rows while `parent_department` is set → `update_nsm()` takes the sibling-repositioning branch (`old_parent != parent`) and rewrites `lft/rgt` across the tree on the first save. Discovered at apply attempt 1 (fail-closed); resolved by disclosed amendment **V2** (pre-sync `old_parent` = current parent — the field update `update_nsm` performs unconditionally in both branches, so no extra write is introduced, and the move branch is skipped). |

### 2.1 Probe disclosures (all rolled back, zero residue)

| Probe | Path | Result |
|---|---|---|
| **P1** | Root, plain `doc.save()` after setting Arabic | `MandatoryError: company` — no write |
| **P2** | Root, `flags.ignore_mandatory=True` | `NestedSetRecursionError: Item cannot be added to its own descendants` (validate self-parent) — no write |
| **P3** | Root, `flags.ignore_mandatory` + scoped `department_module.get_root_of → None` restored in `finally` | **SAVE_OK** — only `department_name_ar`+`_norm` changed; name/parent/company/lft/rgt identical; norm server-derived; **rolled back** |
| **P4** | Normal row (`Accounts - E`), plain `doc.save()` | **SAVE_OK** — only Arabic+norm changed; **rolled back** |

Post-probe state verified: `department_name_ar` populated = **0**, 276 rows, tree intact.

## 3. Mechanism (no surprises)

- Apply = `doc.save()` through the registered validate hook (bidi gate + server-derived
  `_norm`); the 13 company rows are plain saves (**P4**).
- The root row (1 of 14) uses the P3 combined workaround — identical in spirit to
  5D's disclosed `R3b` root-save amendment: `flags.ignore_mandatory` (root has no company
  by design) + module-scoped `get_root_of → None` patch in try/finally (prevents the
  self-parent), restored before commit; **every other validation still runs**
  (bidi policy, NestedSet `on_update`, link checks). Pre-apply proof is P3.
- No fixture JSON, no `Translation` doctype, no registry/`hooks.py` edit, no vendor file.

## 4. Invariants

1. **D5 triad + registry byte-identical to `9ccb4cd`** (call-only; `bilingual_service.py`,
   `search.py`, `bilingual_registry.json` never edited).
2. No file under `apps/frappe` / `apps/erpnext` modified; no patch, hook, test, JS, or
   `?v=` change; zero manifest re-pins (`department` not pinned by any prior manifest —
   verified before commit).
3. Exactly the **14** approved Phase-1 rows written; identity (`name`), `department_name`,
   `parent_department`, `company`, `is_group`, `disabled`, `lft`, `rgt` unchanged on every
   row (verify diffs every frozen field).
4. The 262 test-company rows, all Employee/GL/etc. references, and every other prior
   bilingual surface stay untouched (5D frozen list carried forward).
5. **Fixture JSON:** untouched — F-5G-5 (no sync-wipe risk, contrast 5F-F5).
6. **Privacy R4:** proposal/dry-run/apply values under
   `sites/v16.localhost/private/department-phase1-population/`; committed evidence carries
   counts, classifications, sha256 digests only — **except** Arabic product data if/where
   it ever lands in an app file (it does not this cycle: no fixture edit).
7. **Production:** `production_mutation_authorized: false` (test site only).

## 5. R1–R7 (frozen rules)

- **R1 — frozen Phase-1 allowlist.** Export derives the set from live data
  (`company = 'Elrefae' OR name = 'All Departments'`) and asserts it equals the frozen
  literal of **14 row names** in the script (`{All Departments} ∪ {13 × ' - E'}`); drift
  fails the gate. `PRUNED/EXCLUDED`: 262 test-company rows (F-5G-8), `_Test`-label rows
  (5D fixture rule). Run result: `INVENTORY RESULT: PASS` — `PHASE1_FROZEN_MATCH yes`,
  `PRE_STATE_ARABIC 0`.
- **R2 — phases.** Phase 1 this cycle = 14 rows (root + Elrefae). Phase 2+ = the 262
  test-company rows — audited and disclosed; a future proposal decides if they ever get
  Arabic (default expectation: never; they are ERPNext test-record noise).
- **R3 — read-only until explicit approval; standard apply mechanics.** Export,
  classification, proposal are read-only. If/when the owner approves: dry-run (0 writes,
  sha gate) → apply (`doc.save()` ×14; root under the P3/R3b workaround) → post-verify
  (frozen-field diffs, norm consistency, usage surfaces, 262 untouched). Fail-closed
  rollback on any error; any new quirk becomes a disclosed amendment before commit.
- **R4 — privacy.** Private values + logs under
  `sites/v16.localhost/private/department-phase1-population/`; committed evidence = counts,
  English identities, verdicts, sha16 value hashes, digests.
- **R5 — completeness.** Phase 1 = 14/14 populated, norm-consistent, identity-unchanged;
  site total Arabic == 14 exactly (exceptions: all 262 test rows empty, PROBE residue 0);
  root Arabic visible in the desk scope selector.
- **R6 — repo hygiene.** New files under this work-item directory only → zero shared-file
  edits → zero re-pins; glossary untouched (flagged separately if owner wants unit/org
  terms added later).
- **R7 — no display/config changes.** No doctype_js, no registry state change, no
  tree/parent moves, no Company writes, `name` never altered.

## 6. Out of scope

- The 262 test-company Department rows (Phase 2+, default = never).
- Other doctypes not yet data-populated (e.g. Employee display surfaces beyond this tier).
- `Company` Arabic population (still empty site-wide) — separate tier.
- Glossary additions for org terms — separate governance action (flagged, owner decides).
- Production: not authorized.

## 7. Evidence causal order

export/inventory (read-only) → classification vs frozen 14-row allowlist → probe
disclosures (P1–P4, §2.1) → proposal v1 (14 values, private) → fresh-session review
(verdict per row) → owner approval (sha-bound) → dry-run (0 writes) → apply (13 plain
saves + 1 root R3b save) → post-verify (frozen-field diffs + usage + exceptions) → matrix
+ reconciler + lints → capture logs (`2>&1`) → `git add -f` the `.log` → SHA-256 digests
→ `MANIFEST.json` → commit.

## 8. Results (recorded on completion)

All executed on `v16.localhost` (test site only; production untouched), base `9ccb4cd`.

| Step | Result |
|---|---|
| Export / inventory | `inventory-export.log` → **PASS** — 276 rows classified (root 1 / Elrefae 13 / test-company 260 / `_Test`-label 2 → Phase 1 = **14**, exclusions 262), `PHASE1_FROZEN_MATCH yes`, `PRE_STATE_ARABIC 0`, usage + F-5G-1..8 findings printed. |
| Probes P1–P4 | §2.1 — root quirk characterized (MandatoryError → NestedSetRecursion → combined workaround OK), plain-row save OK; all rolled back, 0 residue. |
| Proposal v1 → review → v2 | v1 sha `cb0a10ee…e5c0a`; fresh non-author round 1: **13 approve / 1 revise** (root, in-app `جميع …` precedent) + 2 non-blocking notes applied; v2 sha256 **`dba85a4ceba5826094c1c7b6e25117afe8e0a696bcb1c3564699b0d736bf64a4`** (rows 2–14 byte-identical); `review-ai-a2.md` committed, private record sha `eaf0ec71…2f82d`. |
| Owner approval | `owner-approval.md` — v2 values, root R3B workaround, phasing 14/262, review chain; sha-bound hard gates. |
| Dry-run | `dry-run.log` → **PASS** — 14/14 validated (13 plain + 1 R3B root planned), frozen-field snapshots captured, `EXCLUSIONS excluded_rows=262`, approved sha matched, **`WRITES_PERFORMED: 0`**. |
| Apply attempt 1 | **FAIL-CLOSED, zero writes** — `Customer Service - E: lft/rgt changed` (F-5G-9: stale `old_parent` → NSM repositioning); full transaction rolled back. Disclosure **V2** (below + `apply.log` attempt-1 block; an intermediate rerun also aborted at parse time with no site interaction). |
| Apply attempt 2 | `apply.log` → **PASS** — `SUMMARY written=14 skipped=0 failed=0 r3b_root=1`; per-row field diff shows only `department_name_ar`, `department_name_ar_norm` (+ `old_parent` bookkeeping sync on the 12 stale rows); norm server-derived everywhere; identity/tree untouched. |
| Post-verify | `post-import-verification.log` → **PASS** — `populated=14 norm_consistent=14 identity_unchanged=14 tree_unchanged=14`; site Arabic total exactly 14 (0 missing / 0 extra); exclusions 262 intact, probe residue 0, total 276; usage surface (root Arabic + scope-ref intact, `_Test` depts empty); frozen prior surfaces (5D list + 5F UOM 15/253 + `uom.json` sha unchanged + Company empty); `get_root_of` patch restored. Disclosure **V3**: verify attempt 1 aborted on a read-only `TypeError` (missing `.read()` on the `uom.json` digest) after all row checks passed — fixed, rerun PASS, zero writes either way; log holds the final run. |
| Gates | `py_compile` 4 scripts OK; `lint_scope_metadata` PASS; `ai_context_check` PASS; `lint_translation_writes` PASS; `schema_drift` PASS; `bash -n` OK; ADR reconciler **19/19** (`reconciliation.log`); canonical matrix **21/21 modules OK, 264 tests, 0 failures** (`regression-matrix.log`; redis 11000/13000 started → run → torn down). |
| Open items flagged to owner | (a) 262 excluded test-company rows — Phase 2+, default expectation never; (b) `Company` Arabic still empty site-wide (separate tier); (c) glossary has no org-department terms (separate governance action if wanted). |

**Amendments**
- **V2 (apply, mid-cycle):** cause — stale `old_parent` made `update_nsm()` take the
  sibling-repositioning branch (would have rewritten `lft/rgt` tree-wide); fix — pre-sync
  `old_parent := parent_department` before save (field `update_nsm` syncs unconditionally
  in both branches; no extra write; move branch skipped; all other validations + strict
  frozen-field diff still enforced); attempt 1 rolled back fail-closed with zero writes;
  disclosure — `apply.log` attempt-1 block + F-5G-9 + this section.
- **V3 (verify, read-only):** attempt-1 `TypeError` on the `uom.json` digest read
  (script bug, after every substantive check had passed); corrected and rerun end-to-end,
  zero writes; disclosure — this section + final run in `post-import-verification.log`.
