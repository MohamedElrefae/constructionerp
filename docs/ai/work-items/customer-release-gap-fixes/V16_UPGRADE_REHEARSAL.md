# Authorized v16 upgrade rehearsal and test-history separation

**2026-10-05. The owner selected `v16.localhost` for the backup/isolated-upgrade work.** The source site's commercial data and schema were not changed. The candidate migrated its private restored copy twice successfully. This is development-site qualification, not customer release approval or installation on the original site.

## Result

- Full native database/public-files/private-files/config backup completed in **27.965 seconds**. Private files are mode 0600 under a mode-0700 directory, outside Git.
- Restored to `release-v16-copy.localhost` in a separate private Bench/database/cache in **117.892 seconds**, retaining the backed-up encryption key and using new database credentials. Scheduler was disabled; no existing site was overwritten.
- Candidate code is `4be0712db90897f8947199f91665275909b7652d`, with integrated source `46e50cef334a4f51c9faea04c99bf9b5f7401a7f`; current task checkout at rehearsal start was `6a5634be76e7f52bb82c546ed8900d4d7d2e8b8d`. The latter adds documentation only. Vendor source/runtime matches the previous verification. No app source changed in this follow-up.
- Both native migrations passed. The old site lacked the cost-basis/provenance and factor-snapshot fields; the copy now has them, and BOQ Header.project is a Project Link.
- Existing-column hashes match for **twenty tables**, including 23 BOQ headers, 59 structures, 34 items, 219 quantity revisions, 34 VOs/27 VO lines, 119 File rows, Company/Project/Item/customer/supplier masters, six User Permissions, 4,033 Sales Invoices, 1,008 Purchase Invoices and four GL Entries. No legacy commercial amount, status, approval attribution, name or stored link in those compared rows was rewritten.
- All **48 stored files** and encrypted authentication rows in the restored baseline stayed unchanged through the migrations and rolled-back acceptance probes. The new isolated site's Administrator password is deliberately separate; this comparison is against the restored baseline, not a promise of preserving login credentials for a new deployed site.
- Before/after read-only audits: zero BOQ header/structure rollup discrepancies, invalid/missing factors or broken Header→Project links. No financial repair was needed or performed.
- All **35 approved revisions whose BOQ parents exist** passed native unchanged saves, retaining the frozen evidence. Quantity tampering and Approved→Rejected reversal were refused. One new correction was approved using the factor/version rule and appeared correctly in the current report; the complete acceptance transaction was rolled back, and final data/file/hash comparisons still passed.

## Historical test records

The real backup exposed **184 of 219 approved quantity revisions with missing headers, structures and items**. They are preserved, but cannot pass native link validation on save. Because all old-column hashes match, these missing relationships were not introduced by migration.

All **25 client-approved VOs** failed native existing checks: one has missing linked BOQ records; nine lack a signed approval reference; fifteen reference an unregistered PDF. No client-approved VO native resave is reported as passing. The PDF-gate function's AST is unchanged between the source-site code at `3fa285a` and this candidate, so these checks are not a new migration requirement. We did not fabricate signatures, approvals or missing parents.

The owner explicitly classified these records: **“Test records; preserve them and separate them from operational data.”** Accordingly:

1. The full original backup, old-schema row hashes and copies remain private.
2. A separate test-only archive retains the 184 revisions, 25 VOs and their 25 child rows. An exact-ID exclusion registry identifies those records and binds the archive and source backup hashes.
3. These artifacts must never seed a customer/operational database or release fixture. The current app fixture hook exports system themes, not BOQ/VO business data.
4. Original rows in `v16.localhost` are still intact. Archive/exclusion separation does **not** add an in-app archived-record flag or automatically remove test effects from that site's projections/reports. Do not present this development site as a clean operational/customer database.
5. If selective operational migration is later required, review the complete parent/child dependency graph and resulting projections on a new copy; filtering approval rows alone can leave inconsistent totals. No generic customer conversion, destructive cleanup or history reversal is authorized by this test classification.

There are **zero BOQ Cost Analyses** in this source backup. The reviewed legacy-cost conversion helper therefore had no real records to convert. Its existing eight synthetic regressions still supply the conversion evidence; this rehearsal does not qualify a populated legacy cost-analysis upgrade.

## Evidence, isolation and continuation

[Nonsecret summary and hashes](V16_REHEARSAL_EVIDENCE.json) binds the public candidate bytes and private local logs/scripts. Private operator artifacts are under `/home/mohamed/frappe-bench/release-tests/customer-release-gap-fixes/private/v16-upgrade-20261005/`: backup/source-state, baseline, before/after audits, comparison, acceptance, test-history archive/registry and logs. Record identities, source config/encryption key and backup contents remain outside Git. No fixture credential or commercial record is committed.

The standalone scripts assert the exact private Bench/site. Restore refuses an existing destination; native migration, read-only audit, snapshot comparison and rolled-back acceptance are separate steps. A first acceptance attempt exposed native missing-parent validation; the corrected probe explicitly excludes orphaned revisions and reports every invalid VO rather than bypassing validation. The final post-acceptance comparison is successful.

The source original remains on the previous schema/code, with maintenance mode unchanged. At final inspection main advanced to `890ae14` (wave-2 population evidence) and has unrelated uncommitted bilingual report API/viewer/test changes plus untracked work-item/RDB files; these were preserved. The rehearsal represents the earlier backup snapshot and tested candidate, not those later live/source changes; no shared checkout advance, original-site migration, reset, reinstall, production deployment or push occurred. Only the two private services restarted for this rehearsal were stopped afterward, preserving their data and backups.

Original-site application would require a coordinated reviewed rollout of shared app code and site schema. Advancing main changes the app used by the Bench's other sites and the concurrent task; do not replace that operation with a migration-only partial install. No additional permission is needed to use the already named source for this rehearsal. Broader site/deployment/customer-release actions and unresolved security/UI/capacity/CI gates retain their actual boundaries.

## Files read and startup

Actual task checkout: customer-release-gap-fixes, branch codex/customer-release-gap-fixes; startup HEAD 6a5634b, clean. Main HEAD 3fa285a with the unrelated untracked bilingual-wave2-group-masters-population work item; preserved.

Read AGENTS.md; Professional Engineering Standard sections 1–3 and 12; SESSION_MEMORY current release entry; CONTEXT_INDEX; SCHEMA_FACTS summary and relevant BOQ fields; root AGENT_WORKFLOW; current work-item PLAN; architect inbox template; gap report G12–G14; current pricing/version patch, quantity/VO controllers and revision service; relevant hooks/fixtures; installed Frappe init/config/installer. Schema checker passed (21 owners, one override); context checker passed (eleven checks). Local checks are not remote freshness or whole-app certification. This is direct owner-authorized consultant work, not a native orchestrator cycle or independent human review.
