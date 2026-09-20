# ERPNext Construction and Contracting: Research and Review Report

**Document ID:** ERP-CONSTRUCTION-REVIEW-001  
**Version:** 1.0 — management and independent AI review draft  
**Research date:** 16 September 2026  
**Language:** English; consolidates research originally discussed in Arabic  
**Status:** Research completed; no product selected for production  
**Audience:** Project owner, manager, implementation team, and independent reviewing AI agent

> This document consolidates the substantive work in the current conversation: the original candidate list, initial verification, expanded research, selected source-code inspection, changes in recommendation, unresolved questions, and a proposed evaluation process. It is a research handoff, not a verbatim chat transcript or a deployment certification.

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

No weighted scoring was used. Star counts, file counts, and commit volume were not treated as proof of quality.

**Unknown business requirements:** Country of operation; current ERPNext version and hosting model; project types and scale; number of companies and sites; required tax/e-invoicing integrations; Arabic document formats; rollout deadline; budget; and willingness to fund customization. The conversation did not establish these requirements.

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

## 6. Findings register

### F-01 — BuildSuite client billing gap

**Evidence:** Documented. **Decision impact:** High. **Confidence:** High about documented scope; runtime untested.

The README identifies client-facing RA/progress billing and client-side retention as outside the current release. Therefore, supplier/subcontractor billing support must not be interpreted as proof of a complete client billing cycle. [S01]

**Required resolution:** Demonstrate a delivered client billing module or budget for implementation and acceptance testing. Confirm the scope against a specific release or commit before contracting.

### F-02 — BuildSuite subcontractor implementation and tests

**Evidence:** Observed. **Decision impact:** High. **Confidence:** High about code presence; execution unverified.

The selected subcontractor controller generates a linked Purchase Invoice on submission and handles cancellation. Its test file includes substantive tests for invoice creation, idempotency, cumulative prior billing, payment/advance behavior, cancellation, amendment, and company/account consistency. These are positive engineering signals, not verified outcomes. [S04, S06]

**Required resolution:** Run the tests on the proposed dependency versions, then reconcile a complete subcontract lifecycle in an actual test site.

### F-03 — BuildSuite CI did not establish a passing build

**Evidence:** Observed. **Decision impact:** High. **Confidence:** High for recorded status; cause unknown.

The inspected CI run for commit `8be9c981a798d2c07c47a201044703d87c29e5af` was marked failed. The retrieved job record identified a failed Server job but supplied no step details. It is not justified to say the business tests themselves failed: execution infrastructure or setup could also be responsible. [S05]

**Required resolution:** Obtain the failure reason and a successful reproducible install/build/test run for the intended deployment revision.

### F-04 — Runtime and release information need reconciliation

**Evidence:** Observed/documented. **Decision impact:** Medium to high.

The Frappe installation guide listed Python 3.14, Node.js 24, and MariaDB 11.8 for its v16/develop column. BuildSuite package metadata required Python `>=3.14`; its inspected CI configuration also used those runtime generations. The earlier README environment description was less strict. [S03, S29, S30]

The BuildSuite website's illustrative stack included `v2.4`, while the inspected package initializer declared `0.0.1` and the tag query returned `release-0.1.0` plus `user-company`. These identifiers must not be treated as equivalent release guarantees. [S02, S31, S32]

**Required resolution:** Agree an exact bill of materials: Frappe/ERPNext/application revisions, Python/Node/database versions, migration procedure, and rollback plan. Do not choose a production release from a marketing example.

### F-05 — BuildX has real ERPNext billing integration

**Evidence:** Observed. **Decision impact:** High.

The inspected `RA Billing` controller includes a `create_sales_invoice` mapping. `Contractor Billing` includes Purchase Invoice/Journal Entry paths, payment-status handling, and cancellation-related logic. This establishes implementation beyond a feature list, but not correct handling of every retention, advance, tax, or cancellation scenario. [S10–S11]

**Required resolution:** Run both client and subcontractor cycles and verify the resulting financial documents. Check configuration, permissions, and cumulative measurement behavior separately.

### F-06 — Selected BuildX certificates/tests are scaffolding

**Evidence:** Observed. **Decision impact:** High for affected workflows.

`ProgressCertificate` contained a class with `pass`; its JavaScript file was a commented template, and its test class also contained `pass`. The inspected `SC Payment Certificate` controller primarily generated a certificate number. A form/schema can still store information without custom controller logic, so these observations do not prove the whole app is nonfunctional. They do mean that the inspected files do not demonstrate an automated certification/settlement cycle. [S12–S14]

**Required resolution:** Identify any logic elsewhere and demonstrate certification, deductions, approval, posting, and reversal. Replace template tests with behavior-based tests for the delivered process.

### F-07 — ProcureX cash-flow screen uses static figures

**Evidence:** Observed. **Decision impact:** High. **Confidence:** High for the inspected screen.

`finance.cashflow-forecasting.lazy.tsx` defines forecast periods, inflows, outflows, balances, and confidence labels directly in the component. The inspected screen does not retrieve those forecast values from company transactions. [S17]

**Required resolution:** Demonstrate live calculations using the buyer's test data. Changing an invoice, expected collection date, or supplier payment should cause explainable forecast changes. Do not accept the screen's appearance as evidence of implemented forecasting.

### F-08 — ProcureX Budget Pro redirects externally

**Evidence:** Observed. **Decision impact:** High for self-hosting and completeness.

`finance.budget-pro.lazy.tsx` redirects to a fixed `construction-management.quantcloud.in/budget_dashboard` address. That does not establish that Budget Pro is supplied as a local component of the buyer's installation. [S18]

**Required resolution:** Identify the destination module, its source/licensing, authentication, data source, and deployment dependencies. Demonstrate operation inside the proposed hosting arrangement.

### F-09 — ProcureX is a collection of separately inspectable components

**Evidence:** Observed/documented. **Decision impact:** Medium to high.

The bundle fetches a Frappe backend and builds a separate frontend. Its README defaults the backend to `version-16` and frontend to `main`. The backend package requires Python `>=3.14`. [S15–S16, S19]

Additional inspection found static initial data in the Project 360 frontend as well as API-fetch logic. That mixed implementation was not fully traced, so we did not conclude that every Project 360 metric is static. Backend API entry points included supplier/RFQ/quotation/order/invoice operations; a complete analytics audit was not performed. [S33–S34]

**Required resolution:** Trace each required dashboard metric to an actual endpoint/query. Review licensing per component; a bundle's MIT label must not be assumed to resolve every dependency's terms.

### F-10 — CMS invoice construction requires financial review

**Evidence:** Observed plus inference. **Decision impact:** High.

The inspected Interim Payment Certificate controller computes deductions and uses `net_payable_this_period` as the rate of a generated Sales Invoice line. That function did not separately allocate retention and advance recovery to their respective accounts. This is a risk requiring review, not a proven ledger error from a live execution. The function inserts a draft invoice rather than demonstrating a fully posted cycle. [S23]

**Required resolution:** Confirm gross certified work, retention, advance recovery, taxes, receivable, and invoice posting treatment in a running site. Inspect hooks and repeat submission/cancellation paths for unwanted duplicate side effects.

### F-11 — CMS regional claims exceed the evidence inspected

**Evidence:** Observed. **Decision impact:** High if local compliance is required.

The inspected Saudi localization file contains tax settings, a `zatca_enabled` flag, and amount-formatting functionality. These alone do not demonstrate an operational electronic-invoicing integration. No full regulatory or compliance assessment was performed. [S24]

**Required resolution:** Validate the required country's actual integration against its operational requirements. A flag, tax rate, or Arabic label is not an acceptance test.

### F-12 — Narrower and older alternatives do not close all gaps

**Evidence:** Documented/observed. **Decision impact:** Medium.

EPCForge deserves consideration for estimation, tendering, budgeting, and engineering document control. ProjectIT serves field tracking and time capture. Neither was established as the complete construction-finance solution sought here. [S20–S21, S25]

The `civil_contracting` repository's reported last push was 30 January 2022. This is a maintenance indicator, not proof of incompatibility. The public `ERPNext-Construction-Module` tree contained only a README; the related forum author described the solution as commercial at that time. [S26–S28]

**Required resolution:** Restrict evaluation to products whose delivery scope and current compatibility can be demonstrated.

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

This is a proposed implementation, not a bundle already available in this form. Maintain clear ownership of project, BOQ, cost-code, and billing records. Do not install overlapping construction apps together without a conflict and data-ownership design.

### Path B — Vendor-delivered BuildX implementation

Ask Quantbit to demonstrate the exact version and modules to be supplied, including how any private or external components differ from public repositories. Include source access, licenses, self-hosting requirements, support, upgrade ownership, and acceptance obligations in the delivery scope.

Do not assume ProcureX forecasting, Budget Pro, or mobile offline behavior works merely because it is described. The public mobile repository exists and documents field functions, but we did not build it or verify offline synchronization. [S36]

### Path C — Ready-made software with no development allowance

No candidate was proven to satisfy this condition. Obtain a live, transaction-based demonstration and a trial installation before selecting. If neither leading candidate passes, reopen the search rather than lowering the acceptance standard to match a feature list.

## 10. Proposed acceptance tests

These are future work, not tests completed in this session.

| ID | Scenario | Evidence to capture |
| --- | --- | --- |
| AT-01 | Clean install, migrate, build, restart, and role setup | Versions, logs, dependencies, missing fixtures/errors |
| AT-02 | BOQ import, approval, revision, and variation order | Original/revised quantities, approvals, linked budget changes |
| AT-03 | Two consecutive client progress certificates | Previous/current/cumulative quantities; no repeated billing |
| AT-04 | Client retention and advance recovery | Gross work, deductions, receivable and retained/advance balances |
| AT-05 | Subcontract order → measurement → bill → partial payment | Linked operational documents, invoice, ledger, and outstanding |
| AT-06 | Cancel/amend a bill with and without payment | Correct blocking/reversal; no duplicate invoice or orphan entry |
| AT-07 | Material request → order → receipt → site issue/return | Commitment, stock value, actual project cost, and no double counting |
| AT-08 | Labor/equipment usage and cost allocation | Source record to project cost, corrections, and payroll separation |
| AT-09 | Multi-company/project permissions | Site user cannot access unauthorized records through UI or API |
| AT-10 | Live budget and cash-flow reporting | Changes in underlying transactions produce explained changes |
| AT-11 | Arabic forms and local integrations | Approved sample outputs and required integration responses |
| AT-12 | Upgrade and restore rehearsal | Preserved customizations, migrated data, successful rollback/restore |

**Illustrative billing fixture:** Start with 100,000 currency units of certified work, 5,000 retention, and 10,000 advance recovery; expected net cash due is 85,000 before taxes and other adjustments. The application must retain the separate quantities and amounts. The finance owner must approve actual posting rules and the applicable tax basis; this fixture is not jurisdiction-specific accounting guidance.

For every scenario, record the application commit, input data, expected result, actual result, screenshots/exported documents, relevant ledger records, and pass/fail decision.

## 11. Manager decisions and open questions

| ID | Question | Answer / owner |
| --- | --- | --- |
| Q-01 | What is the operating country, and which local integrations are mandatory? | Pending |
| Q-02 | Is ERPNext already installed? Which versions and hosting model? | Pending |
| Q-03 | Is client cumulative billing mandatory at initial go-live? | Pending |
| Q-04 | Is funded customization acceptable, or must the product work out of the box? | Pending |
| Q-05 | How many companies, sites, projects, users, and subcontractors are involved? | Pending |
| Q-06 | Which retention, advance, approval, variation, and certification rules apply? | Pending |
| Q-07 | What Arabic layouts, imports, historical data, and reports are essential? | Pending |
| Q-08 | Are offline mobile operations required? Which devices and connectivity conditions? | Pending |
| Q-09 | Who owns acceptance: finance, QS, project management, IT, and management? | Pending |
| Q-10 | What are the rollout deadline, implementation budget, and support expectations? | Pending |

No cost estimate or delivery schedule should be inferred from this report.

## 12. Independent AI-agent review brief

Use the following as a review request. It is intended for evidence-based critique, not automatic agreement with this report.

```text
Review ERP-CONSTRUCTION-REVIEW-001 independently.

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
10. Review business requirements Q-01 through Q-10 before final selection.
11. Do not run code from these repositories on a production system.
    If a sandbox evaluation is authorized, report actual commands and results.
12. Add comments using the review log below. Preserve the original finding
    IDs and distinguish factual corrections from preferences or proposals.

Return: an executive verdict; a finding-by-finding review; any new blockers;
an updated shortlist; and a prioritized acceptance plan with evidence links.
```

## 13. Review and comment log

Copy rows as needed. Use finding IDs and source IDs instead of line numbers, which may change during editing.

| Comment ID | Reviewer / date | Finding or section | Verdict | Comment and supporting evidence | Proposed action | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-001 | Pending | Executive recommendation | Pending | — | — | — | Open |
| R-002 | Pending | F-01 to F-04: BuildSuite | Pending | — | — | — | Open |
| R-003 | Pending | F-05 to F-09: Quantbit/ProcureX | Pending | — | — | — | Open |
| R-004 | Pending | F-10 to F-12: alternatives | Pending | — | — | — | Open |
| R-005 | Pending | Business scope and acceptance | Pending | — | — | — | Open |

Optional longer comment format:

```markdown
### R-006 — Short title

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

## 14. Source register

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

## 15. Installation commands discussed in the session

The initial discussion included the following basic BuildSuite sequence from its repository. These commands were **not executed**. They assume an already compatible test Bench and are not a complete production deployment plan. [S01]

```bash
bench get-app https://github.com/BuildSuite-io/buildsuite_core
bench --site your-site install-app buildsuite_core
bench --site your-site migrate
bench build
```

The user-supplied initial sequence additionally mentioned requirements setup and restart. Their applicability depends on the hosting model and selected versions. Before running any installation, select a reviewed revision and dependencies; successful installation alone does not close the functional findings in this report.

## 16. Proposed next action and document history

**Next action:** Have the manager and independent AI reviewer challenge the findings and answer the business-scope questions. Then choose one sandbox evaluation path and run the acceptance scenarios before making a production decision.

| Version | Date | Change | Approval |
| --- | --- | --- | --- |
| 1.0 | 2026-09-16 | Consolidated current-session research, corrections, evidence, and review workflow | Pending manager review |

**Decision record:** No purchase, deployment, vendor commitment, or production approval has been made in this session.
