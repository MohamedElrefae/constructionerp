# P1 execution-tree reader reconnect-claim repair — Builder + independent Tester cycle, 22 November 2026

Follow-up to `P1_OBSERVER_RECONNECT_FIX_2026-11-22.md`, approved by the owner on 22 November. No site was contacted; no authorization code was run against a site.

## Outcome and affected customer behavior

No customer-facing behavior. Offline repair of the live fresh-authorization reader's false reconnect claim, the same defect class corrected in the offline observer.

The reader (`FreshAuthorityReader`) opens a read-only consistent snapshot for authorization decisions. Its old code claimed "automatic reconnect disabled" via `connection.auto_reconnect = False` plus a `getattr` check. On the installed driver (mysqlclient 2.2.7), that setting does not exist: `auto_reconnect` appears nowhere in the package source; the C connection type exposes no reconnect state to Python (memberlist is `open`/`converter`/`server_capabilities`/`port`/`client_flag`; `tp_dictoffset` 0). The assignment created a dead Python attribute on the `MySQLdb.connections.Connection` subclass (which has a `__dict__`), so the check could never fail and the surrounding try/except was dead code. The real control is the client library's `MYSQL_OPT_RECONNECT` option, applied only inside `ping(reconnect=...)` (`_mysql.c:1933`) and persistent; the internal flag starts `false` (`_mysql.c:455`).

## Changed files

- `construction/services/execution_tree_access.py`
  - Removed the vacuous `auto_reconnect` assignment, try/except and getattr check.
  - Added `PINNED_MYSQLDB_VERSION = (2, 2, 7)`; `__enter__` refuses other driver generations with `UnsupportedProfile` before connecting.
  - Added `_refuse_ping` / `_disable_reconnect`: the reader connection's `ping` is bound to a fail-closed refusal before any cursor or SQL, so the only path that could enable silent reconnection raises `UnsupportedProfile("Reconnect attempt refused")` instead.
  - Module docstring states the real limits: no Python-visible setting exists; the library state at creation is not readable from Python and is not claimed verified; transaction checks detect demonstrated drift only.
- `tests_offline/test_execution_tree_access_rules.py`
  - `FakeConnection` no longer carries `auto_reconnect`; its cursor returns a valid read-only row.
  - Stub `MySQLdb` modules include `release`; the real-driver test's fake lost its `auto_reconnect` attribute.
  - Replaced the vacuous test with: ping refusal during the reader lifetime (rollback/close verified); unreviewed driver generation refused before connect; source-pin test over `_mysql.c`, `connections.py` and `cursors.py` (no `auto_reconnect`; `MYSQL_OPT_RECONNECT` only in ping; `self->reconnect = false;` at init; no reconnect member exposed); and a real never-connected `MySQLdb.connections.Connection` instance test proving the guard binds to the production class and refuses both `ping()` and `ping(reconnect=True)`.

## Verification: commands + actual results + source/environment identity

- Builder: `pytest tests_offline/test_execution_tree_access_rules.py -q` → 150 passed; full suite → 655 passed, 85 subtests, exit 0.
- Builder after delta: 151 passed; full suite → **656 passed, 85 subtests passed**, exit 0.
- Independent Tester (fresh context, read-only, ran separately; delta re-verified in a second round): re-derived all driver facts from `/home/mohamed/frappe-bench/env/lib/python3.14/site-packages/MySQLdb/` — version 2.2.7, no `auto_reconnect` anywhere, no reconnect member, `tp_dictoffset` 0, `MYSQL_OPT_RECONNECT` only in ping, internal flag false at init, `MySQLdb.connect` returns the dict-bearing `Connection` subclass (runtime probe). Demonstrated the original defect mechanism on a real never-connected instance (`conn.__dict__ == {'auto_reconnect': False}`), confirmed the guard refuses on the real class with zero network attempts, and mutation-tested every source-pin assertion (each fails under the corresponding source change). Verdict: **PASS WITH NOTES** (first round) and **PASS WITH NOTES** (delta); no defects found.

## Known limits or unresolved gaps

- The driver's reconnect state at connection creation is not readable from Python; the module refuses the path that could change it and does not claim the initial state. Transaction-state checks detect demonstrated drift only.
- The source-pin test is exact-substring based; a same-version source change in wording would fail it (fail-closed, acceptable).
- Pre-existing, not introduced: `close()` can mask an in-flight exception if `rollback()`/`close()` raises.
- Connection provenance, permission completeness, live MariaDB semantics and full P1 acceptance remain unverified; `_require_verified_runtime()` is untouched and still unconditionally raises.

## Related finding (recorded, not fixed)

Frappe's own pinned `frappe/database/mariadb/mysqlclient.py` line 111 (`conn.auto_reconnect = True`) is the same dead-attribute pattern in framework code. It is outside this task's scope (shared framework app); recorded here as evidence.

## Unrelated working-tree changes preserved

Confirmed by both sessions: exactly the pre-existing 17 tracked modifications and the untracked files; no unrelated work altered.

## Next necessary action

Owner decision. No lab read until scope and authorization are concretely defined.
