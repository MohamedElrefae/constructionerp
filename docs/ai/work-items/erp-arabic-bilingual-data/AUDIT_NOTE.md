# Audit Note: Stage 4 Contract & Privacy Corrections (Canonical Plan §11)

## 1. Commit Provenance and Lineage

- **Historical Base Commit:** `72da63dc693e320ea8b73d5bdf7000c4fda57f07` (Verified Phase 3 Pilot).
- **Intermediate Synchronization Commit:** `50a40562eaf7ec6db29901cb07829bfda144ff61`
  - Captured initial working tree synchronization and Phase 3 pilot evidence records without rewriting any historical Phase 1–3 audits.
  - Retained unmodified as the immediate parent of the corrective implementation commit.
- **Current Corrective Commit:** Follow-up commit on branch `feature/scope-context-portability`.
  - Implements the Project Owner's directive: `MILESTONE PLAN DIRECTIVE: APPROVED FOR CORRECTIVE IMPLEMENTATION`.

## 2. Core Corrective Invariants Enforced

1. **Preallocated Private Artifact IDs & Path Rejection:**
   - The engine preallocates each private `artifact_id` in the job packet (`stage4-proposal-<job_id>`, `stage4-review-<role>-<job_id>`).
   - Agent-selected IDs and all returned paths/symlinks are rejected unconditionally.
   - Output files are captured strictly through orchestrator-controlled neutral mount points (`/workspace/private_output/output.json`).

2. **Untrusted Native Result Data & Verified Durable Events:**
   - Native result data is treated as completely untrusted.
   - Raw proposal rows, row decisions, bundle data, and payload data are NEVER stored in `state["candidate"]`, durable SQLite events, or repository work-item directories.
   - Durable SQLite events record only orchestrator-verified metadata under `verified_private_artifacts`, `proposal_sha256`, `bundle_sha256`, `payload_sha256`, and counts (`81`).

3. **Pure State Transition Routing (`routing.py`):**
   - `apply_event()` performs zero filesystem I/O.
   - State advances purely from verified metadata in durable events.
   - Content-addressed blob storage, validation, and bundle composition are managed exclusively in `Engine` prior to event emission.

4. **Content-Addressed Private Storage:**
   - Private blobs reside in `private_root/blobs/<sha256>.json` with mode `0o700` directories and `0o600` files.
   - Reads verify content SHA-256 against the filename digest.
   - Temporary job outputs (`output.json`) are unlinked immediately upon validation.

5. **Sandbox Isolation:**
   - Host `private_root` is masked via `--tmpfs`.
   - Neutral read-only mounts (`/workspace/private_inputs/...`) ensure reviewers cannot inspect peer reviews or unauthorized catalogs.

6. **Proposal & Review Validation:**
   - Enforces exact 81 identities, English catalog matching, `is_group` boolean matching, non-empty Arabic text, and semantic proposal hash equality.
   - Sanitize error messages: exceptions and pause reasons never interpolate raw account names or values.

7. **Fail-Closed Offline Network Isolation:**
   - Offline validation enforces `--unshare-net` unconditionally; probe fails closed before launching child commands if namespace unsharing is unavailable.

8. **Deterministic Checkpoint-Projected State Export:**
   - `exported_utc` in `STATE.json` is derived directly from durable SQLite events (or `initialized_utc`), ensuring bit-for-bit repeatability across read-only queries (`status`, `run`, `export`).

9. **Zero Mutation to Production Assets:**
   - Production checkout `/home/mohamed/frappe-bench/apps/construction` remains identical to accepted Phase 3 state (`apps_construction_manifest_sha256 = f538d7d10d9600d7d88aec64648a5e72d84615bd26afc0c332db8569dbb94b4e` across 1,616 files).
   - Zero database connections opened; zero live mutations.

10. **Stop Gate Standing Invariant:**
    - Workflow remains parked at `sub_status: "PROPOSAL_PENDING"`, `status: "DRAFT"` behind the owner proposal-dispatch stop gate (`gate: {"scope": "PLAN", ...}`), `next_roles: []`, `plan_granted: false`.
    - Proposer dispatch remains strictly unauthorized.
