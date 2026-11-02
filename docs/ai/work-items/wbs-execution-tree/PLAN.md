# WBS execution tree — P1 bounded implementation plan

## Read and baseline

Pinned reading (coordinator-supplied snapshots under engineering-startup/v1):
- `AGENTS.md`, `docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md`, `docs/ai/ORCHESTRATION_SYSTEM_MANUAL.md`
- `docs/ai/work-items/WBS/Construction_ERP_WBS_Planning_Packet_v1.md` (increments P1–P4, decisions D01–D10)
- `docs/ai/work-items/engineering-startup-gates/IMPLEMENTATION.md`, `.../PLAN.md`

Baseline (verified locally before this plan was written):
- Source repository: `/home/mohamed/frappe-bench/apps/construction`; code baseline commit **`a19bf8e`** (`develop`).
- The orchestrator refuses the main checkout as its root (`check_configured_root`: "Worktree cannot be apps/construction"), so the work item runs in a **dedicated execution worktree** created from the docs-only commit, e.g. `/home/mohamed/frappe-bench/worktrees/wbs-execution-tree` on branch `feature/wbs-execution-tree`. Scope paths in `scope.json` are repo-relative and therefore valid in that worktree.
- A **docs-only baseline commit** adding the dormant P00/G0 records (`docs/ai/work-items/WBS/`, `scripts/p00_g0_witness/`) **and this frozen plan/scope** (`docs/ai/work-items/wbs-execution-tree/`) is performed by the owner before the worktree is created; no application code changes are part of it. `init` records that commit as `base_commit`.
- `doctor` on a fresh, uninitialised worktree reports `branch: false` by design (the expected branch defaults to `feature/scope-context-portability` until `init` records the actual branch). `init` itself does not require `doctor`; `run` does. Therefore the valid order is **init → doctor → status → run**.
- Coordinator startup checks (`schema_drift_checker.py`, `ai_context_check.py`) are run by the orchestrator's readonly sandbox; this plan does not claim their results.

## Contract and compatibility

- New DocType `execution_breakdown_node` is the project execution tree. It is **independent of the commercial BOQ structure** (`BOQ Structure`/`BOQ Item`); no commercial quantities, rates, contract totals or historical BOQ records are read or written by P1.
- Proposed names in the packet (`execution_breakdown_node`, `execution_node`, `ebs_code`) are adopted only after a local naming check; the DocType name is `execution_breakdown_node`, the tree parent field is `parent_execution_node`, and the code field is `ebs_code`. If a collision or convention conflict is found, implementation stops and the plan is revised.
- Tree structure mirrors the existing `BOQ Structure` convention: `is_tree = 1`, `nsm_parent_field = parent_execution_node`, `module = construction`, `engine = InnoDB`, `track_changes = 1`.
- Project/company derivation: `project` is required on the root; children inherit/require the parent's `project`; `company` is derived from `project` when available and never user-edited independently.
- Codes (D08): format `EBS-####` (4-digit per-project sequence), stable, never renumbered. Uniqueness per project is enforced by a pre-insert check using the pure `next_code()` rule plus a duplicate-key retry. **P1 does not claim concurrency-proof uniqueness at the database level** (no composite unique index is added in this stage); this is recorded as a limitation, not a pass.
- Leaf/disabled semantics (D05): only childless, enabled nodes are leaf-eligible for future Stage mapping; disabling a node is allowed and reversible; P1 does not create any mapping.
- Referenced-subtree protections (D06) are **not** implemented in P1; the packet requires them no later than P2. P1 therefore has no Stage references to protect and the safe intermediate (tree exists, no Stage links) holds.
- Scope-aware access (D10): reads inherit the existing wildcard scope hook (`permission_query_conditions["*"] → scope_query.add_scope_conditions`), which filters any doctype carrying `company`/`cost_center`/`project`/`department`. **No `hooks.py` change is required or permitted.** Writes validate that the target `project` is within the caller's permitted scope through the DocType's role permissions plus a controller check that refuses cross-project parent links; P1 does not expand any role's scope beyond existing permissions.
- Compatibility: Frappe v15/v16, Python 3.10 syntax; no ERPNext imports; no new `hooks.py` entries; no changes to `BOQ Item Stage` in this stage.

## Implementation

1. **Schema** — `construction/construction/doctype/execution_breakdown_node/execution_breakdown_node.json`
   - Fields: `title` (Data, reqd), `ebs_code` (Data, reqd, read-only after insert), `parent_execution_node` (Link → self), `project` (Link → Project, reqd), `company` (Link → Company, read-only, derived), `is_group` (Check), `disabled` (Check), `description` (Small Text), plus NestedSet fields managed by Frappe (`lft`, `rgt`, `old_parent`), `idx`.
   - Permissions: System Manager — read/write/create/delete; Projects Manager — read/write/create; Projects User — read. No wildcard permissions.
2. **Controller** — `.../execution_breakdown_node.py`
   - `validate()` delegates to the pure rules module: parent-chain cycle check, project consistency (child inherits parent's project), code format/uniqueness, leaf/disabled consistency, root derivation.
   - `autoname` via `ebs_code`; `before_insert` assigns the next code through `next_code()`; no renumbering on edit.
   - `on_update`/`on_trash` do **not** cascade into BOQ or Stage data in P1.
3. **Pure rules module** — `.../tree_rules.py`
   - **No imports of `frappe`, `erpnext`, or `construction`** (required by the offline harness); operates on plain mappings/lists.
   - Functions: `derive_project(node, parent)`, `detect_cycle(node_name, parent_name, parent_map)`, `validate_leaf(node, children)`, `is_leaf_eligible(node, has_children)`, `next_code(existing_codes)`, `normalize_code(value)`.
4. **Client** — `.../execution_breakdown_node_tree.js` (tree view configuration, project filter) and `.../execution_breakdown_node.js` (form: derive project from parent, warn on disabled/group changes). Cache-buster not applicable (DocType JS is loaded per-form; no `hooks.py` change).
5. **Docs (owner-frozen inputs)** — `PLAN.md` and `scope.json` are owner-provided and **not writable by the builder** (they are outside `allowed_paths`). Post-verification notes and review findings are recorded by the verifier/owner in separate review records, keeping the governing plan frozen.

## Meaningful verification

Offline, network-isolated, no app imports (the harness forbids `construction`/`frappe`/`erpnext`; the test loads `tree_rules.py` by path via `importlib`, as `tests_offline/test_checkers.py` does):

```sh
python3 -m pytest tests_offline/test_execution_breakdown_node.py -v
```

Covered:
- cycle detection (self-parent, 2-cycle, deep cycle) and legal chain;
- parent/child project consistency and root derivation;
- leaf eligibility (childless/enabled vs group/has-children/disabled) and group-conversion refusal where children exist;
- code normalization and `next_code()`: monotonic per project, no reuse of existing codes, gap tolerance, format rejection;
- disabled-node reversibility rules (pure predicates only).

Not covered (must not be claimed): Frappe runtime install/migrate, UI behavior, permission enforcement, database-level concurrency, Stage mapping. Those remain P2/P3/P4 or integrated acceptance.

## Exclusions and completion

Excluded from P1:
- No `BOQ Item Stage` changes, no `execution_node` field, no mapping/relink logic (P2).
- No coverage/navigation report (P3), no billing, payment certificates or measurement ledger changes.
- No data migration, backfill or import.
- No `hooks.py` change; no translation files (the app has no `translations/` directory; DocType labels are standard English).
- No edits to `PLAN.md` or `scope.json` (frozen contract inputs).
- No deployment, no release, no ERP adoption claim.

Completion: the candidate contains the DocType schema, controller, pure rules module, client scripts and the offline test file; the offline validation passes; the worktree diff is limited to the `scope.json` allowed paths. Because the plan/scope documents are tracked by the owner's docs-only baseline commit and excluded from `allowed_paths`, any builder change to them is an out-of-scope violation. The owner commit is a separate owner operation.
