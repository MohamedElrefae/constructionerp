# Stage 1C — Translation Review Evidence Package
## Six Generic Frappe UI Labels

**Document type:** Consultant pre-review assessment — input evidence for human A1/A2/A3 quorum  
**Status:** All six rows **PENDING** — not approved; quorum not met  
**Prepared:** 2026-09-04 (Africa/Cairo)  
**Prepared by:** Technical consultant (linguistic and domain analysis only — no sign-off authority)  
**Applicable plan:** ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md §5 (Workstream B), Stage 1C

---

> **Quorum reminder:** Each row requires A1 (named Arabic localization reviewer) + A2 (named domain reviewer, recording "Not Applicable" if applicable) + A3 (named structural QA reviewer) before it can be promoted to Released. This document is pre-review analysis only. No row may be marked Released based on this document alone.

---

## Proposed Translation Table (Current Status)

| # | English key | Proposed Arabic | A3 structural | A1 linguistic | A2 domain | Status |
|---|---|---|---|---|---|---|
| 1 | `Desktop` | `سطح المكتب` | See §A3-1 | See §A1-1 | See §A2-1 | **PENDING** |
| 2 | `Workspaces` | `مساحات العمل` | See §A3-2 | See §A1-2 | See §A2-2 | **PENDING** |
| 3 | `Edit Sidebar` | `تحرير الشريط الجانبي` | See §A3-3 | See §A1-3 | See §A2-3 | **PENDING** |
| 4 | `Toggle Theme` | `تبديل المظهر` | See §A3-4 | See §A1-4 | See §A2-4 | **PENDING** |
| 5 | `Toggle Full Width` | `تبديل العرض الكامل` | See §A3-5 | See §A1-5 | See §A2-5 — ⚠️ dual-meaning flag |
| 6 | `Typography Settings` | `إعدادات الخطوط` | See §A3-6 | See §A1-6 | See §A2-6 — ⚠️ dual-meaning flag |

Items 5 and 6 carry a dual-meaning flag that the A2 reviewer must explicitly address. See §A2 for details.

---

## A3 — Structural QA Assessment (Mechanical)

A3 structural checks can be evaluated mechanically against the source and proposed strings. These results are provided for the named A3 reviewer's use; they do not replace their sign-off.

| # | Check | Result |
|---|---|---|
| All | Placeholders (`{0}`, `%(name)s`, `{doc}`, etc.) | ✅ None present in any of the six English sources or proposed Arabic strings |
| All | HTML tags in source or target | ✅ None present |
| All | Python/JS format specifiers | ✅ None present |
| All | Trailing/leading whitespace in proposed Arabic | ✅ None detected |
| All | Arabic Unicode range | ✅ All proposed strings consist entirely of Arabic script characters and standard Arabic punctuation/spaces |
| All | Bidirectional control characters (U+202A–U+202E, U+2066–U+2069, U+200F, U+200E, U+061C) | ✅ None present in any proposed string |
| All | Source-equal fallback (`msgstr == msgid`) | ✅ No proposed Arabic string equals its English source |
| All | RTL rendering suitability | ✅ All strings are right-to-left Arabic; no LTR embedded segments; no mixed-direction risk |
| 1 | `سطح المكتب` — length vs `Desktop` (7 chars vs 13 chars Arabic) | ✅ Arabic is longer but within typical UI label tolerance; A3 should verify no clipping at minimum breakpoints |
| 2 | `مساحات العمل` — length vs `Workspaces` (10 chars vs 12 chars Arabic) | ✅ Comparable; no overflow concern |
| 3 | `تحرير الشريط الجانبي` — length vs `Edit Sidebar` (12 chars vs 21 chars Arabic) | ⚠️ Arabic is notably longer. A3 should verify sidebar label truncation behavior on narrow sidebar widths. Recommend mobile/narrow breakpoint test. |
| 4 | `تبديل المظهر` — length vs `Toggle Theme` (12 chars vs 12 chars Arabic) | ✅ Comparable |
| 5 | `تبديل العرض الكامل` — length vs `Toggle Full Width` (16 chars vs 18 chars Arabic) | ✅ Comparable; A3 should verify toolbar button label does not overflow at standard widths |
| 6 | `إعدادات الخطوط` — length vs `Typography Settings` (20 chars vs 15 chars Arabic) | ✅ Arabic is shorter; no overflow risk |
| All | Plural forms | ✅ All six are singular/non-count labels; no plural form required |
| All | Gender agreement (Arabic grammatical gender) | No noun-adjective constructions requiring gender agreement in items 1–4. Items 5–6 require A1 to confirm gender agreement of each compound (see §A1). |

**A3 pre-assessment summary:** Five of six pass all structural checks without concern. Item 3 (`تحرير الشريط الجانبي`) warrants a narrow-width/mobile truncation test. This is not a blocking finding but must be recorded in the A3 sign-off.

---

## A1 — Arabic Localization Assessment (Linguistic)

Assessment of each term against Modern Standard Arabic (MSA) conventions, Egyptian usage preference, UI brevity standards, grammatical correctness, and consistency with the existing Construction ERP Arabic glossary.

### A1-1 — `Desktop` → `سطح المكتب`

**Linguistic analysis:**

- **سطح المكتب** is the universally accepted Arabic term for the computing concept of "Desktop" (the home/launcher screen).
- Literal meaning: سطح = surface/top; المكتب = the desk/office. Together: "the desk surface."
- Established across all major Arabic operating systems (Windows, macOS, Android, iOS) and web applications for 20+ years.
- Egyptian users universally recognize this term. No alternative is in common use.
- No grammatical concern. Definite article `ال` on `المكتب` is correct (definite construction with `سطح` in iḍāfa).
- **Recommendation to A1:** Standard; no revision needed. Confirm against any existing ERP glossary entry for this term.

### A1-2 — `Workspaces` → `مساحات العمل`

**Linguistic analysis:**

- **مساحات العمل** — مساحات = spaces/areas (plural of مساحة); العمل = the work.
- This is the standard Arabic translation of "Workspaces" in modern software interfaces (used in Google Workspace Arabic, Microsoft 365 Arabic, and others).
- Grammatically correct: broken plural مساحات + iḍāfa with العمل.
- An alternative is **بيئات العمل** (work environments), which is slightly more formal and enterprise-oriented but less immediately intuitive to general users.
- For a business ERP Frappe navigation term, **مساحات العمل** is the more recognizable and user-friendly choice.
- **Recommendation to A1:** Accept as proposed. If the organization prefers a more formal register, بيئات العمل is defensible but requires a consistency decision across all Frappe navigation terms.

### A1-3 — `Edit Sidebar` → `تحرير الشريط الجانبي`

**Linguistic analysis:**

- **تحرير** = editing/to edit (verb noun — maṣdar). Correct for the UI action of editing/modifying.
- **الشريط** = the strip/band/bar. **الجانبي** = lateral/side (adjective).
- **الشريط الجانبي** is the established Arabic for "Sidebar" — used by Mozilla, Google, Microsoft, and others.
- Adjective **الجانبي** correctly follows الشريط with matching gender (masculine) and definiteness (definite).
- Alternative: **تعديل الشريط الجانبي** using **تعديل** (modification) instead of **تحرير** (editing). Both are correct. **تحرير** has stronger connotation of content editing; **تعديل** connotes adjustment/modification. For UI that allows drag-and-drop sidebar customization, **تحرير** is marginally more appropriate.
- Length note: 21 Arabic characters vs 12 English — A1 should confirm if the label is truncated to an icon-only state at narrow widths, in which case the length is irrelevant at display time.
- **Recommendation to A1:** Accept as proposed. Note the length flag from A3.

### A1-4 — `Toggle Theme` → `تبديل المظهر`

**Linguistic analysis:**

- **تبديل** = switching/toggling (maṣdar of بدّل = to switch/exchange). Appropriate for a toggle action.
- **المظهر** = the appearance/look/theme. Definite with ال.
- This is the standard rendering of "Theme" in Arabic UI — used in Windows, Chrome, and most major software.
- Alternative: **تبديل السمة** using **السمة** (the characteristic/scheme). This is used in some Arabic Linux distributions. **المظهر** is more natural for Egyptian general users.
- Grammatically correct: تبديل + definite noun object in iḍāfa construction.
- **Recommendation to A1:** Accept as proposed. Confirm **تبديل** is used consistently for other Toggle actions in the system.

### A1-5 — `Toggle Full Width` → `تبديل العرض الكامل`

**Linguistic analysis:**

- **تبديل** = toggle (same as above; consistency check passes).
- **العرض** = the width / the display / the presentation. Definite.
- **الكامل** = the complete/full. Adjective following العرض.
- Grammatically correct: definite adjective **الكامل** agrees with masculine **العرض**.
- **العرض الكامل** as "full width" is correct and natural. The full phrase تبديل العرض الكامل = "toggle full width" is clear.
- ⚠️ **Dual-meaning flag (forwarded to A2):** In Arabic accounting, **العرض** also means "bid/tender offer" (عروض الأسعار = price offers/bids). In UI context alongside **تبديل** (toggle) this ambiguity is entirely resolved by context, but A2 must confirm in writing.
- **Recommendation to A1:** Accept as proposed. Confirm consistent use of **تبديل** for Toggle actions.

### A1-6 — `Typography Settings` → `إعدادات الخطوط`

**Linguistic analysis:**

- **إعدادات** = settings (plural of إعداد; correct for settings menus).
- **الخطوط** = the fonts / the lines / the scripts. Plural of خط (line/font/script).
- In Arabic software UI, **الخطوط** consistently means "fonts/typefaces" in a settings context.
- Grammatically correct: iḍāfa construction إعدادات + الخطوط.
- ⚠️ **Dual-meaning flag (forwarded to A2):** In Egyptian accounting and construction, **خطوط** also means:
  - line items in a budget/BOQ (خطوط البنود)
  - pipeline/duct runs in MEP/civil engineering
  These meanings are entirely different contexts, but A2 must explicitly confirm no confusion risk.
- Alternative: **إعدادات الطباعة** (print/typography settings) — but this is more ambiguous (print = طباعة covers both typography AND physical printing). **إعدادات الخطوط** is more precise for font/typeface settings.
- **Recommendation to A1:** Accept as proposed. Ensure the menu label appears in a Settings/Appearance context so the font meaning is unambiguous at point of use.

---

## A2 — Domain Review Assessment (Egyptian Accounting and Construction)

A2 review evaluates whether the proposed Arabic is appropriate for Egyptian accounting and contracting professional usage, checks for domain-specific dual meanings, and records "Not Applicable" for terms that have no domain sensitivity.

### A2 general assessment

All six terms are **generic software UI chrome** — they are Frappe framework navigation, sidebar, and appearance controls. None are accounting entries, financial report labels, chart of accounts names, transaction terms, or construction document headings. They will appear in the Frappe Desk interface regardless of the user's business domain.

### A2-1 — `Desktop` → `سطح المكتب`

**Domain assessment:**  
- سطح المكتب has no overlap with Egyptian accounting or construction terminology.
- In Egyptian accounting Arabic, "المكتب" means "the office/bureau" — fully consistent with the software desktop being the user's digital office starting point.
- **A2 pre-assessment: Not Applicable.** No accounting or contracting domain concern. A2 reviewer should record: *"Generic UI term. No accounting or construction terminology sensitivity. Domain review: Not Applicable."*

### A2-2 — `Workspaces` → `مساحات العمل`

**Domain assessment:**  
- In Egyptian construction, **مساحة** is used as a technical term for area measurement (e.g., مساحة الأرض = land area). In project management and cost control, **نطاق العمل** or **حجم العمل** are used for work scope.
- **مساحات العمل** as a plural (digital work areas/spaces) is distinguishable from the physical measurement usage by context — any user in a Frappe navigation bar will understand this as software workspaces, not physical site areas.
- **A2 pre-assessment: Not Applicable.** Physical measurement context does not apply in a software navigation bar. A2 reviewer should explicitly record: *"In construction, مساحة refers to physical area. In UI navigation context, مساحات العمل is unambiguous as digital workspaces. Domain review: Not Applicable."*

### A2-3 — `Edit Sidebar` → `تحرير الشريط الجانبي`

**Domain assessment:**  
- **تحرير** in Egyptian accounting Arabic also means "drafting" (of a contract, invoice, or report). However, paired with **الشريط الجانبي** (the sidebar), no accountant or contractor would interpret this as drafting a financial document.
- **A2 pre-assessment: Not Applicable.** No domain concern. A2 reviewer should record: *"Pure UI navigation term. Domain review: Not Applicable."*

### A2-4 — `Toggle Theme` → `تبديل المظهر`

**Domain assessment:**  
- **المظهر** in Egyptian accounting/legal Arabic can mean "the financial appearance" (as in مظهر القوائم المالية = appearance of financial statements). However, the UI context (toggle + visual theme of the application) makes this entirely unambiguous.
- **A2 pre-assessment: Not Applicable.** No domain concern. A2 reviewer should record: *"Pure UI visual appearance control. Domain review: Not Applicable."*

### A2-5 — `Toggle Full Width` → `تبديل العرض الكامل` ⚠️

**Domain assessment — explicit dual-meaning resolution required:**

In Egyptian accounting and contracting Arabic, **العرض** has established domain meanings:

| Domain usage | Arabic | Context |
|---|---|---|
| Price offer / bid | عرض سعر / عرض مالي | Procurement and tendering |
| Tender submission | تقديم العروض | Contracting and subcontracting |
| Presentation of financial statements | عرض القوائم المالية | Accounting |
| Bill of Quantities item width/span | lمقاس / عرض المقطع | Civil/structural engineering |

In the UI context **تبديل العرض الكامل** (toggle full width of the display/page), the word **العرض** means "display width." The action verb **تبديل** (toggle) and the interface context (appearing in Frappe toolbar alongside theme controls) eliminate ambiguity for any competent user.

**However:** The A2 reviewer must not merely record "Not Applicable" — they must explicitly state that they have considered the dual meaning and confirm that in the UI toolbar context the accounting/tendering meaning does not create confusion.

**A2 pre-assessment:** Accept as proposed, with required explicit dual-meaning statement. Suggested A2 wording: *"Reviewed. العرض in accounting Arabic means bid/offer or financial statement presentation. In the context of a Frappe toolbar toggle for page display width, the meaning is unambiguous as visual display width. The dual meaning does not create user confusion in this context. Domain review: Not Applicable."*

### A2-6 — `Typography Settings` → `إعدادات الخطوط` ⚠️

**Domain assessment — explicit dual-meaning resolution required:**

In Egyptian accounting and construction Arabic, **الخطوط** has established domain meanings:

| Domain usage | Arabic | Context |
|---|---|---|
| Budget/BOQ line items | خطوط البنود / بنود الميزانية | Cost control and BOQ |
| Pipeline/duct runs | الخطوط الرئيسية / خط الأنابيب | MEP, civil engineering |
| Credit line | خط ائتمان | Banking and finance |
| Route/path | خط السير | Logistics and projects |

In the UI context **إعدادات الخطوط** (font/typography settings), the word **الخطوط** means "typefaces/fonts." The context (appearing in a Settings menu for text appearance) makes this unambiguous.

**However:** This dual meaning is more present in an accounting ERP than in generic consumer software, because users navigate BOQ line items and budgets daily. The A2 reviewer must explicitly address whether an Egyptian accountant or site engineer seeing **إعدادات الخطوط** in a Settings menu could momentarily misread it as "line item settings" or "pipeline settings."

Assessment: The Settings menu context (adjacent to theme, width, and appearance controls) is sufficient disambiguation. An accountant reaching this menu is clearly in Appearance/Display settings, not financial data settings.

**A2 pre-assessment:** Accept as proposed, with required explicit dual-meaning statement. Suggested A2 wording: *"Reviewed. الخطوط in construction/accounting Arabic refers to line items (BOQ) and pipeline runs. In the context of a Settings/Appearance section controlling typeface and font display, the meaning is unambiguous as fonts/typography. The BOQ and engineering meanings do not create confusion in a settings UI context. Domain review: Not Applicable."*

---

## Summary for Human Reviewers

### What this document provides
- Mechanical A3 structural checks (all pass; one length flag for item 3)
- Linguistic analysis for A1 (all six terms are linguistically standard and correct)
- Domain analysis for A2 (all six are generic UI; items 5 and 6 carry dual-meaning flags requiring explicit A2 acknowledgment)

### What still requires human action before any row can be Released

| Required action | Status |
|---|---|
| A1 named reviewer signs each row | **Not done — reviewer not yet nominated** |
| A2 named reviewer signs each row with explicit dual-meaning statements for items 5 and 6 | **Not done — reviewer not yet nominated** |
| A3 named reviewer signs each row and confirms the item 3 length test result | **Not done — reviewer not yet nominated** |
| Release authority promotes rows to Released | **Not done — authority not yet nominated** |
| Narrow-width/mobile truncation test for item 3 (`تحرير الشريط الجانبي`) | **Not done — pending A3 sign-off** |
| Consistency check: **تبديل** used uniformly for all Toggle actions in the system | **Not done — pending A1 review** |
| Consistency check: **إعدادات** used uniformly for all Settings labels in the system | **Not done — pending A1 review** |

### How to proceed when reviewers are nominated

When the owner nominates A1, A2, A3, and release authority:

1. Share this document with all three reviewers.
2. A1 reviews §A1 assessments and signs each row with name and date.
3. A2 reviews §A2 assessments, writes the explicit dual-meaning statements for items 5 and 6, and signs each row with name and date.
4. A3 reviews §A3 assessments, performs the item 3 narrow-width test, and signs each row with name and date.
5. Once all three quorum members have signed all six rows, the release authority promotes them to Released and records the app commit and catalog hash.
6. The Released rows are added to `construction/data/translations/approved_ar_overrides.csv` under the standard versioned payload format.
7. A new release import is run and verified in a new Arabic session — not a hard refresh.

### Branch and evidence preservation

Until the quorum is complete:
- The uncommitted branch containing the proposed translations is preserved as-is.
- No later stages (Stage 2 catalog pipeline, Stage 3 bilingual registry) are started.
- This document is the evidence file for Stage 1C pre-review. It is updated only when reviewer sign-offs are recorded.

---

## Reviewer Sign-off Table (To be completed by named reviewers)

| # | English | Proposed Arabic | A1 sign-off | A2 sign-off | A3 sign-off | Release authority | Status |
|---|---|---|---|---|---|---|---|
| 1 | Desktop | سطح المكتب | Name / Date: | Name / Date: | Name / Date: | Name / Date: | PENDING |
| 2 | Workspaces | مساحات العمل | Name / Date: | Name / Date: | Name / Date: | Name / Date: | PENDING |
| 3 | Edit Sidebar | تحرير الشريط الجانبي | Name / Date: | Name / Date: | Name / Date: + narrow-width test result | Name / Date: | PENDING |
| 4 | Toggle Theme | تبديل المظهر | Name / Date: | Name / Date: | Name / Date: | Name / Date: | PENDING |
| 5 | Toggle Full Width | تبديل العرض الكامل | Name / Date: | Name / Date: + explicit dual-meaning statement | Name / Date: | Name / Date: | PENDING |
| 6 | Typography Settings | إعدادات الخطوط | Name / Date: | Name / Date: + explicit dual-meaning statement | Name / Date: | Name / Date: | PENDING |
