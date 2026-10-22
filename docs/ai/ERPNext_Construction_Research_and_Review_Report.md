# ERPNext Construction and Contracting: Research and Review Report

**Document ID:** ERP-CONSTRUCTION-REVIEW-001  
**Version:** 1.2 — business scope answered; recommendation context updated  
**Research date:** 16 September 2026  
**Revision date:** 17 September 2026  
**Language:** English; consolidates research originally discussed in Arabic  
**Status:** Business scope answered by the project owner (v1.2); pending manager and independent review; no product selected for production  
**Audience:** Project owner, manager, implementation team, and independent reviewing AI agent

> This document consolidates the substantive work in the current conversation: the original candidate list, initial verification, expanded research, selected source-code inspection, changes in recommendation, unresolved questions, and a proposed evaluation process. It is a research handoff, not a verbatim chat transcript or a deployment certification.
>
> **Version 1.1 note:** This revision adds a table of contents, a decisions-requested list, a capability coverage matrix, finding status fields and a finding-to-test traceability table, an evaluation roadmap with decision gates, a risk register, a vendor due-diligence questionnaire, custom-development governance for Path A, cross-cutting considerations (security, licensing, migration, environments, performance, evidence), two additional acceptance tests (AT-13, AT-14), two additional open questions (Q-11, Q-12), a glossary, and a weighted scoring template. Findings F-01 to F-12, sources S01–S47, and all evidence statements are unchanged from v1.0. Sections 10–14 and the annexes are process proposals, not new evidence. Stable IDs (F, S, AT, Q, R, RSK, VD) are used for cross-reference instead of section or line numbers.
>
> **Version 1.2 note:** The project owner answered Q-01 to Q-12 (Section 16). The answers change the decision context: this is a pre-sales product-development effort by a solo developer working with AI assistance; an in-house v16 construction app already exists; Egypt is the first market; and any purchased component must include rights to modify and resell. Section 1.2, Path D (Section 9), the demo track (Section 10), risks RSK-13 to RSK-16, VD-17, the resale-rights analysis (Section 14.2), and the implications analysis (Section 16.1) were added. Findings, sources, and earlier evidence are unchanged.

## Contents

1. [Executive decision brief](#1-executive-decision-brief)
2. [Objective, scope, and decision criteria](#2-objective-scope-and-decision-criteria)
3. [Work performed and limitations](#3-work-performed-and-limitations)
4. [How the recommendation evolved](#4-how-the-recommendation-evolved)
5. [Candidate comparison](#5-candidate-comparison)
6. [Findings register](#6-findings-register)
7. [Initial claims: correction record](#7-initial-claims-correction-record)
8. [Repository and version snapshot](#8-repository-and-version-snapshot)
9. [Recommended architecture and selection paths](#9-recommended-architecture-and-selection-paths)
10. [Evaluation roadmap and decision gates](#10-evaluation-roadmap-and-decision-gates)
11. [Risk register](#11-risk-register)
12. [Vendor due-diligence questionnaire](#12-vendor-due-diligence-questionnaire)
13. [Custom development governance for Path A](#13-custom-development-governance-for-path-a)
14. [Cross-cutting considerations](#14-cross-cutting-considerations)
15. [Proposed acceptance tests](#15-proposed-acceptance-tests)
16. [Manager decisions and open questions](#16-manager-decisions-and-open-questions)
17. [Independent AI-agent review brief](#17-independent-ai-agent-review-brief)
18. [Review and comment log](#18-review-and-comment-log)
19. [Source register](#19-source-register)
20. [Installation commands discussed in the session](#20-installation-commands-discussed-in-the-session)
21. [Proposed next action and document history](#21-proposed-next-action-and-document-history)
- [Annex A. Glossary](#annex-a-glossary)
- [Annex B. Weighted scoring template](#annex-b-weighted-scoring-template)

## 1. Executive decision brief

**Provisional recommendation:** Prefer **ERPNext v16 + BuildSuite Core as a foundation for a customized construction solution**, provided the organization accepts development of missing client progress-billing functionality and a formal acceptance exercise.

**Alternative procurement path:** Evaluate **Quantbit BuildX** with its developer as a potentially broader implementation. Require the supplier to demonstrate the exact deliverable, source availability, financial workflows, and working integrations. Do not assume the public BuildX + ProcureX combination is already a complete self-hosted product.

**Ready-to-run requirement:** This research did **not** establish a fully integrated, production-ready, publicly downloadable solution that can be recommended without further implementation and testing.

These are engineering judgments, not measured rankings. No application was installed, migrated, or executed on an ERPNext site during this session. No accounting entries were validated against a running ledger. The recommendations remain conditional.

The main reasons are:

- BuildSuite explicitly excludes client RA/progress billing and client-side retention from its current documented release. [S01]
- BuildSuite has meaningful subcontract-billing test implementations, but their presence is not proof they pass; an inspected CI run failed without an explanatory step record available to us. [S04–S05]
- Quantbit publishes real billing code, but selected certificate controllers and tests are only scaffolding. [S10–S13]
- Two inspected ProcureX financial screens do not support the assumption of a complete local analytics package: cash-flow figures are hard-coded, and Budget Pro redirects to a fixed external address. [S17–S18]
- Other candidates are narrower, target v15, lack sufficient current compatibility evidence, or do not expose installable application code. [S20–S26]

### 1.1 Decisions requested from management

| ID | Decision requested | Options / guidance | Needed at |
| --- | --- | --- | --- |
| D-01 | Confirm answers to business-scope questions Q-01 to Q-12 | Section 16; answers drive every later step | Gate G-0 |
| D-02 | Select the evaluation path | Path A (customization foundation), Path B (vendor-led BuildX), Path C (ready-made search), or reopen research | Gate G-0 |
| D-03 | Authorize a sandbox environment and evaluation effort | Non-production Bench only; no production data | Gate G-0 |
| D-04 | Appoint acceptance owners | Named finance, QS, project-management, and IT representatives (Q-09) | Gate G-0 |
| D-05 | Choose the product strategy (added v1.2) | Path A (adopt BuildSuite foundation), Path B (vendor BuildX), Path C (buy ready-made), Path D (continue in-house), or hybrid build + reference adoption | Gate G-0 |
| D-06 | Set the demo target (added v1.2) | Demo scope (modules, Egyptian demo data, Arabic layouts) and target presentation date | Gate G-0 |

### 1.2 Business context established in v1.2

The answered questions (Section 16) establish the following context:

- The evaluator is a solo developer building a construction ERP product to present and sell to owners — not an organization selecting an ERP for its own contracting projects (Q-05, Q-10, Q-12).
- An in-house Frappe/ERPNext v16 construction app already exists in development (BOQ, theme, scope-context, and form-layout systems), deployed on a local Bench and on Frappe Cloud (Q-02).
- The first market is Egypt, with wider MENA later (Q-01); billing rules follow Egyptian market practice and vary per contract (Q-06).
- Client cumulative billing may be deferred to a second phase or developed with AI assistance (Q-03).
- Purchasing a ready app is acceptable only with rights to modify and resell to owners (Q-04).
- There is no historical data to migrate for the developer's own start (Q-07); offline mobile is deferred (Q-08); data residency/DR is undecided (Q-11).

**Updated provisional direction (inference — to be validated, not new evidence):**

1. **A hybrid build-first strategy is now the natural default.** Continue the in-house app as the product, and close the construction-finance gap (client and subcontractor billing, retention, advances, certification) by studying or adopting MIT-licensed components. BuildSuite Core and Quantbit BuildX are both MIT-detected (Section 8): their licenses already permit modification and commercial resale with attribution, without any purchase (Section 14.2).
2. **Adopting BuildSuite Core as an installed foundation now carries a specific conflict.** The in-house app already owns BOQ structures; co-installing overlapping construction apps triggers RSK-12. Adoption requires a data-ownership merge decision before any installation.
3. **Buying a commercial app remains possible only with explicit resale/white-label rights** (VD-17). Standard marketplace licenses and separately sold vendor modules (S35) should be assumed not to grant them.
4. **The near-term priority is a demonstrable product** (Q-05): Egyptian demo data, Arabic layouts, and the end-to-end cycle (Q-09) matter more in the next phase than production hardening. The gate framework applies per owner engagement afterward.

All v1.0/v1.1 findings remain valid evidence about the third-party candidates. What changed is how they are used: as adoption candidates, as reference implementations, or as negotiation scope with vendors.

## 2. Objective, scope, and decision criteria

The original objective was to identify the best integrated construction/contracting extension for ERPNext, with particular attention to v16. The user requested a renewed search and deeper verification after an initial review.

The starting list contained BuildSuite Core, ProjectIT, `construction_management_suite`, and `civil_contracting`. Expanded research added Quantbit BuildX, ProcureX and its component repositories, EPCForge, and `ERPNext-Construction-Module`.

The evaluation considered:

| Criterion | Why it matters |
| --- | --- |
| BOQ, estimation, WBS, and change control | Establishes scope, quantities, rates, and revisions |
| Procurement, stock movement, and project costing | Connects site activity to commitments and actual costs |
| Client and subcontractor progress billing | Covers cumulative measurements, certification, deductions, retention, and advances |
| Accounting integration | Ensures operational documents reconcile to ERPNext financial records |
| Site, labor, and equipment workflows | Captures execution data at its source |
| Compatibility and packaging | Determines whether a reproducible installation is plausible |
| Tests and maintenance evidence | Supports confidence in lifecycle behavior and future support |
| Localization and language | Must match the operating country and document requirements |
| Public code versus commercial scope | Determines what the organization actually receives and can maintain |

No weighted scoring was used in this research phase. Star counts, file counts, and commit volume were not treated as proof of quality. A weighted scoring template for the formal evaluation phase is provided in Annex B.

**Business requirements:** Initially unknown; answered by the project owner on 2026-09-17 (Section 16), with implications analyzed in Section 16.1. Q-11 (data residency, backup, and disaster recovery) remains open.

## 3. Work performed and limitations

### 3.1 Research work completed

1. Opened the original GitHub, vendor, marketplace, and community links.
2. Compared README claims with explicit requirements and release limitations.
3. Searched for alternative Frappe/ERPNext construction applications and implementation references.
4. Inspected GitHub repository metadata and recursive file trees through the public API.
5. Retrieved selected raw Python, JavaScript/TypeScript, JSON, TOML, README, and workflow files.
6. Read selected billing controllers, hooks, certificate schemas, tests, localization files, and ProcureX financial screens.
7. Checked selected branches, tags, and a BuildSuite CI result.
8. Revised the recommendation when code evidence contradicted a more optimistic interpretation of product descriptions.

### 3.2 Evidence labels used below

| Label | Meaning |
| --- | --- |
| **Observed** | Visible directly in retrieved code, metadata, or a specific file |
| **Documented** | Claimed by the publisher or marketplace; not operationally demonstrated here |
| **Inference** | Our interpretation of observed or documented evidence |
| **Unverified** | Requires execution, broader inspection, vendor evidence, or business clarification |

### 3.3 What was not done

- No Bench environment, database, or application was installed.
- No application tests, migrations, builds, mobile builds, or transaction scenarios were executed.
- No full repository security or accounting audit was performed.
- No full localization, licensing, accessibility, performance, or upgrade assessment was performed.
- No vendor was contacted and no demo was attended.
- No price, implementation duration, or support service level was established.
- No source repository was modified and no system was deployed.

Some public pages failed to load through the web reader. Several were subsequently inspected through raw GitHub files or API responses. A retrieval failure is not proof that a repository is private, deleted, or unusable. Search snippets alone were not accepted as proof of working functionality.

Branches and web pages may change after this review. Selected files were fetched from branch URLs during the session, not from an immutable, fully archived checkout. The snapshot information in Section 8 helps a reviewer reproduce the investigation but does not certify byte-for-byte consistency of every retrieval.

## 4. How the recommendation evolved

| Stage | Working conclusion | Evidence that shaped or changed it |
| --- | --- | --- |
| Original user-supplied list | BuildSuite presented as the newest and most comprehensive option | This was an initial claim, not our verified conclusion |
| Initial verification | BuildSuite was worth testing on v16, but not complete | README explicitly excluded client progress billing and retention; CMS documented v15 |
| Expanded discovery | BuildX + ProcureX appeared a potentially broader integrated candidate | Vendor/community descriptions and technical documentation covered more functional areas |
| Billing-code inspection | BuildX had real billing paths, but coverage was uneven | Sales-invoice mapping existed; selected certificate controllers/tests were scaffolding |
| ProcureX inspection | The public combined package could not be treated as complete local analytics | Static cash-flow values and fixed external Budget Pro redirect |
| Final research position | BuildSuite as a customization foundation; BuildX as a vendor-led evaluation candidate | Known scope limitations were weighed against implementation evidence and packaging gaps |

**Superseded conclusion:** Any interim statement favoring BuildX + ProcureX as an already integrated package is superseded by the ProcureX findings. The final recommendation does not certify either candidate for production.

## 5. Candidate comparison

| Candidate | Compatibility evidence | Scope and material limitation | Proposed disposition |
| --- | --- | --- | --- |
| **BuildSuite Core** | README and current package metadata target v16 | Broad construction operations; Beta; client RA/progress billing and client retention explicitly excluded | First foundation to evaluate if customization is acceptable [S01, S03] |
| **Quantbit BuildX / Construction Management** | Current `pyproject.toml` specifies Frappe `>=16.0.0,<17.0.0` | Broad documented scope and real billing code; selected workflows insufficiently proven | Evaluate with exact delivery scope and live evidence [S07–S13] |
| **ProcureX + ProcurexBundle** | Bundle targets v16; backend defaults to `version-16` | Packaging joins frontend/backend, but inspected financial screens have significant limitations | Do not count financial analytics as complete without correction [S15–S19] |
| **EPCForge** | Marketplace and repository explicitly target v16 | BOQ, budget, tendering, document control; complete construction billing not established | Consider for a narrower requirement [S20–S21] |
| **Construction Management Suite** | README specifies Frappe/ERPNext v15 | Broad claims; selected invoice and localization implementation raises questions | Do not adopt directly without remediation and testing [S22–S24] |
| **ProjectIT** | Marketplace lists v15 and v16 | Field attendance, GPS/photos, progress and time capture; ERPNext and HRMS required | Optional field tool, not the construction core [S25] |
| **civil_contracting** | Current v16 support not established | Worker attendance/wages, site costing, measurements; old maintenance signal | Not preferred for a new v16 implementation [S26] |
| **ERPNext-Construction-Module** | README describes v15 | Public default-branch tree contained only README | Not a publicly installable app on inspected evidence [S27–S28] |

### 5.1 Capability coverage matrix

Legend: **Observed** = seen in retrieved code, not executed. **Documented** = publisher/marketplace claim only. **Partial** = some evidence with material gaps. **Gap** = evidence of absence or explicit exclusion. **Unverified** = insufficient inspection. **N/A** = outside the product's purpose. No cell in this matrix means production-proven.

| Capability | BuildSuite Core | BuildX | ProcureX | EPCForge | CMS (v15) | ProjectIT | civil_contracting |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BOQ and estimation | Documented | Documented | N/A | Documented | Documented | N/A | Partial (legacy) |
| WBS and project cost control | Documented | Documented | Partial [F-09] | Documented | Documented | N/A | Documented (legacy) |
| Procurement and stock integration | Documented | Documented | Observed (API inventory) [S34] | Documented | Documented | N/A | Partial (legacy) |
| Subcontractor progress billing | Observed, unexecuted [F-02] | Observed [F-05] | N/A | Unverified | Observed (v15) [F-10] | N/A | Unverified |
| Client progress billing | Gap [F-01] | Observed [F-05] | N/A | Unverified | Observed (v15) [F-10] | N/A | Gap |
| Client retention and advance recovery | Gap [F-01] | Unverified | N/A | Unverified | Partial [F-10] | N/A | Unverified |
| Certification workflow automation | Unverified | Partial [F-06] | N/A | Unverified | Observed (v15) | N/A | Gap |
| Site, labor, and equipment capture | Documented | Documented | N/A | Partial | Documented | Documented (field/time) | Documented (legacy) |
| Financial analytics and cash-flow | Unverified | Unverified | Gap [F-07, F-08] | Unverified | Unverified | N/A | Gap |
| Mobile field operations | Unverified | Documented, unbuilt [S36] | N/A | Unverified | Unverified | Documented | Gap |
| v16 packaging evidence | Observed [S03] | Observed [S09] | Observed [S16, S19] | Documented [S20] | Gap (v15) [S22] | Documented [S25] | Gap [F-12] |
| Test and CI evidence | Observed; CI failing [F-03] | Gap (no workflows in tree) | Unverified | Unverified | Gap | Unverified | Stale [F-12] |

**Reading guidance:** BuildX shows the broadest observed billing coverage but with proven scaffolding in selected certificates and no CI evidence. BuildSuite shows stronger engineering signals (tests, CI configuration) with an explicit client-billing exclusion. The matrix supports the two-path recommendation in Section 9; it does not rank either candidate as production-ready.

## 6. Findings register

All findings are **Open** as of 2026-09-17. A finding is closed only by the resolution evidence named in it, recorded in the review log (Section 18).

### F-01 — BuildSuite client billing gap

**Evidence:** Documented. **Decision impact:** High. **Confidence:** High about documented scope; runtime untested. **Status:** Open.

The README identifies client-facing RA/progress billing and client-side retention as outside the current release. Therefore, supplier/subcontractor billing support must not be interpreted as proof of a complete client billing cycle. [S01]

**Required resolution:** Demonstrate a delivered client billing module or budget for implementation and acceptance testing. Confirm the scope against a specific release or commit before contracting.

### F-02 — BuildSuite subcontractor implementation and tests

**Evidence:** Observed. **Decision impact:** High. **Confidence:** High about code presence; execution unverified. **Status:** Open.

The selected subcontractor controller generates a linked Purchase Invoice on submission and handles cancellation. Its test file includes substantive tests for invoice creation, idempotency, cumulative prior billing, payment/advance behavior, cancellation, amendment, and company/account consistency. These are positive engineering signals, not verified outcomes. [S04, S06]

**Required resolution:** Run the tests on the proposed dependency versions, then reconcile a complete subcontract lifecycle in an actual test site.

### F-03 — BuildSuite CI did not establish a passing build

**Evidence:** Observed. **Decision impact:** High. **Confidence:** High for recorded status; cause unknown. **Status:** Open.

The inspected CI run for commit `8be9c981a798d2c07c47a201044703d87c29e5af` was marked failed. The retrieved job record identified a failed Server job but supplied no step details. It is not justified to say the business tests themselves failed: execution infrastructure or setup could also be responsible. [S05]

**Required resolution:** Obtain the failure reason and a successful reproducible install/build/test run for the intended deployment revision.

### F-04 — Runtime and release information need reconciliation

**Evidence:** Observed/documented. **Decision impact:** Medium to high. **Status:** Open.

The Frappe installation guide listed Python 3.14, Node.js 24, and MariaDB 11.8 for its v16/develop column. BuildSuite package metadata required Python `>=3.14`; its inspected CI configuration also used those runtime generations. The earlier README environment description was less strict. [S03, S29, S30]

The BuildSuite website's illustrative stack included `v2.4`, while the inspected package initializer declared `0.0.1` and the tag query returned `release-0.1.0` plus `user-company`. These identifiers must not be treated as equivalent release guarantees. [S02, S31, S32]

**Required resolution:** Agree an exact bill of materials: Frappe/ERPNext/application revisions, Python/Node/database versions, migration procedure, and rollback plan. Do not choose a production release from a marketing example.

### F-05 — BuildX has real ERPNext billing integration

**Evidence:** Observed. **Decision impact:** High. **Status:** Open.

The inspected `RA Billing` controller includes a `create_sales_invoice` mapping. `Contractor Billing` includes Purchase Invoice/Journal Entry paths, payment-status handling, and cancellation-related logic. This establishes implementation beyond a feature list, but not correct handling of every retention, advance, tax, or cancellation scenario. [S10–S11]

**Required resolution:** Run both client and subcontractor cycles and verify the resulting financial documents. Check configuration, permissions, and cumulative measurement behavior separately.

### F-06 — Selected BuildX certificates/tests are scaffolding

**Evidence:** Observed. **Decision impact:** High for affected workflows. **Status:** Open.

`ProgressCertificate` contained a class with `pass`; its JavaScript file was a commented template, and its test class also contained `pass`. The inspected `SC Payment Certificate` controller primarily generated a certificate number. A form/schema can still store information without custom controller logic, so these observations do not prove the whole app is nonfunctional. They do mean that the inspected files do not demonstrate an automated certification/settlement cycle. [S12–S14]

**Required resolution:** Identify any logic elsewhere and demonstrate certification, deductions, approval, posting, and reversal. Replace template tests with behavior-based tests for the delivered process.

### F-07 — ProcureX cash-flow screen uses static figures

**Evidence:** Observed. **Decision impact:** High. **Confidence:** High for the inspected screen. **Status:** Open.

`finance.cashflow-forecasting.lazy.tsx` defines forecast periods, inflows, outflows, balances, and confidence labels directly in the component. The inspected screen does not retrieve those forecast values from company transactions. [S17]

**Required resolution:** Demonstrate live calculations using the buyer's test data. Changing an invoice, expected collection date, or supplier payment should cause explainable forecast changes. Do not accept the screen's appearance as evidence of implemented forecasting.

### F-08 — ProcureX Budget Pro redirects externally

**Evidence:** Observed. **Decision impact:** High for self-hosting and completeness. **Status:** Open.

`finance.budget-pro.lazy.tsx` redirects to a fixed `construction-management.quantcloud.in/budget_dashboard` address. That does not establish that Budget Pro is supplied as a local component of the buyer's installation. [S18]

**Required resolution:** Identify the destination module, its source/licensing, authentication, data source, and deployment dependencies. Demonstrate operation inside the proposed hosting arrangement.

### F-09 — ProcureX is a collection of separately inspectable components

**Evidence:** Observed/documented. **Decision impact:** Medium to high. **Status:** Open.

The bundle fetches a Frappe backend and builds a separate frontend. Its README defaults the backend to `version-16` and frontend to `main`. The backend package requires Python `>=3.14`. [S15–S16, S19]

Additional inspection found static initial data in the Project 360 frontend as well as API-fetch logic. That mixed implementation was not fully traced, so we did not conclude that every Project 360 metric is static. Backend API entry points included supplier/RFQ/quotation/order/invoice operations; a complete analytics audit was not performed. [S33–S34]

**Required resolution:** Trace each required dashboard metric to an actual endpoint/query. Review licensing per component; a bundle's MIT label must not be assumed to resolve every dependency's terms.

### F-10 — CMS invoice construction requires financial review

**Evidence:** Observed plus inference. **Decision impact:** High. **Status:** Open.

The inspected Interim Payment Certificate controller computes deductions and uses `net_payable_this_period` as the rate of a generated Sales Invoice line. That function did not separately allocate retention and advance recovery to their respective accounts. This is a risk requiring review, not a proven ledger error from a live execution. The function inserts a draft invoice rather than demonstrating a fully posted cycle. [S23]

**Required resolution:** Confirm gross certified work, retention, advance recovery, taxes, receivable, and invoice posting treatment in a running site. Inspect hooks and repeat submission/cancellation paths for unwanted duplicate side effects.

### F-11 — CMS regional claims exceed the evidence inspected

**Evidence:** Observed. **Decision impact:** High if local compliance is required. **Status:** Open.

The inspected Saudi localization file contains tax settings, a `zatca_enabled` flag, and amount-formatting functionality. These alone do not demonstrate an operational electronic-invoicing integration. No full regulatory or compliance assessment was performed. [S24]

**Required resolution:** Validate the required country's actual integration against its operational requirements. A flag, tax rate, or Arabic label is not an acceptance test.

### F-12 — Narrower and older alternatives do not close all gaps

**Evidence:** Documented/observed. **Decision impact:** Medium. **Status:** Open.

EPCForge deserves consideration for estimation, tendering, budgeting, and engineering document control. ProjectIT serves field tracking and time capture. Neither was established as the complete construction-finance solution sought here. [S20–S21, S25]

The `civil_contracting` repository's reported last push was 30 January 2022. This is a maintenance indicator, not proof of incompatibility. The public `ERPNext-Construction-Module` tree contained only a README; the related forum author described the solution as commercial at that time. [S26–S28]

**Required resolution:** Restrict evaluation to products whose delivery scope and current compatibility can be demonstrated.

### 6.1 Finding-to-risk-to-test traceability

| Finding | Linked risk(s) | Acceptance test(s) that would close it |
| --- | --- | --- |
| F-01 | RSK-01 | AT-03, AT-04 |
| F-02 | RSK-02 | AT-05, AT-06 |
| F-03 | RSK-03 | AT-01 |
| F-04 | RSK-04 | AT-01, AT-12 |
| F-05 | RSK-02, RSK-05 | AT-03, AT-04, AT-05, AT-06 |
| F-06 | RSK-05 | AT-03, AT-04 |
| F-07 | RSK-06 | AT-10 |
| F-08 | RSK-06, RSK-07 | AT-10 |
| F-09 | RSK-06 | AT-10 |
| F-10 | RSK-08 | AT-03, AT-04, AT-06 |
| F-11 | RSK-09 | AT-11 |
| F-12 | RSK-10 | AT-01, AT-12 |

## 7. Initial claims: correction record

| Initial statement or implication | Review outcome |
| --- | --- |
| BuildSuite is the newest and most comprehensive | Not established by the research; treat as a claim, not a ranking |
| BuildSuite supports both v15 and v16 | Current inspected materials substantiate v16; v15 support was not established |
| BuildSuite includes client and subcontractor RA billing | Corrected: current README excludes client progress billing and client retention |
| All advertised BuildSuite platform capabilities are included in Core | Not established; the Frappe Incubator description distinguishes advanced commercial modules [S35] |
| The `cepho` account URL identifies the application | Corrected to the actual `cepho/construction_management_suite` repository |
| CMS is suitable for v16 | Not established; its README specifies v15 |
| CMS regional localization proves full Gulf compliance | Not established by inspected code |
| ProjectIT is a full construction application | It is a specialized field/time tool requiring ERPNext and HRMS |
| Legacy civil_contracting can be installed on v16 | No current compatibility proof found |
| A feature-rich README means downloadable working code exists | Contradicted by the inspected README-only construction-module repository |
| BuildX + ProcureX is a complete local package | Withdrawn as an assumption after inspecting financial screens |
| A CI configuration and test files establish stability | Incorrect; passing execution was not demonstrated |

## 8. Repository and version snapshot

Metadata below was observed during this session. `pushed_at` can reflect repository-wide activity, not the last default-branch commit. File/test counts describe the inspected tree; they do not measure quality or test coverage.

| Repository | Default branch | Reported last push (UTC) | Files / `test_` path matches | Notes |
| --- | --- | --- | --- | --- |
| BuildSuite-io/buildsuite_core | develop | 2026-09-16 12:23:25 | 845 / 61 | CI and linter workflows present; MIT detected |
| QuantbitERP/Quantbit-Construction-Management | main | 2026-08-26 06:09:07 | 822 / 87 | No `.github/workflows` files in inspected tree; MIT detected |
| QuantbitERP/ProcurexBundle | main | 2026-09-08 10:15:15 | 18 / 0 | MIT detected |
| cepho/construction_management_suite | master | 2026-05-20 13:58:16 | 319 / 0 | README says MIT; API did not identify a license |
| revant/civil_contracting | master | 2022-01-30 10:20:58 | 148 / 10 | GPL-2.0 detected |
| amet123/ERPNext-Construction-Module | main | 2026-05-19 06:58:15 | 1 / 0 | Only README in inspected tree |
| invento-software-limited/epcforge | version-16 | 2026-09-15 12:13:40 | Not counted in this audit | Marketplace lists v16 |
| QuantbitERP/ProcureX | main | 2026-08-10 04:18:24 | 106 / not assessed | API did not identify a license |
| QuantbitERP/ProcureX-Backend | version-16 | 2026-08-10 04:13:05 | 34 / not assessed | MIT detected |

Sources: GitHub metadata/tree queries for the linked repositories in the source register. Absence of an API-detected license is not a legal determination. Empty/template tests count in path totals.

**Branch commit identifiers returned by the branch API:**

- BuildSuite `develop`: `8be9c981a798d2c07c47a201044703d87c29e5af`.
- Quantbit Construction `main`: `d94af9e2be02aa968155272e46ae8dfd8451e802`.

**Tags inspected:**

- BuildSuite: `release-0.1.0` and `user-company` were returned. No production-readiness conclusion follows from these tag names.
- Quantbit: tag `1.0.0` pointed to `118246bcc7f94c3ac496b22d6784e521ebf62a51`, with a 13 July 2026 commit date. Its inspected package file lacked the explicit compatibility section found in the later `main` package file. We did not recommend that tag as the best deployment target.

Additional access outcomes: API requests for `Zaryab03/construction_management_suite` and `khamad99/erpnext_contracting_app` returned 404 during the session. Those results establish only that these requests did not retrieve public content then; no definitive reason was established.

**Snapshot drift warning:** Upstream repositories may have changed after 2026-09-16. Any evaluation must re-verify the snapshot at kickoff and pin exact commits before testing (see RSK-11).

## 9. Recommended architecture and selection paths

### Path A — Controlled customization

Proposed starting architecture:

| Layer | Proposed responsibility | Acceptance condition |
| --- | --- | --- |
| Frappe + ERPNext v16 | Accounting, procurement, stock, and core project records | Supported, reproducible dependency set |
| BuildSuite Core | Construction operations within verified scope | Passing install, lifecycle tests, and user scenarios |
| Separate custom application | Missing client billing, retention, advance recovery, required change workflows | Explicit specification and financial reconciliation |
| HRMS if required | HR/payroll and labor-cost integration | End-to-end labor posting demonstrated |
| Country-specific localization | Required documents and integrations | Country-specific acceptance evidence |

This is a proposed implementation, not a bundle already available in this form. Maintain clear ownership of project, BOQ, cost-code, and billing records. Do not install overlapping construction apps together without a conflict and data-ownership design. Governance rules for the custom application are specified in Section 13.

### Path B — Vendor-delivered BuildX implementation

Ask Quantbit to demonstrate the exact version and modules to be supplied, including how any private or external components differ from public repositories. Include source access, licenses, self-hosting requirements, support, upgrade ownership, and acceptance obligations in the delivery scope. The structured questionnaire in Section 12 operationalizes this.

Do not assume ProcureX forecasting, Budget Pro, or mobile offline behavior works merely because it is described. The public mobile repository exists and documents field functions, but we did not build it or verify offline synchronization. [S36]

### Path C — Ready-made software with no development allowance

No candidate was proven to satisfy this condition. Obtain a live, transaction-based demonstration and a trial installation before selecting. If neither leading candidate passes, reopen the search rather than lowering the acceptance standard to match a feature list.

### Path D — Continue in-house development (added in v1.2)

The v1.2 answers reveal an existing in-house v16 construction app and an AI-assisted solo development model. Under this path the in-house app remains the product, and the third-party candidates in this report are used as:

- **Reference implementations.** Study BuildSuite's subcontractor billing controller and tests [S04, S06] and BuildX's RA/contractor billing controllers [S10, S11] when specifying the in-house billing engine. Both are MIT-detected, which permits learning from, copying, and modifying their code with attribution (Section 14.2).
- **Negotiation scope.** If speed is required, Path B vendor engagement remains available, now with the resale-rights requirement stated up front (VD-17).

Constraints: do not co-install BuildSuite or BuildX with the in-house app without resolving BOQ and project-record ownership (RSK-12); design billing rules as per-contract configuration for the Egyptian market (Q-06); keep the client-billing phase-2 deferral an explicit, documented scope decision (Q-03); and apply the governance rules in Section 13 to all AI-assisted code.

## 10. Evaluation roadmap and decision gates

This section is a process proposal added in v1.1. Durations are deliberately not estimated: they depend on the answers to Q-01 to Q-12 and on resource availability. No cost estimate or delivery schedule should be inferred from this report.

### 10.1 Phases

| Phase | Objective | Key activities | Exit gate |
| --- | --- | --- | --- |
| **P0 — Scope confirmation** | Convert unknowns into signed scope | Answer Q-01 to Q-12; decide D-01 to D-04; choose Path A/B/C; appoint acceptance owners | G-0 |
| **P1 — Technical sandbox evaluation** | Prove the candidate(s) install and run reproducibly | AT-01, AT-02; run vendor test suites; resolve F-03; pin the bill of materials (F-04); re-verify snapshot (RSK-11) | G-1 |
| **P2 — Functional and financial acceptance** | Prove the construction-finance lifecycle on test data | AT-03 to AT-11; vendor questionnaire responses (Section 12) evaluated in parallel for Path B; finance owner approves posting rules | G-2 |
| **P3 — Pilot and cutover rehearsal** | Prove organizational readiness | AT-12, AT-13, AT-14; migration rehearsal (Section 14.3); training; support model confirmed | G-3 |
| **P4 — Go-live and hypercare** | Operate under observation | Monitored production use; issue triage; benefits review against the acceptance evidence | — |

**Demo track (added in v1.2):** Because the immediate objective is presenting to prospective owners (Q-05) rather than internal go-live, run a demo-readiness track in parallel with P1–P2: a scripted end-to-end scenario (Q-09) on Egyptian demo data with Arabic layouts (Q-01, Q-07), deployed to the Frappe Cloud instance (Q-02). Present only implemented features; label roadmap items explicitly (RSK-15). The formal gates still apply before any owner's production use.

### 10.2 Decision gates

| Gate | Question answered | Minimum evidence to pass |
| --- | --- | --- |
| **G-0** | Is the scope known and a path chosen? | Q-01 to Q-12 answered and signed; D-01 to D-04 decided; sandbox authorized |
| **G-1** | Can the candidate be installed and operated reproducibly? | AT-01 and AT-02 pass; CI/build evidence obtained; bill of materials pinned; shortlist of one foundation plus a written gap list |
| **G-2** | Does the solution pass functional and financial acceptance? | AT-03 to AT-11 pass, or failures have accepted, funded workarounds; risk register (Section 11) updated; vendor questionnaire complete for Path B |
| **G-3** | Is the organization ready to run it? | AT-12 to AT-14 pass; migration and rollback rehearsed; support and maintenance ownership assigned (Q-12) |

A failed gate means: fix and retest, change path, or stop. Do not average a failed gate into a score.

### 10.3 Evaluation RACI

R = Responsible, A = Accountable, C = Consulted, I = Informed. Assign names at G-0.

| Activity | Project owner | Project manager | Finance owner | QS lead | IT lead | Vendor / partner | Independent reviewer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Scope confirmation (Q-01 to Q-12) | A | R | C | C | C | I | I |
| Sandbox setup and AT-01/AT-02 | I | A | I | I | R | C | I |
| Billing and ledger tests (AT-03 to AT-06) | I | A | R | R | C | C | I |
| Permissions and security (AT-09) | I | A | C | I | R | C | C |
| Vendor due diligence (Section 12) | A | R | C | C | C | R | I |
| Posting-rule approval | I | C | A/R | C | I | I | I |
| Gate decisions G-0 to G-3 | A | R | C | C | C | I | C |
| Final selection and contract | A | R | C | C | C | I | C |

## 11. Risk register

This register consolidates the risk implications of the findings. Likelihood and impact are qualitative (Low / Medium / High) and assume no mitigation is applied yet. Owners are assigned at Gate G-0.

| ID | Risk | Source | Likelihood | Impact | Mitigation | Linked tests | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RSK-01 | Client progress billing unavailable at go-live, forcing manual workarounds | F-01 | High (Path A without custom dev) | High | Fund the custom billing module, or select a path with proven client billing | AT-03, AT-04 | Open |
| RSK-02 | Subcontractor billing behaves incorrectly in production (cumulative, advances, cancellation) | F-02, F-05 | Medium | High | Run vendor test suites, then full lifecycle reconciliation on a test site | AT-05, AT-06 | Open |
| RSK-03 | Foundation build/test instability blocks delivery | F-03 | Medium | High | Obtain CI failure cause and a passing reproducible run before contracting | AT-01 | Open |
| RSK-04 | Runtime/version mismatch and future upgrade lock-in | F-04 | Medium | Medium | Pin an exact bill of materials; rehearse upgrades and rollback | AT-01, AT-12 | Open |
| RSK-05 | Certification workflow gaps in BuildX require unplanned development | F-05, F-06 | Medium | High | Vendor demonstration plus behavior-based tests for the delivered process | AT-03, AT-04 | Open |
| RSK-06 | Analytics and dashboards misrepresent live financial position | F-07, F-08, F-09 | High (for inspected screens) | Medium | Trace every required metric to a live endpoint before acceptance | AT-10 | Open |
| RSK-07 | Financial data leaves the controlled environment via external redirect | F-08 | Medium | High | Identify the external service; block or self-host; review network egress and data residency (Q-11) | AT-10 | Open |
| RSK-08 | Retention and advance recovery posted to wrong accounts, misstating the ledger | F-10 | Medium | High | Finance-approved posting rules; reconciled test cycles before go-live | AT-03, AT-04, AT-06 | Open |
| RSK-09 | Localization or e-invoicing non-compliance in the operating country | F-11 | Medium | High | Validate the actual country integration end-to-end; obtain sample accepted documents | AT-11 | Open |
| RSK-10 | Chosen component is abandoned or commercially changed | F-12, Section 8 | Medium | Medium | Prefer actively maintained components; contractual support; documented exit plan (VD-16) | — | Open |
| RSK-11 | Upstream changes after 2026-09-16 invalidate snapshot conclusions | Section 8 | High over time | Medium | Re-verify repositories at evaluation kickoff; pin commits; re-run affected checks | AT-01 | Open |
| RSK-12 | Overlapping construction apps conflict over the same records | Section 9 | Medium | High | Single-owner data design; never co-install overlapping apps without a conflict analysis | AT-01 | Open |
| RSK-13 | Purchased or adopted component lacks modification/resale rights, blocking the business model | Q-04, Section 14.2 | Medium | High | Verify the license per component before adoption; require explicit resale/white-label terms in any purchase (VD-17); prefer MIT-detected components | VD-05, VD-17 | Open |
| RSK-14 | Single-maintainer continuity: the product depends on one developer with AI assistance | Q-12 | Medium | High | Enforce Section 13 governance (tests, CI, documentation, runbooks); keep the pinned bill of materials; obtain independent review of billing logic | AT-01, AT-12 | Open |
| RSK-15 | Demo promises exceed delivered functionality, creating commitments to owners | Q-05, Q-10 | Medium | Medium | Script demos only from implemented features; label roadmap items explicitly; record owner commitments in writing | — | Open |
| RSK-16 | MENA expansion requirements discovered late (multi-country tax, e-invoicing, languages) | Q-01 | Medium | Medium | Design localization as a per-country layer from the start; validate Egypt first (AT-11), then template a country-onboarding checklist | AT-11 | Open |

Review this register at every gate. Add new risks found during testing with the next available RSK number.

## 12. Vendor due-diligence questionnaire

Send this questionnaire to Quantbit (Path B) and adapt it for any other vendor. Require answers in writing, with evidence links, before Gate G-2. Marketing material is not an acceptable answer.

### 12.1 Delivery scope

| ID | Question |
| --- | --- |
| VD-01 | Which exact repositories, branches, and commits will be delivered? How do they differ from the public repositories inspected here (Section 8)? |
| VD-02 | Provide a complete module list with per-module status: generally available, beta, custom, or third-party. |
| VD-03 | Which components are hosted outside the buyer's environment (for example the Budget Pro destination in F-08), why, and under what data terms? |

### 12.2 Source and licensing

| ID | Question |
| --- | --- |
| VD-04 | What source access is included, including any private repositories? Is source escrow available? |
| VD-05 | What are the license terms per component and per third-party dependency? Confirm the right to modify and self-host (see Section 14.2). |

### 12.3 Technical verification

| ID | Question |
| --- | --- |
| VD-06 | Provide reference installations (contacts), their Frappe/ERPNext versions, and how long they have run in production. |
| VD-07 | Demonstrate client and subcontractor billing end-to-end on our test data, matching AT-03 to AT-06, including retention, advance recovery, cancellation, and amendment. |
| VD-08 | Demonstrate live cash-flow forecasting and budget reporting (AT-10). Explain the static figures and external redirect found in F-07 and F-08. |
| VD-09 | Provide mobile app build instructions, the offline synchronization design, and the supported device matrix (relevant if Q-08 requires it). |
| VD-10 | Provide the test suite and CI status. What is the automated coverage of billing, certification, and cancellation paths (see F-06)? |
| VD-11 | What is the upgrade and migration policy across Frappe/ERPNext versions, and who performs it? |
| VD-12 | Describe integration points: hooks, REST/RPC APIs, webhooks, and the approach to country e-invoicing and localization (Q-01). |

### 12.4 Commercial and support

| ID | Question |
| --- | --- |
| VD-13 | Describe the implementation methodology, required roles on both sides, and the main duration drivers. |
| VD-14 | What support service levels are offered: channels, hours, response and resolution targets, and escalation? |
| VD-15 | What training, documentation, and handover are included for administrators and key users? |
| VD-16 | What are the exit terms: full data export formats, decommissioning, and ownership of customizations developed during the engagement? |
| VD-17 | Do the terms grant the buyer the right to modify the delivered code and to resell it, white-labeled, to the buyer's own customers (Q-04)? Cover attribution obligations, trademark/branding use, per-site or per-customer pricing, and whether resale rights survive contract termination. |

## 13. Custom development governance for Path A

These rules apply to the separate custom application proposed in Path A (client billing, retention, advance recovery, change workflows). They are conditions for accepting Path A, not optional improvements.

1. **Separate application, no forks.** Build the missing functionality in its own Frappe app repository. Do not fork ERPNext, Frappe, or BuildSuite Core; integrate through documented extension points (hooks, overrides, custom DocTypes).
2. **Pinned bill of materials.** Record exact Frappe, ERPNext, BuildSuite, Python, Node, and database revisions in the repository (resolves F-04). Reproduce the environment from this file alone.
3. **Automated tests and CI.** Every billing rule has automated tests, including the AT-03 and AT-04 scenarios and the illustrative billing fixture in Section 15. CI must pass on every merge; a failing pipeline blocks release (learns from F-03).
4. **Finance-approved posting rules.** The finance owner signs the account mapping for gross certified work, retention receivable, advance recovery, taxes, and reversals before development starts (learns from F-10).
5. **Data-ownership map.** One document declares which app owns projects, BOQ, cost codes, measurement records, and billing documents. No second construction app may create or mutate those records (mitigates RSK-12).
6. **Naming and collision control.** Prefix custom DocTypes, fields, and endpoints; check for collisions with BuildSuite and ERPNext before each release.
7. **Bug-for-bug upgrade discipline.** Test each new Frappe/ERPNext/BuildSuite release in staging against the full acceptance suite before production upgrade (AT-12).
8. **Code review and security.** All changes reviewed by a second developer; parameterized SQL only; no secrets in the repository; permission rules reviewed against AT-09.
9. **Documentation.** Posting rules, configuration, and operational runbooks are maintained in the repository alongside the code.
10. **Change control.** Scope changes enter through a written variation request with impact on tests and schedule; releases are tagged.

## 14. Cross-cutting considerations

### 14.1 Security and permissions

- Enforce role- and territory-based access; verify through UI and API, not only the desk (AT-09).
- Treat the external Budget Pro redirect (F-08) as a potential data-egress path until the vendor explains it; review outbound network rules and authentication to any external service (RSK-07).
- Manage API tokens and integration credentials in a secrets store; never in repositories.
- Enable and retain audit trails for billing, certification, and cancellation documents.

### 14.2 Licensing

- BuildSuite Core, Quantbit Construction, ProcurexBundle, and ProcureX-Backend were detected as MIT; `civil_contracting` as GPL-2.0; CMS claims MIT in its README without API detection; ProcureX frontend had no detected license (Section 8).
- A bundle's license label does not settle the licenses of its dependencies or of externally hosted components (F-09). Commercial modules advertised separately (S35) are not covered by an open-source label.
- GPL-2.0 components carry copyleft obligations; avoid mixing them into a proprietary delivery without legal review.
- Obtain a per-component license inventory (VD-05) and a legal review before contract signature.

**Resale and white-label rights (decision-critical per Q-04, added v1.2):**

- MIT-detected components (BuildSuite Core, Quantbit BuildX, ProcurexBundle, ProcureX-Backend) permit modification, commercial use, and resale, provided copyright and license notices are preserved. No purchase is required to obtain these rights; paying such vendors buys support, completeness, or private modules — not rights already granted.
- GPL-2.0 (`civil_contracting`) permits modification and sale, but derivative works distributed to customers must remain GPL-2.0 with source availability — incompatible with a proprietary per-customer product model.
- Commercial marketplace apps and separately sold vendor modules (S35) typically license per site and prohibit resale; assume no resale rights unless a contract explicitly grants them (VD-17).
- License rights do not include trademark rights: do not market a resold product under the original vendor's name or branding.
- Record the final license position per adopted component in the repository and have it reviewed before the first commercial sale.

### 14.3 Data migration and cutover

- Identify opening-state data early: work-in-progress balances, certified-but-unbilled amounts, retention receivable, client and subcontractor advances, open purchase orders, and approved BOQs.
- Reconcile every migrated opening balance to the legacy system's totals before cutover; the finance owner signs the reconciliation.
- Define a freeze window, a cutover runbook, and a tested rollback path (rehearsed in AT-12).
- Decide whether historical certificates are migrated as documents or as opening balances only; do not mix the two approaches for the same project.

**v1.2 note:** The developer's own start has no historical data (Q-07), so migration is not a near-term task. This section remains a product requirement: future owner customers will arrive with legacy data, and a repeatable migration and cutover capability is part of what will be sold.

### 14.4 Environments and release management

- Maintain separate development, staging, and production environments; only staging and production receive the pinned bill of materials.
- Every release candidate passes the full acceptance suite in staging before production deployment.
- Schedule upgrades in agreed windows with a rehearsed restore procedure (AT-12).

### 14.5 Performance and scale

- Size the sandbox to the volumes in Q-05 (companies, sites, projects, users, BOQ lines, monthly certificates).
- Run AT-14 with realistic data volumes before Gate G-3; slow BOQ trees, ledger reports, or dashboard queries are acceptance failures, not cosmetic issues.

### 14.6 Evidence and audit discipline

- Retain every acceptance-test record (Section 15 template), including ledger extracts, for the life of the system.
- Record gate decisions and their evidence in the review log (Section 18).
- Keep this report's finding IDs stable in all future correspondence so reviewers can trace decisions to evidence.

## 15. Proposed acceptance tests

These are future work, not tests completed in this session. The **Verifies** column links each test to the findings and risks it would close.

| ID | Scenario | Evidence to capture | Verifies |
| --- | --- | --- | --- |
| AT-01 | Clean install, migrate, build, restart, and role setup | Versions, logs, dependencies, missing fixtures/errors | F-03, F-04, RSK-03, RSK-04, RSK-11, RSK-12 |
| AT-02 | BOQ import, approval, revision, and variation order | Original/revised quantities, approvals, linked budget changes | Scope baseline for all later tests |
| AT-03 | Two consecutive client progress certificates | Previous/current/cumulative quantities; no repeated billing | F-01, F-05, F-06, F-10, RSK-01, RSK-05, RSK-08 |
| AT-04 | Client retention and advance recovery | Gross work, deductions, receivable and retained/advance balances | F-01, F-05, F-10, RSK-01, RSK-08 |
| AT-05 | Subcontract order → measurement → bill → partial payment | Linked operational documents, invoice, ledger, and outstanding | F-02, F-05, RSK-02 |
| AT-06 | Cancel/amend a bill with and without payment | Correct blocking/reversal; no duplicate invoice or orphan entry | F-02, F-05, F-10, RSK-02, RSK-08 |
| AT-07 | Material request → order → receipt → site issue/return | Commitment, stock value, actual project cost, and no double counting | Cost-control baseline |
| AT-08 | Labor/equipment usage and cost allocation | Source record to project cost, corrections, and payroll separation | Cost-control baseline |
| AT-09 | Multi-company/project permissions | Site user cannot access unauthorized records through UI or API | Security baseline, RSK-07 (partially) |
| AT-10 | Live budget and cash-flow reporting | Changes in underlying transactions produce explained changes | F-07, F-08, F-09, RSK-06, RSK-07 |
| AT-11 | Arabic forms and local integrations | Approved sample outputs and required integration responses | F-11, RSK-09, RSK-16 |
| AT-12 | Upgrade and restore rehearsal | Preserved customizations, migrated data, successful rollback/restore | F-04, RSK-04 |
| AT-13 | Mobile field capture and offline synchronization (conditional on Q-08) | Queued offline entries sync once, in order, without duplicates after reconnection | Q-08, S36 claims |
| AT-14 | Performance under realistic volume (sized by Q-05) | Response times for BOQ trees, billing runs, and ledger reports under agreed data volumes | Q-05, Section 14.5 |

**v1.2 scoping:** AT-11's first concrete target is Egypt — Arabic layouts and Egyptian Tax Authority (ETA) e-invoicing integration — with other MENA countries added later through the same test pattern (Q-01). AT-13 is deferred per Q-08 and runs only when mobile enters scope.

**Illustrative billing fixture:** Start with 100,000 currency units of certified work, 5,000 retention, and 10,000 advance recovery; expected net cash due is 85,000 before taxes and other adjustments. The application must retain the separate quantities and amounts. The finance owner must approve actual posting rules and the applicable tax basis; this fixture is not jurisdiction-specific accounting guidance.

For every scenario, record the application commit, input data, expected result, actual result, screenshots/exported documents, relevant ledger records, and pass/fail decision. Use this record template:

```text
Test ID:
Date / tester / environment (app commits and bill of materials):
Preconditions and input data:
Steps executed:
Expected result:
Actual result:
Evidence (screenshots, exported documents, ledger references):
Decision: Pass / Fail / Conditional pass (state condition)
Linked findings and risks:
```

## 16. Manager decisions and open questions

| ID | Question | Answer / owner |
| --- | --- | --- |
| Q-01 | What is the operating country, and which local integrations are mandatory? | **Answered 2026-09-17 (owner):** Egypt first; wider MENA later. |
| Q-02 | Is ERPNext already installed? Which versions and hosting model? | **Answered:** ERPNext v16 on a local Bench and on Frappe Cloud; an in-house construction app is in development but needs significant time to complete and to present to owners. |
| Q-03 | Is client cumulative billing mandatory at initial go-live? | **Answered:** Not mandatory initially; may be deferred to phase 2 or developed with AI assistance into the current app. |
| Q-04 | Is funded customization acceptable, or must the product work out of the box? | **Answered:** Default is AI-assisted in-house development; buying a ready app is acceptable only with rights to modify and resell to owners. |
| Q-05 | How many companies, sites, projects, users, and subcontractors are involved? | **Answered:** None yet — pre-sales stage; preparing to present to prospective owners. |
| Q-06 | Which retention, advance, approval, variation, and certification rules apply? | **Answered:** Egyptian market practice; rules differ per contract and must be configurable per contract. |
| Q-07 | What Arabic layouts, imports, historical data, and reports are essential? | **Answered:** No historical data; fresh start. |
| Q-08 | Are offline mobile operations required? Which devices and connectivity conditions? | **Answered:** Not required now; possibly later. |
| Q-09 | Who owns acceptance: finance, QS, project management, IT, and management? | **Answered:** All of them — the product must work end-to-end across all these roles. |
| Q-10 | What are the rollout deadline, implementation budget, and support expectations? | **Answered:** No fixed external deadline or budget; development proceeds with AI-agent assistance. |
| Q-11 | What data-residency, backup, and disaster-recovery requirements apply? | **Open:** Not yet decided; resolve when choosing the hosting model for owner deployments (Frappe Cloud vs self-hosted Bench). |
| Q-12 | Who will administer and maintain the system, including any custom code, after go-live? | **Answered:** The owner/developer personally, with AI-agent assistance. |

No cost estimate or delivery schedule should be inferred from this report.

### 16.1 Implications of the answered scope (v1.2)

| Answer | Consequence for this report |
| --- | --- |
| Q-01 Egypt first, MENA later | AT-11 targets Egyptian Arabic layouts and Egyptian Tax Authority (ETA) e-invoicing first; design localization as a per-country layer from the start (RSK-16) |
| Q-02 v16 on local Bench + Frappe Cloud; in-house app exists | Compatibility target confirmed (v16). The decision is now explicitly build vs adopt vs buy (D-05, Path D). Co-installing BuildSuite/BuildX with the in-house app triggers RSK-12 (BOQ/project-record ownership) |
| Q-03 Client billing deferrable or AI-built | Lowers the immediate weight of F-01 for a demo, but the gap must be closed before any owner's production billing; the phase-2 deferral must be a documented scope decision |
| Q-04 Buy only with edit + resale rights | Licensing becomes a gating criterion (RSK-13); MIT-detected candidates already grant these rights (Section 14.2); commercial apps need explicit contractual rights (VD-17) |
| Q-05 Pre-sales, no owners yet | The near-term deliverable is a demo environment, not production; the formal gates apply per owner engagement later (RSK-15) |
| Q-06 Egypt rules, varying per contract | The billing engine must parameterize retention percentage and cap, advance recovery method, approval chain, and certificate format per contract; never hard-code them (reinforces Section 13 rule 4) |
| Q-07 Fresh start | Section 14.3 migration is not a near-term task; it remains a product requirement for future owner onboarding |
| Q-08 Mobile later | AT-13 deferred; mobile is excluded from demo scope |
| Q-09 End-to-end across all roles | The demo script must cover the full cycle: BOQ → procurement → measurement → billing → ledger → reports |
| Q-10 AI-assisted development, no fixed deadline | Section 13 governance (tests, CI, documentation) is the main quality control; schedule pressure must not skip AT-03/AT-04 before any real billing |
| Q-11 Undecided | Keep open; affects owner-deployment hosting offers and the RSK-07 data-egress review |
| Q-12 Self-maintained with AI assistance | RSK-14 single-maintainer risk; documentation and automated tests are mandatory, not optional |

## 17. Independent AI-agent review brief

Use the following as a review request. It is intended for evidence-based critique, not automatic agreement with this report.

```text
Review ERP-CONSTRUCTION-REVIEW-001 (v1.2) independently.

1. Treat this report as a hypothesis with cited evidence, not authoritative truth.
2. Verify findings F-01 through F-12. Record repository, commit, file path,
   retrieval date, and the evidence supporting each verdict.
3. Distinguish the historical snapshot from current upstream changes.
4. Label every verdict: Confirmed, Partially confirmed, Contradicted,
   Outdated, or Insufficient evidence.
5. Search beyond the cited file before concluding functionality is absent.
   Logic may live in hooks, server scripts, fixtures, other apps, or services.
6. Distinguish static data used for initialization from data permanently shown
   without a live connection. Trace the complete data path where relevant.
7. Do not equate documentation, license labels, test filenames, or passing
   lint with working financial integration or production readiness.
8. Review gross billing, retention, advance recovery, tax handling,
   duplicate prevention, cancellation, amendment, and permission boundaries.
9. Challenge the preference for BuildSuite versus BuildX. Explain what
   evidence would reverse the recommendation and identify stronger alternatives.
10. Review the business requirements Q-01 through Q-12 and their recorded answers (Section 16, v1.2) before final selection; challenge the implications drawn in Section 16.1.
11. Do not run code from these repositories on a production system.
    If a sandbox evaluation is authorized, report actual commands and results.
12. Add comments using the review log below. Preserve the original finding
    IDs and distinguish factual corrections from preferences or proposals.
13. Sections 10-14 and Annexes A-B were added in v1.1 as process proposals,
    not evidence. Challenge their assumptions, completeness, and consistency
    with the findings.
14. Re-check upstream repositories for changes after 2026-09-16 before
    relying on any finding, and flag material differences.

Return: an executive verdict; a finding-by-finding review; any new blockers;
an updated shortlist; and a prioritized acceptance plan with evidence links.
```

## 18. Review and comment log

Copy rows as needed. Use finding IDs and source IDs instead of line numbers, which may change during editing.

| Comment ID | Reviewer / date | Finding or section | Verdict | Comment and supporting evidence | Proposed action | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-001 | Pending | Executive recommendation | Pending | — | — | — | Open |
| R-002 | Pending | F-01 to F-04: BuildSuite | Pending | — | — | — | Open |
| R-003 | Pending | F-05 to F-09: Quantbit/ProcureX | Pending | — | — | — | Open |
| R-004 | Pending | F-10 to F-12: alternatives | Pending | — | — | — | Open |
| R-005 | Pending | Business scope and acceptance | Pending | — | — | — | Open |
| R-006 | Pending | v1.1 process additions (Sections 10–14, Annexes A–B) | Pending | — | — | — | Open |
| R-007 | Pending | v1.2 business-scope answers and implications (Sections 1.2, 9 Path D, 16.1) | Pending | — | — | — | Open |
| R-008 | Independent AI review / 2026-09-17 | F-01 to F-12 (all findings) | Confirmed | All twelve findings reproduced against raw source (raw.githubusercontent.com) and the GitHub API on 2026-09-17. No finding contradicted or outdated (drift window ~1 day; no material upstream change). | Add new observations R-009 to R-014 | Reviewer | Closed |
| R-009 | Independent AI review / 2026-09-17 | F-04 (BuildSuite runtime) | Confirmed (strengthened) | BuildSuite README "Requirements" states Python 3.11+ while pyproject.toml declares requires-python ">=3.14"; an installer following the README can hit a resolver error. | Treat pyproject.toml as authoritative; correct the README or pin the runtime before install | Publisher / IT | Open |
| R-010 | Independent AI review / 2026-09-17 | F-05, F-09 (BuildX billing) | Confirmed + nuance | RA Billing `create_sales_invoice` maps `grand_total` to a single qty=1 line with no retention or advance-recovery deduction; Contractor Billing `create_payment_entry` hardcodes `paid_to_account_currency="INR"`. | Verify client retention/advance handling before any Egypt go-live; remove the INR hardcode | Vendor / QS | Open |
| R-011 | Independent AI review / 2026-09-17 | §9 Path A, capability matrix | New observation | BuildSuite Core ships a Vue SPA frontend (repo language "Vue"; README: "grow from the Vue app into full Desk accounting"). Path A treats it as a pure Frappe app. | Add the Vue frontend to build/packaging and to the RSK-12 overlap analysis | IT lead | Open |
| R-012 | Independent AI review / 2026-09-17 | F-09, RSK-13, §14.2 | New blocker | The ProcureX frontend repo has no license (API license = null). Unlicensed code cannot be safely copied or resold under Q-04. | Exclude the ProcureX frontend from reuse until a license is declared; re-verify before any adoption | Reviewer / owner | Open |
| R-013 | Independent AI review / 2026-09-17 | F-02, §9 preference | Positive evidence | BuildSuite's subcontract retention treatment is well-designed: the generated PI posts expense at full value and reduces payable via a "Deduct" tax row (test `test_submit_generates_pi_against_the_supplier`). | Cite as supporting evidence for BuildSuite as the billing reference | Reviewer | Closed |
| R-014 | Independent AI review / 2026-09-17 | F-09 (ProcureX packaging) | Confirmed + nuance | ProcurexBundle pyproject requires-python ">=3.10"; ProcureX-Backend requires ">=3.14" — inconsistent bundle vs backend runtime floor. | Resolve the runtime floor before any install | Vendor / IT | Open |

Optional longer comment format:

```markdown
### R-008 — Short title

- Reviewer/date:
- Related finding/source:
- Verdict:
- Evidence URL and commit:
- Observation:
- Business consequence:
- Proposed correction or action:
- Owner and due date:
- Resolution:
```

## 19. Source register

Sources were consulted during the current session. Branch links are mutable. Source-code links are supplied even where inspection succeeded through the raw-file/API route rather than the web page reader.

### BuildSuite and Frappe runtime

- **S01:** [BuildSuite Core repository and README](https://github.com/BuildSuite-io/buildsuite_core) — scope, Beta status, exclusions, installation, license statement.
- **S02:** [BuildSuite platform page](https://www.buildsuite.io/platform.html) — platform positioning and illustrative stack; not treated as proof all modules ship in Core.
- **S03:** [BuildSuite package metadata](https://github.com/BuildSuite-io/buildsuite_core/blob/develop/pyproject.toml) — Python and Frappe compatibility.
- **S04:** [Subcontractor bill tests](https://github.com/BuildSuite-io/buildsuite_core/blob/develop/buildsuite_core/tests/test_subcontractor_bill.py) — selected behavioral tests inspected, not executed.
- **S05:** [Inspected CI run](https://github.com/BuildSuite-io/buildsuite_core/actions/runs/35095537194) — failed status, cause not established from available job details.
- **S06:** [Subcontractor bill controller](https://github.com/BuildSuite-io/buildsuite_core/blob/develop/buildsuite_core/buildsuite_core/doctype/subcontractor_bill/subcontractor_bill.py) — submission and cancellation integration.
- **S29:** [Frappe installation guide](https://docs.frappe.io/framework/user/en/installation) — v16/develop runtime table observed during the session.
- **S30:** [BuildSuite CI configuration](https://github.com/BuildSuite-io/buildsuite_core/blob/develop/.github/workflows/ci.yml) — declared build/test workflow.
- **S31:** [BuildSuite package initializer](https://github.com/BuildSuite-io/buildsuite_core/blob/develop/buildsuite_core/__init__.py) — internal version string.
- **S32:** [BuildSuite tags](https://github.com/BuildSuite-io/buildsuite_core/tags) — tag inventory also checked through GitHub API.
- **S35:** [BuildSuite Frappe Incubator entry](https://frappe.io/incubator/project/BuildSuite) — distinguishes core scope from planned separate commercial capabilities.

### Quantbit BuildX and ProcureX

- **S07:** [Quantbit Construction Management repository](https://github.com/QuantbitERP/Quantbit-Construction-Management) — public application and associated repositories.
- **S08:** [Functional application process](https://github.com/QuantbitERP/Quantbit-Construction-Management/blob/main/docs/functional-application-process.md) — publisher's scope description.
- **S09:** [Construction app package metadata](https://github.com/QuantbitERP/Quantbit-Construction-Management/blob/main/pyproject.toml) — declared Frappe v16 range.
- **S10:** [RA Billing controller](https://github.com/QuantbitERP/Quantbit-Construction-Management/blob/main/quantbit_construction_management/subcontractor_management/doctype/ra_billing/ra_billing.py) — Sales Invoice mapping.
- **S11:** [Contractor Billing controller](https://github.com/QuantbitERP/Quantbit-Construction-Management/blob/main/quantbit_construction_management/subcontractor_management/doctype/contractor_billing/contractor_billing.py) — invoice/journal/payment lifecycle paths.
- **S12:** [Progress Certificate controller](https://github.com/QuantbitERP/Quantbit-Construction-Management/blob/main/quantbit_construction_management/progress_measurement_%26_billing/doctype/progress_certificate/progress_certificate.py) — inspected scaffold. Adjacent JavaScript and JSON files were also read.
- **S13:** [Progress Certificate test](https://github.com/QuantbitERP/Quantbit-Construction-Management/blob/main/quantbit_construction_management/progress_measurement_%26_billing/doctype/progress_certificate/test_progress_certificate.py) — template test class.
- **S14:** [SC Payment Certificate controller](https://github.com/QuantbitERP/Quantbit-Construction-Management/blob/main/quantbit_construction_management/subcontractor_management/doctype/sc_payment_certificate/sc_payment_certificate.py) — numbering logic observed.
- **S15:** [ProcurexBundle README](https://github.com/QuantbitERP/ProcurexBundle/blob/main/README.md) — packaging and default repositories/branches.
- **S16:** [ProcurexBundle package metadata](https://github.com/QuantbitERP/ProcurexBundle/blob/main/pyproject.toml) — declared compatibility.
- **S17:** [Cash-flow forecasting screen](https://github.com/QuantbitERP/ProcureX/blob/main/src/routes/finance.cashflow-forecasting.lazy.tsx) — hard-coded forecast data.
- **S18:** [Budget Pro screen](https://github.com/QuantbitERP/ProcureX/blob/main/src/routes/finance.budget-pro.lazy.tsx) — fixed external redirect.
- **S19:** [ProcureX backend package metadata](https://github.com/QuantbitERP/ProcureX-Backend/blob/version-16/pyproject.toml) — Python requirement.
- **S33:** [Project 360 screen](https://github.com/QuantbitERP/ProcureX/blob/main/src/routes/project.project-360.lazy.tsx) — static initialization and fetch logic; full data lineage unverified.
- **S34:** [ProcureX backend API](https://github.com/QuantbitERP/ProcureX-Backend/blob/version-16/procurex/api.py) — selected endpoint inventory.
- **S36:** [BuildX mobile repository](https://github.com/QuantbitERP/construction-mgmt-sys-mobile) — public Flutter app; no build or offline test performed.
- **S37:** [BuildX product page](https://quantbit.io/products/buildx) — vendor claims, not independent proof.
- **S38:** [BuildX + ProcureX community announcement](https://discuss.frappe.io/t/buildx-procurex-open-source-erp-stack-for-construction-epc-presenting-at-frappeverse-mumbai/164265) — developer announcement and repository links.
- **S39:** [Technical application process](https://github.com/QuantbitERP/Quantbit-Construction-Management/blob/main/docs/technical-application-process.md) — documented modules, hooks, fixtures, and validation expectations.

### Other candidates

- **S20:** [EPCForge marketplace listing](https://cloud.frappe.io/marketplace/apps/epcforge) — declared supported version and feature scope.
- **S21:** [EPCForge repository](https://github.com/invento-software-limited/epcforge) — v16 branch and documentation.
- **S22:** [Construction Management Suite repository](https://github.com/cepho/construction_management_suite) — v15 requirements and feature claims.
- **S23:** [CMS Interim Payment Certificate controller](https://github.com/cepho/construction_management_suite/blob/master/construction_management_suite/progress_billing/doctype/interim_payment_certificate/interim_payment_certificate.py) — invoice generation and deductions.
- **S24:** [CMS Saudi localization file](https://github.com/cepho/construction_management_suite/blob/master/construction_management_suite/localization/ksa/overrides.py) — inspected tax/settings code.
- **S25:** [ProjectIT marketplace listing](https://cloud.frappe.io/marketplace/apps/projectit) — field functions, versions, and HRMS prerequisite.
- **S26:** [civil_contracting repository](https://github.com/revant/civil_contracting) — legacy scope; maintenance metadata checked via API.
- **S27:** [ERPNext-Construction-Module repository](https://github.com/amet123/ERPNext-Construction-Module) — README-only public tree observed.
- **S28:** [Construction ERP forum discussion](https://discuss.frappe.io/t/construction-erp/162956) — commercial-product clarification and community candidate links.
- **S40:** [CMS hooks](https://github.com/cepho/construction_management_suite/blob/master/construction_management_suite/hooks.py) — lifecycle registrations inspected.
- **S41:** [Quantbit Construction hooks](https://github.com/QuantbitERP/Quantbit-Construction-Management/blob/main/quantbit_construction_management/hooks.py) — integration registrations inspected.

### Context sources and additional leads

These sources informed context or discovery. They did not establish that any public candidate passed acceptance testing.

- **S42:** [Setting up ERPNext for a construction company](https://discuss.frappe.io/t/setting-up-erpnext-for-construction-company/137680) — original community reference.
- **S43:** [ERPNext for EPC](https://frappe.io/erpnext/for-EPC-engineering-contruction) — baseline platform capabilities and case-study links.
- **S44:** [ERPGulf solutions](https://app.erpgulf.com/en/solutions) — regional implementation/customization lead; no complete application audit performed.
- **S45:** [Afrotel Group case study](https://frappe.io/stories/Afrotel%20Group) — Egyptian contracting implementation reference; not proof of an installable candidate package.
- **S46:** [National Engineering Services and Trading case study](https://frappe.io/stories/National%20Engineering%20Services%20and%20Trading) — contextual implementation reference.
- **S47:** [Nael General Contracting case study](https://acubeinnovations.com/case-studies/nael-general-contracting/) — implementer's published experience; claims not independently validated here.

Searches also returned unrelated BOQ trackers, CRM/theme projects, and general contract-management material. These were excluded from the shortlist because they did not establish an integrated ERPNext construction application matching the objective.

## 20. Installation commands discussed in the session

The initial discussion included the following basic BuildSuite sequence from its repository. These commands were **not executed**. They assume an already compatible test Bench and are not a complete production deployment plan. [S01]

```bash
bench get-app https://github.com/BuildSuite-io/buildsuite_core
bench --site your-site install-app buildsuite_core
bench --site your-site migrate
bench build
```

The user-supplied initial sequence additionally mentioned requirements setup and restart. Their applicability depends on the hosting model and selected versions. Before running any installation, select a reviewed revision and dependencies; successful installation alone does not close the functional findings in this report.

## 21. Proposed next action and document history

**Next action:** Business-scope questions are answered (Section 16). Remaining Gate G-0 items are D-05 (product strategy: build, adopt, buy, or hybrid) and D-06 (demo scope and target date). Then execute the demo track (Section 10) and the P1 sandbox work before any owner commitment.

| Version | Date | Change | Approval |
| --- | --- | --- | --- |
| 1.0 | 2026-09-16 | Consolidated current-session research, corrections, evidence, and review workflow | Pending manager review |
| 1.1 | 2026-09-17 | Revised and enhanced: added contents, decisions requested (D-01 to D-04), capability matrix (5.1), finding status fields and traceability (6.1), evaluation roadmap and gates (10), risk register (11), vendor questionnaire (12), Path A governance (13), cross-cutting considerations (14), AT-13/AT-14 and test record template (15), Q-11/Q-12 (16), review-brief items 13–14 (17), glossary and scoring template (Annexes A–B). No changes to findings, sources, or evidence. | Pending manager review |
| 1.2 | 2026-09-17 | Recorded owner's answers to Q-01–Q-12; added business context (1.2), Path D (9), demo track (10), RSK-13–RSK-16 (11), VD-17 (12), resale-rights licensing analysis (14.2), migration note (14.3), AT scoping notes (15), implications analysis (16.1), D-05/D-06; updated next action. No changes to findings or sources. | Pending manager review |

**Decision record:** No purchase, deployment, vendor commitment, or production approval has been made in this session.

## Annex A. Glossary

| Term | Meaning in this report |
| --- | --- |
| **BOQ (Bill of Quantities)** | The priced list of work items, quantities, and rates that defines contract scope and the basis for measurement and billing |
| **WBS (Work Breakdown Structure)** | Hierarchical decomposition of a project used to organize BOQ, costs, and progress |
| **RA bill / progress billing** | Running-account billing: periodic cumulative invoicing of measured work to the client |
| **IPC (Interim Payment Certificate)** | A certified periodic payment document, typically issued by the consultant, authorizing payment for measured work |
| **Certification** | The approval step that converts measured quantities into amounts payable |
| **Retention** | A percentage withheld from each certificate as security, released later under contract conditions |
| **Advance recovery** | Scheduled deduction repaying a mobilization advance previously paid to the contractor (or paid to a subcontractor) |
| **Variation / change order** | An approved change to scope, quantities, or rates after contract award |
| **QS (Quantity Surveyor)** | The role responsible for measurement, valuation, and certification support |
| **EPC** | Engineering, Procurement, and Construction contract delivery model |
| **Frappe** | The Python/JS framework underneath ERPNext; apps install into a Frappe "Bench" |
| **ERPNext** | The open-source ERP application built on Frappe (accounting, stock, procurement, projects) |
| **Bench** | The Frappe command-line tool and directory layout that hosts sites and apps |
| **DocType** | Frappe's document/data model unit (roughly: a table plus its forms and controllers) |
| **HRMS** | Frappe's HR and payroll application, required by some field/time tools |
| **E-invoicing / ZATCA** | Mandatory electronic invoicing regimes; ZATCA is the Saudi authority referenced in CMS localization code |
| **CI** | Continuous integration: automated build/test runs on each change |
| **Bill of materials (software)** | The pinned list of application revisions and runtime versions for a reproducible deployment; distinct from a construction BOQ |
| **Sandbox** | A non-production environment used for evaluation and acceptance testing |
| **Cutover** | The planned transition from the legacy system to the new system, including opening balances |
| **Hypercare** | The heightened-support period immediately after go-live |
| **Gate (G-0…G-3)** | A formal decision point with defined entry evidence; failing a gate stops or redirects the project |

## Annex B. Weighted scoring template

Use this template during Phase P2 to compare the surviving candidate(s) after Gate G-1. It was not used for the research conclusions in this report.

**Rules:**

1. Adjust criteria and weights at Gate G-0 with the acceptance owners; weights must sum to 100.
2. Score each candidate 0–5 per criterion: 0 = absent, 1 = claimed but undemonstrated, 2 = partial with material gaps, 3 = working with accepted workarounds, 4 = working and tested, 5 = working, tested, and evidenced at our volumes.
3. Every score must cite evidence (AT records, review-log entries, or vendor questionnaire answers). A score without evidence is 1 at most.
4. Weighted score per criterion = weight × score ÷ 5. Total = sum of weighted scores (maximum 100).
5. A failed gate criterion (any acceptance test marked Fail without an accepted workaround) overrides the total score.

| Criterion | Default weight | Candidate A score (0–5) | Candidate A weighted | Candidate B score (0–5) | Candidate B weighted | Evidence reference |
| --- | --- | --- | --- | --- | --- | --- |
| Client and subcontractor progress billing, retention, advances | 20 | | | | | |
| Accounting integration and ledger reconciliation | 15 | | | | | |
| BOQ, estimation, WBS, and change control | 10 | | | | | |
| Procurement, stock, and project costing | 10 | | | | | |
| Compatibility, packaging, and reproducible installation | 10 | | | | | |
| Tests, maintenance, and vendor viability | 10 | | | | | |
| Site, labor, and equipment workflows | 8 | | | | | |
| Localization and language fit | 7 | | | | | |
| Reporting and analytics (live data) | 5 | | | | | |
| Security and permissions | 5 | | | | | |
| **Total** | **100** | — | | — | | — |
