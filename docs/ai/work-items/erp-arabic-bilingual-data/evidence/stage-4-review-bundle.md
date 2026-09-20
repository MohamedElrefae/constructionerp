# Stage 4 — Governed review-bundle schema + validator (builder record)

Date: 2026-09-10 · HEAD: `e7be48855bde540464ea302e53c9bfca62b7c462` (uncommitted)
Engineering-only, non-mutating, fail-closed.

## What was engineered

`construction/services/account_review_bundle.py` — pure, stdlib-only
contract for the independent proposal + AI-A2 workflow:

- `BUNDLE_SCHEMA = "construction-stage4-account-review-bundle/v1"`,
  `WORKFLOW = independent-proposal -> ai-a2-review -> owner-approval ->
  dry-run -> authorized import`.
- `bundle_template()` — empty scaffold; never pre-fills Arabic values or
  decisions.
- `validate_bundle(bundle)` — fail-closed validation of every row:
  - **proposal** block: non-empty `arabic`, `confidence`, and
    `provenance` (reviewer/model/session/submitted_utc);
  - **AI-A2** block: `decision` in `{approved, exception}`, `confidence`,
    `rationale`, and a `reference` that is either
    `status: verified` with `value` + `source` (references must never be
    invented) or `status: absent` with the explicit
    `no_verified_reference` flag;
  - **independence**: distinct proposal vs AI-A2 `session` AND distinct
    `reviewer` (a proposal cannot approve itself);
  - timestamps present, valid `YYYY-MM-DDTHH:MM:SSZ`, and
    proposal <= AI-A2 review;
  - no duplicate identities.
- **Exceptions preserved**: `exception` decisions are surfaced in
  `reviewable_exceptions` (never silently excluded).
- `build_import_payload(bundle)` — fail-closed: raises `BundleError` on ANY
  violation; otherwise returns an in-memory payload (`identity` + approved
  `arabic` only) plus a manifest (bundle SHA-256, counts, reviewable
  exceptions). **No database write occurs.**

`construction/tests/test_stage4_review_bundle.py` — 18 tests (pure, runs
standalone and via bench) covering: valid pass; empty template; missing
schema; invented/missing Arabic; missing decision/confidence; reference must
be verified-or-explicit-absence; verified requires value+source; absent
requires the explicit flag; explicit absence acceptable; independence;
timestamp order; duplicate identity; exceptions preserved; payload emitted
only when valid and refused on any violation; manifest hash/exceptions;
rollback note.

## Fail-closed guarantees proven

- No import payload without distinct proposal and AI-A2 provenance.
- No payload without a decision, confidence, and either a verified
  authoritative reference or an explicitly documented absence.
- Exceptions remain reviewable rows.
- No Arabic values are invented or defaulted; no DB mutation.

## Rollback note

`account_review_bundle.rollback_note()` — rollback = delete the two new
(untracked) files, `account_review_bundle.py` and
`test_stage4_review_bundle.py`. No database state to reverse.

## Validation

- Standalone `python3 construction/tests/test_stage4_review_bundle.py` →
  18/18 OK; via bench → 18/18 OK.
- Aggregate now 250 (13+6+5+3+8+89+38+53+6+11+18) all green; standalone
  89/89; catalog 805 / `664 + 21` / 0 missing; inventory 18,446 rows root
  `2e284695…` live-matched; evidence-enabled gate errors=0; lints +
  `git diff --check` clean.

## Still blocked / separate gates

Independent AI proposal generation, the separate AI-A2 review session
(fills the bundle), owner approval of the reviewed payload, dry-run +
explicitly authorized test-site import, and post-import verification.

---

## Round 2 (2026-09-10) — AI-R review fixes

AI-R BLOCKED on two required fixes; both are closed:

1. **Mandatory candidate bindings**: `build_import_payload(bundle,
   expected_identities, expected_english, now_utc=None)` now REQUIRES the
   private export's identity set and `{identity: english}` map (empty or
   missing → `BundleError`), so a forged or self-supplied identity can never
   reach a payload. Forged-identity and empty-binding tests added.
2. **Malformed `now_utc` fails closed**: a non-empty unparseable `now_utc`
   now produces a violation (`now_utc is not a valid … timestamp … control
   cannot be silently disabled`) and therefore refuses the payload; only
   `now_utc=None` disables the control. Malformed + future-timestamp tests
   added.

Suite now 27 tests; aggregate 259
(13+6+5+3+8+89+38+53+6+11+27). Reviewer/session independence, reference
rules, exception preservation, and normal timestamp ordering were already
verified and are unchanged.

Updated reviewer hashes:
- `construction/services/account_review_bundle.py` — `c96c5c29f120da9e08f868f8856f8865ff2d92cdf5d1f4ca1caf3aa395f850df`
- `construction/tests/test_stage4_review_bundle.py` — `9ca17740452287598680e31f90418cb9e47535e0db9508465259641319e3e3f5`
- `scripts/check_localization_gates.py` — `7d1ffe3fc1624a3f070ad7777e1c605a70748189c5ed70af60bcaa96c8a97e8f`

---

## Round 3 (2026-09-10) — AI-R re-review P0 fix

AI-R re-review BLOCKED on one P0: the required bindings were still
caller-supplied lists/maps, so the payload could not prove it came from the
private Stage 4 export. Fixed by replacing them with ONE authenticated
candidate object:

- `CandidateExport` — only constructible by `load_candidate_from_export(
  export_path, expected_sha256)`, which reads the private export file and
  requires the computed SHA-256 to equal the recorded value (tampered,
  substituted, missing, wrong-schema, or duplicate-identity exports raise
  `BundleError`). The object carries the exact identity→English mapping.
- `build_import_payload(bundle, candidate, now_utc=None)` — refuses anything
  that is not a `CandidateExport` (raw lists/maps rejected), then binds
  `expected_identities`/`expected_english` from the candidate and rejects
  missing, extra, or forged mapping keys and mismatched English values. The
  manifest records `candidate_export_sha256`, path, company, and identity
  count.

Tests now 33 (added authenticated-candidate coverage: missing file/recorded
SHA, tampered bytes, wrong schema, duplicate identity, extra/missing keys,
plain-dict forgery). Aggregate 265. The malformed-`now_utc` fix and all other
reviewed controls are unchanged and still pass.

Updated reviewer hashes:
- `construction/services/account_review_bundle.py` — see package
- `construction/tests/test_stage4_review_bundle.py` — see package
- `scripts/check_localization_gates.py` — see package

---

## Round 4 (2026-09-10) — AI-R P0: governed-manifest reload at the payload boundary

AI-R reproduced a forged identity reaching a payload because `CandidateExport`
was publicly constructible/mutable and the caller supplied its own SHA.
Fixed by removing any caller object/SHA as authority:

- The export step (`account_language_proposal.export_account_catalog`) now
  persists a GOVERNED, non-sensitive manifest at
  `construction/data/localization/stage4_export_manifest.json`
  (`construction-stage4-export-manifest/v1`) recording the absolute private
  export path and its SHA-256 — no account rows.
- `build_import_payload(bundle, manifest_path=None, now_utc=None)` now:
  1. loads the governed manifest (default: the app manifest),
  2. **itself reloads the private export from disk** immediately before
     payload construction,
  3. verifies the bytes against the manifest's recorded SHA-256,
  4. derives the identity→English map INTERNALLY,
  5. rejects missing/extra/forged mapping keys and English mismatches.
  A caller cannot supply an object, a mapping, or a SHA. Raw objects/dicts
  as paths are refused; missing manifest, wrong manifest schema, tampered
  export bytes, and manifest SHA mismatch all raise `BundleError`.

Tests now 34 (added a signature-authority test proving no
`candidate`/`expected_*` parameters exist; forged-identity, caller-object,
missing/wrong-schema/tampered manifest, extra/missing key coverage).
Aggregate 266.

Updated reviewer hashes:
- `construction/services/account_review_bundle.py` — `c63448d60a294257322b0dde89a069fce5ba71aad8df8ae29b4bd62e9acabd88`
- `construction/services/account_language_proposal.py` — `5dea32f95cd1b4009428dab54a54eed9842d8d7c84a50b5278d35dd9d1ce84b3`
- `construction/tests/test_stage4_review_bundle.py` — `32bfcdb3a4a56de46967bd96a5c03a9e14a62c515ab2c09a7581cb5668105680`
- `scripts/check_localization_gates.py` — `26319bfcfb2901cf957ed88ada47ec3265ad9101e6ba0b5a2343629939bee283`

---

## Round 5 (2026-09-10) — AI-R P0: remove caller-selectable manifest path

AI-R created its own manifest/export pair and emitted a forged payload via
the `manifest_path` parameter. Fixed:

- The PUBLIC production entry point is now
  `build_import_payload(bundle, now_utc=None)` — it accepts NO path, object,
  mapping, or SHA. It resolves exactly one INTERNAL governed manifest via the
  private resolver `_governed_manifest_path()` (fixed app path
  `construction/data/localization/stage4_export_manifest.json`), then reloads
  and SHA-verifies the private export behind it.
- Test-only dependency injection is isolated on the private
  `_governed_manifest_path` resolver (monkeypatched in tests); the public
  entry exposes no seam. Passing `manifest_path=` raises `TypeError`.
- A test asserts the production entry uses the real governed manifest
  (a forged bundle identity is refused without any injection), plus the
  signature has no banned parameters.

Suite now 36 tests; aggregate 268
(13+6+5+3+8+89+38+53+6+11+36).

Updated reviewer hashes:
- `construction/services/account_review_bundle.py` — `dd3bbf692391198897b11f34b0efcf9936e5817d2db9e6b4092407c084c74a74`
- `construction/tests/test_stage4_review_bundle.py` — `3fa0b7aeecb8895eee56a336e1844985c417ca63e8461b7cea92342abc23ec6e`
- `scripts/check_localization_gates.py` — `aaae4f3678a70d2adf1ed25b96c01b2e7639827891e8d38732ee3b9b23b6fa7c`
