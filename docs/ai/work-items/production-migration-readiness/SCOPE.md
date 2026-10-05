# Scope Descriptor — production-migration-readiness

**Work item:** `production-migration-readiness`
**Branch:** `develop`
**Base commit:** `3e871f0` (post 5H `1f55a4a`, post 5I `3e871f0`)
**Date:** 2026-10-05
**Status:** `REVIEW_PENDING` — deliverables A–D built and validated; V1–V7 + governance-gate
runs all PASS on `v16.localhost` (§8); awaiting fresh non-author review + owner approval
**Authority:** Owner briefing `docs/ai/BRIEFING_PRODUCTION_MIGRATION_READINESS.md`
(Antigravity Engineering Lane, 2026-10-05) — bridge dev verification → production
readiness: readiness audit + idempotent fail-closed consolidated runner + post-flight
verifier. **`production_mutation_authorized` remains `false`**: this tier produces and
*validates the playbook on `v16.localhost`*; it never mutates production (no production
site exists on this bench).
**Scope:** Deliverables A–D under this work-item directory: `evidence/READINESS_AUDIT.md`,
the consolidated runner (`evidence/scripts/run_production_bilingual_migration.py`), the
post-migration verifier (`evidence/scripts/verify_production_bilingual_migration.py`), and
`evidence/MANIFEST.json`; plus the private consolidated values bundle under
`sites/v16.localhost/private/production-migration/` (R4). Strictly local commits with
transmitting hooks disabled (confidentiality policy).

---

## 1. Objective

Turn the verified 188-row bilingual master dataset (15 doctypes, all tiers closed through
5I `3e871f0`) into a single executable, idempotent, transaction-safe, fail-closed
production migration playbook with pre-flight (schema, encoding, backup, hooks, redis,
governance flag) and post-flight (counts, norms, trees, desk-search probes) gates.

## 2. Findings (readiness audit evidence; `READINESS_AUDIT.md` carries the full report)

| ID | Finding |
|---|---|
| **F-5J-1** | **Census variance vs briefing:** live census = **189 populated rows across 15 doctypes**; briefing claims 196/12 (its own table sums to 186). Reconciled: 188 **approved** rows + 1 pre-existing test fixture (`CT-TEST-P2-WH-01 - TQC`, frozen-excluded by 5C); briefing omits Customer (1), Task (1), Terms and Conditions (1). Runner covers **all 15** populated doctypes; audit documents the variance. |
| **F-5J-2** | **Value provenance:** 105 rows come from 7 private `proposal.json` bundles (wave1 9, wave1-phase2 13, wave2-groups 23, department 14, company 1, uom-phase1 15, uom-phase2 30 — last under `units`); Account (81) provenance = Stage-4 bundle (`private/stage4/account_catalog_*.json`, confirmed by 5B SCOPE “Tier 5B touches no Account row”); Task (1) + T&C (1) = master-tier applications predating the proposal pattern. Consolidation binds every row to its proposal sha (where one exists) or stage/tier evidence, and cross-checks proposal rows byte-for-byte against the verified site. |
| **F-5J-3** | **Encoding:** every `tab*` table is `utf8mb4` (collation check, 0 exceptions). |
| **F-5J-4** | **Hooks:** 22 registry doctypes bound to `enforce_bilingual_arabic_policy`; **Account** bound to the dedicated `enforce_account_arabic_policy` (+ report-cache bust on update/rename). All bindings registered in `construction/hooks.py`; no `Translation` doctype writes anywhere in the pipeline. |
| **F-5J-5** | **Backup gap:** `sites/v16.localhost/private/backups/` is **empty**; only stale archive `private/backup-archive-20260921/` (dumps of 2026-09-02) exists; no cron/hook automation. Runner pre-flight therefore **requires a fresh DB backup** in the site backup dir (age-gated, `--force` bypass disclosed) — validated by taking a real `bench backup` during this tier. |
| **F-5J-6** | **Root quirk map (all proven in closed tiers, all exercised in V5):** Item Group root → `frappe.in_test` scoped guard (5D, `item_group.py:35`); Customer Group / Supplier Group / Territory / Department roots → module-scoped `get_root_of → None` patch restored in `finally` (5D/5G); Department + Cost Center roots → `flags.ignore_mandatory` (5G/5C R3a); Warehouse / Task / Company + non-root Account → plain/governed save (Stage-4/5C/5H). Account roots → see F-5J-11. Unknown tree-root quirk ⇒ fail-closed abort, never guess. |
| **F-5J-11** | **Account roots are un-saveable through the vanilla doc path:** `Account.validate_root_details` throws `RootNotEditable` on ANY save of an existing root (`account.py` 211 def / 214 if / 215 throw — the same guard also enforces "root must be a group", which holds for all 5 roots), and root `parent_account` is reqd=1 (`_validate_mandatory` honors only `doc.flags`). Runner mechanism (V5-proven): scoped class-method no-op of *only* `validate_root_details` (restored in `finally`) + root-only inline governed save replicating `set_account_name_ar`'s exact token contract (`ct_governed_arabic_edit` doctype/name/old/new, identity check, hook-derived norm, Version) + `doc.flags.ignore_mandatory`. |
| **F-5J-12** | **NestedSet renumber hazard:** `update_nsm` (every `NestedSet.on_update`) reads stale `old_parent` as a move → `update_move_node` renumbers siblings (observed: one Account save renumbered 12 rows) and **always rewrites `old_parent`**. Runner sets `frappe.local.flags.ignore_update_nsm = True` for the apply (vendor precedent `chart_of_accounts.py:71`, `company.py:526`), restored in `finally` — honored only by `Account.on_update` + `Department.on_update`; for the other 8 trees the flag is inert, safety = `old_parent == parent` already + the runner's in-transaction tree assertion (4-tuple incl. `old_parent`, fail-closed → rollback). Account's flag also skips `NestedSet.validate_ledger` (disclosed). V5 rc=0: parent/`lft`/`rgt`/`old_parent` byte-identical over 188 saves. |
| **F-5J-7** | **Redis:** Company/Department-class saves touch the queue-connection getter (11000, F-5H-2) and `update_global_search → frappe.cache` (13000, matrix G1). Pre-flight pings both; production ops note: a worker must drain `global_search_queue` (backlog exists on test bench). |
| **F-5J-8** | **Governance flag:** `production_mutation_authorized: false` is a plan-§18 documented gate, not present in any `site_config.json`. Runner enforces it mechanically: sites other than the development allowlist are refused unless the target site's `site_config.json` explicitly sets `production_mutation_authorized: true`. |
| **F-5J-9** | **Search probe surface exists:** `bilingual_service.search_bilingual(doctype, txt)` (registry search, all 15 doctypes `search.enabled`) and `transaction_link_search.search_transactions(doctype, txt)` (allow-listed transactional links) — both used by the post-flight verifier for desk-link responsiveness probes. |
| **F-5J-10** | **NestedSet trees in scope:** **10 of 15** doctypes are trees (Account, Cost Center, Warehouse, Company, Item Group, Customer Group, Supplier Group, Territory, Department, Task). Approved root rows: Account 5 + Company 1 + Cost Center 1 + Warehouse 1 + Item Group 1 + Customer Group 1 + Supplier Group 1 + Territory 1 + Department 1 = **13** (matches V5 `ROOT_SAVES: 13`; Task row non-root; the excluded Warehouse fixture is an additional site root outside the bundle). Tree integrity = pre/post `parent`/`lft`/`rgt`/`old_parent` snapshot equality + structural validity. |

## 3. Deliverables & design decisions

1. **A — `evidence/READINESS_AUDIT.md`:** F-5J-1..10 with executed check outputs
   (schema fields present on all 15 doctypes, utf8mb4, hook bindings, backup state,
   redis, flag, roots, provenance).
2. **B — consolidated runner** `evidence/scripts/run_production_bilingual_migration.py`:
   - CLI: `--site`, `--values PATH` (default `sites/<site>/private/production-migration/consolidated_values.json`), `--dry-run`, `--force`, `--allow-sites` (default `v16.localhost`).
   - Pre-flight gates (fail-closed): site exists + allowlist/flag check (F-5J-8); values
     bundle present + sha matches committed `EXPECTED_VALUES_SHA256`; all 15 doctype
     schema fields present; utf8mb4; enforce hooks bound; fresh backup (F-5J-5, `--force`
     bypasses only the age gate); redis 11000+13000 reachable.
   - Apply: `frappe.db.begin()` → per-doctype topological order (Company → Account →
     Cost Center → Warehouse → Project → Item Group → Customer Group → Supplier Group →
     Territory → Department → Task → UOM → Item → Customer → Terms and Conditions) →
     per row: already-equal ⇒ **skip (idempotent)**; empty ⇒ `doc.save()` (norm derived
     server-side); unequal ⇒ **CONFLICT → fail-closed abort** (no overwrite without a new
     owner approval); roots route through the F-5J-6 workaround map (scoped, restored in
     `finally`, disclosed per row); `frappe.db.commit()` only after all rows succeed,
     any exception ⇒ `frappe.db.rollback()` + exit 1.
   - `--dry-run`: full classification (`WOULD_WRITE` / `ALREADY_APPLIED` / `CONFLICT` /
     `ABSENT_ON_TARGET`) with delta summary, **0 writes** (transaction always rolled
     back), no redis job side effects beyond read paths.
3. **C — post-flight verifier** `evidence/scripts/verify_production_bilingual_migration.py`:
   exact per-doctype approved counts; zero NULL/empty `*_norm` on approved rows; identity
   + frozen-field equality vs bundle; tree integrity (pre/post snapshot equality + NestedSet
   structure check); `search_bilingual` probes per doctype (English + Arabic hit, bounded
   latency reported); optional `--rollback-ref` comparison for the rehearsal mode.
4. **D — `evidence/MANIFEST.json`** pinning all artefacts with sha256 (R4: digests only).

## 4. Validation protocol on `v16.localhost` (production stays untouched)

| Run | Purpose |
|---|---|
| V1 consolidation | build private bundle; proposals byte-cross-checked vs site; sha recorded |
| V2 pre-flight + backup | take real `bench backup`; runner accepts it; tamper tests rejected — missing dir rc=1 (`v2-backup-missing.log`), stale dump rc=1 (`v2-backup-stale.log`) |
| V3 `--dry-run` | 188-row classification, **0 writes**, site census unchanged |
| V4 idempotent apply | on already-applied site: 188 × `ALREADY_APPLIED`, 0 writes, exit 0 (running twice ≡ once) |
| V5 full-save rollback rehearsal | transaction: real `doc.save()` for all 188 (roots via map) → in-transaction asserts → **rollback** → site census + tree snapshot byte-identical (proves the whole write path without permanent change) |
| V6a sha gate | tampered bundle copy ⇒ refused pre-flight rc=1 before any DB work (`v6a-sha-gate.log`) |
| V6b conflict fail-closed | site-side value diverged from the sha-pinned bundle ⇒ `CONFLICT` rc=2, zero writes, restored (`v6b-conflict.log`) |
| V6c would-write | 2 rows nulled ⇒ WOULD_WRITE=2 classification (`v6c-would-write.log`) |
| V7 post-flight verifier | counts/norms/trees/probes PASS on final state |

## 5. Invariants

1. Zero files under `apps/frappe` / `apps/erpnext` modified; D5 triad + registry
   byte-identical to `3e871f0` (call-only).
2. **No production mutation** (F-5J-8 guard); `v16.localhost` end state matches the V0
   baseline on every field V0 captured (V7: 576 cells + row sets + 189 norms +
   `parent`/`lft`/`rgt`; `old_parent` was added to capture after V0, so its equality is
   proven in-transaction by V5's 4-tuple assertion, rc=0; V5 rollback + V4 no-op prove the
   runner wrote nothing permanent); no schema/patch/hook/fixture/
   JS/`?v=` changes; committed diff = this work-item directory only.
3. **R4:** Arabic values only in `sites/v16.localhost/private/production-migration/`;
   committed evidence = counts, classifications, verdicts, sha256/sha16 digests.
4. Server-derived `*_norm` only (runner never writes norm fields directly); no
   `Translation` writes; no renames; no parent/lft/rgt mutations.
5. Idempotence: N runs ⇒ same end state, no errors, no duplicate writes (V4).
6. Fail-closed: conflict, missing schema field, stale backup, wrong site, unknown root
   quirk, or any exception ⇒ rollback + exit 1, zero partial writes.
7. **Confidentiality policy:** strictly local commit via
   `git -c core.hooksPath=/dev/null commit …`; no push, no CI, no remote anything.

## 6. Out of scope

- Flipping `production_mutation_authorized` (owner's later, separately-governed act).
- Actual production execution, backup automation (cron), worker deployment, remote repos.
- New Arabic translations (bundle = approved values only), glossary changes, customer/supplier
  rows (supplier Arabic 0), any doctype outside the 15.

## 7. Evidence causal order

audit checks (read-only) → consolidation V1 (private) → runner + verifier built →
V2–V7 validation runs (logs captured `2>&1`) → SCOPE §8 → fresh non-author review →
owner approval (sha-bound) → gates (4 lints + py_compile + bash -n + reconciler 19/19 +
matrix 21/21) → MANIFEST → `git add -f` → staged-digest + forbidden checks → local
commit proposal (hooks disabled).

## 8. Results

**Validation (all on `v16.localhost`, logs under `evidence/`):** V1 consolidation PASS
(188 rows byte-cross-checked, bundle sha256 `7390a0c87f8ebab1…`); V2 fresh backup taken
(67.8 MiB SQL dump); V3 dry-run PASS (188 ALREADY_APPLIED, **0 writes**); V4 idempotent apply
PASS (188 SKIPPED, commit no-op); **V5 rollback rehearsal PASS — 188/188 real doc.save()
including 13 root saves through the F-5J-6/11/12 map, in-transaction values+norms verified,
trees byte-identical, rollback → pre-state byte-identical (2.5 s)**; V6a sha-gate exit 1;
V6b CONFLICT exit 2 zero writes; V6c WOULD_WRITE=2; V4b apply path PASS (SAVED=2 via
governed root + plain, SKIPPED=186, FINAL 188); V7 verifier PASS (counts 188+fixture,
189 server-derived norms (188 approved + fixture), 576 frozen cells, 10/10 trees valid, 32 search probes p50 0.7 ms);
F-5J-8 non-allowlisted site refused (exit 1). End state after V7 matches V0 on every
V0-captured field (V7 PASS; V0 lacks `old_parent`, covered by V5's in-transaction 4-tuple
assertion, rc=0). Post-tier baseline snapshot (final format incl. `old_parent`):
sha16 `36f96d929629aa3e`, re-confirmed byte-identical after the final run set.

**Disclosure:** V6/V5 temporarily nulled 2 test rows via `db.set_value` (restored through the
production apply path; `modified` bumped on those 2 rows only); rehearsal enqueues added
metadata-only `global_search_queue` entries (no worker on bench ⇒ no effect, cannot write
post-rollback).

**Gates:** `lint_scope_metadata` PASS (19 DocTypes), `ai_context_check` PASS (11/11 checks),
`lint_translation_writes` PASS, `schema_drift_checker` PASS (each rc=0);
`py_compile` ×3 rc=0 with final script shas (`gates-compile-final.log`), `bash -n` rc=0
(`gates-bashn.log` — `run_bilingual_regression_matrix.sh`), ADR reconciler **19/19**,
regression matrix **21/21 modules, 264 tests, 0 failed** (first attempt aborted — bench redis
11000/13000 transiently unreachable, environmental; restarted, full re-run green). F-5J-13
disclosure: matrix leaks +2 NSM hole on Supplier Group root `rgt` (test-suite side effect,
timeline-proven; restored, `f5j13-rgt-restore.log`); V7-final PASS after restoration.

**Revision pinning (R5 remediation):** early V3/V4/V6a/V6b/V6c cycles ran on pre-final
runner revisions; every runner/verifier run cited above — V3, V6a, V6b, V6c, V5, V4b, V4, V7,
F-5J-8, V2 tamper tests (V0 excepted: it is the pre-state reference, captured before final
pinning) — was re-executed with the final code; logs record
`runner_sha16=2d1f3581b1acbc83` / `verifier_sha16=76ca731a386f54de` and explicit `rc=`.
Pre-final logs are retained only as superseded provenance. Post-tier baseline snapshot:
sha16 `36f96d929629aa3e`.

**Production gate state:** playbook READY; execution NOT authorized — `production_mutation_authorized`
stays `false` until the owner flips it per READINESS_AUDIT §12 checklist.
