# Head of Engineering Phase 0 Gate Report: Enterprise BOQ Reports (MENA)

Date: 2026-06-29
Prepared by: Head of Engineering Department
Repository: /home/mohamed/frappe-bench/apps/construction
Status: Pre-implementation gate. No code changes are authorised until every gate below has an explicit Verify/Decide outcome on file.

---

## 1. Purpose and Non-Purpose

Purpose:
- Act as the single Phase 0 (audit and decision) gate before any Phase 1 implementation begins.
- Anchor every gate item to the live code in the repository with file:line evidence.
- Make the BOQ reporting roadmap enterprise-ready for Egypt and MENA construction practice, including field/site sync, FIDIC commercial mechanics, and statutory tax/vat compliance.
- Capture explicit Verify/Decide outcomes for each open item so engineering starts Phase 1 with zero silent assumptions.

Non-purpose:
- This report does not authorise code changes.
- This report does not host the formal sign-off workflow; that remains in HOE_BOQ_REPORTS_ENTERPRISE_REVIEW_REVISED.md. This report only cites gate criteria.
- This report does not re-derive the Phase 1-6 deliverables; it only gates their start.

---

## 2. Verified Live-Code Baseline (Entry Facts)

The following 15 facts have been verified against the live repository and are accepted as the starting point for implementation. Gate owners should not reinterpret these facts without new evidence, but every fact that depends on database state must have a reproducible evidence artifact attached before Phase 1 starts.

| # | Fact | Live evidence |
|---|------|---------------|
| F01 | BOQ Header lifecycle is Draft -> Pricing -> Frozen -> Locked (forward-only) | boq_header/boq_header.json:47-52; boq_header.py:9-13,72-79 |
| F02 | Lock writes locked_by + locked_date and creates baseline quantity revisions | boq_header.py:61-70; services/quantity_revisions.py:8-82 |
| F03 | BOQ Header rolls up total_contract_value, total_estimated_value, total_budgeted_cost, total_revised_value | boq_header.py:81-113,115-144 |
| F04 | BOQ Item holds quantity, original_qty, current_revised_qty, contract_unit_price, current_revised_unit_price, line_total, est_unit_cost, est_unit_price, est_line_total, overhead_pct, profit_pct, calculated_sell_price, has_stages, quantity_executed, quantity_certified, cost_item | boq_item/boq_item.json:87-92,176-227,237-325 |
| F05 | cost_item is Data, not Link; fetch_cost_item_data() reads CostItem.total_direct_cost | boq_item/boq_item.json:87-92; boq_item.py:141-155 |
| F06 | BOQ Item is allowed only on leaf WBS nodes | boq_item.py:54-59; api/boq_link_queries.py:189 |
| F07 | Frozen/Locked block BOQ Item modification; Pricing allows only PRICING_EDITABLE | boq_item.py:10-24,62-104 |
| F08 | BOQ Item Stage fields: boq_item, boq_header, project, boq_structure, stage_code, stage_name, stage_status, planned_qty, measured_executed_qty, certified_qty, percent_complete | boq_item_stage/boq_item_stage.json:8-134 |
| F09 | certified_qty <= measured_executed_qty; percent_complete 0-100; Frozen/Locked protection; on_doctype_update adds uniqueness + indexes | boq_item_stage.py:136-162,206-209; boq_operational.py:10-21 |
| F10 | BOQ Item is provisioned as an ERPNext Accounting Dimension | install.py:13-14,266-302 |
| F11 | Eight child tables receive boq_header, boq_structure, boq_item, boq_item_stage, boq_selection_scope_type: PO Item, PR Item, PI Item, Stock Entry Detail, Timesheet Detail, JE Account, SI Item, MR Item | install.py:16-25,75-81,375-436 |
| F12 | Per-child gating fields: expense_category (PO/PR/PI/SE/JE/MR), is_progress_billing (SI Item), designation (Timesheet Detail) | install.py:47-68,331-370 |
| F13 | Server-side validation rules live in boq_transaction_validation.py and boq_accounting.py (stage requires item; incomplete attribution rejected; stage belongs to item; project match; only allowed BOQ statuses Frozen/Locked receive attribution) | services/boq_accounting.py:13-64; services/boq_scope_filters.py:17 |
| F14 | revised_boq_queries.py exposes get_original_boq, get_revised_boq, get_quantity_history, get_vo_impact, get_omitted_items, get_variation_items | services/revised_boq_queries.py:5-196 (one per function) |
| F15 | CostItem and PlantResource have no planned production use and are reported by the business as empty; Direct Labor Designation is a child table whose default rows are appended only when the matching ERPNext Designation masters already exist | install.py:83-95,546-578; doctype JSONs; attach SQL COUNT evidence before removal |

---

## 3. Corrections to the Source Documents and This Gate

HOE_BOQ_REPORTS_ENTERPRISE_REVIEW_REVISED.md, implementation_plan.md, and this Phase 0 gate must stay aligned on the following points before Phase 1.

### 3.1 C01 - Server-side gate is UI-only (correction to source doc Section 2.4)

Source doc claim: "Direct-cost gate behavior exists" and "Server-side validation enforces" gating rules.

Live code: server validation in boq_transaction_validation.validate_document -> boq_accounting.validate_transaction_row enforces only attribution completeness (boq_header/boq_structure/boq_item_stage present requires boq_item). It does NOT re-check expense_category == Direct, is_progress_billing == 1, or direct_labor_designations membership. Those gates exist only in the UI depends_on metadata and public/js/boq_filters.js.

Required correction: state explicitly that direct-cost gating is UI-enforced and that a server-side hardening ticket must precede any report that consumes gated rows, otherwise actual-cost reports are poisonable by a client bypass.

### 3.2 C02 - boq_link_queries.py is link-search, not validation (correction to Section 2.4)

Source doc lists api/boq_link_queries.py as one of the files where server-side validation is enforced.

Live code: api/boq_link_queries.py is the whitelisted link-search endpoint set (get_boq_headers, get_boq_structures, get_boq_items, get_boq_item_stages, get_variation_orders, get_vo_line_boq_items, get_variation_structures), applying scope + status filters for dropdowns. Validation rules live in boq_accounting.py + boq_transaction_validation.py.

Required correction: credit validation to boq_transaction_validation.py and boq_accounting.py; reserve boq_link_queries.py for link dropdowns.

### 3.3 C03 - is_progress_billing is declared but not wired end-to-end (correction to Section 2.4 and 5.4)

Source doc Sections 5.4 Progress and Billing Report and 4.x assume billed-from-Sales-Invoice flows.

Live code: the custom field exists, is visible/editable (`hidden = 0`, `read_only = 0`), the UI gate exists, and the validate hook exists. There is no function that creates a progress Sales Invoice from a BOQ Stage, and no event handler updates BOQ Item.quantity_certified. The problem is missing end-to-end wiring, not a hidden/read-only field.

Required correction: mark billed-revenue columns in Section 5.4 as blocked by a Phase 4 deliverable, not as a live feature.

### 3.4 C04 - Direct Labor Designation is conditional seed data (correction to Section 2.6 wording and decision #8)

Source doc Section 2.6 lists CostItem, PlantResource, Direct Labor Designation together under "Existing Custom Resource Masters". Decision #8 confirms CostItem and PlantResource have no production data.

Live code: CostItem and PlantResource have no planned production use and are reported by the business as empty. Direct Labor Designation is a child table with 11 default candidates (Site Worker, Mason, Carpenter, Steel Fixer, Operator, Electrician, Plumber = Mandatory; Site Engineer, Site Supervisor, Foreman = Optional; Project Manager = Not Applicable), but install.py:546-578 appends each row only if the matching ERPNext Designation already exists.

Required correction: do not bundle Direct Labor Designation with the removal of CostItem and PlantResource. Direct Labor Designation stays as a labour policy/gating child table; Phase 0 must decide whether to seed the 11 ERPNext Designation masters or accept conditional rows until those masters exist.

### 3.5 C05 - Egypt social-insurance law and rates must be configurable/current

Source/gate claim: Social insurance is described using Law 79/1975 and fixed employer/employee percentages.

Current regulatory baseline: Egypt issued Social Insurance and Pension Law 148/2019, effective from January 1, 2020, with later amendments including Law 8/2024. Therefore the roadmap must not hard-code Law 79/1975 percentages.

Required correction: model social insurance as configurable rules per company/subcontractor/contract, require current-law advisor sign-off, and treat legacy law references as historical only.

---

## 4. MENA Competitor and Convention Brief (Reference, Not Authority)

The dependent report uses the following MENA reference baseline:

- RIB CCS Candy + iTWO 5D + MTWO: estimating with rate build-up, candy codes, 5D BIM-to-cost, subcontractor procurement portal, FIDIC-aligned progress claim generation.
- Oracle Primavera P6 + Aconex: scheduling + document/FIDIC notice control on infrastructure megaprojects in Egypt and the Gulf.
- Procore: field-first daily logs, RFIs, photos, draw schedule, financials, offline mobile sync.
- BuildSmart: monthly CV/PC valuations, employer-facing dashboards, RICS/NRM cost reporting.
- EGYSHEET, Renez, Kabeja: local Arabic-first BOQ entry tools with simple IPC PDF generation but no real cost ledger.
- Bluebeam Revu, Tradeinterchange: take-off and supplier qualification companions, not standalone ERPs.

Contractual baseline:
- FIDIC Red/Yellow 2017 Sub-Clauses 8.4 (EOT), 13.1-13.3 (Variations), 14.1-14.9 (Payment), 11.3 (DLP), 20.1 (claims).
- BOQ code convention A.B.CC.DD.TT (Project.Division.Sub-section.ItemType).
- IPC: monthly statement, advance payment + advance bond, advance recovery per 14.2 pro-rata, retention 5-10% (half released at Taking-Over, half after DNP), performance bond 10%.
- Subcontractor certificate deductions cascade: carried value -> retention -> advance recovery -> withholding tax -> social insurance -> materials supplied to sub -> penalties/LDs -> bond/guarantee deductions -> previous payments -> net payable.
- Egypt withholding and social-insurance rules must be configurable and advisor-confirmed. Social-insurance implementation must use the current legal framework, including Law 148/2019 and later amendments where applicable, not hard-coded legacy Law 79/1975 percentages.
- Egypt VAT 14% post-2018 (Tax Law 67/2016); Egypt ETA e-invoice/e-receipt platform mandatory since Oct 2022.
- KSA VAT 15%; ZATCA FATOORA Phase 2 (XML clearance, UUID, QR, cryptographic stamp) is mandatory.
- Bilingual Arabic/English contract + certificates; Hijri dates on official site declarations, Gregorian on tax invoices and bank settlements.
- Final account (mokhales nehayi / final account) reconciliation of VOs, dayworks, materials issued, retention -> release.

---

## 5. Verified Live-Code MENA Gaps (Each Becomes a Gate Below)

| # | Gap | Live verification |
|---|-----|--------------------|
| B01 | Retention receivable vs retention payable, advance-payment recovery, withholding tax, social-insurance deductions | zero production code, zero DocType, zero custom field; only present in /docs/ proposals and translation glossary |
| B02 | Multi-currency conversion / exchange gain-loss | Currency used as field type only; no FX logic in app; tests set default_currency USD on Company fixtures |
| B03 | Hijri dates | zero matches repo-wide for hijri |
| B04 | Desk-side RTL/LTR bilingual rendering | RTL selectors exist only on www/index.html; Desk forms have no lang/dir namespace; ar.po translations exist but Desk does not flow per-language dir |
| B05 | Egypt ETA + KSA ZATCA FATOORA Phase 2 e-invoice integration | no integration scaffold, no endpoint, no XML/UUID/QR code |
| B06 | Field/site mobile / offline / gang capture / photo-with-GPS daily report | none; "mobile" matches are responsive theme CSS classes or mobile_no phone field; no PWA, no offline timesheet |
| B07 | Structured BOQ code A.B.CC.DD.TT on BOQ Item | BOQ Item has no structured BOQ code field; only BOQ Structure has wbs_code |
| B08 | Hardened server-side direct-cost gate (closes C01) | UI-only enforcement today |
| B09 | Progress-billing end-to-end wiring (closes C03) | field + gate + validate hook only |
| B10 | VAT 14% (EG) and 15% (KSA) handling on certificates | no production logic; only translation glossary entries |
| B11 | Role separation QS / Commercial / Finance / Site | exists as Workspace/Role in ERPNext baseline but not codified per cost-control responsibility |
| B12 | Audit trail and immutable version history on BOQ/IPC/VO/SPC | BOQ Quantity Revision provides idempotent baseline; VO/SPC immutable history not implemented |
| B13 | Multi-project treasury advances and intercompany recovery | not in scope of this app today |

---

## 6. Phase 0 Exit Gate Checklist

Each gate must end with one outcome: Pass, Fail, or Decided-out-of-scope-with-rationale. No "open" state is acceptable at Phase 1 start. Owner: HOE unless delegated.

### G01 CostItem and PlantResource confirmed-no-data removal audit
Entry: F15 records the business-confirmed no-data status; SQL COUNT evidence must be attached before removal/deprecation.
Required outcome:
- Backup snapshot of tabCostItem and tabPlantResource produced and stored.
- Removal/deprecation patch spec written (drop vs deprecate decision).
- Patch preserves Direct Labor Designation (see G02).
Verify test: SELECT COUNT(*) evidence for tabCostItem and tabPlantResource returns 0 before any drop/deprecation action; no active install.py reference remains after patch; tests/test_boq_properties.py updated.

### G02 Direct Labor Designation seed-data preservation and role classification
Entry: install.py:83-95 has 11 default candidates; doctype is a child table on Construction Settings; install.py:546-578 appends candidates only when matching ERPNext Designation masters exist.
Required outcome:
- Decision recorded: keep as labour policy/gating child table.
- Removal patch must not touch this table; install_migrate idempotent reseed preserved.
- Construction Settings labour configuration stays the source of truth for timesheet BOQ gating.
- Decision recorded: either seed the 11 ERPNext Designation masters first, or document partial/conditional Direct Labor Designation rows until those masters exist.
Verify test: post-patch, Direct Labor Designation behavior matches the recorded decision on a fresh migrate.

### G03 Server-side direct-cost gate hardening spec (closes C01 and B08)
Required outcome:
- Spec for a server validate function that rejects, before transaction submit:
  - PO/PR/PI/SE/JE/MR rows with boq_item set and expense_category != Direct
  - SI Item rows with boq_item set and is_progress_billing != 1
  - Timesheet Detail rows with boq_item set and designation not in configured direct-labor designations
- Spec includes tests for each rejection path.
- Scope deferred or included in Phase 1 is recorded as a decision (recommended: include in Phase 1).
Verify test: trials submitted with bypass payloads throw on the server.

### G04 Sales Invoice progress-billing wiring decision (closes C03 and B09)
Required outcome:
- Decision: Phase 4 wires it (recommended) or out-of-scope for this roadmap and billed-revenue columns are removed from Section 5 of the source HOE report.
- Block dependency declared: Phase 5 report 5.4 not usable until Phase 4 deliverable ships.
Verify test: declaration recorded in both source docs and this dependent report.

### G05 BOQ Item Accounting Dimension performance benchmark at ~1,000 BOQ Items
Required outcome:
- Benchmark script produces numbers for: GL ledger query, permission_query_conditions injection, and report aggregation over 1,000 BOQ Items.
- Pass threshold documented (e.g., p95 < 1s on a standard bench).
- Decision: keep Accounting Dimension; OR demote to a non-dimension link field and update install.py:266-302.
Verify test: benchmark artefact committed to bench/ directory.

### G06 Site/Gang Timesheet field freeze
Required outcome:
- Frozen field set: labor name, project, BOQ Item, description, UOM, price, total.
- Daily-rate card "half-day/day-rate" pattern documented (rate per gang per day per trade, multiplied by attendance count).
- Decision: separate DocType vs child of ERPNext Timesheet; offline/mobile boundary declared (see G14).
Verify test: spec document with mockup of the seven fields and the rate-card pattern committed.

### G07 Subcontractor certificate structure and deductions cascade
Required outcome:
- Cert structure spec: mirrors owner IPC (per decision #6), substitutions only in margin/admin cut (per decision #7).
- Deductions cascade order frozen: carried value -> retention -> advance recovery -> withholding -> social insurance -> materials supplied -> LDs -> bond -> previous -> net payable.
- Main-contractor margin supports both methods: percentage and price-difference (per decision #5/#6).
- DocType outline (Subcontractor Payment Certificate) with field list and PI reconciliation path.
Verify test: spec document committed; PI generation OR reconciliation rule (not both unmanaged) documented.

### G08 Retention receivable vs retention payable GL decision
Required outcome:
- Chart of accounts decision: separate GL accounts for retention receivable (from employer) and retention payable (to subcontractor).
- Release mechanic declared at Taking-Over and at DNP (per FIDIC 14.9 and 11.3).
- VAT treatment of retention clarified (retention is invoiced at release or invoiced at deduction?).
Verify test: COA sample committed; tax advisor sign-off noted.

### G09 Advance payment, advance bond, and recovery (FIDIC 14.2 and 14.6)
Required outcome:
- DocType/field spec for advance payment certificate, advance bond tracking, advance recovery pro-rata.
- Mobilisation advance 10-20% parameter documented; per-IPC recovery formula frozen.
Verify test: spec committed.

### G10 Withholding tax and social-insurance allocation rule
Required outcome:
- Egypt 1% withholding under Tax Law 91/2005 art. 59 implemented as a configurable rate per subcontractor (some exempt).
- Social-insurance rules are configurable per company/subcontractor/contract and are confirmed against current Egypt law, including Law 148/2019 and later amendments where applicable.
- KSA rule: none default; configurable for GCC when needed.
Verify test: rate table committed with advisor sign-off or an explicit out-of-scope decision.

### G11 VAT Egypt 14% and KSA 15% and e-invoice integration boundary
Required outcome:
- Decision: Egypt ETA e-invoice (mandatory since Oct 2022) and KSA ZATCA FATOORA Phase 2 integration scope (clearance XML, UUID, QR, cryptographic stamp).
- In this roadmap: integrated in which phase (recommended: own dedicated phase after Phase 5 reports; not blocking Phase 1).
- VAT rate configuration by company/country.
Verify test: integration boundary document committed, references cited.

### G12 Multi-currency handling for subcontractor certificates
Required outcome:
- Primary EGP; USD/EUR subcontract rates allowed; exchange-rate source declared (Central Bank of Egypt daily rate, manual override, last PI rate).
- Exchange gain/loss booking rule on the sub-cert (per FIDIC 14.3 rate as between parties).
- Resource Price History already stores currency and exchange_rate; confirm certificate uses stored rate.
Verify test: rule committed; sample cert with USD sub-rate and EGP settlement committed.

### G13 Hijri + Gregorian dual-date on official documents
Required outcome:
- Decision: Hijri on which document types (site daily, advance bond, official declarations); Gregorian on which (tax invoices, bank settlements, VAT filings).
- Hijri rendering: Frappe has no native Hijri; choose between hijri-converter python package, JS UmAlQura library, or shared service.
- Print format scope: dual-column or single with conversion header.
Verify test: decision recorded; library chosen; sample print output attached.

### G14 Arabic/English bilingual BOQ and Desk RTL/LTR parity (closes B04)
Required outcome:
- Bilingual field convention: parallel columns "Arabic | English" on BOQ Item, certificates, and reports where contractually required.
- Desk RTL/LTR namespace spec: extend modern_theme.css with a html[lang="ar"] dir namespace so Desk forms and print formats use RTL when the user language is Arabic (today only www/index.html has it).
- Print format RTL template decision (Frappe Print Format Jinja RTL vs custom CSS).
Verify test: spec committed; sample BOQ item bilingual print produced.

### G15 Structured BOQ code A.B.CC.DD.TT
Required outcome:
- Decision: store the structured code on BOQ Item (recommended) as a Data field with a parser/validator, or keep on BOQ Structure and inherit on BOQ Item.
- Migration plan for items currently using free-text title.
- Filter and search use of the structured code in reports.
Verify test: validator and migration spec committed.

### G16 Field/site capture decision
Required outcome:
- One of: Frappe PWA custom page; Frappe Mobile (v15+); third-party field app (Procore, Fieldwire, Plangrid) with import bridge; paper daily then re-keyed into Desk.
- Offline-first mandatory for sites with no stable 4G; sync boundary declared (what merges back vs what stays pending).
- Photo-with-GPS daily report scope: in this phase or deferred.
- Decide whether to use ERPNext standard Timesheet for company employees AND a new Site/Gang Timesheet DocType for daily site labour (per decision #2).
Verify test: decision matrix committed; sync boundary diagram attached.

### G17 Role separation QS / Commercial / Finance / Site (closes B11)
Required outcome:
- Matrix mapping responsibilities (measurement, valuation, subcontract call, certificate approval, payment, cash, daily log, photos) to Frappe Roles and Scope Context dimensions.
- Segregation-of-duties rules in workflow engine (e.g., certifier cannot be payer).
- Approval level matrix (FM-style approvals with M-of-N sign-offs).
Verify test: matrix committed; role updates tested.

### G18 Audit trail and immutable version history
Required outcome:
- For each of BOQ, Variation Order, IPC, Subcontractor Payment Certificate, advance bond, retention release: declare which fields are immutable-after-submit, which are versioned, archive retention (>= 10 years per Egypt Tax Law art. 75).
- BOQ Quantity Revision pattern (idempotent baseline) is the template; reuse for VO and SPC.
- E-signature scope: in this phase or deferred (Egypt Law 181/2018 on e-signature).
Verify test: immutability matrix committed.

### G19 Subcontractor reports separate from owner reports (per decision #6)
Required outcome:
- Confirm: subcontractor reports are independent DocTypes/print formats, not owner-report variants.
- Statement that they match owner certificate structure while exposing main-contractor margin (per decision #6) and admin cut (per decision #7).
- Report registry updates reflected in boq_report_data.py.
Verify test: report list updated; both dev artifacts visible.

### G20 Subcontractor certificates follow owner certificates exactly (per decision #7)
Required outcome:
- Confirm: SPC DocType shares the owner IPC field set; only the admin/main-contractor cut field differs.
- Decision recorded: the "cut" is entered as percentage OR as the difference between owner unit price and subcontract unit price (per decision #5 and #6).
- Decision recorded: SPC creates OR reconciles a Purchase Invoice on approval (one or the other, not both unmanaged).
Verify test: spec committed; PI reconciliation path tested.

---

## 7. Phase 1 Dependencies Blocked by Each Gate

| Gate | Blocks Phase 1st | Unblocks |
|------|------------------|----------|
| G01 | CostItem/PlantResource removal patch | Item construction fields |
| G02 | Removal patch safety | Item construction fields |
| G03 | Actual-cost report credibility | Item fields + report service |
| G04 | Section 5.4 billed-revenue column | Phase 5 Progress Billing report |
| G05 | Accounting Dimension model decision | Item fields indexing + report queries |
| G06 | Site/Gang Timesheet DocType | Phase 4 cost capture |
| G07 | SPC DocType + deductions engine | Phase 4 subcontractor workflow |
| G08..G10 | Retention/advance/withholding scaffolding | Phase 4 SPC and treasury |
| G11 | e-invoice boundary | Phase 4 SI and Phase 5 certificates |
| G12 | Multi-currency rate policy | Resource Price History and SPC |
| G13 | Hijri rendering choice | Print formats (Phase 5) and site daily (Phase 4) |
| G14 | Bi-lingual BOQ + Desk RTL | Item fields UI and certificate print formats |
| G15 | Structured BOQ code | Item mapping and report grouping |
| G16 | Field/site capture route | Site/Gang Timesheet and daily report (Phase 4) |
| G17 | Role workflow | Approval workflows across all phases |
| G18 | Audit and archive policy | All submit-immutable DocTypes |
| G19 | Subcontractor report independence | Report set (Phase 5) and boq_report_data.py |
| G20 | SPC equals IPC | SPC DocType (Phase 4) |

---

## 8. Differences vs HOE_BOQ_REPORTS_ENTERPRISE_REVIEW_REVISED.md

1. Adds 20 explicit Verify/Decide gates; the source doc has none.
2. Corrects C01 (server-side gate is UI-only), C02 (boq_link_queries.py is link-search), C03 (progress billing not wired), C04 (Direct Labor Designation seed rows are conditional), and C05 (Egypt social-insurance law/rates must be current and configurable).
3. Adds MENA sections 4 and 5 referencing FIDIC and Egypt/KSA fiscal law.
4. Forces each MENA gap in section 5 to a Pass/Fail/Out-of-scope outcome before any Phase 1 work.
5. Defers sign-off workflow authority to HOE_BOQ_REPORTS_ENTERPRISE_REVIEW_REVISED.md (per steering decision).

---

## 9. References

- FIDIC Conditions of Contract for Construction, 2nd Ed. 2017 (Red Book): Cl. 8.4, 13.1-13.3, 14.1-14.9, 11.3, 20.1.
- FIDIC Contracts Guide, 2nd Ed. 2022.
- Procore Library: Construction Bill of Quantities, Construction audit trail.
- Oracle Aconex platform documentation.
- RIB Software product pages (Candy, iTWO 5D, MTWO).
- Rider Levett Bucknall BuildSmart.
- Egyptian Tax Authority E-Invoicing (ETA) portal: invoicing.eta.gov.eg.
- KSA ZATCA FATOORA E-Invoicing Phase 2 specification: zatca.gov.sa/en/E-invoicing.
- Egypt Social Insurance and Pension Law 148/2019, later amendments including Law 8/2024 where applicable; Egypt Tax Law 91/2005 art. 59 (withholding).
- Egypt Tax Law 67/2016 (VAT 14%).
- Egypt E-Signature Law 181/2018.
- KSA Digital Government Authority / PDPL: dga.gov.sa.
- Construction ERP repository: /home/mohamed/frappe-bench/apps/construction (live code citations per section 2 above).
