# P1 observer reconnect-claim repair — Builder + independent Tester cycle, 22 November 2026

Continuation of `P1_OPENCODE_HANDOFF_2026-11-22.md`. No site was contacted; no lab read was run or proposed.

## Outcome and affected customer behavior

No customer-facing behavior. Offline repair of the limited lab observer's false reconnect claim.

The earlier independent finding was correct and is now confirmed twice (Builder and independent Tester, each from the installed source): PyMySQL 1.4.6 has **no `auto_reconnect` setting**. The observer's old `connection.auto_reconnect = False` created a dynamic attribute and its boundary check could never fail. The driver's only reconnect path is an explicit `ping()` — whose `reconnect` argument defaults to True and silently re-establishes a closed connection. The observer never calls `ping`, and the query path (`Cursor.execute` → `Connection.query` → `_execute_command`) contains no reconnect.

## Changed files

- `docs/ai/work-items/WBS/tools/b2_limited_observer.py`
  - Removed the vacuous `auto_reconnect` assignment and checks.
  - Added a version pin: the module raises at import against any PyMySQL version other than 1.4.6 (the version whose installed source the claims rest on).
  - Added `_disable_reconnect()` / `_refuse_ping()`: the supplied connection's `ping` is bound to a fail-closed refusal before any cursor is created, so a reconnect attempt during collection raises instead of silently replacing the connection and snapshot.
  - Docstrings now state the real limits: boundary checks detect demonstrated drift but do not prove uninterrupted snapshot identity between statements and do not enforce exclusive use of the supplied connection; exclusivity is the caller's responsibility.
- `tests_offline/test_b2_limited_observer.py`
  - Removed the vacuous flag-drift test (it tested the fake attribute, not the driver).
  - Added: ping refusal during collection fails closed with rollback/close and no row reads; a guard test against a real (never connected, `defer_connect=True`) driver instance; a source-pinning test that re-verifies the installed driver files from disk (no `auto_reconnect`; `self.connect()` exactly 3×: construction + inside `ping`; `ping(reconnect=True)` default; no ping/reconnect in the query path or cursors).

## Verification: commands + actual results + source/environment identity

- Startup: `python3 scripts/schema_drift_checker.py` → match, exit 0. `python3 scripts/ai_context_check.py` → 12/12 PASS, exit 0.
- Builder: `pytest tests_offline/test_b2_limited_observer.py -q` → 18 passed, exit 0. Full suite `pytest tests_offline -q` → **653 passed, 85 subtests passed**, exit 0 (previous report: 651).
- Independent Tester (fresh context, read-only, ran separately): re-derived all four driver-source facts from `/home/mohamed/frappe-bench/env/lib/python3.14/site-packages/pymysql/` (version 1.4.6) — all confirmed; ran both test commands (18 passed; 653 passed, 85 subtests; exit 0); break-the-fix probe with a spied socket layer: without the guard a real `ping()` made one socket connection attempt; with the guard, `ping()` and `ping(reconnect=False)` both raise `ObservationError('Reconnect attempt refused')` with **zero** socket attempts. Verdict: **PASS WITH NOTES**.

## Known limits or unresolved gaps

- Connection provenance, permission completeness, live MariaDB semantics and full P1 acceptance remain unverified; `_require_verified_runtime()` is untouched and still unconditionally raises.
- The observer has not been run against any site; both broad scopes (all BOQ rows, all protected DocShare rows) still require explicit owner authorization with a reviewable scope first.
- The two changed files are untracked (no committed baseline), so "changed relative to HEAD" rests on current content and mtimes, not a git diff. No unrelated work was altered (identical 56-entry status before/after).

## Independent Tester follow-up finding (not fixed in this cycle)

The same vacuous pattern persists in **live app code**: `construction/services/execution_tree_access.py` lines ~122/125 assign/read `auto_reconnect` on a **MySQLdb** (mysqlclient) connection — a different driver with different reconnect semantics — and its fake test `tests_offline/test_execution_tree_access_rules.py` bakes the same fiction in. This belongs to the execution-tree workstream and needs its own Builder + Tester cycle with the actual mysqlclient source inspected before any correction.

## Unrelated working-tree changes preserved

Confirmed by both sessions: 56 dirty/untracked entries before and after, content untouched.

## Next necessary action

Owner decision: approve a separate cycle to correct `execution_tree_access.py`'s reconnect claim (requires inspecting the installed mysqlclient source first), or leave it to the execution-tree workstream. No lab read until scope and authorization are concretely defined.
