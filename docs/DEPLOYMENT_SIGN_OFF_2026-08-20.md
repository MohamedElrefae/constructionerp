# Construction ERP — Deployment Sign-Off

**Date:** 2026-08-20  
**Authority:** Software Consultant Release Review  
**Decision:** **APPROVED FOR USER DEPLOYMENT**

## Scope

This sign-off covers the Scope Context, BOQ, WBS, transaction cascade, Variation Order, quantity-revision, cost database, cost-analysis, and Form Config work reviewed in `USER_GUIDE_DEPLOYMENT_REVIEW_2026-08-19.md`.

## Release Gate

| Gate | Result |
|---|---|
| Original blockers F1–F7 | Resolved |
| BOQ Header Scope Context | Feature-gated, Administrator-safe, preserves explicit integration project values |
| Omitted BOQ items | Excluded from transaction and VO item/leaf-structure selectors; server rejects re-selection |
| User guide | Synced with current UI, field names, cache versions, and test counts |
| Migration | `bench --site localhost migrate` passed |
| Asset build | `bench build --app construction` passed |
| Source integrity | Python and JavaScript syntax checks passed; `git diff --check` passed |

## Test Evidence

| Test area | Result |
|---|---|
| Variation Orders | 23/23 passed |
| Quantity Revisions | 30/30 passed |
| Transaction Validation | 13/13 passed |
| BOQ Link Queries | 9/9 passed |
| BOQ Properties | 17/17 passed |
| Scope Context integration runner | 17/17 passed |
| Cost Analysis Engine | 17/17 passed |
| Cost Database API | 10/10 passed |
| VFC Backend | 39/39 passed |

## Owner Handoff

The code and user guide are approved for deployment. For the production site, run the normal deployment sequence:

```bash
bench --site <production-site> migrate
bench build --app construction
bench restart
```

After deployment, perform one acceptance smoke test with a real non-administrator user: select Scope Context, create and lock a BOQ Header, create an omission VO, and confirm the omitted item cannot be selected in a new transaction or VO line.

**Consultant sign-off:** Approved. No known release blocker remains in the reviewed scope.
