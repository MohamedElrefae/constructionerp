# Audit Note: Stage 4 Native-Path & Recovery Corrections (Canonical Plan §11)

## 1. Commit Provenance and Lineage

- **Historical Base Commit:** `72da63dc693e320ea8b73d5bdf7000c4fda57f07` (Verified Phase 3 Pilot).
- **Synchronization Commit:** `50a40562eaf7ec6db29901cb07829bfda144ff61`
  - Canonical Plan §11 ERP adoption machinery and Stage 4 governance foundation.
- **Contract & Privacy Commit:** `b29106e38cfd20c76c963f08bcc799c80cae550b`
  - First-pass contract and privacy corrections per owner review.
  - Retained unmodified as the immediate parent of this corrective follow-up commit.
- **Current Corrective Commit:** Follow-up commit on branch `feature/scope-context-portability`.
  - Implements the Project Owner's directive: `MILESTONE REVIEW: NATIVE-PATH AND RECOVERY CORRECTIONS REQUIRED`.

## 2. Core Corrective Invariants Enforced

1. **Bubblewrap Neutral Mounts inside Sandbox-Owned Writable Root:**
   - In `orchestrator/sandbox.py`, neutral mounts are strictly anchored inside `/tmp/workspace/private_inputs/...` and `/tmp/workspace/private_output/` within the writable sandbox `--tmpfs /tmp` hierarchy.
   - Intermediate directories are created cleanly with `--dir`, preventing `bwrap: Can't mkdir /workspace: Read-only file system` errors on host root `/`.
   - Hidden roots and protected paths inside `/tmp` create intermediate parent mount points without wiping `/tmp` or `/run`.

2. **Full Test Suite Reproducibility (119 / 119 Passed):**
   - In `orchestrator/tests/test_validation_runner.py`, offline network isolation assertion respects `can_unshare_net()`, proving positive denial when available and failing closed cleanly.
   - All 119 tests across all 11 test modules reproduce with 100% pass rate.

3. **Crash-Recoverable Acceptance Journaling:**
   - In `orchestrator/engine.py`, `Engine.accept()` writes and `fsync`s an atomic acceptance journal (`private-acceptance-record.json`) prior to unlinking `output.json`.
   - If a crash occurs after the private blob is stored but before the SQLite event is committed, `accept()` idempotently recovers verified metadata directly from `private-acceptance-record.json` and completes acceptance without re-evaluating or re-requiring `output.json`.

4. **Review Provenance & Session Binding:**
   - In `orchestrator/stage4.py`, `validate_and_store_review()` verifies that reviewer documents explicitly declare and match `role == expected_role`, `proposal_sha256 == expected_proposal_sha`, and `session_id == expected_session_id`.
   - Any document tampering or mismatch fails closed immediately.

5. **Sanitization of Public Explanations and Findings:**
   - In `orchestrator/stage4.py` and `orchestrator/engine.py`, `sanitize_public_text()` scrubs both Arabic character sequences (`ARABIC_RE`) and confidential catalog terms (identities, English account names) before writing to explanations, findings, `STATE.json`, or SQLite events.
   - Reviewer `blocking_findings` are sanitized before returning `review_meta`.

6. **Catalog TOCTOU Elimination via Content-Addressed Storage:**
   - In `orchestrator/engine.py`, `adopt_historical()` immediately stores the verified export catalog into content-addressed private blob storage (`store_private_blob(..., expected_sha=export_sha256)`).
   - `_prepare()` mounts the immutable private blob (`/tmp/workspace/private_inputs/account_catalog.json`) after verifying its SHA-256 digest against `export_sha256`. Host file modifications or catalog replacement cannot alter the proposer's inputs.

7. **Quorum Panel Failure & Blocking Enforcement in Bundle Composition:**
   - In `orchestrator/stage4.py`, `compose_and_store_bundle_and_payload()` independently inspects all quorum panel review blobs.
   - Fails closed if any review reported a non-PASS verdict, blocking findings, rejected row decisions, or requested renewal.

8. **Zero Private Data Leakage into State or Config:**
   - `expected_identities` (containing account names) is NEVER stored in `e.config`, workflow state, or SQLite checkpoints.
   - `Engine.accept()` dynamically derives `expected_identities` and `catalog_terms` from the verified private export catalog blob and validates `identities_digest`.
   - `test_exhaustive_privacy_leakage_scan` confirms zero account names or identities across all SQLite tables, ledgers, runs, and `STATE.json`.

9. **Zero Mutation to Production Assets:**
   - Production checkout `/home/mohamed/frappe-bench/apps/construction` remains 100% byte-for-byte immutable across all 1,616 files (`apps_construction_manifest_sha256 = f538d7d10d9600d7d88aec64648a5e72d84615bd26afc0c332db8569dbb94b4e`).
   - Entry tree hierarchy (1,759 entries: 1,616 files + 143 directories, 0 symlinks) verified (`b03cf2d03dd5e7c74ad55a9940f0bfbcb86fcc3034241e0b0124379a5ef3cd90`).
   - Zero database connections opened; zero live mutations.

10. **Standing Proposal-Dispatch Stop Gate:**
    - Workflow remains parked at `sub_status: "PROPOSAL_PENDING"`, `status: "DRAFT"` behind the owner proposal-dispatch stop gate (`gate: {"scope": "PLAN", ...}`), `next_roles: []`, `plan_granted: false`.
    - Proposer dispatch remains strictly unauthorized.
