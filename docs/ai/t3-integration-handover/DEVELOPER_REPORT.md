# T3 integration — development handover

**As of 17 November 2026. Status: review candidate, production dispatch disabled.**

## Intent and implementation

Integrate the existing engine with dashboard task controls and T3, preserving the engine's candidate and validation workflow. This candidate contains bounded builder source/result packets, receipt-bound result intake, linked task-worktree application, existing engine validation and candidate freeze/recheck, plus dashboard and supervisor seams. The managed-service and installer files are candidates; the installer remains explicitly disabled. Do not infer production isolation from fixture tests.

## Evidence and limits

A disposable direct dashboard API `run` test dispatched a synthetic builder through the existing Engine and a same-user test supervisor to T3. The resulting change was collected and accepted after an offline Python assertion passed. The configured T3 model was Codex `gpt-6-luna`; the executed-model identity was not independently reported. Collection occurred through the Engine. This was not the live authenticated production route.

A separate authenticated dashboard suite passed 14 tests against a synthetic Git repository, simulator and test-injected launcher. The public-based review candidate passed 80 supervisor/builder/attestation tests and 21 subtests, with 3 skips; 51 engine tests passed; and 40 service-unit/verifier tests with 8 subtests passed. These checks are not production service attestation. Other existing application and site-specific features require their own validation. There is no claim that all suites passed.

## Production work remaining

1. Review this change set against the target branch and existing local work; preserve unrelated changes. Inspect generated files, source paths and security-sensitive changes. Validate the exact resulting revision.
2. Select the minimum supportable trust boundary and working provider. The existing managed candidate requires separate accounts, systemd services and host attestation; those were not installed or verified at this snapshot. Its disabled installer accepts OpenCode/OpenCode Go, not the working desktop Codex route. Do not bypass the gate or expose credentials to bridge this gap.
3. Prove authenticated dashboard dispatch, real result collection, candidate application and engine validation with a disposable project. Include duplicate, interruption, uncertain result, invalid output and recovery cases; preserve customer data and existing task work.
4. Complete host identity and service security checks for the selected design, verify startup and recovery, and document deployment and rollback. Run security review, secret scanning and relevant application/browser/site tests before a production release.

The builder packet currently has small UTF-8 file and total-size limits and does not support general delete/rename operations. Model output is untrusted data; approvals and workflow state remain controlled by the engine. Separate prototype files are not independent proof of production behavior.

This report deliberately excludes local credentials, private runtime data, transcripts, site data, backups and machine-specific evidence paths. External agents should work from the reviewed repository revision and record new evidence without checking secrets or customer data into Git.

## Consolidation update

The reviewed integration is now merged into the actual bench app on a local consolidation branch, after preserving its existing application work. The public continuation branch remains the sanitized sharing branch; the local branch contains private history and must not be pushed to that public destination. Operational source now lives in `dashboard/operations`; the running UI remains a separate immutable installed snapshot. Earlier standalone contract/enrollment/projection source was recovered and separately tested (314 passed, 3 explicit expected failures for a missing legacy API). See [the consolidation record](CONSOLIDATION.md) for source, archive, runtime and test boundaries. This is source consolidation, not a production deployment.
