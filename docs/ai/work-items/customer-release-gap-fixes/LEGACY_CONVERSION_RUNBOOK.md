# Legacy BOQ cost conversion runbook

**Purpose:** Convert one unresolved `Legacy Review` BOQ Item to a current, owner-reviewed cost basis while retaining its old submitted analysis records. This is an operator procedure for an authorized, backed-up site. The helper is not a customer-facing feature or RPC endpoint. No representative customer conversion has yet been completed; that remains a release gate.

## Before conversion

1. Confirm the target site and customer authorization. Take and verify a recoverable full site backup, including its database and files. Rehearse the procedure on an isolated copy of that backup first. Record the site, app/source revision, backup identity, BOQ Header, BOQ Item, and current commercial totals in the private change record. Do not put customer data, credentials, or private evidence in this repository.
2. Use an authenticated `Administrator` or a user with the `Construction Owner` role. The operator must also have native write access to the BOQ Header and BOQ Item, and native write and submit access to the replacement BOQ Cost Analysis. The operator must be able to read every historical analysis for the item.
3. Review the source documents and supporting evidence with the responsible commercial owner. The manual basis is a deliberate restoration amount, not a value inferred from old totals. Preserve the source of the amount and review reason in the approved private customer record.
4. Create and save a replacement **Draft** BOQ Cost Analysis for the same item, with its complete, reviewed resource detail rows. It must not be a template. The preview validates the saved draft; it does not save or repair the replacement for you.

The item must still have `cost_basis == "Legacy Review"`, no existing `manual_cost_snapshot`, and a valid positive factor. The saved submitted-analysis history must be unambiguous: at least one submitted/cancelled record must exist, there may be at most one active Approved record, and any active Approved record must be tagged `legacy-unversioned/v0`. Ambiguous or inconsistent history is rejected for separate reconciliation.

## Preview and apply API

Call these Python functions from trusted server-side operator code in the site's Frappe context (for example, an authenticated Bench console). They are imported from `construction.services.boq_legacy_cost_conversion`; neither function is whitelisted for HTTP/RPC use.

The manual basis must contain all four numeric keys. Values must be finite and nonnegative; percentages may not exceed 100. Zero is valid. The reason must be non-empty and at most 2,000 characters.

```python
from construction.services.boq_legacy_cost_conversion import (
    preview_legacy_cost_conversion,
    apply_legacy_cost_conversion,
)

manual_basis = {
    "est_unit_cost": 80,
    "overhead_pct": 5,
    "profit_pct": 10,
    "tender_tax_pct": 0,
}
reason = "Reviewed manual estimate against the retained supplier evidence."

preview = preview_legacy_cost_conversion(
    "BOQI-...", "COST-...", manual_basis, reason
)
```

Review the returned item name, replacement name, legacy analysis names, before/after unit costs, suggested selling rate, manual basis, reason, and `inputs_digest`. The preview performs locking reads and validation but writes no documents. It computes the replacement using the current additive direct-cost rule; for direct cost 100 with overhead 10%, profit 10%, and tax allowance 0%, the suggested rate is 120.

Only after approving that exact preview, apply it with the same identifiers, exact manual-basis values, exact reason, and digest:

```python
result = apply_legacy_cost_conversion(
    "BOQI-...", "COST-...", manual_basis, reason, preview["inputs_digest"]
)
```

The digest is a freshness check over the current item, all submitted analysis history, the saved replacement draft, the canonical manual basis, and the normalized reason. If any bound input changes between preview and apply, the apply call fails and must be freshly reviewed. Do not reuse a digest for another item or edit the replacement after preview. Applying the same review twice is refused because the first application no longer has an unresolved `Legacy Review` item.

The result includes `applied=True` and the submitted `approved_analysis` name. Before committing, reload and verify that the replacement is submitted and active, the item has `cost_basis == "Approved Analysis"`, its direct estimated cost and selling calculation match the preview, and the retained conversion evidence is present in the item's manual-cost snapshot and the replacement's Info comment.

## Writes, history, and failure handling

On success, the helper supersedes the one active legacy Approved analysis, sets the reviewed manual basis and provenance snapshot, submits the replacement through native document lifecycle methods, and records the review evidence. It deliberately does not recalculate or rewrite the old analyses' costs, rates, totals, approval attribution, approval dates, or docstatus. For the active old analysis, only `analysis_status` changes to `Superseded`; historical non-active statuses remain as they were. No legacy commercial amount is normalized by this procedure.

The apply helper creates a database savepoint and rolls back to it if any step raises, including failure after replacement submission while writing the audit comment. The enclosing request/console transaction belongs to the caller: the helper does **not** commit. Commit only after successful return and the post-apply verification above. On any failure, the operator should roll back the entire conversion transaction and inspect the unchanged records before retrying. In particular, a BOQ lock timeout/deadlock requires a full transaction rollback; the shared transaction guard can refuse a later commit even after savepoint rollback. Start a fresh transaction, regenerate the preview, and obtain a fresh review before retrying.

If a conversion was committed but later proves wrong, do not edit old submitted analyses or reverse their historical status manually. Stop further dependent work and use the verified pre-conversion backup for an exact restoration under the site's authorized recovery process. Cancelling the replacement uses the normal cancellation path and restores the reviewed manual basis, but it does not restore the old active analysis status, so cancellation is not an exact rollback to the pre-conversion state.

## Evidence and remaining qualification

The automated regression fixture covers read-only/stable preview, submitted replacement and manual-basis preservation, cancellation restoring the reviewed manual estimate, stale digest rejection after changing manual evidence or replacement details, duplicate-apply rejection, missing inputs, non-owner refusal, ambiguous multiple active approvals, mismatched replacement item, and rollback after an injected post-submit audit failure. These are synthetic-site tests; they do not qualify a customer-data repair.

Before describing legacy conversion as customer-ready, complete a reviewed conversion on a representative prior-version site copy. Compare pre/post source amounts, statuses, approval actors/dates, replacement calculations, reports/exports, cancellation behavior, and backup restoration. Retain the evidence privately and bind the result to the exact candidate and site copy. Until then, this procedure is a controlled development/operator capability, and representative customer conversion remains pending.
