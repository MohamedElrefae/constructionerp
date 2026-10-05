# Construction ERP — customer-release and private CI handoff

**Snapshot:** 2026-10-05 19:40 Africa/Cairo (16:40 UTC).  
**Purpose:** Continue the existing customer-release work without repeating completed investigation or losing the owner's decisions.  
**Current conclusion:** The private repository exists, the approved application source is uploaded, and actual provider CI has run. Fresh installation succeeded in run 7. **Run 8 is still in progress; no passing provider CI result is established. Customer release is not approved.**

The owner interrupted the CI investigation to request this handoff. Do not interpret that interruption as a CI failure or cancellation: the GitHub run continues remotely. Check its current state before changing anything or starting another run.

## 1. First action for the next agent

Open [CI run 8](https://github.com/MohamedElrefae/constructionerp-private/actions/runs/37342111971), job [111871477488](https://github.com/MohamedElrefae/constructionerp-private/actions/runs/37342111971/job/111871477488). It runs commit **116562f95fc9625df82b0cceb12c094337337a05** on `codex/customer-release-ci-20261005`.

At the snapshot, GitHub showed **In progress**, about four minutes after the Server job started at 19:36 Africa/Cairo. Obtain the completed provider result and logs. Do not push a new commit merely to check progress: workflow concurrency cancels an older run when a new one is queued on this branch.

Then read the local instructions and capture actual checkout state:

```bash
cd /home/mohamed/frappe-bench/worktrees/customer-release-gap-fixes
git status --short
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
python3 scripts/schema_drift_checker.py
python3 scripts/ai_context_check.py
```

Read `AGENTS.md`, `SESSION_MEMORY.md`, `docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md`, `docs/ai/CONTEXT_INDEX.md`, root `AGENT_WORKFLOW.md`, relevant `docs/ai/SCHEMA_FACTS.md`, and `docs/ai/templates/PLAN.md`. The root workflow is the real file; `docs/ai/AGENT_WORKFLOW.md` does not exist. Also read this report, [PRIVATE_CI.md](PRIVATE_CI.md), [STATUS.md](STATUS.md), [VERIFICATION.md](VERIFICATION.md), and [owner confidentiality policy](../../OWNER_CONFIDENTIALITY_POLICY.md).

## 2. Owner decisions and authorization

The owner explicitly authorized:

> Yes, I authorize you to create the private GitHub repository MohamedElrefae/constructionerp-private, upload the reviewed code-only candidate a6bc51c, and run CI. Keep private reports, credentials, backups and site data excluded.

This named authorization is already satisfied for creation/upload and remains applicable to completing this candidate's CI and bounded CI setup corrections. Do not ask for it again. Preserve its exact content/destination boundary; do not treat it as authorization to upload arbitrary future app changes or document-bearing history.

- **Confidential implementation:** no new private source/findings in public repositories, PRs, issues, memory services or alternate destinations. The earlier public push was rejected; that route is superseded.
- Routine software choices are delegated to the parent consultant. Ask the owner for actual construction/commercial workflow decisions, consequential hosting/rollout choices or missing authority, after preparing a concrete reviewable result.
- Use **GPT-6 Luna for bounded/light subagents** to conserve quota; retain parent review for financial/security/release decisions. Report actual review scope. Do not create separate user-owned chats for subtasks.
- The owner approved work on **v16.localhost**. This does not authorize migrations of other original sites or merging release code into their shared checkout.
- The owner classified **184 approved revisions with missing BOQ parents and 25 client-approved VOs with invalid link/PDF evidence as test remnants**: preserve them and separate them from operational inputs. Do not delete or represent them as qualified customer data.
- No customer deployment, public visibility change, license change, shared-site rollout or customer-release certification has occurred.

Confirmed financial rules, already implemented/tested in the release candidate:

| Rule | Owner's decision |
| --- | --- |
| BOQ factor | Must be positive; reject zero, negative and nonfinite values. Missing factor defaults to one. |
| Margins | Add profit + overhead + tender tax allowance, then apply once to direct cost: 100 + 10% overhead + 10% profit = 120. Do not compound to 121. |
| Resource quantities | Factor changes physical quantities and values: quantity 10 × factor 0.5 × analysis consumption 1 = 5 units. |
| Cancellation | Restore eligible prior approved or captured manual values, including legitimate zero manual costs. |
| Approved history | Immutable; corrections use new revisions. |

Tender tax allowance is a pricing rule, not evidence of invoice-tax legal compliance.

## 3. Exact locations and Git state

| Checkout/location | Role and observed state |
| --- | --- |
| `/home/mohamed/frappe-bench/apps/construction` | Main app, another chat's active checkout. Branch `develop`; HEAD **3e871f01522b81d27680e321e1dfeb7c5dc2cf23** at snapshot. Do not merge the release app into it. |
| `/home/mohamed/frappe-bench/worktrees/customer-release-gap-fixes` | Primary continuation worktree. Branch `codex/customer-release-gap-fixes`; HEAD **40a03fa811bee685f70ceeec0653b77741b4f268**. Contains app candidate, committed CI corrections and local uncommitted reports. |
| `/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes` | Isolated test Bench/evidence. Its task-owned database, Redis and web services were stopped earlier; private fixtures/evidence retained. No need to restart it just to inspect GitHub. |
| `/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/private/end-to-end-20261005/code-ci` | Original reviewed local candidate, detached **a6bc51c3172255a242674576fecf96c6cfb46ac4**. Its original remote is public; do not push this checkout. |
| `/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/private/private-ci-20261005/repo` | Independent, clean, history-free private publication checkout. HEAD **116562f95fc9625df82b0cceb12c094337337a05**, branch `codex/customer-release-ci-20261005`; clean at snapshot. Use this checkout for approved CI publication. |
| `/home/mohamed/frappe-bench/worktrees/scope-context-portability` | Separate orchestrator/workflow worktree from previous work. Do not confuse it with the release candidate or claim this direct collaboration ran through the native orchestrator. |

Main currently has these task-owned uncommitted files: `SESSION_MEMORY.md` and `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`. Preserve unrelated untracked production-migration/UOM briefing and work-item documents, plus `dump.rdb`; other chats are advancing main, so recheck status rather than relying on this list.

Release currently has task-owned uncommitted changes to `SESSION_MEMORY.md`, `docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`, and work-item `CI_READINESS.md`, `PLAN.md`, `STATUS.md`, `VERIFICATION.md`. `PRIVATE_CI.md` and this handoff are new/untracked. The interrupted Luna documentation pass had updated the main narrative through run 8; check secondary tables for stale run references before finalizing. **These documentation changes are not committed yet.**

For local commits, disable transmitting hooks **per command**:

```bash
git -c core.hooksPath=/dev/null commit -m '...'
```

The normal post-commit hook can send private metadata to an external memory service. Do not run it or disable repository-wide hooks for other chats. Stage only reviewed task-owned files; never use a broad `git add .` in the main checkout.

## 4. Completed private publication and CI work

[MohamedElrefae/constructionerp-private](https://github.com/MohamedElrefae/constructionerp-private) was created under the named personal owner, verified **Private** before and after upload, with no added collaborators or organization membership. No public upload occurred in this task.

The clean export has a different SHA because private documentation and inherited history were removed. Application source remains the approved candidate; no application logic or test assertions were changed during this CI investigation.

- Initial independent root: **11c48b2d9223153c83a6523261f625e484506f30**, 569 exact-byte source/build files; 1,066 tracked files and inherited history omitted.
- Initial export included two obsolete 917-byte `.bak` Workspace Sidebar source fixture templates. They were inspected as source layout templates without site records or credentials and removed from the current tree. Their historical root remains; do not claim every backup-named file was absent from historical Git. Private site backups/data were excluded.
- Current tree has **569 files**: **566 unchanged original non-workflow files**, corrected workflow and two CI helpers. The retained original files were byte-compared with `a6bc51c`.
- Reports/docs, site/configuration/database data, private backups, credentials and unrelated untracked files remain excluded. Logs and this handoff are local only.
- Keep the export's local `.git/info/attributes` setting `* -text`: it prevents line-ending normalization of the reviewed bytes. The original export required preserving tracked ignored files and CRLF source bytes.

Committed CI corrections mirrored in the release worktree:

| Release commit | Change |
| --- | --- |
| **042032a** | Pin ERPNext before installing/building its assets. |
| **3feccfc** | Bound Construction installation and retain failure diagnostics; correct Bench verbosity position. |
| **ef1986a** | CI-only stack/progress probe and database snapshot; longer bounded full installation. |
| **40a03fa** | Guarded synthetic business fixtures and collection of all selected Python/JS results. |

Harness behavior at run 8:

- Ubuntu 24.04, Python 3.14 (provider resolved 3.14.7), Node 24, MariaDB 10.11 and disposable Redis services. The earlier qualified local runtime used Python 3.14.5; do not imply they are identical environments.
- Exact Frappe **81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0** and ERPNext **2807c9f08fff3f161c0a2e10745a26aa6331ffd5** are asserted. ERPNext is fetched/pinned before `bench get-app --skip-assets` installs it.
- Job cap 45 minutes; Construction install cap 1,800 seconds, with abort diagnostics and a final kill bound. Failed installation remains a failed gate.
- `.github/ci/install_stack_probe/sitecustomize.py` is activated only for the disposable CI installation command. It prints filenames/functions and five specifically allowlisted numeric import counters; no translation content or arbitrary frame locals. Normal app execution/tests do not enable it.
- `.github/ci/business_fixtures.py` rejects non-GitHub Actions, sites other than `test_site`, or missing `allow_tests` before DB access. It creates/reuses only synthetic `_Test Company` with EGP/Egypt/Standard chart, ensures ERPNext's Transit Warehouse Type, saves native Global Defaults, verifies identity/defaults and commits. Unexpected Companies or mutation failures fail/roll back. No Fiscal Year is seeded by this helper; tests that need special years create them.
- Seed invocation uses a scoped `PYTHONPATH` and the trusted Bench execute expression `__import__('business_fixtures').seed()`. Plain `business_fixtures.seed` would be rejected as an uninstalled app by native `frappe.get_attr`; the expression uses Bench's supported CLI evaluation path.
- All **17 Python modules** are still selected. The loop collects failures but exits nonzero if any module fails. The independent JS step runs after successful installation even if Python tests fail. No assertions are disabled or skipped to obtain green CI.

Local harness verification passed Python AST parsing, YAML parsing and `bash -n` for workflow blocks, whitespace checks, default-disabled probe/timer checks, and all three fixture authority guards before DB access. **Native fixture execution and final regression success still depend on run 8.**

## 5. Actual provider evidence

| Run | Uploaded SHA | Observed outcome |
| --- | --- | --- |
| [1 / 37330205489](https://github.com/MohamedElrefae/constructionerp-private/actions/runs/37330205489) | `11c48b2` | Failed before tests: building the moving ERPNext branch changed `banking/yarn.lock`, preventing later pinned checkout. |
| [2 / 37333165347](https://github.com/MohamedElrefae/constructionerp-private/actions/runs/37333165347) | `2f054fe` | Parent canceled after Construction stopped producing visible progress; no tests. |
| [3 / 37334550063](https://github.com/MohamedElrefae/constructionerp-private/actions/runs/37334550063) | `c0ac25c` | Diagnostic command error: `--verbose` in an unsupported position; exit 2 before Construction installation. Corrected. |
| [4 / 37335468850](https://github.com/MohamedElrefae/constructionerp-private/actions/runs/37335468850) | `80d6d20` | Construction hit the 300-second cap, exit 124; no tests. |
| [5 / 37337011288](https://github.com/MohamedElrefae/constructionerp-private/actions/runs/37337011288) | `e8f95af` | Same cap, exit 124. One SQL sample showed no lock wait; not proof about every instant. |
| [6 / 37338321317](https://github.com/MohamedElrefae/constructionerp-private/actions/runs/37338321317) | `9ba74e4` | Canceled by concurrency when run 7 superseded it. Captured 46-frame caller path in the released-translation importer. |
| [7 / 37339470201](https://github.com/MohamedElrefae/constructionerp-private/actions/runs/37339470201) | `8ddea9f` | **Fresh installation passed.** First Python module had 17 setup errors: no Company, so Project.company was missing. Remaining Python modules and JS did not run. Workflow failed, 12m54s. |
| [8 / 37342111971](https://github.com/MohamedElrefae/constructionerp-private/actions/runs/37342111971) | `116562f` | **In progress at handoff.** Includes guarded synthetic Company/defaults and full failure collection. |

Run 7 proves the previous apparent stall could finish with more time: native Construction installation took about **7m27s**; the whole Install step including ERPNext/build took **9m41s**. Packaged import progress was 281 creations at 45 seconds, 1,632 at 180 seconds, and 3,458 at 360 seconds, followed by successful installation.

Source review identifies a plausible performance cause: all 4,337 released Arabic rows use a path that globally clears Frappe caches after every successful upsert. The next row's timestamp/validation can reload System Settings and metadata. This is an observed repeated expensive path; no deadlock or recursive loading bug was established. The timeout change does not optimize the app.

Retained local evidence directory:

`/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/private/private-ci-20261005`

It contains `publication-manifest.json`, `run1-10_Install.txt`, `run2-10_Install.txt`, `run4-10_Install.txt`, `run5-10_Install.txt`, `run6-10_Install.txt`, `run7-10_Install.txt`, and `run7-12_Run Python Business Regression Tests.txt`, plus private repository screenshots. There is no run-8 completion log yet. Do not upload these files with source.

## 6. Earlier release work already completed

These are previous local results, distinct from current GitHub CI:

- Financial/revision corrections, positive-factor validation, additive margins, factor-aware resource/report/export quantities, cancellation restoration and immutable history. See [FINANCIAL_RULES.md](FINANCIAL_RULES.md), [TRANSACTION_PROTOCOL.md](TRANSACTION_PROTOCOL.md) and [VERIFICATION.md](VERIFICATION.md).
- Selected rebuilt-runtime evidence: **234 Python tests across 17 modules**, cumulatively combining 209 passes in 16 unchanged modules with 25 final changed report-module tests. This was an affected-module rerun, not a simultaneous whole-suite run at final HEAD. **35 JavaScript cases across nine suites** and **11 native HTTP checks** also passed locally.
- Browser corrections verified native Save/reload for 10 × 0.5 × 100 = 500, zero refusal, forbidden-item access, accessible Save at 960/1280/1440 widths, native Company/report boundaries and requested fiscal-period behavior. See [BROWSER_VERIFICATION.md](BROWSER_VERIFICATION.md).
- Fresh isolated exact-source dependency rebuild passed installation and `pip check`; exact upstream PyPika/Gunicorn fork sources retained. See [CLEAN_BUILD.md](CLEAN_BUILD.md).
- Named v16 backup/restore/upgrade rehearsal preserved compared records/files/authentication and classified test remnants. It did not migrate original shared sites or qualify real customer legacy data. See [V16_UPGRADE_REHEARSAL.md](V16_UPGRADE_REHEARSAL.md).
- Capacity evidence: 20,025 synthetic item/structure pairs, global tree/amount checks, actual 2,000-row XLSX generation/validation (659.9 ms), and 15 successful concurrent reads. Bulk seeding bypassed native controllers; these are Administrator read/export measurements, not customer write capacity or an SLA. See [CAPACITY_PROTOCOL.md](CAPACITY_PROTOCOL.md).
- Security reconciliation: 108 raw scanner rows reduced to **70 distinct package/advisory identities** whose affected ranges included installed versions. This is not proof of 70 reachable exploits, nor a resolved-security claim. See [DEPENDENCY_VALIDATION.md](DEPENDENCY_VALIDATION.md) and [SECURITY_UPGRADE_PATH.md](SECURITY_UPGRADE_PATH.md).

Preserve historical evidence manifests, including `END_TO_END_TESTED_FILES.json`. The workflow has legitimately changed since its historical hash binding; record a new harness/current-CI bridge rather than overwriting old hashes to make them match.

## 7. Remaining work, in execution order

1. **Finish provider CI evidence.** Observe run 8 to terminal state; retain logs privately. Record exact SHA/ref, fixture outcome, all 17 module outcomes/counts, JS counts and any failures. A red run is evidence, not permission to suppress a check. If it fails in fixtures, repair the bounded synthetic setup and rerun. If it identifies a real app defect, prepare/review/test the correction locally and respect the approved publication scope for any new application candidate.
2. **Finalize local records and commits.** Update `PRIVATE_CI.md`, `CI_READINESS.md`, `STATUS.md` (including G07), `PLAN.md`, `VERIFICATION.md`, session memory, confidentiality policy and the private publication manifest with the actual run result. Stage only task-owned files. Main's two owner/session documentation changes and the release reports still need local commits with transmitting hooks disabled. Verify outgoing original source hashes, private destination and exact remote SHA; keep reports/private logs local.
3. **Qualify dependency-security resolution.** Choose supported vendor/dependency upgrades or effective advisory-specific mitigations and verify them against official sources and representative functionality. The existing upgrade-path document is a plan, not a security fix. Review production JS/native OS/PDF/authentication packages too.
4. **Complete sold workflow and permission coverage.** Test populated Arabic/English analysis, approval, cancellation, variation, report, print/export and import routes with customer roles/Companies/shares/attachments. Realtime and populated Arabic print quality remain unqualified. Complete financial consumers and representative operational legacy conversion if migration is offered.
5. **Measure the chosen deployment workload.** Validate mixed customer-role reads/writes, database/queue/worker contention, memory, admitted workbook shapes, proxy limits and representative customer data on the selected hosting stack. Existing synthetic read/export measurements do not set a customer SLA.
6. **Resolve original-site rollout authority.** `localhost`, `v16.localhost` and `v16rehearsal.localhost` share the main app source and older schemas. Obtain the owner's choice of coordinated backup/migration for the affected sites or a separate Bench for v16; prepare the concrete migration/recovery plan before asking. No authority exists for the other original sites. Reconcile later main commits before any integration; do not assume the release worktree is current main.
7. **Finalize hosting/support and release acceptance.** The owner has not decided the delivery model. Confirm supported version matrix, site isolation, operator responsibility, off-host backups/retention, monitoring, support and validated recovery objectives. Self-hosted customers with server access can inspect Python; browser-delivered JS is inspectable. Use [RELEASE_OPERATING_PROFILE.md](RELEASE_OPERATING_PROFILE.md) for concrete choices. Close each relevant gate in [STATUS.md](STATUS.md) and the [customer gap report](../../CUSTOMER_RELEASE_GAPS_2026-10-04.md) with evidence before customer release.

A separately reviewed performance improvement should batch/defer packaged translation invalidation while preserving immediate single-row edit behavior, native lifecycle/permissions, quorum, version checks, site overrides, duplicate convergence and transaction/cache consistency. Measure clean/repeat import time and cache clearing. It is **not implemented** in this candidate; do not bypass Arabic import to obtain green CI.

## 8. Practical continuation constraints

- GitHub creation/status/download used the signed-in in-app Browser because no `gh` CLI or GitHub connector was available. Use the Browser skill's supported runtime/UI; do not extract browser tokens/cookies or install a connector merely to bypass a boundary. Browser variables from this chat will not exist in a new chat; initialize its documented runtime afresh.
- Actual publication used SSH from the clean export checkout to the explicit private repository URL, with command-local disabled hooks and batch mode. Never push the main/release/original candidate checkout to its existing public origin. Reconfirm Private before any continuation upload.
- No customer/site backup was sent to GitHub. CI creates its own synthetic database; do not seed it using private site dumps or records.
- The isolated test Bench is preserved but stopped. Do not kill/start unrelated Bench services. Starting it for a necessary new local check requires identifying its private ports/processes and reusing its own operating instructions.
- This handoff is a timestamped snapshot. Current repo/site/provider state wins over memory and older reports. No agent should represent documentation, local passes, a partially completed run or a generated plan as production readiness.
