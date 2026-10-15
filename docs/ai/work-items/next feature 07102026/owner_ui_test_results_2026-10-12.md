# Owner UI acceptance — results workbook

**Scope clarification — 12 October 2026:** The [foundation remediation master plan](construction_foundation_remediation_master_plan_2026-10-12.md) now governs the full program: existing gaps, required enhancements, maintainability, operations and owner acceptance before new business modules. Track execution in the [foundation work register](construction_foundation_work_register_2026-10-12.md). The UI plan is one workstream; its earlier backend-only classifications describe current availability, while master tasks F18/F19 plan completion of those interfaces and require additional owner tests.

**Owner:** Mohamed  
**Plan date:** 12 October 2026  
**Execution status:** Not started; no test has been marked passed.

Use with the [test plan](existing_features_owner_ui_acceptance_plan_2026-10-12.md) and [defect register](owner_ui_defect_register_2026-10-12.md). Duplicate the attempt template for every case variant and retest. Do not overwrite earlier failures.

## Environment and readiness manifest

| Field | Record before execution |
|---|---|
| UAT URL / operator / isolation from shared sites | Pending |
| Candidate label / Construction commit / asset build | Pending |
| Frappe / ERPNext commits and versions / runtime | Pending |
| Browser / version / screen size / language | Pending |
| Scope, cascade, registry, VO, Option B settings | Pending |
| Backup / restore evidence / outbound integrations | Pending |
| Test accounts / roles / user permissions (no passwords) | Pending |
| Fixture document IDs / expected finance worksheet | Pending |
| Finance reviewer / QS reviewer / engineering owner | Pending |
| Start date / session calendar | Pending |
| Gate A decision / date / blockers | Pending |

## Deployed feature inventory — complete before sign-off

Add one row per actual DocType workflow, page, report, print format, flag-controlled behavior and site customization. Use the plan's 21-schema ledger and eight integrations as the starting inventory; enumerate each individual report/print language variant.

| Feature / actual route | Installed and exposed? | Role / flag | UI case or T-task | Mandatory / optional / backend-only | Gap or exclusion reason + owner decision |
|---|---|---|---|---|---|
| To inventory | Pending | Pending | Pending | Pending | Pending |

## Preparation and engineering tasks

| Task | Status | Candidate / evidence / issue |
|---|---|---|
| PRE-01 | Not started | — |
| PRE-02 | Not started | — |
| PRE-03 | Not started | — |
| PRE-04 | Not started | — |
| PRE-05 | Not started | — |
| PRE-06 | Not started | — |
| PRE-07 | Not started | — |
| PRE-08 | Not started | — |
| PRE-09 | Not started | — |
| T-01 | Not started | — |
| T-02 | Not started | — |
| T-03 | Not started | — |
| T-04 | Not started | — |
| T-05 | Not started | — |
| T-06 | Not started | — |
| T-07 | Not started | — |
| T-08 | Not started | — |
| UAT-01 | Not started | — |
| UAT-02 | Not started | — |
| UAT-03 | Not started | — |
| FIX-01 | Not started | — |
| RETEST-01 | Not started | — |
| UAT-04 | Not started | — |
| CLOSE-01 | Not started | — |
| NEXT-01 | Not started | — |

## Owner case index

Status values: **Not Run / Pass / Fail / Blocked / Excluded**. Parent status reflects all mandatory variants; Excluded needs explicit approved scope reasoning. Evidence is not optional for a Pass.

| Case | Test | Status | Attempts / evidence | Defects |
|---|---|---|---|---|
| UI-01 | Login and daily navigation | Not Run | — | — |
| UI-02 | Construction Settings and business switches | Not Run | — | — |
| UI-03 | Scope selection and persistence | Not Run | — | — |
| UI-04 | Denied records and files | Not Run | — | — |
| UI-05 | Scope change with unsaved work | Not Run | — | — |
| UI-06 | Exclusions and report-access switch | Not Run | — | — |
| UI-07 | Project and task foundation | Not Run | — | — |
| UI-08 | Create BOQ Header | Not Run | — | — |
| UI-09 | WBS group, leaves and tree | Not Run | — | — |
| UI-10 | BOQ lines and factor arithmetic | Not Run | — | — |
| UI-11 | Cascade, quick-create and invalid hierarchy | Not Run | — | — |
| UI-12 | Rollups and navigation | Not Run | — | — |
| UI-13 | Lifecycle and immutable baseline | Not Run | — | — |
| UI-14 | Draft editing and deletion boundaries | Not Run | — | — |
| UI-15 | Resource and price reference data | Not Run | — | — |
| UI-16 | Direct cost and additive pricing | Not Run | — | — |
| UI-17 | Batch quantities, wastage and streams | Not Run | — | — |
| UI-18 | Cost validation and scope | Not Run | — | — |
| UI-19 | Approve cost without changing contract rate | Not Run | — | — |
| UI-20 | Supersede and restore prior approval | Not Run | — | — |
| UI-21 | Restore manual cost including zero | Not Run | — | — |
| UI-22 | Cancel superseded history | Not Run | — | — |
| UI-23 | Templates and legacy hold | Not Run | — | — |
| UI-24 | Create planned stages | Not Run | — | — |
| UI-25 | Measure work and validate quantities | Not Run | — | — |
| UI-26 | Certify with correct authority | Not Run | — | — |
| UI-27 | Certified and locked-stage protection | Not Run | — | — |
| UI-28 | Stage distribution at lock and after revision | Not Run | — | — |
| UI-29 | VO entry and lifecycle prerequisites | Not Run | — | — |
| UI-30 | Increase, approvals and separation of duties | Not Run | — | — |
| UI-31 | PDF evidence and approval restrictions | Not Run | — | — |
| UI-32 | Decrease based on current quantity | Not Run | — | — |
| UI-33 | Omission and selection gates | Not Run | — | — |
| UI-34 | New variation scope item | Not Run | — | — |
| UI-35 | Final totals, history and repeated save | Not Run | — | — |
| UI-36 | Reject, justification and rate/factor cases | Not Run | — | — |
| UI-37 | Material Request | Not Run | — | — |
| UI-38 | Purchase Order | Not Run | — | — |
| UI-39 | Purchase Receipt | Not Run | — | — |
| UI-40 | Purchase Invoice | Not Run | — | — |
| UI-41 | Sales Invoice progress-billing gate | Not Run | — | — |
| UI-42 | Stock Entry | Not Run | — | — |
| UI-43 | Timesheet and Direct Labor Designation | Not Run | — | — |
| UI-44 | Journal Entry override | Not Run | — | — |
| UI-45 | Supplier payment and customer receipt | Not Run | — | — |
| UI-46 | Cancellation and audit trail | Not Run | — | — |
| UI-47 | Budget and variance controls | Not Run | — | — |
| UI-48 | Native commercial handoffs used by pilot | Not Run | — | — |
| UI-49 | Quality/asset dependencies if used | Not Run | — | — |
| UI-50 | BOQ Excel import through the actual button | Not Run | — | — |
| UI-51 | Import validation and safe retry | Not Run | — | — |
| UI-52 | BOQ workbook/PDF/print exports | Not Run | — | — |
| UI-53 | BOQ Import Batch evidence | Not Run | — | — |
| UI-54 | CostItem and PlantResource schema disposition | Not Run | — | — |
| UI-55 | All 11 protected financial reports | Not Run | — | — |
| UI-56 | All four protected dashboard reports | Not Run | — | — |
| UI-57 | Bilingual Report Viewer | Not Run | — | — |
| UI-58 | Report stale results, empty data and errors | Not Run | — | — |
| UI-59 | Arabic account/customer/supplier search | Not Run | — | — |
| UI-60 | Four commercial print formats | Not Run | — | — |
| UI-61 | Themes and personal preference isolation | Not Run | — | — |
| UI-62 | Theme administration and native controls | Not Run | — | — |
| UI-63 | Layout controls, density and presets | Not Run | — | — |
| UI-64 | Shared/personal layout permissions and reset | Not Run | — | — |
| UI-65 | Unsupported layout and responsive usability | Not Run | — | — |
| UI-66 | Two-session stale edit | Not Run | — | — |
| UI-67 | Network failure and repeat click | Not Run | — | — |
| UI-68 | Egyptian contractor daily journey | Not Run | — | — |
| UI-69 | Repeatability and final acceptance rehearsal | Not Run | — | — |

## Mandatory variant checklist

Create separate attempt entries for each applicable variant. This prevents one successful example being mistaken for full coverage.

- UI-01/03/04/06: each role, company/project boundary, record/file/report/export route and switch state.
- UI-10/18/21/23/26/27/31/36: each invalid input, independent restoration fixture, legacy refusal and approval-evidence restriction.
- UI-37–44: **eight subchecks for each of eight transaction types** from the plan's common row matrix; mark any true nonapplicability with rationale.
- UI-48–49: each enabled native handoff; any unused optional module explicitly classified.
- UI-50–53: each advertised import mode actually accessible, workbook variant, retry and saved-count inspection; six BOQ export/print choices.
- UI-55: all 11 named reports, expected balances, allowed and denied accounts.
- UI-56: all four named dashboard/report functions.
- UI-57: seven named bilingual reports plus any additional offered viewer reports.
- UI-60: four formats × two languages, including multi-page PDF evidence.
- UI-61–65: theme, profile/role, form eligibility, width/zoom and supported device combinations recorded.
- UI-68–69: handoff outcomes, total elapsed minutes, repeated-entry count and spreadsheet workarounds.

## F03 coverage additions — pending script design

The [source route inventory](construction_foundation_feature_route_inventory_2026-10-12.md) lists COV-01–10 requiring additional scripts or engineering checks. In particular, add **Accounts Receivable aging** as the eighth bilingual report; the existing seven are not the entire source allowlist. Cover governed account rename, translation administration, VO → Material Request, WBS conversion/resequence/health, bulk stage methods, generic exports and guest/legacy boundaries as applicable. F43 assigns final new UI IDs and expectations; no case is marked passed or executed here. Actual installed metadata/permissions remain pending F02/F03.

## Attempt template — copy for each case/subcase/retest

### Attempt: UI-__ / variant __ / attempt __

| Field | Record |
|---|---|
| Date / tester / account persona | |
| Candidate / site / browser / language | |
| Case and exact variant | |
| Prerequisite record IDs / company / project | |
| Steps actually followed | |
| Expected result and values | |
| Actual saved result and values | |
| Pass / Fail / Blocked / Excluded | |
| Screenshot / PDF / workbook / other evidence path | |
| Defect ID / blocked prerequisite | |
| Elapsed minutes / confusion / duplicate entry | |
| Retest of prior attempt / fix candidate | |

## Accepted exclusions and deferred minor issues

| Feature/case | Reason / business impact | Evidence / workaround | Owner decision + date | Responsible person / due date |
|---|---|---|---|---|
| None approved | — | — | — | — |

## Final decision — leave unsigned until complete

- Final candidate/site: **Pending**
- Mandatory variants: total __ / passed __ / failed __ / blocked __ / not run __.
- Optional exclusions: __, each approved above.
- Open defects: S0 __ / S1 __ / S2 __ / S3 __.
- Engineering readiness T-01–T-08 and final-change impact review: **Pending**.
- Finance/QS calculations and outputs reviewed by / date / evidence: **Pending**.
- Mohamed independently completed UI-69: **Not Run**.
- Gate B decision: **Not accepted yet**.
- Mohamed signature/date: ____________________.
- Next-feature authorization: **Not granted by this workbook**. Record a later explicit scope decision separately.
- Production/customer release: **Separate decision; not authorized here**.
