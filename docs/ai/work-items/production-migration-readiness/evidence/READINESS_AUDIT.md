# Production Migration & Readiness Audit — Tier 5J (deliverable A)

**Work item:** `production-migration-readiness` · **Site:** `v16.localhost` (dev)
**Base commit:** `3e871f0` · **Date:** 2026-10-05 · **Auditor:** engineering lane, per owner briefing
`docs/ai/BRIEFING_PRODUCTION_MIGRATION_READINESS.md`
**Governance:** `production_mutation_authorized` = **false** — production is never touched by
this tier; the playbook was validated end-to-end on the development site only.
**R4:** this document contains counts, classifications, verdicts and digests only — no Arabic
master values (those live exclusively under `sites/v16.localhost/private/production-migration/`).

---

## 1. Executive verdict

| Area | Verdict |
|---|---|
| Target dataset | **188 approved rows / 15 doctypes** consolidated and owner-sha-bound; byte-cross-checked against the verified site (V1) |
| Schema prerequisites (custom fields `*_ar` + `*_ar_norm`) | **PASS** — present on all 15 doctypes |
| Encoding (utf8mb4) | **PASS** — 779/779 site tables utf8mb4, 0 exceptions |
| Policy hooks | **PASS** — all 15 doctypes bound (`Account` → dedicated governed policy) |
| Backup protocol | **GAP (closed by runner)** — site backup dir was empty, no automation; runner now requires a fresh SQL dump (age-gated) before any write |
| Redis dependency | **documented** — queue `11000` + cache `13000` must be reachable (pre-flight enforces) |
| Governance guard | **PASS** — non-allowlisted sites refused unless `site_config.production_mutation_authorized: true` |
| Runner validation (V1–V7) | **PASS** — dry-run 0 writes; idempotent; conflict/absent/sha fail-closed; 188-save rollback rehearsal byte-identical; verifier PASS |
| Production readiness | **Playbook READY, execution NOT authorized** — flips only when the owner sets the flag (plan §18), takes a fresh backup, and re-runs the runner |

## 2. Census variance vs briefing (F-5J-1)

Briefing claims **196 records / 12 DocTypes** (its own table sums to 186). Live census: **189
populated rows across 15 DocTypes**. Reconciliation:

* **188 approved** rows (the runner's contract) + **1 pre-existing test fixture**
  (`Warehouse / CT-TEST-P2-WH-01 - TQC`, frozen-excluded since Tier 5C, does not exist on
  production) = 189.
* Briefing omits three populated surfaces: **Customer (1), Task (1), Terms and Conditions (1)**
  (briefing Warehouse 6 = 5 approved + 1 frozen fixture — already inclusive); the sum
  discrepancy (196 vs 186 internal) is a briefing table error, not a data gap.
* Per-doctype approved counts (runner contract, all owner-approved tiers):

| Doctype | n | | Doctype | n |
|---|---:|---|---|---:|
| Account | 81 | | Supplier Group | 8 |
| Item | 8 | | Item Group | 6 |
| Warehouse | 5 (+1 fixture) | | Territory | 4 |
| Project | 5 | | Company | 1 |
| Customer Group | 5 | | Customer | 1 |
| Department | 14 | | Task | 1 |
| Cost Center | 3 | | Terms and Conditions | 1 |
| UOM | 45 | | **Total** | **188** |

## 3. Value provenance (F-5J-2)

Consolidation (`evidence/scripts/consolidate_production_values.py`, V1 log) bound every row to
its approval source; all 105 proposal rows were re-verified **byte-identical** to the live
site before the bundle was sealed:

| Source (private) | rows | sha256 (source) |
|---|---:|---|
| `wave1-population/proposal.json` | 9 | `a00cfb432ed6680e…` |
| `wave1-phase2-population/proposal.json` | 13 | `e68ef0c687516a11…` |
| `wave2-group-masters-population/proposal.json` | 23 | `08dba90a8134c238…` |
| `department-phase1-population/proposal.json` | 14 | `dba85a4ceba58260…` |
| `company-phase1-population/proposal.json` | 1 | `b5fcc02a6854ebb2…` |
| `uom-phase1-population/proposal.json` | 15 | `18a16a953ebbaad70…` |
| `uom-phase2-triage/proposal.json` (`units`) | 30 | `930b91cd2f5c64ec…` |
| site export: Account (Stage-4 bundle) | 81 | tier evidence (5B SCOPE: no Account row touched) |
| site export: Task, Terms and Conditions | 2 | master tiers predating proposal pattern |
| **Sealed bundle** `consolidated_values.json` | **188** | **`7390a0c87f8ebab1e602521549b775f8768d3ab9bb40a1caf055f4c5c31d53bf`** |

Populated-but-unapproved rows = **exactly the one fixture** (asserted). Runner refuses any
bundle whose sha ≠ committed `EXPECTED_VALUES_SHA256` (V6a: tampered copy → exit 1).

## 4. Schema & encoding (F-5J-3)

* Runner pre-flight: for all 15 doctypes, `information_schema` confirms both `*_ar` and
  `*_ar_norm` columns exist; table collation `utf8mb4*` (**15/15**).
* Whole-site sweep: **779 tables, 0 non-utf8mb4** (`gates-audit-numbers.log`).
* Note: Frappe table names preserve spaces (`tabCost Center`) — pre-flight uses `tab` + doctype.

## 5. Policy hooks (F-5J-4)

All 15 in-scope doctypes are bound in `construction/hooks.py`:

* `Account` → `enforce_account_arabic_policy` (insertion confinement, **governed-operation
  token** binding `doctype/name/old/new`, server-derived norm on every save) +
  report-cache busters.
* The other 14 → `enforce_bilingual_arabic_policy` (bidi/control rejection, **server-derived
  norm overwrite** on every save — client-passed keys are never trusted).
* The runner contains **no norm write path** (norm fields are never set directly) and **no
  `Translation` write path** (22,762 pre-existing rows are vendor/bench data, out of scope —
  `gates-audit-numbers.log`).

## 6. Backup protocol (F-5J-5) — gap and enforcement

* State at audit: `sites/v16.localhost/private/backups/` **empty**; only stale archive
  `private/backup-archive-20260921/` (dumps of 2026-09-02); no cron/hook automation.
* During this tier a fresh backup was taken: `20261005_215245-v16_localhost-database.sql.gz`
  (67.8 MiB) — V2.
* Runner pre-flight now **requires** a `*.sql*` dump in the site's `private/backups/` younger
  than 24 h; `--force` bypasses **only the age gate** (never the presence gate); the
  site-config JSON alone does not satisfy it. Both failure modes were exercised against the
  final runner: missing dir → exit 1 (`v2-backup-missing.log`); dump aged to 25 h → exit 1
  (`v2-backup-stale.log`).

## 7. Root-save mechanics (F-5J-6 / F-5J-11 / F-5J-12) — proven map used by the runner

13 approved root rows are in scope (Account ×5, then Company, Cost Center, Warehouse, Item
Group, Customer Group, Supplier Group, Territory, Department — 5+8 = 13, matching V5
`ROOT_SAVES: 13`; the Task row is non-root; the excluded Warehouse fixture is a further site
root outside the bundle). Ten of the 15 doctypes are trees (the 9 root-bearing ones listed + Task). Every mechanism below was
exercised for real inside the V5 rollback rehearsal (188/188 saves, 13 root saves):

| Doctype(s) | Vendor obstacle | Runner mechanism (scoped, restored in `finally`) |
|---|---|---|
| Item Group | `validate` forces `_("All Item Groups")` parent unless `frappe.in_test` (`item_group.py:35`) | temporary `frappe.in_test = True` (5D precedent) |
| Customer Group, Supplier Group, Territory, Department | `get_root_of()` returns the root itself → self-parent → `NestedSetRecursionError` | module-scoped `get_root_of → None` patch (5D/5G precedent) |
| Department, Cost Center | root saves violate reqd fields (`company` NULL; `parent_cost_center` reqd) | `doc.flags.ignore_mandatory = True` (R3a/5C/5G precedent); disclosed non-root safety net fails closed |
| **Account roots** | **`validate_root_details` throws `RootNotEditable` on ANY save of an existing root (`account.py` 211 def / 214 if / 215 throw)** + `parent_account` reqd=1 | **(F-5J-11)** narrow class-method no-op of *only* `validate_root_details` (this also disables its second check, "root must be a group", which holds for all 5 roots) + root-only inline **governed** save: same `ct_governed_arabic_edit` token contract the hook validates, identity check, norm derived server-side by the hook, Version recorded, `doc.flags.ignore_mandatory` for reqd `parent_account` |
| Warehouse, Task, Company, other Account rows | none (proven plain: 5C/5H/Stage-4) | plain save (Account via governed `set_account_name_ar`) |
| **All tree doctypes** | **(F-5J-12)** `update_nsm` (invoked by every `NestedSet.on_update`) treats stale `old_parent` bookkeeping (bulk-import artifact) as a move → `update_move_node` renumbers sibling `lft/rgt` (observed: ONE Account save renumbered 12 rows), and **unconditionally rewrites `old_parent`** (`update_modified=False`) | `frappe.local.flags.ignore_update_nsm = True` for the apply (`chart_of_accounts.py:71`, `company.py:526` precedent), restored in `finally`. **Scope precision:** that flag is honored only by `Account.on_update` and `Department.on_update`; for the other 8 trees it is inert — safety there is `old_parent == parent` already holding on this dataset **plus** the runner's in-transaction tree assertion (now a 4-tuple incl. `old_parent`, fail-closed → rollback). For Account the flag also skips `NestedSet.validate_ledger` (disclosed vendor check bypass; ledgers unchanged by ar-only saves). V5 rc=0 proves parent/`lft`/`rgt`/`old_parent` byte-identical across all 188 saves |

Unknown root quirk or any other exception ⇒ `frappe.db.rollback()` + exit 1 (fail-closed;
no invented workarounds).

## 8. Redis & runtime dependencies (F-5J-7)

* Company/Department-class saves reach the **queue** connection (port `11000`,
  `frappe.cache`-adjacent enqueue paths; F-5H-2) and `update_global_search → frappe.cache.lpush`
  (**cache** port `13000`; matrix gate G1). Pre-flight PINGs both; execution requires them up.
* `global_search_queue` backlog on the bench: **10,678 entries** at gate time
  (`gates-audit-numbers.log`) — no rq worker runs on this bench, so queue entries accumulate
  without side effects (and cannot write after a rollback).
  **Production note: a worker must be running** so the post-migration queue drains; entries
  are metadata-only rebuild jobs.

## 9. Governance guard (F-5J-8)

`production_mutation_authorized: false` is documented in plan §18, not present in any
`site_config.json`. The runner enforces it mechanically: a site is accepted only if it is in
`--allow-sites` (default `v16.localhost`) **or** its own `site_config.json` sets
`production_mutation_authorized: true`. Verified: refusing test → exit 1
(`gates-f5j8.log` — `v16.localhost` deliberately absent from `--allow-sites
prod.example.com` with no site-config flag; final runner sha recorded). Precedence note: an allowlisted site is
accepted even if its site_config carried an explicit `false` (allowlist wins); an explicit
`true` in site_config is what unlocks any other site.

## 10. Search probe surface (F-5J-9)

Post-flight verifier probes, per doctype, Arabic exact + English identity:

* `bilingual_service.search_bilingual(doctype, txt, with_meta=True)` — 30 queries (one
  representative approved row per doctype, Arabic exact + English identity), **all hits**;
  p50 **0.7 ms**, max **5.2 ms** (V7).
* `transaction_link_search.search_transactions("Sales Order" | "Purchase Order", txt)` — 2
  queries, bounded list returns, included in the same latency pool (32 queries total).

## 11. Validation runs (executed, logs in `evidence/`)

| Run | Command essence | Result |
|---|---|---|
| V1 | `consolidate_production_values.py` | **PASS** — 188 rows, 15 doctypes, proposals byte-match site, fixture-only unapproved (`v1-consolidation.log`) |
| V0 | verifier `--snapshot-out` (pre-state) | 189 rows, sha16 `dbba9ee9a9c0cd99` |
| V2 | `bench backup` | fresh 67.8 MiB SQL dump |
| V3 | runner `--dry-run` (final code) | **PASS** — 188 ALREADY_APPLIED / 0 writes, rc=0 (`v3-dry-run.log`, `runner_sha16` recorded) |
| V4 | runner (idempotent apply, final code) | **PASS** — 188 SKIPPED / 0 SAVED, commit no-op, rc=0 (`v4-idempotent-apply.log`) |
| V5 | runner `--reapply --rollback-rehearsal` (final code) | **PASS** — **188/188 real saves, 13 root saves**, in-transaction values+norms verified, parent/`lft`/`rgt`/`old_parent` byte-identical, **rollback → full pre-state byte-identical**, rc=0 (`v5-rollback-rehearsal.log`) |
| V6a | tampered bundle copy (final code) | **PASS** — sha gate rc=1 before any DB work (`v6a-sha-gate.log`) |
| V6b | site-side divergent value, committed bundle (final code) | **PASS** — `CONFLICT … rc=2`, zero writes, restored byte-equal (`v6b-conflict.log`) |
| V6c | 2 rows nulled via `db.set_value` (Account root + Item; final code) | **PASS** — WOULD_WRITE=2 classification, rc=0 (`v6c-would-write.log`) |
| V4b | runner (apply path, final code) | **PASS** — SAVED=2 (governed root + plain), SKIPPED=186, FINAL 188, rc=0 (`v4b-apply-restores.log`) |
| V7 | verifier `--pre V0` (final code) | **PASS** — V1 counts (188+fixture), V2 **189** server-derived norms (incl. fixture), V3 frozen (576 cells), V4 trees (10/10 valid), V5 probes (rc=0, `v7-final-verifier.log`, `verifier_sha16` recorded) |
| F-5J-8 | non-allowlisted site (final code) | **PASS** — refused, rc=1 (`gates-f5j8.log`) |
| V2-gates | backup presence/age tamper (final code) | **PASS** — both refused, rc=1 (`v2-backup-missing.log`, `v2-backup-stale.log`) |
| Gates | lints + compile + reconciler + matrix | **PASS** — `lint_scope_metadata` PASS (19 DocTypes), `ai_context_check` PASS (11/11 checks), `lint_translation_writes` PASS, `schema_drift_checker` PASS (each rc=0, `gates-lints-final.log`, re-run after the final doc edits); `py_compile` ×3 rc=0 with final script shas (`gates-compile-final.log`); `bash -n` rc=0 (`gates-bashn.log` — `run_bilingual_regression_matrix.sh`); ADR reconciler **19/19** (`gates-compile-reconcile.log`); matrix **21 modules / 264 tests / 0 failed** (`gates-matrix.log`) |
| V7-final | verifier after all gates + F-5J-13 restore | **PASS** (rc=0); post-tier baseline snapshot sha16 `36f96d929629aa3e` (`v7-post-snapshot.log`) |

**R5 remediation (revision drift):** early V3/V4/V6a/V6b/V6c cycles ran against pre-final
runner revisions (differing at least in the backup-acceptance filter and the governed-flag
restore). **Every runner/verifier run cited in the table except V0** (the
pre-state reference, captured before final pinning) was **re-executed with the final pinned
code** — each such log carries `runner_sha16=2d1f3581b1acbc83` (runner) or
`verifier_sha16=76ca731a386f54de` (verifier) and an explicit `rc=` line. V1
(`v1-consolidation.log`, consolidator — its sha pinned in `gates-compile-final.log`) and the
gate runs that execute neither pinned script (`gates-lints-final.log`, `gates-bashn.log`,
`gates-compile-reconcile.log`, `gates-audit-numbers.log`, `gates-compile-final.log`, each
with its own `rc=`; `gates-matrix.log`, whose unittest output records `OK` — 21 modules /
264 tests / 0 failed — rather than an rc line) are unaffected by the runner revision and are
cited as recorded. The earlier
`v7-verifier.log`/`v7-post-gates-verifier.log` and other pre-final logs are retained solely
as superseded provenance.

**F-5J-13 (disclosure):** the unchanged regression matrix leaks a **+2 NestedSet hole on
`Supplier Group / All Supplier Groups` root `rgt`** (a test creates then deletes a group; the
ancestor decrement is missed — the bench already carried a historical 17..130 hole). Timeline
proves it is test-suite side effect, not migration: V7-pre-matrix PASS (root `rgt`=130) →
matrix green → V7-post-gates flagged root `rgt`=132 (row set, values, norms, nesting all
intact) → restored `rgt` to 130 (`update_modified=False`, `f5j13-rgt-restore.log`) →
**V7-final PASS**. First matrix attempt also aborted at module 1 when the bench's
transient `11000`/`13000` redis daemons were unreachable (environmental; restarted with
logfiles, full re-run green).

**Validation-only disclosures:** V6/V5 exercised `db.set_value` perturbation on **2 test
rows** — the Item row was first set to a divergent **non-empty** value (V6b) and then,
together with the Account root row, **nulled** (V6c) — all restored through the production
apply path (`modified` bumped on those 2 rows only); during
rehearsals the `global_search_queue` backlog grew by metadata-only entries (no worker ⇒ no
effect). End state after V7 matches V0 on every V0-captured field (V7 PASS: 576 cells,
row sets, 189 norms, `parent`/`lft`/`rgt`; V0 predates `old_parent` — that field's
byte-equality is proven in-transaction by V5's 4-tuple assertion, rc=0). Post-tier baseline
snapshot (final format incl. `old_parent`): sha16 `36f96d929629aa3e`, re-confirmed
byte-identical after the final run set.

## 12. Residual risks / before flipping the flag (owner checklist)

1. Take a fresh `bench backup` (runner enforces <24 h anyway) and verify restore drill.
2. Start queue (`11000`) + cache (`13000`) redis and the rq worker (§8).
3. Run `--dry-run` on production: expect **188 WOULD_WRITE / 0 conflicts** if state matches
   the export baseline; any CONFLICT/ABSENT ⇒ stop and re-approve (fail-closed by design).
4. Set `production_mutation_authorized: true` **only in production's** `site_config.json`
   (or pass the site via `--allow-sites`), run the apply once, then run the verifier with a
   pre-snapshot.
5. Idempotence: re-running the runner afterwards ⇒ 188 ALREADY_APPLIED / 0 writes (V4 proof).
6. Quiesce: classification runs before `frappe.db.begin()`; run the migration with the site
   quiesced (no concurrent writers to the 15 doctypes) so a value written between CLASSIFY
   and save cannot be clobbered without a CONFLICT.
