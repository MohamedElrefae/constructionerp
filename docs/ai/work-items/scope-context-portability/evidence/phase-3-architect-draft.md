# Unapproved architect draft — blocked on scope decision

# Proposed offline portability pilot plan

Status: proposed for independent plan review; blocked for build pending the baseline decision below. This proposal does not authorize implementation or change the dispatch scope.

## 1. Binding inputs and boundaries

Work item: `scope-context-portability`; architectural dispatch stage: `1`; canonical technical scope: Phase 3 offline pilot.

Execution root: `/home/mohamed/frappe-bench/worktrees/scope-context-portability-pilot`.

Reviewed contract: `docs/ai/work-items/scope-context-portability/CANONICAL_PLAN.md`, SHA-256 `93e193cab827f67bbf6cfda794ef51429641e81b30facbbebbfa31eb9dfb2f89`.

Candidate: `38e04df7b6feeef3acd5a726d98c663da05152ef356eb79195bd45c6858e6db2`; base commit `4b77803af418cea8459c4cb7d9a0248674845da3`; tree `b72f470db46869199fd9eca2d81fb207ae3515b7`. The packet manifest contains no pilot changes. Local HEAD/tree and unchanged checker source agree with that baseline; the archive itself was not supplied for independent hashing.

Current permitted future edit paths remain:

- `scripts/ai_context_check.py`
- `scripts/lint_scope_metadata.py`, only for a demonstrated relevant gap
- `tests_offline/`

This architectural session permits read-only inspection and stdout results only. Future implementation and test-created files require a separate owner-controlled builder dispatch with effective write permission. Keep all other files unchanged, including the orchestrator, workflow controls, approval records, historical evidence, documentation and application schemas. Do not access the original ERP checkout, call external memory services, import Frappe, perform site operations, install packages, or commit/push/merge/deploy.

## 2. Blocking baseline decision — SCP-R4, SCP-R7

The real baseline contains schema-facts drift. `docs/ai/SCHEMA_FACTS.md:34` and its Variation Order table at line 574 record 18 fields. The actual JSON defines 22 fields; the additional definitions start at lines 77, 84, 109 and 132: `submitted_by`, `submitted_at`, `engineer_approved_by` and `client_approved_by`.

`scripts/schema_drift_checker.py:126` renders each field, and its comparison at line 249 reports failure when the rendered document differs. Check 8B must continue to propagate that failure. Portability changes alone cannot satisfy the all-pass real-copy gate.

Recommended owner resolution: authorize a separate, narrowly scoped correction of the current schema-facts document after reviewing the intended four additions, then provide a newly frozen baseline and updated bindings for renewed plan review and approval. That correction is not part of the presently allowed builder work. It must preserve historical Phase 1/2 evidence and must not roll back application fields merely to obtain a green checker.

Alternatively, the owner may explicitly revise the scope to include that document and submit the revised contract for independent review. Until an authorized resolution arrives, SCP-R7 remains blocked. Never skip Check 8B, reinterpret drift as success, regenerate documentation during checks, or substitute a synthetic repository for the real-copy gate.

The existing theme count is not a blocker: inspected source contains exactly 17 whitelist decorators and 33 top-level functions. Preserve these expectations.

## 3. Context checker architecture — SCP-R1 through SCP-R4

### Root selection and drift subprocess — SCP-R1

Use `Path(__file__).resolve().parents[1]` as the default repository root. Resolve an explicit `--repo-root` override once and derive every repository path from the selected root. Relative overrides resolve against the invocation CWD; the default never depends on CWD. Remove the old absolute root, including misleading usage examples.

Execute Check 8B using the selected repository's own `scripts/schema_drift_checker.py`, with `sys.executable`, an argument list and `cwd=selected_root`. The helper already derives its root from its own file location and accepts only `--update`; do not pass an unsupported `--repo-root` flag. Propagate the selected root through both the absolute child-script path and its CWD. Test that the actual child reads the selected copy's inputs. Never pass `--update`.

If that interpretation of root propagation is rejected during independent review, return to architecture: adding a new CLI option to the helper would require a scope revision. Do not introduce a wrapper that rewrites the helper's globals.

### Import safety and execution state — SCP-R2

Move execution into `main(argv=None) -> int`, with `sys.exit(main())` only inside the `__main__` guard. Importing defines functions and constants but performs no checks, subprocess calls, argument parsing, output or exit. Keep results and counters local to each run so repeated calls cannot accumulate prior failures.

### CLI and reporting — SCP-R3

Use argparse for `--repo-root`, `--json` and `--help`. No prompting, site argument or `TARGET_SITE` dependency. Exit 0 for successful checks and help, 1 for recorded check/input failures, and 2 for argparse usage errors.

Human output remains the default. JSON mode emits one JSON object containing the effective root, ordered check records, PASS/FAIL/INFO statuses, explanatory messages, totals and overall success. Child output must not corrupt JSON stdout. Tests assert outcome semantics and structure rather than incidental punctuation or Git commit counts.

### Preserve checks and failures — SCP-R4

Retain all existing check groups: core memory files; Git branch/commit/count; BOQ Item required and forbidden fields; BOQ Structure NestedSet fields; the six required CSS registrations; exact theme API counts; required patch paths; expected DocType folders and unexpected-folder failures; schema-facts drift; CostItem/PlantResource key fields; and the ADR minimum.

Preserve the known nonmatching JSON filenames `costitem/cost_item.json` and `plantresource/plant_resource.json` in Check 9. Additional patch versions remain permitted; unexpected DocType folders remain failures.

Validate required JSON container and field shapes, and handle missing files, decoding failures, unreadable paths and malformed required input as clear recorded failures. Continue independent checks where practical. A malformed input must not produce a successful empty scan. Handle Git and drift-child launch failures and nonzero exits without an uncaught traceback. Report a concise child-failure diagnostic rather than reproducing a traceback as normal checker output. Do not catch an error and silently omit its check.

Keep the exact drift-document comparison delegated to the existing helper. Do not duplicate its schema renderer in production code or soften its result.

## 4. Metadata linter — SCP-R5

First prove the existing implementation's behavior with offline tests. Invoke its absolute script path from a different CWD and invoke a relocated copy against that copy's metadata. Prove import safety and verify scope violations and malformed JSON produce the documented failure outcomes.

Leave the linter unchanged if these required behaviors pass. If a relevant failure is demonstrated, capture the failing test and make the smallest repair inside the allowed file while preserving the existing rule for truthy `in_standard_filter` values on the five scope dimensions.

The current filename convention skips the CostItem and PlantResource schema files. Inspection found no scope fields in those two files, so this is not a present fresh-copy blocker. Broader discovery changes belong in backlog unless independently justified as necessary for the approved requirements.

## 5. Offline tests — SCP-R6

Create a repository-root `tests_offline/` directory with its own `conftest.py`, outside the application package. Do not add an application import or fake Frappe module to make collection succeed.

Load checker modules directly by file path. Install an early import guard that rejects `construction`, `frappe`, `erpnext` and their submodules before module execution; fail if they were already loaded. Include a controlled test demonstrating that the guard rejects an attempted import without executing the package initializer. Child-process tests must also establish that the scripts work in the supplied environment without those packages.

Cover these cases:

- Every scope dimension violates the linter rule when enabled; permitted fields and disabled filters pass.
- Malformed JSON syntax and the context checker's malformed JSON shapes produce recorded failures and exit 1 without traceback.
- Missing required files/directories cannot produce success.
- Drift child success, nonzero exit, stderr diagnostics and launch failure map to the correct parent outcome.
- The real drift helper uses the selected root; a fixture-only fake child can verify argv/CWD plumbing but cannot prove helper compatibility.
- Changed CWD, default root discovery, explicit root override, and a copy at a different absolute path use the intended inputs.
- Importing each checker performs no checks, output or exit; repeated context-checker calls have independent results.
- Human/JSON success and failure exits, help, unknown options and missing option values follow the CLI contract.
- Existing check groups retain meaningful negative cases, including forbidden BOQ fields, registry drift and theme-count mismatch.

Synthetic repositories may contain deliberately missing or malformed inputs to test failure behavior. Label them as fixtures. Keep fixture outputs separate from the genuine candidate-copy gate. Test scratch directories must be explicitly permitted by the builder dispatch, remain within its allowed roots, and must not recursively copy themselves.

## 6. Real fresh-copy acceptance — SCP-R7

This gate remains pending until the baseline conflict is resolved and an authorized builder candidate is available.

The owner-controlled runner must supply a clean copy of the complete frozen candidate at a different absolute path, along with permission to execute there. Do not silently use an external temporary root from the present dispatch. Copy real repository inputs byte-for-byte; do not install synthetic schemas, fake executables, corrected fixture documentation or stub drift helpers into the gate copy.

Preserve usable, local Git metadata for Check 2. A worktree `.git` pointer back to the original checkout is insufficient isolation; a Git-free archive cannot satisfy the preserved Git check. The runner must provision an isolated copy with genuine Git metadata without asking the architect or builder to create a commit. Record candidate content identity separately from the local Git checkout status.

Use the provided interpreter:

`/home/mohamed/frappe-bench/worktrees/scope-context-portability/orchestrator/var/pilot-test-venv/bin/python`

From the fresh copy, capture these exact validation commands in native events:

1. `<test_python> -m pytest tests_offline/ -q -p no:cacheprovider`
2. `<test_python> scripts/ai_context_check.py --json`
3. `<test_python> scripts/lint_scope_metadata.py`

Record command argv, effective CWD, candidate identity, environment isolation, exit code and captured output. Remove inherited site and app-path settings; use no downloads, site configuration or Frappe/application imports. Disabling bytecode and unrelated pytest plugin autoload is acceptable and must be recorded. Git remains an existing external executable used by the preserved checker.

All three commands must exit 0. Fixture tests passing while a real checker fails is a failed gate. Missing writable scratch space, isolated Git metadata, interpreter access or captured evidence blocks validation; do not simulate success.

## 7. Design tradeoffs and evidence impact

Keep the drift checker unchanged and select its physical copy to preserve its existing interface and scope. This requires a complete repository copy for root-override tests and the real gate.

Use per-run structured records to support both output modes without duplicating check logic. Preserve exact existing expectations rather than replacing them with permissive thresholds.

Use fixtures for deterministic negative tests and the full copied candidate for acceptance. These provide different evidence and cannot replace each other.

No builder evidence was supplied. Historical workflow evidence remains historical and unchanged. An authorized schema-facts correction changes the candidate baseline and requires renewed affected review; current source observations remain attributable to the original candidate but do not prove the revised candidate passes.

## 8. Builder handoff and completion criteria

Independent plan review and the owner baseline decision come first. The runner must freeze the accepted revised plan/scope and obtain the renewed owner PLAN grant. A builder may begin only after receiving a separate owner-controlled dispatch bound to those inputs and with sufficient permissions.

The builder then implements the context-checker refactor, adds offline tests, changes the metadata linter only for an evidenced relevant gap, and runs the authorized validation commands. Return the allowed-path delta, requirement-to-test mapping, unresolved findings and captured evidence references. Any unexpected baseline failure returns for classification; do not widen scope or edit documentation to hide it.

A separate verifier session reviews the frozen implementation and real-copy evidence without receiving peer verdicts. Completion requires SCP-R1 through SCP-R7 to be satisfied, no unresolved blocking findings, and verified preservation of all out-of-scope files. Commit, push, merge, deployment and ERP actions remain outside this handoff.
