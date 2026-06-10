# Manager Review Request: VO Quantity Revision Model

**Date:** 2026-06-11

**To:** Project Manager / Technical Lead

**From:** Development Team

**Subject:** Request for Manager Review — VO Quantity Revision Planning Phase Complete

---

## 1. Executive Summary

The VO Quantity Revision Model planning phase is complete. We have produced a revised implementation plan that incorporates critical feedback from the product owner regarding:

- **Rate change threshold computation** (FIDIC 25% rule)
- **VO line editing lifecycle** (editable until Client Approval)
- **Atomic VO lines** (one revision per VO line, matching Procore/COINS/Aconex standards)
- **Schema simplification** (removal of `item_code` from VO Line)

**We request your review of the revised plan before authorizing the implementation phase.**

---

## 2. Background

The original handoff plan (Document #12) proposed a simplified Quantity Revision architecture where:

- BOQ Item remains the work item
- Variation Order is the approval document
- BOQ Quantity Revision is the historical measurement record

During the planning review with the product owner, several critical decisions were refined to align with Egypt/Gulf quantity surveying practice and industry-standard ERP behavior.

---

## 3. Key Decisions Requiring Your Review

| # | Decision Point | Original Plan | **Revised Plan** | Rationale |
|---|---|---|---|---|
| 1 | **Rate change threshold** | Computed from `previous_qty` (current revised) | **Computed from `original_qty` (contract qty)** | FIDIC 25% rule applies to total deviation from original contract quantity, not incremental change |
| 2 | **VO line editing** | Locked after Draft status | **Editable until Client Approved** | Allows PM to add quantity changes during Engineer approval without creating new VO |
| 3 | **Multiple VOs for same line** | Not explicitly defined | **Atomic VO lines** — each line creates one revision record | Matches Procore, COINS, Aconex standard. Better audit trail |
| 4 | **`item_code` in VO Line** | Present (Link to ERPNext Item) | **Removed completely** | BOQ items are specification lines, not ERPNext Items. Prevents confusion in this phase |
| 5 | **Primary input field** | `delta_qty` (user enters delta) | **`revised_qty` (user enters total surveyed qty)** | Matches Egypt/Gulf QS practice |
| 6 | **Previous qty capture** | At Draft creation | **Reference at Draft; actual value at approval time** | Prevents stale delta if another VO is approved in between |
| 7 | **Report scope** | Full UI reports | **Query/service data layer first, UI templates later** | Faster delivery, foundation for all reports |
| 8 | **`total_revised_value`** | Not present | **Added to BOQ Header** | Shows contract + variation value for project financial tracking |

---

## 4. Documents Produced

### Planning Documents

| # | Document | Path | Status |
|---|---|---|---|
| 12 | Original AI Agent Handoff | `docs/feature_reviews/12_vo_quantity_revision_ai_agent_handoff.md` | Baseline |
| 13 | **Revised Implementation Plan** | `docs/feature_reviews/13_vo_quantity_revision_implementation_plan.md` | **Ready for review** |

### Evidence Templates (Ready for Implementation Fill-In)

| # | Document | Path | Purpose |
|---|---|---|---|
| 65 | Schema Evidence | `docs/feature_reviews/evidence/EV-065-vo-quantity-revision-schema.md` | DocType schema changes, migration results |
| 66 | Tests Evidence | `docs/feature_reviews/evidence/EV-066-vo-quantity-revision-tests.md` | 17 automated test cases with pass/fail tracking |
| 67 | Manual QA Evidence | `docs/feature_reviews/evidence/EV-067-vo-quantity-revision-manual-qa.md` | 25-step manual verification checklist |

---

## 5. What Will Be Implemented (Scope)

### Schema Changes
- **BOQ Item:** Add `original_qty`, `current_revised_qty`, `last_quantity_revision`
- **BOQ Header:** Add `total_revised_value`
- **VO Line:** Remove `item_code`, add `previous_qty`, `delta_from_contract`, `change_pct_from_contract`, `created_quantity_revision`
- **New DocType:** `BOQ Quantity Revision` with 8 auto-computed revision types

### Service Layer
- `quantity_revisions.py` — 6 functions (baseline creation, revision lifecycle, approval, DB locking)
- `revised_boq_queries.py` — 5 query functions (Original BOQ, Revised BOQ, History, VO Impact, Omitted Items)

### Controller & UI Updates
- `boq_header.py` — Hook baseline creation on lock
- `vo_line.py` — Primary input is `revised_qty`, `delta_qty` computed, FIDIC rule from contract
- `variation_order.py` — Atomic VO line processing, actual `previous_qty` read at approval time
- `variation_order.js` — Remove `item_code`, `revised_qty` editable, lock only after Client Approved
- `boq_link_queries.py` — Replace `quantity + SUM` with `current_revised_qty > 0`

### Tests
- Updated `test_variation_orders.py` — Remove `item_code`, add `previous_qty` checks
- New `test_quantity_revisions.py` — 17 test cases covering baseline, revisions, omissions, history

---

## 6. What Will NOT Be Implemented (Non-Goals)

Per the plan, these remain out of scope for this phase:

- ❌ ERPNext Item mapping (`item_code`)
- ❌ Material Request creation enhancement
- ❌ Purchase Order integration
- ❌ Inventory/procurement valuation
- ❌ Subcontractor IPC integration
- ❌ Full claims module
- ❌ UI report templates (HTML/CSS) — data layer only

These can be built on top of the quantity revision history in subsequent phases.

---

## 7. Acceptance Criteria

Implementation will be considered complete when:

1. ✅ `item_code` is not present in VO Line schema
2. ✅ BOQ lock creates original quantity snapshots (`original_qty`, `current_revised_qty`)
3. ✅ `BOQ Quantity Revision` exists with 8 auto-computed revision types
4. ✅ `rate_change_triggered` computed from `change_pct_from_contract` (FIDIC rule)
5. ✅ Original quantity remains available after revisions
6. ✅ Current revised quantity reflects latest approved revision
7. ✅ Quantity increase, decrease, omission, and new variation item supported
8. ✅ New items after lock are normal BOQ Items marked as variation items
9. ✅ Direct post-lock BOQ item edits remain blocked
10. ✅ Omitted items remain auditable
11. ✅ Transaction selectors hide omitted items but not from history/reporting
12. ✅ Automated tests pass or failures documented with root cause
13. ✅ Migration succeeds on `v16.localhost`
14. ✅ Evidence files (EV-065, 066, 067) are filled in
15. ✅ `total_revised_value` added to BOQ Header
16. ✅ VO lines editable until Client Approved

---

## 8. Review Request

**Please review the following document:**

📄 **`docs/feature_reviews/13_vo_quantity_revision_implementation_plan.md`**

This document contains the complete technical specification, file impact list, and execution instructions.

**Questions for your review:**

1. Do you approve the 8 revised decisions listed in Section 3?
2. Do you approve the scope of implementation (Section 5)?
3. Do you approve the acceptance criteria (Section 7)?
4. Are there any additional constraints or dependencies we should consider?
5. Should we proceed with implementation, or do you require changes to the plan?

---

## 9. Next Steps

| Step | Action | Owner | Status |
|---|---|---|---|
| 1 | Manager review of revised plan | Project Manager | ⏳ Pending |
| 2 | Approve or request changes | Project Manager | ⏳ Pending |
| 3 | Implementation by AI agent | Development Team | ⏳ Blocked until approval |
| 4 | Automated tests + migration | Development Team | ⏳ Blocked until approval |
| 5 | Manual QA on `v16.localhost` | QA / Product Owner | ⏳ Blocked until approval |
| 6 | Evidence documentation | Development Team | ⏳ Blocked until approval |
| 7 | Final manager review | Project Manager | ⏳ Blocked until approval |

---

**We are ready to proceed upon your approval.**

Please reply with your review comments or approval to continue.

---

*Planning completed: 2026-06-11*
*Documents: 13_vo_quantity_revision_implementation_plan.md, EV-065, EV-066, EV-067*
