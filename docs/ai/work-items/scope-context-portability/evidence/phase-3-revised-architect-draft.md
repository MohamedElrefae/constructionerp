# Rejected result: unapproved draft for inspection only

# Proposed scope-context-portability pilot revision

## Binding and authorization

This proposal covers SCP-R1 through SCP-R7 for execution root `/home/mohamed/frappe-bench/worktrees/scope-context-portability-pilot`. It revises the pilot implementation plan under canonical contract `docs/ai/work-items/scope-context-portability/CANONICAL_PLAN.md`, whose inspected SHA-256 is `93e193cab827f67bbf6cfda794ef51429641e81b30facbbebbfa31eb9dfb2f89`, and incorporates the owner scope amendment dated 2026-09-11.

The supplied starting candidate is `38e04df7b6feeef3acd5a726d98c663da05152ef356eb79195bd45c6858e6db2`, with base commit `4b77803af418cea8459c4cb7d9a0248674845da3`, tree `b72f470db46869199fd9eca2d81fb207ae3515b7`, and an empty change manifest. Candidate archive identity is supplied by the runner, not independently established by this architecture inspection.

Submit this complete proposal for independent plan review. The runner must bind the accepted revised bytes and amended scope to renewed owner PLAN approval. Neither this proposal nor the documentation amendment authorizes builder launch. Implementation begins only through a subsequent owner-controlled builder dispatch with appropriate filesystem permissions. This architecture session remains read-only.

## Scope and operations

Permitted implementation changes are limited to:

- `scripts/ai_context_check.py`: portability, import safety, CLI, recorded results, and failure handling.
- `scripts/lint_scope_metadata.py`: changes only when an offline test demonstrates a relevant gap.
- `tests_offline/`: root conftest, offline tests, and bounded test helpers.
- `docs/ai/SCHEMA_FACTS.md`: only the exact owner-approved documentation correction described below.

All other source, schema definitions, workflow files, checkpoints, approvals, peer results, historical evidence, and the frozen orchestrator remain unchanged. Do not update AGENTS.md or SESSION_MEMORY.md. No external memory/MCP calls, package downloads, Frappe imports, ERP/site operations, tool reconfiguration, commits, pushes, merges, or deployments are authorized.

Source dependencies are repository files, not installed application modules. No operation may resolve into the original app checkout or private ERP storage. Any required input or scratch location that cannot be supplied within the authorized execution boundary blocks the corresponding operation; the builder must not widen that boundary.

## Baseline and SCP-001 disposition

Captured source inspection established:

- The context checker hard-codes the original app checkout, executes checks at module import, and ends with sys.exit.
- Check 8B invokes the schema drift checker without an explicit repository-root argument.
- The metadata linter already uses its script location and a main guard.
- `tests_offline/` does not exist in the inspected execution root.
- SCHEMA_FACTS still records Variation Order as 18 fields and verification date 2026-08-19. Its inspected hash matches historical evidence `baseline-schema-facts`.

The packet supplies historical source-comparison evidence that the unchanged Variation Order JSON has 22 fields, including submitted_by, submitted_at, engineer_approved_by, and client_approved_by. No checker execution is claimed for that evidence or this inspection.

Preserve finding ID SCP-001. The owner amendment removes its documentation-scope obstacle and supplies a remedy; it does not prove the correction has landed or the fresh-copy gate passes. Carry the finding’s remediation into the builder handoff and close the technical mismatch only after independent verification.

## Implementation design and acceptance mapping

### SCP-R1 — Repository-root selection

Use `Path(__file__).resolve().parents[1]` as the default repository root. Resolve an explicitly supplied --repo-root once, with relative overrides interpreted from the invocation directory. Derive every repository input path from the selected root. Remove the hard-coded app path from executable configuration and update the script’s usage example.

Check 8B must invoke the selected root’s `scripts/schema_drift_checker.py` using `sys.executable`, explicitly pass that same root through the drift checker’s supported --repo-root interface, and set cwd consistently. Inspect the local subprocess interface before implementation; do not modify the drift checker. No fallback may read the original checkout.

Acceptance: source assertions and subprocess tests establish the exact default-root expression, override behavior, matching child root/cwd, changed-CWD behavior, and relocation without edits to either checker.

### SCP-R2 — Import safety

Move execution into `main(argv=None)` and functions it calls. Return the integer exit status from main; use the __main__ guard for process exit. Keep results and counters local to an invocation so repeated calls do not accumulate state.

Acceptance: import by file location from outside the app package while trapping subprocess calls, check-input reads, output, and process exit. Import must perform none of those actions. Repeated main calls must report independent results.

### SCP-R3 — Noninteractive CLI and output

Use stdlib argparse for --repo-root, --json, and --help. No prompt, site lookup, --site requirement, or TARGET_SITE requirement is allowed.

Normal output retains understandable section and failure messages. JSON mode emits one parseable JSON object on stdout, containing a schema version, selected root, ordered check records, pass/fail totals, and overall success. Keep subprocess diagnostics inside recorded result details rather than interleaving them with JSON output. Both output modes use the same check execution and result data.

Acceptance: help exits 0 without running checks; successful validation exits 0; recorded validation failures exit 1; argparse usage errors exit 2. Verify clean JSON stdout for passing and failing validation. Invalid or missing repository inputs are validation failures, not successful empty scans.

### SCP-R4 — Preserve checks and record failures

Retain all existing checks and their predicates: core memory files, Git state, BOQ Item invariants, BOQ Structure NestedSet fields, six expected CSS registrations, theme endpoint/function counts, patch paths, expected DocType registry, Check 8B schema drift, CostItem/PlantResource key fields, and ADR minimum count. In particular, preserve the source’s expected 17 endpoints and 33 functions; do not adjust constants from stale narrative counts.

Use bounded input and operation handling to turn missing files/directories, unreadable or undecodable content, malformed JSON, invalid JSON structure, and child-process launch/nonzero failures into attributed FAIL records and exit 1. Validate JSON object/list/field structure before using it. Continue independent checks where possible. Do not expose an uncaught traceback for these expected input failures.

A nonzero drift subprocess status remains a failure. Preserve useful child stdout/stderr as diagnostics while ensuring the parent’s public result remains controlled. Never suppress drift, omit a check, substitute expected data, or add an automatic documentation-update mode.

Acceptance: targeted negative tests for required inputs, malformed JSON syntax and shape, drift success/nonzero/launch failure, and checks whose expected values must remain unchanged. A failing check must remain visible in both text and JSON summaries with exit 1.

### SCP-R5 — Metadata-linter independence

First prove the existing linter works from a changed CWD and from a relocated real copy. Keep it unchanged if those tests and the required negative cases pass. Exercise all five scope dimensions and malformed JSON. If a relevant error-handling or path gap is demonstrated, capture the failure before making the smallest repair within this file. Preserve the existing scope-filter rule and do not broaden the lint policy as an optional improvement.

Acceptance: clean local metadata passes; scope-field violations and malformed inputs fail; location changes do not alter results. Any linter change must identify the test evidence that justified it.

### SCP-R6 — Offline test isolation

Create root `tests_offline/conftest.py` outside the construction package. Establish an early import guard that rejects imports of Frappe and the construction application package, including their submodules, and detects preloaded forbidden modules. Apply equivalent isolation to test subprocesses where needed. Do not stub forbidden imports into apparent success. Load checker modules by file path.

Keep tests and helpers dependent only on stdlib and the provided pytest environment. Cover all five scope fields, malformed and structurally invalid JSON, missing required inputs, drift subprocess handling, changed CWD, relocated copies, root override, import safety, repeated invocation, text/JSON output, help, and exit codes. Use fixtures and mocks for intentional negative cases and subprocess-contract tests; label their evidence as fixture evidence.

Temporary outputs must remain in a runner-authorized scratch area within the execution root and allowed paths. Disable bytecode/cache writes outside that area. Do not write application-package caches or modify real DocType JSON for negative tests.

### SCP-R7 — Real fresh-copy gate

After implementation, the runner must freeze the complete candidate and provision a clean copy at a different absolute path within the authorized execution boundary. Include real repository source, documentation, revised checkers, and tests. Preserve unchanged DocType JSON byte-for-byte. Exclude recursive scratch content, environments, and mutable workflow runtime artifacts.

Check 2 genuinely requires Git metadata. The runner must supply a self-contained Git-backed copy sufficient for the unchanged Git checks, with no external worktree pointers or object alternates. An archive lacking Git metadata is not sufficient. Do not skip Git validation, fake its output, or create an unauthorized commit to make it pass. If provisioning cannot satisfy containment and Git requirements, report the gate blocked.

Use only the provided interpreter `/home/mohamed/frappe-bench/worktrees/scope-context-portability/orchestrator/var/pilot-test-venv/bin/python`. Its packet-authorized use is not permission to inspect or modify the control runtime. No site or installed Frappe/application package may be required; the application source remains present for static inspection.

From the real copied checkout, run these exact validation command arrays with runner-captured command, cwd, timestamps, stdout/stderr, and exit status:

1. `[test_python, "-m", "pytest", "tests_offline/", "-q", "-p", "no:cacheprovider"]`
2. `[test_python, "scripts/ai_context_check.py", "--json"]`
3. `[test_python, "scripts/lint_scope_metadata.py"]`

All three must exit 0. Also capture checker execution by absolute script path from another authorized CWD. Run with site configuration absent and without inherited application paths. Record candidate identity, copied-content hashes, environment isolation, and Git containment. A fixture-only all-pass result cannot satisfy this gate.

## Exact documentation remedy — SCP-R4, SCP-R7, SCP-001

The owner-approved patch identity is SHA-256 `1304761847b019d7adb454ba9a25905d4e06a9539554c4538f1f31fcce4294e2`. Before application, the builder must receive the exact patch bytes through the authorized channel and verify this hash; this architecture session did not inspect those bytes.

Apply only the generated documentation reconciliation for submitted_by, submitted_at, engineer_approved_by, and client_approved_by, the two corresponding Variation Order field counts from 18 to 22, and verification date exactly 2026-09-10. Preserve field ordering, types, options, and flags from unchanged local schema evidence. Do not regenerate using the current date or accept additional generated differences. Do not change DocType JSON or schema_drift_checker.py.

Verify the resulting diff is exactly bounded and unchanged schema inputs retain their hashes. If the supplied patch is unavailable, has a different hash, fails to apply, or changes additional content, stop this operation and report the concrete issue. Do not reconstruct an allegedly identical approved patch from its digest. Check 8B and the fresh-copy gate must subsequently validate the real corrected documentation.

## Design tradeoffs

A shared result collector keeps human and JSON output consistent while retaining the existing predicates. Targeted error handling makes malformed input reviewable without converting failures into passes. Keeping the already-portable linter unchanged unless a test demonstrates a gap minimizes scope. The exact documentation patch reconciles the baseline while preserving drift enforcement. Fixtures provide precise negative coverage; the separate real-copy gate establishes repository portability. Real Git metadata adds a provisioning requirement but preserves Check 2 faithfully.

## Builder handoff and evidence

After independent plan review and renewed owner PLAN approval, a separately authorized builder should verify candidate/input bindings, verify and apply the exact documentation patch, implement the checker changes and offline tests, make only evidence-justified linter repairs, and request runner provisioning of the frozen real-copy validation gate.

Return a requirement-to-evidence mapping for SCP-R1 through SCP-R7, the complete allowed-path diff, patch hash verification, unchanged-schema hash evidence, fixture test results, and separate real-copy command evidence. Preserve SCP-001 until its technical verification is accepted. New genuine baseline blockers receive finding_id null for runner assignment; do not manufacture findings or weaken checks to achieve green output.

Independent verification uses a distinct identity/session and the frozen candidate, without peer verdicts. Existing Phase 1/2 evidence remains historical and unchanged. This revision requires new pilot evidence but does not authorize historical reruns. Optional improvements go to backlog; unresolved scope/design disagreements go to the owner. No commit or release operation is part of this handoff.
