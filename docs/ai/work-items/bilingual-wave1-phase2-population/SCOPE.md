# Scope Descriptor — bilingual-wave1-phase2-population

**Work item:** `bilingual-wave1-phase2-population`
**Branch:** `develop`
**Base commit:** `66acc8e`
**Date:** 2026-10-05
**Status:** `COMPLETE` (2026-10-05) — all 13 in-scope phase-2 rows (Cost Center, Warehouse,
Project) populated on `v16.localhost` under approved proposal `e68ef0c6…108557`; all evidence
gates green, zero shared-file changes
**Authority:** Plan Tier 5C — remainder of Plan §11 Stage 5 ("Wave 1 masters (Item, Customer,
Supplier, Cost Center, Warehouse, Project)"), owner session choice A after Tier 5B (`66acc8e`)
closed the first three members
**Scope:** Populate `Cost Center.cost_center_name_ar`, `Warehouse.warehouse_name_ar`,
`Project.project_name_ar` for the non-fixture rows on `v16.localhost` through the same
D4/D5-shaped governed cycle as 5B — export → independent proposal → independent AI-A2 review →
**owner approval** → dry-run → import → post-import verification — with zero app-code changes,
zero vendor edits, and a committed completeness/exception report.

---

## 1. The gap this closes

Plan §11 Stage 5 defines the wave-1 gate as six masters: Item, Customer, Supplier,
**Cost Center, Warehouse, Project** — "Per-DocType UAT passes; 100% approved names or
documented exceptions; bilingual search works."

- Tier 5B (`66acc8e`) populated the first three members (8 Items + 1 Customer; Supplier = 0
  documented exception).
- The phase-2 trio has full **schema + display readiness** but **no data**:
  - registry entries `active` with `arabic_field` + `norm_field` declared
    (`bilingual_registry.json`);
  - `validate` policy hooks registered in `construction/hooks.py` (`enforce_bilingual_arabic_policy`
    for all three; `narrative_sanitizer` additionally for Project);
  - `test_bilingual_wave1_phase2_pilot` (9 tests) already in the canonical matrix;
  - wave2a SCOPE deliberately left "Arabic value population or backfill of business data"
    out of scope (`bilingual-wave2a-classification-masters/SCOPE.md:134`) — this item is
    exactly that deferred row.
- Live probe + R1 export (2026-10-05, base `66acc8e`): fixture classification is
  **company-aware**, because the site's only operating company is `Elrefae` (Egypt,
  created 2026-04-02) while **every other Company row was created 2026-06-10 in one
  ERPNext test-records batch** (Wind Power LLC, Best Test, Trial Balance Company,
  Test Quality Company, Child/Parent Group companies, all `_Test Company*`). Final
  classification: **in-scope 13 rows** (3 Cost Center + 5 Warehouse + 5 Project),
  36 vendor fixtures, 127 other-company rows; pre-state of all 13 in-scope rows empty;
  the only pre-existing Arabic value anywhere in the trio is the vendor-fixture row
  `CT-TEST-P2-WH-01 - TQC` (`مستودع إعادة التسمية`) — untouched by this item.

## 2. Verified current state (exported 2026-10-05, base `66acc8e`, `inventory-export.log` PASS)

| Doctype | Total | In-scope (Elrefae, non-fixture) | Vendor fixture | Other-company exception |
|---|---|---|---|---|
| Cost Center | 47 | **3** — `Elrefae - E`, `Main - E`, `Stage 8 Pilot - E` | 17 | 27 (20 demo companies) |
| Warehouse | 118 | **5** — `All Warehouses - E`, `Finished Goods - E`, `Goods In Transit - E`, `Stores - E`, `Work In Progress - E` | 13 (incl. the pre-populated `CT-TEST` row) | 100 (20 demo companies × 5-tree) |
| Project | 11 | **5** — `PROJ-0001` (`test project`), `PROJ-0002` (Arabic-identity row), `PROJ-0003` (`test ui`), `PROJ-0008` (`VO QA Project`), `PROJ-0009` (Arabic-identity row) | 6 (`_Test*` labels) | 0 |
| Registry | all three `state: active`, `identity_section: false` (stays false — R7) |
| Write governance | same wave-1 asymmetry as 5B: standard `doc.save()` admitted; the registered validate hook rejects bidi controls and derives `_norm` server-authoritatively on every save |
| Tests | `test_bilingual_wave1_phase2_pilot` (9) in the 21-module matrix (258 tests) |
| Site classification | `non-production test`, `production_mutation_authorized: false` — authorized test site only |
| Probe caveat | name-based fixture heuristic only; authoritative classification = the R1 export (may also flag hierarchy/company-suffix treatment for Warehouse names) |

## 3. Decisions

### R1 — in-scope set = non-fixture phase-2 rows; everything else is a documented exception

The export script enumerates every Cost Center, Warehouse and Project row, applies the
established fixture rules (`_Test*`, `Test*`, `TEST-%`, vendor scaffolding — same family as
`stage5-wave1-readiness-2026-09-20.md` L49-52), and freezes the in-scope list before any
proposal work. The in-scope list must reach **100% approved values or documented exceptions**.
The single already-Arabic Warehouse row is explicitly dispositioned (not silently skipped).

### R2 — D4/D5-shaped governed cycle, with owner approval as the hard gate

`export → independent proposal → independent AI-A2 review → owner approval → dry-run → import →
post-import verification` — identical contract to 5B: proposal authored in-session, review by
distinct subagent session(s) returning per-row verdicts, every final value approved by a
non-author session, owner approval bound to the exact proposal sha256, nothing written before
the gate.

### R3 — write path: standard document save through the existing validate hook

`frappe.get_doc(...); doc.<arabic field> = value; doc.save()` as Administrator. The registered
`enforce_bilingual_arabic_policy` hook (all three doctypes) guarantees bidi rejection + fresh
server-authoritative `_norm`. **No setter, no token, no hook change, no app-code change.**

**R3a (disclosed mid-cycle amendment):** ERPNext marks `Cost Center.parent_cost_center`
`reqd=1`, but root cost centres legitimately store NULL — the first apply attempt proved
plain `save()` raises `MandatoryError` on the root row and rolled back fail-closed. Root
nodes (empty vendor parent) are retried with frappe's documented
`doc.flags.ignore_mandatory = True` + `save()` on a freshly loaded copy (the flag is the
same mechanism `insert(ignore_mandatory=True)` sets; `_validate_mandatory` is the only
check skipped — validate hooks, ERPNext validations, and all other mandatory fields still
run). Non-root rows keep strict plain `save()`. Evidence: `apply.log` `R3A_ROOT_RETRY`
line; post-save assertions (identity unchanged, value stored, norm server-derived) pass
for the retried row like every other row.

### R4 — data privacy: values private, hashes committed

Full values and the rollback export live under
`sites/v16.localhost/private/wave1-phase2-population/`. Committed evidence carries counts +
SHA-256 digests only (5B pattern).

### R5 — completeness = 100% of in-scope rows approved, exceptions enumerated

Post-import verification emits per-doctype in-scope/approved/populated counts, the full
exception list, norm-consistency (`<field>_norm == normalize_arabic(<field>)` for every
written row), bidi/byte sanity, and the pre-existing-value disposition. Any in-scope row not
populated fails the item.

### R6 — evidence pipeline, no shared-file edits, therefore zero manifest re-pins

Only new files under this work-item directory plus private site data. Gates: export log,
proposal + review records, owner-approval record, dry-run log, apply log, post-import
verification log, matrix rerun (21/258), reconciler 19/19, lints, `MANIFEST.json`.
No shared living file changes ⇒ **no other manifest needs re-pinning.**

### R7 — no display/config changes

`identity_section` stays `false` for the trio; no `doctype_js`, no `?v=` bump, no registry
edit, no Account rows, no translation-catalog work.

## 4. Invariants preserved

- **Vendor boundary:** zero files under `apps/frappe` / `apps/erpnext` change.
- **D5 triad / registry:** `bilingual_service.py`, `searchable_dropdown/api/search.py`,
  `bilingual_registry.json`, `bilingual_registry.py` untouched (call-only).
- **Account surface:** no `account_name_ar` write; Stage-4 bundle/manifest untouched.
- **Mutation boundary:** exactly the in-scope trio rows' Arabic field + derived `_norm`;
  rollback export captured before the first write; identity/code/name/narrative fields untouched.
- **No app-code changes:** no service, hook, patch, test, JS, or registry edit ⇒ no `?v=` bump,
  no matrix-header change, no manifest re-pins.
- **Fixture protection:** name-based allowlist from the R1 export, never a broad "all rows" write.

## 5. Tests and evidence gates

No new test modules (site data state verified by evidence scripts; behavioral surface already
covered by `test_bilingual_wave1_phase2_pilot` in the matrix). Evidence gates:

1. `inventory-export.log` — live row inventory with fixture classification (R1 lists).
2. `proposal.json` (private) + committed sha — every in-scope row with confidence, provenance.
3. `review-ai-a2.md` — independent per-row verdicts from distinct review session(s) (R2).
4. `owner-approval.md` — approval of the exact proposal sha.
5. `dry-run.log` — exact before/after for the approved rows, zero writes (asserted).
6. `apply.log` — import execution; per-row success; counts.
7. `post-import-verification.log` — 100% in-scope populated, norm consistency, exception
   report, pre-existing-value disposition, rollback-export sha.
8. `regression-matrix.log` — 21/258 all OK.
9. `reconciliation.log` — reconciler 19/19.
10. Lints: `lint_scope_metadata`, `ai_context_check`, `lint_translation_writes`,
    `schema_drift_checker`, `py_compile`, `bash -n`.

Causal order (mandatory): final verification run → capture log (`2>&1`) → `git add -f` the
`.log` → SHA-256 digests → `evidence/MANIFEST.json` → commit.

## 6. Out of scope

- **Stage 8 / true production:** `production_mutation_authorized: false`; owner-gated.
- **Fixture rows** — permanent exceptions for this site.
- **Wave-2 classification masters** (Item Group, Customer Group, Supplier Group, Territory,
  UOM) — candidate Tier 5D, not this item.
- **Department / Employee / other registry doctypes** — separate rows.
- **Report allowlist expansion (BS/P&L)** — Tier candidate B, not this item.
- **Display/identity-section config, doctype JS, print formats, translation catalogs.**
- **Hierarchy semantics:** no parent/child moves, no renames, no code-column writes — data
  population only.

## 7. Evidence causal order

export/inventory → proposal → independent review → **owner approval** → dry-run → apply →
post-import verification → matrix + reconciler + lints → capture logs (`2>&1`) → `git add -f`
the `.log` files → SHA-256 digests → `evidence/MANIFEST.json` → commit.

## 8. Results (recorded on completion)

| Gate | Result |
|---|---|
| Inventory export (R1) | PASS — rule-derived in-scope (company-aware: Elrefae only) matches frozen allowlist 3/5/5; pre-state of all 13 rows empty; pre-existing Arabic only on fixture row `CT-TEST-P2-WH-01` (recorded, untouched) |
| Proposal → review → approval (R2) | proposal v1 `cc382f46…bad6` → review round 1 (`ses_ef70c00a…`, 11 approve / 2 revise) → v2 `e68ef0c6…108557` → review round 2 (`ses_ef7027ce…`, **13/13 approve, overall approve**); owner approval of the exact v2 sha recorded in `evidence/owner-approval.md` (no amendments; label-parity swaps declined) |
| Dry-run (zero writes) | PASS — `13/13 rows validated; approved sha matched; zero writes` |
| Apply | PASS — 13/13 written, 0 skipped/failed; per-row `identity=unchanged`; norms server-derived; transaction committed after two fail-closed rolled-back attempts disclosed under R3a (vendor mandatory-parent quirk on the root cost centre). Rollback export = `dry-run.json` (before-values all empty, sha `b158ca44…e7e29`) |
| Post-import verification | PASS — `in_scope=13 populated=13 norm_consistent=13 identity_unchanged=13 exceptions=0`; completeness 3/3 + 5/5 + 5/5; norm-key search 13/13; fixture pre-existing value intact; totals unchanged (47/118/11); Account Arabic still 81; `Company.company_name_ar` still empty |
| Regression matrix | 21 modules / 258 tests, all OK (unchanged, as R6 predicted) |
| ADR↔evidence reconciler | 19/19 PASS |
| Lints | `lint_scope_metadata` PASS, `ai_context_check` PASS (11/11), `lint_translation_writes` PASS, `schema_drift_checker` PASS, `py_compile` all evidence scripts, `bash -n` matrix script |
| Manifest digests | all 22 pre-existing manifests verify unchanged after this item (zero re-pins, R6); this item's `evidence/MANIFEST.json` pins its own artefacts |
| Shared-file changes | **0** — no hooks, matrix, tests, service, JS, or registry edit ⇒ no `?v=` bump, no header change, no re-pins |
