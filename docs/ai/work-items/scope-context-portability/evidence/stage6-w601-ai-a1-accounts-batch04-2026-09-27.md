# Independent Linguistic Review Report: W6-1 Accounts Batch 04 (v16.localhost)
**Reviewer:** Subagent AI-A1 (Read-Only Linguistic Auditor)
**Target Cycle:** W6-1 Accounts Batch 04 (Owner-Approved scope on `v16.localhost`)
**Target Report Path:** `/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a1-accounts-batch04-2026-09-27.md`
**Verdict:** **PASS**

---

### 1. Cryptographic Hash & Artifact Verification

The exact SHA-256 hashes, file existence, and row partitions were verified against the scope files, reconciliation output, and proposal artifacts:

- **Scope CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch04_rows_2026-09-27.csv`
  - **Verified SHA-256:** `0286741911fbe377c0a723131611d8a91cbe7c943c59d307756d7e1f18cfae30`
  - **Row Count:** 250 data rows (252 lines including header and trailing newline)
  - **File Size:** 44,332 bytes
  - **Status:** **MATCH / VERIFIED**

- **Proposal CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch04_proposal_2026-09-27.csv`
  - **Verified SHA-256:** `4c72e83b3d41476914dcf884a8798c51ec5f6e662500105509fc2b8aad6bc47a`
  - **Row Count:** 250 data rows (252 lines including header and trailing newline)
  - **File Size:** 91,542 bytes
  - **Status:** **MATCH / VERIFIED**

- **Site Reconciliation JSON:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch04_site_recon_2026-09-27.json`
  - **Scope reference SHA-256:** `0286741911fbe377c0a723131611d8a91cbe7c943c59d307756d7e1f18cfae30`
  - **Partitioning:**
    - `site_overrides_count`: 125
    - `missing_runtime_keys_count`: 125 (124 payload candidates + 1 technical candidate)
    - `total_scope_rows`: 250 (125 + 124 + 1 = 250)
  - **Status:** **MATCH / VERIFIED**

---

### 2. Comprehensive Linguistic Evaluation of 124 Proposed Arabic Translations

All 124 candidate translations (`PROPOSED-payload`) were thoroughly scrutinized for linguistic correctness, grammar, morphology, syntax, readability, punctuation, placeholder integrity, and natural idiomatic style appropriate for enterprise ERP accounting software:

1. **Accounting & Financial Terminological Accuracy:**
   Standard international and regional accounting standards (IFRS / SOCPA Arabic terminology) are applied with precision:
   - `Return on Asset Ratio` -> `"نسبة العائد على الأصول"` (Canonical financial ratio for ROA).
   - `Return on Equity Ratio` -> `"نسبة العائد على حقوق الملكية"` (Canonical financial ratio for ROE).
   - `Revaluation Surplus` -> `"فائض إعادة التقييم"` (Standard IFRS/IAS 16 terminology for asset revaluation surplus).
   - `Short-term Investments` -> `"استثمارات قصيرة الأجل"` (Standard balance sheet current asset classification).
   - `Short-term Provisions` -> `"مخصصات قصيرة الأجل"` (Standard balance sheet current liability classification).
   - `Solvency Ratios` -> `"نسب الملاءة المالية"` (Standard financial ratio category).
   - `Reporting Currency Exchange Not Found` -> `"سعر صرف عملة التقارير غير موجود"` (Accurate rendering of reporting currency in general ledger closing).
   - `Root Type for {0} must be one of the Asset, Liability, Income, Expense and Equity` -> `"يجب أن يكون النوع الجذري لـ {0} أحد الأنواع: الأصول، الخصوم، الدخل، المصروفات، وحقوق الملكية"` (Canonical 5 core accounting root heads in Arabic).
   - `Split Early Payment Discount Loss into Income and Tax Loss` -> `"تقسيم خسارة خصم السداد المبكر إلى خسارة دخل وخسارة ضريبية"` (Accurate rendering of cash discount tax treatment).
   - `The currency of invoice {} ({}) is different from the currency of this dunning ({}).` -> `"عملة الفاتورة {} ({}) تختلف عن عملة إشعار المطالبة هذا ({})."` (Accurate credit control rendering of dunning as "إشعار المطالبة").
   - `Unrealized Profit / Loss account for intra-company transfers` -> `"حساب الأرباح / الخسائر غير المحققة للتحويلات داخل الشركة"` (Standard inter-company transfer accounting terminology).
   - `Unrealized Profit/Loss account for intra-company transfers` -> `"حساب الأرباح/الخسائر غير المحققة للتحويلات داخل الشركة"` (Strict adherence to slash spacing variant).
   - `Use Legacy Controller For Period Closing Voucher` -> `"استخدام المتحكم القديم لسند إقفال الفترة"` (Consistent rendering of Period Closing Voucher as "سند إقفال الفترة").
   - `Tax Amount will be rounded on a row(items) level` -> `"سيتم تقريب مبلغ الضريبة على مستوى السطر (الأصناف)"` (Accurate tax calculation rule).
   - `Text displayed on the financial statement (e.g., 'Total Revenue', 'Cash and Cash Equivalents')` -> `"النص المعروض في القائمة المالية (مثال: 'إجمالي الإيرادات'، 'النقد وما في حكمه')"` (Canonical IFRS presentation line items).

2. **Grammatical & Morphological Correctness (النحو والصرف):**
   - **Accusative Predicate & Adverbs (خبر كان وأخواتها والتمييز والظروف المنصوبة):**
     - `"Returned exchange rate is neither integer not float."` -> `"سعر الصرف المرتجع ليس عدداً صحيحاً ولا عشرياً."` (`عدداً صحيحاً ولا عشرياً` correctly carries Tanwin al-nasb as predicate of `ليس`).
     - `"Total distributed amount {0} must be equal to Budget Amount {1}"` -> `"يجب أن يكون إجمالي المبلغ الموزع {0} مساوياً لمبلغ الميزانية {1}"` (`مساوياً` correctly inflected with Tanwin al-nasb as predicate of `يكون`).
     - `"Total distribution percent must equal 100 (currently {0})"` -> `"يجب أن تكون نسبة التوزيع الإجمالية مساوية لـ 100 (حالياً {0})"` (`مساوية` correctly takes Tanwin al-nasb as predicate of `تكون`).
   - **Noun-Adjective & Verbal Concord (المطابقة في التذكير والتأنيث والعدد):**
     - `"Scheduler is Inactive. Can't trigger job now."` -> `"المجدول غير نشط. لا يمكن تشغيل المهمة الآن."` (Singular `job` -> `المهمة`).
     - `"Scheduler is Inactive. Can't trigger jobs now."` -> `"المجدول غير نشط. لا يمكن تشغيل المهام الآن."` (Plural `jobs` -> `المهام`). Exact morphological distinction.
     - `"Row #{0}: Dates overlapping with other row"` -> `"السطر رقم {0}: التواريخ متداخلة مع سطر آخر"` (Feminine predicate `متداخلة` agreeing with non-human plural `التواريخ`).
     - `"Successfully imported {0} record."` -> `"تم استيراد {0} سجل بنجاح."` vs `"Successfully imported {0} records."` -> `"تم استيراد {0} سجلات بنجاح."` (Careful count-noun discrimination).
     - `"Successfully updated {0} record."` -> `"تم تحديث {0} سجل بنجاح."` vs `"Successfully updated {0} records."` -> `"تم تحديث {0} سجلات بنجاح."`.
   - **Orthography & Hamza Precision (رسم الهمزة):**
     - Flawless distinction between Hamzat al-Qat' (`أصول`, `إلغاء`, `إعادة`, `إشعار`, `إيرادات`, `إدخال`, `أكبر`, `أقل`) and Hamzat al-Wasl (`استيراد`, `استثمارات`, `استئناف`, `استخدام`, `استقطاع`).

3. **Syntax & Natural UI Flow (الأسلوب والوضوح):**
   - Professional ERP instructions, alerts, and validations:
     - `"Sales Invoice mode is activated in POS. Please create Sales Invoice instead."` -> `"وضع فاتورة المبيعات مفعل في نقطة البيع. يرجى إنشاء فاتورة مبيعات بدلاً من ذلك."`
     - `"Setting the account as a Company Account is necessary for Bank Reconciliation"` -> `"تعيين الحساب كحساب شركة ضروري للتسوية البنكية"`
     - `"The original invoice should be consolidated before or along with the return invoice."` -> `"يجب تجميع الفاتورة الأصلية قبل أو بالتزامن مع فاتورة المرتجع."`
     - `"To use a different finance book, please uncheck 'Include Default FB Assets'"` -> `"لاستخدام دفتر مالي مختلف، يرجى إلغاء تحديد 'تضمين أصول الدفتر المالي الافتراضي'"`
     - `"Too many columns. Export the report and print it using a spreadsheet application."` -> `"أعمدة كثيرة جداً. قم بتصدير التقرير وطباعته باستخدام تطبيق جداول البيانات."`
     - `"Users with this role are allowed to over bill above the allowance percentage"` -> `"يُسمح للمستخدمين بهذا الدور بالفوترة الزائدة بما يتجاوز نسبة السماح"`
     - `"Users with this role will be notified if the asset depreciation gets failed"` -> `"سيتم إخطار المستخدمين بهذا الدور في حال فشل إهلاك الأصل"`
   - Sequence markers and technical tokens:
     - `"Supplier > Supplier Type"` -> `"المورد > نوع المورد"` (Hierarchy delimiter `>` preserved).
     - `"SCIO Detail"` -> `"تفاصيل SCIO"` (Acronym preserved).
     - `"The uploaded file does not appear to be in valid MT940 format."` -> `"الملف المرفوع لا يبدو بتنسيق MT940 صالح."` (MT940 preserved).
     - `"There was an issue connecting to Plaid's authentication server. Check browser console for more information"` -> `"حدثت مشكلة أثناء الاتصال بخادم مصادقة Plaid. تحقق من وحدة تحكم المتصفح لمزيد من المعلومات"` (Plaid preserved).

4. **Multi-Placeholder Multiset Parity:**
   Strict positional multiset matching was verified across all placeholders:
   - Positional `{0}`, `{1}`, `{2}`, `{3}`, `{4}`:
     - `"Row #{0}: Asset {1} cannot be sold, it is already {2}"` -> `"السطر رقم {0}: لا يمكن بيع الأصل {1}، فهو بالفعل {2}"` (3 placeholders).
     - `"Row #{0}: Item {1} in warehouse {2}: Available {3}, Needed {4}."` -> `"السطر رقم {0}: الصنف {1} في المستودع {2}: المتاح {3}، المطلوب {4}."` (5 placeholders).
     - `"Row #{0}: Stock quantity {1} ({2}) for item {3} cannot exceed {4}"` -> `"السطر رقم {0}: كمية المخزون {1} ({2}) للصنف {3} لا يمكن أن تتجاوز {4}"` (5 placeholders).
     - `"To submit the invoice without purchase order please set {0} as {1} in {2}"` -> `"لترحيل الفاتورة دون أمر شراء، يرجى تعيين {0} كـ {1} في {2}"` (3 placeholders).
     - `"To submit the invoice without purchase receipt please set {0} as {1} in {2}"` -> `"لترحيل الفاتورة دون إيصال شراء، يرجى تعيين {0} كـ {1} في {2}"` (3 placeholders).
     - `"Transaction currency: {0} cannot be different from Bank Account({1}) currency: {2}"` -> `"عملة المعاملة: {0} لا يمكن أن تختلف عن عملة الحساب البنكي({1}): {2}"` (3 placeholders).
     - Single and dual placeholders `{0}` and `{1}` verified across rows 41, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 64, 65, 66, 67, 68, 69, 114, 124, 128, 129, 130, 131, 132, 133, 134, 135, 136, 168, 169, 175, 179, 180, 181, 205, 206, 211, 234, 247.
   - Positional `{}` placeholders:
     - `"Row #{}: The original Invoice {} of return invoice {} is not consolidated."` -> `"السطر رقم {}: الفاتورة الأصلية {} لفاتورة المرتجع {} غير مجمعة."` (3x `{}`).
     - `"Row #{}: You cannot add positive quantities in a return invoice. Please remove item {} to complete the return."` -> `"السطر رقم {}: لا يمكنك إضافة كميات موجبة في فاتورة مرتجع. يرجى إزالة الصنف {} لإتمام الإرجاع."` (2x `{}`).
     - `"Tax Withholding Category {} against Company {} for Customer {} should have Cumulative Threshold value."` -> `"يجب أن تحتوي فئة الاستقطاع الضريبي {} مقابل الشركة {} للعميل {} على قيمة الحد التراكمي."` (3x `{}`).
     - `"The currency of invoice {} ({}) is different from the currency of this dunning ({})."` -> `"عملة الفاتورة {} ({}) تختلف عن عملة إشعار المطالبة هذا ({})."` (3x `{}`).
     - `"To cancel a {} you need to cancel the POS Closing Entry {}."` -> `"لإلغاء {} تحتاج إلى إلغاء قيد إغلاق نقطة البيع {}."` (2x `{}`).
     - Single `{}` verified across rows 80, 187.
   - Result: 100% placeholder parity without omissions, duplications, or syntax inversions.

5. **Whitespace Affix Integrity:**
   - Exact whitespace affix parity is maintained on trailing-space candidates:
     - `"Role Allowed to Over Bill "` -> `"الدور المسموح له بالفوترة الزائدة "` (trailing space preserved).
     - `"Sales Partner "` -> `"شريك المبيعات "` (trailing space preserved).
     - `"Select Dispatch Address "` -> `"تحديد عنوان الإرسال "` (trailing space preserved).
   - 0 leading/trailing whitespace mismatches across all remaining proposed candidates.
   - 0 illegal newline (`\n`) or carriage return (`\r`) characters.
   - 0 untranslated source-equal payload rows.

---

### 3. Verification of 125 Preserved-Site-Override Entries

All 125 entries designated as `preserved-site-override` were cross-checked against the live test-site reconciliation JSON (`stage6_w601_accounts_batch04_site_recon_2026-09-27.json`):
- Every source string maps verbatim to the existing `v16.localhost` live translation (`tabTranslation`).
- The proposed disposition is uniformly set to `preserved-site-override`.
- The disposition rationale correctly enforces: `"Preserve the exact live v16.localhost Site Override; do not import or replace."`
- In accordance with Stage 6 Plan Section 12, none of these 125 entries will overwrite or mutate the live site state.

---

### 4. Technical Exception Candidate Verification

The technical candidate row was verified:
- **Source Text:** `Rgt` (Row 33 in proposal CSV)
- **Proposed Translation:** `""` (Empty string)
- **Proposed Disposition:** `EXCEPTION-technical`
- **Disposition Rationale:** `"Keep vendor code/symbol/markup content untouched — internal NestedSet right-bound column identifier, technical exception"`
- **Evaluation:** Approved. `Rgt` is an internal column identifier representing the right boundary of the nested-set tree structure in Frappe/ERPNext DocTypes (`Account`, `Company`, etc.). Preserving it untranslated prevents runtime column resolution and schema corruption issues.

---

### 5. Formal Verdict and Sign-off

- **Linguistic Quality:** **EXCELLENT / APPROVED**
- **Accounting Accuracy:** **PRECISE & COMPLIANT WITH IFRS / SOCPA NORMS**
- **Placeholder & Affix Integrity:** **100% VERIFIED**
- **Preserved Overrides & Technical Exceptions:** **100% VERIFIED**
- **Formal Verdict:** **PASS**

Subagent AI-A1 formally recommends approving the payload candidate translations for W6-1 Accounts Batch 04.
