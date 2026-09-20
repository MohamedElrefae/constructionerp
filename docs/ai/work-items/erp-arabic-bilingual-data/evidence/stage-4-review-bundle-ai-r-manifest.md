# Stage 4 review-bundle governed-manifest boundary — independent AI-R review

**Date:** 2026-09-10 (Africa/Cairo)  
**Candidate:** `e7be48855bde540464ea302e53c9bfca62b7c462` with the existing
uncommitted worktree  
**Verdict:** **BLOCKED** — private-export byte verification works for a
given manifest, but the import-facing API accepts an arbitrary caller-supplied
manifest path. A caller can therefore provide a self-created export and a
matching self-created manifest, and obtain a payload containing a foreign
Account identity.

## Artifact identity

| Artifact | Required SHA-256 | Observed SHA-256 | Result |
|---|---|---|---|
| `construction/services/account_review_bundle.py` | `c63448d60a294257322b0dde89a069fce5ba71aad8df8ae29b4bd62e9acabd88` | `c63448d60a294257322b0dde89a069fce5ba71aad8df8ae29b4bd62e9acabd88` | match |
| `construction/services/account_language_proposal.py` | `5dea32f95cd1b4009428dab54a54eed9842d8d7c84a50b5278d35dd9d1ce84b3` | `5dea32f95cd1b4009428dab54a54eed9842d8d7c84a50b5278d35dd9d1ce84b3` | match |
| `construction/tests/test_stage4_review_bundle.py` | `32bfcdb3a4a56de46967bd96a5c03a9e14a62c515ab2c09a7581cb5668105680` | `32bfcdb3a4a56de46967bd96a5c03a9e14a62c515ab2c09a7581cb5668105680` | match |
| `scripts/check_localization_gates.py` | `26319bfcfb2901cf957ed88ada47ec3265ad9101e6ba0b5a2343629939bee283` | `26319bfcfb2901cf957ed88ada47ec3265ad9101e6ba0b5a2343629939bee283` | match |

This is a fresh review of the pinned current hashes. Earlier CandidateExport
reports were not used as this verdict.

## Verified controls

- The default manifest is non-sensitive: it contains export metadata and a
  private path/SHA but no Account rows. The actual private export is re-read
  immediately before payload construction; its SHA-256, JSON schema,
  non-empty rows, unique identities, and English values are checked.
- Against a trusted manifest, the identity-to-English map is derived
  internally. Foreign/duplicate identities, omitted exported identities, and
  English mismatches stop the whole payload.
- Missing/wrong-schema/missing-path/SHA-mismatch manifests and tampered
  exports fail closed. A non-empty malformed `now_utc` fails closed; a valid
  control rejects future timestamps.
- Proposal and AI-A2 reviewer and session independence, timestamp ordering,
  decision/reference rules, exception retention, and whole-bundle refusal
  all function as specified.
- `python3 construction/tests/test_stage4_review_bundle.py` passed: 34 tests.
  `python3 scripts/check_localization_gates.py` passed with `errors=0`
  (catalog 805; wrapped 664; JSON labels 21; missing 0).

## Blocking finding

### P0 — caller-controlled `manifest_path` is still authority

`build_import_payload(bundle, manifest_path=None, now_utc=None)` calls
`_load_governed_manifest(manifest_path)` whenever the caller supplies a
non-empty path. It checks only that the file is structurally valid, then
trusts the export path and SHA contained in that caller-selected file. The
manifest SHA therefore proves only that the caller's arbitrary export is
self-consistent; it does not bind the result to the governed Stage 4 export.

This exact bypass was reproduced without changing any Account or translation
data: a temporary export containing only `9999 - Forged - E` and a matching
temporary manifest were supplied as `manifest_path`. The function returned:

```text
ARBITRARY_MANIFEST_ACCEPTED
[{"identity": "9999 - Forged - E", "arabic": "مزور"}]
```

Object/dictionary rejection is insufficient because an attacker can pass a
string filesystem path. Symlink/path-normalization checks would not repair
this: the problem is selection of the trust root itself.

## Required repair

The import-facing public boundary must always resolve and verify the one
governed manifest location itself. Do not accept an arbitrary `manifest_path`
from an endpoint/caller. Remove that public parameter, or make any test-only
injection private and ensure production calls reject every non-default path
after realpath comparison. Tests may monkeypatch the internal resolver rather
than expose caller manifest selection.

Treat the governed manifest as deployment-controlled provenance: document its
ownership/change-control and reject manifest paths outside that fixed root.
Add a permanent regression that recreates the above temporary export/manifest
bypass and proves it is refused. Retest the default-manifest path and all
whole-bundle failure behavior afterward.

## Required disposition

Stage 4 remains at the review-bundle stop gate. Do not accept proposal or
AI-A2 output for owner approval, dry-run, or authorized import until the P0
is repaired and independently re-reviewed. This review made no implementation,
business-data, Git, deployment, or import change.
