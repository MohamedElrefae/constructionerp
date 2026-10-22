# Backlog: VO Status Transition `required_role` Hook

**Source:** Manager Condition 1.1 from second-pass review (`EV-058` sign-off, 2026-06-10).

## Current State

`Variation Order.validate_status_transition()` enforces the approval chain by **status state machine only**:

```python
allowed = {
    DRAFT_STATUS: {DRAFT_STATUS, SUBMITTED_STATUS, REJECTED_STATUS},
    SUBMITTED_STATUS: {SUBMITTED_STATUS, ENGINEER_APPROVED_STATUS, REJECTED_STATUS},
    ENGINEER_APPROVED_STATUS: {ENGINEER_APPROVED_STATUS, CLIENT_APPROVED_STATUS, REJECTED_STATUS},
    CLIENT_APPROVED_STATUS: {CLIENT_APPROVED_STATUS},
    REJECTED_STATUS: {REJECTED_STATUS},
}
```

Any user with `write` permission on `Variation Order` can change status to any allowed next state. There is **no role check**.

## Gap

Segregation of duties is not enforced:
- The same Project Manager could submit a VO, approve it as Engineer, and approve it as Client.
- The `Engineer` and `Client` roles do not exist in the VO permission matrix.

## Proposed Enhancement

Add an optional `required_role` configuration per transition in `validate_status_transition()`:

```python
# Example configuration (could live in Construction Settings or a new VO Workflow Config DocType)
TRANSITION_ROLES = {
    (DRAFT_STATUS, SUBMITTED_STATUS): None,  # any writer
    (SUBMITTED_STATUS, ENGINEER_APPROVED_STATUS): "Engineer",
    (SUBMITTED_STATUS, REJECTED_STATUS): "Project Manager",
    (ENGINEER_APPROVED_STATUS, CLIENT_APPROVED_STATUS): "Client",
}
```

If `required_role` is set and the current user does not have that role, `frappe.throw` with a clear message.

## Acceptance Criteria

- [ ] Configuration is optional (default: no role checks, backward compatible).
- [ ] Can be enabled per-deployment without code change.
- [ ] Clear error message when a user lacks the required role for a transition.
- [ ] Existing VOs are not affected by the change.

## Priority

**Low / Post-release.** Not a v1 blocker. The manager explicitly accepted the current design for the initial release.

## References

- `EV-058:19-23` — Security review finding
- `construction/construction/doctype/variation_order/variation_order.py:44-60`
