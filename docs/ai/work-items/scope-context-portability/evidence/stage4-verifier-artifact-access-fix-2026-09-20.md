# Stage 4 Verifier Artifact Access Fix (2026-09-20)

## Result reached

With the finding-reconciliation fix, the independent panel returned **PASS / PASS / PASS**
and `compose_and_store_bundle_and_payload` succeeded (`BUNDLE_VALIDATED`). This is the
first time the Stage 4 proposal and panel gates have fully passed.

## Problem

The Stage 4 verifier failed with `EVIDENCE_UNAVAILABLE`. Its job packet mounted only the
private output directory and the plan; it had **no read-only access** to the frozen
proposal, the review bundle, or the import payload it is required to verify. The verifier
correctly refused to pass an unverifiable bundle.

## Fix

For `role == "verifier"` on a `stage4-proposal` candidate, `_prepare` now verifies and
mounts the frozen proposal, bundle and payload read-only under
`/tmp/workspace/private_inputs/`, plus a `verifier-manifest.json` binding each artifact to
its candidate SHA-256. A Stage 4 verifier stage instruction tells the verifier to check
hashes, 81-identity coverage, bundle/payload consistency, and panel bindings — and never
to re-review translation quality or authorize ERP mutation.

## Verification

Full orchestrator suite: **225 passed**. No ERP mutation, DRY_RUN, IMPORT, commit, push,
or merge.
