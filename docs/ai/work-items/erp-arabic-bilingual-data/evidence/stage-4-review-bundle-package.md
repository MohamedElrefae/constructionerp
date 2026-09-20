# Stage 4 — Review-bundle schema/validator: AI-R review package

Date: 2026-09-10 · HEAD: `e7be48855bde540464ea302e53c9bfca62b7c462` (uncommitted)
Purpose: request an **independent AI-R review** of the review-bundle schema
and validator BEFORE it is relied on for any import. This file is the
builder's review package; the builder does not self-verify.

## Exact reviewed artifacts (SHA-256)

| Artifact | SHA-256 |
|---|---|
| `construction/services/account_review_bundle.py` | `dd3bbf692391198897b11f34b0efcf9936e5817d2db9e6b4092407c084c74a74` |
| `construction/tests/test_stage4_review_bundle.py` | `3fa0b7aeecb8895eee56a336e1844985c417ca63e8461b7cea92342abc23ec6e` |
| `scripts/check_localization_gates.py` | `aaae4f3678a70d2adf1ed25b96c01b2e7639827891e8d38732ee3b9b23b6fa7c` |

## Requested review focus

1. **Identity binding**
   - `validate_bundle(bundle, expected_identities=..., expected_english=..., now_utc=...)`:
     bundle identities must belong to the exported/candidate set; every
     expected identity must appear exactly once (a silently omitted exported
     account is a violation, not acceptable); `expected_english` prevents
     identity/content mix-ups; duplicate identities rejected.
2. **Timestamp ordering**
   - `proposal.submitted_utc <= a2_review.reviewed_utc`; both must be valid
     `YYYY-MM-DDTHH:MM:SSZ`; when `now_utc` is supplied, future timestamps
     are refused. Check whether bundle-level `created_utc` ordering should
     also be enforced.
3. **Exception handling**
   - `decision in {approved, exception}`; both validated identically;
     exceptions surfaced in `reviewable_exceptions` and counted in the
     manifest (never silently excluded); payload includes exception rows
     (the value is imported with a recorded exception).
4. **Refusal behavior**
   - `build_import_payload` validates the ENTIRE bundle first and raises
     `BundleError` on any violation — no partial payload; identity binding,
     reference rules, independence, and time bounds all gate the payload.

## Contract summary

- Proposal block: non-empty `arabic` (never invented/defaulted here),
  `confidence`, and provenance (reviewer/model/session/submitted_utc).
- AI-A2 block: `decision ∈ {approved, exception}`, `confidence`,
  `rationale`, `reference` either `verified` (value+source required;
  references must never be invented) or `absent` with the explicit
  `no_verified_reference` flag; provenance (reviewer/model/session/
  reviewed_utc).
- Independence: proposal vs AI-A2 must use DISTINCT `session` AND DISTINCT
  `reviewer` (a proposal cannot approve itself).
- No database write anywhere in this module.

## Reproduce the evidence

```
python3 construction/tests/test_stage4_review_bundle.py            # -> Ran 36 tests OK
bench --site v16.localhost run-tests --module construction.tests.test_stage4_review_bundle
python3 scripts/check_localization_gates.py                        # -> errors=0
```

## Current green state

- 23 review-bundle tests (standalone + bench); aggregate 268
  (13+6+5+3+8+89+38+53+6+11+36) all green.
- Catalog 805; extraction `664 + 21`; missing 0. Inventory 18,446 rows root
  `2e284695…` live-matched. Evidence-enabled gate `errors=0`. Lints +
  `git diff --check` clean.

## Round-5 fix (AI-R manifest review)

- The public entry point is now `build_import_payload(bundle,
  now_utc=None)` with NO caller-selectable manifest path/object/SHA. It
  resolves exactly one internally governed manifest via the private
  `_governed_manifest_path()`; test DI lives only on that private resolver.

## Round-4 fix (AI-R candidate-export review)

- Removed `CandidateExport`/caller-SHA as authority. `build_import_payload`
  now reloads the private export itself and verifies it against the GOVERNED
  manifest (`construction/data/localization/stage4_export_manifest.json`,
  which records the absolute export path + SHA-256, no rows), deriving the
  identity->English map internally. Caller object/mapping/SHA is refused.

## Round-3 fix (AI-R re-review)

- Replaced caller-supplied identity/English lists with a single
  authenticated `CandidateExport` produced only by
  `load_candidate_from_export(export_path, expected_sha256)` — the exact
  identity→English mapping is integrity-bound to the private export's
  SHA-256. `build_import_payload` refuses raw lists/maps and rejects missing,
  extra, or forged mapping keys and mismatched English values.

## Round-2 fix (AI-R review)

- `build_import_payload` now REQUIRES `expected_identities` and
  `expected_english`; missing/empty bindings raise `BundleError` (no forged
  identity can reach a payload).
- A malformed non-empty `now_utc` now fails closed (violation + payload
  refusal) instead of silently disabling the future-timestamp control.

## Explicitly out of scope / still blocked

Independent proposal population, the separate AI-A2 review session, owner
approval of the reviewed payload, dry-run + explicitly authorized test-site
import, and post-import verification. No Account or translation data was
mutated by this work.
