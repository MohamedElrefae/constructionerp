# Foundation inspection — isolated provisioning, install, recovery and regression evidence

Date: 2026-10-15. Private engineering report; no customer publication or production approval.

## Outcome

The DBA-password dependency has been removed for local inspection. A user-owned MariaDB instance and two private Redis services support isolated qualification. Shared MariaDB credentials and privileges were not changed; existing sites were not restored over or reinstalled. Rehearsal application credentials were deliberately rotated as the previously owed operator action.

Program HEAD: `fa380226d641f32f749c7ae003f82eeb6404ba2c` plus the current uncommitted foundation changes. Qualification is local snapshot/curated-source testing, not final committed `bench get-app` delivery. The full prepared test tier ran locally; no GitHub Actions/cloud result is claimed.

## Environment and isolation

- Lab: `/tmp/construction-foundation-lab-20261014` (mode 0700; volatile scratch storage).
- Private MariaDB 10.11.14 uses the lab data directory and Unix socket; networking disabled. Generated lab credentials remain in a local mode-0600 file, outside app/customer artifacts.
- Private Redis: loopback 16379/16380. Original Redis/database services and default-site configuration were not restarted or changed.
- Frappe source: installed 16.51.1 / `2871914`; ERPNext source: clean archive of pinned 16.50.0 / `7474d9e`. Construction imports from the curated lab copy. Existing Python runtime reused; shared Bench dependencies were not upgraded.
- The shared ERPNext checkout has unrelated/unreviewed Company JSON/Python changes, including a broad Cost Database Maintainer Company grant. They were preserved and excluded from clean-vendor qualification. F38 must reconcile them before the shared bench is described as vendor-clean.
- An initial lab on `/home` ran out of space. Only its incomplete generated SQL copy was removed; the lab was moved to `/tmp`. `/home` still has approximately 430 MiB free and needs an operational capacity review. No user backups or unrelated files were deleted.

## F31 local qualification

**Fresh:** `f31fresh-clean.localhost` was created from an empty private database, installed Frappe/ERPNext/Construction through native installer APIs, and passed migration twice. Scope default ON; import/stage flags retain shipped defaults. Native fresh creation and migration logs are retained.

**Upgrade:** `f31upgrade.localhost` was restored from verified rehearsal backup `20261014_234948`, with database, public/private files and encryption configuration. The earlier F02 backup named in the plan is unavailable; this is explicitly different origin coverage. The copied dataset contains 36 headers, 94 items, 162 structures, 12 analyses, 235 revisions, 45 VOs and 188 File records, including Draft/Approved/Superseded/Cancelled analyses.

The first copied-site migration failed closed on four existing translation-provenance conflicts. An operator-only, non-whitelisted canonical adoption helper now permits **only identical already-released text**, preserves runtime row identity, records the actual operator/decision, and refuses conflicting text or ordinary users. Six retained native tests pass. Four approved provenance corrections were applied only to the lab copy. Migration and replay then passed. All eight financial/history table hashes remained unchanged. Scope was explicitly restored from the backup's OFF state to the approved ON posture.

Fresh testing exposed five workspaces and the maintainer role identity existing only on rehearsal. Five standard app-owned Workspace JSONs now ship; the idempotent app role seeder creates the maintainer identity **without grants or assignments**. Clean fresh checks find all six intended workspaces and no broad maintainer Company rights. Explicit native grant setup is documented in `docs/PERMISSION_SETUP.md`; production activation remains separately gated.

F31 is locally qualified within the stated scope. Final committed-route qualification, configured fresh ordinary-user workflow coverage and any additional supported upgrade origins remain required before full closure.

## F32 controlled recovery

A native backup of the copied site included database, files and configuration; exact app code was separately archived. A lab-only after-migrate hook committed an intentionally wrong header total and raised, and one backed-up private PDF was removed. No injection entered program source.

Recovery restored matching code, database, public/private files and configuration without a compatibility-force bypass. Comparisons prove:

- All eight business/history table hashes and record counts equal the pre-failure state.
- Settings and configuration equal the backup, including scope ON.
- File records/content equal the pre-failure snapshot; restored code had zero archive mismatches.
- Site-bound WSGI login returns Administrator; private PDF download succeeds (3,236 bytes), Guest receives 403 without PDF bytes, before and after recovery.

A separate timed restore measured **138.907 seconds for database/files restoration**, excluding operator response and code-restore time. This is observed lab evidence, not a customer RTO/SLA.

Of 188 File records, 132 available local contents match rehearsal byte-for-byte. **54 local paths are already absent on the source site**; none is a restore-introduced loss. Their operational/test classification and recovery impact remain F10/F38 work. Existing incorrect legacy financial values were preserved, not silently repaired.

## Security and regression corrections

Company-wide construction reports now enforce selected-company scope in addition to native Company read. Protected File mutation checks examine stored and requested attachments. Standalone generated exports require their owner plus current Company/scope and source-row authorization; protection metadata cannot be renamed away by ordinary users.

Seven retained native regressions pass; four fail on pre-fix modules with valid request isolation. Native File resolution already protects nonowners of private unattached files: this review does **not** claim a reproduced generic nonowner leak. The additional controls close selected-scope and mutable-parent/protection gaps. Positive fixtures were given valid scopes; dedicated missing-scope denials remain. Per-request cache reset and exact test-fixture cleanup were corrected without weakening product guards.

## F35 and artifact evidence

- Prepared full tier: **19/19 modules, 236 native tests**, derived from actual successful logs; required skip markers: 0.
- Initial matrix was 18/19 because my lab asset copy omitted the built manifest. Actual vendor assets were copied, private cache warmed (70 entries), and only the failed 27-test VO/PDF module rerun successfully. Initial failure logs/results are retained separately.
- Directly affected suites additionally verified 56 outcomes. New regression modules are registered in prepared smoke/full CI lists. No remote CI upload/execution occurred; final matching private workflow/committed-candidate gates remain open.
- Final wheel and sdist were built with **flit_core 3.12.0**, inside declared `>=3.4,<4`, in a private tool directory. Both have 1,244 members and zero source maps. Hashes: [compliant build evidence](isolated-qualification-evidence-2026-10-15/compliant-build.json).
- Curated staging verifies 1,252 hashed customer files, required files and relative documentation links. It is unpublished preparation, not delivery approval. Earlier snapshot/artifact hashes are superseded by this turn's changed source and docs.

## Rehearsal operator action

Rotated only rehearsal Administrator and 16 known inspection-persona accounts. All **17/17 real site-bound logins** passed. Passwords are stored under the protected bench-local `.inspection-credentials` directory, never in chat, repository evidence or customer artifacts. No database/root passwords, roles, Company grants or other-site accounts changed. Rehearsal counts remain 36/94/12/235/45.

## Current gate disposition and next execution

The operator does not need to supply a shared DBA password for the lab. Use its private services for remaining F33/F34/F37 engineering work. Maintain positive site binding and preserve rehearsal owner-UAT fixtures. F41 operator walkthrough and F43 preparation follow engineering readiness; F44 remains Mohamed's consolidated final block, and F45 remains open.

Do not call the plan fully complete: F38 must reconcile the vendor Company edits, absent source files and remaining defects; F27 stays operators-only; publication/customer delivery and final committed-route qualification remain separate. The 19-module local tier is real evidence, not a claimed GitHub job. No program commit, push, publication or existing-site overwrite occurred.

## Evidence preservation

[Evidence folder](isolated-qualification-evidence-2026-10-15/) retains nonsecret methods, baseline/result JSON, hashes and native logs. Credentials, site configurations and backup contents are not copied there. Initial failed results remain; successful rerun summaries are separately derived from actual logs. Automatic approval review rejected a command that would have overwritten a prior failed summary; the safer append-only evidence method completed successfully.

Startup/context: AGENTS.md, professional standard, workflow, schema facts, context index, active memory and relevant foundation plan/evidence were read. Schema check passes 21 owners + 1 override; context check passes 11/0. Unrelated orchestrator/living-document changes and shared vendor edits were preserved.

Final repository whitespace check still reports CRLF endings on the pre-existing ten-line `pyproject.toml` sdist addition. Those packaging bytes were preserved; this is not a runtime-test failure or a clean-diff claim.
