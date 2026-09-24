# W6-6 Manufacturing Batch 02 — governed cycle closed (2026-09-24)

## Scope and review

Owner approval applied only to
`stage6_w606_manufacturing_batch02_rows_2026-09-24.csv` (202 rows;
SHA-256 `195c789945cf2b069a1620e855b22ad38aa9cb0adf03b9b2342166c47b6e88ff`)
on the non-production test site `v16.localhost`. Final proposal CSV SHA-256 is
`fde2fa6722c8b69bb87cbdc2c9927cf1a545e0f78f4c3b71f292f567d6f544f5`.
Independent A1/A2/A3 reviews and final AI-R all PASS on those exact hashes.
The proposal was normalized from CRLF to repository-standard LF before commit;
each reviewer rechecked the normalized file and verified that LF→CRLF restores
the earlier reviewed SHA `7dd6bdd85aaf49a89847d038aa740b7fbbf9d6a34945df4cf2a1b4f9137332ec`.
No row values or translations changed.

| Disposition | Rows | Result |
| --- | ---: | --- |
| Released payload | 82 | Imported as release v1.9 |
| Preserved Site Override | 119 | Left unchanged; not imported |
| Technical exception | 1 | `material_request_item`; blank translation retained |
| **Total** | **202** | **82 + 119 + 1** |

The quote-containing Arabic strings are bound through the plain-text content
evidence file (SHA-256 `5881d944f34f94b6eb1721a029128058659a81fe4f0df01db8039f248a15db64`)
so provenance checks compare decoded content rather than CSV-escaped text.
The final applied-row ledger SHA-256 is
`beb8a753393a14614b0b2c57d7f6357fd39797decb11bb01819b98213efd6fae`.

## Test-site execution and verification

- Import: **82 created**, 0 updated; the 119 preserved overrides and one
  technical exception were not imported.
- Post-import dry-run: `total=3326 created=0 updated=0 skipped=3326 drift=0`.
- Translation health: loader installed, no fallback, duplicates, null digests,
  drift, or orphan overrides.
- Arabic Desk UAT preflight: PASS; Redis 13000/11000, `/ping` 200, fresh `ar`
  boot with 13,628 messages and required key, session logged out, language
  restored to `en`, temporary password rotated.
- Browser evidence: `ar`, RTL, Arabic DOM visible, **82/82 exact boot-payload
  matches**, 0 mismatches; technical exception absent. Socket.IO polling
  warnings are documented as a browser transport issue, not a translation
  failure.
- Tests: standalone **92/92**, module suite **271/271**.
- Scoped gate, vendor audit, scope/translation lints, and `git diff --check`:
  PASS; catalog sync: 0 created, 0 updated.
- Inventory: **21,743 rows**, Merkle
  `ed69ebe56d9861caedc0312bfa547b568a7f356f8742a7af9628df39214b6998`,
  `LIVE_MATCH`.
- Ten Stage-2 evidence envelopes and index were atomically assembled on
  candidate HEAD `69b999e5f7d0eb003bc8fd26c1d765dee1de0526`; the evidence-inclusive
  gate exits **0** with `errors=0`, `csv_rows=3326`.
- Final independent AI-R: **PASS**; see
  `docs/ai/work-items/scope-context-portability/evidence/stage6-w606-manufacturing-batch02-ai-r-2026-09-24.md`.

## Boundaries

Only the approved scope ran, only on `v16.localhost`. Production and Stage 8
were not accessed or authorized. The untracked `v16.localhost/` app-root log
directory remains untouched. No push was performed.
