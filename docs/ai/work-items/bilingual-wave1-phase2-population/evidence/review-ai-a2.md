# Independent AI-A2 review record — bilingual-wave1-phase2-population

**Item:** `bilingual-wave1-phase2-population` (Tier 5C)
**Privacy (R4):** values are redacted from this committed record; per-row `sha256[:16]`
digests and counts only. Full values live in
`sites/v16.localhost/private/wave1-phase2-population/proposal.json` +
`review-ai-a2.json`.

## Review chain

| Round | Proposal version | Proposal sha256 | Review session (non-author) | Overall | Approved | Revised |
|---|---|---|---|---|---|---|
| 1 | v1 | `cc382f46449da2ed940a78e905b9d6f438c0e682fbb65433d859563c2b55bad6` | `ses_ef70c00a3ffeKFdmDXvDxiBkgT` | **revise** | 11/13 | 2 |
| 2 | v2 | `e68ef0c687516a110ed553a52cfe7d871808ba6007d9c1444ec1739730108557` | `ses_ef7027ce9ffe2qYPR6EuUV2Ei5` | **approve** | **13/13** | 0 |

**Final state:** every final value approved by a non-author session (round 2, overall
approve), satisfying R2. Private review record sha256 =
`b462acd2f0ee31e502df8b439ff86842cba2b90bfcc0a128d417a87611bb5dd3`.

## Round-1 dispositions (v1 → v2)

| Row | Verdict | Disposition (values redacted) |
|---|---|---|
| Cost Center `Elrefae - E` | approve | low-confidence proper-name default kept, flagged **OWNER AMEND WELCOME** |
| Cost Center `Main - E` | approve | standard root-node term |
| Cost Center `Stage 8 Pilot - E` | approve | metadata nit only (parent corrected in v2 notes) |
| Warehouse `All Warehouses - E` | approve | group-root label |
| Warehouse `Finished Goods - E` | **revise** | v1 attached the qualifier to "warehouses" instead of the goods; v2 adopts the site-corpus Finished-Goods label family |
| Warehouse `Goods In Transit - E` | approve | standard accounting rendering |
| Warehouse `Stores - E` | approve | corpus-attested term |
| Warehouse `Work In Progress - E` | approve | standard WIP warehouse term (construction alternate left as owner option) |
| Project `PROJ-0001` | approve | direct translation |
| Project `PROJ-0002` | approve | mirror of existing Arabic identity, trailing space trimmed in the derived value only |
| Project `PROJ-0003` | approve | direct translation |
| Project `PROJ-0008` | **revise** | v2 restores the canonical QA collocation and applies the glossary v2.0 term for "Variation Order" |
| Project `PROJ-0009` | approve | exact mirror of existing Arabic identity |

## Round-2 independent re-judgement (v2)

All 13 rows independently re-checked: byte-safety clean everywhere (no bidi/ZW/control
marks, no tatweel, no Arabic-Indic digits, no edge whitespace; the single digit is
Western per plan convention); both round-1 revisions independently confirmed; both
mirror rows verified byte-for-byte against their identity fields; no normalized-key
collisions across the warehouse tree; overall **approve**.

## Cross-row notes carried forward (non-blocking)

1. Approved site translation strings exist for three warehouse labels with alternate
   wording (all-warehouses / in-transit / WIP families). Chosen values judged equally
   conventional; strict label-parity swaps are an owner option, not corrections.
2. Glossary citation numbering nit for the VO term (value correct, index off by one) —
   recorded, no value impact.
3. `PROJ-0009` identity contains a source spelling variant (expected spelling of the
   "until" particle); mirror rule keeps the `_ar` value identical — flagged as a
   separate identity data-quality item, out of scope here.
4. `Elrefae - E` proper-name transliteration remains owner-editable at approval.
