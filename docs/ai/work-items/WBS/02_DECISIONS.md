# Decision Register — WBS First Increment

## Settled current owner scope
WBS now; billing later. Existing Stages represent item execution portions. Formal payment approval is item-line based, not mandatory Stage metadata. Preserve existing quantities/history/certified_qty meaning. Revisit VO only in a separately justified scope. No native tests or source changes occurred in prior review.

## Local recommendations requiring explicit resolution
| ID | Decision | Recommended starting position | Gate |
|---|---|---|---|
| D01 | Legacy Stage mapping | Remain unmapped by default; authorized explicit mapping | P2 |
| D02 | Measured/certified mapping/relink | No automatic mapping; choose reviewed historical mapping policy and audit | P2 |
| D03 | Out-of-balance mapping save | Compare rejection vs narrow invariant-preserving route; no silent bypass | P2 |
| D04 | Mapping permission | Planning-level document authority and scope; deny measurement-only relink | P2 |
| D05 | Leaf/disabled node | New assignments only eligible leaves; preserve references, show warning on disabled | P1/P2 |
| D06 | Referenced tree change | Block structural changes affecting referenced subtree initially; define title/code edits | P1/P2 |
| D07 | Header eligibility | No new Contract-only restriction without checking existing Locked Tender usage | P2 |
| D08 | Code generation | Stable unique per project, no auto-history renumbering; choose format locally | P1 |
| D09 | Coverage denominator | Healthy linked / all eligible Stage records; invalid links separate; zero=N/A | P3 |
| D10 | Active scope semantics | Reuse audited permission boundary, verify node access before Stage exists | P1 |

For each decision record selected rule, rationale, actor, date, affected requirements and test. Routine code choices delegated to architect within governance; consequential history/access/business choices escalate. No need to reopen future payment questionnaires.

## Explicitly deferred
Ledger schema/migration, partial certification redesign, financial corrections, VO rate rules/duplicate-line repair, Stage distribution revision, Stage generator, certificate sequence/reversal. Track candidates; escalate only if mapping exercises/worsens the path.
