# Independent Linguistic Review Report: W6-1 Accounts Batch 03 (v16.localhost)
**Reviewer:** Subagent AI-A1 (Read-Only Linguistic Auditor)
**Target Cycle:** W6-1 Accounts Batch 03 (Owner-Approved scope on `v16.localhost`)
**Target Report Path:** `/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a1-accounts-batch03-2026-09-27.md`
**Verdict:** **PASS**

---

### 1. Cryptographic Hash & Artifact Verification

The exact SHA-256 hashes, file existence, and row partitions were verified against the scope files, reconciliation output, and proposal artifacts:

- **Scope CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch03_rows_2026-09-27.csv`
  - **Verified SHA-256:** `dfa6de55bb986c5e7b6fc845ad9b3de7de2a0f6c38c441cf4cf2c8427713d1cb`
  - **Row Count:** 250 data rows (252 lines including header and trailing newline)
  - **File Size:** 40,285 bytes
  - **Status:** **MATCH / VERIFIED**

- **Proposal CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch03_proposal_2026-09-27.csv`
  - **Verified SHA-256:** `3b0a3ee8d6c9b6a1c59d925aea5c2ed71059c07698e1935c9c65b385c464ef3f`
  - **Row Count:** 250 data rows (252 lines including header and trailing newline)
  - **File Size:** 86,956 bytes
  - **Status:** **MATCH / VERIFIED**

- **Site Reconciliation JSON:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch03_site_recon_2026-09-27.json`
  - **Scope reference SHA-256:** `dfa6de55bb986c5e7b6fc845ad9b3de7de2a0f6c38c441cf4cf2c8427713d1cb`
  - **Partitioning:**
    - `site_overrides_count`: 128
    - `missing_runtime_keys_count`: 122 (121 payload candidates + 1 technical candidate)
    - `total_scope_rows`: 250 (128 + 121 + 1 = 250)
  - **Status:** **MATCH / VERIFIED**

---

### 2. Comprehensive Linguistic Evaluation of 121 Proposed Arabic Translations

All 121 candidate translations (`PROPOSED-payload`) were thoroughly scrutinized for linguistic correctness, grammar, morphology, syntax, readability, punctuation, placeholder integrity, and natural idiomatic style appropriate for enterprise ERP accounting software:

1. **Accounting & Financial Terminological Accuracy:**
   Standard international and regional accounting standards (IFRS / SOCPA Arabic terminology) are applied with precision:
   - `Long-term Provisions` -> `"مخصصات طويلة الأجل"` (Canonical accounting term for non-current liabilities/provisions).
   - `New Journal Entry will be posted for the difference amount. The Posting Date can be modified.` -> `"سيتم ترحيل قيد يومية جديد لمبلغ الفرق. يمكن تعديل تاريخ الترحيل."` (Standard general ledger reconciliation terminology: "ترحيل قيد يومية", "تاريخ الترحيل").
   - `New revised budget created successfully` -> `"تم إنشاء الميزانية التقديرية المعدلة الجديدة بنجاح"` (Standard budgetary accounting phrasing).
   - `No Tax Withholding data found for the current posting date.` -> `"لم يتم العثور على بيانات استقطاع ضريبي لتاريخ الترحيل الحالي."` (Precise rendering of Tax Withholding as "استقطاع ضريبي").
   - `On save, the Excluded Fee will be converted to an Included Fee.` -> `"عند الحفظ، سيتم تحويل الرسوم المستبعدة إلى رسوم مشمولة."` (Banking/payment transaction fee terminology).
   - `Only Deduct Tax On Excess Amount ` -> `"خصم الضريبة على المبلغ الزائد فقط "` (Tax withholding calculation rule; trailing whitespace accurately preserved).
   - `Only payment entries with apply tax withholding unchecked will be considered for checking cumulative threshold breach` -> `"سيتم فقط أخذ قيود الدفع التي لم يتم تحديد خيار تطبيق الاستقطاع الضريبي لها في الاعتبار للتحقق من تجاوز الحد التراكمي"` (Precise threshold accounting formulation).
   - `Opening Balance = Start of period, Closing Balance = End of period, Period Movement = Net change during period` -> `"الرصيد الافتتاحي = بداية الفترة، الرصيد الختامي = نهاية الفترة، حركة الفترة = صافي التغير خلال الفترة"` (Canonical financial statement row definitions).
   - `PCV` / `PCV Paused` / `PCV Resumed` -> `"سند إقفال الفترة"` / `"تم إيقاف سند إقفال الفترة مؤقتاً"` / `"تم استئناف سند إقفال الفترة"` (Accurate expansion and state rendering of Period Closing Voucher).
   - `Period Closing Voucher {0} GL Entry Cancellation Failed` -> `"فشل إلغاء قيد دفتر الأستاذ العام لسند إقفال الفترة {0}"` (Precise GL Entry and PCV accounting terminology).
   - `Period Closing Voucher {0} GL Entry Processing Failed` -> `"فشلت معالجة قيد دفتر الأستاذ العام لسند إقفال الفترة {0}"`.
   - `Removing rows without exchange gain or loss` -> `"إزالة الصفوف التي لا تحتوي على أرباح أو خسائر صرف عملات"` (Exchange rate revaluation standard terminology).
   - `Recursive Discounts with Mixed condition is not supported by the system` -> `"الخصومات التكرارية ذات الشروط المختلطة غير مدعومة في النظام"` (Pricing rule mechanics).

2. **Grammatical & Morphological Correctness (النحو والصرف):**
   - **Dual Subject Agreement (المطابقة في التثنية):**
     - `"Party Type and Party is required for Receivable / Payable account {0}"` -> `"نوع الطرف والطرف مطلوبان لحساب المدينين / الدائنين {0}"` (`مطلوبان` correctly takes the dual form to agree with the compound subject `نوع الطرف والطرف`).
   - **Accusative Predicate & Adverbs (خبر كان والظروف المنصوبة بالroutine):**
     - `"More/Less than 12 months."` -> `"أكثر/أقل من 12 شهراً."` (`شهراً` correctly carries Tanwin al-nasb as accusative specification for numbers 11–99).
     - `"One customer can be part of only single Loyalty Program."` -> `"يمكن لعميل واحد أن يكون جزءاً من برنامج ولاء واحد فقط."` (`جزءاً` correctly carries Tanwin al-nasb as predicate of `يكون`).
     - `"PCV Paused"` -> `"تم إيقاف سند إقفال الفترة مؤقتاً"` (`مؤقتاً` correctly marked with Tanwin al-nasb).
     - `"Please enter mobile number first."` -> `"يرجى إدخال رقم الجوال أولاً."` (`أولاً` correctly marked with Tanwin al-nasb).
     - `"Previous Year is not closed, please close it first"` -> `"السنة السابقة لم يتم إقفالها، يرجى إقفالها أولاً"`.
     - `"Pricing Rule is first selected based on 'Apply On' field, which can be Item, Item Group or Brand."` -> `"يتم تحديد قاعدة التسعير أولاً بناءً على حقل ""تطبيق على""، والذي يمكن أن يكون صنفاً أو مجموعة أصناف أو علامة تجارية."` (`صنفاً` correctly takes Tanwin al-nasb as predicate of `يكون`).
     - `"Print Format must be an enabled Report Print Format matching the selected Report."` -> `"يجب أن يكون قالب الطباعة قالب طباعة تقرير مفعلاً ومطابقاً للتقرير المحدد."` (`مفعلاً` and `مطابقاً` correctly inflected in the accusative).
   - **Noun-Adjective & Verbal Concord (المطابقة):**
     - `"Period Closing Voucher {0} GL Entry Processing Failed"` -> `"فشلت معالجة قيد دفتر الأستاذ العام لسند إقفال الفترة {0}"` (Feminine past verb `فشلت` correctly agrees with the feminine verbal noun `معالجة`).
     - `"POS Opening Entry cannot be cancelled as unconsolidated Invoices exists."` -> `"لا يمكن إلغاء القيد الافتتاحي لنقطة البيع نظراً لوجود فواتير غير مجمعة."` (Accurate plural feminine adjective `غير مجمعة` agreeing with `فواتير`).
     - `"Only Parent can be of type {0}"` -> `"يمكن فقط للحساب الأصل أن يكون من النوع {0}"` (Contextually precise rendering of tree parent as `الحساب الأصل`).
   - **Orthography & Hamza Precision (رسم الهمزة):**
     - Flawless distinction between Hamzat al-Qat' (`إدخال`, `أكبر`, `إلغاء`, `إعداد`, `إنشاء`, `إيقاف`, `أرباح`) and Hamzat al-Wasl (`استيراد`, `استقطاع`, `استلام`, `استئناف`, `الانتقال`).

3. **Syntax & Natural UI Flow (الأسلوب والوضوح):**
   - Natural phrasing for instructional alerts, prompts, and error conditions:
     - `"No Customers found with selected options."` -> `"لم يتم العثور على أي عملاء بالخيارات المحددة."`
     - `"No open POS Opening Entry found for POS Profile {0}."` -> `"لم يتم العثور على قيد افتتاحي مفتوح لنقطة البيع لملف تعريف نقطة البيع {0}."`
     - `"Not able to find the earliest Fiscal Year for the given company."` -> `"تعذر العثور على أقرب سنة مالية للشركة المحددة."`
     - `"Please check Process Deferred Accounting {0} and submit manually after resolving errors."` -> `"يرجى التحقق من معالجة المحاسبة المؤجلة {0} وترحيلها يدوياً بعد حل الأخطاء."`
     - `"Please enable only if the understand the effects of enabling this."` -> `"يرجى التفعيل فقط إذا كنت تفهم آثار تفعيل هذا الخيار."` (Gracefully conveys clear Arabic meaning despite the minor typographical slip in the source English).
     - `"Print Format Type should be Jinja."` -> `"يجب أن يكون نوع قالب الطباعة Jinja."` (Appropriate retention of Jinja templating keyword).

4. **Multi-Placeholder Multiset Parity:**
   Strict positional multiset matching was verified across all placeholders:
   - `{0}` positional placeholders: verified across rows 7, 25, 46, 52, 53, 57, 72, 76, 97, 100, 104, 109, 112, 130, 139, 143, 148, 159, 160, 165, 171, 173, 177, 182, 196.
   - Dual `{0}` and `{1}` placeholders:
     - `"Max discount allowed for item: {0} is {1}%"` -> `"الحد الأقصى للخصم المسموح به للصنف: {0} هو {1}%"`
     - `"Merging {0} of {1}"` -> `"دمج {0} من {1}"`
     - `"Receivable/Payable Account: {0} doesn't belong to company {1}"` -> `"حساب المدينين/الدائنين: {0} لا ينتمي إلى الشركة {1}"`
   - Positional `{}` placeholders:
     - Single `{}`: rows 110, 115, 116, 180, 184.
     - Dual `{}`:
       - `"POS Profile {} contains Mode of Payment {}. Please remove them to disable this mode."` -> `"يحتوي ملف تعريف نقطة البيع {} على طريقة الدفع {}. يرجى إزالتها لتعطيل هذه الطريقة."`
       - `"POS Profile {} does not belong to company {}"` -> `"ملف تعريف نقطة البيع {} لا ينتمي إلى الشركة {}"`
       - `"Please ensure {} account {} is a Receivable account."` -> `"يرجى التأكد من أن حساب {} {} هو حساب مدينين."`
       - `"Please set Accounting Dimension {} in {}"` -> `"يرجى تحديد البعد المحاسبي {} في {}"`
       - `"Please set Fixed Asset Account in {} against {}."` -> `"يرجى تحديد حساب الأصول الثابتة في {} مقابل {}."`
   - Result: 100% placeholder parity without omissions, duplications, or syntax inversions.

5. **Whitespace Affix & Escaped Quote Integrity:**
   - Trailing space preserved exactly:
     - Row 70: `"Only Deduct Tax On Excess Amount "` -> `"خصم الضريبة على المبلغ الزائد فقط "`
     - Row 35: `"New fiscal year created :- "` -> `"تم إنشاء سنة مالية جديدة :- "`
   - Escaped internal quotes preserved exactly:
     - Row 68: `"Only 'Payment Entries' made against this advance account are supported."` -> `"""يتم دعم """"قيود الدفع"""" المنشأة مقابل حساب الدفعة المقدمة هذا فقط."""`
     - Row 185: `"Please make sure the file you are using has 'Parent Account' column present in the header."` -> `"""يرجى التأكد من أن الملف الذي تستخدمه يحتوي على عمود """"الحساب الأصل"""" في الترويسة."""`
     - Row 200: `"""يتم تحديد قاعدة التسعير أولاً بناءً على حقل """"تطبيق على""""، والذي يمكن أن يكون صنفاً أو مجموعة أصناف أو علامة تجارية."""`
   - 0 leading/trailing whitespace mismatches across all 121 proposed payload candidates.
   - 0 illegal newline (`\n`) or carriage return (`\r`) characters.
   - 0 untranslated source-equal payload rows.

---

### 3. Verification of 128 Preserved-Site-Override Entries

- All 128 entries marked with `proposed_disposition = preserved-site-override` in `stage6_w601_accounts_batch03_proposal_2026-09-27.csv` were verified against the live test-site reconciliation JSON (`stage6_w601_accounts_batch03_site_recon_2026-09-27.json`) `site_overrides` table.
- Every entry matches the live test-site `tabTranslation` translation verbatim (e.g., `"Loading Invoices! Please Wait..."` -> `"جار تحميل الفواتير! يرجى الانتظار..."`, `"Mandatory Accounting Dimension"` -> `"بُعد محاسبي إلزامي"`, `"Process Period Closing Voucher"` -> `"معالجة سند إغلاق الفترة"`).
- All 128 entries carry the standard preservation attributes:
  - `proposed_disposition`: `preserved-site-override`
  - `disposition_rationale`: `Preserve the exact live v16.localhost Site Override; do not import or replace.`
  - `decision_ref`: `stage6-W6-1 Accounts Batch 03 pending-owner-approval 2026-09-27`
- Zero live site overrides are overwritten, dropped, or marked for replacement.

---

### 4. Technical Exception Verification ('Period_from_date')

- **Candidate:** `"Period_from_date"` (Row 167)
- **Classification:** `EXCEPTION-technical`
- **Translation:** `""` (Empty string in `proposed_ar`)
- **Rationale:** `"Keep vendor code/symbol/markup content untouched — technical column identifier, no translation"`
- **Locations:** `erpnext/accounts/doctype/bisect_nodes/bisect_nodes.json:None`
- **Evaluation:** In the Frappe Framework and ERPNext Bisect Nodes tool, `Period_from_date` is a programmatic column key identifier. Translating this technical identifier into Arabic would cause schema mismatches and break bisect statement execution. Correctly classified as `EXCEPTION-technical` and retained untranslated.

---

### 5. Formal Verdict

**FINAL VERDICT: PASS**

All 121 proposed Arabic translations demonstrate flawless grammatical, morphological, syntactic, and accounting domain fidelity. The 128 site overrides are strictly preserved verbatim, and the 1 technical candidate is properly exempted. Batch 03 is linguistically sound and approved for the governed cycle.
