# AI Agent Continuation Report — Civil Engineer Dashboard

**Purpose:** technical handoff for the next AI agent or maintainer improving the dashboard and orchestrator.

**Current baseline:** `737365a` on `feature/scope-context-portability`.

**Status:** Week 3 dashboard milestone accepted locally. Do not infer authorization for a Week 4 change, ERP mutation, agent dispatch, commit, push, or deployment from this document.

## 1. Read first

Before proposing or changing anything, read these live repository files in this order:

1. `AGENTS.md` — project conventions and non-negotiable ERP constraints.
2. `SESSION_MEMORY.md` — current sprint, decisions, and blockers.
3. `docs/ai/ORCHESTRATION_SYSTEM_MANUAL.md` — workflow authority and CLI lifecycle.
4. `docs/ai/work-items/scope-context-portability/IMPLEMENTATION.md` and `IMPLEMENTATION_HANDOFF.md` — work-item history and requirements.
5. `docs/ai/CIVIL_ENGINEER_DASHBOARD_GUIDE.md` — operator-facing contract.
6. `dashboard/tests/` and `orchestrator/tests/` — executable behavioral contract.

Live repository files outrank this report and any cached memory. Keep `apps/construction` out of scope unless an owner explicitly authorizes it.

## 2. Architecture map

| Component | Responsibility | Important files |
|---|---|---|
| Dashboard HTTP service | Local Starlette UI, authentication, task routes, governed actions | `dashboard/app.py`, `dashboard/templates/index.html`, `dashboard/static/` |
| Configuration | Loopback binding, paths, runtime security limits, structural bench-root discovery | `dashboard/config.py` |
| Authentication | scrypt credentials, first-run setup, sessions, CSRF, host/origin controls | `dashboard/auth.py` |
| Registry and action log | Registered tasks, worktree validation, action ownership/recovery state | `dashboard/registry.py`, `dashboard/bootstrap.py`, `dashboard/process.py`, `dashboard/launcher.py` |
| Dashboard subprocess boundary | Fixed action allowlist, trusted Python execution, timeouts | `dashboard/subprocess_client.py` |
| Orchestrator projections | Read-only state/plan/context/findings/evidence/diff/settings/audit data | `orchestrator/dashboard_api.py` |
| Orchestrator authority | Workflow state, gates, tokens, dispatch and checkpoint synchronization | `orchestrator/engine.py` |
| Stage 4 status | Sanitized, descriptor-relative read of canonical export manifest | `dashboard/security.py` |

The dashboard is intentionally split: ordinary Week 3 inspection calls do not construct `Engine`, do not take `execution.lock`, and must not cause checkpoint/event/job mutations. Governed Week 2 actions retain their explicit fencing and lock ownership.

## 3. Hard invariants — do not weaken

### Authority and dispatch

- Week 3 inspection endpoints must never call `Engine.run`, `_prepare`, `_dispatch`, a launcher, or worker subprocesses.
- `Engine.grant_and_synchronize()` is the approval-only path. Do not replace it with `Engine.approve()` unless the dispatch consequences are expressly intended and reviewed.
- Approval requires current gate/review/plan/scope/roles bindings and an empty active-job set.
- Never add pause, resume, reset-budget, direct run, role editing, Git commit/push, ERP import, or deployment controls without a new owner-approved milestone.

### Stage 4 isolation

- `erp-arabic-bilingual-data` is rejected by every dashboard mutation.
- `GET /api/erp/projection` is read-only. It reads only the fixed canonical manifest path derived from the structural Frappe bench root.
- Return only flat sanitized manifest fields. Never restore raw `manifest`, `export_path`, site-private paths, tokens, or credentials.
- A manifest with unsafe permissions reports integrity disclosure; it is not permission to repair the file or execute ERP work.

### Filesystem and data safety

- Evidence reads use descriptor-relative traversal with `O_NOFOLLOW`, `fstat`, trusted owner checks, and strict no group/world writable path components. Do not replace with `Path.resolve()` plus ordinary file I/O.
- Unsafe evidence must fail closed; the dashboard must never run `chmod` as remediation.
- Audit exports stay bounded: no more than 1,000 events, 512 KiB serialized output, and 16 KiB per string field. Caps must remain server-side, regardless of CLI payload values.
- Git diff uses only a stored base revision, no caller revision, `--no-ext-diff`, `--no-textconv`, `--no-color`, byte bounds, `stderr=DEVNULL`, and the monotonic `select.poll()` deadline for both diff and name-status processes.

### Process/recovery safety

- Mutating action state uses the exact fence tuple: action ID, fencing token, executor instance ID, and expected state.
- Lock ordering is Action Lock then `execution.lock`, released in reverse order.
- Preserve process start-time validation, launcher parent identity checks, and recovery compare-and-swap behavior. Do not simplify these based on a passing happy-path test.

## 4. Public endpoint inventory

| Class | Endpoints | Constraint |
|---|---|---|
| Authentication | `/api/auth/*` | CSRF and session protected as applicable. |
| Task registration/bootstrap | `/api/tasks/register`, `/api/tasks/bootstrap`, delete task | Controlled mutations; worktree and action-log protections apply. |
| Plan governance | `adopt-scope`, `create-review`, `approve-plan` | Explicit review snapshot and fence validation. Stage 4 blocked. |
| Inspection | `state`, `plan`, `review-context`, `ai-context`, `findings`, `evidence`, `diff`, `settings` | No Engine construction/dispatch or workflow-state writes. |
| Export | `export/audit`, `export/state`, `export/reviews` | Sanitized and bounded. |
| ERP projection | `/api/erp/projection` | Fixed manifest, read-only, sanitized. |

Any new route needs: authentication review, CSRF/origin review if mutating, Stage 4 behavior, scope/registry validation, error sanitization, non-dispatch implications, and an automated test.

## 5. Required verification before a proposal or merge

Use the feature worktree:

```bash
cd /home/mohamed/frappe-bench/worktrees/scope-context-portability
dashboard/.venv/bin/pytest dashboard/tests -q \
  -W error::pytest.PytestUnraisableExceptionWarning
orchestrator/.venv/bin/pytest orchestrator/tests -q
```

For a change touching Week 3 data projections, additionally run:

```bash
dashboard/.venv/bin/pytest \
  dashboard/tests/test_week3_api.py \
  dashboard/tests/test_week3_non_dispatching.py -v \
  -W error::pytest.PytestUnraisableExceptionWarning
```

For UI work, run the UI suites sequentially; they share a local Uvicorn port:

```bash
dashboard/.venv/bin/pytest dashboard/tests/test_ui_integration.py \
  dashboard/tests/test_ui_plan_approval.py \
  dashboard/tests/test_ui_week3.py -v
dashboard/.venv/bin/pytest dashboard/tests/test_ui_week3.py \
  dashboard/tests/test_ui_plan_approval.py \
  dashboard/tests/test_ui_integration.py -v
```

Do not run browser suites concurrently. Do not weaken browser sandboxing or suppress warnings to obtain a passing result.

## 6. Recommended next-improvement process

There is no approved Week 4 scope. A future agent should:

1. Identify a concrete owner problem and document it in the work-item inbox/plan.
2. State whether it is inspection-only or mutating, and whether it could reach the orchestrator, Git, Frappe, or Stage 4.
3. Design the smallest change that preserves the invariants in Section 3.
4. Add negative tests for unauthorized dispatch, stale authority, malformed inputs, unsafe paths, and privacy leakage.
5. Obtain explicit owner approval before implementation when the change expands authority or writes outside dashboard-local state.
6. Update the civil-engineer guide when user-visible behavior changes.
7. Preserve evidence and commit only the approved scope. Push only when explicitly requested.

## 7. Known operational notes

- The dashboard is local-only by default (`127.0.0.1:8080`). Treat remote access as a separate security design.
- Runtime data, credentials, virtual environments, and wheel caches are intentionally excluded from Git.
- The Stage 4 manifest currently may report `unverified_permissions`; this is a truthful signal, not a dashboard defect to auto-repair.
- A `409` from a governed endpoint normally means a stale snapshot, duplicate action, or active executor. Reconcile rather than retrying blindly.
- Test results are evidence for the tested revision only. Always run relevant suites after modifying code.

## 8. Handoff checklist

Before ending a future agent session:

- [ ] Record the owner request, chosen scope, and explicit non-goals.
- [ ] State whether Stage 4, ERP data, dispatch, Git, or role settings were touched (normally all **no**).
- [ ] List modified files and test commands/results.
- [ ] Update the operator guide for visible changes.
- [ ] Update `SESSION_MEMORY.md` only when the project protocol authorizes it and the entry is accurate.
- [ ] Leave the worktree status and next required owner decision clear.

