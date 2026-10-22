# Scope Descriptor — bilingual-wave2-group-masters-population

**Work item:** `bilingual-wave2-group-masters-population`
**Branch:** `develop`
**Base commit:** `3fa285a`
**Date:** 2026-10-05
**Status:** `COMPLETE` (2026-10-05) — all 23 in-scope wave-2 group master rows (Item Group,
Customer Group, Supplier Group, Territory) populated on `v16.localhost` under approved proposal
`08dba90a…f6ea47e`; all evidence gates green, zero shared-file changes
**Authority:** Plan Tier 5D — owner's chosen next step after Tier 5C (`3fa285a`) closed the
wave-1 gate (all six wave-1 masters populated on `v16.localhost`)
**Scope:** Populate `Item Group.item_group_name_ar`, `Customer Group.customer_group_name_ar`,
`Supplier Group.supplier_group_name_ar`, `Territory.territory_name_ar` for the non-fixture rows
on `v16.localhost` through the same D4/D5-shaped governed cycle as 5B/5C — export → independent
proposal → independent AI-A2 review → **owner approval** → dry-run → import → post-import
verification — with zero app-code changes, zero vendor edits, and a committed
completeness/exception report.

---

## 1. The gap this closes

Wave 2a (`bilingual-wave2a-classification-masters`) delivered **schema + display readiness**
for the classification masters but deliberately left out of scope:

- "Arabic value population or backfill of business data." (`bilingual-wave2a-classification-masters/SCOPE.md:134`)

These four doctypes are exactly that deferred row:

- registry entries `state: active` with `arabic_field` + `norm_field` declared
  (`bilingual_registry.json`);
- `validate` policy hooks registered in `construction/hooks.py` (`enforce_bilingual_arabic_policy`
  for all four);
- no separate code column (wave2a decision) — identity is the label field + its `_norm`.

Completing them finishes the **master-data taxonomy** for the site: group/territory picklists,
group filters, and bilingual search across all four trees return Arabic labels instead of
English-only text.

## 2. Verified current state (probed 2026-10-05, base `3fa285a`)

| Doctype | Total | In-scope (non-fixture) | Fixture (`_Test*`) | Pre-existing Arabic |
|---|---|---|---|---|
| Item Group | 19 | **6** — `All Item Groups`, `Consumable`, `Products`, `Raw Material`, `Services`, `Sub Assemblies` | 13 | 0 |
| Customer Group | 7 | **5** — `All Customer Groups`, `Commercial`, `Government`, `Individual`, `Non Profit` | 2 | 0 |
| Supplier Group | 9 | **8** — `All Supplier Groups`, `Distributor`, `Electrical`, `Hardware`, `Local`, `Pharmaceutical`, `Raw Material`, `Services` | 1 | 0 |
| Territory | 9 | **4** — `All Territories`, `Egypt`, `India`, `Rest Of The World` | 5 | 0 |
| **Total** | **44** | **23** | **21** | **0** |

Classification difference vs 5C (disclosed): these four doctypes are **global trees — no
`company` field**, so 5C's company-aware rule does not apply. The only classification axis is
the fixture rule (R1).

Live usage (context, not a classification axis): real items use `All Item Groups` (7) and
`Raw Material` (4); all 12 territory-bearing customers point at the fixture `_Test Territory`;
no real customer/supplier uses a non-fixture group. The non-fixture rows are nonetheless the
**standard ERPNext taxonomy** exposed in every live picklist — they are the labels real users
see, independent of current transactional usage.

## 3. Decisions

### R1 — in-scope set = non-fixture rows of the four trees; everything else is a documented exception

The export script enumerates every Item Group, Customer Group, Supplier Group and Territory
row, applies the fixture rule (**name or label starts with `_Test`** — same family as every
prior tier), and freezes the in-scope list (expected 6+5+8+4 = 23) before any proposal work.
Root nodes (`All *`) are included, consistent with `All Warehouses - E` in 5C. The in-scope
list must reach **100% approved values or documented exceptions**.

### R2 — D4/D5-shaped governed cycle, with owner approval as the hard gate

`export → independent proposal → independent AI-A2 review → owner approval → dry-run → import →
post-import verification` — identical contract to 5B/5C: proposal authored in-session, review
by distinct subagent session(s) returning per-row verdicts, every final value approved by a
non-author session, owner approval bound to the exact proposal sha256, nothing written before
the gate.

### R3 — write path: standard document save through the existing validate hook

`frappe.get_doc(...); doc.<arabic field> = value; doc.save()` as Administrator. The registered
`enforce_bilingual_arabic_policy` hook guarantees bidi rejection + fresh server-authoritative
`_norm`. **No setter, no token, no hook change, no app-code change.**

The 5C R3a fallback (`flags.ignore_mandatory` retry on a freshly loaded copy, disclosed in
5C SCOPE) is carried forward in the apply script as a safety net only: ERPNext marks all four
`parent_*` fields **optional** (`reqd` unset), so no mandatory-parent quirk is expected. If the
retry triggers anyway, it is disclosed in `apply.log` and in this item's results exactly as 5C
did.

**R3b (disclosed mid-cycle amendment, proved by fail-closed first attempt):** ERPNext forces
**empty-parent roots to reparent under themselves** on save — `Item Group.validate()` hardcodes
the operating-company root name guarded only by `frappe.in_test`
(`erpnext/setup/doctype/item_group/item_group.py:35`), and `Customer Group` / `Supplier Group` /
`Territory.validate()` each call `get_root_of(<doctype>)`, which returns the root's own name.
The resulting self-parent makes `NestedSet` `validate_loop` throw
`NestedSetRecursionError: Item cannot be added to its own descendants`, aborting and rolling
back the whole apply (first attempt, zero writes kept). Root rows (4 of 23) are therefore saved
under a **narrow, disclosed vendor-workaround**: `frappe.in_test = True` around the Item Group
root save (ERPNext's own test exemption) and a scoped `get_root_of` patch on the three module
namespaces returning `None` around their root saves (restore in `finally`) — each prevents only
the forced self-parent; `enforce_bilingual_arabic_policy` (bidi gate + server-derived `_norm`)
and every other validate/on_update check still run, parents stay exactly as shipped
(`''`/`NULL`), and no hierarchy moves. Verified empirically pre-apply in a rolled-back
transaction for all four roots (value stored, hook-derived norm, parent unchanged). Non-root
rows (19 of 23) keep strict plain `save()`. Evidence: `apply.log` `R3B_ROOT_SAVE` lines; any
R3A trigger would be logged as before.

### R4 — data privacy: values private, hashes committed

Full values and the rollback export live under
`sites/v16.localhost/private/wave2-group-masters-population/`. Committed evidence carries
counts + SHA-256 digests only (5B/5C pattern).

### R5 — completeness = 100% of in-scope rows approved, exceptions enumerated

Post-import verification emits per-doctype in-scope/approved/populated counts (6/5/8/4), the
full exception list (21 fixtures), norm-consistency (`<field>_norm == normalize_arabic(<field>)`
for every written row), bidi/byte sanity, and fixture-row untouched proof. Any in-scope row not
populated fails the item.

### R6 — evidence pipeline, no shared-file edits, therefore zero manifest re-pins

Only new files under this work-item directory plus private site data. Gates: export log,
proposal + review records, owner-approval record, dry-run log, apply log, post-import
verification log, matrix rerun (21/258), reconciler 19/19, lints, `MANIFEST.json`.
No shared living file changes ⇒ **no other manifest needs re-pinning** (baseline: 23 manifests /
211 digests after 5C).

### R7 — no display/config changes

`identity_section` stays `false` for the four; no `doctype_js`, no `?v=` bump, no registry edit,
no Account/Company writes, no translation-catalog work.

## 4. Invariants preserved

- **Vendor boundary:** zero files under `apps/frappe` / `apps/erpnext` change.
- **D5 triad / registry:** `bilingual_service.py`, `searchable_dropdown/api/search.py`,
  `bilingual_registry.json`, `bilingual_registry.py` untouched (call-only).
- **Account surface:** no `account_name_ar` write; Stage-4 bundle/manifest untouched.
- **Mutation boundary:** exactly the in-scope four-tree rows' Arabic field + derived `_norm`;
  rollback export captured before the first write; identity/label/parent/hierarchy fields
  untouched.
- **No app-code changes:** no service, hook, patch, test, JS, or registry edit ⇒ no `?v=` bump,
  no matrix-header change, no manifest re-pins.
- **Fixture protection:** name/label-based allowlist from the R1 export, never a broad
  "all rows" write.

## 5. Tests and evidence gates

No new test modules (site data state verified by evidence scripts; behavioral surface already
covered by the wave-2a test module in the matrix). Evidence gates:

1. `inventory-export.log` — live row inventory with fixture classification (R1 lists).
2. `proposal.json` (private) + committed sha — every in-scope row with confidence, provenance.
3. `review-ai-a2.md` — independent per-row verdicts from distinct review session(s) (R2).
4. `owner-approval.md` — approval of the exact proposal sha.
5. `dry-run.log` — exact before/after for the approved rows, zero writes (asserted).
6. `apply.log` — import execution; per-row success; counts.
7. `post-import-verification.log` — 100% in-scope populated, norm consistency, exception
   report, fixture-untouched proof, rollback-export sha.
8. `regression-matrix.log` — 21/258 all OK.
9. `reconciliation.log` — reconciler 19/19.
10. Lints: `lint_scope_metadata`, `ai_context_check`, `lint_translation_writes`,
    `schema_drift_checker`, `py_compile`, `bash -n`.

Causal order (mandatory): final verification run → capture log (`2>&1`) → `git add -f` the
`.log` → SHA-256 digests → `evidence/MANIFEST.json` → commit.

## 6. Out of scope

- **Stage 8 / true production:** `production_mutation_authorized: false`; owner-gated.
- **Fixture rows (21)** — permanent exceptions for this site.
- **UOM (251) / Department (274)** — large sets, fixture audit first; separate tier.
- **Report allowlist expansion (BS/P&L)** — Tier 5E candidate.
- **Wave-2b transactional documents** — deferred by wave2a/wave2b SCOPE.
- **Hierarchy semantics:** no parent/child moves, no renames, no code-column writes — data
  population only.
- **Display/identity-section config, doctype JS, print formats, translation catalogs.**

## 7. Evidence causal order

export/inventory → proposal → independent review → **owner approval** → dry-run → apply →
post-import verification → matrix + reconciler + lints → capture logs (`2>&1`) → `git add -f`
the `.log` files → SHA-256 digests → `evidence/MANIFEST.json` → commit.

## 8. Results (recorded on completion)

| Gate | Result |
|---|---|
| Inventory export (R1) | PASS — rule-derived in-scope matches frozen allowlist 6/5/8/4 = 23; 21 fixtures classified; pre-state of all four trees empty; `PARENT_FIELDS_OPTIONAL yes` (R3a dormant as expected) |
| Proposal → review → approval (R2) | proposal v1 `08dba90a…f6ea47e` → review round 1 (`ses_ef6f18e07ffeVf22gghj4KWEwt`, fresh non-author session, **23/23 approve, overall approve** — no revision round needed; 7 rows byte-match the site translation catalog; glossary scan 47/47 terms, 0 hits; cross-tree anchors verified). Owner approval of the exact v1 sha recorded in `evidence/owner-approval.md` (no amendments; 8 catalog parity options declined) |
| Dry-run (zero writes) | PASS — `23/23 rows validated; approved sha matched; zero writes` |
| Apply attempt 1 | **FAIL-CLOSED, rolled back** — first root row aborted with `NestedSetRecursionError: Item cannot be added to its own descendants` (vendor forces empty-parent roots to self-parent); zero writes kept. Led to disclosed R3b (SCOPE §3) |
| Apply (after R3b) | PASS — 23/23 written, 0 skipped/failed; 19 plain `doc.save()` + 4 root saves via R3b workaround (`R3B_ROOT_SAVE` ×4: `frappe.in_test` guard for Item Group, scoped `get_root_of` patch → None for the other three); per-row `identity=unchanged`; parents exactly as shipped; norms server-derived. Rollback export = `dry-run.json` (before-values all empty, sha `2e5e3c7a…04cb01`); `apply.json` sha `dac85751…26d1cfc` |
| Post-import verification | PASS — `in_scope=23 populated=23 norm_consistent=23 identity_unchanged=23 exceptions=0 fixtures_untouched=21`; completeness 6/6 + 5/5 + 8/8 + 4/4; norm-key search 23/23; tree totals unchanged (19/7/9/9); frozen prior surfaces: Account Arabic 81, wave-1 trio 3/6/5, items 8, customers 1, suppliers 0, `Company.company_name_ar` empty |
| Regression matrix | 21 modules / 258 tests, all OK (unchanged, as R6 predicted) |
| ADR↔evidence reconciler | 19/19 PASS |
| Lints | `lint_scope_metadata` PASS, `ai_context_check` PASS (11/11), `lint_translation_writes` PASS, `schema_drift_checker` PASS, `py_compile` all evidence scripts, `bash -n` matrix script |
| Manifest digests | all 23 pre-existing manifests verify unchanged after this item (zero re-pins, R6); this item's `evidence/MANIFEST.json` pins its own artefacts |
| Shared-file changes | **0** — no hooks, matrix, tests, service, JS, or registry edit ⇒ no `?v=` bump, no header change, no re-pins |

**Disclosed mid-cycle amendments:** R3a (5C precedent, carried, never triggered — parents
proved optional) and **R3b** (proved fail-closed on apply attempt 1, workaround scoped to the
4 root rows only, vendor workarounds documented in §3 with empirical pre-apply proof).