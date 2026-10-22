# Construction ERP — Engineering Review Summary Report

**Prepared for:** General Manager  
**Perspective:** Head of Engineering  
**Date:** 8 October 2026  
**Version:** 1.0  
**Classification:** Confidential — internal management and engineering  
**Based on:** `construction_platform_engineering_review_for_gm_v2_1_revised.md` (full report); original v2.0 preserved unchanged.

---

## 1. Executive summary

- **Recommendation:** Build **customer Payment Certificates (مستخلصات المالك)** first. It closes the gap between measured work and billing using the BOQ foundation that already exists.
- **Method:** Definition and accounting-validation phase → controlled pilot → two real certificate cycles before expansion.
- **Platform posture:** Existing foundation with recorded qualification evidence; not certified as production-ready for all customers.
- **Key decision:** GM approves definition phase, nominates owners, rings-fences capacity at kickoff.

## 2. What the platform has today

| Area | Status |
|---|---|
| BOQ/WBS with variations and quantity revisions | Implemented and documented |
| BOQ transaction attribution on 8 ERPNext document types | Implemented; integration testing still needed for the proposed workflow |
| Stage measurement (planned/measured/certified) | Present; not a period-billing or allocation engine |
| Payment Certificates, Subcontracting, Site Diary | **Not implemented** — new commercial transaction capability required |
| Bilingual UI / RTL / VFC forms | Established infrastructure; new screens need ordinary-user qualification |
| Release evidence | Private CI Run 11: 234 Python tests + 35 JS cases; must be bound to the deployment candidate |

## 3. Priority roadmap

| P | Deliverable | Outcome |
|---|---|---|
| P0 | Candidate/evidence reconciliation and contract/accounting definition | No build on uncertain rules |
| P1 | Customer certificates, measurement allocations, invoice reconciliation | Auditable billable workflow |
| P1 | Retention and advance registers with finance-approved policy | Explainable balances |
| P2 | Committed/actual cost report, forecast to completion | Reliable cost exposure |
| P2 | Subcontract agreement and subcontractor certificates | Controlled liabilities |
| P3 | Site Diary, mobile capture, plant lifecycle, dashboards | Operational depth on proven demand |

## 4. Scope of the customer-certificate pilot

**In:** measured-work items, period evidence, partial stage allocation, retention cap, advance recovery, bilingual print, draft invoice generation, partial-collection visibility, supported corrections, legacy opening balances.

**Out:** subcontractor administration, FX, multi-company certificates, statutory e-invoice submission, escalation/indexation, materials-on-site, daywork, final accounts, advanced EVM, Site Diary, plant operations.

## 5. Engineering design highlights

- Versioned contract-terms record; certificate identity scoped to company + contract + customer + currency + series.
- Source allocation child table with partial consumption history; existing certified stages remain immutable.
- Factor applied exactly once; historical amounts preserved; new rates apply only to new work.
- Retention held ≠ retention withheld to date; advances tracked from posted receipts, not manual maxima.
- No GL on certificate approval; invoice draft → finance review → posting; retry-safe via operation keys; concurrent approvals serialized by contract locks.
- Corrections via linked adjustments/credit notes; previously approved certificates never recalculated in place.

## 6. Accounting acceptance evidence required

| Event | Must prove |
|---|---|
| Certificate approval | Frozen values; no unintended GL |
| Invoice draft/post | Customer/company/currency/UOM, tax, payment terms correct; debits = credits |
| Advance allocation | Posted receipt consumed once; register reconciles |
| Partial collection | Due remainder and retention remain separately visible |
| Retention release | Correct balance shift; no duplicated revenue |
| Cancellation/credit note | Intended reversal; closed periods and later dependencies protected |

## 7. Delivery plan and capacity

| Phase | Window | Exit |
|---|---|---|
| Definition and evidence reconciliation | Weeks 1–2 | D0 |
| Certificate and measurement core | Weeks 3–5 | D1 |
| Finance and reporting | Weeks 6–8 | D2 |
| Qualification and pilot preparation | Weeks 9–10 | D3–D4 |
| Observed pilot | Two actual cycles | D5 |

- Planning range: ~8–12 engineering + 3–4 QA + 1–2 QS + 1–2 Finance person-weeks over ~10 weeks.
- Solo-engineer scenario: ~12–16 calendar weeks before pilot, with QA/business reviewers available.
- Budget: loaded weekly rates + infrastructure + independent review + training + 20% contingency; no currency figure proposed.

## 8. Risks (top five)

| Risk | Impact | Mitigation |
|---|---|---|
| Unclear contract/tax policy | High | D0 signed posting examples |
| Duplicate allocation/invoice under concurrency | Critical | Locks, idempotency, real concurrent/failure tests |
| Historical quantities billed again | Critical | Opening reconciliation, quarantine ambiguous history |
| Retention/advance imbalance | High | Separate registers and reconciliation |
| Scope creep into subcontracting/connectors | High | Written pilot boundary, separate estimates |

## 9. Pilot scorecard (targets to agree at D0)

- Zero duplicate allocations/invoices; zero unexplained reconciliation differences.
- 100% of approved lines traceable to accepted measurement or approved opening/correction evidence.
- ≥30% less staff preparation time vs agreed baseline.
- ≥90% first-pass internal acceptance without arithmetic/source-evidence rework.
- 100% of in-scope certificates processed through the approved workflow.
- Two reconciled cycles with no unresolved critical/high financial or access defect.

## 10. Decisions requested

1. Approve the definition phase and nominate pilot sponsor, QS owner, finance owner.
2. Approve quantity basis, retention, advance recovery, tax configuration, correction policy, authority limits at D0 exit.
3. Ring-fence engineering/QA/finance/QS capacity before committing the build budget.
4. Keep release authority separate from engineering readiness.

**Next step:** Approve definition kickoff. No implementation or deployment is authorized by this summary.

---

*Prepared 8 October 2026 by the Head of Engineering. Full detail in the v2.1 revised report; original v2.0 and platform analysis preserved unchanged for traceability.*
