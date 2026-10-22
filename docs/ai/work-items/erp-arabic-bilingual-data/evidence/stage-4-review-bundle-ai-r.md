# Stage 4 review-bundle contract — independent AI-R review

**Date:** 2026-09-10 (Africa/Cairo)  
**Candidate:** `e7be48855bde540464ea302e53c9bfca62b7c462`, with the existing
uncommitted Stage 1–4 worktree changes  
**Verdict:** **BLOCKED** — the proposed import-payload boundary can be called
without the exported candidate identity and English-value bindings, so it is
not fail-closed for the stated identity-completeness contract.

## Artifact identity

The review-package hashes match the bytes inspected:

| Artifact | SHA-256 | Result |
|---|---|---|
| `construction/services/account_review_bundle.py` | `7c5d1785ca7ff31c482effef69ab52076c445b65ad199b09bd3a13fd929dbce7` | match |
| `construction/tests/test_stage4_review_bundle.py` | `aa87ac2d655da3f37e23e21ed6e1886b87a1005bb493e820727b556514d57e80` | match |
| `scripts/check_localization_gates.py` | `475ba807bf2fb466ef82dca050105e026a32788f8053aa5df8a5be45e9bf84c6` | match |

## Verified controls

- `bundle_template()` supplies no Arabic value, identity, or AI-A2 decision.
- With a supplied candidate set, `validate_bundle()` rejects foreign and
  duplicate identities, reports omitted expected identities, and compares
  English values where supplied.
- Proposal and AI-A2 provenance require distinct reviewer and session values.
- Row timestamps use the documented UTC format and proposal-after-review is
  refused. Supplied future timestamps are refused when `now_utc` parses.
- Both `approved` and `exception` decisions require confidence, rationale,
  and a verified reference or explicitly flagged absence. Exceptions remain
  in `reviewable_exceptions` and the returned manifest.
- The module is pure/stdlib-only; no database or report data was mutated.

## Blocking findings

### P0 — candidate identity and English bindings are optional at the payload boundary

`build_import_payload()` defaults `expected_identities`, `expected_english`,
and `now_utc` to `None` (lines 247–255). Therefore a caller can emit a
payload for a self-supplied, foreign identity without proving it belongs to
the private Stage-4 export or that its English value is current. This directly
defeats the required rule that every exported identity occur exactly once and
that English identity/content binding gate payload creation.

Reproduced without modifying data:

```python
bundle = {"schema": rb.BUNDLE_SCHEMA, "rows": [valid_row_for("forged-id")]}
rb.build_import_payload(bundle)["payload"]
# [{"identity": "forged-id", "arabic": "اختبار"}]
```

The existing `test_payload_emitted_only_when_valid` intentionally calls the
same unbound path, so the 23-test suite currently encodes the bypass rather
than preventing it. Identity binding must be mandatory for any payload-build
entry point, preferably via a verified private-export manifest/candidate
object that contains identity and English values together. Add negative tests
for omitted candidate binding, a foreign identity with only an English map,
and an omitted expected identity. Do not rely on call-site convention.

### P1 — malformed `now_utc` silently disables the future-time gate

`validate_bundle(..., now_utc="not-a-timestamp")` parses to `None` and
returns no violation for otherwise valid rows. The package describes
future-time checking as fail-closed when a time bound is supplied, but an
invalid supplied bound currently behaves like no bound. Reject a non-empty,
invalid `now_utc` explicitly and add a regression test. A safe default current
UTC bound (or a mandatory caller-supplied bound at the payload boundary) is
also needed once P0 is fixed.

`created_utc` remains a scaffold field only. This is not independently
blocking if it is deliberately non-authoritative, but the contract should say
so; otherwise validate its format and its relation to proposal/review times.

## Commands run

```text
sha256sum construction/services/account_review_bundle.py \
  construction/tests/test_stage4_review_bundle.py scripts/check_localization_gates.py
# all three hashes matched the review package

python3 construction/tests/test_stage4_review_bundle.py
# Ran 23 tests ... OK

bench --site v16.localhost run-tests --module construction.tests.test_stage4_review_bundle
# Ran 23 tests ... OK

python3 scripts/check_localization_gates.py
# errors=0; catalog 805; wrapped 664; JSON labels 21; missing 0

git diff --check
# exit 0
```

The focused suite and localization gate are green, but they do not establish
that the import boundary is bound to the authorized export candidate. No
proposal, AI-A2 approval, import, Account-name update, translation mutation,
commit, push, or deployment was performed during this review.

## Required disposition

Stage 4 remains at the review-bundle stop gate. Repair and independently
re-review the P0 before any independent proposal/AI-A2 bundle is treated as
eligible for owner approval or an authorized test-site import.
