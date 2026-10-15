# Construction ERP — Egypt and MENA Product Benchmark

**Audience:** General Manager, Engineering, Commercial and Finance  
**Date:** 8 October 2026  
**Version:** 1.0  
**Target confirmed by the owner:** Egyptian small and mid-sized contractors first, followed by Gulf expansion  
**Classification:** Confidential — internal product strategy  
**Companion:** [Engineering review and delivery recommendation](construction_platform_engineering_review_for_gm.md)

**12 October follow-up:** [External AI report reconciliation](consultant_review_line_by_line_reconciliation_2026-10-12.md) distinguishes already-implemented controls from residual customer qualification and reconciles the proposed roadmap with this Egypt-first benchmark. The vendor evidence below remains dated 8 October; it was not freshly revalidated for the follow-up.

## 1. Executive decision

**Our strongest current asset is the BOQ and commercial-control foundation. Our largest competitive gap is turning that foundation into complete daily workflows for billing, subcontractors, cost control and site operations.** The next product investment should make those workflows usable by an Egyptian contractor's QS, accountant, buyer and site engineer with minimal repeated entry.

The recommended direction is:

1. Deliver the customer measurement-to-certificate-to-invoice workflow, including retention, advances, corrections and traceable balances.
2. Treat Egyptian e-invoice integration or a proven integration partner as an explicit requirement for the intended customer deployment. Discover and qualify this alongside billing design.
3. Connect existing ERPNext procurement, stock, accounting and budget capabilities to BOQ work packages; add a reconciled project cost view.
4. Deliver subcontract agreements, measurement, certificates and payment controls using a separate supplier-side commercial model.
5. Improve site productivity with simple mobile evidence capture and material requests, then expand to daily reports, labor/equipment productivity and document control.

These priorities reflect engineering judgment informed by public product evidence. They are not a market-share ranking, proof of customer willingness to pay, or a claim that competitor software has been independently tested.

**Positioning proposal:** “An Arabic-first construction commercial-control system on ERPNext, connecting quantities, procurement, certificates and accounts for growing contractors.” Arabic support alone is not a defensible advantage; the advantage must be a shorter, demonstrably reliable workflow and a practical implementation/support service.

## 2. How the comparison is made

The benchmark includes five regional offerings and three global product families. Regional products are more directly relevant to the first customer segment; global suites provide benchmarks for control, reporting and integration. “Major” here means selected relevant comparators, not verified regional revenue or installed-base leadership.

### Evidence rules

| Mark | Meaning |
|---|---|
| A | Explicitly advertised on the cited vendor page; not independently demonstrated |
| D | Described in official product documentation; applicability depends on edition, deployment and configuration |
| ? | Not established in the reviewed source; does not mean the vendor lacks the feature |
| Source present | Our repository contains the relevant implementation; current production behavior is not certified by this review |
| Partial | Useful elements exist, but the construction workflow is incomplete or unqualified |
| ERPNext base | General capability exists in the local ERPNext source; app integration and customer configuration need qualification |
| Gap | No dedicated end-to-end capability was established in the reviewed construction app |

Vendor claims and our source evidence are deliberately different evidence classes. Neither an advertised checkbox nor a source file proves operational quality, uptime, implementation time, tax compliance or customer benefit. No vendor was contacted, no demo booked and no private repository material shared.

The public sources were consulted on 8 October 2026. Scope is strongest for Egypt, Saudi Arabia and the UAE. Other MENA countries require separate customer and localization research; this report does not treat MENA as one regulatory market.

## 3. Relevant products and what they teach us

| Comparator | Why included | Published capability evidence | Implication for our product |
|---|---|---|---|
| **AccFlex Construction** | Direct Egyptian contractor workflow comparator, also marketed regionally | Owner and subcontractor certificates, preliminary/final approvals, evidence archiving, advance-related deductions, balance corrections and e-invoice synchronization are advertised. [V1](https://accflex.com/en/Accounts-programs/constructions-software) | Certificate preparation must connect to approvals, corrections, accounts and invoice status |
| **NTS construction solution on Odoo** | Egypt/KSA implementation offering; compare the configured solution, not bare Odoo | BOQ-linked scheduling, daily mobile logs, site material requests, cost comparisons, subcontract claims, variations, retention and RFQ automation are advertised. [V2](https://www.ntscompany.net/construction) | Site-to-office handoffs and implementation quality matter alongside financial features |
| **FALCON ERP Construction** | GCC-oriented contractor comparator | BOQ/rate analysis, cost control, subcontract work orders/payments/retention, site inventory and resource planning are advertised. [V3](https://falconerp.com/construind.html) | Buyers will expect control of purchased/consumed resources and subcontract exposure |
| **FACTS Construction ERP** | UAE/GCC-oriented comparator | BOQ, subcontract payments, retention, equipment, site attendance, mobile access, Arabic/English and multi-entity/currency support are advertised. [V4](https://factserp.ae/products/construction-erp-software/) | Gulf expansion needs integrated operations and validated entity/currency behavior |
| **Horizon EBS / FIT** | Regional construction operations and accounting comparator | Estimation through accounting, subcontract progress billing/retention, procurement, plant, approvals and deployment choices are advertised. [V5](https://www.fit.ae/construction) | Include onboarding, training, support and deployment needs in the product offering |
| **SAP S/4HANA project controls** | Enterprise financial-control reference, rather than first-release scope target | Official documentation covers WBS/project planned versus actual costs and budget/commitment reporting. [V6](https://help.sap.com/docs/SAP_S4HANA_ON-PREMISE/4dd8cb7b1c484b4b93af84d00f60fdb8/1448cfa991784030b1a4a39f425cfd1c.html), [V7](https://help.sap.com/docs/SAP_S4HANA_CLOUD/bd39d476d1e34b48afed98759286efd6/2fe078816bf348f69d114881d04c89e8.html) | Traceability and consistent cost definitions are the standard to learn from |
| **Microsoft Dynamics 365 Project Operations** | Project costing and subcontract-process reference | Official documentation describes subcontract lines, cost actuals/vendor-invoice verification, budgets and forecasting. Deployment-specific limitations apply. [V8](https://learn.microsoft.com/en-us/dynamics365/project-operations/pro/subcontracting/managing-subcontracts-overview), [V9](https://learn.microsoft.com/en-us/dynamics365/project-operations/pro/budget/keyconcepts-projectbudget) | Reconcile operational cost with supplier invoices; do not count the same cost twice |
| **Oracle Primavera Unifier + Aconex** | Enterprise project-control and collaboration reference; separate products | Unifier advertises connected contracts, changes, commitments, cash flow and schedule integration. Aconex provides document/workflow collaboration. [V10](https://www.oracle.com/construction-engineering/primavera-unifier-project-controls-asset-management/), [V11](https://www.oracle.com/middleeast/construction-engineering/aconex/) | Preserve the trail from change/evidence to approval; integrate with specialist systems when customers already use them |

SAP and Oracle publish regional construction material ([SAP MENA](https://www.sap.com/mena/topics/engineering-construction-operations), [Oracle Middle East](https://www.oracle.com/middleeast/construction-engineering/aconex/)). Microsoft is included as a global capability reference; regional penetration was not measured. Oracle's construction applications are not interchangeable with a complete accounting ERP. Likewise, a Project Operations capability is not proof of an Egyptian BOQ certificate module.

CivitBUILD was considered from the previous report, but its website timed out during this review. It is excluded from scored comparisons until its capabilities can be substantiated. The older report's blanket competitor checkmarks should not be reused.

## 4. Regional feature comparison

The five vendor columns refer to V1–V5 above. “?” preserves uncertainty rather than inferring a missing product feature. This is a compact evidence map, not a functionality or quality score.

| Workflow | Our current position | AccFlex V1 | NTS V2 | FALCON V3 | FACTS V4 | Horizon V5 |
|---|---|---|---|---|---|---|
| Work-item estimating / cost planning | Source present: BOQ/WBS and resource cost analysis | A | A | A | A | A |
| Variations linked to commercial baseline | Source present: VO and quantity revisions | ? | A | ? | ? | ? |
| Customer certificates / progress billing | Gap: stage data and invoice attribution only | A | A | ? | ? | ? |
| Subcontract agreement / payment workflow | Gap: supplier transactions are available in base ERP | A | A | A | A | A |
| Explicit retention management | Gap: contract-based register/release not established | ? | A | A | A | A |
| Advance-related contract deductions | Gap: base payments do not define certificate recovery | A | ? | ? | ? | ? |
| Project cost / budget visibility | Partial: estimates and base project data; BOQ actual/commitment view incomplete | A | A | A | A | A |
| Procurement connected to project execution | Partial: ERPNext base plus BOQ transaction links | ? | A | A | A | A |
| Site-mobile progress or requests | Gap: responsive UI is not a dedicated field workflow | ? | A | A | A | ? |
| Labor / plant planning or operational visibility | Partial: rate inputs, base timesheets/assets, limited plant schema | ? | A | A | A | A |
| Approval/evidence workflow | Partial: existing commercial controls; certificates not implemented | A | A | ? | ? | A |
| Country e-invoice connection | Not established as a deployed connector | A | A | ? | ? | A |

For AccFlex, work-insurance/deduction terminology is not treated as proof of a complete retention-release engine; that remains a demo question. For FACTS/FALCON, broad payment or VAT claims do not prove a customer certificate or tax-authority connector. NTS's advertised compliance readiness and Horizon's e-invoicing claim still require technical demonstration. No vendor certification claim is independently endorsed here.

### Enterprise reference comparison

| Control | Documented/advertised benchmark | Our position | Proportionate SME response |
|---|---|---|---|
| Budget, commitments, actuals and drill-down | SAP project budget and cost reports — D, V6/V7 | Attribution exists; full BOQ reconciliation is incomplete | One reliable cost report before elaborate dashboards |
| Operational costs matched to supplier invoices | Dynamics subcontract management — D, V8 | Timesheet and purchasing foundations exist; subcontract matching missing | Separate accrual/operational view from posted cost and reconcile |
| Forecast and budget versions | Dynamics budget concepts — D, V9 | Estimated BOQ costs exist; forecast-to-complete workflow not established | Dated forecasts with owner, assumptions and variance explanation |
| Contract/change/cash-flow alignment | Unifier — A, V10 | VO foundation exists; certificate and cash-flow link missing | Connect approved variation to billing entitlement and due-date forecast |
| Controlled document review | Aconex — A, V11 | Attachments and framework permissions are foundations | Evidence register and overdue approvals first; full CDE integration later |

Do not import enterprise breadth into the first SME release. Use these controls to design data ownership and auditability while keeping daily forms short.

## 5. Our actual product baseline: build versus reuse

The source baseline remains `develop` at `c9e6803c5ac63073aeb0b166c779844d29051d8d`. Both required startup checks passed again: 21 construction schema owners plus one override; 11 context checks passed, zero failed. These are static/local results, not fresh business UAT.

| Capability | Construction app / ERPNext evidence | Assessment and next action |
|---|---|---|
| BOQ, WBS and estimating | BOQ Header/Structure/Item, Cost Analysis, resource price history and cost-report service | Preserve and improve usability; avoid rebuilding the estimating core |
| Contract change control | Variation Order and BOQ Quantity Revision schemas/controllers | Existing source capability; extend its link into certificate entitlement |
| Measurement | BOQ Item Stage has measured/certified quantities and server restrictions | Add period evidence, partial source allocation and correction provenance |
| Financial accounting, invoices and payments | ERPNext foundation plus BOQ links on relevant transactions | Configure and qualify; do not create a second general ledger |
| Procurement | ERPNext RFQ, Supplier Quotation, PO, receipt and invoice foundations | Add BOQ work-package mapping, budget checks and status visibility where missing |
| Inventory/site materials | Stock transactions carry BOQ attribution; ERPNext project stock reporting exists | Connect consumption/returns to quantities and costs; distinguish buying from consumption |
| Budgets | Local ERPNext Budget schema supports project/cost-center selection and control actions | Verify configured controls first; BOQ-level budgets and commitments need mapping |
| Project/task management | Local ERPNext Project/Task fields include dates, costs and dependencies | Reuse basic tasks and milestones; qualify mapping to BOQ/WBS |
| Cost reporting | App reports estimated cost versus contract rate and resource requirements; ERPNext Project contains cost totals | “No cost reporting” is too broad. Missing piece is a reconciled construction cost/commitment/forecast model |
| Subcontracting | Supplier and purchase documents exist, but no dedicated construction agreement/certificate schema | New commercial domain linked to ERPNext purchasing/payables |
| Plant and workforce | PlantResource schema; ERPNext asset foundation and app timesheet attribution | Do not equate a schema to fleet operations; payroll/local labor integration needs separate qualification |
| Arabic and permissions | Bilingual/VFC/theme/scope foundations and historical test evidence | Use as an adoption foundation; test complete Arabic tasks and printed outputs |
| Customer/consultant collaboration | Generic framework primitives; dedicated certificate portal/CDE workflow not established | Start with controlled exports/evidence; add portal or connector on demonstrated demand |
| Country compliance | Generic taxes and invoice records; construction-specific deployed country connection not established | Inventory installed integrations and qualify the actual country/customer route |

ERPNext capabilities are not automatically missing because the custom app lacks matching DocTypes. They also are not automatically delivered merely because source schemas exist. Demonstrate configuration, permissions, data flow and accounting reconciliation on the selected test site.

## 6. Customer requirements to validate

The requirements below are proposed buyer needs inferred from workflow gaps and vendor emphasis. They have not yet been confirmed by interviews with our target customers.

| User | Job they need to finish | Proposed requirement | Acceptance evidence | Priority |
|---|---|---|---|---|
| Owner / GM | Know which projects need intervention | Project margin/exposure, cash due and overdue approvals with drill-down | One review screen reconciled to its transactions | High |
| QS / technical office | Prepare a certificate without rebuilding spreadsheets | Prior/current/cumulative quantities, rates, variations, evidence and deductions | Replay two historical cycles without duplicate entry/billing | Essential |
| Accountant | Turn approved work into collectible, correctly recorded invoices | Approved certificate mapping, tax configuration, advance/retention registers, collection allocation | Certificate, invoice and accounts reconcile | Essential |
| Commercial manager | Control subcontract entitlements | Agreement quantities/rates, measured claims, withheld/disputed amounts and back-charges | Supplier certificate cannot exceed approved entitlement | Essential for subcontract-heavy firms |
| Buyer | Buy the required materials in time | BOQ resource need → material request → RFQ → quotation → PO | Trace request to cost exposure and delivery date | High |
| Storekeeper | Explain site stock and consumption | Site receipt/transfer/issue/return tied to project and work | Physical/stock/financial records reconcile on agreed basis | High |
| Site engineer | Record progress once, from the site | Short Arabic/mobile form, photo/evidence and material request | Successful entry on agreed phone/network profile | High |
| Project manager | Identify delay or productivity loss | Planned versus completed quantities, labor hours and equipment usage | Daily record links to work package and reason for variance | Next |
| Estimator | Reuse reliable prices and assemblies | Controlled resource rates, rate build-ups and BOQ import validation | Reprice a tender with traceable assumptions | High; improve existing foundation |
| Document controller | Find the right approved evidence | Revision, reviewer, due date and status on key records | No reliance on an uncontrolled attachment filename | Next; higher for EPC/consultant-led contracts |
| Business owner / IT | Adopt and keep the system operating | Data templates, Arabic training, access roles, backups, upgrade/support procedure | Successful onboarding and restore rehearsal | Essential |

Do not assume every SME needs all modules. For a labor-heavy specialist, timesheets/productivity may rank above fleet management. For a subcontract-heavy main contractor, subcontract claims can be a buying prerequisite. For MEP/fit-out, procurement lead time and material approval may dominate. Classify the pilot before locking later milestones.

## 7. Productivity opportunities and how to measure them

The objective is fewer handoffs, less rekeying and earlier exceptions. A new screen alone is not a productivity improvement.

| Process | Proposed improvement | Metric | Initial target to validate |
|---|---|---|---|
| Certificate preparation | Carry forward approved history and pull only eligible measured quantities | Active staff minutes per comparable certificate | 30% reduction from measured baseline |
| Invoice preparation | Generate draft from approved certificate with validated mapping | Re-entered fields and correction rate | No rekeying of approved work quantities/rates |
| Approval chasing | Role-based pending list, due dates and reminders | Internal waiting time by approval step | 20% reduction, excluding customer waiting |
| Procurement | Reuse approved resource needs and carry BOQ identity through documents | Request-to-PO lead time and duplicate entry | 20% less internal processing time |
| Cost reporting | Reconciled source-driven report with exception drill-down | Time to produce weekly project cost pack | 50% reduction after data stabilization |
| Site reporting | Capture quantity and evidence once on mobile | Same-day completion rate; office transcription minutes | At least 90% same-day capture in pilot |
| Subcontract valuation | Agreement-based claim verification | Quantity/rate corrections per claim and verification time | Baseline first; no unsupported numerical claim |
| Financial integrity | Automated allocation/reconciliation checks | Duplicate bills and unexplained differences | Zero accepted discrepancies |

Targets are proposals, not measured outcomes. Compare similar projects, line counts and staff experience. Track staff time separately from elapsed approval time. Faster billing is not automatically faster customer payment.

Illustrative sizing only: if 12 certificates per month require four staff hours each and preparation falls by 30%, the saving is **14.4 staff hours/month**. Financial value equals verified hours saved × actual loaded hourly cost. Do not add speculative collections acceleration or avoided losses to ROI without observed evidence.

## 8. Egypt first; Gulf expansion by country

### Egypt release requirements

Prioritize Arabic terminology and print acceptance, familiar QS/accounting workflows, assisted Excel migration, explicit company/contract account mappings, and the selected customer's tax-authority integration. Contract-specific deductions, guarantees, withholding treatment and advance rules need the customer's accountant/commercial owner; no universal default should be presented as Egyptian law.

The ETA publishes an invoice submission API with submitted-document identifiers and responses. An integration must retain the relationship between our invoice and the authority record and support the required lifecycle, not merely produce a PDF. See the [ETA Submit Documents API](https://sdk.invoicing.eta.gov.eg/einvoicingapi/01-submit-documents/).

**Product decision:** evaluate a maintained connector/provider before building a new connector. Qualify authentication/signing requirements, item/tax mapping, validation errors, retries, status retrieval, corrections and operational support against current ETA specifications. Reconcile rejected or pending submissions in a finance queue. Do not assume our generic invoice feature already satisfies this.

The prior report deferred automatic statutory submission. This benchmark refines that scope: the certificate module need not own the connector, but the Egypt customer offering needs an accepted compliant invoicing route where applicable. Connector discovery must run with billing definition; a missing required route can block customer go-live.

### Saudi Arabia expansion gate

Saudi Phase 2 is an integration rollout by taxpayer waves, and applicability is tied to the taxpayer's requirements/notification. Confirm the selected customer's status rather than assuming one date for every business. [ZATCA rollout phases](https://zatca.gov.sa/en/E-Invoicing/Introduction/Pages/Roll-out-phases.aspx).

Qualify the Saudi integration, Arabic outputs, company/currency configuration, deployment/support arrangements and contract deductions independently. A vendor's “ZATCA-ready” statement is not our acceptance test. ZATCA also distinguishes taxpayer compliance from whether a provider appears on its indicative list. [ZATCA e-invoicing portal](https://www.zatca.gov.sa/en/E-Invoicing/Pages/default.aspx).

### UAE expansion gate

UAE electronic invoicing has a separate programme and accredited-service-provider model; it must not be equated with a VAT-formatted PDF. Check the current programme, applicable phase and requirements for the specific customer before quoting a deployment. [UAE Ministry of Finance programme](https://mof.gov.ae/en/about-us/initiatives/einvoicing/).

For Gulf entry, select **one country and one pilot segment**. Validate multi-company permissions, contract currency and exchange-rate treatment, payroll/HR integration where required, customer-mandated scheduling/document systems, support hours and data-hosting terms. Avoid a generic “MENA compliant” product claim.

## 9. Prioritization and delivery sequence

### Selection criteria

Evaluate each package using: whether it blocks a target customer's purchase/go-live; frequency and staff effort; cash/cost exposure; reuse of existing ERPNext/app capabilities; implementation and support burden; and evidence confidence. No numerical market-size or ROI score is assigned without customer data.

| Rank | Package | Why it earns this position | Implementation approach | Confidence |
|---|---|---|---|---|
| 1 | Customer certificates + retention/advance registers | Closes the clearest incomplete commercial workflow | Build construction domain; reuse invoice/payment engine | High on technical gap; demand to validate |
| 1, deployment gate | Egypt invoice integration route | Potential go-live prerequisite for target clients | Integrate/partner first; qualify per customer | High on need for country qualification |
| 2 | BOQ cost visibility + procurement connection | Reuses recorded transactions to expose cost and material needs | Extend reports and mappings; configure base ERP controls | High on reuse; effort needs prototype |
| 3 | Subcontract agreements and certificates | Closes a prominent regional contractor workflow | New supplier-side domain using shared technical components | High on gap; order depends on client mix |
| 4 | Mobile site evidence and material requests | Improves source-data timeliness for earlier packages | Small field workflow on existing records before full Site Diary | Medium until network/user tests |
| 5 | Daily productivity, forecast and cash-flow views | Supports operational decisions once inputs are reliable | Labor/plant logs, dated forecasts and exception reporting | Medium |
| 6 | Full document control, scheduling integrations and Gulf packs | Customer/contract-driven expansion | Integrate specialist systems; add country adapters | Segment dependent |

Arabic usability, permission checks, onboarding, data quality and backup/support are acceptance requirements across all packages, not the final backlog items. A blocking UX problem should be fixed immediately; broad theme customization should not displace commercial workflow delivery.

### How this changes the earlier engineering recommendation

- **Retain customer certificates as the first complete build.** The vendor evidence supports investigating this priority; it does not prove universal highest ROI.
- **Start ETA-route discovery during definition.** Do not wait until invoice construction is finished to discover mapping or lifecycle constraints.
- **Bring forward a small procurement/cost prototype using base ERPNext.** Validate report definitions and data quality during the certificate pilot without adding it to the certificate critical path.
- **Make subcontracting the next committed commercial module if the pilot is subcontract-heavy.** Customer-first sequencing can still be the technical delivery order, but both workflows may be needed before broad sales.
- **Separate minimum mobile capture from a full Site Diary.** Capture required certificate evidence early; broader daily labor/equipment workflows follow.
- **Keep the previous staffing estimates conditional.** This benchmark adds product scope, not delivery capacity. ETA integration, cost reporting, subcontracting and Gulf localization need separate estimates before dates are promised.

### Proposed packages and completion conditions

| Package | Accountable lead | Completion condition |
|---|---|---|
| Market/client definition | Product/Commercial | Interview evidence, pilot segment, purchase blockers and signed scope |
| Certificate pilot | Engineering + QS + Finance | Two reconciled billing cycles; no duplicate allocation/invoice; accepted Arabic print |
| Egypt invoicing route | Finance + Integration Lead | Applicable end-to-end submission/status/correction flow accepted and supported |
| Procurement/cost increment | Engineering + Procurement + Finance | PO/receipt/invoice/consumption scenario reconciles without double counting |
| Subcontract increment | Commercial + Engineering | Agreement-to-claim-to-invoice/payment and disputed/corrected scenarios accepted |
| Field-productivity increment | Operations + Engineering | Agreed mobile/network usability and measurable same-day data capture |
| Gulf entry | GM + Country Finance/Commercial owners | Country-specific requirements, integration, support and pilot evidence accepted |

## 10. Client discovery and comparable vendor demonstrations

Public pages tell us what vendors sell; interviews and demonstrations establish what our target clients actually need. The next team exercise should use one shared test pack rather than eight unrelated presentations.

### Ten-working-day discovery proposal

| Period | Work | Evidence to retain |
|---|---|---|
| Days 1–2 | Recruit three to five Egyptian contractors spanning general contracting, subcontract-heavy and specialist work | Segment, project types, current systems, buying authority and constraints |
| Days 3–5 | Observe QS/accountant/buyer/site workflows and collect redacted examples | Actual processing time, duplicate entry, exceptions, certificate/deduction formats |
| Days 6–7 | Demonstrate our existing BOQ-to-procurement path and a certificate prototype | Observed usability, missing steps and minimum purchase requirements |
| Days 8–9 | If management authorizes vendor contact, run the same scenarios with two or three relevant vendors | Module/edition requirements, configuration versus customization, evidence and commercial quotation |
| Day 10 | Review findings with GM/Finance/Engineering | Prioritized release scope, named pilot, capacity/budget decision and acceptance pack |

This is a proposed team exercise, not completed interviews or authorization to contact vendors.

### Questions that reveal buying requirements

1. How many projects, monthly certificates, subcontractors, users and BOQ lines are involved?
2. Which steps are repeated in Excel, email or messaging applications, and how long do they take?
3. Which deductions, advances, retentions, corrections and customer approval formats are used in real contracts?
4. Is the first buying problem customer billing, subcontract liabilities, project cost visibility or site control?
5. What tax-authority integration and accounting/payroll/scheduling systems must remain?
6. What mobile devices and network conditions do site teams actually have? Is offline operation necessary?
7. Who approves changes and who will own data cleanup, implementation and support?
8. What would prevent a purchase even if the feature demonstration succeeds? Ask about cost, trust, training, migration and support.

### Shared demonstration pack

Use a redacted BOQ with multiple WBS branches, two billing periods, a prospective rate variation, partial measurement, retention cap, an evidenced advance, a disputed subcontract claim, partial deliveries, a material return, a partial customer receipt and a correction.

Require each product, including ours, to demonstrate:

- Import and revise the BOQ without destroying previously approved history.
- Trace a certificate line to measurement evidence and show prior/current/cumulative values.
- Generate an invoice once, show country-integration status where included, and process a correction.
- Explain budget, open commitment and actual cost after partial receipt/invoice/consumption/return.
- Separate customer and subcontractor prices, quantities and balances.
- Deny an unauthorized project/approval action and protect attachments.
- Complete Arabic mobile entry and produce an accepted bilingual/Arabic output.
- Show data export, recovery/support procedure and the exact licensed modules required.

Record outcomes as **demonstrated / configured / requires customization / not demonstrated**. Distinguish available-today capability from a roadmap promise. Do not convert an undisclosed vendor feature into a negative score.

## 11. Commercial viability and product differentiation

Compare a complete implementation rather than headline license prices. Request like-for-like three-year cost for the same users, companies, projects, hosting, data volumes, integrations and support obligations. Pricing was not normalized or quoted in this review.

Include software/subscription, configuration, custom development, data migration, invoice connector/provider fees, training, hosting/backups, upgrades, support and the customer's internal staff time. Our open-source base does not make implementation and ongoing maintenance free.

Potential differentiation to prove in pilots:

| Proposed differentiator | Proof needed |
|---|---|
| Arabic-first QS/accountant workflow | Users complete real tasks and approve terminology/print without workarounds |
| BOQ traceability from estimate through billing/cost | Every figure drills down to a consistent approved source |
| Faster implementation for a defined SME segment | Repeatable templates, migration checks and measured onboarding effort |
| Transparent commercial history | Variations, reversals and allocations remain explainable after corrections |
| Practical site entry | Fewer fields/re-entry steps with reliable evidence and permissions |
| Predictable ownership/support | Documented responsibilities, export/recovery process and realistic response commitments |

These are hypotheses, not established competitive advantages. Avoid claims of feature parity with SAP/Oracle, universal tax compliance, proven cheapest total cost, or production readiness across all customer environments.

## 12. Management action and evidence limits

**Next decision:** nominate a product/commercial owner, QS and finance owner; select the first Egyptian pilot profile; fund a short discovery/definition phase; and reserve implementation/QA capacity. Produce a customer-backed scope and invoice-integration decision before committing the full build budget.

Track a weekly register of requirements, evidence confidence, accepted scope, blockers, owner and next decision. Keep the engineering report's financial-integrity and release gates as the technical acceptance baseline.

### Local verification record

- Baseline: `develop`, `c9e6803c5ac63073aeb0b166c779844d29051d8d`; existing report/session-note changes preserved.
- `python3 scripts/schema_drift_checker.py`: exit 0, source schema facts match.
- `python3 scripts/ai_context_check.py`: exit 0, 11 passed / zero failed.
- Reviewed the earlier engineering report, internal feature review, construction DocType inventory, `construction/services/boq_report_service.py`, `construction/services/boq_scope_registry.py`, and selected source searches for certificate/site/country integrations.
- Reviewed local ERPNext Project, Task, Budget and Request for Quotation JSON; located Supplier Quotation, Payment Entry, Asset and Quality Inspection schemas and project-stock/budget-variance report sources. Located files are not claimed as executed features.
- Repository governance/context read in the preceding review remains applicable; no relevant baseline change was observed.
- No new business tests, installed-site audit, vendor demonstrations, interviews, market-share study or regulatory implementation certification were performed.

### Evidence maintenance

The URLs beside the vendor rows and country requirements are the source register. Recheck them at procurement/design decisions because products, editions and requirements change. Retain a dated demo/test record for any capability promoted from “advertised” to “accepted.” Customer interviews should replace assumptions about frequency, willingness to pay and priorities; repository/runtime verification should replace assumptions about our deployed capabilities.
