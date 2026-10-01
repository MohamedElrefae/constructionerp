# Owner Disposition — decision-3 (`workspace-desk-coverage-v2`)

**Work item:** `workspace-desk-coverage-v2`
**Gate:** `decision-3` (DECISION), raised by Builder job `job-57f86a3a10cbd00a12ba2e50`
**Candidate:** `d8be079d388472a42494d35a8e9ccc0b058d8163c55f21337ce3e3c5401554df`
**Base commit:** `fd9aecc372aec6a1341dd0cac4f779c1ec539756`
**Tree OID:** `d354aac073c0b1dc1241b4f56e9689e0bff7ea9f`
**Date:** 2026-10-01
**Authority:** owner instruction given in session; transcribed by the agent
**Dispositions SHA-256:** recorded externally (a file cannot contain its own hash;
see the resume payload `decision_ref` and the ledger `decision-3` event)

Issued in response to the three blocking findings raised at `decision-3`. Each finding is
addressed below by an explicit owner ruling. No requirement, historical byte, or candidate
file is altered by this disposition.

---

## 1. Finding 1 — `implementation_defect` (six empty Workspace translations)

**Finding.** Semantic PO validation found empty translations for six visible Workspace
labels: `BOQ Management`, `Variation Management`, `Variation Order`, `Scope Management`,
`User Scope Context`, `Construction ERP`. Seventeen of the twenty-two visible Workspace
labels resolve; the complete semantic check exited 1.

**Owner ruling: DEFERRED** to the next Localization Maintenance / Bilingual Catalog
Release. Not repaired within this candidate.

**Rationale.** The six labels are Workspace navigation chrome, not requirement-bearing
records. They are correctly *detected* and *untranslated*; nothing silently misreports.
The repair is a catalog-maintenance action, not a workspace-UI action, and is properly
batched with the next bilingual release rather than performed opportunistically here.

**Verified counter-neutrality.** Filling the six `msgstr` values does not add or remove
catalog entries. The checker counts 817 entries both before and after repair, so this
deferral perturbs no ratified gate counter. (`EXPECTED_GATE.catalog` = 817 is a checker
entry count; the raw `msgid` line count is 811 at base and 818 in this candidate. These are
different counting domains and must not be compared.)

## 2. Finding 2 — `design_defect` (PO hash bound to the Stage-2 evidence chain)

**Finding.** Repairing `ar.po` changes its SHA-256. That hash is bound by
`localization_manifest.json`, `freshness_evidence.json`, and all eleven Stage-2 bilingual
envelopes. Regenerating those envelopes requires a live database catalog sync
(`sync_translation_catalog(dry_run=False)`), eleven module test suites, and a stage-2
inventory run — a full bilingual data release cycle exceeding the scope of this
workspace-UI milestone. The finding additionally noted that the checker forbids both
editing historical evidence and relaxing its assertions.

**Owner ruling: DISPOSITIONED — not a plan defect, and not repaired here.**

The premise "the repair requires a checker change" is rejected. The checker
(`scripts/check_localization_gates.py`) is left **byte-identical** at
`54fa583cb250b4707c8dd8f88b6c1454c15fd16d6db6ff667ef7c0dcec0642bb`. No assertion is
weakened, no ratchet is extended, and no disposition against the ratified contract is
required. The apparent deadlock arises only if one repairs `ar.po` inside this candidate.
This disposition declines that repair, so the binding never moves.

Because the repair is declined, `ar.po` remains at
`af343ac233cac0e022aa1d84fef87943cd94eff78d364f842115614be56c3698`, which is fully
aligned with the ratified Stage-2 envelopes, `localization_manifest.json`
(`adbd3d8d40102b8517494b39f910531bb64d4cb8ea01f99f037cced0f31895dc`), and
`freshness_evidence.json`
(`ba2d839df0d922ba86181051d4cc52712684fb3b72b5b2f6f77ae6190407f3ca`).

**Consequence for routing.** The Builder classified this as a `design_defect`, which routes
to the architect by default. The Owner overrides that fallback to `builder`: the design
question is answered here in writing, so no plan revision is required and the approved plan
revision `c754b40712adfc5c572b3ac3d53083ffa0aeb07f205f35576efb05520db20430` stands unaltered.

**Follow-up obligation.** The deferred repair must be performed in a bilingual catalog
release whose scope includes the evidence chain — specifically
`construction/locale/ar.po`, `construction/data/localization/localization_manifest.json`,
`construction/data/localization/freshness_evidence.json`, and
`docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage2/`. That release
carries its own authorization for the live catalog sync and the eleven module suites.

## 3. Finding 3 — `owner_decision` (dispatch authority versus context data)

**Finding.** Dependent work lacked a separately bounded executable dispatch: staging and
runtime measurement, real-role permission probes, collector changes outside
`allowed_paths`, and isolated orchestrator regression execution. The supplied authorization
transcript does not widen the packet's `allowed_paths` or filesystem permissions.

**Owner ruling: the Builder's reading is CORRECT and is hereby affirmed.**

`owner-execution-authorization.md` is authoritative *evidence* of owner intent. It is not
a mechanical grant of dispatch authority, and an agent must not treat it as one. The
Builder declined to self-widen on exactly this ground, which is the orchestrator behaving
as designed. This ruling records that the refusal was correct, not obstructive.

For this build leg no staging, catalog sync, or live probe is required: the candidate
retains its bytes unchanged and the build is an offline verification of the existing
nineteen files. Live site permission verification (WDC-R6) and the WDC-R5 isolated
regression harness remain scheduled for the verification phase under separately bounded
dispatches.

---

## 4. Scope of this disposition

| Item | Ruling |
|---|---|
| Candidate files altered | none |
| Checker altered | no — byte-identical |
| Historical evidence altered | none |
| Site state altered | none — `v16.localhost` untouched by this disposition |
| Plan revision | unchanged (`c754b407…`) |
| Deferred work | six Arabic translations → next bilingual catalog release |
| Verification-phase work | WDC-R6 live permission probe; WDC-R5 isolated regression harness |

## 5. Supersession

This disposition supersedes no prior owner disposition. It does not alter the ratified
Stage-2 evidence, the `scp006` delta-ratification disposition
(`3ca04f4770cf659c08296e16513d7494b8dc6fe1221e7d57c6ddfe981e49899a`), or the `scp008`
base-suite report (`2912dc5f6e3cdf37fb936b15a0fe91777292805310ae902f88c7016150dca35f`),
all of which remain bound to candidate `d8be079d…` at base `fd9aecc…`.
