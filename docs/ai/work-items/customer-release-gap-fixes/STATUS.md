# Customer release corrections — current status

**2026-10-05: local corrections and selected qualification are complete; customer release remains withheld.** This is the current ledger. [Prior milestone history](STATUS_PRIOR_INTEGRATION.md) retains earlier observations; it is not the current candidate identity.

Source candidate: **4f110b00dec43d70724f20eeabc94a0c4edb881f**, branch `codex/customer-release-gap-fixes`, worktree `/home/mohamed/frappe-bench/worktrees/customer-release-gap-fixes`. Main's committed bilingual expansion through **aecef45** was merged before qualification. The prepared code-only public-CI candidate is **a6bc51c3172255a242674576fecf96c6cfb46ac4**; all 511 tracked app/CI/package source files match. It is local and unpublished. Documentation and private evidence are excluded from that publication candidate.

## New completed evidence

- The fresh isolated runtime installs all 177 public requirements plus three exact local app sources and passes `pip check`. Frappe's exact PyPika and Gunicorn fork pins are retained. [Clean build](CLEAN_BUILD.md).
- Selected cumulative rebuilt-runtime evidence: **234 Python tests in 17 modules**, including 25 final report/date/authorization tests, **35 actual JavaScript cases in nine suites**, and **11 native HTTP access checks**. The sixteen earlier passing modules retained unchanged affected behavior; the changed report module was rerun. [Verification](VERIFICATION.md).
- Browser testing found and corrected a theme control covering Save and a future fiscal year overriding a requested 2026 period. Native Save/reload produces 500 for quantity 10 × factor 0.5 × rate 100; zero is refused with a visible native validation message. Save is reachable at 960/1280/1440 widths. Final report smoke passes with native Report/Company gates. [Browser evidence and limits](BROWSER_VERIFICATION.md).
- The bilingual endpoint now honors native Report roles, report permission, disabled state and Company read permissions before vendor execution. Real accounting-user Company allow/deny and disabled-report tests pass. Static independent Luna review found a stale response race; the parent corrected it.
- Full primary-source reconciliation reduces 108 scanner rows to **70 distinct package/advisory identities**. Current GitHub affected ranges include the installed versions for all 70. Conflicting/unverified aliases are retained. This is package matching, not proof of 70 reachable app exploits, and it does not close security. [Dependency validation](DEPENDENCY_VALIDATION.md).
- [Capacity results](CAPACITY_PROTOCOL.md): 20,025 synthetic item/structure pairs pass global tree/amount checks; a real 2,000-row XLSX passes row/formula/total checks and takes 659.9 ms. All 15 concurrent read requests completed. These are private Administrator measurements, not customer authoring capacity or an SLA.
- [Security upgrade path](SECURITY_UPGRADE_PATH.md) compares exact current official version-16 releases with the remaining advisory constraints. Several fixes fit newer upstream constraints; PDF and authentication issues remain. No vendor upgrade or mitigation qualification is claimed.
- [Recommended operating profile](RELEASE_OPERATING_PROFILE.md) prepares site isolation, version support, coordinated rollout, recovery and pilot/support choices without purchasing hosting or inventing an SLA.

## All sixteen acceptance gates

| ID | Evidence achieved | Remaining requirement |
| --- | --- | --- |
| G01 | Deletion/current aggregate and real contention fixes; named v16 copy has zero rollup discrepancies | Review actual customer discrepancies if migration is offered; do not silently repair financial data. |
| G02 | Frozen history/current projections; all 219 old revisions preserved, 35 linked approvals resave | Preserve/exclude owner-classified test remnants; qualify sold approval/variation UI routes and representative operational legacy records. |
| G03 | Manual/prior cancellation restoration and reviewed atomic conversion regressions | Qualify sold analysis/cancel UI and representative legacy conversion when legacy migration is offered. |
| G04 | Positive factors in native controllers/import/readers; browser zero refusal | Inventory old operational factors and resolve invalid values using commercial evidence. |
| G05 | Twelve real overlapping-connection/contention regressions | Qualify customer writes/concurrency through the chosen web/worker/database stack and upgrade bypasses. |
| G06 | Additive direct-cost pricing and factor-aware resources/revisions/export | Review remaining sold consumers and representative legacy margin bases. Invoice-tax compliance is separate. |
| G07 | 234 selected Python / 35 JS; all 17 Python modules configured in CI | Run actual committed-candidate GitHub CI and retain run URL/SHA/result; placeholder legacy properties are not full coverage. |
| G08 | Non-admin native BOQ/HTTP boundaries, mutation verbs and new native report/Company gates | Complete sold role/company/share/attachment/import/export/report matrix; review existing grants and chosen customer isolation. |
| G09 | Workbook bounds, hostile numeric checks; actual 2,000-row parser dry-run measurement | Measure worker/proxy behavior and adversarial admitted size/shape limits for the sold import profile. |
| G10 | Compatible updates, exact-source clean rebuild, 70-advisory primary-source reconciliation | Qualify supported vendor/dependency fixes or effective advisory-specific mitigations; review production JS and OS/native packages. |
| G11 | Bounded 20,000-row fixture; audited 2,000-row reads/XLSX, 15 concurrent requests and workbook parser | Set sold workload and validate mixed customer-role reads/writes, queue behavior, memory and response expectations on hosting. |
| G12 | Fresh install, synthetic restoration and named v16 backup/copy/two migrations preserve compared rows/files/auth | Coordinate original shared-code/site rollout; qualify operational/customer legacy data if migration is offered. |
| G13 | Exact Frappe 16.18.1 / ERPNext 16.18.3 source qualification | Adopt a supported, security-qualified version matrix; no v15 claim follows from this work. |
| G14 | Real native Save, positive/zero pricing, forbidden item, report period and Company smoke | Complete populated Arabic/English sold workflows, printing/export visuals and broader browser/role/device coverage. Realtime remains unqualified. |
| G15 | Timed synthetic recovery plus retained fresh v16 backup | Select hosting/operator, off-host backups/retention, monitoring, support and RPO/RTO; validate on representative hosted data. |
| G16 | Reviewed local source, bounded independent static review and code-only publication candidate | Authorized coordinated rollout, actual CI, resolved security and final customer release acceptance/bundle. |

## Confirmed rules and pending authority

[Financial contract](FINANCIAL_RULES.md): positive factor; missing defaults to one; additive percentages on direct cost; recoverable captured manual/prior cost; immutable approval history with new corrections; factor changes physical resource quantities and values.

The owner authorized v16.localhost and classified 184 orphan approved revisions plus 25 invalid-evidence client-approved VOs as test records to preserve/separate. The completed named-site rehearsal preserves their original rows, archives/excludes exact IDs from customer inputs and proves selected backup/restore/upgrade behavior. It does not certify real customer legacy data.

Three original sites share the app checkout: localhost, v16.localhost and v16rehearsal.localhost. Their old schemas make advancing shared code unsafe without coordinated upgrades. The owner was asked to authorize backup/migration of all three or choose a separate Bench for v16. **No answer means no authority for the other sites. Main remains unchanged by this task.** Other-session untracked UOM documents and dump.rdb are preserved.

Automatic approval review rejected the attempted public Git push because private source disclosure to that public destination was not specifically authorized. No upload or provider run occurred. A refreshed question identifies final candidate a6bc51c and the exact public repository/branch; it supersedes the older unpublished a1219c2 payload. Await explicit approval before publishing. Do not bypass the rejection through browser upload, another branch, PR creation or memory services.

Local commits use command-local disabled transmitting hooks. Site configurations, encryption material, credentials, backups, fixture data and raw private logs stay outside Git. Luna agents performed bounded work; the parent owns financial/security decisions and release conclusions. This is direct authorized collaboration, not a fabricated native orchestrator execution or human release certification.

[Current evidence binding](END_TO_END_TESTED_FILES.json) records the tested source bytes, exact vendor revisions, final test counts and hashes of retained private artifacts. Historical TESTED_FILES.json remains intact. All task-owned private web, database and Redis services were stopped after testing; fixtures and evidence were retained. Shared services and original sites were not stopped or migrated.
