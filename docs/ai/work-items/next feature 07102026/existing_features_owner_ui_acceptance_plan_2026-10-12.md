# Existing-feature stabilization and owner UI acceptance plan

**Scope clarification — 12 October 2026:** The [foundation remediation master plan](construction_foundation_remediation_master_plan_2026-10-12.md) now governs the full program: existing gaps, required enhancements, maintainability, operations and owner acceptance before new business modules. Track execution in the [foundation work register](construction_foundation_work_register_2026-10-12.md). The UI plan is one workstream; its earlier backend-only classifications describe current availability, while master tasks F18/F19 plan completion of those interfaces and require additional owner tests.

**Prepared for:** Mohamed / General Manager  
**Prepared from:** Head of Engineering perspective  
**Date:** 12 October 2026  
**Market focus:** Egyptian small and mid-sized contractors first; Gulf expansion later  
**Status:** Proposed execution plan; all acceptance tests are **Not Run**  
**Source baseline inspected:** `develop` at `c9e6803c5ac63073aeb0b166c779844d29051d8d`; deployed site/version not verified  
**Classification:** Confidential — internal engineering and management

## 1. Decision for now

**Pause new-feature implementation. Prepare a controlled test environment, let Mohamed test all existing user-facing construction workflows himself, fix demonstrated defects, and repeat affected tests before agreeing the next feature.**

This changes the immediate sequence in the [engineering report](construction_platform_engineering_review_for_gm.md) and [consultant reconciliation](consultant_review_line_by_line_reconciliation_2026-10-12.md). Their certificate and market roadmap remains a later proposal. Neither historical test counts nor source inspection is owner acceptance. This document authorizes no site changes by itself; it plans the work requested. No tests, migrations or deployments were performed while writing it.

Three working documents form the acceptance pack:

1. This plan: preparation, scope, scripts, engineering evidence and gates.
2. [Owner UI test results](owner_ui_test_results_2026-10-12.md): record Pass/Fail/Blocked for each test and each listed variant.
3. [Defect register](owner_ui_defect_register_2026-10-12.md): track reproduction, fixes and owner retests; includes the import finding awaiting UI confirmation.

### What “all existing features” means

Cover all 21 Construction schema-owning DocTypes, its Journal Entry override, all eight registered transaction integrations, active theme/layout/scope behavior, applicable bilingual/printing/report functions, and the native ERPNext processes used in the agreed contractor workflow. Child tables are tested through their parent forms. Source-only helpers require engineering evidence and an honest UI limitation. This is not a claim to exhaustively test every module of ERPNext or every retained legacy JavaScript file.

Before execution, engineering inventories the actual installed pages, workspaces, custom fields, custom scripts, reports, print formats, flags and customizations. Add a case for every additional active behavior absent below. A capability cannot disappear from coverage merely because a button is missing. Classify it as a defect, backend-only function, or explicitly excluded optional/scaffold functionality with the owner's written reason. Existing customer-required behavior cannot be waived as “not applicable.”

## 2. Responsibilities and work order

Mohamed is the business tester and acceptance owner. Engineering prepares the site, accounts, data and accurate instructions, investigates defects and supplies technical evidence. Finance validates accounting expectations; a QS/commercial reviewer validates measurements/VO arithmetic. If one person covers several roles, record the names anyway. Mohamed uses separate ordinary test logins to exercise business roles; Administrator is reserved for setup/diagnostics.

| Task | Responsible | Depends on | Concrete completion evidence | Priority |
|---|---|---|---|---|
| PRE-01 Record feature hold and nominate named tester, engineer and finance/QS reviewers | Owner | None | Names, scope and hold recorded in results file | First |
| PRE-02 Choose isolated UAT URL and candidate; record Construction/Frappe/ERPNext commits, runtime, assets and settings | Engineering | PRE-01 | Environment manifest and exact candidate identity | First |
| PRE-03 Prepare safe UAT copy, baseline backup and proven restoration path; disable external email, SMS, payments and tax submissions | Engineering | PRE-02 | Isolated target verified, restoration evidence and integration settings recorded | First |
| PRE-04 Inventory deployed UI and map each source feature to route, roles, flag, case and limitation | Engineering | PRE-02 | Coverage inventory completed; no unclassified active features | First |
| PRE-05 Reproduce import mismatch K-01; inspect candidate-specific open financial/security/release findings | Engineering | PRE-02–04 | Triage disposition and readiness blockers recorded | First |
| PRE-06 Prepare ordinary-role access matrix, separate approval identities and cross-company denied fixtures | Engineering + Owner | PRE-03–04 | Successful logins; expected allow/deny matrix signed | Before UI |
| PRE-07 Prepare small reference data/workbooks/PDFs and independently calculated expected financial values | Engineering + Finance/QS | PRE-03–06 | Fixture IDs, formulas and expected outputs reviewed | Before UI |
| PRE-08 Correct stale user-guide instructions and confirm actual click paths; no API/console workaround in owner's script | Engineering | PRE-04–07 | Usable task sheet with menu labels and known limitations | Before UI |
| PRE-09 Run candidate-bound technical readiness checks T-01–T-08 below and a short ordinary-user smoke | Engineering | PRE-05–08 | Results/logs tied to candidate; no blocking setup/security/correctness issue | Before UI |
| UAT-01 Execute foundation, costing and stage sessions | Mohamed | Gate A | UI-01–28 with evidence; failures logged | Now |
| UAT-02 Execute variations, all transaction integrations and native dependencies | Mohamed + Finance/QS | Relevant UAT-01 prerequisites | UI-29–49; per-role/per-variant outcomes | Now |
| UAT-03 Execute import/output/report/theme/layout/error cases | Mohamed | Relevant fixtures ready | UI-50–67 and all report/print variants | Now |
| FIX-01 Triage daily; fix existing-behavior defects in small reviewed changes | Engineering | A reproducible failure | Root cause, changed candidate, targeted regression and updated instructions | As found |
| RETEST-01 Retest original failure, denied path and affected neighboring flows | Mohamed + Engineering | FIX-01 | Owner confirms UI correction; engineer confirms technical regressions | After each fix |
| UAT-04 Perform full daily-journey rehearsal and independent repeat | Mohamed + Finance/QS | Relevant cases corrected | UI-68–69; final arithmetic and usability results | Final |
| CLOSE-01 Reconcile coverage, unresolved issues and documentation; archive acceptance pack | Engineering + Owner | UAT-04 | Gate B signed against exact candidate | Final |
| NEXT-01 Select and approve one next feature based on demonstrated gaps and Egyptian client needs | Owner/GM | Gate B | Explicit feature scope, business rules and acceptance criteria | After acceptance |

New business-module implementation remains on hold. Under the clarified master plan, foundation work includes defect correction, necessary enhancements to existing capabilities, fixtures, environment/configuration repair, evidence and documentation. In particular, master tasks F18/F19 include usable interfaces for existing import/report services before foundation sign-off. Define their interface contracts and add UI cases; introducing a new financial/domain engine remains later scope.

### Planning allowance

Use 60–90 minute owner sessions, normally 2–4 sessions per week. Start by reserving **12–16 sessions**, including report/print variants and one final repeat. This is a scheduling allowance, not a deadline or measured estimate. Engineering preparation is provisionally 2–4 working days after a suitable isolated environment is available; defects, security remediation and migration issues add time. Re-estimate after the first two sessions. Do not compress permission, monetary or approval checks to meet a calendar target.

Suggested sequence: access/settings → BOQ/WBS → costing → cancellation/legacy → stages → variations → procurement/stock → finance/remaining integrations → imports/exports → reports/Arabic prints (two sessions) → themes/layouts → errors/end-to-end → final retests. Reserve extra slots for failures rather than declaring unrun cases passed.

## 3. Gate A: ready for Mohamed to start

- [ ] Exact isolated UAT URL and candidate are recorded; page visibly identifies the test environment.
- [ ] Actual site owner/operator has confirmed that the target is safe for synthetic financial transactions. No production records are used casually.
- [ ] Shared Bench effects have been checked. Do not switch shared app code or migrate adjacent sites as a side effect of UAT preparation.
- [ ] Backup includes database, files and necessary configuration; restore is proven into an authorized isolated target.
- [ ] Outbound integration side effects are disabled or use confirmed sandboxes; fixtures contain no real payment credentials or unapproved customer data.
- [ ] All role accounts work, with no Administrator/System Manager grants on ordinary-role proof accounts.
- [ ] Current UI routes, business role permissions, flags and expected calculations are supplied.
- [ ] Technical blockers are corrected or the affected sessions clearly held. No known cross-company leak or incorrect-money path is exposed for ordinary use.
- [ ] K-01 is reproduced/classified; the import session stays blocked until the result and usable route are clear.
- [ ] Results/defect files are ready; all test statuses initially remain Not Run.

This gate can release unaffected sessions while a clearly isolated feature is held; final acceptance cannot pass with mandatory cases still blocked.

## 4. Fixture pack and permission setup

Engineering records real internal document names beside these human labels. Keep separate fixtures so cancellation, omission and negative tests do not damage the next case.

| Fixture | Contents and expected baseline |
|---|---|
| Company A / Company B | Two isolated synthetic legal entities; Company A uses EGP; separate customers, suppliers, warehouses, accounts and cost centers |
| A1 / A2 / B1 | Two projects in A and one in B; include a child cost center and optional department/branch only if enabled |
| H-CORE | Draft contract BOQ, one group and separate leaves for each line; F1 qty 10 × factor 0.5 × price 100 = 500; direct cost 60 gives 300; second line qty 4 × 1 × 50 = 200, cost 20 gives 80; totals 700/380 |
| H-LOCK / H-COST | Independent copies for lifecycle and analysis; H-COST contract rate 150, initial manual estimate 60; manual-zero and second-cycle-70 cases separate |
| H-STAGE | Qty 10, factor 1, planned stages 4+6 created before freeze/lock; separate incomplete plan and post-VO fixtures |
| H-VO | Locked item qty 100, price 50, factor 1, no stages, original value 5,000; sequential increase/decrease/omission/new-item cases use only this header |
| H-IMPORT | Fresh Draft header for each import case; 3 known rows plus small invalid/ambiguous files; team records expected counts, hierarchy, quantities and totals |
| Resource pack | Five ERPNext resource Items M/L/P/S/O; known UOMs, dates, prices, streams and stock settings; approved manual/template/legacy samples |
| Transaction pack | Supplier PO 10 units, partial PR/PI 6; warehouse opening stock; independent SI/JE/payment and cancellation fixtures; detailed finance-calculated GL and residual balances |
| Evidence pack | Synthetic signed approval PDF attached to intended VO, another VO's PDF, harmless invalid PDF example; bilingual/multi-page outputs |
| Denied pack | B1 record/file/report/export URLs and unequal balances so unauthorized leakage is detectable; no broad role added just to finish tests |
| Rehearsal pack | Fresh E2E-A project with separate staged and VO items; small realistic contractor quantities; manual expected totals and elapsed-time sheet |

### Required ordinary accounts

| Test persona | Proposed starting role mapping; verify installed permissions | Important boundary |
|---|---|---|
| Owner/client approver | Construction Owner | No System Manager bypass; not the VO preparer or engineer approver |
| PM/preparer | Project Manager plus only necessary native roles | Can prepare/submit where allowed; do not assume PM can never write cost analyses |
| Engineer approver / site recorder | Site Engineer with confirmed document access | May engineer-approve VO where permitted; stage certification needs a certifier role |
| Finance | Minimal installed accounts roles mapped by finance lead | Approved company only; no accidental all-company visibility |
| Procurement / Stores | Minimal buying/stock roles plus required construction access | Per-company and per-project transaction scope |
| Restricted | Ordinary role limited to A1 | Denied A2/B1 routes tested explicitly |
| Setup administrator | System Manager/Administrator | Setup and diagnostic checks only; never counted as ordinary-role security proof |

Role names alone do not prove behavior: export the effective DocType permissions, User Permissions, company/project assignment and report settings before execution. Distinct VO approval accounts must be distinct user identities, not just role switches in one login.

## 5. How Mohamed records each UI test

1. Select the case and confirm its prerequisite and correct login/scope.
2. Follow the UI steps. Search the exact DocType name from Desk when a workspace shortcut is absent. The team supplies the verified route for pages and reports.
3. Compare what you see with the expected result; reopen the record to distinguish saved data from an unsaved form.
4. Record **Pass**, **Fail** or **Blocked**, actual values, candidate/site, account, record IDs, date and evidence. Use **Excluded** only for a separately approved optional scope exclusion; retain the reason.
5. For a negative test, refusal is the expected Pass. A crash or silently accepted invalid value is a Fail. A missing prerequisite is Blocked.
6. For a case with several variants, use one subrow per variant. The parent cannot Pass until every required subrow passes. Keep old attempts after retesting.
7. If a result is wrong, record a defect immediately. Do not edit SQL, use the console or have engineering complete the missing business step invisibly.

Use screenshot names such as `UI-30_attempt1_owner_after-approval.png`; record evidence paths privately, excluding credentials and customer-sensitive data. For wrong totals, capture inputs, saved document and output. For an access leak, stop the affected path, preserve minimal evidence and notify the assigned engineer.

### Common transaction row checks — apply separately to UI-37 through UI-44

For **each** of the eight DocTypes, record subresults for: (a) valid gated row; (b) missing required BOQ selection; (c) cross-project item; (d) wrong structure/item combination; (e) inappropriate stage; (f) changing the parent project after entering rows; (g) nongated row where applicable; (h) reopening/submitting the valid fixture. Exercise both collapsed and expanded grid rows. A row gate must not be defeated by collapsing a grid. Native document/accounting mandatory fields still apply.

Gates: Direct expense classification for PO/PR/PI/Stock Entry/JE/MR; `Is Progress Billing` for SI; configured Direct Labor Designation for Timesheet. Engineering records the candidate's allowed BOQ statuses and cascade strictness before the session. Test the enabled intended configuration; engineering separately checks relevant disabled-flag behavior.

## 6. Owner UI scripts

These are **69 case groups**, not 69 single clicks. The eight transaction matrices, report names, print languages, roles and invalid-input variants each require subresults. No case has been executed for this planning document.

### 1. Access, settings and scope

#### UI-01 — Login and daily navigation

**Login:** All. **Prerequisite:** Prepared accounts; mapped workspace routes.

**UI steps:** Log in separately as Owner, PM, Site Engineer and Finance. Open workspace, search for an assigned document, open its list and record, log out, then use Back.

**Expected:** Each account sees its permitted work; no blank workspace or script error. A logged-out session cannot reopen protected data.

#### UI-02 — Construction Settings and business switches

**Login:** Admin + Owner. **Prerequisite:** Engineering records baseline settings.

**UI steps:** Admin opens Construction Settings. Inspect scope dimensions, BOQ cascade mode, variation flag, registry flag and Direct Labor Designations. Save one agreed change; reload; restore baseline. Owner repeats read/access check.

**Expected:** Values persist; only permitted users change settings. Direct Labor Designations are retained as active configuration, not removed as obsolete data.

#### UI-03 — Scope selection and persistence

**Login:** PM. **Prerequisite:** Companies A/B, projects A1/A2/B1; PM assigned A1 only.

**UI steps:** Select Company A, its cost center and Project A1 in the top bar. Open BOQ lists and a new Header; log out/in. Attempt B1 selection.

**Expected:** Allowed scope persists according to recorded policy; defaults belong to A1; unassigned company/project is unavailable or denied. Header project is sourced from scope, not a manually typed hidden field.

#### UI-04 — Denied records and files

**Login:** Restricted. **Prerequisite:** Admin supplies URLs of B1 document, private PDF, report and export; no credentials in workbook.

**UI steps:** As the A1-only account, paste each B1 URL into the address bar. Try search, list filters and link autocomplete for B1 as well.

**Expected:** No unauthorized content, totals, identifiers beyond approved policy, or downloaded file. UI denial is evidence only for these routes; engineering verifies APIs separately.

#### UI-05 — Scope change with unsaved work

**Login:** PM. **Prerequisite:** PM allowed both A1 and A2 for this case only; saved record IDs noted.

**UI steps:** Start an unsaved A1 transaction. Switch top-bar scope to A2 and attempt Save. Reopen both projects and inspect records.

**Expected:** Scope drift is detected or the conflicting save is refused; no silent posting under the wrong project. Capture any reload warning and whether unsaved work is explained.

#### UI-06 — Exclusions and report-access switch

**Login:** Admin + Restricted. **Prerequisite:** Engineering supplies expected allow/deny matrix and isolated settings checkpoint.

**UI steps:** Admin toggles Enable Option B Report Access Bypass off/on; restricted user retries permitted and forbidden reports. Test one agreed Scope Filter Exclusion, then restore.

**Expected:** Behavior matches the signed access matrix in both states; no cross-company disclosure. A scope-query exclusion does not grant document permission. Admin inspects Scope Report Access Log and relevant Error Log entries without requiring restricted users to read them.

### 2. Project, BOQ and WBS foundation

#### UI-07 — Project and task foundation

**Login:** PM. **Prerequisite:** Finance has configured Company A, cost center and EGP.

**UI steps:** Create a synthetic Project A1 and two Tasks with dates, owner, dependency and status. Search, filter, update progress and reopen.

**Expected:** Project/task data and dependencies persist using native ERPNext behavior; project/company attribution is correct. Record only scheduling functions actually enabled.

#### UI-08 — Create BOQ Header

**Login:** Owner. **Prerequisite:** Select A1 in scope; use fresh Draft header H-CORE.

**UI steps:** Search BOQ Header → New. Enter title and Contract type, Save, reload, then inspect list and header. Repeat a Tender header on a separate fixture.

**Expected:** Both supported types save in Draft with correct project/title. No manual database action is needed.

#### UI-09 — WBS group, leaves and tree

**Login:** Owner. **Prerequisite:** H-CORE remains Draft.

**UI steps:** Create BOQ Structure group Civil Works and separate leaves Concrete and Excavation. Open BOQ Structure → Tree; expand/collapse and follow node links.

**Expected:** Parent hierarchy and generated WBS codes are consistent; leaves belong to H-CORE; links open the selected node.

#### UI-10 — BOQ lines and factor arithmetic

**Login:** Owner. **Prerequisite:** Separate leaf per item; arithmetic fixture F1.

**UI steps:** Create Concrete BOQ Item with Cost Item free text, Structure leaf, qty 10, factor 0.5, contract rate 100, manual direct cost 60. Save/reload. On another Draft line try factor 0 and -1; then 1.

**Expected:** F1 contract value 500 and budget direct cost 300. Zero/negative factor rejected; factor 1 accepted. No ERPNext Item Code is required for BOQ specification text.

#### UI-11 — Cascade, quick-create and invalid hierarchy

**Login:** Owner. **Prerequisite:** Dedicated Draft header with no leaves; separate unrelated header.

**UI steps:** Open BOQ Item; select header and use Create → Create Leaf Structure. Save an item there. Attempt group-node selection and another header’s leaf. Change parent selection and inspect dependent fields.

**Expected:** Quick-create selects the new leaf; invalid group/cross-header links cannot persist. Changing parent clears or revalidates incompatible children.

#### UI-12 — Rollups and navigation

**Login:** Owner. **Prerequisite:** H-CORE has F1 and a second line qty 4, factor 1, rate 50, cost 20 on its own leaf.

**UI steps:** Reload item, leaf, group tree, header and Table View. Follow item breadcrumb. Change second line qty to 5 while Draft; reload totals; restore 4.

**Expected:** Initial header contract 700 and budget 380; changed totals 750 and 400; restoration returns 700/380. Tree/list totals reconcile; zero segments may be omitted by tree display.

#### UI-13 — Lifecycle and immutable baseline

**Login:** Owner. **Prerequisite:** Copy the pricing fixture to H-LOCK; stages already planned if used.

**UI steps:** Use Actions → Advance Status from Draft to Pricing, Frozen, Locked. At each state reopen item/structure and attempt commercial edits and deletion on a disposable copy.

**Expected:** Allowed transitions succeed; frozen/locked restrictions follow the prepared lifecycle matrix. Locked quantities/rates establish original history; unauthorized changes are refused. Engineer verifies hidden lock attribution if not visible in UI.

#### UI-14 — Draft editing and deletion boundaries

**Login:** Owner. **Prerequisite:** Unlinked disposable Draft header, leaf, item; separate linked/locked records.

**UI steps:** Edit and delete the unlinked Draft records in child-first order. Attempt deleting a linked structure/header through the normal menu; cancel confirmations if target is not the designated fixture.

**Expected:** Permitted draft cleanup succeeds; protected parents/history cannot be silently orphaned. Missing Delete due to permissions is a valid refusal, not a reason to grant admin access.

### 3. Cost estimation and approval integrity

#### UI-15 — Resource and price reference data

**Login:** Admin + Owner. **Prerequisite:** Prepared ERPNext Items in M/L/P/S/O streams; effective dates and company recorded.

**UI steps:** Open each construction resource Item and its Resource Price History. Admin creates one authorized manual price; Owner/PM inspect it; Site Engineer tries to change it.

**Expected:** Codes, UOM, stream, bilingual name and company are correct; only permitted roles edit prices. Resource Item stock behavior follows Item configuration; do not assume every resource is non-stock.

#### UI-16 — Direct cost and additive pricing

**Login:** Owner. **Prerequisite:** Separate H-COST Draft line with contract rate 150 and manual cost 60; resource rate 100.

**UI steps:** Create BOQ Cost Analysis linked to the line: analysis qty 1; detail qty 1, rate 100, wastage 0; overhead 10%, profit 10%, allowance 0. Save. Set tender tax allowance 5 and save.

**Expected:** Direct unit cost 100; suggested selling rate 120 then 125. Tender allowance is a costing input, separate from invoice taxes.

#### UI-17 — Batch quantities, wastage and streams

**Login:** Owner. **Prerequisite:** New Draft analysis and five resource streams.

**UI steps:** First use analysis qty 10, resource qty 20, rate 5, wastage 10%. Save; then add one known-value row for each remaining stream and compare with the fixture worksheet.

**Expected:** First resource amount 110 and normalized direct unit cost 11. Each stream is counted once; totals match independent calculations. Quantity labels must not obscure batch normalization.

#### UI-18 — Cost validation and scope

**Login:** Owner. **Prerequisite:** Disposable Draft analyses.

**UI steps:** Try analysis qty 0 and negative; negative resource qty/rate; wastage above 100; non-template without BOQ Item; company mismatched to linked project. Restore valid values between attempts.

**Expected:** Invalid inputs are refused with understandable messages; no submitted or active cost is altered. Mark each variant separately.

#### UI-19 — Approve cost without changing contract rate

**Login:** Owner. **Prerequisite:** UI-16 analysis ready; cost item manual basis 60.

**UI steps:** Submit analysis A. Reopen item, header and analysis. Attempt direct edit of approved cost inputs through ordinary item/form controls.

**Expected:** Active analysis A and direct estimated unit cost 100; suggested sell 125; contract rate remains 150. Approved basis/provenance cannot be overwritten by ordinary editing.

#### UI-20 — Supersede and restore prior approval

**Login:** Owner. **Prerequisite:** A approved; B is a new analysis with direct cost 120 and known percentages.

**UI steps:** Submit B; verify A superseded. Cancel B using normal permitted action; reopen all linked records.

**Expected:** B initially active with direct cost 120; cancellation restores eligible A with cost 100 and its percentages, and correct header totals.

#### UI-21 — Restore manual cost including zero

**Login:** Owner. **Prerequisite:** Three independent prepared cost fixtures: manual 60, manual 0, manual changed to 70 between approval cycles.

**UI steps:** For each fixture approve its sole analysis, cancel it and reopen item/header. For the third, complete one cycle, edit manual basis to 70, then repeat approval/cancellation.

**Expected:** Manual 60, 0 and 70 respectively are restored with captured percentages. Zero is not replaced by another amount; screenshots identify each independent case.

#### UI-22 — Cancel superseded history

**Login:** Owner. **Prerequisite:** Dedicated fixture with A superseded by active B.

**UI steps:** Cancel A, then inspect B, item and header; reload in a fresh tab.

**Expected:** Active B and its financial basis stay unchanged. Native linked-document restrictions must be understood; do not bypass a refusal with database editing.

#### UI-23 — Templates and legacy hold

**Login:** Owner + Admin. **Prerequisite:** Admin provides reusable template and safely prepared Legacy Review record.

**UI steps:** Open a template without live BOQ link; make a separate analysis by manually copying its recipe. On Legacy Review item attempt ordinary price save/new approval.

**Expected:** Template does not automatically price a live item; manual-copy result is checked. Unresolved legacy basis remains blocked with reason. Operator conversion is a separate engineering activity, not an owner UI workaround.

### 4. Stage planning and measurement

#### UI-24 — Create planned stages

**Login:** Site Engineer. **Prerequisite:** H-STAGE Draft item qty 10, factor 1, Has Stages checked.

**UI steps:** Create two BOQ Item Stages using Project → Header → Structure → Item: planned 4 and 6. Save and reopen; inspect codes/onboarding guidance.

**Expected:** Stages identify the correct item and planned sum 10. Duplicate stage code and wrong parent chain are refused.

#### UI-25 — Measure work and validate quantities

**Login:** Site Engineer. **Prerequisite:** Stages prepared before parent freeze/lock; not yet certified.

**UI steps:** Record measured 3, percent complete 75 on planned-4 stage. Try negative measurement and percent 101. On a separate Draft fixture try planned total above parent quantity.

**Expected:** Valid measurement persists; negative values, percentage outside 0–100 and prohibited over-allocation are rejected. This is measurement recording, not a payment certificate.

#### UI-26 — Certify with correct authority

**Login:** PM + Site Engineer. **Prerequisite:** Measured 3 stage; PM has confirmed certifier permissions.

**UI steps:** Site Engineer tries certified qty 2 or Certified status. PM tries certified qty 4, then 2. Reopen as both users.

**Expected:** Site Engineer cannot certify; certification above measured 3 refused; PM certification 2 accepted. Any positive certified quantity makes the record protected, even if status label differs.

#### UI-27 — Certified and locked-stage protection

**Login:** PM. **Prerequisite:** Separate certified and Frozen/Locked stage fixtures.

**UI steps:** Try changing certified quantities, identity, status and description. On an uncertified locked-parent stage try planned_qty/name edit and valid measurement edit.

**Expected:** Certified commercial/evidence fields remain immutable. Locked planning fields stay fixed; allowed measurement updates persist. No direct reset to bypass certification.

#### UI-28 — Stage distribution at lock and after revision

**Login:** Owner + PM. **Prerequisite:** Complete 4+6 plan; separate incomplete plan; engineer supplies supported correction sequence.

**UI steps:** Attempt parent lock with incomplete plan, then complete it and retry. On a dedicated staged BOQ process a quantity-change VO; inspect revised quantity and attempt normal stage update.

**Expected:** Lock/distribution behavior matches current validation. After VO, no silent mismatch or invented editable route; an impossible reallocation is recorded as a workflow defect/limitation for triage.

### 5. Variation Orders and quantity history

#### UI-29 — VO entry and lifecycle prerequisites

**Login:** PM. **Prerequisite:** H-VO Locked, no stages; baseline qty 100, rate 50, factor 1; separate Draft header.

**UI steps:** From H-VO use Actions → New Variation Order or Variation Orders → New. Enter reason; add Quantity Change line. Try Draft header selection and direct Draft → client approval jump.

**Expected:** Only permitted header/status combinations accepted; line basis derives from its BOQ; transition bypass refused.

#### UI-30 — Increase, approvals and separation of duties

**Login:** PM + Approver + Owner. **Prerequisite:** Distinct ordinary identities: preparer PM, engineer approver, client approver Owner; valid synthetic signed PDF.

**UI steps:** Request qty 126 and rate 60 with justification. Submit; same preparer tries engineer approval and is refused. Distinct approver approves engineer stage. Try editing line. Owner attaches PDF and performs client approval.

**Expected:** Actors/dates retained; lines protected after engineer approval. Original qty/rate remain 100/50; revised 126/60; original value 5,000, revised 7,560, delta 2,560. History records increase above 25%.

#### UI-31 — PDF evidence and approval restrictions

**Login:** Owner. **Prerequisite:** Separate engineer-approved VO; prepared valid PDF, text renamed .pdf and unrelated attachment.

**UI steps:** Try client approval without PDF, with disguised non-PDF, and with another VO’s attachment. Then attach valid PDF to this VO and approve as distinct client approver.

**Expected:** Invalid/missing/mislinked evidence refused; valid case accepted. Ordinary preparer/engineer cannot also provide client approval where separation is required. Do not use Administrator/System Manager for this proof.

#### UI-32 — Decrease based on current quantity

**Login:** PM + Approver + Owner. **Prerequisite:** UI-30 completed.

**UI steps:** New VO sets current qty to 90 and revised rate 60; follow distinct-user approvals with evidence. Inspect revision and header.

**Expected:** Previous qty 126; delta -36; original qty still 100; current qty 90, revised value 5,400. Baseline-relative change and prior-revision delta are distinguishable.

#### UI-33 — Omission and selection gates

**Login:** PM + Approver + Owner. **Prerequisite:** UI-32 completed; separate transaction draft for lookup.

**UI steps:** New Omission VO for same item; approve. Reopen item/history and new BOQ selectors on transaction and VO.

**Expected:** Revised qty/value 0; original baseline retained; omitted item unavailable for new selection; historical references remain readable.

#### UI-34 — New variation scope item

**Login:** PM + Approver + Owner. **Prerequisite:** Dedicated VO; H-VO group available.

**UI steps:** Choose New Item line with group structure, title, UOM, qty 5, rate 200. Approve through normal roles. Open created item/structure links.

**Expected:** Created item has original qty 0, revised qty 5, variation traceability and revised value 1,000. Free-text BOQ specification does not require Item Code.

#### UI-35 — Final totals, history and repeated save

**Login:** Owner. **Prerequisite:** UI-30–34 completed in order on H-VO only.

**UI steps:** Open Revised BOQ View and BOQ Quantity Revision list; note count. Re-save approved VO without changes if offered; reload twice. Try editing/deleting approved revision/evidence.

**Expected:** H-VO original value 5,000; revised value 1,000 after omission plus new item. No duplicate revisions/items; approved history/evidence immutable. Corrections require a new supported revision.

#### UI-36 — Reject, justification and rate/factor cases

**Login:** PM + Approver. **Prerequisite:** Separate fixtures so H-VO arithmetic stays intact.

**UI steps:** Reject an unapproved VO through the offered transition. Attempt above-threshold rate change without justification. Run a factor-0.5 variation with engineer-calculated expected quantity/rate delta.

**Expected:** Rejected VO does not update BOQ basis; required justification enforced; factor included once in revised values. Engineering records permitted resubmission/new-VO route rather than guessing a Reset action.

### 6. All eight construction transaction integrations

#### UI-37 — Material Request

**Login:** Procurement. **Prerequisite:** Locked available BOQ and stock Item; Direct row.

**UI steps:** Create Material Request; select project then BOQ Header → Structure → Item → Stage where applicable. Save/submit as allowed. Repeat common row checks below.

**Expected:** Correct attribution persists; irrelevant stage is not forced. Submission and downstream mapping follow the configured native workflow.

#### UI-38 — Purchase Order

**Login:** Procurement. **Prerequisite:** Material Request or independent PO fixture; resource Item with known rate.

**UI steps:** Create PO from the approved request where supported; verify each mapped BOQ field, supplier, UOM, qty, rate; submit. Inspect Resource Price History.

**Expected:** No silent loss/wrong copying of attribution; native commitments correct; eligible resource rate captured with source document/row and company. Complete common row checks.

#### UI-39 — Purchase Receipt

**Login:** Stores. **Prerequisite:** Submitted PO; warehouse and stock settings prepared.

**UI steps:** Create partial PR for 6 of 10 units; inspect each attribution; submit. View stock ledger and remaining PO quantity.

**Expected:** Stock increases by 6 in intended warehouse; PO remaining quantity is 4; BOQ scope retained/explicitly reselected correctly. Complete common row checks.

#### UI-40 — Purchase Invoice

**Login:** Finance. **Prerequisite:** Prepared PO/PR; independent expected accounting sheet.

**UI steps:** Create PI from PR for 6 units; inspect attribution, quantities and configured taxes; submit. Open General Ledger and Resource Price History.

**Expected:** Only received/invoiced fixture quantities billed as configured; balanced ledger matches finance sheet; eligible source price recorded. Complete common row checks.

#### UI-41 — Sales Invoice progress-billing gate

**Login:** Finance. **Prerequisite:** Customer and separate invoice fixtures; no certificate module assumed.

**UI steps:** Create SI with Is Progress Billing enabled on applicable row; select BOQ chain and submit the permitted fixture. Repeat on an ordinary non-progress row, then inspect ledger and receivable.

**Expected:** Progress flag drives BOQ requirement; ordinary sales follow their configured rules. Invoice balances match finance sheet. This proves SI attribution, not certificate/retention automation. Complete common row checks.

#### UI-42 — Stock Entry

**Login:** Stores. **Prerequisite:** Known stock balance and two test warehouses.

**UI steps:** Create intended Material Issue or Transfer, Direct row, correct project/BOQ chain; submit. Inspect source/destination quantities and ledger; cancel only the independent cancellation fixture.

**Expected:** Movement occurs once with correct scope; reversal follows native rules. Complete common row checks.

#### UI-43 — Timesheet and Direct Labor Designation

**Login:** Site Engineer + Finance. **Prerequisite:** Employee and two designations: included/excluded from configured direct labor list.

**UI steps:** Create Timesheet rows under each designation; select project and BOQ chain where gated. Save/submit with known hours; reopen.

**Expected:** Direct labor gate follows configured designation; hours persist once. Excluded designation follows native requirements. No payroll/automatic labor-cost claim beyond configured functionality. Complete common row checks.

#### UI-44 — Journal Entry override

**Login:** Finance. **Prerequisite:** Balanced independent JE fixture; configured project/cost center.

**UI steps:** Enter debit and credit rows with Direct expense classification where appropriate; select BOQ chain. Try unbalanced save/submit then correct and submit; inspect ledger.

**Expected:** Native balancing enforced; construction fields preserved and scope validated on relevant rows. Complete common row checks.

### 7. Finance and native ERPNext dependencies

#### UI-45 — Supplier payment and customer receipt

**Login:** Finance. **Prerequisite:** Submitted isolated PI and SI; expected residual balances.

**UI steps:** Use native Payment Entry against each invoice; make partial payment/receipt, submit and reopen invoice and AP/AR.

**Expected:** Allocations, outstanding balances, bank/cash and party ledger match finance worksheet. No claim of Egypt e-invoice submission.

#### UI-46 — Cancellation and audit trail

**Login:** Finance + Procurement. **Prerequisite:** Independent PO/PI/stock/payment fixtures with documented dependency order.

**UI steps:** Cancel downstream documents in permitted order, then source PO/PI; inspect stock, GL and price-history rows. Try cancelling a still-linked source first.

**Expected:** Native link guard blocks unsafe order; reversals reconcile; captured source prices marked Cancelled and excluded from active use, not erased.

#### UI-47 — Budget and variance controls

**Login:** Finance + PM. **Prerequisite:** Native Budget for project/cost center, chosen Warn/Stop settings and transaction types recorded.

**UI steps:** Enter below-budget and above-budget purchase/expense fixtures; inspect warning/refusal and Budget Variance Report.

**Expected:** Behavior follows configured ERPNext controls and finance-calculated actuals. Do not equate BOQ estimate approval with automatic creation of ERPNext Budget.

#### UI-48 — Native commercial handoffs used by pilot

**Login:** Procurement + Owner. **Prerequisite:** Prepared supplier/customer; owner selects used native flows in manifest.

**UI steps:** For used flows run RFQ → Supplier Quotation → PO and Lead/Opportunity → Quotation → Sales Order/customer handoff. Reopen mapped quantities, rates and project links.

**Expected:** Each enabled native handoff retains its expected data. Unsupported BOQ auto-conversion is documented rather than assumed. Split results by handoff; unused optional native modules need explicit scope disposition.

#### UI-49 — Quality/asset dependencies if used

**Login:** Stores + Finance. **Prerequisite:** Manifest declares applicable Quality Inspection/Asset processes; independent fixtures.

**UI steps:** For applicable receipt inspection, record pass/fail and exercise configured receipt gate. For asset purchase, open created Asset and relevant register.

**Expected:** Native configured controls and asset values match fixture. PlantResource schema alone does not prove equipment maintenance, rental or utilization workflows.

### 8. Import, export and reference coverage

#### UI-50 — BOQ Excel import through the actual button

**Login:** Owner. **Prerequisite:** H-IMPORT fresh Draft; team-supplied 3-line valid workbook with independent counts/totals.

**UI steps:** Use Actions → Import Excel; attach workbook, click Import. Note message. Refresh header, item/structure lists and Import Batch; count saved records. Try the documented confirmation step only if the UI actually provides it.

**Expected:** Success requires committed records and correct totals/traceability, not only a green message. Known source mismatch K-01 must be resolved/reproduced before this can pass.

#### UI-51 — Import validation and safe retry

**Login:** Owner. **Prerequisite:** Separate headers and small valid/invalid/ambiguous workbooks supplied by engineering.

**UI steps:** Through available UI run invalid factor, missing UOM, ambiguous classification and duplicate/retry variants. Inspect errors, resulting records and batch traceability. Try import on Locked header.

**Expected:** Blocking errors cause no partial committed BOQ; ambiguity requires supported explicit resolution; retry does not silently duplicate; locked header cannot accept import. Missing UI review/commit route is Blocked/Fail, never a pass via developer console.

#### UI-52 — BOQ workbook/PDF/print exports

**Login:** Owner. **Prerequisite:** F1 and final H-VO fixture.

**UI steps:** Use header Export menu: Excel/PDF/Print, Header Only and Full BOQ. Open every output; compare original/revised quantity, factor, rate, totals and owner/source refs. Repeat as restricted account.

**Expected:** Outputs match selected basis and fixture; factor applied once; no excluded project data. Original value may remain in original-contract columns; revised values must be clearly identified and correct.

#### UI-53 — BOQ Import Batch evidence

**Login:** Admin + Owner. **Prerequisite:** Successful/failed or preview batches from engineering or UI import.

**UI steps:** Open BOQ Import Batch by search; inspect status/counts/source file and item source row links. Follow a source attachment as permitted and repeat as restricted account.

**Expected:** Traceability matches the actual import outcome; preview is not labelled committed; private source file obeys access policy. If UI import cannot create a batch, record the limitation explicitly.

#### UI-54 — CostItem and PlantResource schema disposition

**Login:** Admin. **Prerequisite:** Engineering checks whether these DocTypes are installed/exposed and declares supported basic use.

**UI steps:** If exposed, open list/form and create a disposable minimal reference, save/reload, test required codes and available read access. If not exposed, record manifest exclusion and source-only status.

**Expected:** Only actual reference-field CRUD is claimed. No invented Item linkage, plant operations or automated costing. Required-but-missing deployment becomes a defect; intentionally unexposed scaffolding has an owner-approved exclusion.

### 9. Reports, bilingual accounting and printing

#### UI-55 — All 11 protected financial reports

**Login:** Finance. **Prerequisite:** Populated current-period fixture and finance totals; report-role matrix prepared.

**UI steps:** Run each report listed below using Company A/period/project where supported. Check detail rows, totals and document drill-down; export where offered. Repeat protected access as restricted user.

**Expected:** Each report matches independently calculated balances and enforced company/scope behavior. Record one subresult per report; a blank report alone is not financial validation.

#### UI-56 — All four protected dashboard reports

**Login:** PM + Finance. **Prerequisite:** Seeded purchases and asset fixture; allowed report access.

**UI steps:** Open each of Purchase Order Trends, Purchase Receipt Trends, Purchase Analytics and Fixed Asset Register. Change allowed filters and attempt forbidden company.

**Expected:** Chart/report values reflect fixtures and correct company; no unauthorized data. Record separate results for all four.

#### UI-57 — Bilingual Report Viewer

**Login:** Finance. **Prerequisite:** Engineering confirms installed route; seven core reports populated.

**UI steps:** Search Bilingual Report Viewer; select report, company, period and language. Compare native report with viewer for the seven named reports below; test refresh/export.

**Expected:** Amounts agree between native and viewer; Arabic labels/accounts display correctly; filter/date defaults do not select an unintended future fiscal year.

#### UI-58 — Report stale results, empty data and errors

**Login:** Finance + Restricted. **Prerequisite:** Two reports/periods with deliberately different known totals; denied user.

**UI steps:** Change report/filter quickly; select an empty period; trigger denied report; restore valid choice. Try direct viewer URL as restricted user.

**Expected:** Latest selection wins; empty/error state clears old values; forbidden report/company is not shown. No old totals presented as new results.

#### UI-59 — Arabic account/customer/supplier search

**Login:** Owner + Finance. **Prerequisite:** Bilingual names and duplicate-looking account labels prepared.

**UI steps:** Switch to Arabic. Search account links on JE/SI and customer/supplier selectors in Arabic and English; use account tree/form bilingual view. Save, print and reopen a fixture.

**Expected:** Search selects the intended internal record; translations do not rename account identity or change ledger links. Mixed-direction codes and numbers remain readable.

#### UI-60 — Four commercial print formats

**Login:** Owner. **Prerequisite:** PO, SI, Stock Entry and Material Request fixtures, including a multi-page document.

**UI steps:** Preview and save PDF for each installed construction print format in Arabic and English. Check logo/header, parties, project, row wrapping, totals, page breaks and signatory areas.

**Expected:** All eight language/document combinations are readable with correct totals and no clipped/repeated/missing rows. Log each variant separately; preview alone does not prove downloaded PDF quality.

### 10. Theme, native forms and personal layouts

#### UI-61 — Themes and personal preference isolation

**Login:** Owner + Site Engineer. **Prerequisite:** Two ordinary users; engineering documents current theme controls.

**UI steps:** Switch Light/Dark and available custom theme; change supported font/density preferences; reload/log out/in. Open other user session and another browser if available.

**Expected:** Supported server preferences persist per user; browser-only preferences are labelled accordingly. Text, required/error states, grids and dialogs remain legible; no leakage of personal changes to the other user.

#### UI-62 — Theme administration and native controls

**Login:** Admin + Owner. **Prerequisite:** Construction Theme, Modern Theme Settings and User Desk Theme installed.

**UI steps:** Admin applies one reversible theme setting; users open BOQ Item, SI and JE. Exercise link autocomplete, select, date, attachment and Save/Submit. Restore baseline.

**Expected:** Settings persist with proper permissions; native controls work; toolbar/theme buttons never cover Save/Submit. Public/legacy loaders are not assumed supported simply because source files exist.

#### UI-63 — Layout controls, density and presets

**Login:** Owner. **Prerequisite:** Eligible BOQ Header/Item/Stage profiles confirmed; ordinary user.

**UI steps:** Open Form Config; change 1/2/3-column density, field visibility and available preset; refresh and reopen. Attempt to expose a dependency-hidden field.

**Expected:** Supported layout preferences work without missing mandatory input or changing document values; dependency-hidden fields remain governed by native rules. Record density as browser-local if that is actual behavior.

#### UI-64 — Shared/personal layout permissions and reset

**Login:** Admin + Owner. **Prerequisite:** Admin-prepared default, role and personal profiles; supported non-tabbed form.

**UI steps:** Admin saves a section layout. Ordinary user attempts shared-profile save, then changes own preferences and uses Revert to Default/Native; refresh. Test other user profile.

**Expected:** Privileged profile save controlled; ordinary users can reset their own layout without editing others. Personal → role → default resolution matches setup. Revert restores usable form and fields.

#### UI-65 — Unsupported layout and responsive usability

**Login:** Owner. **Prerequisite:** Representative tabbed form and laptop widths 1366 and 1280; zoom 100%/125%; actual browser recorded.

**UI steps:** Open tabbed/excluded forms; navigate without forcing VFC. On core forms open long tables/dialogs and keyboard-tab through required fields, save and close. If mobile use is required, repeat on intended phone browser.

**Expected:** Native forms remain usable where VFC is skipped; no clipped primary actions or focus traps. Mobile observations do not establish offline support; unsupported advertised workflow is a recorded issue.

### 11. Recovery from everyday errors and complete business rehearsal

#### UI-66 — Two-session stale edit

**Login:** Owner + PM. **Prerequisite:** Disposable Draft record opened in two separate ordinary-user sessions.

**UI steps:** User A saves a price/quantity edit; user B tries saving older content. Refresh both and inspect final values.

**Expected:** Conflict/reload behavior prevents silent overwrite of protected business state; user can understand retry. This is not proof of database concurrency correctness.

#### UI-67 — Network failure and repeat click

**Login:** Owner. **Prerequisite:** Safe disposable Draft; no active financial submission in other tabs.

**UI steps:** Briefly use browser offline mode while saving a draft; reconnect, reload and inspect. On separate fixture click permitted approval once and refresh before deciding any retry.

**Expected:** Clear error or recoverable state; no silent loss labelled success, no duplicate document/approval. Do not repeatedly submit blindly after an uncertain result.

#### UI-68 — Egyptian contractor daily journey

**Login:** Owner + All. **Prerequisite:** Earlier individual cases pass; fresh mini-project E2E-A; finance expected totals.

**UI steps:** Through normal UI run project → BOQ/WBS → analysis approval → planned stages → lock → measure/certify; run one independent VO; procure/receive/invoice/pay; issue sales invoice/receive payment; inspect revised BOQ, GL, AP/AR and Arabic PDF.

**Expected:** All handoffs keep project/company and financial basis; no developer-console assistance. Use separate staged and VO items to preserve supported stage policy. Log total minutes, repeated entry, confusing steps and unresolved handoffs.

#### UI-69 — Repeatability and final acceptance rehearsal

**Login:** Owner. **Prerequisite:** Candidate with all accepted fixes; new fixture pack.

**UI steps:** Repeat UI-68 independently using only this guide and corrected user instructions. Re-run impacted cases and core smoke list after last fix. Complete final decision form.

**Expected:** Owner can complete the supported workflow; every mandatory case/variant has evidence and an accepted outcome on the final candidate. No new feature starts automatically.

## 7. Expanded report/output coverage

UI-55 covers **11** protected financial reports: General Ledger; Trial Balance; Profit and Loss Statement; Balance Sheet; Accounts Payable; Accounts Payable Summary; Accounts Receivable; Accounts Receivable Summary; Budget Variance Report; Cash Flow; Project-wise Profitability. Do not reuse the older “10 reports” count. For reports that cannot express project scope, document actual supported filtering and prove company/role authorization; do not claim row isolation from a hidden filter alone.

UI-56 adds four protected dashboard/report functions: Purchase Order Trends; Purchase Receipt Trends; Purchase Analytics; Fixed Asset Register. Optional native modules may be explicitly excluded, but their permission boundary remains an engineering requirement if the report route is installed and accessible.

UI-57 compares seven bilingual report samples: Trial Balance; Balance Sheet; Accounts Payable Summary; Accounts Receivable Summary; Profit and Loss Statement; General Ledger; Cash Flow. Engineering inventories any additional report offered by the actual viewer and adds it. UI-60 requires PO, SI, Stock Entry and MR in both English and Arabic, including multi-page output. UI-52 covers all six advertised BOQ header/full workbook/PDF/print menu variants.

## 8. Source-to-test coverage ledger

| Construction schema or override | Owner cases / engineering coverage | Scope note |
|---|---|---|
| BOQ Header | UI-08,12,13,29,35,50–52 | Lifecycle, totals, views and output |
| BOQ Structure | UI-09,11–14,34,51 | Hierarchy, leaf rules, deletion and variation trace |
| BOQ Item | UI-10–13,16–23,30–35 | Free-text specification, factor, active cost and revised basis |
| BOQ Item Stage | UI-24–28, transaction row variants | Planning, measurement and certification |
| BOQ Cost Analysis | UI-16–23; T-01,03 | Approval/restoration plus legacy behavior |
| BOQ Cost Analysis Detail | UI-16–18,23 | Child rows within parent analysis |
| Variation Order | UI-29–36; T-01,02 | Workflow, actors and PDF evidence |
| VO Line | UI-29–36 | Child rows within VO |
| BOQ Quantity Revision | UI-30–36; T-01 | Immutable baseline/history |
| BOQ Import Batch | UI-50,51,53; T-04 | Preview/commit outcome and provenance |
| Resource Price History | UI-15,38,40,46; T-04 | Manual permissions and PO/PI lifecycle |
| CostItem | UI-54 | Basic reference schema only unless deployed scope proves more |
| PlantResource | UI-54 | Basic reference schema; no assumed plant lifecycle |
| Construction Settings | UI-02,06, transaction variants | Settings/flags and security impact |
| Direct Labor Designation | UI-02,43 | Active settings child table |
| User Scope Context | UI-03–06; T-02 | Defaults, allowed dimensions and drift |
| Scope Report Access Log | UI-06; T-02 | Admin-visible audit evidence and permissions |
| Construction Theme | UI-61,62 | Shared theme configuration |
| Modern Theme Settings | UI-61,62 | Supported settings and persistence |
| User Desk Theme | UI-61,62 | User-specific preference isolation |
| Form Layout Profile | UI-63–65; T-06 | Profile resolution, reset and permissions |
| Journal Entry override (ERPNext owns schema) | UI-44,59; T-01,02 | Native accounting plus construction row gates |

The eight transaction integrations each have a dedicated case, UI-37–44. Native Project/Task, Budget, purchase, stock, invoicing, payments, CRM handoffs and optional asset/quality dependencies are covered through UI-07,37–49. This ledger is a baseline for the deployed inventory, not a substitute for it.

## 9. Engineering evidence outside Mohamed's UI test

The owner should not be asked to execute API calls, shell commands or developer-console scripts. Review these evidence summaries alongside his UI acceptance. For each task record exact candidate, fixture, tool/log and result; retain a clear distinction between tests newly run and historical evidence.

| ID | Required engineering task | Completion condition |
|---|---|---|
| T-01 | Re-run financial/lifecycle regressions for factor, additive pricing, active analysis, manual/zero/superseded cancellation, revision immutability, stage controls and all eight transaction gates | Candidate-bound positive/negative tests pass; rollback and totals agree; fix-specific tests cover the cause |
| T-02 | Verify direct server/API, report, dashboard, export and private-file authorization for ordinary roles, cross-company/project records, methods and disabled flags | Unauthorized reads/writes denied server-side; UI hiding alone is insufficient; scope/report audit evidence checked |
| T-03 | Exercise existing transaction guard suite and relevant true concurrent approval/cancel/import scenarios with independent connections; run existing Administrator-only read-only rollup audit | No partial commits or duplicate active basis; contention/retry documented; audit reports reconciled. Two UI tabs alone do not prove this |
| T-04 | Test BOQ and cost-database import bounds, preview/commit atomicity, ambiguity, retry, Unicode headers, source-file access, rate selection, repricing and exports | Admitted workbooks correct; malformed/over-limit fixtures fail safely without partial changes. Reuse existing limits, do not rebuild them from stale gap claims |
| T-05 | Qualify exact install/upgrade/dependency state; review security findings and perform representative backup/restore/legacy conversion rehearsal where applicable | Candidate and environment pinned; data/files/history preserved; unresolved legacy cases held. No production/shared-site action inferred from this plan |
| T-06 | Verify native/VFC safeguards, own/other-user profile permissions, skipped forms, malformed/unknown fields, and candidate assets/build/browser compatibility | Supported surfaces stable; unsupported ones correctly remain native; no global deprecated React loader introduced |
| T-07 | Test bounded realistic responsiveness and reliability through actual HTTP/workers with ordinary roles, reports, writes, imports and PDF generation | Workload, errors and observed response times recorded; owner sets acceptable pilot thresholds before measurement. Historical Administrator read timings are not an SLA |
| T-08 | Refresh operating notes, source/candidate mapping, private CI evidence where applicable, role/workspace guidance, release limits and recovery contacts | One coherent private acceptance pack; outstanding release issues remain explicit; no claim of customer release just because UAT is complete |

### Existing capabilities with no established customer UI

- **Five cost-report services:** analysis summary, item cost versus contract, resource requirement summary, resource price history query, and missing-analysis items. Team tests the actual service and shares readable sample results; no Desk report is promised. Resource requirement planning currently uses contract quantities, factor, wastage and batch normalization; it is not a revised-quantity procurement forecast.
- **Cost-database workbook import, bulk repricing and template download:** documented primarily as endpoints. Engineering verifies current interface availability. Service tests cover dry run, identity-based retry behavior, submitted-template protection, company/currency/UOM/date rate selection and draft-only repricing. A downloaded template alone does not establish a usable import workflow.
- **Rollup audit:** internal Administrator-only read-only service; do not invent an owner reconciliation screen or require owner admin access.
- **Legacy basis conversion, locking and infrastructure recovery:** operator/engineering activities with their own evidence. Owner reviews before/after business values where relevant.

Classify these in the inventory as backend-tested/UI-unavailable where that is true. If Mohamed needs a particular one through UI for acceptance, it stays an explicit unmet requirement until a scope decision; it cannot silently become “Passed” through a developer demonstration.

## 10. Known issues to resolve before relying on old instructions

| Ref | Evidence found in source/docs | Required handling now |
|---|---|---|
| K-01 | BOQ Header's Import Excel handler calls `import_boq_excel` without `dry_run`; API defaults `dry_run=1`; handler displays “Import successful” when preview `success` is true | Reproduce on actual UAT candidate. Confirm whether another deployed UI supplies preview/commit. If not, record broken advertised import workflow; do not report committed import from the message. No implementation performed here |
| K-02 | User Guide §9.3 describes projecting total/suggested cost onto the BOQ item; confirmed financial rules project direct cost and preserve contract rate | Correct guide and expected worksheet before UI-16–23. Use direct cost 100/suggested 125/contract 150 example |
| K-03 | August UAT plan broadly describes PM as unable to change costs and mixes admin setup with ordinary-owner checks | Derive effective role expectations from current installed permissions/controller rules. Keep distinct approval identities and admin-only setup |
| K-04 | Old documentation can overstate universal form-layout support or treat service-layer reports/imports as usable screens | Inventory supported forms/routes; use backend-only classification where appropriate; no “all existing UI passed” claim with missing mandatory routes |

These are planning findings, not new runtime failures already reproduced. The defect register preserves that distinction.

## 11. Defects, fixes and retesting

| Severity | Meaning | Handling |
|---|---|---|
| S0 Critical | Cross-company/file disclosure, data loss, duplicate financial posting, corrupted approval/history | Stop affected testing; isolate cause and fix before continuing that path; cannot waive for next-feature readiness |
| S1 High | Wrong monetary/quantity result, authorization failure, blocked required business workflow or no usable promised UI | Fix and owner-retest before Gate B; only unaffected sessions may continue |
| S2 Medium | Important usability or reporting defect with a safe documented workaround and no monetary/security/history impact | Prefer fix now; any deferment needs owner reason, responsible person and target date |
| S3 Low | Cosmetic/text issue with no functional ambiguity | Record and fix in a bounded batch or explicitly accept with deadline |

Lifecycle: **Observed/source finding → Reproduced → Triaged → Fix in progress → Ready for owner retest → Verified closed**. Use “Not reproduced” only with the tested environment/steps and evidence; it does not erase the report. An engineer passing a unit test cannot mark the owner's failed UI case closed.

After a fix, engineering records changed source/assets/settings and targeted regression evidence. Mohamed reruns the original case, its invalid/denied variants, and any linked downstream case. A pricing change triggers item/header/VO/export checks; a scope change triggers ordinary-role list/link/report/export/file checks; a layout change triggers native Save and mandatory-field checks; an import change triggers preview/commit/count/retry/rollback checks. On the final candidate, repeat UI-03,10,19–21,26–27,30–35, the valid paths UI-37–44, UI-50,52,55,60,64,68–69 and affected security variants. Preserve earlier results but identify any invalidated evidence.

## 12. Gate B: existing-feature acceptance before next-feature implementation

- [ ] Deployed inventory is complete and every active in-scope behavior maps to a test.
- [ ] Every mandatory UI case and every required role/report/print/transaction variant passed on the final candidate or has traceable unaffected evidence accepted after the final change review.
- [ ] No mandatory Not Run/Blocked case, no S0/S1 defect, and no unresolved wrong-money, unauthorized-access, broken approval or missing-history result remains.
- [ ] Optional exclusions and backend-only limitations are individually accepted with business impact. Required existing functionality is not excluded just to close UAT.
- [ ] Any deferred S2/S3 issue has a safe workaround where needed, named owner and date; no blanket acceptance.
- [ ] Finance/QS confirm expected totals, approval traceability, quantities and sample outputs.
- [ ] T-01–T-08 have candidate-bound evidence and no unresolved issue blocking the safe intended test/pilot scope; release-only obligations are separately labelled and retained.
- [ ] Mohamed completed the final realistic journey independently and can use the corrected instructions.
- [ ] Result ledger, defects, candidate/settings, evidence and user guide are preserved together.
- [ ] Mohamed signs **Existing features accepted for the recorded scope**; GM/owner explicitly authorizes the next-feature definition/implementation scope afterwards.

**Passing this gate is not production deployment or customer go-live approval.** Hosting/security/operations/compliance obligations for a customer release remain separate. If Gate B is not met, continue stabilization; do not use a future feature to hide an existing broken workflow.

## 13. How this informs the later Egypt-first roadmap

During UI-68–69, record baseline time to create/import a BOQ, approve a cost analysis, complete a VO, attribute a purchase, and prepare an Arabic output; count duplicate entries, spreadsheet workarounds and mistakes. Distinguish a current defect from a missing feature and a training problem. These observations are internal baseline evidence, not proof of Egyptian market demand.

After acceptance, compare the measured gaps with actual Egyptian SME client interviews and the [market benchmark](construction_erp_egypt_mena_market_benchmark.md). Re-evaluate certificates, procurement/cost visibility and subcontracting in that order only where customer evidence supports it. Country-specific e-invoice and Gulf entry work needs later qualified scope. Payment certificates, retention/advance recovery automation, a subcontract lifecycle, plant lifecycle, site diaries, offline operation, new FX policy and a new tax connector are **not existing features to mark as passed** in this pack.

## 14. Evidence and document verification

Sources inspected for this plan include:

- [Professional Engineering Standard](../../PROFESSIONAL_ENGINEERING_STANDARD.md), [Context Index](../../CONTEXT_INDEX.md), [schema facts](../../SCHEMA_FACTS.md), repository `AGENTS.md`, `AGENT_WORKFLOW.md` and `SESSION_MEMORY.md`.
- [Existing User Guide](../../../USER_GUIDE.md), [August role UAT plan](../../../UAT_PLAN_2026-08-21.md), and [VO manual QA](../../../feature_reviews/evidence/ev_067_ui_tests/VO_QUANTITY_REVISION_MANUAL_TEST.md), treated as dated guidance with the corrections above.
- [Confirmed financial rules](../customer-release-gap-fixes/FINANCIAL_RULES.md), [release operating profile](../customer-release-gap-fixes/RELEASE_OPERATING_PROFILE.md), prior management/market reports and line-by-line reconciliation.
- Actual source: `construction/construction/doctype/boq_header/boq_header.js`, `construction/api/boq_api.py`, `construction/services/boq_import_service.py`, `construction/construction/doctype/variation_order/variation_order.py`, `construction/construction/doctype/boq_item_stage/boq_item_stage.py`, `construction/services/boq_operational.py`, `construction/services/boq_scope_registry.py`, `construction/overrides/report_guard.py`, `construction/overrides/scope_report.py`, and DocType JSON/schema inventory.

Planning checks: schema checker passed **21 schema owners + one override**; context checker passed **11 checks, zero failures**. Source/Markdown inventory, unique case IDs, ledger coverage, relative links and table structure were checked. These checks validate the plan's structure and local source facts; they do not validate the deployed UI. All owner cases and engineering tasks remain unexecuted by this document.
