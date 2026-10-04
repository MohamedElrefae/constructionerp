# Verification evidence and practical limits

2026-10-04. Tested the task worktree source; the code is committed as candidate `d4f071e`. The concurrently edited main app is outside this candidate. `TESTED_FILES.json` contains exact SHA-256 hashes for thirty tested source/test/CI files. Subsequent documentation commits do not change those files.

## Environment isolation

New disposable bench: `/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes`.

Sites: `release-gaps.localhost` for tests and `release-install.localhost` for a second fresh-install check. Each has a new database in a separately initialized MariaDB instance with networking disabled. Redis uses a separate authenticated loopback instance because the installed Frappe Redis wrapper does not support the proposed Unix connection. Random fixture credentials stay in private local configuration and are not committed. Scheduler remains disabled. After checks, only our three known private fixture servers were gracefully stopped; their local data/configuration remain available for deliberate replay. Existing Bench sites, database and Redis instances are outside this test scope.

The disposable bench links the reviewed construction worktree and reads installed framework/ERPNext source. The PDF regression reads the existing public asset build and uses the installed wkhtmltopdf renderer; this proves one native PDF flow, not a rebuilt frontend or visual/browser qualification. The standard Bench wrapper selected the main bench due to the linked runtime; successful tests therefore invoke `frappe.utils.bench_helper` directly from the disposable `sites` directory, with the worktree first in PYTHONPATH. No command changed an existing site.

Observed stack:

- Python 3.14.5; Node 24.15.0; MariaDB 10.11.14; Redis 7.0.15.
- Frappe 16.18.1 source `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0`.
- ERPNext source `2807c9f08fff3f161c0a2e10745a26aa6331ffd5`.
- wkhtmltopdf 0.12.6-2build2 (Ubuntu package). No v15 test runtime used.
- `pip check` fails in the shared runtime: Frappe requires filelock `~=3.20.1` / requests `~=2.33.0`, installed 3.29.0 / 2.34.1. The shared environment was preserved. These conflicts remain part of G10, even though selected functional tests pass.

## Actual successful checks

| Test module | Passed |
| --- | ---: |
| `construction.tests.test_customer_release_financial_guards` | 6 |
| `construction.tests.test_cost_database_api` | 21 |
| `construction.tests.test_boq_rollup_audit` | 5 |
| `construction.tests.test_bilingual_install_schema` | 4 |
| `construction.tests.test_quantity_revisions` | 30 |
| `construction.tests.test_variation_orders` | 23 |
| `construction.tests.test_cost_analysis_engine` | 20 |
| `construction.tests.test_boq_properties` | 17 |
| `construction.tests.test_boq_transactions` | 12 |
| `construction.tests.test_boq_wbs_generation` | 2 |
| `construction.tests.test_boq_structure_conversion` | 1 |
| `construction.tests.test_boq_structure_delete_safety` | 1 |
| `construction.tests.test_boq_excel_parser` | 2 |
| **Python total** | **144** |

Some legacy property cases are placeholders. The total is an observed run count; it is not a count of every business invariant or a certification of all modules.

- JS print-settings properties: **35 passed in 9 suites**, lockfile packages installed with `npm ci`. Node's child-test reporting lost suite details in the outer sandbox; the successful full report came from reviewed execution outside it, and direct execution also reported all 35 tests.
- Authenticated real Frappe WSGI request pipeline: Project Manager and System Manager each read the approved revision (HTTP 200); REST quantity edits and Desk form rate edits each returned HTTP 417 / ValidationError. Stored quantity remained unchanged. This used token authentication with synthetic users and records. It is not browser UI evidence or a complete permission matrix.
- Second completely new site installed Frappe/ERPNext/construction with the new hooks automatically; subsequent required-schema setup checked 23 installed adapters, created zero fields, and passed. This establishes fresh-install and immediate schema idempotence for this source/runtime only.
- Invalid System Manager import flags and absence of an internal commit are verified using an actual DB savepoint regression.
- Schema facts checker: 21 schema-owning DocTypes plus one override, PASS. Context checker: 11 PASS / zero failures. Ruff lint passes on every touched Python file; changed/new code formatting and `git diff --check` pass. `construction/install.py` has an unrelated pre-existing adjacent-f-string formatting difference outside the edited section; that line was preserved.

## G05 reproduction, correction and bounded evidence

Before the concurrency correction, two independent thread-local connections established a REPEATABLE READ snapshot in writer A, committed a different-item quantity update in writer B, then saved writer A through the real controller. Both completed, but authoritative contract 120/cost 48 became stored contract 110/cost 44. The earlier local fingerprints are retained in `PRE_CONCURRENCY_FIX_FILES.json`; these identify an uncommitted intermediate source state, not an immutable release commit.

The same actual two-thread sequence against the final source now produces stored and computed contract **120**, estimated/budget **48**, with zero mismatched header fields. The prior probe/log is retained as counter-evidence, alongside `/tmp/probe_customer_release_concurrency_fixed.py` and `/tmp/customer-release-concurrency-fixed.log` for the correction.

The twelve committed regressions use real independent MariaDB connections with distinct connection IDs and overlapping transactions. They cover stale snapshots for save/delete/deferred flush/approvals/cost/header changes; repeated approval; current Frozen status; actual NOWAIT contention; two refused commit attempts after a caught guard failure; refusal after savepoint recovery of an earlier partial write; one explicit fresh-transaction retry; an injected deadlock; and rollback after an injected failure between header and structure update. The deadlock is injected, not claimed as a real server deadlock. An initial fixture bug in Frappe's legacy secondary-connection restoration was corrected before the passing run; the final suite explicitly restores and distinguishes both connections.

The broader native WBS suite exposed rejection of legitimate parallel inserts by unconditional NOWAIT. New structure insertion now obtains its header guard before naming/child locks with `WAIT 5`; the unchanged three-thread WBS test passes, along with structure conversion/deletion safety and BOQ import regressions. Existing document operations retain non-waiting guards after possible framework child locking. See `TRANSACTION_PROTOCOL.md` for scope and tradeoffs. This establishes the tested invariants, not a load guarantee, comprehensive approval policy, upgrade-path qualification or automatic retry feature.

## Local reproduction and retained evidence

Successful logs remain local under `/tmp/customer-release-*.log`; startup JSON is `/tmp/customer-release-context-final.json`. Fixture/probe scripts and private state are local under `/tmp`; do not publish fixture credentials or arbitrary site configuration. For the Python modules, use the following pattern after deliberately restarting the private fixtures:

```bash
cd /home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/sites
PYTHONPATH=/home/mohamed/frappe-bench/worktrees/customer-release-gap-fixes \
  /home/mohamed/frappe-bench/env/bin/python -m frappe.utils.bench_helper frappe \
  --site release-gaps.localhost run-tests --app construction \
  --module construction.tests.test_customer_release_financial_guards
```

Repeat only needed module checks after new changes; never substitute an existing Bench site for this disposable fixture. The HTTP and concurrency probes are `/tmp/probe_customer_release_http.py`, `/tmp/probe_customer_release_concurrency.py` (expects the pre-fix failure) and `/tmp/probe_customer_release_concurrency_fixed.py` (expects correct totals); they create synthetic records and are guarded to this exact fixture bench. They must not be adapted to customer data casually.

The native orchestrator, GitHub CI, a provider job, representative prior-version upgrade, timed restore, load qualification, full browser/access matrix and production deployment were not executed. Parent review of delegated diffs is recorded; no independent human release review or native approval packet is claimed.
