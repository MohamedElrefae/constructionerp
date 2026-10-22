# Stage 1C — Independent AI-A2 Egyptian Accounting/Construction Domain Review

## Review identity and scope

| Field | Value |
|---|---|
| Role | AI-A2 — Egyptian accounting, QS, and construction-operations domain reviewer |
| Independence | Independent review run; not the Builder/proposer session; no other review role is claimed |
| Agent/model | OpenAI Codex, GPT-5 model family (the session exposes no more-specific model identifier) |
| Canonical task/session identifier | `/root/ai_a2_domain` |
| Review timestamp (UTC) | `2026-09-04T20:41:27Z` |
| Candidate commit inspected | `e7be48855bde540464ea302e53c9bfca62b7c462` (working tree also contains the disclosed uncommitted work-item changes) |
| Overall AI-A2 decision | **PASS — all six proposed Arabic labels are acceptable in their verified UI contexts; domain review is reasoned N/A for each label** |

This decision covers Egyptian accounting/construction domain meaning only. It does not release translations, approve structural or linguistic QA, grant AI-R verification, authorize an operational action, or modify any approval state.

## Reviewed artifacts and hashes

| Artifact | SHA-256 |
|---|---|
| Canonical plan v4, `docs/translation/ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md` | `07cc65342a20be94b193cb6abf21873acaea30bc597c621d2d282cdcb3311e1d` |
| Build handoff, `docs/ai/work-items/erp-arabic-bilingual-data/BUILD_HANDOFF.md` | `488b16321d2b4ff98b6bb4596ee9fedee9a28107da99ab9f0a830a28fb0212bd` |
| Builder record, `docs/ai/work-items/erp-arabic-bilingual-data/IMPLEMENTATION.md` | `22a90951e417343fa0ff276e5181e90bdab0188f85a331578515b5cd5ed607d9` |
| Proposal/review package, `docs/ai/work-items/erp-arabic-bilingual-data/evidence/stage-1c-review-package.md` | `ceaddc440e27656cdc66f5ec89515233e4d92c3f31c1a387dc76945ada1b68c1` |
| Frappe sidebar source, `frappe/public/js/frappe/ui/sidebar/sidebar_header.js` | `2f5cf3dd5087ee21e8a170c9fb6588d420c3b280c39551777f1e51ad527c94c9` |
| Construction typography source, `construction/public/js/typography_settings.js` | `8363c4c159d5b11d9300e37e95faf5a4fff4949d435e68899c9e2efbca28463b` |
| Construction Arabic catalog, `construction/locale/ar.po` | `e4678987ab3d11d632397de7dfc4a926681e862bdca6c09872e3f211ca85161e` |
| Supplied UI screenshot, `/home/mohamed/Desktop/arabic architecure .png` | `3c5d786bedcd55e7bbe6fba49a657a92ef9f472df8fe1975fba8b9e0ca726acd` |

## Method and verified context

The review inspected the actual menu construction rather than relying only on the English labels. In Frappe's sidebar header, `Desktop`, `Workspaces`, and `Edit Sidebar` are navigation/customization entries. `Toggle Theme` opens the theme switcher, while `Toggle Full Width` calls `frappe.ui.toolbar.toggle_full_width()`. Construction appends `Typography Settings` to the same display-controls list and opens a dialog containing font family, font size, and font weight controls. These source-level facts establish that all six strings are application chrome/display controls and are not transaction, ledger, tender, BOQ, measurement, or engineering-network terminology.

No regulatory source is relevant or claimed: these labels do not express Egyptian Accounting Standards, Egyptian tax treatment, government contracting rules, measurement rules, or contractual terminology. The verified repository source is the controlling reference for their actual meaning.

## Per-string AI-A2 decisions

| # | Source | Proposed Arabic | AI-A2 decision | Domain applicability | Confidence | Rationale |
|---:|---|---|---|---|---:|---|
| 1 | `Desktop` | `سطح المكتب` | **ACCEPT** | **N/A — generic navigation UI** | 0.99 | The source is the route to `/desk`. It cannot reasonably be read as an accounting office, project office, or contractual term in this menu context. |
| 2 | `Workspaces` | `مساحات العمل` | **ACCEPT** | **N/A — generic navigation UI** | 0.98 | Although `مساحة` can denote physical area in construction, the entry contains nested Frappe workspace links. `مساحات العمل` truthfully denotes digital workspaces here, not measured site areas or scope of work. |
| 3 | `Edit Sidebar` | `تحرير الشريط الجانبي` | **ACCEPT** | **N/A — UI customization action** | 0.99 | The action toggles the sidebar editor. `الشريط الجانبي` removes any possible accounting/document-drafting meaning of `تحرير`. |
| 4 | `Toggle Theme` | `تبديل المظهر` | **ACCEPT** | **N/A — visual appearance control** | 0.99 | The action opens Frappe's theme switcher. It has no accounting presentation, report-formatting, or construction-domain consequence. |
| 5 | `Toggle Full Width` | `تبديل العرض الكامل` | **ACCEPT** | **N/A after explicit dual-meaning review** | 0.97 | `العرض` can mean bid/offer or financial-statement presentation, and can mean physical width in engineering. Here the action directly calls `toggle_full_width()` beside theme/sidebar controls, so it unambiguously means full page/display width. An Egyptian accountant, QS, or contractor would not interpret this toolbar action as toggling a tender offer. |
| 6 | `Typography Settings` | `إعدادات الخطوط` | **ACCEPT** | **N/A after explicit dual-meaning review** | 0.98 | `الخطوط` can refer to pipelines/routes and, in compounds, credit lines or line items. The verified dialog controls font family, size, and weight and is inserted beside theme/display controls. In that context `الخطوط` unambiguously means fonts/typefaces, not BOQ items or engineering lines. |

## Verified references

1. `/home/mohamed/frappe-bench/apps/frappe/frappe/public/js/frappe/ui/sidebar/sidebar_header.js:8-45` — navigation entries and sidebar editor action.
2. `/home/mohamed/frappe-bench/apps/frappe/frappe/public/js/frappe/ui/sidebar/sidebar_header.js:228-253` — theme, full-width, and sidebar display controls; the full-width handler calls `frappe.ui.toolbar.toggle_full_width()`.
3. `/home/mohamed/frappe-bench/apps/construction/construction/public/js/typography_settings.js:627-670` — Typography Settings dialog and font family/size/weight fields.
4. `/home/mohamed/frappe-bench/apps/construction/construction/public/js/typography_settings.js:865-923` — Typography Settings inserted into the display menu and user menus.
5. `/home/mohamed/Desktop/arabic architecure .png` — supplied screenshot showing the six labels in the sidebar/navigation and display-control UI context.

## Exceptions, drift, and downstream risks

1. **Stale governance wording in the input package:** `stage-1c-review-package.md` still describes named-human A1/A2/A3 sign-offs and release authority. This is non-substantive governance drift for the translation proposals. Canonical plan v4 and the current handoff supersede it with independent AI-A1/AI-A2/AI-A3 plus AI-R. The shared package was not edited during this review.
2. **Technical extraction/runtime risk outside AI-A2 scope:** Frappe's current `Workspaces` label is a raw string (`label: "Workspaces"`) rather than `__("Workspaces")` in `sidebar_header.js:20`. The Arabic proposal is domain-correct, but a catalog/runtime value alone may not localize that visible instance. This must be resolved or expressly tested by the Builder/AI-A3 before Stage 1C can be considered operationally complete. This review does not authorize a vendor-source edit.
3. This review did not test responsive rendering, clipping, placeholders, catalogs, cache behavior, or runtime release. Those belong to AI-A3/Builder/AI-R.

## Final AI-A2 disposition

**PASS.** All six proposed Arabic strings are truthful and safe in their verified UI contexts for users of an Egyptian construction-accounting ERP. Items 5 and 6 have been explicitly assessed for their domain-adjacent alternate meanings; context resolves both without material ambiguity. No external accounting or regulatory citation is necessary, and none was fabricated.

The separate raw-`Workspaces` source finding is an operational translation-path risk for downstream technical review, not a domain-language rejection.
