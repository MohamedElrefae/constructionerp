# Scope Descriptor — bilingual-uom-phase1-population

**Work item:** `bilingual-uom-phase1-population`
**Branch:** `develop`
**Base commit:** `aecef45`
**Date:** 2026-10-05
**Status:** `COMPLETE` — 253 rows classified; owner decisions received (values approved
15/15 effective, F4 prune to 15, F1 bundle, F5 bilingual fixture); proposal v2 bound at
sha256 `18a16a953ebbaad704acc7982ed96de71808235c7fc5b258b6825fbd80598bbf`; dry-run /
bilingual `uom.json` edit / apply / post-verify all PASS; gates green (matrix 21/21,
reconciler 19/19, 5 lints). Full results in §8; evidence under `evidence/`.
**Authority:** Owner's in-session choice after Tier 5E (`aecef45`) closed: "5F: UOM fixture
audit (Recommended)" — fixture inventory audit, extraction, governed translation review,
read-only until the population proposal is approved
**Scope:** Inventory and classify every UOM row on `v16.localhost` under deterministic rules
(vendor fixture / app fixture / in-use / disabled), freeze a Phase-1 allowlist (app
construction fixtures + every non-fixture unit referenced by live Items or BOQs), draft the
governed Arabic proposal for that allowlist, and — only after owner approval — run the
standard dry-run → apply → verify cycle for Phase 1. The remaining 234 enabled unused
units are audited and disclosed, **not** populated (separate future proposal).

---

## 1. The gap this closes

UOM is a fully *enabled* bilingual surface with zero *data*:

- Registered in `bilingual_registry.json` (`doctypes.UOM` active: `uom_name` /
  `uom_name_ar` / `uom_name_ar_norm`, code field `common_code`, search on).
- Schema landed with wave2a (`patches/v9_4` added `uom_name_ar` + norm; wave2a pilot tests
  cover `("UOM", "uom_name_ar")` enablement).
- Policy hooks live: `enforce_bilingual_arabic_policy` + narrative sanitizer
  (`UOM.description` limit 1) on UOM `validate` (`hooks.py` doc_events).
- Desk link dispatch supports `search_link("UOM")` (tested).
- **Population: 0 / 253 rows have `uom_name_ar`.** The Arabic Translation doctype carries
  zero Arabic rows for units too. Every UOM picker, BOQ line, item, and print renders
  English-only units.

Wave2a enabled the surface; this tier (and its phases) fills it — starting with the units
that actually matter on a construction site.

## 2. Verified current state (probed 2026-10-05, base `aecef45`)

| Fact | Value |
|---|---|
| UOM rows | **253** (owner's "251" = non-`_Test` count: 253 − 2 fixtures); enabled 241, disabled 12 |
| Arabic surface | `uom_name_ar` populated **0/253**; Translation doctype Arabic unit rows **0** |
| Vendor fixtures | `_Test UOM`, `_Test UOM 1` (name prefix rule) — referenced by 22 Items (fixture Items), both enabled |
| App fixtures | `construction/fixtures/uom.json` ships **12**: M3, M2, M, TON, KG, PCS, LS, DAY, HR, BAG, LTR, SET — all present on site; **JSON carries no `uom_name_ar` key and no `enabled` key** |
| **F1 (new)** | **All 12 app fixtures are `enabled=0`** — they are the entire disabled set (241 enabled = 239 ERPNext seed + 2 `_Test`); fixture-sync path (data_import `import_doc`) materializes the absent `enabled` key as **0**, a plain `insert()` yields 1 (DocType default, DDL default `'1'`), and re-import **clobbers a manual enable back to 0 on every migrate** (probed A/B/C, rollback + residue-cleaned — see §2.1) |
| **F2 (new)** | Link search mirrors `enabled=1` (contract-tested at `test_bilingual_desk_link_dispatch.py:245`): **3/15** Phase-1 rows visible in the picker (Nos/Tonne/Box); the 12 fixture units (M3, KG, …) are **invisible** — live pickers use ERPNext seed names (e.g. `Cubic Meter`) instead |
| **F4 (new)** | BOQ usage provenance: all usage rows are drafts (`docstatus=0`); `Pint (US)` = 9/11 rows under `_Test Security Audit Project` + 2/11 `VO QA Project`; `Acre` = single row under an Arabic "test project"; `Nos`/`Box` rows are non-test — **owner decision: prune both (F4), Phase-1 = 15** |
| **F5 (new, blocking → resolved)** | `bench migrate` runs `sync_fixtures()` → `import_doc(uom.json, force=True)` = **delete + reinsert of all 12 fixture rows on every migrate**; keys absent from the JSON are wiped (this is the precise root cause of F1 `enabled=0`, and `uom_name_ar` would be wiped the same way). **Owner decision: bilingual fixture** — `uom.json` gains `enabled:1` + `uom_name_ar` (§2.2) |
| **F6 (new, minor)** | `uom_code` in `uom.json` is a dead key — not an ERPNext v16 UOM meta field (meta fields: `uom_name, must_be_whole_number, enabled, symbol, common_code, description, category`) → fixture rows always land `uom_code=NULL`, matching site state; left untouched (out of scope, cosmetic) |
| Live usage — Items | 5 distinct `stock_uom`: `_Test UOM` (20), `Nos` (15), `Tonne` (5), `_Test UOM 1` (2), `Box` (1) → non-fixture in-use: **Nos, Tonne, Box** |
| Live usage — BOQs | 4 distinct `unit`: `Nos` (11 rows / 6 headers), `Pint (US)` (11 / 10 headers), `Box` (1), `Acre` (1) — **no `_Test` BOQ headers** → non-fixture in-use: **Pint (US), Acre, Nos, Box** |
| Classification result | vendor_fixture 2 · app_fixture 12 · in_use 5 · disabled-class 0 (F1: every disabled row is an app fixture, so the class never fires) · remainder **234** (enabled, unused, non-fixture → Phase 2+) = 253 |
| Metadata | `common_code` 3 rows, `symbol` 3, `description` 0; categories = ERPNext standard taxonomy (Density 34, Length 30, Volume 29, … , unset 25) |
| Norm | `uom_name_ar_norm` read-only; **server-derived on save** by `enforce_bilingual_arabic_policy` (client-passed norm discarded, same contract as 5C/5D) |
| Glossary | 47 approved terms, **zero unit terms** — unit translations have no glossary authority ⇒ R6 owner review required |
| Registry change needed | **none** (already active) — zero registry/triad edits this tier |
| Future drift | `cost_database_service` auto-inserts missing UOMs on demand (app code path, disclosed) |

### 2.1 F1 probe record (write-probes, rollback + residue-verified)

Insert-path probes establish mechanism (each `import_doc` call commits internally):

| Path | Result |
|---|---|
| A: `frappe.get_doc({...}).insert()` | `enabled=1` (DocType default honored) |
| B: `import_doc(fixture_json)` new row | `enabled=0` — fixture path materializes absent key as 0 (→ fresh installs land disabled) |
| C: flip `M3`→1, re-import real `uom.json` | `M3`→**0** — fixture sync clobbers manual enable on every migrate |

Consequence for the owner decision: a **site-only enable is temporary** (reverted by next
`bench migrate`); durable enablement requires adding `"enabled": 1` to `uom.json` (app
code change; `uom.json` is **not** pinned by any manifest — verified by grep across
`docs/ai/work-items/*/evidence/MANIFEST.json`).

**A1 probe disclosure:** probe B's committed `PROBE-B-FIXTURE` row was removed with
`frappe.db.delete(...)` + `commit` (plain `delete_doc` enqueues a Redis job and queue
11000 was down). Post-cleanup verified: 0 rows `name LIKE 'PROBE%'`, 253 total, `M3`/`M2`
back at `enabled=0`. Probe A never committed (implicit rollback). **A1b:** probe `PROBE-H`
(pre-restart stepwise probe) crashed before its cleanup ran, leaving 1 committed row
(`uom_name_ar='قيمة'`, total 254) — removed 2026-10-05 before the frozen export re-run;
verified `total=253`, zero `PROBE%` residue, `M3 enabled=0`. Net site state unchanged by
all probes.

### 2.2 F5 fixture-sync mechanism (probed with commit suppression + rollback)

`frappe.utils.fixtures.sync_fixtures()` runs on every `bench migrate` (migrate.py:165,
`skip_fixtures` false by default) and imports every `construction/fixtures/*.json` with
`force=True`. For UOM the semantics (established by stepwise instrumentation of
`Document.insert`, PROBE-K full round-trip):

| Behavior | Effect on our plan |
|---|---|
| existing row → **delete + reinsert** from JSON dict | not an update — JSON is source of truth per migrate |
| keys absent from JSON → never inserted | `enabled` absent → materialized **0** (F1 root cause: `_set_defaults` early-returns under `in_import`); **`uom_name_ar` absent → wiped to NULL** |
| `enabled: 1` present → persists | F1 fix works |
| `uom_name_ar` present → persists; validate hook runs during import → **norm re-derived server-side** | F5 fix works; norm never stored in JSON (contract intact) |
| `_sync_autoname_field` forces `uom_name := name` | pre-existing: fixture's `uom_name` label (`Cubic Meter`) never reaches DB under sync — cosmetic drift, out of scope |
| `uom_code` dropped (dead key, F6) | pre-existing, out of scope |

Durable bilingual fixtures therefore require `enabled` **and** `uom_name_ar` in
`uom.json` (owner-approved); the 3 non-fixture rows (`Nos`, `Tonne`, `Box`) are pure DB
rows and are durable regardless.

## 3. Decisions

### R1 — deterministic classification, asserted against a frozen allowlist

Every row gets exactly one class (first match wins):

1. `vendor_fixture` — `name` starts with `_Test` → **never translated** (5D fixture rule,
   now covering the 2 rows *even though live Items reference them*).
2. `app_fixture` — `name` ∈ the 12 names parsed from `construction/fixtures/uom.json`.
3. `in_use` — referenced by live `Item.stock_uom` or `BOQ Item.unit` (any owner), not 1/2.
4. `disabled` — `enabled = 0`, not already classed → excluded from every phase. **Amended
   by F1:** the class is currently empty because the only disabled rows on the site *are*
   the 12 app fixtures (classed in 2 first). Disabled rows outside the app fixture set
   would still be excluded; the app fixtures stay in Phase 1 as construction-critical
   data regardless of their (defective) enabled state — visibility is an owner decision
   (§8 question), not a classification input.

The export script derives in-use/app classes **from live joins + the fixture file**,
subtracts the owner's F4 prune, and asserts the derived Phase-1 set equals a frozen literal
list in the script (`{M3, M2, M, TON, KG, PCS, LS, DAY, HR, BAG, LTR, SET, Nos, Tonne,
Box}` = **15**; `PRUNED_BY_OWNER = {Pint (US), Acre}`) — drift fails the gate, exactly like
the wave allowlists. Run result: `inventory-export.log` → `INVENTORY RESULT: PASS`
(PHASE1_FROZEN_MATCH yes, PRUNED_BY_OWNER printed, PRE_STATE 0, DISABLED_IN_USE none,
F1/F2 findings printed, 253 ROW lines).

### R2 — phased population; Phase 1 only this cycle

- **Phase 1 (approved, 15 rows)** — the 12 construction-standard units + the 3 live
  non-fixture units (`Nos`, `Tonne`, `Box`).
- **F4-pruned (2 rows):** `Pint (US)`, `Acre` — stay classified `in_use`, untranslated,
  Phase 2+ candidates.
- **Remainder (234 enabled unused vendor-standard units)**: audited, classified, counts
  disclosed — **no values drafted, no writes**. A future proposal decides whether exotic
  categories (Magnetic Induction, Electrical Charge, …) are ever worth translating.
- The 12 disabled app fixtures translate under Phase 1 as data **and** become selectable
  via the approved F1/F5 bundle (`uom.json` `enabled:1` + one-time site enable).

### R3 — read-only until explicit approval; standard apply mechanics *(amended by owner decisions F1+F5)*

Export, classification, and proposal are read-only. After approval (received):
dry-run (0 writes, sha gate) → **bilingual `uom.json` edit** (`enabled:1` + `uom_name_ar`
on 12 rows — owner-authorized app-file change, sha recorded) → apply via plain `doc.save()`
on `UOM` for the 15 DB rows (`uom_name_ar` set, `enabled=1` on the 12 fixture rows; norm
derived server-side; no `Translation` doctype; no vendor file) → post-verify incl. a
fixture durability round-trip proof (commit-suppressed `import_doc` + rollback).
Fail-closed rollback on any apply error.

### R4 — privacy R4 (5C/5D model) *(amended by F5)*

Proposal values, dry-run/apply/rollback logs live under
`sites/v16.localhost/private/uom-phase1-population/`. Committed evidence carries counts,
classifications (English identities), verdicts, and sha256 digests only — **except**
`construction/fixtures/uom.json`, which now carries the 12 approved `uom_name_ar` values:
owner-authorized (F5 bilingual fixture, recorded in `owner-approval.md`); this is product
data, not evidence, and the same values are readable on the site by the app contract.

### R5 — vendor boundary, triad, registry untouched

Zero files under `apps/frappe` / `apps/erpnext`; `bilingual_service.py` +
`searchable_dropdown/api/search.py` + `bilingual_registry.json` byte-identical to `aecef45`
(call-only; registry needs no edit — UOM entry already active).

### R6 — translation values are proposals under owner review

The glossary has **no unit terms**, so every Arabic value is AI-proposed, Egyptian
construction usage, with rationale/alternates where ambiguous (e.g. `LS` lump sum,
`PCS` vs `Nos` distinctness). The owner's Round-1 review approved the 15-row effective set
(16/17 on v1, prune mooted the single revise); edits are applied to the proposal, not the
repo.

### R7 — in-use joins are broad, fixtures stay dark

In-use = any reference from `Item.stock_uom` **or** `BOQ Item.unit` (headers are real site
BOQs, none `_Test`). The 2 vendor fixtures stay untranslated despite 22 Item references —
their referencing Items are fixtures too, and the fixture rule is absolute (5D precedent).

## 4. Invariants preserved

- **Vendor boundary:** no file under `apps/frappe` / `apps/erpnext` changes.
- **D5 triad / registry:** unchanged (call-only); no hooks, patch, or test-matrix change.
- **Read-only pre-approval:** classification phase touches no document.
- **Norm contract:** server-derived only (client-passed norm discarded on save).
- **Fixture JSON:** *amended by owner F5 decision* — `uom.json` gains `enabled: 1` +
  `uom_name_ar` on its 12 rows (bilingual fixture); `uom_name_ar_norm` deliberately NOT
  stored (server-derived on every import by the validate hook — contract intact); no other
  key added or removed (`uom_code` dead key left as-is per F6).
- **Fail-closed:** classification mismatch vs frozen allowlist aborts the export; apply
  aborts on any validation error with rollback.
- **Matrix:** module list (21) unchanged; tests grow only inside stage4/stage7-style modules
  if touched (expected: zero test-module edits — UOM coverage rides existing wave2a +
  registry tests).

## 5. Tests and evidence gates

1. `inventory-export.log` — full 253-row classification, frozen 15-row allowlist assertion
   + F4 prune, pre-state (0 populated), F1/F2 findings, usage attribution.
2. `owner-approval.md` — owner's decisions bound to proposal v2 sha (values / F4 / F1 / F5)
   + `review-ai-a2.md` (redacted verdicts).
3. Post-approval: `dry-run.log` (0 writes, v2 sha gate), `apply.log` (15/15 plain saves +
   12 enables + `uom.json` sha), `post-import-verification.log` (15 populated,
   norm-consistent, exceptions empty, fixture durability round-trip proof, visibility
   15/15).
4. Canonical matrix (21 modules), ADR reconciler 19/19, lints (scope_metadata,
   ai_context_check, translation_writes, schema_drift, py_compile, bash -n).
5. `MANIFEST.json` + digest verification; zero re-pins expected (`uom.json` not pinned by
   any manifest — verified).

## 6. Out of scope

- **Department (274 rows)** and any other doctype — separate tier.
- **Phase 2+ population** of the 234 unused enabled units + the F4-pruned `Pint (US)` /
  `Acre` (future proposal; audit data here).
- **F6 cosmetic drift** (`uom_code` dead key, fixture `uom_name` label never syncing) —
  disclosed, not fixed.
- **`Translation` doctype writes**, registry/glossary edits (adding unit terms to the
  glossary is a separate governance action, flagged in §8 if owner wants it).
- **Production:** `production_mutation_authorized: false` (test site only).

## 7. Evidence causal order

export/inventory (read-only) → classification vs frozen allowlist → proposal v1 (17 values,
private) → Round-1 review (16 approve / 1 revise) → owner decisions (F4 prune → proposal v2
15 rows, sha-bound; F1 bundle; F5 bilingual fixture) → dry-run (0 writes, v2 sha gate) →
bilingual `uom.json` edit → apply (`doc.save()` ×15 + site enables) → post-verify (incl.
durability round-trip proof) → matrix + reconciler + lints → capture logs (`2>&1`) →
`git add -f` the `.log` → SHA-256 digests → `MANIFEST.json` → commit.

## 8. Results (recorded on completion)

All executed on `v16.localhost` (test site only; production untouched), base `aecef45`.

| Step | Result |
|---|---|
| Export / inventory | `inventory-export.log` → **PASS** — 253 rows classified (2 vendor / 12 app fixtures / 5 in-use → F4-prune 2 → Phase 1 = **15** / 234 remainder), `PHASE1_FROZEN_MATCH yes`, `PRUNED_BY_OWNER` printed, `PRE_STATE 0`, `DISABLED_IN_USE none`, F1/F2 findings printed. |
| Proposal v2 (15 rows) | sha256 `18a16a953ebbaad704acc7982ed96de71808235c7fc5b258b6825fbd80598bbf` bound in `owner-approval.md`; v1 preserved (`00cff4cd…4b30`, rows 1–15 byte-identical); Round-1 review 16/17 approve (1 revise mooted by F4 prune) → effective **15/15 approve**. |
| Owner decisions | **F4** prune `Pint (US)` + `Acre` → 15 rows; **F1** bundle `uom.json` `"enabled": 1` fix; **F5** bilingual fixture (`uom_name_ar` in `uom.json`). Recorded in `owner-approval.md`. |
| Dry-run | `dry-run.log` → **PASS** — 15/15 rows validated, 12 enables planned, `POPULATED_NOW 0`, approved sha matched, **`WRITES_PERFORMED: 0`**; pre-edit `uom.json` sha `aaf57840…904a`. |
| `uom.json` bilingual edit | 12 rows gained `"enabled": 1` + `"uom_name_ar"` (values byte-exact from proposal; no `_norm` key); post-edit sha256 `d6e27a01483c841dccdb090277aa9c59459b270d52d40661bf9934d9e4c33ad2`. |
| Apply | `apply.log` → **PASS** — `SUMMARY written=15 skipped=0 failed=0 fixture_enabled=12`; fixture-file gate `consistent_with_proposal=yes`; every save derived `_norm` server-side, identity unchanged; no `Translation` doctype writes. |
| Post-verify | `post-import-verification.log` → **PASS** — `15 populated, norm_consistent=15, identity_unchanged=15`; site Arabic total exactly 15 (missing 0 / extra 0); exceptions 0 (Pint/Acre/vendor/234 remainder/PROBE residue all empty); `fixtures_enabled=12/12`, site disabled `0`; **visibility 15/15** (F2 closed); **durability proof PASS** (commit-suppressed fixture sync round-trip preserves Arabic + enabled + re-derived norm, rollback restored); frozen prior surfaces (accounts 81, items 8, customers 1, suppliers 0, cost_centers 3, warehouses 6, projects 5, groups 6/5/8/4, Company empty) and `uom_total=253`. **R4b (amendment V1):** verify attempt 1 aborted on a read-only frozen-surfaces query using a wrong Supplier column (`supplier_name_ar` → `supplier_name_in_arabic`) after all other checks had passed; corrected and rerun end-to-end, zero writes at any point; log holds the final passing run. |
| Gates | `py_compile` 4 scripts OK; `lint_scope_metadata` PASS (11 checks); `ai_context_check` 0; `lint_translation_writes` PASS; `schema_drift` 0; `bash -n` OK; ADR reconciler **19/19** (`reconciliation.log`); canonical matrix **21/21 modules OK, 264 tests, 0 failures** (`regression-matrix.log`; redis 11000/13000 started → run → torn down). |
| Open items flagged to owner | (a) glossary still has **no unit terms** — adding them is a separate governance action (R6); (b) **F6** cosmetic drift (`uom_code` dead key, fixture `uom_name` label never syncing) disclosed, not fixed; (c) Phase 2+ (234 remainder + 2 pruned) awaits a future proposal. |
