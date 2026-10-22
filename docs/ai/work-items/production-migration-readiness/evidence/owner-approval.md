# Owner Approval Record — production-migration-readiness

**Work item:** `production-migration-readiness` (Tier 5J)
**Base commit:** `3e871f0`
**Branch:** `develop`
**Date:** 2026-10-05
**Authorized test site:** `v16.localhost` (`production_mutation_authorized: false` — unchanged)
**Independent review:** 5 rounds, non-author reviewer, final verdict **APPROVE** (round 5)

---

## 1. Approved SHA-256 pins (owner-approved, sha-bound)

| Artefact | sha256 (first 16) |
|---|---|
| `READINESS_AUDIT.md` (deliverable A) | `03ec8ef8dedf9573` |
| `SCOPE.md` | `b9f66fe7a2f87e5a` |
| `scripts/run_production_bilingual_migration.py` (deliverable B) | `2d1f3581b1acbc83` |
| `scripts/verify_production_bilingual_migration.py` (deliverable C) | `76ca731a386f54de` |
| `scripts/consolidate_production_values.py` | `363157ac1c06f4d0` |
| `consolidated_values.json` (private, R4) | `7390a0c87f8ebab1` |
| `pre_state_5J.json` (private, V0) | `dbba9ee9a9c0cd99` |
| `post_state_5J.json` (private, final baseline) | `36f96d929629aa3e` |

Full digests are pinned in `MANIFEST.json`; it is generated after this record and pins this
record's digest.

## 2. Owner approval scope

1. **Deliverables A–D** as built and validated: readiness audit (F-5J-1..13), fail-closed
   idempotent migration runner (classify → pre-flight gates → transactional apply /
   rollback rehearsal), post-flight verifier (V1 counts, V2 norms incl. fixture,
   V3 frozen cells, V4 trees, V5 search probes), `MANIFEST.json`.
2. **Validation evidence** on `v16.localhost`: V3 dry-run 188 ALREADY_APPLIED / 0 writes
   (rc=0); V4 idempotent 188 SKIPPED / 0 SAVED (rc=0); V5 `--reapply --rollback-rehearsal`
   188/188 real saves, 13 root saves, in-transaction 4-tuple tree equality, rollback →
   pre-state byte-identical (rc=0); V6a sha-gate rc=1, V6b CONFLICT rc=2 zero writes,
   V6c WOULD_WRITE=2; V4b apply SAVED=2 / SKIPPED=186 / FINAL 188 (rc=0); V7 verifier PASS
   (189 norms, 576 frozen cells, 10/10 trees, 32 probes; rc=0); F-5J-8 governance guard
   rc=1; backup missing/stale tamper rc=1 each.
3. **Gates:** 4 lints + `py_compile` ×3 + `bash -n` (all rc=0), ADR reconciler **19/19**,
   regression matrix **21 modules / 264 tests / 0 failed**, R4 Arabic scan **NONE**.
4. **Invariants:** `production_mutation_authorized` stays `false` (no production mutation,
   execution NOT authorized); zero changes under `apps/frappe` / `apps/erpnext` and no
   shared-source edits (commit = this work-item directory only); F-5J-13 NSM hole
   disclosure + restoration; revision-drift re-runs pinned to final code.
5. **Commit authority:** stage exactly this work item (`git add -f`), local commit via
   `git -c core.hooksPath=/dev/null commit …`, **no push, no PR**.

## 3. Status

**APPROVED FOR STAGE & LOCAL COMMIT** — owner decision recorded 2026-10-05
(interactive approval, options: "Approve — pin & commit").
