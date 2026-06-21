# Manager Decision Record: WP5 and WP7

> Date: 2026-06-21
> Audience: Engineering, Product, and Delivery
> Status: Approved for current sprint with one deferred item

## 1. Approval Note

Engineering may treat the WP1, WP2, WP3, WP4, WP6, and WP7 deliverables from `docs/handover/SESSION_REPORT_2026-06-21_WP1-WP7.md` as approved.

WP5 remains deferred and must not be implemented until the client confirms whether they need a profitability report now.

## 2. Decision Record

### WP5: Project-wise Profitability

Decision: **Deferred / pending client decision**.

Rationale:
- The standard ERPNext `Project-wise Profitability` report is GL-based.
- It does not reflect BOQ-driven construction reality.
- Installing it now would create a report that is technically correct but commercially misleading.

Direction:
- Do not install the standard report in the current sprint.
- Revisit WP5 only after BOQ reporting is finalized.
- At that time, choose between:
  - `Option A`: install the standard ERPNext report for a quick GL view.
  - `Option B`: build a BOQ-aware Construction Profitability report that combines BOQ values with GL actuals.

Current recommendation:
- Prefer `Option B` once BOQ reporting is ready, unless the client explicitly wants a fast interim GL-only report.

### WP7: Audit Log Retention

Decision: **Keep audit logs indefinitely for now; do not add auto-deletion in the current sprint**.

Rationale:
- The audit log is a security and accountability control.
- Deleting entries without a confirmed policy would remove evidence that may be needed later.
- There is no client-confirmed compliance retention period yet.

Direction:
- Leave the `Scope Report Access Log` append-only for now.
- Do not implement a cleanup job in the current sprint.
- Revisit retention only if the client, legal, or compliance team specifies a required retention period.

## 3. Engineering Guidance

- Treat WP5 as explicitly deferred, not forgotten.
- Treat WP7 retention as an interim policy, not a permanent compliance decision.
- If either item becomes a client or compliance requirement later, create a follow-up work package rather than folding it into unrelated scope.

## 4. Short Approval Note Back To Engineering

Approved:
- WP1 broader-app audit and integration plan
- WP2 scratch test conversion
- WP3 handover doc cleanup
- WP4 VFC debug flag
- WP6 Option B toggle
- WP7 audit logging

Deferred:
- WP5 Project-wise Profitability, pending client decision

Open policy:
- WP7 logs remain indefinite until a retention requirement is confirmed

