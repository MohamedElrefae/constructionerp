# Independent AI-A2 review record — bilingual-uom-phase1-population

**Item:** `bilingual-uom-phase1-population` (Tier 5F)
**Privacy (R4):** values are redacted from this committed record; per-row verdicts,
rationales and counts only. Full values live in
`sites/v16.localhost/private/uom-phase1-population/proposal.json` +
`review-ai-a2.json` (v1 preserved as `proposal-v1.json`).

## Review chain

| Round | Proposal version | Proposal sha256 | Overall | Approved | Revised |
|---|---|---|---|---|---|
| 1 | v1 (17 rows) | `00cff4cda58629e5c4e31393d58129739f213379d17b89c1127a02be971c4b30` | **approve** | **16/17** | 1 |
| — | v2 (15 rows, effective) | `18a16a953ebbaad704acc7982ed96de71808235c7fc5b258b6825fbd80598bbf` | **15/15 approve** | 15 | 0 |

**v2 derivation:** rows 1–15 byte-identical to v1 (verified at build time); rows 16–17
dropped by owner F4 decision, so the single Round-1 revise (row 16 transliteration, alternative
suggested) left the approved set. Round-1 verdicts carry over unchanged.

**Final state:** every value in the approved 15-row set was approved by a non-author
Round-1 review AND bound to the owner's in-session decisions (F4 prune / F1 bundle /
F5 bilingual fixture), satisfying R2.

## Round-1 dispositions (v1, values redacted)

| Row | Verdict | Disposition |
|---|---|---|
| `M3` | approve | standard Egyptian BOQ volume unit; distinct from M2/M |
| `M2` | approve | standard area unit |
| `M` | approve | plain SI unit name approved (description-style alternate reserved for prose) |
| `TON` | approve | mass; intentional synonym alignment with `Tonne` accepted |
| `KG` | approve | formal transliteration |
| `PCS` | approve | distinctness rule vs `Nos` upheld |
| `LS` | approve | Egyptian BOQ lump-sum convention accepted (was medium-confidence flag) |
| `DAY` | approve | standard time unit |
| `HR` | approve | standard time unit |
| `BAG` | approve | standard procurement term |
| `LTR` | approve | standard volume unit |
| `SET` | approve | standard assembly unit |
| `Nos` | approve | standard count unit |
| `Tonne` | approve | intentional duplicate with `TON` accepted (alternate retained privately) |
| `Box` | approve | standard packaging unit |
| `Pint (US)` | revise | transliteration alternative proposed — **moot**: row pruned by owner F4 |
| `Acre` | approve | transliteration correct; `فدان` must never be used (area mismatch noted) |

## Owner decisions bound to this review

| Decision | Choice |
|---|---|
| F4 membership | prune to 15 (drop `Pint (US)`, `Acre`) |
| F1 enablement | bundle `uom.json` `"enabled": 1` fix this cycle |
| F5 durability | bilingual fixture: `uom.json` gains `uom_name_ar` (norm stays server-derived) |

Private review record sha256 = `2e58a4f06359319587af56ba3387c5934e31dfc1095a61e5fa238ea0fa07921b`.
