# F36 — Critical browser regressions (evidence)

Date: 2026-10-14 · Site: `v16rehearsal.localhost` (positive identity per session: the persona
logged in exists only there; Redis PONG both instances before the run).

## API outcomes (9/9)

| Check | Persona | Outcome |
|---|---|---|
| R0 identity ×2 | pm, buyer | logins prove the rehearsal site |
| R1 persisted import | pm | header 200; 4 BOQ Items read back |
| R2 reprice gate | pm | dry-run 200 — refusal or preview, never silent rewrite |
| R3 VO list | pm | 200, 3 VOs |
| R4 handoff | buyer | MR `MAT-MR-2026-00023` created 200, cleaned up afterwards |
| R5 denied analysis doc | buyer | 403 (no cost-doc access for Purchase role) |
| R6 cross-company | pm | 403 on Elrefae header |

R4 needed a real fixture (`_Test FG Item` / `_Test Warehouse - _TC`); the first attempt
failed 417 on a non-existent item — itself proof the validation chain runs for personas.

## Browser outcomes (6/6)

| Check | Outcome |
|---|---|
| B0 identity | buyer login proves site |
| B1 handoff slice | 20 MRs listed for the buyer |
| B2 form renders | doc URL + items section + Arabic status values |
| B3 denied analysis list | denial text in the UI |
| B4 Arabic list | `lang=ar dir=rtl`, title بند جدول الكميات, 3 rows |
| B5 Arabic error | denial/mandatory message in Arabic |

Two suite corrections during the run: B2 clicked a non-row element (hardened to row-subject
clicks + doc-URL wait); B4 first targeted the MR list, which the PM cannot see at all
(F20-D001 role design — verified "غير مسموح" in-session), so it now uses the BOQ Item list
the PM reads. Both are documented here so a future failure is not mistaken for a product
regression.

## Status

F36 **Engineering verified** (38/38 outcomes with site identity — lifecycle 15/15, import
8/8, first-round 15/15). Owner acceptance stays in the consolidated final block.

### Lifecycle detail (this round)

- **L1** (isolated `F36 L1` graph): PM submits draft analysis → Approved, item cost
  10.0 → 150.0; PM cancels → Cancelled, item cost restored to 10.0; graph deleted.
- **L2** (isolated `F36 L2` graph, Locked header): PM creates + submits VO →
  engineer approves (recorded identity) → owner client-approves with signed PDF →
  status Approved by Client, 1 quantity revision projected; graph deleted.
- **L3**: buyer submits MR → docstatus 1 → cancels → docstatus 2 → deleted.
- **Import** (isolated headers, fresh per run): attach → Validate → preview
  (Rows: 3, sections: 1, items: 2) → Confirm → batch + dialog closes → 2 items read back
  from the database → graphs + probe files deleted. Re-running against an already-imported
  header correctly refuses with "WBS code already exists" (idempotency guard, not a failure).
- **Failed save**: quantity −5 refused; form retains the rejected edit while the database
  keeps 40.00 — proven two ways in the same check, then reloaded equal.

### F36-D003 (fixed this round)

The K-01 browser path had three stacked defects behind one symptom (dialog stuck on
"Validating…" despite API 200): undefined `d.doc`, `d.refresh()` wiping staged values,
translated enum options breaking the round-trip. All fixed in `boq_header.js`, verified
end-to-end above. F16's earlier verification evidently covered the API path only.
