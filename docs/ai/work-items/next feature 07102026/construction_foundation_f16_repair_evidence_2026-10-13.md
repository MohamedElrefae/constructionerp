# F16 — Repair BOQ import completion (K-01): evidence

**Date:** 2026-10-13
**Candidate:** construction `09c8cb1` + uncommitted F16 changes · frappe 16.51.1 · erpnext 16.50.0
**Site:** v16rehearsal.localhost, enforcement ON, PM/Engineer sessions + Administrator setup
**Status:** UI dialog repaired + contract verified (8/8) + duplicate-commit suppression with regression (3/3, fail-before proven). F16 **Engineering verified** for the repair scope; owner UI-50/51/53 retest in the consolidated block.

## 1. The repair (K-01 root cause eliminated)

`boq_header.js` Import Excel dialog rebuilt as an explicit two-step flow:
- **Validate:** calls `import_boq_excel` with `dry_run: 1`, renders "Preview only — nothing saved yet" with row/section/item/warning counts, detected layout and the error list. No success message for previews (the old lie is gone; only a code comment references it).
- **Confirm Import:** armed only after a clean preview; mode selector preselected with the detected layout; commits with `dry_run: 0` + `confirmed_import_mode`. Success reports persisted counts + batch ("Imported N items in M structures (batch X)"); a repeat showing the same attachment reports "Already imported ... No duplicates created."
- **Guards:** busy flag + disabled primary button during requests (duplicate-click protection); file-change since validation forces re-validation; commit without confirmed mode is refused server-side (417); errors reset to Validate state; transport failures advise verifying saved records before retrying.

## 2. Contract verification (8/8, dedicated Draft header BOQ-2026-8605)

Preview success with zero writes and exact counts (3 items); commit persists exactly 3 + traceable batch; commit-without-mode refused with zero writes; error file surfaces row-level errors (`missing_unit`); engineer denied (403).

## 3. Duplicate-commit suppression (new server behavior)

Concurrent duplicate commits: one wins, the other fails — but only by race, so a same-attachment suppression was added in `_commit_import` (no schema change): a Committed batch with the same file URL whose tagged items still exist returns the existing outcome with `duplicate_suppressed: true`. Verified: sequential double-commit → same batch, zero new items. After item deletion, re-commit proceeds fresh (explicit re-confirmation).
- Residual (F16-D001, S2): byte-identical re-uploads receive fresh URLs and are not deduped; content-digest detection tracked for F38.
- Incidental fix in the same function: `source_file` was always NULL because `os.path.isabs` misfires on `/files/` URLs; now records web URLs (local existing paths still excluded).

## 4. Candidate note (PR-04)

Evidence gathered on working tree @ `09c8cb1` ("declare Frappe Cloud v16 app compatibility": pyproject vendor pins frappe ≥16.36.1/erpnext ≥16.37.0 — satisfied by installed 16.51.1/16.50.0, consistent with F25-D001's update-vendor direction). No runtime code in that commit; import paths re-verified above. Unrelated `orchestrator/engine.py` working-tree change preserved untouched.

## 5. Remaining

Owner UI-50/51/53 journeys on the repaired dialog (consolidated block); F17 error-file/traceability UI; F38 triage of F16-D001.

## 6. Concurrency after fix (2026-10-13)

Repeated the concurrent same-attachment test with suppression live: one winner commits (200 + batch), the loser fails without writes; fresh counts confirm exactly the winner's items, one new batch. Sequential same-URL recommit returns the existing batch with `duplicate_suppressed`. Uncertain-response retry therefore converges without duplicates in both orders. Combined with the 3/3 regression, duplicate handling is complete except byte-identical re-uploads (F16-D001).
