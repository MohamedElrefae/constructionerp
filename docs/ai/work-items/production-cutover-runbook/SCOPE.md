# Scope Descriptor — production-cutover-runbook

**Work item:** `production-cutover-runbook`
**Branch:** `develop`
**Base commit:** `234c024` (post 5J `5933c0d`)
**Date:** 2026-10-05
**Status:** `REVIEW_PENDING` — deliverables built and rehearsed green on `v16.localhost` (§5); awaiting
independent audit + local commit by the Lead Verifier (Antigravity Engineering Lane)
**Authority:** Owner briefing `docs/ai/BRIEFING_PRODUCTION_CUTOVER_RUNBOOK.md` (Antigravity Engineering Lane,
2026-10-05) — produce the operational runbook, the post-cutover smoke suite, the pre/post-flight wrapper and
a rehearsal execution record that engineering operations can follow inside a maintenance window.
**Governance:** **`production_mutation_authorized` remains unset/false.** This tier writes *no database row*:
every migration step is a `--dry-run` classification, the verifier and smoke suite are read-only (rollback in
`finally`), and the only writes performed are `bench backup` artefacts plus the `maintenance_mode` toggle,
which is restored within the same step. Zero files under `apps/frappe` / `apps/erpnext`. Strictly local —
no push, no remote CI.

---

## 1. Objective

Convert Tier 5J's migration machinery (`5933c0d`: consolidated fail-closed runner + post-migration verifier)
into an **executable, rehearsed cutover procedure**: a step-by-step runbook (T-24h → T-1h → T-0 → post-cutover
→ rollback), an automated pre-flight/post-flight wrapper, and a post-cutover smoke suite — each with its own
fail-closed exit code, each exercised on `v16.localhost` and captured verbatim in `evidence/`.

## 2. Deliverables

| # | Deliverable | Design decision |
|---|---|---|
| **A** | `PRODUCTION_CUTOVER_RUNBOOK.md` | Five timed sections (T-24h checklist, T-1h dry-run, T-0 execution, post-cutover smoke, emergency rollback) plus an orchestrator reference, a latency contract, the F-D-* findings, an exit-code table and a sign-off list. Steps that were deliberately **not** executed are labelled **[OWNER-GATED]** / **[NOT REHEARSED]** in-line and repeated in §10 — the runbook never presents an unproven command as proven. |
| **B** | `evidence/scripts/cutover_smoke_tests.py` | Checks **S1** registry bootstrap · **S2** governance-gate state · **S3** link-search correctness + P95 gate (30 probes = 15 doctypes × ar/en) · **S4** transactional link sidecar (advisory) · **S5** `Balance Sheet` + `Profit and Loss Statement` geometry **and read-only census** · **S6** print previews on live transaction documents · **S7** maintenance mode · **S8** redis. Any failed check ⇒ `rc=1`; `frappe.db.rollback()` in `finally`. |
| **C** | `evidence/scripts/cutover_orchestrator.py` | Phases `preflight` (P1–P6) / `dry-run` (D1 runner + D2 verifier) / `smoke` (S1) / `rehearsal` (all). Interactive unless `--yes`; fail-closed (`rc=1` on the first red gate); **never writes the database and never sets `production_mutation_authorized`**; redacts the database name from all output. |
| **D** | `evidence/rehearsal-dry-run.log` | One self-contained rehearsal record: Stage A baseline establishment → Stage B `--phase rehearsal --take-backup --demo-maintenance` → post-state invariants. |
| **E** | `evidence/gates.log`, `evidence/MANIFEST.json` | 6 lints + ADR reconciler (19/19) + R4 scan; manifest **#35** pinning every artefact by sha256. |

Supporting artefacts pinned in the manifest: `evidence/latency-baseline.json` (the S3 non-regression pin) and
`evidence/account-latency-investigation.log` (the F-D-1 root-cause investigation).

### Design decisions worth auditing

1. **Two-tier latency gate (decided by this work item, not inherited).** The ADR
   (`bilingual-performance-sla.md`) fixes an absolute Tier-1 ceiling of **≤ 1.50 ms P95** and a relative
   Tier-2A band of ≤ 1.15×. This suite treats *correctness* as a hard gate, applies **absolute 1.50 ms** to
   probes that were compliant in the baseline pin and **`baseline × 1.25`** to probes that breached at
   baseline, and always reports true ADR compliance separately as `S3-absolute ADVISORY`. Rationale: a
   pre-existing breach must be visible on every run without being able to fail a cutover that did not cause it.
2. **Baseline establishment is retried, never fudged.** `--write-baseline` refuses any pin above
   `--baseline-cap-ms` (10.0), retries up to `--establish-attempts` (3) with `load1/load5` printed per attempt,
   and fails loudly if it never quiets down. A pin is a promise about the future; garbage-in is refused.
3. **`--skip-latency` exists but is self-labelled** "diagnostic only — never use for a real cutover", and the
   log line it emits says the same.
4. **No automated rollback command.** §5 of the runbook documents `bench restore` with its verified option set
   but does **not** wrap it in a script: executing it is destructive, owner-gated, and needs MariaDB root
   credentials. The rehearsal invariant (no database writes) forbids proving it here.
5. **Maintenance-mode semantics.** The rehearsal demonstrates `on → off` and leaves the site serving; a real
   window keeps maintenance ON through the smoke run with `--allow-maintenance`, then closes it (runbook §4.6).
6. **Reports are gated on the ledger-bearing company** (Elrefae, 4 GL rows) rather than the newest `Company`,
   because the newest test company has zero GL rows and would render an empty "pass" (F-D-8).

## 3. Findings

| ID | Finding |
|---|---|
| **F-D-1** | **`Account` link search sits at/above the ADR 1.50 ms Tier-1 ceiling** (desk surface: 3.075 ms pin, 2.698–3.340 ms across three query shapes, 1.977 ms with a company filter; ADR methodology on the same data: native 1.402–1.449 / governed 1.567–1.668 ms, ratio 1.081–1.190×). The other 14 cutover doctypes are 0.65–1.10 ms on the identical harness. Unfiltered row scope (2102 vs 86 rows) explains **+1.364 ms** of the desk-surface cost. The ADR §4 frozen pin (1.322 / 1.482 ms) was calibrated on the synthetic fixture prefix `CT-T3-` over a handful of rows and **does not transfer** to production query text. **Stable across the dry-run (3.075 → 3.123 ms): not cutover-induced.** Evidence: `evidence/account-latency-investigation.log`. Owner decision required (runbook §10.5). |
| **F-D-2** | **First rehearsal attempt failed and is disclosed:** establishing the pin while a concurrent test-suite run was active produced P95 29.851/32.402 ms for `Account`, and the cap correctly **refused** the pin (`baseline refused: P95 above --baseline-cap-ms 10.0`); Stage B then failed the absolute gate. Cause was DB lock contention on a 12-CPU box with load1 ≈ 2.4 (not CPU). Remediated: quiesce step (runbook §1.1) + bounded `--establish-attempts` with load transparency. |
| **F-D-3** | **Transactional link sidecar has no ratified latency budget** (Sales Order 1.775 ms, Material Request 2.310 ms, Sales Invoice 2.619 ms, Purchase Order 0.906 ms P95). Measured and reported as **S4 ADVISORY** every run; a budget decision belongs to the owner/ADR, not to this work item. |
| **F-D-4** | **`Purchase Order` has zero documents** on the rehearsal site, so its print preview cannot be exercised. `S6 SKIP` is emitted and explicitly *not* counted as a pass; must be re-run on a site carrying live POs. |
| **F-D-5** | Latency gates are meaningless on a busy bench (F-D-2). The smoke header now prints `load1/load5/load15` on every attempt so contention is visible, never silent. |
| **F-D-6** | **Disk 96% used, 2.47 GiB free** against a P3 floor of 2 GiB; each `bench backup --with-files` costs 68 MiB. Keep exactly one ≤24 h backup, prune only dumps that are not digest-pinned by an earlier manifest, and consider raising the floor. |
| **F-D-7** | `frappe.get_print` resolves `assets/assets.json` relative to the process CWD — helpers anchor every path off `BENCH` and `chdir(sites/)`, so they can be invoked from any directory (runbook §10 note). |
| **F-D-8** | Financial reports must run against the **ledger-bearing** company; the newest `Company` on this site has 0 GL rows. S5 selects by GL presence and records geometry only (R4). |

## 4. Boundary record

* **Database writes:** none. S5/S3/S4/S6/S8 are read-only and roll back in `finally`; D1 classifies without
  opening a write transaction; D2 is read-only. The rehearsal's only writes: one `bench backup --with-files
  --compress` artefact set (20261006_021223, 68.0 MiB + files) and the `maintenance_mode` `0 → 1 → 0` demo.
* **Governance flag:** never written by any code in this work item; asserted `None` in P1, S2 and the post-state
  block of the rehearsal log.
* **Vendor code:** zero files under `apps/frappe` / `apps/erpnext` opened for writing.
* **Concurrent-session work left untouched:** `SESSION_MEMORY.md`, `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`,
  `construction/api/bilingual_reports.py`, `construction/hooks.py`, `construction/install.py`,
  `construction/tests/test_stage7_bilingual_reports.py`, `bilingual_report_viewer.js`, the untracked
  `print_format/*` folders, `tests/test_bilingual_transaction_print.py`, the Session A/B/C briefings and their
  work-item directories.
* **R4 privacy:** no Arabic value, report cell or query text is printed, logged or committed. Query text in the
  investigation log is represented by length + sha8 only; gates.log carries an explicit RTL-codepoint scan of
  the whole work item (`Arabic/RTL codepoints: NONE`).
* **Backups:** the Tier-5J backup (`20261005_215245`, digest pinned in the 5J manifest) was left intact; this
  session's own intermediate backup was pruned to keep disk headroom, leaving one ≤24 h restore point.

## 5. Rehearsal verification record

`evidence/rehearsal-dry-run.log` — one continuous capture, head `234c024`, branch `develop`, start
`2026-10-05T20:42:16Z`:

| Stage | Result | Key output |
|---|---|---|
| **A — baseline establishment (T-1h)** | `rc=0`, `SMOKE RESULT: PASS (9 passed, 2 advisory)` | `load1=2.36 load5=2.72`; **30/30 probes correct**; baseline written (`captured_utc 20:42:21Z`, worst 3.075 ms `Account/ar`); `S3-absolute ADVISORY` for the 2 pre-existing breaches; S5 `Balance Sheet 5×10 in 200.6 ms`, `P&L 5×6 in 52.7 ms`, census `Account=2102 GL=4` unchanged; S6 `SKIP` for Purchase Order disclosed |
| **B1 — P1 site/gate** | PASS | `db_name configured=yes; production_mutation_authorized=None` |
| **B2 — P2 backup (T-24h)** | PASS | `bench backup --with-files --compress` → `20261006_021223` **68.0 MiB, 0 min old, gzip stream verified end-to-end** |
| **B3 — P3 disk / P4 redis / P5 schema** | PASS | `2.47 GiB free`; `queue:11000`+`cache:13000` PONG; arabic+norm+utf8mb4 on all 15 tables; `Account rows=2102` |
| **B4 — P6 maintenance demo** | PASS | `set-maintenance-mode on` `rc=0` → `off` `rc=0` (site left serving) |
| **B5 — D1 dry-run** | PASS `rc=0` | `CLASSIFY {"ABSENT": 0, "ALREADY_APPLIED": 188, "CONFLICT": 0, "WOULD_WRITE": 0}` · `RESULT: PASS dry-run, 0 writes … (0.4s)` |
| **B6 — D2 verifier** | PASS `rc=0` | `VERIFY RESULT: PASS (V1 counts, V2 norms, V3 frozen, V4 trees, V5 probes)` |
| **B7 — S1 smoke** | PASS `rc=0` | `SMOKE RESULT: PASS (9 checks passed, 2 advisory)`; worst gate 3.123 ms within `baseline × 1.25` |
| **Summary** | **`RESULT: PASS`** | every `[PASS]` line P1–P6, D1, D2, S1 |
| **Post-state** | invariant holds | `production_mutation_authorized= None` · `maintenance_mode= 0` |

Additional executed evidence: `evidence/account-latency-investigation.log` (F-D-1, five sections, two
repeat runs of the ADR methodology, one filter-scope control) and `evidence/gates.log`.

## 6. Gates

`evidence/gates.log` — all `exit=0`:

1. `scripts/lint_scope_metadata.py` — PASS (19 DocTypes)
2. `scripts/ai_context_check.py` — PASS (11/11, ADR 8 records)
3. `scripts/lint_translation_writes.py` — PASS
4. `scripts/schema_drift_checker.py` — PASS (21 schema-owning DocTypes, 1 override folder)
5. `py_compile` of both work-item scripts on bench Python 3.14 — PASS
6. `bash -n` over `scripts/*.sh` — PASS
7. ADR reconciler `reconcile_adr_vs_evidence.py` — **19/19, mismatched 0, unsourced 0**
8. R4 scan over the work item — `Arabic/RTL codepoints: NONE`

## 7. Out of scope (respected)

* Any production mutation, and therefore any run with `production_mutation_authorized: true`.
* Editing the Tier-5J runner/verifier (invoked read-only as external commands; their digests are theirs).
* Editing `bilingual-performance-sla.md` or any ADR — F-D-1 raises an owner decision, it does not rewrite policy.
* A `bench restore` drill (destructive; documented, flagged **[NOT REHEARSED]**, needs root credentials).
* Index/SQL rework for Account link search (candidate follow-up, owner decision).
* Push, PR, remote CI, or any change under `apps/frappe` / `apps/erpnext`.
* `SESSION_MEMORY.md`, `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`, and other sessions' work items.

## 8. Sign-off

Deliverables A–E are complete and green; **execution remains unauthorized**. Outstanding owner decisions are
listed in `PRODUCTION_CUTOVER_RUNBOOK.md` §10 (governance-flag flip, first-time `WOULD_WRITE` apply, restore
drill, live-PO print re-check, and the F-D-1 Tier-1 scope question). Working tree left **unstaged** for the
Lead Verifier's independent audit and commit.
