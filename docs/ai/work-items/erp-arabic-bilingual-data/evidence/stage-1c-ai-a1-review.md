# Stage 1C — Independent AI-A1 Arabic Linguistic Review

## Review identity and scope

| Field | Value |
|---|---|
| Role | AI-A1 — Arabic localization reviewer |
| Independence | Independent review run; not the Builder/proposal session |
| Model identity | OpenAI Codex, GPT-5 family |
| Review session/task | `/root/ai_a1_arabic` |
| Reviewed at (UTC) | `2026-09-04T20:41:29Z` |
| Scope | Modern Standard Arabic accuracy, grammar, brevity, consistency, Egyptian-user clarity, and suitability as generic ERP UI labels |
| Excluded from this decision | Egyptian accounting/construction domain approval (AI-A2), structural/rendering QA (AI-A3), bundle verification (AI-R), release promotion, runtime import, and production authorization |

## Reviewed artifacts

| Artifact | SHA-256 |
|---|---|
| `docs/translation/ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md` | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| `docs/ai/work-items/erp-arabic-bilingual-data/BUILD_HANDOFF.md` | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| `docs/ai/work-items/erp-arabic-bilingual-data/IMPLEMENTATION.md` | `22a90951e417343fa0ff276e5181e90bdab0188f85a331578515b5cd5ed607d9` |
| `docs/ai/work-items/erp-arabic-bilingual-data/evidence/stage-1c-review-package.md` | `ceaddc440e27656cdc66f5ec89515233e4d92c3f31c1a387dc76945ada1b68c1` |
| `construction/locale/ar.po` | `e4678987ab3d11d632397de7dfc4a926681e862bdca6c09872e3f211ca85161e` |

The decision applies only to the six source/target pairs at the review-package hash above. Any edit to a source string, proposed Arabic value, or relevant context invalidates this AI-A1 decision and requires a new AI-A1 run.

## Per-string decisions

| # | English source | Proposed Arabic | Decision | Confidence | AI-A1 rationale |
|---|---|---|---|---|---|
| 1 | `Desktop` | `سطح المكتب` | **APPROVE** | High | Standard, immediately recognizable MSA computing term. The iḍāfa construction is grammatical and suitably brief for navigation. It is also internally consistent with the existing catalog translation `Desktop Icon` → `أيقونة سطح المكتب`. |
| 2 | `Workspaces` | `مساحات العمل` | **APPROVE** | High | Natural plural rendering of software workspaces, grammatically correct, concise, and clearer for general ERP users than the more abstract alternative `بيئات العمل`. |
| 3 | `Edit Sidebar` | `تحرير الشريط الجانبي` | **APPROVE** | High | `الشريط الجانبي` is the established repository term for sidebar, and `تحرير` accurately expresses editing/customizing it. The wording is consistent with existing `Edit …` translations such as `تحرير القيم` and `تحرير {0}`. Visual fit remains an AI-A3 responsibility. |
| 4 | `Toggle Theme` | `تبديل المظهر` | **APPROVE** | High | Clear action-label phrasing. `تبديل` matches the existing catalog convention for toggle actions, while `المظهر` is natural for the visible theme/appearance concept in an Egyptian Arabic UI. |
| 5 | `Toggle Full Width` | `تبديل العرض الكامل` | **APPROVE** | High | Grammatically correct and concise. `الكامل` agrees with masculine `العرض`; the surrounding appearance-control context makes “full width” clear. Domain polysemy of `العرض` is reserved for AI-A2 and does not create a linguistic defect in this UI phrase. |
| 6 | `Typography Settings` | `إعدادات الخطوط` | **APPROVE** | High | Natural MSA UI wording for font/typeface settings. The iḍāfa is grammatical and concise; `إعدادات` follows established catalog usage and `الخطوط` is already used for `Fonts` in the Frappe Arabic catalog. Domain polysemy is reserved for AI-A2. |

## Consistency checks

- Existing Frappe Arabic entries use `تبديل` for `Toggle Chart`, `Toggle Grid View`, and `Toggle Sidebar`; items 4 and 5 follow that convention.
- Existing Frappe/ERPNext/Construction Arabic entries consistently use `إعدادات` for settings labels; item 6 follows that convention.
- Existing Arabic catalog entries use `الشريط الجانبي` for sidebar and `سطح المكتب` within desktop-related phrases; items 1 and 3 follow those established terms.
- The six Arabic values are concise nominal UI labels without unnecessary punctuation or explanatory text.
- No external linguistic or regulatory source was required or relied upon. Repository source context and existing Arabic catalogs were used as consistency evidence. Unverified claims in the pre-review package about particular external products were not used for this decision.

## Exceptions, drift, and remaining gates

1. The review package still contains stale v3 references to named human reviewers, human signatures, and a human release authority. Canonical plan v4 and the matching handoff supersede that governance. This is **non-substantive governance drift**: it does not alter any of the six source/target pairs reviewed here. The package itself was not edited during this independent run.
2. Item 3 may require a narrow-width truncation check. That is presentation/structural evidence for AI-A3, not a linguistic blocker.
3. Items 5 and 6 have possible domain polysemy. Explicit contextual disposition belongs to AI-A2; AI-A1 approval does not substitute for it.
4. This record does not change catalog rows, proposal status, runtime translations, database data, code, or Git history, and it does not promote any row to `Released`.
5. AI-A2, AI-A3, and AI-R decisions remain mandatory under plan v4 before Stage 1C promotion.

## Overall decision

**PASS — AI-A1 APPROVED FOR ALL SIX PROPOSED ARABIC LABELS.**

This is the complete AI-A1 linguistic decision only. It is not a Stage 1C quorum result and is not authorization to import, release, commit, push, merge, deploy, or mutate any site.
