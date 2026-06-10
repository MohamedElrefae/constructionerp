# Head of Engineering Review: VO Quantity Revision Model

Date: 2026-06-11

Reviewed documents:

- `docs/feature_reviews/14_manager_review_request.md`
- `docs/feature_reviews/13_vo_quantity_revision_implementation_plan.md`

Review role: Head of Engineering gate review before implementation.

## Review Decision

Status: **Conditionally approved, with required changes before implementation starts.**

The architecture is correct:

> BOQ Item is the work item. Variation Order is the approval/change document. BOQ Quantity Revision is the historical measurement record.

This is the right direction and should replace the older VO-line-as-second-BOQ approach. The plan is also correct to remove `item_code` and procurement scope from this phase.

However, implementation should not begin until the blockers below are resolved in Document 13. These are not cosmetic comments; they affect approval integrity, financial correctness, and migration safety.

## Blocking Findings

### P0-1: VO lines editable after Engineer Approval can invalidate approvals

Current revised decision:

- VO lines remain editable in Draft, Submitted, and Engineer Approved.
- VO lines lock only after Client Approved.

Risk:

If a user changes or adds VO lines after Engineer Approval, the engineer-approved commercial scope is no longer the same scope that goes to Client Approval. This breaks approval integrity.

Required correction:

Choose one of these policies:

1. **Preferred enterprise policy:** VO lines are editable in Draft and Submitted only. Once Engineer Approved, line edits are blocked. To change scope, return VO to Draft/Submitted or create a revision/new VO.
2. **Allowed flexible policy:** VO lines may be edited before Client Approval, but any line change after Engineer Approval must automatically reset status back to Submitted and clear engineer approval date/user.

Acceptance criteria must include:

- Editing lines after Engineer Approval cannot preserve the previous Engineer Approval.
- Client Approval must apply only to the exact lines that were engineer-approved.

### P0-2: `total_revised_value` is under-specified and will be wrong after rate changes

Current plan:

- `total_revised_value = current_revised_qty * contract_unit_price * factor`

Risk:

The plan also supports rate changes via `revised_unit_price`. If an item has an approved revised rate, calculating current value using `contract_unit_price` is wrong.

Required correction:

Add a current approved rate concept:

- Add `current_revised_unit_price` to `BOQ Item`, or
- Compute current value from the latest approved `BOQ Quantity Revision.revised_unit_price`.

Recommended implementation:

- Add `current_revised_unit_price` to `BOQ Item`.
- At BOQ lock: `current_revised_unit_price = contract_unit_price`.
- On approved revision: update `current_revised_unit_price = revision.revised_unit_price`.
- Compute `total_revised_value = current_revised_qty * current_revised_unit_price * factor`.

Acceptance criteria must include:

- Rate change updates current revised BOQ value.
- `total_revised_value` uses latest approved rate, not always original contract rate.

### P0-3: FIDIC percentage rule needs explicit behavior for variation items and zero original quantity

Current plan:

- `change_pct_from_contract = abs(revised_qty - original_qty) / original_qty * 100`
- Rate trigger is based on original contract quantity.

Risk:

For new variation items, `original_qty = 0`. For later revisions to variation items, the formula divides by zero or becomes undefined.

Required correction:

Define separate threshold behavior:

- Original contract items: FIDIC percentage uses `original_qty`.
- New variation items: first approved item has explicit agreed rate and no percentage threshold.
- Later revisions to variation items: use the first approved variation quantity or latest agreed baseline quantity as the comparison base, depending on commercial policy.

Recommended simple policy for this phase:

- If `original_qty > 0`, compute `change_pct_from_contract`.
- If `original_qty = 0`, set `change_pct_from_contract = 100` for first New Variation Item and require explicit rate.
- For later revisions to variation items, compute percentage from the first approved variation quantity stored as `variation_baseline_qty`, or defer formal 25 percent rule and always require commercial review.

Document 13 must choose one policy.

### P0-4: Revision approval must be idempotent and transactional

Current plan says each VO line creates one revision, but does not fully define duplicate protection.

Risk:

The existing `VariationOrder.on_update()` runs approved behavior whenever status is Approved by Client. Without strict line-level idempotency and transaction locking, repeated saves can duplicate quantity revisions or create multiple variation BOQ items.

Required correction:

Implementation must:

- Check `VO Line.created_quantity_revision` before creating a new revision.
- Check `VO Line.created_boq_item` / `created_boq_structure` before creating new variation items.
- Lock the BOQ Item row during approval.
- Validate that actual DB `current_revised_qty` still matches expected previous quantity unless the design intentionally recomputes from current value.
- Apply all VO lines in one transaction or fail the whole approval cleanly.

Acceptance criteria must include:

- Re-saving an Approved by Client VO does not create duplicate revisions.
- Partial approval failure does not leave half-created revisions/items.

## Major Findings

### P1-1: Migration/backfill for existing VO data is incomplete

The site already has VO and variation test data from previous implementation work. The plan covers new baseline creation but not enough detail for existing variation items and approved VOs.

Required correction:

Migration section must define:

- Existing non-variation BOQ Items under Locked BOQs get `original_qty = quantity` and `current_revised_qty = quantity`.
- Existing variation BOQ Items get `original_qty = 0` and `current_revised_qty = quantity`.
- Existing approved VO-created variation items should get a `BOQ Quantity Revision` of type `New Variation Item` where possible.
- Existing approved Quantity Change/Omission VO lines should either be migrated to quantity revisions or explicitly marked as legacy and excluded from new revision totals.

### P1-2: Transaction selector filtering must be opt-in and null-safe

Current plan:

- Replace `quantity + SUM(delta)` with `current_revised_qty > 0`.

Risk:

If `current_revised_qty` is null during migration or on older records, valid items may disappear. Also, omitted items must not be globally hidden from audit/reporting selectors.

Required correction:

- Use `coalesce(current_revised_qty, quantity) > 0`.
- Apply this only when a filter such as `exclude_zero_revised_qty` is passed.
- Do not globally change all BOQ item queries.

### P1-3: `BOQ Quantity Revision.status` vs Frappe `docstatus` must be decided

The plan defines a custom `status` field but does not decide whether the DocType is submittable.

Recommendation:

- Keep custom `status` if approval is driven by VO workflow.
- Set `BOQ Quantity Revision` as non-submittable unless there is a real independent revision approval workflow.
- Make approved records protected by controller validation.

Document 13 should explicitly state this.

### P1-4: Rate Change revision type is ambiguous

The revision type list includes `Rate Change`, but the VO line types are New Item, Quantity Change, and Omission.

Risk:

Implementation may accidentally support price-only changes without defined UX or approval rules.

Required correction:

Either:

- Add a clear `Rate Change` VO line type and UX, or
- Remove `Rate Change` from this phase and treat rate changes only as part of quantity revisions above threshold.

For this phase, I recommend removing standalone `Rate Change`.

## Minor Findings

### P2-1: Evidence files should be mandatory outputs

Document 14 correctly lists EV-065, EV-066, and EV-067. Document 13 should also say implementation is not complete until those files are filled with actual results, not templates.

### P2-2: Report service acceptance needs examples

The query service report scope is good, but test fixtures should assert concrete values:

- original value,
- revised value,
- delta value,
- omitted item handling,
- variation item inclusion.

### P2-3: Naming consistency

Use one field name consistently:

- `delta_from_contract_qty` is used in Document 13 schema.
- `delta_from_contract` is used in VO Line section.

Pick one name. Recommended: `delta_from_contract_qty`.

## Approved Decisions

The following decisions are approved:

- Remove `item_code` from VO Line for this phase.
- Exclude procurement and Material Request work from this phase.
- Use `revised_qty` as the primary QS input.
- Add `BOQ Quantity Revision` as the historical measurement ledger.
- Keep BOQ Items as the operational work items.
- Add `original_qty` and `current_revised_qty` to BOQ Item.
- New post-lock items should be normal BOQ Items marked as variation items.
- Reports should start with query/service layer before UI templates.

## Required Plan Updates Before Implementation

Update `docs/feature_reviews/13_vo_quantity_revision_implementation_plan.md` to include:

1. Approval integrity rule for edits after Engineer Approval.
2. `current_revised_unit_price` or equivalent latest-rate mechanism.
3. Explicit percentage rule for variation items where `original_qty = 0`.
4. Transactional/idempotent VO approval behavior.
5. Existing data migration/backfill strategy.
6. Null-safe and opt-in transaction selector filtering.
7. Decision on `BOQ Quantity Revision.status` vs `docstatus`.
8. Remove or formally define standalone `Rate Change`.
9. Consistent field naming for contract delta fields.

## Final Gate

Engineering recommendation:

- **Do not start implementation yet.**
- Update the plan for the P0 and P1 findings above.
- After the plan is updated, implementation can proceed without another major architecture review unless the team changes the core model.

Once these corrections are made, this plan is suitable for AI-agent implementation and later engineering review.
