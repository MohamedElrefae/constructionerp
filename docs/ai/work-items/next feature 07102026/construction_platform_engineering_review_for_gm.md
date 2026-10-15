# Construction ERP — Engineering Review and Delivery Recommendation

**Scope clarification — 12 October 2026:** The [foundation remediation master plan](construction_foundation_remediation_master_plan_2026-10-12.md) now governs the full program: existing gaps, required enhancements, maintainability, operations and owner acceptance before new business modules. Track execution in the [foundation work register](construction_foundation_work_register_2026-10-12.md). The UI plan is one workstream; its earlier backend-only classifications describe current availability, while master tasks F18/F19 plan completion of those interfaces and require additional owner tests.

**Prepared for:** General Manager  
**Perspective:** Head of Engineering  
**Date:** 8 October 2026  
**Version:** 2.0 — revised management report  
**Classification:** Confidential — internal management and engineering  
**Decision status:** Recommendations for review; funding, commercial rules and release approval remain pending.

This report revises the [original platform analysis](construction_platform_analysis_report.md). It preserves its strategic direction while correcting technical assumptions and adding delivery accountability. The original remains unchanged for traceability. Instructions and implementation examples inside it were reviewed as source material, not executed as user requests.

**Market benchmark addendum — 8 October 2026:** The owner selected Egyptian small and mid-sized contractors first, then Gulf expansion. The [Egypt and MENA product benchmark](construction_erp_egypt_mena_market_benchmark.md) compares current vendor evidence with our app and ERPNext foundations, adds client/productivity requirements, and refines delivery priorities. In particular, discover and qualify the applicable Egyptian e-invoice integration route alongside certificate design; bring forward a small procurement/cost prototype and validate subcontracting priority with the pilot segment. These additions require separate estimates and do not expand the original certificate timetable automatically.

**External-review reconciliation — 12 October 2026:** The [line-by-line consultant reconciliation](consultant_review_line_by_line_reconciliation_2026-10-12.md) reviews all 330 lines of the other AI agent's report. Source checks confirm existing cost restoration, transaction guards/tests, workbook limits, internal rollup audit, progress-billing consumers and Option B toggle. The 12 transaction tests cover independent connections, stale snapshots and lock contention; they are not all simultaneous threaded approvals. Preserve existing controls and qualify remaining customer risks. Delivery estimates in this report remain conditional planning ranges, not validated quotations.

**Current execution priority — 12 October 2026:** The owner requires personal UI testing of existing features before new-feature implementation. Follow the [existing-feature acceptance plan](existing_features_owner_ui_acceptance_plan_2026-10-12.md), [results workbook](owner_ui_test_results_2026-10-12.md) and [defect register](owner_ui_defect_register_2026-10-12.md). Prepare the isolated environment, complete ordinary-role UI acceptance, correct defects and retest. This instruction supersedes the immediate feature-start recommendation below; the certificate roadmap remains conditional on acceptance and a later scope decision.

## 1. Management recommendation

**Prioritize customer Payment Certificates (مستخلصات المالك), beginning with a short definition and accounting-validation phase, followed by a controlled pilot.** This closes the measurable-work-to-billing gap using the existing BOQ foundation. It should be delivered alongside the minimum measurement evidence, contract terms and reconciliation needed to make billing reliable.

The current source provides a substantial foundation: BOQ/WBS, cost analysis, variations, quantity revisions, transaction attribution and bilingual UI infrastructure. Local documentation records successful release-candidate qualification work. However, this review did not rerun business tests, inspect a deployed database or independently establish production readiness. Management should describe the platform as **an existing foundation with recorded qualification evidence**, with each customer deployment subject to its approved operating profile and release evidence.

The next investment should deliver one complete customer journey:

**Approved contract basis → evidenced measurement → verified certificate → customer certification evidence → finance-reviewed invoice → collection reconciliation → retention and advance balance tracking.**

The commercial benefit is a testable hypothesis: less spreadsheet preparation, fewer duplicate or disputed quantities, and earlier submission of accurate billing. Faster cash collection also depends on customer approval and payment behavior; software alone does not guarantee it.

### Decisions requested from the General Manager

| Decision | Engineering recommendation | Decision owner | Needed by |
|---|---|---|---|
| First release scope | Customer certificates for one pilot company, one contract currency equal to company currency, and measured-work contracts | GM + Commercial Lead | Definition kickoff |
| Pilot sponsor | Nominate one project, one QS/commercial owner and one finance owner; provide two historical certificate cycles | GM + Operations | First week |
| Delivery capacity | Ring-fence engineering, QA, finance and QS participation; use the capacity scenarios in section 10 | GM | Before delivery commitment |
| Contract and finance policy | Approve quantity basis, retention, advance recovery, tax configuration, correction policy and authority limits | Commercial Lead + Finance Lead | Definition exit |
| Release authority | Separate engineering readiness, business acceptance and final go-live authorization | GM | Before pilot deployment |

**Immediate request (updated 12 October 2026):** nominate the UAT preparation and business reviewers and complete the owner's existing-feature acceptance plan. Hold certificate/new-feature implementation until the acceptance gate passes and the owner approves the next scope. The definition/build estimates below are retained as later planning proposals; this report does not authorize implementation or deployment.

## 2. What this review established

### Evidence basis

The local checkout reviewed was `apps/construction`, branch `develop`, commit `c9e6803c5ac63073aeb0b166c779844d29051d8d`. The report directory was untracked at startup. Source/schema checks passed: **21 schema-owning DocTypes plus one override-only directory; 11 context checks passed, zero failed.** These checks compare repository files, not installed site metadata.

The October 6 [release-candidate summary](../../CUSTOMER_RELEASE_CANDIDATE_SUMMARY.md) identifies an earlier candidate, `4c236bd`. The [release ledger](../customer-release-gap-fixes/STATUS.md) combines later closure notes with older remaining requirements. Its reported results are useful evidence but must be bound to the selected deployment candidate before release. This review does not reopen every closed gate or count an old pass as a fresh test.

### Capability assessment

| Area | Evidence found | Management implication |
|---|---|---|
| BOQ/WBS and commercial revisions | Source schemas and documented pricing/revision rules exist | Reuse the model; preserve approved history and factor semantics |
| Stage measurement | Measured and certified quantities exist; controller restricts certification and protects certified fields | A useful input, but insufficient by itself for period billing and allocation history |
| Transaction attribution | Validation hooks cover eight ERPNext document types, including Journal Entry | Attribution supports integration; it does not prove complete cost reporting |
| Progress billing | `is_progress_billing` is installed on Sales Invoice Item | A flag and BOQ links are not a certificate-to-invoice workflow |
| Payment Certificates | No dedicated schema in the inspected DocType inventory | New commercial transaction capability is required |
| Subcontracting and Site Diary | No dedicated schemas in the inspected inventory | Treat as later product increments, not completed capabilities |
| PlantResource and CostItem | Source schemas exist | Database installation and business usability were not checked; “not migrated” is unproven here |
| CI | Current workflow defines a seven-module smoke subset and a 17-module full suite | Do not add overlapping subsets and report 24 unique modules |
| Historical qualification | Ledger records 234 Python tests and 35 JS cases for private CI Run 11; later summary records further bilingual/UAT work | Preserve candidate, environment and scope with each result |
| UI, scope and localization | Established infrastructure and historical evidence exist | Extend native forms/VFC; qualify new screens, reports and private attachments with ordinary users |

The eight transaction hooks are Purchase Order, Purchase Receipt, Purchase Invoice, Stock Entry, Timesheet, Journal Entry, Sales Invoice and Material Request. Their scope/mandatory-field conditions still need integration testing for the proposed workflow.

### Corrections to the original report

| Original statement or design | Revised engineering position |
|---|---|
| “Stable, production-ready” across the platform | Distinguish source maturity, historical qualification and deployment approval |
| All competitors support every listed capability; certificates have the highest proven ROI | Treat the internal market review as directional input. Remove unsupported competitor checkmarks and demand rankings; validate with pilot users |
| FIDIC rule enforcement or clause references establish compliance | Code naming does not establish compliance. Use the signed contract, its edition/amendments and qualified commercial review |
| Stage certification is “all-or-nothing” | Partial numeric quantities exist, but positive certification freezes protected fields; there is no durable period-allocation model |
| One stage link per certificate item | One item may consume multiple stages; retain explicit source allocation rows |
| Previous totals can come from the last certificate alone | Use the full effective certificate history, including opening balances and linked corrections |
| Cumulative quantity multiplied by the latest rate determines current value | Preserve previously approved amounts; value new quantities using their applicable rate/factor snapshot |
| Subcontractor billing is a supplier switch | It requires separate subcontract terms, quantities, rates, liabilities and entitlement controls |
| Retention and advances are negative service items | Select and prove the accounting treatment before implementation; avoid unintentionally reducing revenue or tax |
| All existing stages can start with zero previously billed quantity | Reconcile historical billing before cutover; zero is safe only where evidence proves nothing was billed |
| Earned value equals quantity × selling rate | That is a commercial valuation. Earned value uses the approved budget basis for completed work |
| Four weeks is enough for both billing directions | Replace the fixed promise with an explicitly resourced, gated estimate |

## 3. Priority and product scope

The priority order below is engineering judgment based on workflow dependencies, not a quantified market study.

| Priority | Deliverable | Business outcome | Prerequisite |
|---|---|---|---|
| P0 | Candidate/evidence reconciliation and contract/accounting definition | Avoid building on uncertain rules or promising unsupported readiness | Named owners and pilot |
| P1 | Customer certificates, measurement allocations and invoice reconciliation | Complete a billable workflow with an auditable history | P0 acceptance |
| P1 | Retention register, advance register, basic release/correction handling | Keep balances explainable throughout the pilot | Finance-approved policy |
| P2 | Committed/actual cost report and forecast to completion | Give management reliable cost exposure | Cost recognition and attribution rules |
| P2 | Subcontract agreement and subcontractor certificates | Control subcontract liabilities and payment entitlement | Customer pilot learning plus separate subcontract definition |
| P3 | Site Diary and mobile evidence capture | Improve timeliness of site inputs | Agreed measurement process |
| P3 | Plant lifecycle, procurement planning and richer dashboards | Expand operational depth where customers need it | Proven demand and reliable transactional data |

### Customer certificate pilot boundary

**Included:** approved contract terms; locked BOQ and approved revisions; measured-work items; period evidence; partial stage allocation; internal verification/approval; customer certification reference; retention cap and register; advance recovery against evidenced receipts; bilingual print; draft Sales Invoice generation; finance submission; partial collection visibility; supported correction/reversal; reconciled legacy opening balances where applicable.

**Deferred:** subcontractor invoices; full subcontract administration; foreign-exchange valuation; multiple companies in one certificate; automatic statutory e-invoice submission; escalation/indexation; materials-on-site billing; daywork/provisional-sum valuation; automated final accounts; advanced EVM; Site Diary and plant operations. Unsupported item types or contractual mechanisms must be blocked or explicitly excluded from the pilot contract scope.

Retention release still needs a supported basic finance-controlled process in the pilot, even if automated milestone release is deferred. Otherwise the feature would create balances without a documented way to close them.

## 4. Proposed end-to-end operating process

| Step | Responsible role | Output and control |
|---|---|---|
| 1. Establish contract basis | Commercial Lead + Finance | Approved customer/company/project/BOQ association, currency, contract reference, terms version and opening balances |
| 2. Capture measurement | Site Engineer / Surveyor | Quantities with work date or period, stage, author, private evidence and revision reason |
| 3. Verify entitlement | QS / Commercial Engineer | Accepted, withheld and disputed quantities separated; measurement is not automatically billable |
| 4. Prepare certificate | Certificate preparer | Current-period claim plus full prior/cumulative history and explicit source allocations |
| 5. Verify and approve | Independent verifier + authorized approver | Actor/time/reason evidence; server validation; amounts and commercial snapshots frozen |
| 6. Record customer outcome | Commercial Lead | Customer-certified reference/date/file; discrepancy returns the claim for controlled correction |
| 7. Generate invoice | Authorized finance user | Exactly one active invoice mapping for the approved billing operation; creates a draft |
| 8. Review and post | Finance | Tax, accounts, payment terms and balances checked before native ERPNext submission |
| 9. Collect and reconcile | Accounts Receivable | Payments allocated; billed, due, collected, retained and outstanding values shown separately |
| 10. Correct or close | Commercial Lead + Finance | Linked adjustments/credit notes, retention release and advance closure; original approvals retained |

For the proposed pilot, billing requires customer-certified evidence. If the selected contract permits another trigger, Commercial and Finance must document it at the definition gate. Internal approval and customer acceptance must remain distinguishable.

The certificate itself is a commercial approval record. Proposed v1 creates no General Ledger entry merely because a certificate is approved. Finance must confirm whether a separate unbilled-revenue process is needed for the selected contract; it is not implied by certificate approval.

## 5. Engineering design and data ownership

### 5.1 Contract terms and certificate identity

Introduce an approved, versioned contract-terms record linked to BOQ Header and ERPNext Customer/Project/Company. Confirm during definition whether an existing contract object can be extended; avoid duplicating an authoritative contract master. Current BOQ Header source has no customer or contract-currency fields, so those cannot be assumed to be available already.

Terms must contain contract reference, effective dates, currency, baseline BOQ/revision, retention rate/base/cap, release conditions, actual advance references, recovery base/threshold/rate, payment terms, tax configuration references, approval limits and billing trigger. Global settings may supply draft defaults; approved contract terms control the transaction.

Scope certificate numbering and cumulative history to **company + contract + customer + currency + certificate series**, with BOQ references validated inside that contract. Project plus party alone is insufficient when the same customer has multiple contracts on one project. Persist a unique certificate identity; cancelled numbers remain traceable.

### 5.2 Proposed records

These are design requirements, not existing DocTypes or a final migration specification.

| Record | Required information |
|---|---|
| Contract Terms / version | Parties, scope, commercial rules, currency, baseline and approval evidence |
| Payment Certificate | Identity, period, type, terms version, predecessor for navigation, totals, approval trail and customer evidence |
| Payment Certificate Item | BOQ item/structure, UOM, quantity basis, rate/factor/revision snapshots, previous/current/cumulative quantities and amounts |
| Certificate Source Allocation | Certificate line, source stage/measurement, eligible quantity, allocated quantity and reversal provenance |
| Deduction / Release detail | Type, amount, basis, agreement/evidence reference, authority and linked finance document |
| Invoice mapping | Certificate operation identity, invoice/replacement links, allocation and posting status |
| Opening-balance record | Cutover date, certified/billed quantities and values, retention, advances, invoice references and reconciliation approval |

Use a source allocation child table or focused ledger with database constraints and parent locks; choose the smallest design that protects partial consumption and audit history. Existing certified stage records remain unchanged. New period quantities must not be implemented by overwriting immutable stage history.

### 5.3 Measurement selection and history

1. Select eligible evidence by contract, BOQ, period cutoff and accepted status. The current stage schema lacks measurement dates, so add explicit period evidence rather than interpreting creation/modification timestamps as work dates.
2. Validate the entire project → BOQ → structure → item → stage chain server-side. `BOQ Item.structure` is the actual source field; `cost_item` is free text, not an ERPNext Item link.
3. Calculate available quantity from accepted source quantity less effective approved allocations and reconciled opening consumption. Define treatment of late measurements through a referenced later-period adjustment.
4. Drafts may preview the same availability. Final approval must recalculate under lock and fail cleanly if another approval consumed it.
5. An item with no current-period movement must still appear in cumulative reporting or be included in a reconciled carried-forward summary. Summing only changed rows understates the contract total.
6. Avoid double inclusion when one physical measurement is represented in multiple stages. Source uniqueness and measurement ownership must be defined with the QS.

### 5.4 Document lifecycle and authority

| Business state | Proposed Frappe `docstatus` | Commercial edits |
|---|---:|---|
| Draft | 0 | Authorized preparer may edit |
| Under Review | 0 | Controlled review; return to Draft for changes |
| Verified | 0 | Locked for preparer; material change resets verification |
| Approved | 1 | Submit once; commercial content immutable |
| Cancelled | 2 | Only after permitted dependency checks and recorded authorization |

Keep billing status separate: Not Invoiced, Draft Invoice, Posted Invoice, Partly Settled and Settled are derived from effective linked finance documents. “Invoiced” must not mean merely that a draft exists. External certification evidence also has its own status.

Recommended segregation: preparer, verifier and final approver are distinct for the pilot; Finance controls invoice posting. Map these business responsibilities to actual installed role names during definition. Source stage certification currently recognizes `Project Manager`, `Construction Owner` and `System Manager`; do not invent a working `Projects Manager` mapping.

If staffing makes full segregation impossible, management must approve a specific documented exception with compensating review and audit evidence. A general checkbox disabling financial controls is not the recommended default. Administrative recovery actions remain auditable.

### 5.5 Retries, concurrency and corrections

Use a contract-level serialization protocol coordinated with existing BOQ transaction locks. Acquire locks in a deterministic order, then read authoritative allocations/balances and approve atomically. Certificate numbering uniqueness alone cannot prevent two different certificates consuming the same stage.

Persist an operation key for invoice generation with a uniqueness constraint. A retry with identical input returns the existing result; conflicting reuse is rejected. Verify rollback after failure between allocation, certificate submission and invoice linking. Do not bypass document lifecycle with direct status writes.

An invoice cancellation must not silently release certified quantities. A certificate cancellation requires dependency checks against invoices, collections, retention releases, advance allocations and later certificates. Reverse dependent records in a supported order, or issue a linked adjustment/credit note in an open period. Never recalculate a previously approved certificate in place. Negative adjustments require explicit reason and approval; they are not ordinary negative progress lines.

## 6. Commercial calculations and accounting acceptance

### 6.1 Quantity, rates and factors

The existing approved financial contract states that BOQ factor is positive and affects physical quantities and values. Certificate design must preserve it. The QS must confirm whether each imported measurement is recorded in nominal BOQ quantity or already-expanded physical quantity, so factor is applied exactly once.

For a **nominal BOQ quantity** source, the proposed valuation is:

```text
Current work value = sum(current nominal quantity × approved factor × applicable unit rate)
Cumulative quantity = opening quantity + prior effective quantities + current quantity
Cumulative work value = opening value + prior effective amounts + current work value
```

For an already-expanded measurement, normalize to the approved basis first; do not multiply it by factor twice. Snapshot the applicable quantity ceiling, factor, UOM, rate and approved revision. Missing revised quantity is different from a legitimate revised quantity of zero.

If a new rate applies prospectively, apply it to eligible new work only. A retroactive price adjustment must be a separately approved amount with its own basis. Never compute the new period amount by repricing all historical quantity at today's rate.

### 6.2 Retention and advance recovery

For an ordinary positive-progress certificate, subject to approved contract terms:

```text
Remaining retention cap = max(0, approved cap − effective retention withheld to date)
Current retention = min(eligible retention base × rate, remaining retention cap)
Retention held = opening held + withholdings − releases ± approved corrections

Unrecovered advance = evidenced receipts allocated to this contract − effective recoveries
Current recovery = min(eligible recovery base × recovery rate, unrecovered advance)
```

Retention withheld to date and retention still held are separate values. Releasing retention must not automatically reopen the original cap. Any replenishment rule requires explicit contract terms. Recovery thresholds, tax effects, cap changes, rounding and correction behavior require finance-approved examples.

Track advances from actual posted receipts/allocations, not a manually entered contractual maximum. Prevent one receipt being recovered in multiple contracts. Track certified/planned recovery separately from posted recovery so an unposted certificate cannot leave the next certificate unaware of a reserved amount.

### 6.3 Invoice and tax treatment

ERPNext Sales Invoice submission records accounting entries; it supports tax configuration, payment schedules and advance allocation. These capabilities are integration building blocks, not proof of the proposed construction treatment. See [ERPNext Sales Invoice documentation](https://docs.frappe.io/erpnext/sales-invoice).

**Remove the original universal formula that calculates tax after retention and advance deductions.** The taxable base depends on the approved jurisdiction/contract treatment. Use reviewed ERPNext tax configuration and reconcile invoice calculations with the certificate. Tender tax allowance is a pricing input and must not be substituted for invoice tax.

Likewise, do not default to negative service-item lines for retention and recovery. Finance must choose and test an account/payment-term/allocation treatment that preserves the approved work value, receivable, advance liability and retention balance. No account number should be hardcoded across companies. A fixture containing account `1220` does not establish correct classification or posting behavior.

| Event | Required acceptance evidence |
|---|---|
| Certificate approval | Frozen quantities/values; no unintended GL posting |
| Draft invoice generation | Correct customer/company/currency/UOM, service-item mapping, BOQ dimensions, tax and payment terms |
| Invoice posting | Debits equal credits; finance-approved revenue, tax, receivable, retention and advance treatment |
| Advance allocation | Consumes the approved receipt balance once; certificate register reconciles to finance records |
| Partial collection | Payment allocation and remaining due match the ledger; retained balance remains separately visible |
| Retention release | Changes the appropriate balance/due classification once with approval; does not duplicate work revenue |
| Cancellation / credit note | Reverses the intended amounts and links; closed periods and later dependencies remain protected |

Country connectors, tax rates, statutory clauses and broad FIDIC compliance are outside the verified findings of this review. Select the pilot jurisdiction and obtain its current finance/commercial requirements before implementation.

### 6.4 Worked acceptance examples

These are illustrative, non-statutory examples for Commercial and Finance to review independently. They are proposed acceptance cases, not executed software tests. Amounts use a single currency with two decimal places; tax is deliberately excluded.

| Case | Inputs | Expected outcome |
|---|---|---|
| Basic progress | 100 nominal units × factor 0.5 × rate 200; retention 5%, cap available 2,000; recovery 10%, unrecovered advance 800 | Work 10,000; retention 500; recovery capped at 800; current amount before tax/other adjustments 8,700 |
| Retention cap | Work 10,000; rate 5%; only 200 of cap remains | Retention 200; total withholding does not exceed cap |
| Exhausted advance | Same work; unrecovered advance 0 | Recovery 0 |
| Prospective rate change | Prior 100 units × 200 = 20,000; current 10 units × 220 = 2,200; factor 1 | Cumulative value 22,200, not 24,200 |
| Multiple stages | One item has accepted stage quantities 30 and 20; prior effective allocations total 40 | At most 10 remains available, with stage-level provenance |
| No movement | An item has prior value 20,000 and zero current quantity | Current value 0; cumulative report still includes 20,000 |
| Retry | Invoice generation called twice with the same operation key | One active invoice result, no duplicate commercial effect |
| Concurrent approval | Two requests each try to consume the last 10 units | At most 10 units allocated across successful approvals |
| Partial receipt | Current due is 8,700; linked collection is 5,000 | Remaining current due 3,700; retention shown separately |
| Legacy cutover | Evidence shows 40 units already billed from 50 certified | Only 10 units eligible after opening reconciliation, not 50 |

Add independent fixtures for rounding, zero revised quantities, revised rates/factors, rejected evidence, tax, negative adjustments, cancelled invoices and retention release before definition exits.

## 7. Cost visibility and reporting enhancement

Do not simply add Purchase Invoice, Stock Entry, Timesheet and Journal Entry totals. The same economic cost may pass through more than one document. Define a recognition source and reversal treatment for each cost stream, then reconcile the financial view to ERPNext.

| Measure | Proposed meaning | Required control |
|---|---|---|
| Budget | Approved direct-cost baseline by BOQ/WBS, with separate authorized changes | Preserve original and current approved baselines |
| Open commitment | Remaining approved procurement/subcontract exposure not yet recognized in the selected actual-cost basis | Handle partial fulfillment, closing, returns, tax and currency consistently |
| Actual financial cost | Recognized cost from the agreed accounting sources, with source drill-down | Reconcile to GL; do not count receipt, invoice and stock consumption as three costs |
| Operational labor/equipment cost | Approved operational quantities valued at approved cost rates | Keep separate until reconciled to payroll/GL; label unposted accruals |
| Estimate to complete (ETC) | Forecast remaining cost based on remaining work, revised rates, productivity and risks | Owner, date, assumptions and confidence recorded |
| Estimate at completion | Actual cost + ETC | Do not add commitments again if already included in ETC |
| Forecast margin | Approved forecast contract value − EAC | Show pending variations separately from approved entitlement |
| Certified value | Commercial value of approved certificate work | Separate from posted revenue, invoices and cash |
| Earned value | Approved budget value of completed work | Requires an agreed progress method and baseline |

Earned value is budget-based, whereas a selling-rate valuation measures commercial value. The [US Department of Energy EVM explanation](https://www.energy.gov/em/earned-value-management) supports that distinction. Defer CPI/SPI claims until cost, schedule and progress baselines are comparable.

Initial management reports should show: contract and approved variations; certified but unbilled; billed and collected; overdue receivables; retention held/released; advance received/recovered/outstanding; and exceptions requiring action. Cost dashboards follow only after reconciliation is reliable.

## 8. Security, migration and operating readiness

| Area | Required delivery behavior |
|---|---|
| Permissions | Test allowed and denied preparer/verifier/approver/accountant users across forms, REST, reports, exports and files |
| Scope | Enforce authoritative company/project/contract relationships and the agreed selected-scope behavior; avoid permission-bypassing reads |
| Evidence files | Private files with ownership/access checks, bounded uploads and safe print rendering |
| Approval history | Authenticated actor/time stamps; changes reset approvals; submitted commercial data immutable |
| Migration | Dry-run inventory and exception report; preserve existing stages; approved opening balances; repeated migration leaves values unchanged |
| Legacy billing | Reconcile quantities and money separately to historical certificates/invoices; quarantine ambiguous records from automatic billing |
| Recovery | Backup, restore rehearsal and documented schema/data recovery; code rollback alone is insufficient |
| Performance | Agree pilot line/stage/file/concurrency limits; benchmark real user paths and approval contention on the chosen stack |
| Observability | Log operation identity and actionable errors; monitor failed invoice links, stale drafts and reconciliation exceptions |
| Deployment | Named site, exact versions/candidate, release evidence, access owners and go-live authorization |

No migration, account repair, customer data modification or deployment was performed during this report review.

## 9. Delivery acceptance and release gates

| Gate | Required evidence | Accountable owner |
|---|---|---|
| D0 — Definition accepted | Pilot contract, workflow, data model, posting examples, scope limits, role matrix, opening policy and revised estimate | Head of Engineering + Commercial + Finance |
| D1 — Commercial core | Source allocation, immutable approval, period/rate/factor examples, negative cases and concurrent requests verified | Engineering Lead + QA |
| D2 — Finance integration | Draft/post/cancel/credit/partial-payment/release paths reconcile; retry and injected-failure checks pass | Finance Lead + Engineering |
| D3 — User and migration acceptance | Ordinary-user permissions, bilingual prints, UAT, opening balances, upgrade replay and recovery rehearsal | QA + Pilot Operations |
| D4 — Pilot go-live | Candidate-bound evidence, approved unresolved-risk disposition, trained users, support owner and rollback criteria | GM with Engineering/Finance recommendation |
| D5 — Expansion | Two reconciled certificate cycles and agreed KPI evidence | GM + Commercial + Engineering |

Release blockers include duplicate billing, unexplained monetary differences, unauthorized access/approval, missing historical-billing reconciliation, unsupported accounting treatment and inability to recover the pilot data. Scope can be reduced to remove an unsupported scenario; a financial-integrity defect should not be relabeled as an accepted cosmetic issue.

Verification must include real document persistence and reload, normal REST/import routes, two genuinely overlapping database connections, and browser/Arabic-print checks where applicable. Unit tests alone cannot establish the complete workflow. Reuse relevant existing BOQ regression suites and preserve the financial rules already agreed by the owner.

## 10. Delivery plan, staffing and investment control

### Recommended capacity scenario

For planning only, assume two engineering contributors, a QA contributor at approximately half capacity, and scheduled QS/Finance availability. These are requested allocations, not an assertion that the current team has this staffing. The repository identifies a solo owner/developer; if that remains the available capacity, use the second scenario below.

| Phase | Indicative elapsed window | Deliverable | Exit condition |
|---|---|---|---|
| Definition and evidence reconciliation | Weeks 1–2 | Accepted contract/accounting pack, pilot examples, candidate evidence and build estimate | D0 |
| Certificate and measurement core | Weeks 3–5 | Terms, source allocation, valuation, workflow and audit controls | D1 |
| Finance and reporting | Weeks 6–8 | Invoice integration, registers, bilingual print, reconciliation and basic correction/release | D2 |
| Qualification and pilot preparation | Weeks 9–10 | UAT, migration/recovery rehearsal, training and readiness decision | D3–D4 |
| Observed pilot | Two actual certificate cycles | Operational evidence, defects and measured benefit | D5 |

**Planning range:** approximately **8–12 engineering person-weeks**, plus **3–4 QA person-weeks**, **1–2 QS person-weeks** and **1–2 Finance person-weeks**, spread across an indicative 10-week preparation period. The range is a decomposition-based estimate, not a quotation. Integration discovery or contract complexity can increase it; re-estimate at D0.

With **one implementation engineer**, allow roughly **12–16 calendar weeks before pilot**, provided QA and business reviewers remain available. If the owner must also perform all QA and business review, schedule further time. AI assistance supports implementation and review but does not replace accountable finance approval or independent acceptance.

Pilot observation is additional elapsed time and follows the actual billing cadence. Two monthly cycles cannot be represented as two weeks of testing.

### Budget method

Finance should apply loaded weekly rates to the role ranges above, then add test infrastructure, independent commercial/technical review, training/support and a proposed 20% contingency. No currency amount is quoted because rates and allocations have not been supplied. Release contingency against documented risks; do not hide new scope inside it.

Commit spending in increments: definition first, core/integration after D0, and deployment after D3/D4. Cost reporting and subcontracting receive separate estimates after pilot evidence. They are not promised within the customer-certificate timetable.

### First ten working days after kickoff

| Action | Owner | Reviewable output |
|---|---|---|
| Name pilot, project sponsor and available team | GM | Assignment and capacity sheet |
| Collect contract, two certificate examples, invoices and payment/advance/retention evidence | QS + Finance | Redacted acceptance dataset and exception list |
| Reconcile candidate, versions and relevant historical release evidence | Engineering | Short evidence matrix with any additional checks required |
| Demonstrate current measurement workflow and agree quantity/factor basis | QS + Engineering | Approved measurement scenarios |
| Define tax/accounts/advance/retention/correction treatment | Finance | Balanced posting examples and reconciliation rules |
| Review native UI/print prototype and role matrix | Engineering + Operations | Approved workflow and bilingual terminology |
| Break implementation into bounded work packages | Engineering + QA | Estimates, dependencies, acceptance tests and release checklist |
| Hold D0 review | Engineering + Commercial + Finance | Proceed/revise decision and proposed pilot date |

## 11. Ownership, risks and success measures

### Accountability

The GM owns investment, scope tradeoffs and go-live authorization. The Head of Engineering owns architecture, estimates, technical evidence and release recommendation. The Commercial/QS Lead owns measurement entitlement and contract interpretation. Finance owns accounts, taxes, balance reconciliation and posting acceptance. QA owns test execution and defect evidence. Pilot Operations owns user availability, training and operational acceptance. Assign people to these roles at kickoff; role names alone are not staffing.

### Risk register

| Risk | Likelihood / impact | Mitigation and owner |
|---|---|---|
| Unclear contract/tax policy causes rework | High / High | D0 signed examples; Finance + Commercial |
| Duplicate allocation or invoice under retries/concurrency | Medium / Critical | Locking, uniqueness, idempotency and real concurrent/failure tests; Engineering |
| Historical quantities billed again | Medium / Critical | Opening reconciliation and exclusion of ambiguous history; QS + Finance |
| Incorrect rate/factor application | Medium / High | Explicit units, immutable snapshots and independent examples; QS + Engineering |
| Retention/advance balances do not reconcile | Medium / High | Separate registers, caps, receipts and posting reconciliation; Finance |
| Scope grows to include subcontracting and country connectors | High / High | Written pilot boundary and separate estimates; Engineering + GM |
| Reviewer availability delays delivery | High / Medium | Reserved weekly review slots and escalation; GM |
| Old release evidence is attributed to new code | Medium / High | Candidate/version binding and targeted requalification; Engineering + QA |
| Site users continue parallel spreadsheets | Medium / Medium | Historical replay, training and two-cycle adoption review; Operations |

### Proposed pilot scorecard

Targets below are proposals to agree at D0. Baselines are currently unknown.

| Indicator | Proposed acceptance / target | How measured |
|---|---|---|
| Quantity and monetary integrity | Zero duplicate allocations/invoices and zero unexplained reconciliation differences | Automated reconciliation plus Finance review each cycle |
| Evidence completeness | 100% of approved lines traceable to accepted measurement or approved opening/correction evidence | Certificate drill-down audit |
| Preparation effort | At least 30% less staff time than the agreed historical baseline | Timed comparable certificates; exclude customer waiting time |
| First-pass quality | At least 90% accepted internally without arithmetic/source-evidence rework | Workflow reasons and review log |
| Adoption | All in-scope pilot certificates processed through the approved workflow | Compare project certificate register to system records |
| Pilot stability | Two reconciled cycles with no unresolved critical/high financial or access defect | Defect register and D5 review |
| Billing delay | Track internal approval-to-invoice time against baseline | Timestamp report; keep customer approval delay separate |

Treat reduced days-to-cash as a monitored business outcome, not a guaranteed release result. After D5, prioritize either cost visibility or subcontracting using actual pilot demand, available capacity and the remaining reconciliation gaps.

## 12. Engineering handover backlog

| ID | Work package | Acceptance outcome | Dependency |
|---|---|---|---|
| PC-01 | Contract terms and opening balances | Approved versioned basis; no guessed historical consumption | D0 |
| PC-02 | Measurement period/evidence and source allocations | Partial allocations traceable across multiple stages and certificates | PC-01 |
| PC-03 | Certificate valuation and lifecycle | Factor/rate/history rules, immutability and independent approvals verified | PC-01–02 |
| PC-04 | Retention and advance registers | Cap, recovery, release and correction balances reconcile | PC-01, PC-03 |
| PC-05 | Invoice integration and settlement visibility | Draft/post/cancel/retry/partial-payment paths preserve ledger correctness | PC-03–04 |
| PC-06 | Reports, bilingual print and VFC | Clear previous/current/cumulative presentation; ordinary-user access enforced | PC-03–05 |
| PC-07 | Qualification, migration and pilot | D3/D4 evidence and trained support/operations | PC-01–06 |
| COST-01 | Cost recognition and commitment design | No double counting; Finance-approved actual/commitment definitions | Separate definition after pilot priorities reviewed |
| SUB-01 | Subcontract domain definition | Separate supplier agreement, rate schedule, quantities, deductions and entitlement | Customer pilot learning |
| MAINT-01 | MCP BOQ-header item retrieval | Query separate BOQ Items with bounded, permission-aware access | Independent maintenance slot |

For MAINT-01, source inspection confirms `tool_get_boq_header` attempts to read `doc.get("items", [])` even though BOQ Item is a separate DocType. This is a schema mismatch. The exact runtime outcome was not reproduced; do not state that a specific exception always occurs. Correct data retrieval must also preserve permissions, scope and response limits.

## Appendix A. Evidence and review limitations

### Principal local sources

- [Original analysis](construction_platform_analysis_report.md): all 787 lines reviewed; source of the requested revision.
- [Schema facts](../../SCHEMA_FACTS.md) and actual BOQ Header/Item/Item Stage JSON: field names and source schema ownership.
- [Release summary](../../CUSTOMER_RELEASE_CANDIDATE_SUMMARY.md), [release ledger](../customer-release-gap-fixes/STATUS.md) and [dated release gaps](../../CUSTOMER_RELEASE_GAPS_2026-10-04.md): historical qualification and remaining/evolving evidence context.
- [Financial rules](../customer-release-gap-fixes/FINANCIAL_RULES.md): factor, pricing and permanent approval history.
- [Internal market review](../../../feature_reviews/07_egypt_gulf_enterprise_roi_review.md): directional product hypotheses; contains dated implementation statements and is not a current verified competitor scorecard.
- [Stage controller](../../../../construction/construction/doctype/boq_item_stage/boq_item_stage.py), [operational validation](../../../../construction/services/boq_operational.py), [transaction hooks](../../../../construction/hooks.py), [transaction validator](../../../../construction/services/boq_transaction_validation.py), [installation fields](../../../../construction/install.py), [CI workflow](../../../../.github/workflows/ci.yml) and [MCP server](../../../../erpnext-mcp-server/server.py): selected source checks supporting corrections.

### Review execution record

| Check | Result | Limit |
|---|---|---|
| Repository/branch/HEAD/status inspection | `develop`, `c9e6803c5ac63073aeb0b166c779844d29051d8d`; original report directory untracked | Local baseline only; no remote freshness assertion |
| `python3 scripts/schema_drift_checker.py` | Exit 0; 21 schema owners, one override-only directory | Repository JSON comparison, not deployed DB |
| `python3 scripts/ai_context_check.py` | Exit 0; 11 passed, zero failed | Context consistency, not business acceptance |
| Selected source and historical-evidence review | Completed for findings above | Static review; no newly executed business suite |
| Markdown validation | All local links resolve; table column counts and code fences are consistent | Content/structure checks, not application tests |
| Primary public references | ERPNext Sales Invoice and DOE EVM pages consulted on 8 October 2026 | Supports general concepts; no country tax/contract certification |

Repository instructions/context read: `AGENTS.md`, `docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md`, `docs/ai/CONTEXT_INDEX.md`, `AGENT_WORKFLOW.md`, relevant schema facts, `SESSION_MEMORY.md` current work sections, and root `STATUS.md`. The original report's `docs/CUSTOMER_RELEASE_GAPS_2026-10-04.md` reference was incorrect; the actual report is under `docs/ai/` as linked above.

No independent human technical review, customer acceptance, current production audit, competitor verification, legal opinion or quantified ROI study is claimed. The deliverable is a management-ready engineering recommendation and a proposed delivery contract for the next phase.

## Appendix B. Working terminology

| English | Arabic | Meaning in this report |
|---|---|---|
| Customer Payment Certificate | مستخلص المالك | Commercial certificate for work payable by the customer |
| Subcontractor Payment Certificate | مستخلص مقاول الباطن | Separate supplier-side commercial entitlement |
| Measured quantity | الكمية المقاسة للأعمال المنفذة | Evidenced work measured on site |
| Certified quantity | الكمية المعتمدة | Quantity accepted under the approval process |
| Current-period quantity | كمية الفترة الحالية | Quantity allocated to this certificate period |
| Retention | محتجزات الضمان | Amount retained under approved contract terms |
| Advance recovery | استرداد الدفعة المقدمة | Recovery allocated against evidenced advance balances |
| Certified but unbilled | أعمال معتمدة لم تُفوتر | Approved commercial value without a posted invoice |
| Cost to complete | التكلفة المتوقعة لاستكمال الأعمال | Forecast remaining cost, with dated assumptions |

Business users should approve final Arabic terminology and printed certificate wording during UAT.
