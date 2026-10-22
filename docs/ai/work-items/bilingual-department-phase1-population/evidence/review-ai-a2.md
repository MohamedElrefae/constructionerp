# Review — bilingual-department-phase1-population (Round 1)

**Work item:** `bilingual-department-phase1-population`
**Reviewer:** fresh non-author session (independent of the proposal author)
**Reviewed artefact:** `proposal.json` v1 (14 rows), sha256
`cb0a10ee61e7bad14eb6847acc26530af6d351b5848781a80948a7307cee5c0a`
(reviewer independently recomputed the digest — matched)
**Record (private):** `sites/v16.localhost/private/department-phase1-population/review-ai-a2.json`
sha256 `eaf0ec7174a24a71846f4ab23441c521b140e7894e779ec767038019f362f82d`

## Verdict chain

| Round | Scope | Approve | Revise | Overall |
|---|---|---|---|---|
| 1 (v1) | 14 rows | 13 | 1 — row 1, the company-less tree root (value contested against in-app precedent) | **revise** |

Redaction: per privacy R4 the Arabic values and the suggested correction live only in the
private proposal/review; committed evidence records row identities, verdicts, and digests.

## Reviewer checks (independently confirmed)

- **Glossary:** 47 terms, **0 exact matches** on the 14 labels (substring-only relations,
  non-binding); no applied value equals any `forbidden_ar`. Author claim F-5G-6 confirmed.
- **Identity:** 14/14 `english_label` == live `department_name` for each frozen `name`
  (read-only site query); site total 276, pre-state Arabic 0.
- **Byte hygiene:** 14/14 clean — no bidi/ZW/format chars, no tatweel, no Arabic-Indic
  digits, no edge whitespace; UTF-8, no BOM/CR.
- **Distinctness:** 14/14 mutually distinct.
- **Row 1 revise:** the `All Departments` root — proposed primary contradicted the in-app
  master-root pattern (all five live `All *` roots use the `جميع …` construction; the
  proposed value matched only .po UI-string batches, not master data). Correction = swap
  with the row's own approved alternate.
- **Non-blocking notes:** (a) Dispatch alternate contained a string that is `forbidden_ar`
  for a different doctype — alternate dropped, primary approved as-is; (b) row-11
  rationale cited a bare glossary term that does not exist — rationale reworded, value
  unchanged.

## Resolution

Author applied the revision to v1 → **proposal v2**, sha256
`dba85a4ceba5826094c1c7b6e25117afe8e0a696bcb1c3564699b0d736bf64a4`
(rows 2–14 Arabic values byte-identical v1→v2; only row 1 primary/alternate swap +
cosmetic rationale/alternate edits). v1 preserved for the audit trail.

**Effective standing: 14/14 approved** (13 from round 1 + row 1 via the applied revise)
— pending owner sha-bound approval before any dry-run (hard gate, SCOPE R3).
