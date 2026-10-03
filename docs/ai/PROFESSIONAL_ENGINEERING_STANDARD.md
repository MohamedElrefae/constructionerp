# Construction ERP — Professional Engineering Standard for AI Agents

**Owner:** Mohamed Elrefae

**Established:** 2026-10-04

**Applies to:** Future review, development, debugging, maintenance, and release sessions in this repository.

**Current release assessment:** [Customer release gaps](CUSTOMER_RELEASE_GAPS_2026-10-04.md)

## 1. Consultant's recommendation to the owner

Keep the existing Frappe/ERPNext foundation and build a disciplined engineering process around it. Your construction knowledge is a substantial part of the product's value. AI can help implement it, but professional quality depends on explicit business rules, verifiable behavior, controlled changes, and reliable operation.

The app currently combines strong practices with important correctness and verification gaps. It can continue growing; it should not be represented as comprehensively production-ready until the release gaps for the sold capabilities close. Avoid a wholesale rewrite, a new framework, or more infrastructure unless a concrete requirement and evidence justify it.

Use this standard for daily work. Use the companion gap report to prioritize stabilization. For commercial calculations, security boundaries, data migrations, and the first customer release, arrange qualified technical review in addition to your domain approval. A second AI review can improve coverage, but it does not establish human review or transfer operational responsibility.

Professional development does not mean applying the heaviest process to every small change. It means using the level of evidence appropriate to the consequence of being wrong.

## 2. Authority and how to apply this document

This is the owner's reusable engineering instruction set. `MUST` means a required behavior within the authorized task; `SHOULD` means the default unless a documented reason supports another choice. The current user's explicit scope and preferences, and higher-priority platform instructions, take precedence. Existing scoped architecture decisions and governed workflows remain applicable; this guide does not grant production access, a commit/push, or a migration authorization.

This guide refines broad examples in [AGENTS.md](../../AGENTS.md) and [coding patterns](CODING_PATTERNS.md). A template is not a complete secure implementation. In particular:

- Whitelisting exposes a callable method; it does not establish document authorization.
- Parameterized SQL prevents value injection; it does not enforce permissions, scope, or business relationships.
- `read_only` on a form is not a server-side commercial integrity rule.
- Direct database writes are exceptions requiring a reason and invariant coverage, not a general substitute for saving business documents.
- Use `!important` where an existing Frappe override genuinely requires it; do not add it to every new style.
- Dual-version support is a requirement to verify against a declared matrix, not a fact established by copying compatible-looking selectors.

Follow [AGENT_WORKFLOW.md](../../AGENT_WORKFLOW.md) when the task belongs to its governed workstream. Verify its current state against the relevant work-item evidence and owner grants. Do not invent approval, quorum, independent verification, or a successful native execution. Do not start extra agent sessions unless the user or applicable workflow authorizes them.

For workflow changes or integration of these standards into agent execution, read the [future development workflow review](FUTURE_DEVELOPMENT_WORKFLOW_REVIEW_2026-10-04.md). It reconciles the August proposal, legacy active plans, and the older controller worktree with current implementation. Its work packages are recommendations, not approved contract amendments. Ensure this standard reaches each role through the applicable versioned, read-only context mechanism; a link in the main checkout alone does not distribute it to older worktrees or sandboxes.

If a task requires a new business decision, ask a concise question while completing independent authorized work. Routine engineering choices and already authorized actions do not need repeated owner confirmation. If a rule blocks an action, identify the exact rule and concrete action; prepare the reviewable result before seeking approval for its final gated step.

## 3. Required startup in every session

Before editing:

1. Read the required files listed below from the actual task checkout. Read scoped instructions, accepted architecture decisions, and the applicable work-item documents.
2. Run the startup commands below before planning or editing. Inspect branch, HEAD, and working-tree status, including staged and untracked files. Preserve unrelated modifications. Assume another active task may be using the same workspace.
3. Restate the user's intended outcome and identify the affected routes, DocTypes, services, client assets, reports, and tests. Use live source and installed metadata to confirm facts; do not trust stale counts, memory, or generated plans as authority.
4. Classify the change using section 4. If it touches money, approval history, permissions, migrations, imports, or global framework behavior, read the relevant open release gaps.
5. Identify the environment and named site before any site command. Never assume the default site is disposable or that `v16.localhost` is always safe merely because past work used it.
6. Give the owner a short update explaining the intended result, known constraints, and how the result will be verified.

### Required files and planning references

| File, relative to the actual repository root | Startup requirement |
| --- | --- |
| `AGENTS.md` | Read every session, including applicable scoped instructions. |
| `docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md` | Read every session. |
| `SESSION_MEMORY.md` | Read the current relevant work, blockers, decisions, and handover; confirm dated claims against source. |
| `docs/ai/CONTEXT_INDEX.md` | Read to locate the repository's context and authority references. |
| `docs/ai/SCHEMA_FACTS.md` | Read the summary and schemas relevant to the task; verify them with the schema checker. |
| `AGENT_WORKFLOW.md` | Read to determine whether governed workflow rules apply; read the relevant contract/state/evidence when they do. The legacy path `docs/ai/AGENT_WORKFLOW.md` does not exist. |
| Applicable work-item plan and planning template | For planning/building tasks, read the current plan and applicable existing role/template. `docs/ai/templates/PLAN.md` does not exist; do not report reading it. Governed architect packets use their approved role and the existing `docs/ai/templates/inbox-architect.md`. This is a role packet template, not a generic replacement PLAN document. |

Record a concise **Files Read** list with actual paths and relevant sections in the work-item handover or session notes. List only files actually read. If required context is missing or unavailable in a sandbox, record the problem and obtain it through the approved context mechanism before dependent work; do not silently use another checkout's older instructions.

### Required startup commands

Run from the **actual task repository root**, which can be a feature worktree rather than the main app checkout:

```bash
git rev-parse --show-toplevel
git status --short
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
git rev-parse HEAD
python3 scripts/schema_drift_checker.py
python3 scripts/ai_context_check.py
```

The short commit is useful for communication; retain the full commit and working-tree status with verification evidence. Inspect relevant staged and unstaged diffs and affected untracked files: HEAD alone excludes unfinished changes. If `python3` cannot run these local checkers, use the documented compatible interpreter for this checkout and report that interpreter and actual result. Do not install dependencies or initialize a workflow merely to perform startup inspection.

If either checker fails, explain the drift or environment problem and resolve it within the task's authorized scope before relying on those facts. Unaffected investigation may continue. Do not run the schema checker's `--update` merely to hide a discrepancy; regenerate facts only after reviewing the intended schema changes. Record command, outcome, and exit status; a command that did not run is not a pass.

These commands establish the **local checkout baseline** and compare selected facts with repository files. They do not prove this branch contains the latest remote commits, that the installed database matches DocType JSON, or that business behavior is correct. For integration/release work, also identify the intended base/upstream and any divergence using the existing refs, obtain fresh remote refs when authorized and necessary, and inspect the intended site's installed versions/metadata through authorized checks. Do not automatically pull, reset, migrate, or switch a shared checkout to make it "latest."

Recheck Git status and HEAD before final verification/handover. If concurrent work changes the base or affected files, inspect the change and repeat only the checks whose evidence it invalidates. Report the final verified baseline.

### Applying startup inside governed agent jobs

When the coordinator supplies valid candidate-bound `engineering-startup/v1` evidence, use its recorded Git baseline and checker results for startup. Read the supplied immutable context snapshots at their packet paths and identify them by their original relative paths. Record the check results as **coordinator-executed**; do not claim that your role personally ran them. The coordinator verifies these bindings before dispatch and result acceptance. Additional task-specific business verification remains required.

Core instructions (`AGENTS.md`, this standard, and root `AGENT_WORKFLOW.md`) remain fixed for a governed task. Factual context (`SESSION_MEMORY.md`, `SCHEMA_FACTS.md`, and `CONTEXT_INDEX.md`) may be updated only when each exact path is explicitly included in the approved write scope. A broad wildcard does not provide that exception. Each role still receives an immutable snapshot, and changed factual context requires fresh coordinator checks for the resulting candidate. Do not edit the read-only snapshots or approval state.

Repository facts that deserve special attention:

- `BOQ Item.cost_item` is free-text Data, not ERPNext `item_code` or `item_name`. Confirm the actual DocType schema before adding fields or queries.
- Scope dimensions include company, project, cost center, department, and branch where applicable; validate actual relationships, not just nonempty strings.
- VFC is the established form layout path. The React modern-form API is deprecated and restricted; do not build a parallel form engine by accident.
- The existing local environment uses Python 3.14; code conventions also require Python 3.10-compatible quote nesting. A customer's supported runtime must follow the declared Frappe/ERPNext compatibility matrix.
- Other tasks may have unfinished changes. Do not treat another task's files as yours or declare them release-ready without its evidence.

Keep repository findings, secrets, customer records, and diagnostic dumps local unless an external destination and scope are authorized. External memory is a cache, never authority. If an external memory write is rejected or unavailable, use local session notes and report the limitation where relevant; do not retry through a different transport to evade the decision. Inspect automatic Git hooks before any authorized commit because they may transmit metadata.

## 4. Choose verification according to risk

| Change | Minimum useful verification | When to broaden it |
| --- | --- | --- |
| Documentation or isolated cosmetic adjustment | Diff, links/content checks, and visual inspection where applicable | If a functional interaction or registered asset changes |
| Ordinary business field or feature | Focused unit/integration checks, relevant document lifecycle, actual persistence/reload | If multiple routes or reports depend on it |
| Commercial calculation or approval | Independent worked examples; failed-before regression; real-site transition, rollback, and retry tests | Shared aggregates require real concurrency checks |
| API, report, scope, file access | Allowed and denied real-user requests; input bounds; no sensitive output | Broaden across equivalent REST/import/export paths |
| Schema, data patch, permissions setup | Clean install/upgrade, repeated migration, preservation checks, recovery plan | Legacy duplicates and destructive transformations require dedicated fixtures/review |
| Framework override, global asset, dependency upgrade | Relevant native UI/API regression on supported versions; reproducible build | A global change requires broader smoke coverage |
| Customer release | Complete offered workflow, security, upgrade, workload, and restore evidence for one candidate | Required across every advertised deployment/version combination |

Do not write tests that only restate the implementation, assert incidental source strings, or create maintenance burden for reversible low-impact edits. Do write meaningful regression tests for defects and invariants. Once appropriate checks pass, repeat or broaden them only because a new change, failure, or unresolved risk justifies it.

## 5. Define the business contract before implementing a feature

For a feature affecting commercial or transactional state, record:

```text
User and intended outcome:
Inputs, units, currency, precision, and size limits:
Source of truth and derived fields:
Allowed roles, document permissions, and scope behavior:
Valid states and transitions; immutable fields after approval:
Expected result with a worked example:
Zero/missing/invalid values and boundary behavior:
Retry, concurrent requests, failure, cancellation, and reversal:
Affected forms, APIs, imports, reports, prints, and exports:
Acceptance checks and customer-visible behavior:
```

Keep this brief for a simple feature. Do not silently decide an owner's commercial policy while fixing a technical bug. Current decisions include factor-zero meaning, cancellation fallback, margin layering, active scope meaning, supported versions, delivery model, capacity promise, and backup/recovery targets.

For calculations, the owner should supply or approve small independent construction examples. These examples become acceptance fixtures. Agent-produced expected values copied from the same formula are weak evidence. Technical choices such as helper names, local refactoring, and parameter binding remain the agent's responsibility.

## 6. Architecture and maintainable implementation

MUST trace the complete feature path before changing it: browser action → actual request → authorization → service/controller → database effects → response/reload → report/export consumers.

SHOULD keep transport endpoints small and put reusable domain operations in focused services. DocType controllers must enforce lifecycle invariants that apply to ordinary document saves, REST, imports, and internal callers. A safe custom endpoint does not protect an unsafe standard document route. Reuse domain rules instead of copying formulas into each layer; avoid circular services and competing implementations.

Prefer a cohesive, readable Frappe app over unnecessary microservices, new frontend frameworks, or a large abstraction layer. Extract a helper when it represents a stable business rule, removes meaningful duplication, or enables useful testing. File length is a warning to inspect responsibilities, not a reason to split every function.

MUST preserve public contracts unless changing them is part of the task. Validate caller-controlled fields with an explicit allowlist; do not feed an arbitrary payload into privileged document updates. Name variables by their domain meaning and unit. Add comments explaining policy or constraints rather than narrating obvious code. Remove newly introduced dead code/debug output, but avoid unrelated cleanup during a defect fix.

Keep work reviewable: localized changes, small logical work packages, explicit imports, clear errors, and documentation of any interface or architecture change. Do not introduce a second implementation merely because an agent did not discover the existing service.

## 7. Frappe document lifecycle and writes

Use supported controller methods and hooks for the installed framework. Verify actual invocation order in local Frappe source when an invariant depends on it. On the inspected implementation, `on_trash` runs before row deletion and `after_delete` runs afterwards. A declaration in `hooks.py` alone does not prove an event is called; inspect the controller too before declaring a missing guard. [Hooks documentation](https://docs.frappe.io/framework/user/en/python-api/hooks)

MUST distinguish a custom `status` field from Frappe `docstatus` and submission rules. Implement the chosen transition policy on the server. Validate relationships against authoritative documents and derive protected identifiers/approval actors from trusted state. Do not accept a browser's claim that an item belongs to a company, project, header, or approved operation.

Use normal document `insert`, `save`, `submit`, or `cancel` when their validations and lifecycle are required. Loading with `frappe.get_doc` does not by itself establish authorization; use the relevant permission checks before returning or modifying sensitive data. [Document API](https://docs.frappe.io/framework/user/en/api/document)

Every new use of `db_set`, `frappe.db.set_value`, raw SQL writes, `ignore_permissions`, or validation bypass flags MUST have a specific reason, an authorized caller, and protection of the invariants bypassed. Direct setters bypass normal ORM validation hooks. Keeping `update_modified=False` also requires a reason; it is not appropriate for concealing business changes or avoiding concurrency checks. [Database API](https://docs.frappe.io/framework/user/en/api/database)

The established high-frequency theme preference pattern can use a narrow direct setter after permission and field validation. Do not extend that exception to arbitrary commercial documents. Fix business timestamp conflicts by addressing stale state and operation ownership, not by suppressing timestamps everywhere.

Treat internal bypass flags as privileged control flow. Audit whether external input can influence them. Never infer system authorization from a revision type, status, or user-supplied field that says “system-generated.”

## 8. Financial correctness, immutable history, and reconciliation

MUST define one meaning for each monetary field: direct cost, budget cost, selling suggestion, contract rate, revised rate, certified value, and totals. Write down overhead/profit bases and whether layers intentionally compound. Define per-unit quantities and wastage. Align UI, controller, service, aggregate SQL, reports, and exports.

Distinguish missing values from legitimate zero. Do not use `value or default` where zero has business meaning. Validate negative, non-finite, extreme, and malformed inputs according to the domain. Use explicit quantity/currency precision and a documented rounding point. Choose numeric handling compatible with Frappe and the database; do not mix floats and Decimal casually or claim binary floats are exact money.

Approved quantities, rates, baselines, and approval identity MUST be protected server-side. Changes after approval use a defined adjustment, amendment, or reversal with provenance. Define explicitly any permitted metadata edits. `track_changes` complements these rules; it does not establish immutability.

Every cancellation/reversal MUST define the resulting active basis and all dependent projections, including the no-prior-record case. Do not leave a cancelled source looking approved through a retained amount. Specify how to select a prior basis deterministically and preserve audit history.

Derived aggregates MUST equal their authoritative eligible detail records after successful operations. Include insert, update, delete, approval, cancellation, and batch paths. Avoid silently repairing records during a read. First produce a bounded read-only reconciliation; any historical data repair requires a scoped plan, named target, recoverable backup, domain rule, and appropriate authorization.

Construction or contract-standard terminology in comments is not legal/domain certification. Obtain the owner's expected rule and review any externally advertised compliance claim separately.

## 9. Transactions, concurrency, and retries

MUST identify the entire business invariant and all routes that mutate it. An item lock protects that item; it does not automatically serialize every update to a shared BOQ header. Read authoritative state at the correct point in the transaction and document the lock protocol.

For multi-record operations, choose deterministic lock order across services and account for MariaDB's installed isolation and snapshot semantics. A lock acquired after reading stale state may still allow stale calculation. Verify the design with independent connections and controlled interleavings, rather than only a mocked database or sequential test.

Use Frappe's transaction ownership for normal requests/jobs. Do not scatter manual commits through low-level helpers or unconditionally start independent transactions inside document events. If an exception is caught, deliberately preserve the required rollback semantics; an error response after partial writes is not an atomic failure. Savepoints do not undo filesystem or external effects. [Database transaction model](https://docs.frappe.io/framework/user/en/api/database)

MUST make retried approvals, import commits, and external side effects safe. Define a stable operation identity, validate reuse against the same input, and use database uniqueness where appropriate. An in-memory flag or an unlocked “check then insert” is insufficient across workers. Return a meaningful existing outcome for a valid retry, and reject conflicting reuse.

Schedule external work after successful commit where supported. For required external effects, design an explicit durable status/retry mechanism; do not introduce an elaborate outbox unless the operation needs it. Bounded deadlock retries must replay a safe whole operation. Do not retry an irreversible action blindly.

Verify simultaneous changes, repeated requests, failure midway, and concurrent status changes. Assert final database state and totals, not only response success. Tests must genuinely overlap when claiming concurrency evidence.

## 10. API security, permissions, scope, and customer boundaries

For every exposed endpoint or report, MUST:

1. Identify the permitted caller, document permission type, parent/child relationships, and selected-scope rule.
2. Whitelist only functions intended as RPC endpoints. Keep guest access off unless expressly required. Restrict mutations to the appropriate HTTP method, normally POST, using a supported framework API.
3. Validate field types, values, names, enumerations, ranges, payload size, pagination, and caller-controlled sorting/query options. Type hints alone are not authorization or complete validation.
4. Check document permissions before sensitive output or writes. Prove parent and child belong to the same authorized business scope. Avoid leaking existence or names unnecessarily in permission errors.
5. Return only the fields needed by the caller; protect private attachments and generated exports as carefully as the source document.

MUST distinguish three boundaries: permitted documents, selected working context, and separate customer sites. Decide whether selected context is a filter or an access restriction. Reuse an audited helper for the chosen meaning instead of assuming all permission query hooks implement it. Administrative exceptions must be deliberate and tested.

Frappe's permission-aware listing API and unrestricted listing API have different guarantees. Raw SQL and unrestricted reads require an explicit permitted dataset boundary. Parameterize values; allowlist dynamic identifiers/sort choices because they cannot safely be treated as arbitrary user strings. Do not copy a raw subtree template without its required checks. [Database API](https://docs.frappe.io/framework/user/en/api/database)

Tests MUST include an ordinary allowed user and a denied user. Administrator-only success is insufficient. Test relevant User Permissions and company/project combinations through the real transport, including standard REST routes if the document remains writable there. Do not grant broad roles, disable CSRF, make private files public, or use `ignore_permissions=True` just to make a failing flow work.

A customer's environment also needs protected sessions, tokens, TLS, least-privilege deployment/admin access, and controlled secrets. Keep credentials and raw customer data out of code, logs, test artifacts, and external AI/memory services. Document support access and sanitize reproductions.

## 11. Imports, files, exports, and background jobs

MUST validate file type, byte size, ownership, and storage path before expensive processing. For XLSX archives, bound expanded data, members/worksheets, rows, and columns before unrestricted workbook materialization. Limits must match worker resources and supported product sizes. A row check after loading an enormous workbook is too late.

Use private storage for sensitive input/output. Canonicalize permitted paths and do not accept arbitrary server filenames. Escape HTML and treat spreadsheet cells that resemble formulas safely on export. Avoid echoing sensitive full rows in errors. Reject malformed input cleanly, preserving the previous business state.

Preview and commit MUST agree on interpretation and permissions. Revalidate live authoritative state when committing; a preview is not a permanent approval. Handle duplicates and retries with a durable operation identity. Batch mutations use explicit transaction/rollup behavior, and invalid rows have a documented all-or-nothing or partial-acceptance policy.

Long-running operations SHOULD use bounded jobs when justified. A job needs authorized input, target site identity, progress/outcome, failure reporting, retry rules, and safe cancellation where offered. Calling an asynchronous helper that is not wired or currently rejects the work does not constitute an implemented async feature.

Test small valid files, boundary files, malformed safe fixtures, timeout/failure behavior, retry, and the actual customer-role browser path. Do not generate harmful huge archives to test bounds.

## 12. Schema changes, fixtures, installation, and migrations

MUST inspect source DocType JSON and installed metadata before assuming a field. Add schema through the supported repository mechanisms, including patches/fixtures/custom fields where appropriate; a field existing only on the developer's site is not a delivered feature.

Keep installation and migration idempotent, scoped, and minimally invasive. They must not reset customer settings, overwrite customization, broaden permissions, rename commercial records, or delete history without a specific reviewed requirement. Backfill uses an explicit rule and preserves names, links, and provenance. Deduplication must identify a safe survivor and linked-data treatment before deleting anything.

Test fresh installation, upgrade from relevant previous data/schema, and a second migration. Include legacy and multi-company fixtures where the patch affects them. Verify unique/index definitions actually exist after installation and migration; source declarations are not sufficient evidence.

Database DDL can make rollback different from ordinary request rollback. Document recovery of code, schema, data, files, and required configuration. Never use `reinstall`, `drop-site`, force delete, or blanket permission reset on valuable data as a troubleshooting shortcut. Commands with a production or ambiguous site must follow the actual authorization boundary; use a known disposable site for authorized tests.

Frappe migration runs framework-defined steps, including application patches and schema synchronization. Verify the installed version's behavior when ordering matters. [Bench migrate](https://docs.frappe.io/framework/user/en/bench/reference/migrate)

## 13. Frontend, framework extensions, and full feature wiring

MUST use the established VFC/native form path and theme tokens. Preserve `depends_on`, permissions, field state, validation messages, and native navigation. Minimize global prototype replacements. Prefer supported hooks or small tested adapters; a v16-only extension API cannot silently become a v15 dependency. [Frappe extension hooks](https://docs.frappe.io/framework/user/en/python-api/hooks)

For a changed asset, verify registration/import, the actual build, cache invalidation using the established mechanism, and the loaded browser file. Update the relevant query-string version where this app uses it; a bundler hash may cover a different asset path. Do not mark a feature complete because code exists in an unregistered file.

SHOULD use scoped selectors, theme variables, and the least specificity needed. Preserve intentional Frappe overrides; avoid creating an escalating chain of `!important` rules. Do not replace the theme architecture while implementing an unrelated feature.

Check the real browser action, request argument mapping, response shape, permission denial, saving and reloading. Include English/Arabic, RTL, relevant light/dark state, and promised device layouts where the change affects them. Check keyboard/focus behavior and readable errors. Keep implementation details out of customer UI unless they help a meaningful user decision.

A backend helper test is not proof of native Link search behavior. Trace the real Desk call before changing or connecting a sidecar endpoint. Report unwired work honestly.

## 14. Performance, caching, and cost discipline

MUST bound lists, exports, parsers, and expensive requests. Use pagination, efficient set queries, appropriate indexes, and deferred rollups for batches. Avoid unbounded `get_all`, per-row database queries, and repeated full hierarchy recalculation where measurement identifies a cost. Verify query plans and installed indexes on representative data.

Measure the real user path: import preview/commit, opening a BOQ, approvals, reports, and exports under realistic roles and activity. Record dataset size, environment, latency distribution, memory, queue delays, lock waits, and correctness. A synthetic insertion harness or guessed benchmark is not a customer capacity claim.

Cache only where the saved work and invalidation are understood. Keys must include required site, user/permission, scope, and version dimensions. Module globals are not request-local merely because a comment says so. Clear or version caches when the underlying permission or domain state changes. Do not globally cache restricted records by document name alone across sites.

If metered APIs or AI features are added, define per-operation/user/customer budgets, retry limits, observability, and pricing implications before offering unlimited use. Do not introduce such services as part of unrelated maintenance.

## 15. Dependencies and supported version matrix

MUST record and verify the supported Frappe/ERPNext/runtime combinations. Match Python and Node requirements to the selected framework release. Do not advertise v15 compatibility solely because the current v16 environment builds.

Use the repository's existing dependency tools and lockfiles. Prefer deterministic JS installation from the lockfile where supported. Account for Bench-managed Python/framework dependencies rather than installing a competing framework distribution into the app. An audit of an app with empty declared dependencies is not an audit of the deployed environment.

For dependency changes, review upstream primary documentation/release notes, resolved versions, security findings, and compatibility. Run affected checks and retain a reproducible environment record. Do not install tools, change locks, or upgrade the full Bench unnecessarily during a documentation review.

## 16. Testing and evidence standards

Use meaningful tests at the layer where the risk lives:

- Pure domain unit tests for deterministic math and input rules.
- Frappe integration tests for document lifecycle, persistence, permissions, and migrations.
- Real authenticated HTTP tests for transport, allowed/denied routes, and standard REST bypass opportunities.
- Independent database connections for concurrency and committed state.
- Browser checks for asset loading, real feature wiring, Arabic/RTL, and interaction.
- Workload and restore exercises for release capacity and recovery.

The offline suite intentionally forbids app/Frappe/ERPNext imports. Its success is valuable tooling evidence, not proof of BOQ business correctness. AST-extracted probes likewise must be labeled as isolated evidence. Existing historical results are reusable context, but their candidate and scope must remain visible.

For a defect, reproduce the behavior, add a regression that fails for the right reason, implement the smallest correct fix, and demonstrate the pass. Assert outcomes and invariants, including denied-operation state, rather than only HTTP 200 or mock call counts. Inspect tests for fixtures that erase the risk, unsupported monkeypatches, unexpected skips, or shared environment assumptions.

Useful command templates follow. Run from the stated directory and only when relevant; they are not a claim that a suite has passed. These commands do not provision a test site or install missing dependencies.

```bash
# From /home/mohamed/frappe-bench/apps/construction:
/home/mohamed/frappe-bench/env/bin/python -m pytest tests_offline -q
/home/mohamed/frappe-bench/env/bin/python scripts/ai_context_check.py
/home/mohamed/frappe-bench/env/bin/python scripts/lint_scope_metadata.py

# From /home/mohamed/frappe-bench/apps/construction/construction/tests:
node --test test_print_settings_properties.js
```

For site tests, use an explicitly identified, authorized, already provisioned disposable site. Verify its configuration and fixtures first. This example intentionally uses a placeholder:

```bash
# From /home/mohamed/frappe-bench:
TEST_SITE='replace-with-confirmed-disposable-test-site'
bench --site "$TEST_SITE" run-tests --app construction --module construction.tests.test_quantity_revisions
# Candidate release: full relevant application suite after fixtures are ready.
bench --site "$TEST_SITE" run-tests --app construction
```

Confirm options with the installed Bench/Frappe version. Business tests may write fixtures and touch site state; do not run these templates against a customer site. Frappe provides site-based application test execution. [Testing documentation](https://docs.frappe.io/framework/user/en/testing)

Record command, candidate, environment/site classification, expected outcome, actual outcome, exit status, and relevant artifacts. Do not report a test as passing when it did not start, was skipped, ran against the wrong code, or used mocks that bypassed the invariant. A missing dependency requires an explicit blocked result until resolved within the task's scope.

## 17. Daily feature and defect workflow

### A. Understand

Read startup context, trace the live path, identify related callers and open gaps, and define expected behavior. For a defect, isolate a minimal reproduction. For a commercial ambiguity, get the required owner decision while continuing independent work.

### B. Implement

Change the smallest cohesive set of files, preserve unrelated work, enforce server rules, and add the schema/assets/migration wiring actually needed. Keep business, transport, and UI responsibilities understandable. Avoid incidental framework upgrades or sweeping rewrites.

### C. Verify

Run the checks appropriate to the risk. Inspect the final diff and real browser/HTTP/database path where required. Confirm no unapproved permission widening, debug bypass, data mutation, or secrets have appeared. If a check fails, diagnose the cause rather than weakening the gate.

### D. Handover

Update local session notes and affected documentation. Explain the change, why it is correct, what ran, and material limits. Do not infer release approval from a focused feature pass. Follow scoped commit/release governance and existing authorization; don't ask for repeated routine permission.

Use this concise completion record:

```text
Outcome and affected customer behavior:
Changed files and relevant policy:
Verification: commands + actual results + source/environment identity:
Known limits or unresolved gap IDs:
Migration/deployment/data repair required, if any:
Unrelated working-tree changes preserved:
Next necessary action, if any:
```

If authorization for a final external or irreversible step is still missing, present the concrete reviewed result and identify why the permission is needed. Do not stop before completing the already authorized preparation.

## 18. Customer release definition of done

A supported release MUST have:

1. An identifiable source/build version and declared framework/runtime matrix.
2. Closed correctness gaps for the included commercial workflows, with owner-approved meanings and regression evidence.
3. Passing relevant business, permission, HTTP, and browser workflows on that candidate.
4. Verified fresh install and safe upgrade with customer settings/history preserved.
5. Bounded imports/jobs and measured supported workload limits.
6. A complete backup/restore drill with financial/file checks and an agreed recovery target.
7. A delivery/support plan, monitoring, secrets handling, onboarding, exclusions, and a named technical owner.
8. Honest review and approval provenance under the applicable workflow.

Use one Frappe site/database per customer as a starting delivery proposal, then decide bench isolation and upgrade cohorts deliberately. Multiple sites can share the same application code and workers; a site boundary does not make updates independent. [Sites documentation](https://docs.frappe.io/framework/user/en/basics/sites)

Rolling back app files is insufficient if migration altered schema/data. Prepare the recovery procedure before updating valuable data. During an incident, preserve evidence, reproduce safely, and make a targeted fix; do not drop records, disable checks, or rewrite hundreds of lines merely to silence the exception.

Maintain a gap closure record with evidence and remaining limits. Product claims must match included and tested workflows. Treat “professional,” “scalable,” and “release-ready” as conclusions requiring evidence, not labels an agent can award itself.

## 19. Practical learning and ownership for Mohamed

You do not need to become a full-time programmer before continuing. Build working knowledge of these areas so you can judge the agent's work and the product's risks:

| Learn enough to understand | Practical exercise |
| --- | --- |
| Git and reviewable changes | Read a small diff, recognize unrelated changes, and explain which version was tested |
| Frappe lifecycle and permissions | Follow one save/submit/cancel/delete; test it as a project manager and read-only user |
| Source values versus projections | Calculate a small BOQ independently and compare line, header, report, and export |
| Concurrency and retries | Explain why two people approving different lines can affect one total; request actual overlapping tests |
| Safe upgrades and recovery | Observe an isolated restore and verify known totals/files before trusting a backup claim |
| Operations and support | Know who receives an error alert, who can repair a site, and how customer work is restored |

Use your domain expertise to approve quantities, commercial meanings, and real customer workflows. Ask the agent to explain the behavior in construction terms and show evidence. Appoint or engage a Frappe-capable engineer for high-risk review and production support; the scale of that engagement can grow with customers.

The strongest improvement is consistent practice: define the rule, implement it in the right layer, test the real path, preserve history, and record what is actually proven.

## 20. Reusable instruction for an agent that does not auto-read AGENTS.md

Paste this at the beginning of a session with such a tool:

```text
Work as a careful Frappe/ERPNext engineer in /home/mohamed/frappe-bench/apps/construction.
Read AGENTS.md, docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md, and relevant SESSION_MEMORY.md
before editing. Follow applicable scoped workflow and architecture instructions.
Verify live code/schema and working-tree state; preserve unrelated changes.
Implement my authorized request end to end with proportional verification.
Protect commercial math, approved history, permissions, scope, transactions, and customer data.
For money/security/migration/release work, read the relevant customer release gaps.
Report actual checks and limitations; do not invent readiness, approvals, or test results.
Keep private findings local unless I authorize an external destination.
Ask only for necessary missing business decisions or final actions that are not authorized.
```

This file is a daily engineering standard. It improves future changes; it does not itself remediate the current app or guarantee that any AI agent always complies. Review the standard when the architecture, supported versions, or delivery model changes.
