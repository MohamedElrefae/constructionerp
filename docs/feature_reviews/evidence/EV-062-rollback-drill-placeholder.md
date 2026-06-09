# EV-062 — Rollback Drill on Staging (Placeholder)

Date: TBD — to be completed after staging deploy

## Scope

Document the result of the rollback drill required by the manager (Condition 4.2, second-pass review).

## Drill Plan

1. Deploy `release/v6.8` to `construction-staging.frappe.cloud`.
2. Run post-deploy smoke (`EV-061`, Section 4).
3. Simulate a failure or restore pre-deploy DB snapshot.
4. Confirm rollback restores the site to pre-deploy state.
5. Document steps, timing, and any issues.

## Status

⏳ **Pending staging deploy.**
