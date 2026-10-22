# Stage 1C — Independent AI-A3 Structural/Technical Translation QA

## Review identity and scope

- **Role:** AI-A3 structural/technical translation QA reviewer only
- **Reviewer model:** OpenAI GPT-5.6-sol
- **Canonical task/session identifier:** `/root/ai_a3_structural`
- **UTC timestamp:** `2026-09-04T20:42:01Z`
- **Independence:** This session did not create the six proposals and is not the Builder, AI-A1, AI-A2, or AI-R.
- **Decision scope:** Structural acceptance of the six Stage 1C proposal mappings only. This is not runtime release, deployment authorization, linguistic/domain approval, or AI-R verification.
- **Repository state:** `feature/erp-arabic-bilingual-data` at base/HEAD `e7be48855bde540464ea302e53c9bfca62b7c462`; reviewed changes remain uncommitted.

## Reviewed artifacts

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4, `docs/translation/ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md` | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Builder handoff, `docs/ai/work-items/erp-arabic-bilingual-data/BUILD_HANDOFF.md` | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Builder record, `docs/ai/work-items/erp-arabic-bilingual-data/IMPLEMENTATION.md` | `22a90951e417343fa0ff276e5181e90bdab0188f85a331578515b5cd5ed607d9` |
| Six-row proposal package, `docs/ai/work-items/erp-arabic-bilingual-data/evidence/stage-1c-review-package.md` | `ceaddc440e27656cdc66f5ec89515233e4d92c3f31c1a387dc76945ada1b68c1` |
| Construction Arabic catalog, `construction/locale/ar.po` | `e4678987ab3d11d632397de7dfc4a926681e862bdca6c09872e3f211ca85161e` |
| Construction source, `construction/public/js/typography_settings.js` | `8363c4c159d5b11d9300e37e95faf5a4fff4949d435e68899c9e2efbca28463b` |
| Frappe Arabic catalog, `apps/frappe/frappe/locale/ar.po` | `cc353e76ebd37c0ef0d72f79cf0c081a460cfa5fe6846dcf36d122384c225502` |

The proposal package contains stale v3 instructions requiring named human reviewers and a human release authority. Those instructions conflict with canonical plan v4 and the matching handoff, so they were treated as governance drift, not as review authority. The six proposal values at the recorded package hash were reviewed unchanged under AI-A3 v4 governance. The shared package was not edited.

## Mechanical checks

| Check | Result |
|---|---|
| Exact source-to-target mapping | PASS — six source keys map one-to-one to the six reviewed Arabic values |
| Missing/extra rows | PASS — exactly six distinct source keys and six non-empty targets |
| Duplicate source keys in owning catalogs | PASS — each of the five Frappe keys occurs once in Frappe `ar.po`; `Typography Settings` occurs once in Construction `ar.po` |
| Duplicate target values | PASS — all six Arabic targets are distinct |
| Source ownership | PASS — five keys are Frappe-owned; `Typography Settings` is Construction-owned and referenced from `construction/public/js/typography_settings.js:634` |
| Vendor modification | PASS for reviewed scope — the pending Construction diff adds only its owned `Typography Settings` msgid; the five Frappe gaps are not added to Construction `ar.po` |
| Placeholders/format tokens | PASS — neither side contains interpolation placeholders or format specifiers |
| HTML/XML | PASS — neither side contains tags or entities |
| Plural structure | PASS — no plural form applies to these menu/action labels |
| Leading/trailing whitespace | PASS — none |
| Newlines/tabs/non-breaking spaces | PASS — none |
| Punctuation parity | PASS — neither source nor target requires terminal punctuation |
| Unicode/script | PASS — targets contain Arabic letters and ordinary U+0020 spaces only |
| Hidden bidi controls | PASS — none of U+202A–U+202E, U+2066–U+2069, U+200E, U+200F, or U+061C occurs |
| Embedded LTR content | PASS — none; no isolation marks are required |
| Source-equal fallback | PASS — no target equals its English source |
| Forbidden technical-`Child` terms | PASS — no `طفل` or `أطفال`; the six keys do not contain the technical concept `Child` |
| Injection/unsafe markup risk | PASS — plain text only |

The proposal package's character-count notes contain minor arithmetic errors. Actual Unicode code-point counts, including spaces, are: `Desktop` 7 / `سطح المكتب` 10; `Workspaces` 10 / `مساحات العمل` 12; `Edit Sidebar` 12 / `تحرير الشريط الجانبي` 20; `Toggle Theme` 12 / `تبديل المظهر` 12; `Toggle Full Width` 17 / `تبديل العرض الكامل` 18; `Typography Settings` 19 / `إعدادات الخطوط` 14. These documentation errors do not change the strings or their structural validity.

## Per-string AI-A3 decisions

| # | English source | Reviewed Arabic target | Ownership | Decision | Confidence | Structural rationale / exception |
|---|---|---|---|---|---|---|
| 1 | `Desktop` | `سطح المكتب` | Frappe | **APPROVE** | High | Plain Arabic text; no tokens, markup, bidi controls, whitespace, punctuation, duplication, or material overflow risk. |
| 2 | `Workspaces` | `مساحات العمل` | Frappe | **APPROVE** | High | Plain Arabic text; one-to-one mapping and comparable label length; no mechanical defect. |
| 3 | `Edit Sidebar` | `تحرير الشريط الجانبي` | Frappe | **APPROVE WITH NON-BLOCKING UX EXCEPTION** | High for payload; Medium for narrow layout | Structurally valid, but the 20-code-point Arabic target is materially longer than the 12-code-point source. No actual narrow/mobile rendering of the proposed runtime value was supplied. Verify clipping/wrapping at the minimum supported sidebar width before the Stage 1C runtime/render gate is declared complete. |
| 4 | `Toggle Theme` | `تبديل المظهر` | Frappe | **APPROVE** | High | Equal code-point length; plain text; no directionality or formatting risk. |
| 5 | `Toggle Full Width` | `تبديل العرض الكامل` | Frappe | **APPROVE** | High | Plain Arabic text; target length is comparable; no mechanical or toolbar-overflow blocker identified. Semantic dual meaning belongs to AI-A2, not AI-A3. |
| 6 | `Typography Settings` | `إعدادات الخطوط` | Construction | **APPROVE** | High | Exact extracted msgid and owned source verified; short plain target; no format or directionality risk. Semantic dual meaning belongs to AI-A2, not AI-A3. |

## Exceptions and blockers

1. **Non-blocking UX evidence gap:** Item 3 has not been rendered with the proposed Arabic text at the minimum supported sidebar/mobile width. This does not invalidate the payload, but it remains mandatory evidence for the later runtime/render gate. AI-A3 does not claim that browser test passed.
2. **Governance drift:** The package's human sign-off sections are stale relative to plan v4. AI-R should verify v4 review records and must not require or infer the obsolete human sign-off table.
3. **Package count corrections:** The length arithmetic in the package should not be reused as exact evidence; the corrected counts above are authoritative for this review.
4. **Out of scope:** Linguistic naturalness and Egyptian accounting/construction ambiguity are reserved for AI-A1 and AI-A2. Runtime dictionary state, new-session rendering, release promotion, and operational authorization were not tested or granted here.

## Overall decision

**PASS — AI-A3 APPROVES ALL SIX STAGE 1C PROPOSAL MAPPINGS FOR STRUCTURAL/TECHNICAL QUORUM.**

Item 3 carries a non-blocking layout-risk exception that must be closed with a real minimum-width/new-Arabic-session rendering test before the Stage 1C runtime/render gate can pass. This record must be hashed and independently verified by AI-R together with the separate AI-A1 and AI-A2 decisions. No proposal was promoted, no catalog/runtime value was released, and no code, database data, Git history, or approval state was changed by this review.
