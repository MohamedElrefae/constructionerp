# Stage 4 review-bundle fixed governed-path — independent AI-R review

Date: 2026-09-10  
Candidate HEAD: `e7be48855bde540464ea302e53c9bfca62b7c462` (uncommitted worktree)  
Verdict: **VERIFIED**

This is a fresh review of the current fixed-path boundary. It does not rely
on the earlier manifest-path report or its pre-fix artifacts. No Account,
translation, proposal, review-bundle, database, Git, or deployment state was
modified during this review.

## Reviewed artifacts

| Artifact | Required SHA-256 | Actual SHA-256 | Result |
|---|---|---|---|
| `construction/services/account_review_bundle.py` | `dd3bbf692391198897b11f34b0efcf9936e5817d2db9e6b4092407c084c74a74` | `dd3bbf692391198897b11f34b0efcf9936e5817d2db9e6b4092407c084c74a74` | Match |
| `construction/tests/test_stage4_review_bundle.py` | `3fa0b7aeecb8895eee56a336e1844985c417ca63e8461b7cea92342abc23ec6e` | `3fa0b7aeecb8895eee56a336e1844985c417ca63e8461b7cea92342abc23ec6e` | Match |
| `scripts/check_localization_gates.py` | `aaae4f3678a70d2adf1ed25b96c01b2e7639827891e8d38732ee3b9b23b6fa7c` | `aaae4f3678a70d2adf1ed25b96c01b2e7639827891e8d38732ee3b9b23b6fa7c` | Match |

## Authority boundary

`build_import_payload` has exactly the public signature
`(bundle, now_utc=None)`. Its public parameters contain no manifest path,
candidate object, identity map/list, English map, or SHA. Passing each of
`manifest_path`, `candidate`, `expected_identities`, `expected_english`, and
`expected_sha256` as a keyword produced `TypeError`.

The public entry resolves only the private `_governed_manifest_path()` value:
`construction/data/localization/stage4_export_manifest.json`. It then loads
that manifest, reloads the referenced absolute private export immediately,
recomputes its SHA-256, and compares it to the manifest before parsing rows.
The current governed export SHA matched its manifest. Identity-to-English
binding is derived from those verified export rows internally; no caller
authority is accepted.

The test injection seam is limited to monkeypatching the private resolver in
the test module. It does not create a production parameter or public API
route. As with any Python process, code with arbitrary in-process monkeypatch
or filesystem-write authority is already trusted application-code authority;
that is not a caller-controlled payload path.

## Adversarial results

- A forged `9999 - Forged - E` row against the real production governed path
  was refused: `BundleError`, including the foreign identity and the omitted
  authentic export identities.
- Missing/non-path manifest, wrong schema, missing export path, tampered
  export bytes, and manifest SHA mismatch are refused by the focused suite.
- Extra, omitted, duplicate, and English-mismatched identities are refused;
  every exported identity must occur exactly once.
- Malformed non-empty `now_utc` is a violation and prevents payload output;
  valid `now_utc` rejects future proposal or AI-A2 timestamps.
- The suite verifies ordered proposal/AI-A2 timestamps, distinct reviewer and
  session provenance, required confidence/decision/rationale, verified
  references or explicitly flagged absence, exception preservation, and
  all-or-nothing payload refusal.

`approved` and `exception` rows both remain reviewable in the in-memory
payload and exceptions are carried in the returned manifest. This matches the
documented contract: exceptions are not silently dropped. The function
performs no database write.

## Reproduction

```text
python3 construction/tests/test_stage4_review_bundle.py
# Ran 36 tests ... OK

bench --site v16.localhost run-tests --module construction.tests.test_stage4_review_bundle
# Ran 36 tests ... OK

python3 scripts/check_localization_gates.py
# errors=0; catalog 805; wrapped 664; JSON labels 21; missing 0
```

`git diff --check` also passed after the review report was added.

## Gate outcome

The fixed governed-manifest path closes the prior P0: callers cannot select a
manifest, candidate, mapping, or SHA, and a forged bundle cannot reach an
import payload over the production path. The review-bundle validator is
eligible for the separate independent proposal and AI-A2 sessions to populate
it. Owner approval, dry-run, explicitly authorized test-site import,
post-import verification, and deployment remain separate blocked gates.
