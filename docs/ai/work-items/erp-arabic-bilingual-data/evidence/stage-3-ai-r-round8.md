# Stage 3 — Independent AI-R Round 8 Verification

**Verdict: BLOCKED. Stage 4 must not begin.**

I reviewed the current candidate (not the prior report), including `AGENTS.md`,
the canonical v4 plan §10.3, the current service and dropdown implementations,
registry and hooks, permanent tests, Round-7 report, Round-8 pilot evidence,
implementation tracker through row 46, HTTP evidence, governed localization and
Stage-2 evidence, and the preserved P95 artifact. No implementation, catalog,
payload, business-data, runtime Translation, Git, or existing-evidence files
were changed. The only file written is this report.

## Round-7 closure verification

The current source does fetch `RANK_WINDOW + 1` rows for text searches on both
public paths, sets overflow only for `len(rows) > RANK_WINDOW`, removes the
probe with `rows[:RANK_WINDOW]`, and refuses the plain service and dropdown
shapes on real overflow. The service `with_meta` shape reports the structured
flag. Permission-aware `frappe.get_list` is used, and formatting occurs after
windowing/ranking. The genuine fixture test inserts and verifies exactly 5,000
then 5,001 matching Account rows on both paths; it passed live.

The upper page clamp is present on both paths (`MAX_PAGE_LENGTH = 200` in the
service and equivalent 200 clamp in the dropdown), including blank queries.
Large positive page lengths therefore remain bounded.

### Blocking finding

**P1 — caller input normalization is incomplete.** Both implementations use
`page_length = min(int(page_length or 0), MAX_PAGE_LENGTH)` and
`start_i = int(start)` without a lower-bound clamp. A negative `page_length`
remains negative and a negative `start` remains negative, then reaches
`limit_page_length`/`limit_start` (blank path) or Python slicing (text path).
This violates the explicit Round-8 requirement to normalize negative inputs and
leaves pagination semantics dependent on framework/database behavior. Add
permanent tests for negative `page_length`, negative `start`, zero, and
oversize values on both service and dropdown paths; normalize to documented
non-negative values before any query or slice.

## P95 verification

The artifact is hash-bound to the live files:

| File | SHA-256 |
|---|---|
| `construction/services/bilingual_service.py` | `6729793b94a5c6d08bed8c8a7cd19f753ed73ac1d6dd7e6fc6bc39ca5b206f24` |
| `construction/services/bilingual_registry.py` | `691f74feb7fb72bf3a487ce89d5b55bf4512b07584d8a3f9b763530c33df3538` |
| `construction/searchable_dropdown/api/search.py` | `267448da518b348fd7ed6d5df6ff7f7fbc2325711ce83b2a3c9adf62aa070fdd` |

The preserved artifact contains 5 warmups and 50 balanced samples, alternating
pair order with GC paused in the timed region, equal 12-row match sets, and
per-call SQL counts of one. Recomputed nearest-rank P95 and true medians agree:
baseline **2.085 ms / median 1.418 ms**; bilingual **2.234 ms / median 1.479
ms**; overhead **7.14%**, within the owner-approved bare `<= 1.10x` rule and
with no rejected 15 ms floor. Environment binding is present (Frappe 16.18.1,
MariaDB 10.11.14, host/user/company/cardinality and code hashes).

The permanent artifact test and the live comparative test both passed.

## Test and evidence results

`bench --site v16.localhost run-tests --module
construction.tests.test_bilingual_account_pilot` passed **51/51**. This
includes handler-level `execute_cmd` coercion, refusal and boundary tests,
permission checks, normalized-key and Unicode controls, rename/version/comment
controls, HTTP cleanup, and the P95 tests. Reported aggregate evidence remains
213 (`13+6+5+3+8+89+38+51`), catalog 804, extraction `663+21` with zero
missing, inventory 18,445 with Merkle `6fcffc90…`, evidence gate `errors=0`,
lints and `git diff --check` clean; these were not regenerated or modified in
this review.

## Release disposition and next gate

Round 8 is **conditionally verified except for the P1 normalization blocker**.
Before a fresh AI-R review, the builder must normalize negative `start` and
`page_length` consistently on both public paths and add permanent tests proving
the behavior, while preserving the already verified 5,001 probe/refusal/meta
contract and hash-bound bare P95 gate. After that, rerun the complete evidence
suite and provide fresh current hashes/results. Even on verification, owner
authorization remains required for commit, push, merge, deploy, runtime name
migration, or other production mutations.
