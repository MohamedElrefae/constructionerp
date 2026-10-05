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

## Owner financial rules — final candidate verification (2026-10-05)

The following counts replace the earlier source candidate's counts for this follow-up. All thirteen modules were run sequentially against the final integrated source in the private `release-gaps.localhost` fixture; no customer or existing working site was used. Formatting-only normalization followed the successful functional checks. The JavaScript/source assets are unchanged; the earlier 35 JS passes are earlier evidence, not a new run.

| Module | Passed |
| --- | ---: |
| `construction.tests.test_cost_analysis_engine` | 36 |
| `construction.tests.test_customer_release_financial_guards` | 12 |
| `construction.tests.test_quantity_revisions` | 30 |
| `construction.tests.test_variation_orders` | 23 |
| `construction.tests.test_cost_database_api` | 22 |
| `construction.tests.test_boq_transactions` | 12 |
| `construction.tests.test_boq_properties` | 17 |
| `construction.tests.test_boq_excel_parser` | 4 |
| `construction.tests.test_boq_rollup_audit` | 5 |
| `construction.tests.test_boq_wbs_generation` | 2 |
| `construction.tests.test_boq_structure_conversion` | 1 |
| `construction.tests.test_boq_structure_delete_safety` | 1 |
| `construction.tests.test_bilingual_install_schema` | 5 |
| **Python total** | **170** |

The suite covers additive 120 pricing and a configured 125 tax allowance, analysis quantity normalization, item/header/report/export persistence, manual restoration (including zero and edited manual costs), multiple cancellations, cancellation of superseded history, absent evidence, duplicate approvals, derived parent identity/company mismatch, blocked unresolved legacy pricing/approval, explicit zero/negative/nonfinite factors, actual workbook previews, optional English/Arabic tax headers and old-workbook defaults, immutable status/deletion/attribution, direct-document correction projection, stale corrections, forged baselines, Draft/old-history replay, and the existing real transaction/import/VO regressions. Existing property placeholders remain; 170 passes are not complete-app certification.

Authenticated actual Frappe WSGI requests on the final source: Project Manager and System Manager REST Approved→Rejected/Draft and Desk reversal returned 417; protected deletion returned native 403 for Project Manager and controller 417 for System Manager. Factor zero returned 417. New correction approval returned 200, recorded the authenticated actor instead of supplied Guest attribution, and updated current quantities while original history stayed Approved. Site Engineer approval returned 403 and remained Draft. This is request/lifecycle evidence, not a browser or complete customer-access matrix.

The synthetic legacy preservation probe ran the version/provenance patch repeatedly: recorded commercial amounts, status and attribution were preserved; unresolved new approval was refused. A deliberately constructed current-version fixture alongside older history retained its active basis on replay. This is bounded synthetic upgrade evidence, not a general conversion tool or representative customer migration.

The second isolated site (`release-install.localhost`, originally created empty for this task) successfully completed two actual migrations with the new fields. This fresh-site fixture had zero BOQ Header/Item/Cost Analysis/Quantity Revision records and two File records. The record comparisons and schema-column checks passed; the separate populated synthetic legacy probe supplies the bounded commercial-preservation evidence. Migration initially failed twice: sidebar reconciliation ran before its linked page existed, then page reconciliation tried to save a new named Workspace rather than insert it. Both setup defects were corrected; the final migrations passed, and a real lifecycle regression covers missing-page insertion, sidebar links and repeated reconciliation. Fresh-site preservation is not proof of a populated prior-customer upgrade or timed restore.

Parent review accepted the bounded GPT-6 Luna workbook/permanence edits and corrected two read-only-review findings: Legacy Review items could otherwise be repriced, and new analyses could be approved without a recoverable legacy source. Both now fail safely and have actual regressions. No independent human review is claimed.

Final Ruff lint passes for all touched Python files. Changed/new files pass formatting checks; the unrelated existing adjacent-f-string format difference in `construction/install.py` is preserved. Schema facts were regenerated after review of the additive JSON fields; schema and context checkers pass. Whitespace checks pass. Existing framework/runtime versions and two shared Python dependency conflicts remain as described above.

Local evidence: `/tmp/customer-release-owner-candidate-suite.log`, `/tmp/customer-release-owner-http.log`, `/tmp/customer-release-owner-upgrade.log`, `/tmp/customer-release-owner-double-migrate.log`, and `/tmp/customer-release-owner-test-counts.json`. Probe scripts are deliberately guarded to the private bench. The first batch's source fingerprint is preserved in `FIRST_BATCH_TESTED_FILES.json`; `TESTED_FILES.json` binds the current candidate. No fixture credentials or private configuration are committed.

All sixteen release gaps remain tracked in STATUS.md. The owner's decisions close the missing-policy questions, not representative legacy conversion, reader consistency, browser/security/capacity/version/support/recovery gates, integration, observed GitHub CI or customer release authorization. Main checkout advanced separately to `7839e67` during this follow-up and was not edited.

Source commits: `a01ac75` (financial rules) and `efda04d` (migration setup). Both were committed with external-memory hooks disabled for those commands; documentation follows separately.

After verification, only the two private fixture servers restarted for this follow-up were gracefully stopped. Their data/configuration remain local for deliberate replay; existing site services were not stopped.

## Integrated candidate — final verification (2026-10-05)

**This section supersedes earlier candidate/environment claims for the current handover.** Earlier sections remain historical. Their `/tmp` probe scripts/logs were no longer present after a runtime restart; historical committed fingerprints remain, but those paths must not be reported as currently available proof.

Financial/security code commit: `4be0712db90897f8947199f91665275909b7652d`. Integrated candidate: `46e50cef334a4f51c9faea04c99bf9b5f7401a7f`. Main source through `7839e67` was merged before the final suite, including bilingual Desk/report work. Main advanced to `3fa285a` during verification; its later commits add population documentation/evidence only. They were merged after the suite without executing their site scripts. App source and CI bytes match the tested code commit. Subsequent handover changes affect documentation only.

### Actual final selected run

All modules below ran sequentially in `release-gaps.localhost` using the private `candidate-env`, after the thirteen compatible dependency updates and final source edits. No existing shared site was selected. [Count record](QUALIFIED_TEST_COUNTS.JSON).

| Module suffix (`construction.tests.test_`) | Passed |
| --- | ---: |
| boq_properties | 17 |
| quantity_revisions | 31 |
| variation_orders | 27 |
| cost_analysis_engine | 37 |
| cost_database_api | 23 |
| customer_release_financial_guards | 12 |
| boq_transactions | 12 |
| boq_wbs_generation | 2 |
| boq_structure_conversion | 1 |
| boq_structure_delete_safety | 1 |
| boq_excel_parser | 4 |
| boq_rollup_audit | 5 |
| bilingual_install_schema | 6 |
| boq_legacy_cost_conversion | 8 |
| boq_parent_permissions | 6 |
| bilingual_desk_link_dispatch | 17 |
| stage7_bilingual_reports | 10 |
| **Total** | **219** |

Selected JavaScript properties were rerun: **35 passed / nine suites**. Some legacy Python property cases remain placeholders. These counts do not measure complete-app coverage.

New regressions establish independent factor-aware revision/VO/report/export examples, standalone corrections and variation item projections, successive incremental VOs, approved snapshot resave/tamper refusal, the owner's physical-resource example with wastage/batch normalization, malformed workbook numeric rejection in preview and commit, absence of automatic vendor role grants and caller-transaction preservation, eight reviewed conversion invariants, and native read/write/list boundaries across six BOQ DocTypes with assigned Project permissions and the working scope filter disabled. The corrected Project Link is required for native user permissions.

Ruff lint and format checks pass on all 22 touched/new Python files; the earlier harmless adjacent-f-string formatting difference in install.py is normalized. Whitespace checks pass. Reviewed schema regeneration and final schema/context checks pass: 21 schema owners plus one override; eleven context checks. Candidate `pip check` passes. Dependency advisories remain as described in DEPENDENCY_REVIEW.md; compatibility alone is not security clearance.

### Native HTTP access checks

The actual Frappe WSGI pipeline used token-authenticated synthetic Project Manager credentials with one assigned Project. [Nonsecret result record](QUALIFIED_HTTP_ACCESS.JSON): allowed item read 200, forbidden item read 403, permission-filtered list 200 with only the allowed item, forbidden write 403, forbidden reassignment 403, allowed private file 200, forbidden private file 403, mutation GET 403, allowed mutation POST 200, forbidden mutation POST 403 and forbidden Excel export 403. Stored forbidden parent/header remained unchanged; the allowed transition persisted.

The initial probe hit the fixture test runner's maintenance mode (503). HTTP was enabled only on that disposable fixture. A second fixture error used identical attachment bytes, so Frappe deduplicated both files to the accessible content; the final probe uses distinct bytes and verifies the intended forbidden attachment. These were probe corrections, not hidden app fixes. The final probe's synthetic credential was disabled afterward; no credential is committed. This is eleven request checks for one role/project boundary, not browser evidence, a complete role/company/share matrix or production reverse-proxy validation.

### Backup, restore and repeated migrations

A populated synthetic source fixture deliberately includes legacy cost/history, two approved quantity records, a private Arabic UTF-8 attachment and an encrypted test User API secret. A native database/public-files/private-files/config backup was restored into **release-restore.localhost**, with a new database on a second isolated MariaDB server. Original encryption key was restored while new database credentials/socket were retained. The source site was preserved.

[Nonsecret recovery record](RECOVERY_EVIDENCE.JSON): backup 1.206 seconds; restore 24.858 seconds; header/structure/item/analysis/detail/file rows and two revisions hash-match. The private attachment bytes match and the encrypted secret decrypts to the expected hash. Two native migrations on the restored fixture passed; the verification passed again afterward. Source and restored read-only rollup audits match. The fixture's deliberate legacy direct database edit leaves `total_budgeted_cost` discrepant before and after restoration; that discrepancy is preserved, not repaired. This proves faithful recovery of the selected fixture, not commercial reconciliation or a representative prior-version upgrade.

Initial operator-script mistakes were corrected before success: native new-site initialization was required, and the audit's actual key is `mismatched_fields`. An initial zero-discrepancy assertion was inappropriate for the deliberately inconsistent legacy fixture; the correct criterion is exact source/restored audit equality plus row/file/secret preservation. No force overwrite or original-site repair was used.

### Isolation, reproduction and evidence

Private bench: `/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes`. Its candidate runtime, database directories and configuration are separate from existing services. Use the direct helper from that bench's `sites` directory after deliberately restarting only its retained private servers:

```bash
PYTHONPATH=/home/mohamed/frappe-bench/worktrees/customer-release-gap-fixes \
  /home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/candidate-env/bin/python \
  -m frappe.utils.bench_helper frappe --site release-gaps.localhost run-tests \
  --app construction --module construction.tests.test_boq_legacy_cost_conversion
```

Private scripts are under the bench's `private/` directory: final_verification.py, recovery_drill.py and http_access_probe.py. The latter two create synthetic data and contain exact bench/site guards; do not retarget them to customer sites. Backups/config/secrets remain private and outside Git. Final successful logs are under `logs/qualified-*`, `recovery-*`, and `final-*`. File hashes include source/test/schema/CI inputs plus successful logs and public inventory summaries. `OWNER_RULES_TESTED_FILES.json` preserves the preceding efda04d fingerprint; FIRST_BATCH_TESTED_FILES.json preserves the earlier batch.

GPT-6 Luna supplied bounded tests, read-only inventories/review and the conversion runbook. The parent reviewed the integrated diff, owned financial/security implementation, corrected discovered defects, ran the final suite/HTTP/recovery checks and committed locally with transmitting hooks disabled. No native orchestrator run, human independent release review, v15/runtime matrix, complete browser/capacity/security clearance, actual GitHub run, representative customer conversion, existing-site installation, push/deployment or customer release approval is claimed. See STATUS.md for all remaining requirements and the named-site authorization boundary.


## Named v16 source follow-up (2026-10-05)

The owner selected v16.localhost for the requested backup/isolated upgrade. [The rehearsal report](V16_UPGRADE_REHEARSAL.md) supersedes the earlier missing-source requirement. Native backup 27.965 seconds / restore 117.892 seconds; two actual candidate migrations on the copy passed. Twenty existing-column table comparisons, 48 physical files and restored encrypted auth rows match. All 219 revisions were preserved; 35 with existing parents pass unchanged native saves. A new correction/report probe and tamper/reversal refusal pass with all mutations rolled back.

The source has zero cost analyses, 184 revisions with deleted BOQ parents, and 25 client-approved VOs failing pre-existing link/PDF checks. The owner classifies these as test records. A private test archive/exclusion registry preserves their identities and evidence; original rows remain unchanged. No successful legacy VO resave or real legacy cost conversion is claimed. This is an older development-site upgrade, not operational customer-data qualification, original-site installation or customer release authority. Candidate source is unchanged from 4be0712/46e50ce; fresh whole-suite repetition was unnecessary because only operator evidence/docs changed.


## End-to-end follow-up — 2026-10-05

The earlier 219-test/46e50ce records above are historical. Main's committed bilingual statement expansion through aecef45 was merged at 10280ab; CI preparation was committed at fd218cf. The final source correction is **4f110b00dec43d70724f20eeabc94a0c4edb881f**. The separately prepared, unpublished code-only CI candidate is **a6bc51c3172255a242674576fecf96c6cfb46ac4**; byte comparison confirms all 511 tracked app/CI/package source files match. Private reports, site data, credentials and backups are excluded from publication.

### Build and tests

A fresh isolated rebuilt-env resolves 177 public requirements and three exact local editable apps with no dependency overrides; pip check passes. Frappe's declared PyPika and Gunicorn fork sources are preserved. The first attempt using PyPI PyPika failed on Python 3.14; the source declaration, corrected build and limits are in CLEAN_BUILD.md. Exact inventories/source identities are retained privately. This does not qualify deployment or remove advisories.

The first integrated run passed 225 tests before the browser/report corrections. A rebuilt-runtime follow-up passed the sixteen unchanged selected modules (209 tests); its first Stage-7 run exposed three test-harness errors from blanket module mocks while the real FY defaults accessed native ERPNext hooks. The mocks were narrowed, source defects fixed, and the final changed module passed **15 ordinary + 10 native Frappe tests**, with no skips. Thus the selected cumulative rebuilt-runtime result is **234 tests / 17 modules**. This is an affected-module rerun, not a claim that every test was rerun simultaneously at the final commit. Both counts and all OK markers were checked. Raw final count record: isolated logs/end-to-end-20261005-final-test-counts.json; changed-module log: private/end-to-end-20261005/stage7_fiscal_auth_20261005_rerun.log. The earlier failing run remains available as counter-evidence.

The five new native FY tests cover future years not hijacking 2026, historical bounds not stretching to today, explicit FY preservation, explicit complete fiscal/date-range periods without a current FY, and a missing requested FY failing closed. Five native authorization tests cover absent accounting roles, an actual accounting user allowed in their assigned Company and refused in another, Administrator access and a disabled Report refused before vendor resolution. Pure transform/default tests explicitly mock the access helper; they are not permission proof. Native user/FY fixtures roll back, and disabled Report state restores in finally.

All **35 JavaScript cases / nine suites** pass with Node 24 test isolation disabled. The ordinary isolated invocation reported only a wrapper, so CI now uses the individually qualified invocation. Syntax checks pass for the changed raw JS. Construction-only production assets were rebuilt in the private Bench; new raw theme/page assets were exercised by the browser. Ruff lint/format passes on all touched Python files, whitespace checks pass, and final schema/context checks pass (21 schema owners + one override; eleven checks / zero failures).

The rebuilt runtime repeated all **11 native HTTP** checks successfully, with the intended allowed/denied status and no forbidden parent/header mutation. The probe credential was disabled after the run. Earlier sandbox-denied local socket/build attempts were environment access restrictions; bounded local DB/cache/process access was then authorized by automatic review. No shared service was reset or replaced.

### Browser and independent review

BROWSER_VERIFICATION.md records real permitted login/list/item Save/reload, forbidden item refusal, visible zero-factor rejection and selected Arabic/English report rendering. The browser exposed a theme zone covering Save and a vendor FY default changing requested dates to a future year; both are corrected. Save is reachable at 960, 1280 and 1440 widths. The final report browser smoke uses source 4f110b0 and the rebuilt runtime; the selected Company and 2026 dates render with native HTTP 200.

A separate Luna static review verified the new native report/Company guard against installed Frappe source and identified one stale callback after the missing-Company early return; the parent moved sequence invalidation before that return. The reviewer did not execute tests or certify the whole app. The parent reviewed the final diff and actual pass logs. The browser user was disabled, API credentials cleared, original private site config restored, owned test tabs closed and loopback server stopped. Screenshots stay private. Missing realtime service, zero ledger rows and untested populated Arabic printing are explicit limitations.

### Dependencies, deployment and authority

DEPENDENCY_VALIDATION.md reconciles all 70 distinct package/advisory identities against primary sources, retains conflicting PyJWT range metadata and unverified identifiers, and traces possible PDF/auth/upload/parser use paths. The parent separately checked official pdfkit and PyJWT advisory pages. Installed-version matching is not exploit proof, and pip check/build success is not security clearance. Vendor-constrained fixes, advisory-specific mitigations, production JS and OS/native qualification remain open.

A fresh v16.localhost DB/files/config backup is retained privately. The original shared app checkout still serves localhost, v16.localhost and v16rehearsal.localhost with old schemas; the owner has not authorized the other sites' migration or chosen a separate Bench. Main remains aecef45; other-session UOM docs and dump.rdb are untouched. No original-site migration, shared runtime replacement or customer deployment occurred.

Automatic approval review rejected the attempted public CI push because public source disclosure was not specifically authorized. No upload or GitHub run occurred. The refreshed publication question names final code-only candidate a6bc51c and its public destination/branch. Await its explicit answer. RELEASE_OPERATING_PROFILE.md is a prepared engineering recommendation, not hosting/SLA approval. STATUS.md retains all sixteen acceptance requirements; unresolved security, operational scope and release checks remain open.

### Final measured capacity, integrity and handover

The separate release-capacity.localhost site contains 25 native calibration pairs and 20,000 bulk synthetic pairs across eleven headers. All ten profile header audits pass. A final read-only global check verifies 20,025 one-to-one item/leaf pairs and globally unique contiguous NestedSet bounds 1–40,050; combined contract 500,625, estimated/direct cost 400,500. Bulk item/structure seeding bypasses controllers and establishes no native write capacity.

On one representative 2,000-item header, three direct samples gave summary/revised/export-source p50 15.60/53.00/78.72 ms. The actual XLSX took 659.9 ms and produced 98,092 bytes. Read-only reopening verifies all 2,000 rows, each quantity × factor × contract unit price, and both value sums plus grand total 50,000. Five independent readers × three rounds completed 15/15 requests with p50 130.22 ms and descriptive p95 144.26 ms; process peak RSS was 189,894,656 bytes. The ordinary 118,002-byte cost workbook contained exactly 2,000 imported rows and took 313.85 ms for one dry-run parser sample, without business writes. CAPACITY_PROTOCOL.md records exact environment, raw paths, failed attempts and sample limits. This is no HTTP/worker/mixed-role/customer-write/SLA qualification.

The parent reviewed the final raw capacity JSON, separate XLSX/global-integrity JSON and agent conclusions. No capacity driver remained active. The private Redis exited successfully; both task-owned MariaDB processes received SIGTERM only after exact PID/owner/datadir verification and exited gracefully. The browser loopback server and credentials were already cleaned up. Private service-cleanup-20261005.json records ownership-limited shutdown. Shared services, original sites and unrelated files were preserved.

SECURITY_UPGRADE_PATH.md identifies official upstream candidates and remaining constraints, without claiming a resolved or tested upgrade. END_TO_END_TESTED_FILES.json binds the current source files, selected test log counts/hashes, private build/advisory/capacity/browser evidence and cleanup record. Documentation committed after source 4f110b0 changes no tested app bytes; the unpublished a6bc51c candidate still matches all 511 app/CI/package files and four additional build/install manifest files. Historical TESTED_FILES.json and previous failed logs remain untouched.
