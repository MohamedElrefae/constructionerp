# PR #11 lint and review corrections

The configured all-files pre-commit run failed on the consolidated integration source. The correction applies the repository's pinned Ruff 0.8.1 import/format rules and Prettier formatting, removes unused lint suppressions, updates equivalent Python expressions, and fixes the missing dashboard logger import. No hook is disabled or excluded. JavaScript task inspection now asks the run-status observer to poll through a DOM event, keeping its polling state inside its existing initialization scope.

The GitHub-hosted Codex review of `9fcf99c` identified three additional defects. Commit-response replays now require the same task and operation. Plan-approval replays also require the same operation and a stable digest of the reviewed approval, excluding generated token IDs and issuance timestamps. Unregistering a task clears its direct-run records while preserving other tasks' records. Authenticated API and coordinator regression tests cover these cases.

The all-files formatter also reflowed the existing layout permission condition. Its Python AST is identical before and after formatting. The three formatted client assets have cache-version bumps; their behavior is unchanged. Review-ledger renewal is limited to the layout API guard digest, the existing hooks.py guard digests and their canonical source manifests. Permission records, decisions, tests, prior review evidence and strict rejection behavior remain unchanged. This is source equivalence verification, not new native permission or business acceptance.

Installed dashboard startup tools pin source hashes. Synchronizing these formatted operational scripts locally requires renewing only those existing source pins after reviewing equivalent code; it does not authorize bypassing startup admission, resetting state or enabling production dispatch.

The dashboard and orchestrator remain integration work in progress. This lint correction is not a production release approval.

## Local verification

- All configured pre-commit hooks passed, including Ruff import sorting/lint/format, Prettier, ESLint, syntax/metadata checks.
- Authenticated API regressions: 22 passed. Coordinator state/cleanup: 35 passed. Synthetic authenticated dashboard-to-engine route: 14 passed.
- Exact pinned Frappe Semgrep rules plus the workflow's Python correctness rules: five findings matched the existing reviewed ledger, zero unresolved findings or scanner errors.
- Schema facts and all 12 context checks passed in the review checkout. Candidate namespace tests passed 14 cases using the system interpreter available inside their sandbox.
- Broader module-by-module checks are supplemental. Some historical harnesses require `/opt/base-fixture`, `/opt/dash-deps` and additional import paths that are absent on this host; those invocations did not pass and are not release evidence. Combined collection also changes global environment, so focused modules were verified separately.
- Local source-only localization checking reached only missing sibling Frappe/ERPNext checkouts in the temporary review directory; the hosted workflow supplies its pinned sibling trees. Hosted results must be checked on the pushed revision.
