# Confirmed financial rules and implementation contract

Owner decisions confirmed in this conversation, implemented on `codex/customer-release-gap-fixes`; verification completed 2026-10-05. These changes are isolated from the main app checkout and are not customer deployment approval.

## Tender pricing

The owner specifies additive pricing on a shared direct-cost base:

`Selling unit rate = direct unit cost × (1 + (overhead% + profit% + tender tax allowance%) / 100)`

Direct cost 100, overhead 10%, profit 10%, tax allowance 0% gives **120**. Adding a configured 5% allowance gives **125**. Each amount uses direct cost; overhead does not become the profit base. The analysis records direct resource cost separately from suggested selling rate. The approved item's estimated unit cost remains direct cost, with percentages projected once. Contract price remains the separately entered commercial rate; approving an estimate does not replace it automatically.

`analysis_qty` must be positive. Resource quantities/rates and financial inputs must be finite and nonnegative; each percentage is restricted to 0–100. Resource wastage is applied in resource detail amounts. A multi-unit analysis divides its direct resource total by its analysis quantity before deriving the suggested unit rate.

The configurable **Tender Tax Allowance %** defaults to zero and is optional in older cost-database workbooks. It is a tender pricing allowance, separate from ERPNext invoice tax templates. No Egyptian statutory tax rate, taxable base, invoice treatment or legal compliance is established by this owner's arithmetic decision.

The shared calculation lives in `construction/services/boq_pricing.py`, identified as `additive-direct-cost/v1`. Controllers enforce it; form read-only settings alone are insufficient. The BOQ cost report supplies the version and allowance so consumers can identify the basis.

## BOQ factor

The owner confirms **factor must be greater than zero**. Missing values default to 1; explicit zero, negative and nonfinite factors are refused. Positive fractional factors remain valid.

Contract line value is `quantity × contract unit price × factor`; estimated/budgeted direct cost uses `quantity × estimated direct unit cost × factor`. Controllers, workbook preview and import updates preserve this meaning. An older zero/negative factor blocks guarded total recalculation and exports until reviewed and corrected; it is never silently converted to 1. The preview validator's existing swapped row-number/type arguments were also corrected; regression tests reach the actual workbook parser.

## Cost approval and cancellation

First approval captures the known manual estimate and overhead/profit/tax inputs with actor/time provenance. Approval projects a protected direct-cost basis and active analysis reference onto the item. Ordinary item saves cannot overwrite that provenance or the active approved cost inputs.

Each new approval records the actual analysis it supersedes, under the BOQ transaction guard. Cancelling the current approval restores the preceding eligible approval and its percentages; if the chain is exhausted, it restores the captured manual estimate and its percentages. A manual estimate of zero is valid evidence and remains zero. Cancelling superseded history leaves a newer active basis in place. After returning to manual pricing, a changed manual estimate is captured anew for the next approval cycle.

Duplicate active approvals, cycles, mismatched identities, invalid snapshots and missing restoration evidence require reconciliation. Restoration never guesses a manual cost. Historical approval self-links remain intact and may refer to cancelled history; cancellation retains native checks for other linked DocTypes.

The additive patch labels unversioned submitted/cancelled analyses `legacy-unversioned/v0` and unresolved items **Legacy Review**, preserving recorded prices, amounts, statuses and approval attribution. Ordinary saves and new approvals on unresolved legacy bases are blocked until a reviewed conversion establishes reliable evidence. The patch also preserves a newer active approved basis on replay. There is no general legacy-conversion UI or customer-data repair in this batch. That reviewed conversion and representative upgrade remain open release work.

## Permanent quantity approval history

Approved quantity revisions retain their status, commercial inputs, calculated evidence, references and approval attribution permanently. Approved→Rejected/Draft and deletion are refused on the server. Legacy Rejected records carrying prior approval attribution remain protected in their historical state; they are not automatically reapproved or repaired.

A correction is a **new revision**. First approval through ordinary document CRUD or the service applies its current quantity/rate projection once and records the authenticated approving user/time. Authorized roles retain the existing Project Manager / Construction Owner / System Manager policy and applicable document/read permissions; Administrator retains framework authority. Caller-supplied attribution cannot replace the actual approver. Header/structure must match the item, and an ordinary correction must use its current previous quantity. Original Lock creation is confined to the baseline factory using server context, not request flags.

Draft revisions cannot change current quantities. Reapplying old approval history cannot replace a newer projection; repeating the current approval is a no-op. Guards use the stored revision values, not an arbitrary caller object's amounts. Immutable numeric comparison uses database storage scale rather than displayed currency precision, preserving sub-cent protection while accepting unchanged fractional computed percentages.

These rules do not certify all permission/import/report routes. Some existing readers calculate revised figures from Variation Order deltas while others read quantity-revision projections. Customer release still requires a unified reader audit and representative historical reconciliation; approved history must not be rewritten to make those views agree.

## Verification and next development

See [verification](VERIFICATION.md) for actual module counts, authenticated request checks, patch preservation and real migrations. GPT-6 Luna handled bounded workbook/permanence changes and a read-only review; the parent implemented financial policy, reviewed the changes and ran the integrated checks. The review found legacy edit/uncancellable-approval risks; both were corrected and regressed before commit. This is AI review, not independent human release review.

Future changes must preserve these worked examples, server invariants, transaction protocol and legacy protection. Integration must reconcile concurrent main-checkout changes and rerun applicable checks on one immutable candidate. Browser wiring, capacity/security qualification, supported framework matrix, customer upgrade/restore, observed GitHub CI and release authority remain separate gates.
