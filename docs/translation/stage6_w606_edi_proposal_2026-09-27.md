# Stage 6 — W6-6 EDI Remainder Proposal (2026-09-27)

**Status:** PROPOSAL ONLY — owner approval pending. No quorum review, no runtime import, no catalog update, no evidence re-pin, no git commit, no git push.

---

## 1. Scope and Artifacts

| Artifact | Path | SHA-256 | Rows |
| :--- | :--- | :--- | :---: |
| **Scope CSV** | `docs/translation/stage6_w606_edi_rows_2026-09-27.csv` | `2b0cc9b46546aa36310f81738c72ff0d2b50ca35666110033976c424c149cef1` | 26 |
| **Proposal CSV** | `docs/translation/stage6_w606_edi_proposal_2026-09-27.csv` | `ea74475780980e95f13346db8aaf8beb7b56c3202336950ae9432f2d2eebb6b7` | 26 |
| **Site Recon JSON** | `docs/translation/stage6_w606_edi_site_recon_2026-09-27.json` | Live reconciliation on `v16.localhost` | 26 |

---

## 2. Partition Summary

| Disposition | Count | Description |
| :--- | :---: | :--- |
| **`preserved-site-override`** | 9 | Preserved verbatim from live `v16.localhost` `tabTranslation` (Plan §12) |
| **`PROPOSED-payload`** | 17 | Candidate Arabic translations for ERPNext EDI module |
| **`EXCEPTION-technical`** | 0 | None (all entries are translatable user-facing or model strings) |
| **Total** | **26** | **9 + 17 + 0 = 26** |

---

## 3. Structural & HTML Validation Notes

- **Placeholder Multiset Parity:** `{0}`, `{1}`, `{2}`, and `{}` have exact multiset parity between source and proposed translation.
- **HTML Structure Validation:** `<p>...</p>` tags (in row 3) are validated independently as HTML structure, strictly preserving opening `<p>` and closing `</p>` tags.
- **Whitespace & Punctuation Parity:** Colons (`:`) and trailing ellipses (`...`) strictly match the source strings.

---

## 4. Evidence Handling Clarification

- **Proposal Stage:** No evidence envelopes or index files are modified.
- **Post-Approval Execution:** Following owner authorization, the catalog will expand by +17 rows (from 3,830 to 3,847). During final cycle verification, all 10 Stage-2 evidence envelopes will be re-assembled to pin the candidate pre-commit HEAD, ensuring 100% gate compliance (`errors=0`).

---

## 5. Full 26-Row Proposal Table

| # | Source Text | Proposed Translation | Disposition | Notes |
| :-: | :--- | :--- | :--- | :--- |
| 1 | `Additional Data` | `بيانات إضافية` | `preserved-site-override` | Live site override |
| 2 | `Applies To` | `ينطبق على` | `preserved-site-override` | Live site override |
| 3 | `Are you sure you want to delete {0}?<p>This action will also delete all associated Common Code documents.</p>` | `هل أنت متأكد من رغبتك في حذف {0}؟<p>سيؤدي هذا الإجراء أيضًا إلى حذف جميع مستندات الكود المشترك المرتبطة.</p>` | `PROPOSED-payload` | `{0}` placeholder + `<p>` tag parity |
| 4 | `Canonical URI` | `المعرف الموحد القياسي (Canonical URI)` | `PROPOSED-payload` | EDI standard field label |
| 5 | `Code List` | `قائمة الأكواد` | `preserved-site-override` | Live site override |
| 6 | `Common Code` | `الكود المشترك` | `preserved-site-override` | Live site override |
| 7 | `Default Common Code` | `الكود المشترك الافتراضي` | `preserved-site-override` | Live site override |
| 8 | `Deleting {0} and all associated Common Code documents...` | `جارٍ حذف {0} وجميع مستندات الكود المشترك المرتبطة...` | `PROPOSED-payload` | `{0}` placeholder + ellipsis parity |
| 9 | `Fetching Error` | `خطأ في الجلب` | `preserved-site-override` | Live site override |
| 10 | `If there is no title column, use the code column for the title.` | `إذا لم يكن هناك عمود للعنوان، فاستخدم عمود الكود كعنوان.` | `PROPOSED-payload` | Import guidance instruction |
| 11 | `Import Genericode File` | `استيراد ملف Genericode` | `preserved-site-override` | Live site override |
| 12 | `Import completed. {0} common codes created.` | `اكتمل الاستيراد. تم إنشاء {0} من الأكواد المشتركة.` | `PROPOSED-payload` | `{0}` placeholder parity |
| 13 | `Importing Common Codes` | `جار استيراد الأكواد المشتركة` | `preserved-site-override` | Live site override |
| 14 | `Parsing Error` | `خطأ في التحليل` | `PROPOSED-payload` | File parser error message |
| 15 | `Publisher` | `الناشر` | `PROPOSED-payload` | EDI code list publisher |
| 16 | `Publisher ID` | `معرف الناشر` | `PROPOSED-payload` | Code list identifier |
| 17 | `Select Columns and Filters` | `تحديد الأعمدة وعوامل التصفية` | `preserved-site-override` | Live site override |
| 18 | `The uploaded file does not match the selected Code List.` | `الملف المرفوع لا يتطابق مع قائمة الأكواد المحددة.` | `PROPOSED-payload` | Validation error message |
| 19 | `This value shall be used when no matching Common Code for a record is found.` | `ستُستخدم هذه القيمة عند عدم العثور على كود مشترك مطابق للسجل.` | `PROPOSED-payload` | Tooltip description |
| 20 | `You are importing data for the code list:` | `أنت تستورد بيانات لقائمة الأكواد:` | `PROPOSED-payload` | Colon parity |
| 21 | `as Code` | `ككود` | `PROPOSED-payload` | Column mapping option |
| 22 | `as Description` | `كوصف` | `PROPOSED-payload` | Column mapping option |
| 23 | `as Title` | `كعنوان` | `PROPOSED-payload` | Column mapping option |
| 24 | `by {}` | `بواسطة {}` | `PROPOSED-payload` | `{}` placeholder parity |
| 25 | `description` | `الوصف` | `PROPOSED-payload` | Standard lowercase label |
| 26 | `{0} {1} is already linked to Common Code {2}.` | `{0} {1} مرتبط بالفعل بالكود المشترك {2}.` | `PROPOSED-payload` | `{0}`, `{1}`, `{2}` placeholder parity |
