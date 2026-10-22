# Scope Descriptor — bilingual-wave1-masters-population

**Work item:** `bilingual-wave1-masters-population`
**Branch:** `develop`
**Base commit:** `7839e67`
**Date:** 2026-10-04
**Status:** `COMPLETE` (2026-10-05) — all 9 in-scope wave-1 master rows populated on `v16.localhost`
under the approved proposal `a00cfb43…1c77`; all evidence gates green, zero shared-file changes
**Authority:** Plan Tier 5B ("production Arabic data population"); owner session decision narrowed the
target to **test-site wave-1 masters** after ground truth showed Elrefae's chart is already 81/81
complete and production mutation remains unauthorized in this bench
**Scope:** Populate `Item.item_name_ar`, `Customer.customer_name_in_arabic` (Supplier in-scope = 0)
for the non-fixture wave-1 subset on `v16.localhost` through a D4/D5-shaped governed cycle —
export → independent proposal → independent AI-A2 review → **owner approval** → dry-run →
import → post-import verification — with zero app-code changes, zero vendor edits, and a
committed completeness/exception report.

---

## 1. The gap this closes

Wave-1 schema, registry, adapters and tests shipped earlier
(`bilingual-wave1-masters`, `bilingual-wave1-masters-phase1`, `bilingual-wave1-masters-phase2`):
Arabic fields + `_norm` fields installed, registry entries **active**, bidi rejection +
server-authoritative norm enforced by `enforce_bilingual_arabic_policy`, both pilot test modules
in the canonical matrix. What never happened is the data itself:

- **0 of 43 Items, 0 of 12 Customers, 0 of 10 Suppliers** carry Arabic values
  (`scope-context-portability/evidence/stage5-wave1-readiness-2026-09-20.md`).
- Stage-5 readiness recorded the inventory and offered the owner a fork: (a) defer data
  migration to Stage 8, or (b) pilot now under the full D4/D5 cycle. The owner chose (a) on
  2026-09-20 (`ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md:852`).
- Tier 5B reopens exactly option (b), scoped by the owner's session answer
  ("Test-site wave-1 masters"): populate the **non-fixture** subset on the authorized
  non-production test site now.

## 2. Verified current state (probed 2026-10-04, base `7839e67`)

| Fact | Value |
|---|---|
| Account chart | Elrefae **81/81 populated** (the 5 empty leaves are `CT-SCHEMA-*` test-schema accounts, correctly outside the Stage-4 bundle) — Tier 5B touches **no** Account row |
| Items non-fixture (excl. `_Test*`, `TEST-CONC-%`) | 14 rows: 8 readiness candidates + 6 scaffolding rows |
| Customers non-fixture | 2: `Prestiga-Biz` (real, live AR EGP 6,000) + `Test Loyalty Customer` (scaffolding) |
| Suppliers non-fixture | **0** — all 10 are vendor `_Test*` fixtures |
| Fixture governance | "vendor `_Test*` fixtures are excluded from any future Wave-1 Arabic migration by governance" (stage5-wave1-readiness L49-52) |
| Registry | `Item`/`Customer`/`Supplier` all `state: active` with `arabic_field` + `norm_field` declared — display/search already enabled, nothing to change |
| Write governance | **Deliberate asymmetry vs Account** (documented at `bilingual_service.py:320-329`): wave-1 masters admit standard Desk/CSV/REST writes; the validate hook rejects bidi controls and derives `_norm` server-authoritatively on every save. No token machinery exists — or is needed — for these fields |
| Existing tooling | Account-only (`account_language_proposal.py`, `account_review_bundle.py`); **no** non-Account proposal/export tool exists |
| Prior bulk writer | `cost_database_service.py` already writes `item_name_ar` on cost import (in-scope precedent for population writes) |
| Tests | `test_bilingual_wave1_pilot` (8) + `test_bilingual_wave1_phase2_pilot` (9) already in the 21-module matrix (258 tests) |
| Site classification | `non-production test`, `production_mutation_authorized: false` — this item mutates the **authorized test site only** |

## 3. Decisions

### R1 — in-scope set = Stage-5 readiness candidates; everything else is a documented exception

In scope (**9 rows, must reach 100% approved**):

- Items (8): `OH-SITE-ADMIN-001`, `SUBCONCRETE-001`, `PLANT-MIXER-001`, `LAB-MASON-001\``,
  `Consulting`, `Macbook Pro`, `Photocopier`, `138-CMS Shoe`
- Customers (1): `Prestiga-Biz`
- Suppliers (0): none exist outside `_Test*` — recorded as an explicit zero-population exception

Documented exceptions (never written): all `_Test*` vendor fixtures; `TEST-CONC-%` scaffolding;
`Test Loyalty Customer`, `Test Asset Item`, `Test Esstimate`, `Loyal Item`,
`Stock-Reco-batch-Item-1`, `Stock-Reco-Serial-Item-1`, `Stock-Reco-Serial-Item-2`.
The completeness rule is "100% approved names **or documented exceptions**" — the completeness
report in §5 carries both lists.

### R2 — D4/D5-shaped governed cycle, with owner approval as the hard gate

`export → independent proposal → independent AI-A2 review → owner approval → dry-run → import →
post-import verification`

- **Proposal and review are separate sessions.** The proposal is authored in this session; the
  AI-A2 review is executed by a distinct subagent session (different session identity, no access
  to the proposal's rationale beyond the proposed rows themselves), returning per-row
  verdicts/rationales exactly like the Stage-4 panel contract
  (`docs/ai/roles/ai-reviewer.md`).
- **Owner approval is non-delegable:** the full proposal + review table is presented in-session;
  import does not start without the owner's explicit go.
- Nothing may be written before the approval gate; the dry-run runs after approval and must
  match what the owner approved (identical row set, before/after values).

### R3 — write path: standard document save through the existing validate hook

Import = `frappe.get_doc(...); doc.<arabic field> = value; doc.save()` as Administrator.
The existing `enforce_bilingual_arabic_policy` hook then guarantees bidi rejection and a fresh
server-authoritative `_norm`. **No new setter, no token, no hook change, no app-code change of
any kind** — the policy asymmetry (Account strict, wave-1 standard) is by design and stays.

### R4 — data privacy: values private, hashes committed

Full values and the rollback export live under
`sites/v16.localhost/private/wave1-population/` (site master data is access-controlled backup
material per the canonical plan L76). Committed evidence carries counts + SHA-256 digests only
(same pattern as the Stage-4 export manifest).

### R5 — completeness = 100% of in-scope rows approved, exceptions enumerated

The post-import verification emits: per-doctype in-scope/approved/populated counts, the full
exception list, norm-consistency check (`<field>_norm == normalize_arabic(<field>)` for every
written row), and a bidi sanity check. Any in-scope row not populated fails the item.

### R6 — evidence pipeline, no shared-file edits, therefore zero manifest re-pins

This item touches only new files under its own work-item directory plus private site data — no
hooks, no matrix script, no tests, no service code. Gates: export/inventory log, proposal +
review records, owner-approval record, dry-run log, apply log, post-import verification log,
matrix rerun (21/258, unchanged), reconciler 19/19, lints, `MANIFEST.json`. Because no shared
living file changes, **no other manifest needs re-pinning** (unlike Tier 4/5A).

### R7 — no display/config changes

Registry `form.identity_section` stays `false` for wave-1 doctypes; no `doctype_js`, no `?v=`
bump, no Cost Center/Warehouse/Project work (phase-2 territory), no Account rows, no
translation-catalog (Stage 6) strings.

## 4. Invariants preserved

- **Vendor boundary:** zero files under `apps/frappe` / `apps/erpnext` change.
- **D5 triad / registry:** `bilingual_service.py`, `searchable_dropdown/api/search.py`,
  `bilingual_registry.json`, `bilingual_registry.py` untouched (only *called*, never edited).
- **Account surface:** no `account_name_ar` write; Stage-4 bundle/manifest untouched.
- **Mutation boundary:** exactly the 9 in-scope rows' Arabic field + derived `_norm`;
  rollback export captured before the first write; narrative fields untouched.
- **No app-code changes:** no service, hook, patch, test, JS, or registry edit ⇒ no `?v=` bump,
  no matrix-header change, no manifest re-pins.
- **Fixture protection:** `_Test*` / scaffolding rows enumerated in the exception report and
  structurally excluded from the apply script (name-based allowlist = the R1 list, never a
  broad "all rows" write).

## 5. Tests and evidence gates

No new test modules (site data state is verified by evidence scripts, not unit tests — the
behavioral surface is already covered by `test_bilingual_wave1_pilot` + phase2 in the matrix).
Evidence gates:

1. `inventory-export.log` — live row inventory with fixture classification (R1 lists).
2. `proposal.md` / `proposal.json` (private) + committed sha — 9 proposed values with
   confidence, provenance, glossary notes.
3. `review-ai-a2.md` — independent per-row verdicts from the separate review session (R2).
4. `owner-approval.md` — the approved table as accepted by the owner in-session.
5. `dry-run.log` — exact before/after for the approved rows, zero writes (asserted).
6. `apply.log` — import execution; per-row success; counts.
7. `post-import-verification.log` — 9/9 populated, norm consistency, bidi sanity, exception
   report, rollback-export sha.
8. `regression-matrix.log` — 21/258 all OK (rerun as the bilingual-surface gate).
9. `reconciliation.log` — reconciler 19/19.
10. Lints: `lint_scope_metadata`, `ai_context_check`, `lint_translation_writes`.

Causal order (mandatory): final verification run → capture log (`2>&1`) → `git add -f` the
`.log` → SHA-256 digests → `evidence/MANIFEST.json` → commit. Verify via `git show HEAD:<path>`.

## 6. Out of scope

- **Stage 8 / true production:** no production site exists in this bench;
  `production_mutation_authorized: false`; Stage-8 gates (named production site, production
  data, rollout window, backup confirmation) remain owner-gated.
- **Fixture rows** (`_Test*`, scaffolding) — permanent exceptions for this site.
- **Supplier population** — zero in-scope rows (exception documented).
- **Phase-2 doctypes** (Cost Center, Warehouse, Project) — registry entries only, untouched.
- **Account chart** — already complete; not read-modified beyond verification counts.
- **Form/identity-section config, doctype JS, print formats, translation catalogs (Stage 6).**
- **Cost Database import behavior** (`cost_database_service.py`) — existing writer, untouched.

## 7. Evidence causal order

export/inventory → proposal → independent review → **owner approval** → dry-run → apply →
post-import verification → matrix + reconciler + lints → capture logs (`2>&1`) → `git add -f`
the `.log` files → SHA-256 digests → `evidence/MANIFEST.json` → commit.

## 8. Results (recorded on completion)

| Gate | Result |
|---|---|
| Inventory export (R1) | PASS — allowlist matches live site, pre-state empty, no unclassified non-fixture rows |
| Proposal → review → approval (R2) | proposal v3 sha `a00cfb43…1c77`; 3 independent AI-A2 review rounds (2 approve/3 revise, 2 approve/1 revise, approve-high); every final value approved by a non-author session; owner approval of the exact sha recorded in `evidence/owner-approval.md` |
| Dry-run (zero writes) | PASS — `9/9 rows validated; approved sha matched; zero writes` |
| Apply | PASS — 9/9 written, 0 skipped/failed; per-row `identity=unchanged`; norms server-derived by the validate hook; transaction committed; rollback export = `dry-run.json` (before-values all empty, sha `1d016b0f…e1882`) |
| Post-import verification | PASS — `in_scope=9 populated=9 norm_consistent=9 identity_unchanged=9 exceptions=0`; completeness 8/8 Items, 1/1 Customers, 0/0 Suppliers (zero-population exception); scaffold + `_Test*` fixture protection intact; row totals unchanged (43/12/10); Account Arabic surface unchanged at 81; norm-key search resolves 9/9 |
| Regression matrix | 21 modules / 258 tests, all OK (unchanged, as R6 predicted) |
| ADR↔evidence reconciler | 19/19 PASS |
| Lints | `lint_scope_metadata` PASS, `ai_context_check` PASS (11/11), `lint_translation_writes` PASS, `schema_drift_checker` PASS, `py_compile` all evidence scripts, `bash -n` matrix script |
| Manifest digests | all 21 pre-existing manifests verify 185/185 after this item (zero re-pins, R6); this item's `evidence/MANIFEST.json` pins its own artefacts |
| Shared-file changes | **0** — no hooks, matrix, tests, service, JS, or registry edit ⇒ no `?v=` bump, no header change, no re-pins |
