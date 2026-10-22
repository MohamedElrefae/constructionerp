# Stage 4 review-bundle contract — independent AI-R re-review

**Date:** 2026-09-10 (Africa/Cairo)  
**Candidate:** `e7be48855bde540464ea302e53c9bfca62b7c462` with the existing
uncommitted worktree  
**Verdict:** **BLOCKED** — the two reported repairs work at the supplied
parameter boundary, but the payload builder still accepts an entirely
self-supplied candidate identity/English binding. It therefore cannot prove
that an emitted identity belongs to the private Stage-4 export.

## Artifact identity

| Artifact | Required SHA-256 | Observed SHA-256 | Result |
|---|---|---|---|
| `construction/services/account_review_bundle.py` | `c96c5c29f120da9e08f868f8856f8865ff2d92cdf5d1f4ca1caf3aa395f850df` | `c96c5c29f120da9e08f868f8856f8865ff2d92cdf5d1f4ca1caf3aa395f850df` | match |
| `construction/tests/test_stage4_review_bundle.py` | `9ca17740452287598680e31f90418cb9e47535e0db9508465259641319e3e3f5` | `9ca17740452287598680e31f90418cb9e47535e0db9508465259641319e3e3f5` | match |
| `scripts/check_localization_gates.py` | `7d1ffe3fc1624a3f070ad7777e1c605a70748189c5ed70af60bcaa96c8a97e8f` | `7d1ffe3fc1624a3f070ad7777e1c605a70748189c5ed70af60bcaa96c8a97e8f` | match |

## Verified repairs and retained controls

- `build_import_payload` now has required `expected_identities` and
  `expected_english` arguments; omitted arguments raise `TypeError`, while
  empty bindings raise `BundleError`.
- A malformed non-`None` `now_utc` creates a violation and the payload path
  raises `BundleError`; a valid bound rejects future proposal/review times.
  `now_utc=None` intentionally disables only the future-time comparison. That
  behavior is explicit in the function signature and does not silently turn a
  malformed supplied bound into `None`.
- Distinct proposal/AI-A2 reviewer and session, reference status/value/source
  rules, timestamp ordering, duplicate detection, and whole-bundle refusal
  remain enforced.
- `approved` and `exception` rows are both validated; exception identities are
  retained in `reviewable_exceptions` and counted in the returned manifest.
- The focused standalone and Bench tests both report 27 passing tests; the
  localization gate reports `errors=0`; `git diff --check` exits zero.

## Blocking finding

### P0 — caller can manufacture the mandatory candidate bindings

Making two arguments mandatory does not bind them to the private export. A
caller can submit a foreign row and supply matching values in both mandatory
arguments. The current builder emits an import payload:

```python
forged = good_row(identity="9999 - Forged - E")
forged["english"] = "Forged English"
rb.build_import_payload(
    bundle_with(forged),
    ["9999 - Forged - E"],
    {"9999 - Forged - E": "Forged English"},
)["payload"]
# [{"identity": "9999 - Forged - E", "arabic": "نقدية"}]
```

There is also no requirement that the supplied English map cover every
expected identity: a non-empty map with only unrelated keys leaves the known
row's English value unchecked. The contract says the private export's
candidate identity and English value must bind the payload, including complete
coverage. Current ordinary lists/dicts are only caller assertions, not a
verifiable export binding.

Repair this by accepting a single candidate-export object/manifest that
contains the exact identity-to-English mapping and is authenticated against
the private export (for example, an expected export SHA-256 or trusted
private-file loader). Require its map keys to equal the candidate identity
set, reject unknown/missing keys, and make `build_import_payload` use that
verified object rather than independent caller-controlled values. Add
regressions for (1) a fully self-supplied forged set/map and (2) a non-empty
English map missing one expected identity. Do not emit a payload until these
fail.

## Reproduction

```text
sha256sum construction/services/account_review_bundle.py \
  construction/tests/test_stage4_review_bundle.py scripts/check_localization_gates.py
# all required hashes matched

python3 construction/tests/test_stage4_review_bundle.py
# Ran 27 tests ... OK

bench --site v16.localhost run-tests --module construction.tests.test_stage4_review_bundle
# Ran 27 tests ... OK

python3 scripts/check_localization_gates.py
# errors=0; catalog 805; wrapped 664; JSON labels 21; missing 0

git diff --check
# exit 0
```

No Arabic proposal/review approval, import, Account update, translation
mutation, commit, push, deployment, or Git cleanup was performed during this
review.

## Required disposition

Stage 4 remains at the review-bundle stop gate. The independent proposal and
AI-A2 sessions may not treat a bundle as eligible for owner approval or a
test-site import until the export binding P0 is repaired and independently
re-reviewed.
