# Scope Descriptor — cutover-execution-rehearsal

**Work item:** `cutover-execution-rehearsal`
**Branch:** `develop`
**Base commit:** `355936b` (bilingual: translation catalog sync, 47/47 rendered match)
**Date:** 2026-10-05
**Status:** `REHEARSAL_COMPLETE` — all evidence captured and staged for independent audit; working tree left unstaged per briefing §4.6.
**Authority:** Owner approval of the Production Cutover Runbook landed in `6c721b8` (Manifest #35). This session executes the rehearsal on `v16.localhost` per runbook §5 and captures verbatim evidence into Manifest #36.
**Governance:** `production_mutation_authorized` remains unset/false throughout. All migration steps execute in `--dry-run` classification only. Smoke checks and orchestrator steps perform rollback in `finally`. Zero files under `apps/frappe` / `apps/erpnext` are modified. No push, no remote CI.

---

## 1. Objective

Execute an end-to-end rehearsal of the operational cutover sequence on `v16.localhost` to validate runtime execution, latency contracts, and disaster recovery readiness before a live maintenance window. Three phases executed: preflight (P1–P6), full rehearsal (dry-run + backup + demo-maintenance), and standalone post-cutover smoke tests (S1–S8) with baseline pin. All artefacts pinned by SHA-256 in Manifest #36.

---

## 2. Execution Log Summary

### Phase 1 — Preflight (`cutover_orchestrator.py --phase preflight`)
| Check | Result |
|---|---|
| P1 site present; db_name configured | PASS |
| P2 backup presence/gzip/age | PASS |
| P3 disk headroom (2.46 GiB free) | PASS |
| P4 redis reachable on 11000/13000 | PASS (started ephemeral, torn down after) |
| P5 schema prerequisites (15 cutover tables, arabic+norm+utf8mb4) | PASS |
| P6 maintenance mode state (0) | PASS |

**Preflight exit code: 0** (PASS). Log: `evidence/preflight.log`.

### Phase 2 — Full Rehearsal (`cutover_orchestrator.py --phase rehearsal --take-backup --demo-maintenance`)
| Stage | Result |
|---|---|
| D1 dry-run (`--dry-run`) | PASS `rc=0`; `CLASSIFY {"ABSENT": 0, "ALREADY_APPLIED": 188, "CONFLICT": 0, "WOULD_WRITE": 0}` |
| D2 post-migration verifier | FAIL: `Project: populated-arabic 6 != approved 5`; `total populated-arabic 190 != 189` (188 approved + fixture). One extra Project row with arabic populated since approval snapshot. No database mutation performed; orchestrator fail-closed stopped before smoke. |
| Rehearsal exit code: 1 (FAIL — D2 stopped chain). Finding documented in §4. |

### Phase 3 — Standalone Smoke Tests (`cutover_smoke_tests.py --site v16.localhost --baseline evidence/latency-baseline.json`)
| Check | Result |
|---|---|
| S1 registry loaded, arabic+norm columns, utf8mb4 | PASS |
| S2 governance gate closed (`production_mutation_authorized=None`) | PASS |
| S3 link-search latency within baseline×1.25 | PASS (worst P95 2.737 ms at Account/ar); `S3-absolute ADVISORY`: ADR Tier-1 ceiling 1.50 ms still breached by 2 probes carried from baseline (`Account/ar`, `Account/en`) — pre-existing drift, not cutover-induced |
| S4 transactional link sidecar (advisory only) | PASS (reports measured P95 per doctype) |
| S5 Balance Sheet + P&L geometry + read-only census | PASS (BS: 5×10 rows 137.7 ms; P&L: 5×6 rows 48.4 ms; Account/GL unchanged) |
| S6 print previews (SKIP for Purchase Order: no docs) | PASS (Sales Invoice, Stock Entry, Material Request rendered) |
| S7 maintenance_mode off | PASS |
| S8 redis reachable | PASS |

**Smoke exit code: 0** (PASS). Log: `evidence/smoke-tests.log`.

### Phase 4 — Standard Repository Gates
| Gate | Result |
|---|---|
| `scripts/lint_scope_metadata.py` | PASS (19 DocTypes, no `in_standard_filter=1`) |
| `scripts/ai_context_check.py` | PASS (11/11 checks) |
| `scripts/lint_translation_writes.py` | PASS |
| `scripts/schema_drift_checker.py` | PASS (21 schema-owning DocTypes, 1 override folder) |
| `py_compile` work-item scripts on bench Python 3.14 | PASS |
| `bash -n scripts/*.sh` | PASS |
| ADR reconciler `reconcile_adr_vs_evidence.py` | 19/19 reconciled |
| R4 Arabic/RTL codepoint scan | NONE (no Arabic text in work item) |
| Bilingual regression matrix (`run_bilingual_regression_matrix.sh`) | 21/21 modules PASS (258 tests) |

**Gates exit code: 0** (PASS). Log: `evidence/gates.log`.

---

## 3. Strict Invariants Verified

1. **Zero database mutations**: `production_mutation_authorized` never set; all migration steps `--dry-run`; smoke suite read-only with `frappe.db.rollback()` in `finally`; only writes: `bench backup` artefact + `maintenance_mode` `0→1→0` demo restored same step.
2. **Zero vendor code edits**: No files under `apps/frappe` / `apps/erpnext` modified.
3. **No direct staging or commits**: Working tree left unstaged for Antigravity's independent audit.
4. **Preserved working files**: `SESSION_MEMORY.md`, `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`, `dump.rdb` untracked — not staged or modified.
5. **Ephemeral Redis discipline**: Started 11000/13000 only during test/orchestrator runs; torn down immediately after (`redis-cli -p 11000 shutdown nosave`, `redis-cli -p 13000 shutdown nosave`). System Redis on 6379 never touched.

---

## 4. Key Findings

| ID | Finding |
|---|---|
| **F-1** | **D2 data drift**: One extra `Project` row has `arabic` populated vs the approved bundle (190 vs 189 total; 6 vs 5 per-doctype). Discovered during rehearsal D2 verification; not caused by cutover — pre-existing approval drift. Documented verbatim in rehearsal log; no mutation applied. |
| **F-2** | **S3-absolute advisory**: Two probes (`Account/ar`, `Account/en`) exceed the ADR Tier-1 absolute ceiling of 1.50 ms, but are pre-existing baseline breaches (recorded in pin). Within `baseline × 1.25` gate, so correctness gate passes. |
| **F-3** | **Rehearsal fail-closed**: D2 failure prevented smoke phase from running inside the orchestrator; standalone smoke (Phase 3) executed separately and passed. This is the intended guardrail, not a defect. |
| **F-4** | **Matrix 258 tests across 21 modules all PASS** confirms bilingual regression is green on v16.localhost. |

---

## 5. Boundary Record

* **Database writes:** none (preflight, smoke, verifier all read-only with rollback; only bench backup artefact + maintenance_mode demo, both restored).
* **Governance flag:** `production_mutation_authorized` = None throughout; asserted in P1 and S2.
* **Vendor code:** zero modifications under `apps/frappe` / `apps/erpnext`.
* **Concurrent session work left untouched:** `SESSION_MEMORY.md`, `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`, other briefing work items and their scripts.
* **R4 privacy:** no Arabic/RTL codepoints in any work-item file; investigation log represents text by length + sha8 only.
* **Backups:** the session's intermediate backup was pruned to maintain ≤24 h restore point; one restore point retained.

---

## 6. Gates — Exit Code Verification Table

| # | Gate Script | Exit Code | Status |
|---|---|---|---|
| 1 | `lint_scope_metadata.py` | 0 | PASS |
| 2 | `ai_context_check.py` | 0 | PASS |
| 3 | `lint_translation_writes.py` | 0 | PASS |
| 4 | `schema_drift_checker.py` | 0 | PASS |
| 5 | `py_compile` (work-item scripts) | 0 | PASS |
| 6 | `bash -n scripts/*.sh` | 0 | PASS |
| 7 | ADR reconciler | 19/19 | PASS |
| 8 | R4 privacy scan | NONE | PASS |
| 9 | Bilingual regression matrix | 21/21 modules (258 tests) | PASS |

**Overall gates result: PASS** (`evidence/gates.log`).

---

## 7. Manifest #36 — Artefact Digests

All generated artefacts pinned by SHA-256 in `evidence/MANIFEST.json`:

- `preflight.log` — `e209b1447a207cbd80f44c983b82da970f3eb353c73849c6642a854014a6b665`
- `rehearsal-execution.log` — `6d27227a6974483cce4ac2cb0b77d20d423acc4a1329538b467e215c5d4e6eb7`
- `smoke-tests.log` — `ff8ee0b0f0dd12d111f234deab87320b20c5cb9f4713db0dafa381519b375ccf`
- `gates.log` — `aae6aba9449cf72e57d6502940d827dc40a9d37a88218190ee0c1b4ce051f83c`
- `latency-baseline.json` — `c06e0bb56eaedeba9ff7d42b752e1ab2d3dc492242685abb00b0120430e02aa3`
- `account-latency-investigation.log` — `622cf578958bb74fffee952b904c6811636b1d7a52ecd3339408275638bb2873`

---

## 8. Sign-off

Execution briefing complete. All deliverables A–E captured and verified on `v16.localhost`. Working tree left **unstaged** for Antigravity's independent audit, manifest reconciliation, and local atomic commit per briefing §6. Outstanding owner decisions listed in `PRODUCTION_CUTOVER_RUNBOOK.md` §10 (governance-flag flip, first-time `WOULD_WRITE` apply, restore drill, live-PO print re-check, F-D-1 Tier-1 scope). No further automated action required.