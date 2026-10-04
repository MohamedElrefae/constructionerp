# Customer release corrections — integrated status

**2026-10-05. Engineering corrections committed and locally integrated; customer release remains blocked.**

The original [sixteen-gap report](../../CUSTOMER_RELEASE_GAPS_2026-10-04.md) is a dated assessment. This ledger records what was corrected and what still needs evidence. Code is `4be0712db90897f8947199f91665275909b7652d`; integrated candidate is `46e50cef334a4f51c9faea04c99bf9b5f7401a7f`. [Verification](VERIFICATION.md) and [file/log bindings](TESTED_FILES.json) identify the tested result. The owner subsequently named v16.localhost for backup/isolated-upgrade work; its original schema/commercial data remain unchanged. See [the completed named-site rehearsal](V16_UPGRADE_REHEARSAL.md).

## Implemented and verified

- Post-delete aggregates and guarded current reads prevent the reproduced stale-total race. Twelve real transaction regressions cover overlapping connections, refused commits after contention, explicit whole-operation retry and rollback. No throughput guarantee or automatic retry is claimed.
- Quantity approvals are permanent; corrections create new history. Revised reports/export now read current quantity/rate projections. New revision and VO snapshots capture factor/version; successive VO deltas use the previous current quantity/rate, and approved VO commercial snapshots cannot be edited or recomputed on resave.
- Direct cost 100 + overhead 10% + profit 10% gives 120. Optional configured tender tax allowance is additive; this is not statutory invoice-tax certification. Cancellation restores eligible prior approval or the captured manual estimate, including zero and edits between approval cycles.
- Positive factor validation reaches controllers, workbook previews and revised/resource reports. The owner confirms physical quantities too: quantity 10 × factor 0.5 × one resource unit = 5 units. Resource planning includes wastage and normalizes batch analysis quantity; it retains the existing contract-quantity planning basis.
- A reviewed, non-RPC legacy cost conversion previews a saved replacement and explicit manual basis, binds all reviewed inputs, checks native permissions, preserves legacy financial amounts/approval identity, and applies atomically in the caller's transaction. Eight real regressions pass. [Operator instructions](LEGACY_CONVERSION_RUNBOOK.md) explain the remaining customer-data qualification.
- BOQ Header.project is now a native Project Link. Six BOQ document types inherit actual header authorization through deny-only hooks and permission-aware list predicates; stored and proposed parents are checked. Six non-admin regressions and real native HTTP allowed/denied checks pass with the selected scope filter disabled.
- BOQ mutations and cost import/repricing are POST-only. Cost import uses native permissions/documents, checks authorization in preview and commit, and refuses malformed numeric workbook values. Bulk selection is permission-aware and filters exact resource rows. Workbook bounds remain enforced.
- Setup no longer manufactures broad System Manager grants across vendor DocTypes. Select repair is confined to Construction metadata; impossible old import flags are corrected without an inner commit. Existing valid old grants are preserved pending an authorized review.
- Required bilingual fields install automatically; native workspace insertion and migration ordering are corrected. Concurrent bilingual Desk/report source was merged, then tested with the financial corrections. The later two bilingual population commits contain documentation/evidence only and are retained without executing their scripts.
- Selected final suite: **219 Python tests / 17 modules; 35 JavaScript tests**. CI includes fifteen business modules, including legacy conversion and parent permissions; no actual GitHub run is claimed.
- A synthetic DB/files/config backup restored to a new site on a separate private database in 24.858 seconds (backup 1.206 seconds). Financial/history rows, attachment, encrypted secret and source audit results match after two migrations. The intentionally created legacy budget discrepancy remains unchanged; recovery is not data repair or a production recovery promise.
- The isolated runtime passes `pip check`; thirteen constraint-compatible package updates were tested. The scanner still reports **108 advisory entries across nine packages**, including duplicate identifiers and unfixed entries. This is a security qualification blocker, not 108 proven exploitable app defects. [Dependency review](DEPENDENCY_REVIEW.md) records scope and next steps.

## All sixteen release gates

| ID | Current evidence | Remaining acceptance requirement |
| --- | --- | --- |
| G01 | Deletion/current aggregates tested; named v16 copy has zero header/structure discrepancies | Review any actual customer discrepancies separately; no repair needed on this copy. |
| G02 | Permanent history/new projections tested; all 219 old revisions preserved and 35 linked approvals native-resave successfully | Preserve/exclude owner-classified orphan/test history from customer inputs; qualify actual operational legacy records and sold routes. |
| G03 | Manual/prior restoration and reviewed conversion helper tested | Convert reviewed representative legacy records on an authorized copy; verify sold UI and cancellation. |
| G04 | Positive factors and revised/resource reader checks tested | Inventory and resolve old invalid factors using commercial evidence; no silent normalization. |
| G05 | Reproduced race fixed; real connection/contention regressions pass | Qualify promised workload and declared framework/database versions; review upgrade bypasses. |
| G06 | Additive pricing, batch normalization, resource factor/wastage tested | Review representative legacy margin bases and remaining sold consumers. Invoice taxation is separately governed. |
| G07 | Local 17-module run passes; fifteen modules configured in CI | Observe actual committed-candidate CI. Legacy placeholder property cases are not complete coverage. |
| G08 | Parent Project boundaries, non-admin native read/write/list/files/export denial, POST-only mutation and native imports tested; global auto-grants removed | Complete full role/company/report/import/export/share/attachment matrix and review existing grants. Customer isolation/selected-scope architecture remains undecided. |
| G09 | Workbook bounds, malformed numbers, native permissions and filters tested | Measure admitted worst-case workbooks and confirm worker/proxy limits. Synchronous safety ceilings are not capacity promises. |
| G10 | Isolated constraints repaired, public inventory and repeated scanner results retained | Resolve/apply vendor-compatible advisory fixes or justified mitigations; review framework/OS/production JS assets and prove clean reproducible build. |
| G11 | No capacity promise invented | Owner selects sold workload; measure response time, memory and concurrent correctness at that workload. |
| G12 | Fresh install, synthetic restore and actual old-schema v16 backup/restore/two migrations preserve compared data/files; 35 linked legacy approvals tested | Named source is owner-confirmed test data with no cost analyses. Qualify operational/customer legacy cost data and coordinated original-site rollout before wider closure. |
| G13 | Evidence bound to installed Frappe 16.18.1/ERPNext SHAs | Declare and pin sold support matrix; review global overrides and verify advertised versions. No v15 qualification. |
| G14 | Relevant backend/HTTP and merged bilingual suites pass; earlier native PDF evidence retained | Test actual English/Arabic UI workflows, printing and visual output with customer roles and built candidate assets. |
| G15 | Timed synthetic recovery demonstrated | Decide hosting/isolation, monitoring, support, retention and production RPO/RTO; qualify recovery at customer scale. |
| G16 | Concurrent source integrated locally; immutable code/evidence retained | Authorized main/site upgrade, qualified independent review, actual CI, final release bundle and customer release authority. |

## Confirmed owner rules

Positive factor (missing → 1, explicit zero rejected); additive percentages on direct cost; cancellation restores eligible prior/captured manual basis; approval history is permanent with new corrections; factor changes resource quantities and values. These are conversation decisions, not assumptions. [Financial contract](FINANCIAL_RULES.md).

## Integration and next action

Main is at `3fa285a`; its two later population evidence commits were merged into this task branch. Final inspection also found the other task's untracked `docs/ai/work-items/bilingual-wave2-group-masters-population/`; it was preserved and is outside this candidate. Main's app path remains linked to existing sites, so its checkout has not been advanced to new controller/schema code. This avoids serving new code against an unmigrated site. No push, deploy, existing-site migration, actual customer conversion or customer release occurred.

The owner authorized **v16.localhost**, and its backup/isolated upgrade is complete. The owner classified the discovered orphan/invalid approval histories as test records; a private archive and exact-ID customer-input exclusion registry preserve them. No in-app archive flag or original-row removal is claimed. Remaining steps include actual operational/customer cost data and coordinated shared-code/site rollout. The owner was separately asked about v16/separate-customer-site delivery and workload; unanswered choices remain open. The professional standard section 12 requires: “Commands with a production or ambiguous site must follow the actual authorization boundary; use a known disposable site for authorized tests.” [Exact instruction](../../PROFESSIONAL_ENGINEERING_STANDARD.md).

All local commits/merges disabled the external-memory Git hook for those commands. Private fixture credentials/configuration/backups stay outside Git. Remaining private fixture servers are stopped at handover, with local data retained for deliberate replay. Local integration is complete; installation and release qualification are pending the requirements above.


### Named-site follow-up integration observation

The v16 rehearsal is complete against the retained backup snapshot; no original-site migration occurred. Final main inspection advanced to 890ae14 with another task's uncommitted bilingual report API/viewer/test edits, untracked work-item files and dump.rdb. All remain untouched and outside the tested source candidate. The earlier site-name requirement is satisfied. Before any shared-code/site rollout, reconcile this later source and current site changes; do not claim that the rehearsal qualifies uncommitted report changes or the live site after concurrent population.
