# Independent Linguistic Review Report: W6-1 Accounts Batch 02 (v16.localhost)
**Reviewer:** Subagent AI-A1 (Read-Only Linguistic Auditor)
**Target Cycle:** W6-1 Accounts Batch 02 (Owner-Approved scope on `v16.localhost`)
**Target Report Path:** `/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a1-accounts-batch02-2026-09-27.md`
**Verdict:** **PASS**

---

### 1. Cryptographic Hash & Artifact Verification

The exact SHA-256 hashes, file existence, and row partitions were verified against the scope files, reconciliation output, and proposal artifacts:

- **Scope CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch02_rows_2026-09-24.csv`
  - **Verified SHA-256:** `dc9b6c022c01a5cfcad5c6934c58a3ba74cc091f17676b607d50a96ab0d60e4e`
  - **Row Count:** 250 rows (252 lines including header and trailing newline)
  - **File Size:** 42,779 bytes
  - **Status:** **MATCH / VERIFIED**

- **Proposal CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch02_proposal_2026-09-26.csv`
  - **Verified SHA-256:** `e0fac4c67787aba3c5ac50b52a9f21625360da0693f7b17e77dbf7a315e7567e`
  - **Row Count:** 250 rows (252 lines including header and trailing newline)
  - **File Size:** 87,552 bytes
  - **Status:** **MATCH / VERIFIED**

- **Site Reconciliation JSON:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch02_site_recon_2026-09-26.json`
  - **Scope reference SHA-256:** `dc9b6c022c01a5cfcad5c6934c58a3ba74cc091f17676b607d50a96ab0d60e4e`
  - **Partitioning:**
    - `site_overrides_count`: 160
    - `missing_runtime_keys_count`: 90 (89 payload candidates + 1 technical candidate)
    - `total_scope_rows`: 250 (160 + 89 + 1 = 250)
  - **Status:** **MATCH / VERIFIED**

---

### 2. Comprehensive Linguistic Evaluation of 89 Proposed Arabic Translations

All 89 candidate translations (`PROPOSED-payload`) were thoroughly scrutinized for linguistic correctness, grammar, morphology, syntax, readability, punctuation, placeholder integrity, and natural idiomatic style appropriate for enterprise ERP accounting software:

1. **Accounting & Financial Terminological Accuracy:**
   Standard international and regional accounting standards (IFRS / SOCPA Arabic terminology) are applied with precision:
   - `Debit Note will update it's own outstanding amount, even if 'Return Against' is specified.` -> `"سيقوم إشعار المدين بتحديث المبلغ المستحق الخاص به، حتى في حال تحديد 'مرتجع مقابل'."` (Accurate rendering of "إشعار مدين" and "المبلغ المستحق", matching ERPNext standard field labels).
   - `Debit-Credit Mismatch` -> `"عدم تطابق بين المدين والدائن"` (Standard general ledger reconciliation terminology).
   - `Debtor/Creditor Advance` -> `"دفعة مقدمة لمدين/دائن"` (Canonical accounting term for advance payments).
   - `Deferred accounting failed for some invoices:` -> `"فشلت المحاسبة المؤجلة لبعض الفواتير:"` (Accurate rendering of deferred accounting).
   - `Depreciation eliminated via reversal` -> `"تم استبعاد الإهلاك عبر القيد العكسي"` (Precise asset accounting phrasing).
   - `Impairment` -> `"اضمحلال القيمة"` (Standard IFRS/IAS 36 Arabic term for asset impairment).
   - `Interest on Fixed Deposits` -> `"فوائد الودائع لأجل"` (Standard banking/deposit term).
   - `Include Default FB Assets` -> `"تضمين أصول دفتر المالية الافتراضي"` (FB = Finance Book accurately expanded in context).
   - `Gain/Loss accumulated in foreign currency account. Accounts with '0' balance in either Base or Account currency` -> `"الأرباح/الخسائر المتراكمة في حساب العملة الأجنبية. الحسابات ذات الرصيد '0' إما بالعملة الأساسية أو بعملة الحساب"`.
   - `Enter the Bank Guarantee Number before submitting.` -> `"أدخل رقم خطاب الضمان البنكي قبل الإرسال."` (Bank Guarantee rendered as "خطاب الضمان البنكي").
   - `Payment Entry` rendered appropriately as `"سند الصرف/القبض"` in `"إذا تم التحديد، فسيُعتبر مبلغ الضريبة مشمولاً بالفعل في المبلغ المدفوع في سند الصرف/القبض"`.

2. **Grammatical & Morphological Correctness (النحو والصرف):**
   - **Accusative Predicate (خبر كان منصوب):**
     - `"If rate is zero then item will be treated as 'Free Item'"` -> `"إذا كان السعر صفراً، فسيُعامل الصنف على أنه 'صنف مجاني'"` (`صفراً` correctly carries Tanwin al-nasb).
     - `"Hide this line if amount is zero"` -> `"إخفاء هذا السطر إذا كان المبلغ صفراً"` (`صفراً` correctly marked).
     - `"If unlimited expiry for the Loyalty Points, keep the Expiry Duration empty or 0."` -> `"إذا كانت نقاط الولاء غير محددة الصلاحية، اترك مدة انتهاء الصلاحية فارغة أو 0."` (`فارغة` correctly in accusative).
     - `"If checked, the tax amount will be considered as already included in the Paid Amount in Payment Entry"` -> `"إذا تم التحديد، فسيُعتبر مبلغ الضريبة مشمولاً بالفعل في المبلغ المدفوع في سند الصرف/القبض"` (`مشمولاً` correctly in accusative).
   - **Weak Verb Imperatives (أمر الفعل المعتل الآخر):**
     - `"Discounts to be applied in sequential ranges like buy 1 get 1, buy 2 get 2, buy 3 get 3 and so on"` -> `"خصومات تُطبق في نطاقات متسلسلة مثل اشترِ 1 واحصل على 1، اشترِ 2 واحصل على 2، اشترِ 3 واحصل على 3 وهكذا"` (`اشترِ` correctly retains kasra with omission of yaa).
   - **Noun-Adjective & Verbal Concord (المطابقة):**
     - `"If enabled, this row's values will be displayed on financial charts"` -> `"إذا تم التفعيل، فستُعرض قيم هذا السطر في المخططات البيانية المالية"` (Passive feminine `فستُعرض` agrees with plural non-human `قيم`).
     - `"Exempted Role"` -> `"الدور المعفى"` (Masculine concord preserved).
     - `"Documents: {0} have deferred revenue/expense enabled for them. Cannot repost."` -> `"المستندات: {0} مفعل لها الإيراد/المصروف المؤجل. لا يمكن إعادة الترحيل."`
   - **Numeral Grammar (تمييز العدد):**
     - `"Interval should be between 1 to 59 MInutes"` -> `"يجب أن تكون الفترة بين 1 إلى 59 دقيقة"` (Accusative singular `دقيقة` correctly applied for numbers 11–59).
   - **Orthography & Hamza Precision (رسم الهمزة):**
     - All hamzat al-qat' (`إشعار`, `إجراءات`, `أولويات`, `إلغاء`, `إدخال`, `إنشاء`) and hamzat al-wasl (`استبعاد`, `استيراد`, `اشترِ`, `اختيار`) are orthographically exact.

3. **Syntax & Natural UI Flow (الأسلوب والوضوح):**
   - Natural confirmation and instructional prompts:
     - `"Do you still want to enable immutable ledger?"` -> `"هل ما زلت ترغب في تفعيل دفتر الأستاذ غير القابل للتعديل؟"`
     - `"Enable this checkbox even if you want to set the zero priority"` -> `"فعّل خانة الاختيار هذه حتى لو كنت ترغب في ضبط الأولوية على صفر"`
     - `"Helps you distribute the Budget/Target across months if you have seasonality in your business."` -> `"يساعدك على توزيع الميزانية/المستهدف عبر الأشهر إذا كانت أعمالك تتسم بالموسمية."`
     - `"From Fiscal Year cannot be greater than To Fiscal Year"` -> `"السنة المالية 'من' لا يمكن أن تكون أكبر من السنة المالية 'إلى'"` (Natural framing with quotes around field markers).
   - Error messages:
     - `"Financial Report Template {0} not found"` -> `"لم يتم العثور على نموذج التقرير المالي {0}"`
     - `"Invalid filter formula. Please check the syntax."` -> `"صيغة التصفية غير صالحة. يرجى التحقق من بناء الجملة."`
   - Sequence markers:
     - `"Item Code > Item Group > Brand"` -> `"كود الصنف > مجموعة الأصناف > العلامة التجارية"` (Delimiters preserved).

4. **Multi-Placeholder Multiset Parity:**
   Strict verification of all placeholder structures was conducted:
   - `{0}` / `{1}` positional placeholders:
     - `"From Date: {0} cannot be greater than To date: {1}"` -> `"من تاريخ: {0} لا يمكن أن يكون أكبر من إلى تاريخ: {1}"`
     - `"Item Tax Row {0}: Account must belong to Company - {1}"` -> `"سطر ضريبة الصنف {0}: يجب أن ينتمي الحساب إلى الشركة - {1}"`
   - Positional `{}` placeholders:
     - `"Invalid amount in accounting entries of {} {} for Account {}: {}"` -> `"مبلغ غير صالح في القيود المحاسبية لـ {} {} للحساب {}: {}"` (Exact 4x `{}` multiset match).
   - Single placeholders:
     - `{0}` verified across rows 27, 40, 41, 44, 45, 46, 50, 88, 97.
   - Result: 100% placeholder parity without omissions, duplications, or syntax inversions.

5. **Whitespace Affix Integrity:**
   - 0 leading/trailing whitespace mismatches across all 89 proposed payload candidates.
   - 0 illegal newline (`\n`) or carriage return (`\r`) characters.
   - 0 untranslated source-equal payload rows.

---

### 3. Verification of 160 Preserved-Site-Override Entries

- All 160 entries marked with `proposed_disposition = preserved-site-override` in `stage6_w601_accounts_batch02_proposal_2026-09-26.csv` were verified against the live test-site reconciliation JSON (`stage6_w601_accounts_batch02_site_recon_2026-09-26.json`) `site_overrides` table.
- Every entry matches the live test-site `tabTranslation` translation verbatim (e.g., `"Debit Amount in Reporting Currency"` -> `"مبلغ المدين بعملة التقارير"`).
- All 160 entries carry the standard preservation attributes:
  - `proposed_disposition`: `preserved-site-override`
  - `disposition_rationale`: `Preserve the exact live v16.localhost Site Override; do not import or replace.`
  - `decision_ref`: `stage6-W6-1 Accounts Batch 02 pending-owner-approval 2026-09-26`
- Zero live site overrides are overwritten, dropped, or marked for replacement.

---

### 4. Technical Exception Verification ('Lft')

- **Candidate:** `"Lft"`
- **Classification:** `EXCEPTION-technical`
- **Translation:** `""` (Empty string in `proposed_ar`)
- **Rationale:** `"Internal NestedSet tree column name (lft); preserved untranslated."`
- **Locations:** `erpnext/accounts/doctype/account/account.json:None; erpnext/setup/doctype/company/company.json:None`
- **Evaluation:** In the Frappe Framework, `lft` and `rgt` are reserved internal database column names used to maintain the NestedSet tree data structure (for hierarchical doctypes such as Account and Company). Translating this field label would corrupt metadata or confuse schema introspection. Correctly classified as `EXCEPTION-technical` and retained untranslated.

---

### 5. Formal Verdict

**FINAL VERDICT: PASS**

All 89 proposed Arabic translations demonstrate flawless grammatical, morphological, syntactic, and accounting domain fidelity. The 160 site overrides are strictly preserved verbatim, and the 1 technical candidate is properly exempted. Batch 02 is linguistically sound and approved for the governed cycle.
