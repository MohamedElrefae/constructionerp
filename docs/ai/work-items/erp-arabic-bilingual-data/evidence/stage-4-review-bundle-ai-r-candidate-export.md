# Stage 4 review-bundle CandidateExport — independent AI-R review

**Date:** 2026-09-10 (Africa/Cairo)  
**Candidate:** `e7be48855bde540464ea302e53c9bfca62b7c462` with the existing
uncommitted worktree  
**Verdict:** **BLOCKED** — the new loader validates a real private export,
but `CandidateExport` is publicly constructible and mutable. Consequently,
the payload boundary can still receive a forged `CandidateExport` and emit a
foreign Account identity without reading or SHA-verifying the private export.

## Artifact identity

| Artifact | Required SHA-256 | Observed SHA-256 | Result |
|---|---|---|---|
| `construction/services/account_review_bundle.py` | `e5fc2ea6f8f4c32c1622730ab49762e8f0201fb1587465ba4f9b3da88191309a` | `e5fc2ea6f8f4c32c1622730ab49762e8f0201fb1587465ba4f9b3da88191309a` | match |
| `construction/tests/test_stage4_review_bundle.py` | `556d294b637f2745d9f98392690412aaa7c28e75c6f40d47ebb89f991485f624` | `556d294b637f2745d9f98392690412aaa7c28e75c6f40d47ebb89f991485f624` | match |
| `scripts/check_localization_gates.py` | `41c0e2d3e7577c5c4c962ffc7c90e2fb4a8adde45630d9111a8e6deeb2c34d68` | `41c0e2d3e7577c5c4c962ffc7c90e2fb4a8adde45630d9111a8e6deeb2c34d68` | match |

This is a fresh review of those hashes. The earlier `c96c5c29…` report was
not used as this verdict.

## Verified controls

- `load_candidate_from_export()` rejects missing exports, missing or wrong
  SHA values, altered bytes, invalid JSON/schema, empty exports, duplicate
  identities, and missing English values. Its mapping is correctly derived
  from bytes whose SHA equals the supplied expected SHA.
- A bundle validated against a loader-produced candidate rejects foreign and
  duplicate identities, silently omitted candidate identities, and English
  mismatches. `build_import_payload()` rejects plain lists and dictionaries.
- Invalid non-empty `now_utc` is fail-closed; a valid bound rejects future
  proposal/review timestamps. `now_utc=None` is the explicit opt-out.
- Proposal and AI-A2 reviewer **and** session must differ. Timestamp order,
  required confidence/rationale, approved/exception decisions, verified or
  explicitly absent references, exception retention, and whole-bundle
  refusal work as specified.
- The module is pure/stdlib-only; this review made no Account, translation,
  import, Git, or deployment change.

## Blocking finding

### P0 — `CandidateExport` is forgeable at the import boundary

The code documents that only `load_candidate_from_export()` can create a
candidate, but `CandidateExport` is a public class with a public constructor
and public mutable `identities` dictionary. `build_import_payload()` checks
only `isinstance(candidate, CandidateExport)`. It never proves that the
object was created by the loader or that its mapping still corresponds to the
private export SHA.

This reproduces the bypass without reading a private export or changing any
data:

```python
forged = rb.CandidateExport(
    "/not/private-export.json", "0" * 64, "Elrefae",
    {"FORGED-9999": "Forged English"}, 1, rb.EXPORT_SCHEMA,
)
result = rb.build_import_payload(valid_bundle_for("FORGED-9999"), forged,
                                 now_utc="2026-09-10T12:00:00Z")
assert result["payload"] == [{"identity": "FORGED-9999", "arabic": "مزور"}]
```

The exact reproduction ran and printed `BYPASS_CONFIRMED` with the forged
identity and an all-zero candidate SHA. An authenticated candidate can also
have `candidate.identities` mutated after loading, because it is an exposed
dictionary.

### Required repair

Make the import boundary authenticate the candidate bytes itself against the
governed private-export manifest, rather than treating an object type as the
authority. A suitable design is an import-facing function that accepts the
private export path plus a trusted manifest record (including the exact
recorded SHA), reloads and verifies the bytes immediately before building the
payload, and derives the identity-to-English mapping internally. Do not
expose a public mutable candidate constructor/mapping as sufficient evidence.
Add regressions proving that direct construction and post-load mapping
mutation cannot emit a payload.

The expected SHA must itself come from a governed manifest/owner-approved
record, not merely a caller-provided hash for arbitrary bytes; otherwise a
caller can hash a self-created export and call the loader legitimately.

## Reproduction

```text
sha256sum construction/services/account_review_bundle.py \
  construction/tests/test_stage4_review_bundle.py scripts/check_localization_gates.py
# all three required hashes matched

python3 construction/tests/test_stage4_review_bundle.py
# Ran 33 tests ... OK

bench --site v16.localhost run-tests --module construction.tests.test_stage4_review_bundle
# Ran 33 tests ... OK

python3 scripts/check_localization_gates.py
# errors=0; catalog 805; wrapped 664; JSON labels 21; missing 0
```

## Required disposition

Stage 4 remains at the review-bundle stop gate. Do not allow independent
proposal/AI-A2 output to become eligible for owner approval or an authorized
test-site import until the candidate-export P0 is repaired and independently
reviewed again.
