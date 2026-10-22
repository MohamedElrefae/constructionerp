# Independent AI-A2 review record — bilingual-wave2-group-masters-population

**Item:** `bilingual-wave2-group-masters-population` (Tier 5D)
**Privacy (R4):** values are redacted from this committed record; per-row verdicts,
rationales and counts only. Full values live in
`sites/v16.localhost/private/wave2-group-masters-population/proposal.json` +
`review-ai-a2.json`.

## Review chain

| Round | Proposal version | Proposal sha256 | Review session (non-author) | Overall | Approved | Revised |
|---|---|---|---|---|---|---|
| 1 | v1 | `08dba90a8134c238d2e2e74b69081c0ec0c879ddecb82b2b7bb3a0ed2f6ea47e` | `ses_ef6f18e07ffeVf22gghj4KWEwt` | **approve** | **23/23** | 0 |

**Final state:** every final value approved by a non-author session (round 1, overall
approve), satisfying R2 — no revision round was required. The reviewer independently
re-verified the proposal sha256, the frozen inventory counts (6/5/8/4 in-scope,
21 fixtures), and the SCOPE base commit. Private review record sha256 =
`105c60d83e9d591359f6181a8c96d875d87dabb2313b2555989fe70d4f46a950`.

## Round-1 dispositions (v1, all rows)

| Row | Verdict | Disposition (values redacted) |
|---|---|---|
| Item Group `All Item Groups` | approve | root-noun pattern on the 5C `جميع …` anchor |
| Item Group `Consumable` | approve | standard category noun (catalog alternate rejected as "consumer" reading) |
| Item Group `Products` | approve | matches 5C products family; indefinite leaf style like 5B |
| Item Group `Raw Material` | approve | standard; **cross-tree identical** with Supplier Group row |
| Item Group `Services` | approve | standard; **cross-tree identical** with Supplier Group row |
| Item Group `Sub Assemblies` | approve | glossary anchor **verified**: `Child Item` → `عنصر فرعي` supports `Sub` → `فرعي` |
| Customer Group `All Customer Groups` | approve | root pattern; byte-identical to site catalog msgstr |
| Customer Group `Commercial` | approve | segment adjective; byte-identical to catalog |
| Customer Group `Government` | approve | segment adjective; better as picklist label than the catalog noun |
| Customer Group `Individual` | approve | **choice row** → category noun selected (adjective alternative rejected: retail-price reading) |
| Customer Group `Non Profit` | approve | **choice row** → masculine adjective parallel to siblings (long noun phrase rejected; catalog gender variant = owner option) |
| Supplier Group `All Supplier Groups` | approve | root pattern; byte-identical to catalog |
| Supplier Group `Distributor` | approve | standard supplier-type noun; byte-identical to catalog |
| Supplier Group `Electrical` | approve | standard trade adjective; byte-identical to catalog |
| Supplier Group `Hardware` | approve | **choice row** → clear tools/equipment reading (colloquial alternative rejected as ambiguous) |
| Supplier Group `Local` | approve | standard supplier adjective; byte-identical to catalog |
| Supplier Group `Pharmaceutical` | approve | supplier adjective parallel to siblings (catalog goods-noun = owner option) |
| Supplier Group `Raw Material` | approve | cross-tree identical with Item Group row |
| Supplier Group `Services` | approve | cross-tree identical with Item Group row |
| Territory `All Territories` | approve | root pattern (catalog alternate = owner option) |
| Territory `Egypt` | approve | proper noun, no variant |
| Territory `India` | approve | proper noun, standard definite form |
| Territory `Rest Of The World` | approve | **choice row** → idiomatic concise rendering (wordy alternative rejected; catalog variant = owner option) |

## Independent checks performed (all PASS)

1. **Glossary scan:** all 47 glossary v2.0 terms scanned — every `forbidden_ar` list (15
   distinct entries) and every `approved_ar`: **0 hits** raw and normalized; no glossary
   entry exists for any of the 23 labels; sole cited anchor verified.
2. **Cross-tree consistency:** the two shared English labels are byte-identical across
   both trees (values and `_norm`); zero within-doctype norm collisions.
3. **Norm safety:** 20/23 rows have display = `_norm`; the 3 deltas are canonical alef
   unification only; `ة`/`ئ`/`ء` preserved verbatim by `normalize_arabic` (expected);
   no surprising keys, no collisions.
4. **Byte safety:** Arabic letters + single spaces only — no bidi/control marks, no
   diacritics, no tatweel, no Arabic-Indic digits, no edge/double whitespace.
5. **Inventory cross-check:** proposal counts 6/5/8/4 + 21 fixtures == frozen
   `inventory-export.log`; in-scope names byte-identical per doctype.

## Cross-row notes carried forward (non-blocking, owner options)

1. Site translation catalog holds approved alternates for 8 labels (root-plural style for
   one tree, territory/region wording, gender variant of one customer segment, goods-noun
   vs supplier-adjective for two supplier groups, longer territory wording). Chosen values
   judged equally conventional; strict label-parity swaps are an owner option at approval,
   not corrections (5C parity treatment).
2. 7 rows already byte-match the site catalog — those need no parity decision.
