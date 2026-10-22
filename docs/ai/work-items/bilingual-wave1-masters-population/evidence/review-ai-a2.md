# AI-A2 independent review record — bilingual-wave1-masters-population

**Date:** 2026-10-04 · **Site:** `v16.localhost` (non-production test)
**Privacy (SCOPE R4):** proposed values are stored privately at
`sites/v16.localhost/private/wave1-population/proposal.json` (v3, sha256
`a00cfb432ed6680eefb20f22cc852923f059ff9320533569cdb57791e1cd1c77`) and were presented to the
owner in-session for approval. This committed record carries verdicts, evidence references and
per-row value digests only — **no Arabic values are committed** (short digest16 = sha256 of the
UTF-8 value, first 16 hex chars).

## Independence chain (SCOPE R2)

| Round | Session | Scope | Outcome |
|---|---|---|---|
| 1 | `ses_ef7495b37ffepb8rEAJCi1dkLp` (independent AI-A2) | all 9 rows vs proposal v1 (`17e915bf…4db`) | 6 approve, 3 revise (SUBCONCRETE-001, PLANT-MIXER-001, LAB-MASON-001\`) |
| 2 | `ses_ef72e5d17ffer37Yjm4bEnWFpP` (independent AI-A2, fresh session) | the 3 revised rows vs proposal v2 (`3f8e2414…6a8b`) | 2 approve, 1 revise (SUBCONCRETE-001 — glossary-mandated subcontract marker) |
| 3 | `ses_ef727c1c6ffe70nbWa5bdKctDy` (independent AI-A2, fresh session) | the final SUBCONCRETE-001 string (not authored by this session) | approve, high |

The proposal was authored in the build session; **every final value was approved by an AI-A2
session that did not author it.** Reviewer rationales quote proposed values and therefore live
in the session transcripts + the private review record
`sites/v16.localhost/private/wave1-population/review-ai-a2.json` (sha256
`c613ff8e8c8260450491c436fa00d4f5f76838e422afce926ff2f669146f76f4`).

## Final verdicts (proposal v3)

| # | Doctype | Row identity | Round | Verdict | Confidence | Value sha256[:16] |
|---|---|---|---|---|---|---|
| 1 | Item | `OH-SITE-ADMIN-001` | 1 | approve | high | `13666ed4f66bfa57` |
| 2 | Item | `SUBCONCRETE-001` | 3 | approve | high | `1b80f074c87c8080` |
| 3 | Item | `PLANT-MIXER-001` | 2 | approve | high | `50d1e344fe50ca76` |
| 4 | Item | `` LAB-MASON-001` `` | 2 | approve | high | `0d02acd46129f85f` |
| 5 | Item | `Consulting` | 1 | approve | high | `fa885dabcf8c2fad` |
| 6 | Item | `Macbook Pro` | 1 | approve | high | `adc27f0950fdd164` |
| 7 | Item | `Photocopier` | 1 | approve | high | `b2473ec598a4a1ad` |
| 8 | Item | `138-CMS Shoe` | 1 | approve | medium | `5bcd54e8ded93cd3` |
| 9 | Customer | `Prestiga-Biz` | 1 | approve | high | `3f5981c0b6a5cf03` |

## Reviewer evidence highlights (values omitted)

- **Live-row verification:** reviewers queried the live `tabItem` rows and confirmed the prefix
  semantics against `construction_resource_type` — `OH`=Overhead, `SUB`=Subcontract,
  `PLANT`=Plant, `LAB`=Labor (`cost_database_service.py:406-410`, `RESOURCE_TYPE_TO_STREAM`).
- **Site lexicon anchoring:** round 1/2 replacements were taken from the site's own mappings —
  `cost_database_service.py:1141` (Concrete Mixer → the proposed mixer term),
  `:1105-1107` (LAB-MASON-001 → mason term); round 2/3 anchored the subcontract marker in
  glossary v2.0 / D2 (`docs/translation/smoke-test-1.0.md:38`, approved `ar` overrides,
  stage6-w602 released payloads).
- **Correction of a proposer error:** round 1 caught that `LAB` means Labor, not laboratory
  (the initial proposal read the prefix as "lab"), and that a shadda diacritic violated the
  plain-register rule — replaced and re-reviewed.
- **Byte safety:** every final value was scanned codepoint-by-codepoint: no bidi controls,
  zero-width/NUL/C0/C1/DEL, no tatweel, no Arabic-Indic digits, no tashkeel, no leading or
  trailing whitespace.
- **UBA display check:** the hybrid code+noun item value was verified against a bidi renderer
  so the Latin code tokens do not reorder (round 1).

## Data-quality flag (disclosed, not fixed)

The Item identity `LAB-MASON-001\`` ends with a pre-existing stray backtick. The identity is
**not** modified by this work item (only `item_name_ar` is written); flagged to the owner.

## Gate statement

Populating and passing these reviews is **not** owner approval and **not** import
authorization. Import requires the owner's explicit in-session approval of proposal v3,
followed by dry-run, then apply (SCOPE R2).
