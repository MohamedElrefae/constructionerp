# Stage 3 Round 11 — Independent AI-R Verification

**Date:** 2026-09-10  
**Role:** AI-R, fresh review of the current candidate  
**Decision:** **BLOCKED**

## Scope and integrity

Review was performed against the live working tree, current Round-11 pilot
and implementation records, current search/service/tests, and the current
Stage-3 evidence set. No implementation, catalog, payload, business-data,
runtime Translation, Git/index/history, or existing-evidence files were
changed. This report is the only file written by this review.

## Round-10 gate review

The implementation portion is verified:

- `construction/searchable_dropdown/api/search.py` has no local `_coerce_int`.
  It imports and calls `_coerce_int` from
  `construction.services.bilingual_service` for both `page_length` and
  `start`.
- The dropdown annotations are `int | float | str | None`, allowing the
  shared helper to receive the values before Frappe's narrower type handling
  can produce a different exception class.
- The helper rejects fractional floats, garbage, and `None` with
  `frappe.ValidationError`; accepted integer and integer-valued string inputs
  are clamped (`page_length >= 1`, `start >= 0`, maximum page length 200).
- The permanent test does assert `frappe.ValidationError` on both public
  paths for its listed garbage cases and checks first-result agreement for
  integer-valued inputs.

However, the requested permanent verification contract is incomplete. The
test `test_non_integer_pagination_inputs_are_cross_path_consistent`:

1. does not include `None` in its garbage cases (despite the gate explicitly
   requiring it, including blank/text query coverage);
2. asserts the exception class only, not equality of the exact exception
   message between service and dropdown; and
3. does not capture both exceptions and compare their messages, so a future
   message divergence can pass the test.

This is a P1 permanent-test gate defect, not evidence that the current helper
implementations visibly diverge. The test comments also retain stale wording
about truncation/defaulting, which should be corrected while tightening the
contract.

## P95 artifact

The current artifact is hash-bound and current:

| Item | Result |
|---|---|
| Artifact SHA-256 | `040d92e1e9703e77fc177166ef8ed6df344dc75ee93463da97def02809daaba6` |
| Code hashes | service, registry, and dropdown all match artifact hashes |
| Preserved rounds | 5 baseline + 5 bilingual, with raw samples and per-round P95s |
| Selected P95 | baseline `1.987 ms`; bilingual `2.120 ms` |
| Relative change | `+6.69%`, inside the bare 10% rule |
| Selection/statistic | nearest-rank recomputation and min-of-rounds contract present in permanent test |

No duplicate legacy floor test was found in the current pilot test file.

## Other regression/evidence review

The supplied current evidence and live records remain internally consistent:
pilot `53/53`, standalone `89/89`, pure `38/38`, aggregate `215`
(`13+6+5+3+8+89+38+53`); catalog `805`; extraction `664 + 21`, missing `0`;
inventory `18,446` with Merkle root `2e284695…`; evidence-enabled gate
`errors=0`; synchronization `0/0` followed by freshness, rebind, inventory,
Merkle, and gates in the required order; lint and diff checks clean. Existing
evidence covers the previously reviewed pagination/ranking, overflow/refusal
metadata, permissions/single-query behavior, normalization, registry
fail-closed behavior, insert/rename/audit, HTTP/browser cleanup, and POs/build
checks. No Account names were migrated and no residue is reported.

## Required next gate

Add `None` cases (including blank and text queries and both pagination
positions), capture exceptions from both paths, and assert both exact
`type(...) is frappe.ValidationError` and identical `str(exception)` (or the
documented exact message). Re-run the complete evidence-enabled suite and
refresh the round-11 evidence after that change. Until then, Stage 3 is not
independently verified and Stage 4 must not begin.

If the test gate is closed, Stage 3 may be declared closed and Stage 4 may
begin under the canonical plan. Owner authorization remains required for any
commit, push, merge, deploy, runtime migration, or Account-name migration.
