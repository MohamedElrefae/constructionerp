# Native Stage 4 DRY_RUN Adapter (2026-09-20)

## Purpose

Implement and qualify the dedicated native DRY_RUN adapter required by Canonical Plan
§D4 "Migration execution" step 1, before any ERP import mutation.

## Implementation

`orchestrator/dry_run.py`:
- Reads Account records through a read-only Frappe console (`bench --site <site> console`)
  and never calls insert/save/rename/delete; `frappe.flags.ignore_permissions` only for
  reads.
- Reports: missing parents, duplicate codes, blank names, unexpected current values,
  stale rows and approval gaps.
- Returns a deterministic evidence digest over the observed summary plus the SHA-256 of
  the planned payload values.
- Writes `dry-run-evidence.json` under the runtime.

Engine and CLI:
- `Engine.execute_dry_run()` runs the owner-authorized read-only operation, records a
  `dry_run_evidence` event and advances to the IMPORT authorization gate on success or
  pauses `DRY_RUN_FAILED` on blocking findings.
- Routing handles `dry_run_evidence` explicitly in the `DRY_RUN` sub-status.
- CLI: `run --dry-run`.

## Qualification

- Offline tests: `orchestrator/tests/test_dry_run.py` (6 tests) cover clean payloads,
  stale/missing/blank rows, unexpected current values, duplicate codes, approval gaps,
  deterministic digest binding and descriptor validation.
- Live read-only smoke test against `v16.localhost`: 81/81 identities present, 2097 total
  accounts, zero blocking findings, digest `acec01b23ae8434b…`.
- Full orchestrator suite: **231 passed**.

## Boundary

The dry run performs no mutation. The write/import path remains a separate authorization
and is not implemented here. No ERP data was modified.
