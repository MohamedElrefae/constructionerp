# Stage 3 Round 12 — Independent AI-R Verification

**Date:** 2026-09-10  
**Role:** AI-R, fresh review of the current working tree  
**Decision:** **VERIFIED**

## Scope and integrity

I reviewed the current candidate, not the prior report: AGENTS.md, the
canonical v4 plan and handoff, IMPLEMENTATION through rows 54/55, the Round-11
report, current service/dropdown/handler/tests, P95 artifact, HTTP/browser
evidence, and governed Stage-2/localization evidence. No implementation,
catalog, payload, business-data, runtime Translation, Git/index/history, or
existing evidence file was changed. This report is the only file written by
this review.

Working-tree HEAD before and after review: `e7be48855bde540464ea302e53c9bfca62b7c462`.
The tree contains the owner’s pre-existing uncommitted candidate changes;
`git diff --check` and Python compilation of the reviewed service, dropdown,
and pilot test passed.

## Round-11 closure

Verified at source and through a fresh focused Bench run:

- `searchable_link_search` has no duplicate coercer and imports the sole
  `_coerce_int` from `construction.services.bilingual_service` for both
  pagination values.
- The dropdown annotations accept `int | float | str | None`, allowing the
  shared helper to run before framework type short-circuiting.
- The helper accepts real integers and integer-valued strings, rejects
  fractional floats, garbage, and `None` with `frappe.ValidationError`, and
  applies the lower/upper clamps consistently.
- `test_non_integer_pagination_inputs_are_cross_path_consistent` includes
  `None` for page length, start, and both together, fractional values and
  garbage; it captures both exceptions and requires exact type plus identical
  messages. No broad `assertRaises(Exception)` or duplicate test name exists.
- Fresh execution: the permanent cross-path test and P95 artifact test both
  passed (`Ran 2 tests ... OK`). The HTTP `execute_cmd`/POST-shaped coercion
  coverage is present, including string `from_descendant`; blank/text queries,
  accepted integer forms, clamps, ranking/pagination, permissions and
  single-query behavior remain covered by the pilot.

## P95 and evidence integrity

The current artifact SHA-256 is
`040d92e1e9703e77fc177166ef8ed6df344dc75ee93463da97def02809daaba6`.
It preserves five raw rounds and per-round nearest-rank P95s for each side;
the selected values are the minima of those recorded rounds and match the
artifact test. Baseline is `1.987 ms`, bilingual `2.120 ms` (`+6.69%`, within
the bare 10% rule). Current code hashes bound by the artifact are:

```
bilingual_service.py       a8c049443d7755714e2a173c75cd5747fce527a374be6b43cf7c76b49ebd0698
bilingual_registry.py      691f74feb7fb72bf3a487ce89d5b55bf4512b07584d8a3f9b763530c33df3538
search.py                  ca59f814ac0d381a7888e76bd4e0e8827807add96a5b3574d0c9eabdfe3587c3
```

The supplied current evidence remains coherent: pilot `53/53`, pure `38/38`,
standalone `89/89`, aggregate `215 = 13+6+5+3+8+89+38+53`; catalog `805`;
extraction `664 + 21`, missing `0`; inventory `18,446`, Merkle
`2e284695…`; evidence-enabled full/scoped/vendor gates `errors=0`; and clean
lints/diff-check. Synchronization is `0/0` followed by freshness, rebind,
inventory, Merkle, and gates in the required order. Prior P0/P1 controls,
browser/HTTP cleanup, insert/Unicode/savepoint rename, Version/Comment,
registry/normalization/UI, POs, and build evidence remain intact.

## Conclusion and next gate

**Stage 3 is independently verified and closed. Stage 4 may begin under the
canonical plan.** Owner authorization remains required for commit, push,
merge, deploy, runtime Translation/name migration, or Account-name migration.
No such action was taken in this review.
