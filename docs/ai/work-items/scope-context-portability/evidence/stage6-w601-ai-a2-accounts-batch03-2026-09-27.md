# Formal Review Verdict: PASS
**Role:** AI-A2 Independent Domain and Terminology Reviewer
**Scope:** Stage 6 — W6-1 Accounts Batch 03 (v16.localhost)
**Mode:** Strictly Read-Only Domain Evaluation
**Report Destination:** `/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a2-accounts-batch03-2026-09-27.md`

---

### 1. Cryptographic Hash & Batch Partition Verification
- **Scope CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch03_rows_2026-09-27.csv`
  - Expected SHA-256: `dfa6de55bb986c5e7b6fc845ad9b3de7de2a0f6c38c441cf4cf2c8427713d1cb`
  - Verified SHA-256: `dfa6de55bb986c5e7b6fc845ad9b3de7de2a0f6c38c441cf4cf2c8427713d1cb` (**MATCH**)
- **Proposal CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch03_proposal_2026-09-27.csv`
  - Expected SHA-256: `3b0a3ee8d6c9b6a1c59d925aea5c2ed71059c07698e1935c9c65b385c464ef3f`
  - Verified SHA-256: `3b0a3ee8d6c9b6a1c59d925aea5c2ed71059c07698e1935c9c65b385c464ef3f` (**MATCH**)
- **Site Recon JSON:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch03_site_recon_2026-09-27.json`
- **Total Rows in Scope:** 250 rows, partitioned strictly into:
  - `preserved-site-override`: 128 rows
  - `PROPOSED-payload`: 121 rows
  - `EXCEPTION-technical`: 1 row (`Period_from_date`)
  - Total: 128 + 121 + 1 = 250 rows.

---

### 2. Preservation of 128 Site Overrides
- Reconciled against `stage6_w601_accounts_batch03_site_recon_2026-09-27.json` from `v16.localhost`.
- All 128 site overrides are assigned disposition `preserved-site-override` with rationale `"Preserve the exact live v16.localhost Site Override; do not import or replace."`.
- Key live accounting overrides verified preserved verbatim include:
  - `'Loading Invoices! Please Wait...'` -> `'جار تحميل الفواتير! يرجى الانتظار...'`
  - `'MT940 file detected. Please enable 'Import MT940 Format' to proceed.'` -> `'تم اكتشاف ملف MT940. يرجى تمكين 'استيراد تنسيق MT940' للمتابعة.'`
  - `'Main Cost Center'` -> `'مركز التكلفة الرئيسي'`
  - `'Mandatory Accounting Dimension'` -> `'بُعد محاسبي إلزامي'`
  - `'Margin View'` -> `'عرض الهامش'`
  - `'Max Qty (As Per Stock UOM)'` -> `'أقصى كمية (حسب وحدة قياس المخزون)'`
  - `'Maximum Payment Amount'` -> `'أقصى مبلغ دفع'`
  - `'Minimum Payment Amount'` -> `'أدنى مبلغ دفع'`
  - `'Merge Invoices Based On'` -> `'دمج الفواتير بناء على'`
  - `'Merge Similar Account Heads'` -> `'دمج رؤوس الحسابات المتشابهة'`
  - `'Missing Asset'` -> `'أصل مفقود'`
  - `'Missing Cost Center'` -> `'مركز تكلفة مفقود'`
  - `'Net Profit Ratio'` -> `'نسبة صافي الربح'`
  - `'New Balance In Account Currency'` -> `'الرصيد الجديد بعملة الحساب'`
  - `'No Matching Bank Transactions Found'` -> `'لم يتم العثور على معاملات بنكية مطابقة'`
  - `'No Outstanding Invoices found for this party'` -> `'لم يتم العثور على فواتير مستحقة لهذه الجهة'`
  - `'Non-Current Liabilities'` -> `'التزامات غير متداولة'`
  - `'Note: Due Date exceeds allowed {0} credit days by {1} day(s)'` -> `'ملاحظة: تاريخ الاستحقاق يتجاوز أيام الائتمان المسموحة {0} بمقدار {1} يوم'`
- Zero alterations, overwrites, or regressions against existing live site overrides.

---

### 3. Classification of Technical Candidate ('Period_from_date')
- **Source Text:** `Period_from_date`
- **Location:** `erpnext/accounts/doctype/bisect_nodes/bisect_nodes.json:None`
- **Classification:** `EXCEPTION-technical`
- **Rationale:** `"Keep vendor code/symbol/markup content untouched — technical column identifier, no translation"`
- **Domain Audit:** Direct inspection of DocType `Bisect Nodes` (`erpnext/accounts/doctype/bisect_nodes/bisect_nodes.json`) confirms fieldname `period_from_date` with raw un-normalized label `Period_from_date`. This is a developer-internal column/field label for tree bisection nodes rather than customer-facing UI prose. Leaving it untranslated prevents schema/database reference anomalies and preserves architectural integrity. The classification as `EXCEPTION-technical` is accurate and verified.

---

### 4. Domain & Terminology Evaluation Across ERPNext Accounts Subsystems

The 121 proposed candidate translations were audited across all functional domains against ERPNext Accounts architecture, standard accounting principles (IFRS / SOCPA), and the ERP Arabic Glossary:

1. **General Ledger, Accounting Periods & Year-End Principles:**
   - `'Opening Balance = Start of period, Closing Balance = End of period, Period Movement = Net change during period'` -> `'الرصيد الافتتاحي = بداية الفترة، الرصيد الختامي = نهاية الفترة، حركة الفترة = صافي التغير خلال الفترة'` (Fundamental accounting equation in financial statements; exact standard Arabic terminology: Opening Balance: الرصيد الافتتاحي, Closing Balance: الرصيد الختامي, Period Movement: حركة الفترة, Net change: صافي التغير).
   - `'Long-term Provisions'` -> `'مخصصات طويلة الأجل'` (IAS 37 Provisions, Contingent Liabilities and Contingent Assets; compliant with SOCPA/IFRS distinction between current and long-term provisions).
   - `'Only Parent can be of type {0}'` -> `'يمكن فقط للحساب الأصل أن يكون من النوع {0}'` (Chart of accounts hierarchy).
   - `'Please ensure {} account is a Balance Sheet account.'` -> `'يرجى التأكد من أن حساب {} هو حساب ميزانية عمومية.'`
   - `'Please enter Root Type for account- {0}'` -> `'يرجى إدخال نوع الجذر للحساب - {0}'`
   - `'Please add Root Account for - {0}'` -> `'يرجى إضافة حساب جذر لـ - {0}'`
   - `'Please add the account to root level Company - {0}'` -> `'يرجى إضافة الحساب إلى الشركة على مستوى الجذر - {0}'`
   - `'Please import accounts against parent company or enable {} in company master.'` -> `'يرجى استيراد الحسابات مقابل الشركة الأم أو تفعيل {} في سجل الشركة.'`
   - `'Please make sure the file you are using has 'Parent Account' column present in the header.'` -> `'يرجى التأكد من أن الملف الذي تستخدمه يحتوي على عمود "الحساب الأصل" في الترويسة.'`
   - `'Previous Year is not closed, please close it first'` -> `'السنة السابقة لم يتم إقفالها، يرجى إقفالها أولاً'`
   - `'Period End Date cannot be greater than Fiscal Year End Date'` -> `'لا يمكن أن يكون تاريخ نهاية الفترة أكبر من تاريخ نهاية السنة المالية'`
   - `'Period Start Date cannot be greater than Period End Date'` -> `'لا يمكن أن يكون تاريخ بداية الفترة أكبر من تاريخ نهاية الفترة'`
   - `'Period Start Date must be {0}'` -> `'يجب أن يكون تاريخ بداية الفترة {0}'`
   - `'New fiscal year created :- '` -> `'تم إنشاء سنة مالية جديدة :- '` (Affix parity preserved).
   - `'More/Less than 12 months.'` -> `'أكثر/أقل من 12 شهراً.'`
   - `'Moving up in tree ...'` -> `'الانتقال لأعلى في الشجرة...'` and `'Rebuilding BTree for period ...'` -> `'إعادة بناء شجرة B للفترة...'` (Bisect accounting statements tool).
   - `'Procedures dropped'` -> `'تم حذف الإجراءات المخزنة'`

2. **Period Closing Voucher (PCV):**
   - `'PCV'` -> `'سند إقفال الفترة'` (Period Closing Voucher; standard ERPNext mechanism for closing P&L balances to retained earnings).
   - `'PCV Paused'` -> `'تم إيقاف سند إقفال الفترة مؤقتاً'`
   - `'PCV Resumed'` -> `'تم استئناف سند إقفال الفترة'`
   - `'Period Closing Voucher {0} GL Entry Cancellation Failed'` -> `'فشل إلغاء قيد دفتر الأستاذ العام لسند إقفال الفترة {0}'`
   - `'Period Closing Voucher {0} GL Entry Processing Failed'` -> `'فشلت معالجة قيد دفتر الأستاذ العام لسند إقفال الفترة {0}'`

3. **Journals, Payments & Payment Reconciliation:**
   - `'New Journal Entry will be posted for the difference amount. The Posting Date can be modified.'` -> `'سيتم ترحيل قيد يومية جديد لمبلغ الفرق. يمكن تعديل تاريخ الترحيل.'` (Journal Entry: قيد يومية, difference amount: مبلغ الفرق, Posting Date: تاريخ الترحيل, posted: ترحيل).
   - `'No Unreconciled Invoices and Payments found for this party and account'` -> `'لم يتم العثور على فواتير ومدفوعات غير مسواة لهذا الطرف وهذا الحساب'` (Unreconciled: غير مسواة; standard reconciliation terminology).
   - `'No Unreconciled Payments found for this party'` -> `'لم يتم العثور على مدفوعات غير مسواة لهذا الطرف'`
   - `'No records found in Allocation table'` -> `'لم يتم العثور على سجلات في جدول التخصيص'`
   - `'No records found in the Invoices table'` -> `'لم يتم العثور على سجلات في جدول الفواتير'`
   - `'No records found in the Payments table'` -> `'لم يتم العثور على سجلات في جدول المدفوعات'`
   - `'Payment Reconciliation Job: {0} is running for this party. Can't reconcile now.'` -> `'مهمة تسوية المدفوعات: {0} قيد التشغيل لهذا الطرف. لا يمكن إجراء التسوية الآن.'`
   - `'Payment of {0} received successfully.'` -> `'تم استلام دفعة بقيمة {0} بنجاح.'`
   - `'Payment Terms from orders will be fetched into the invoices as is'` -> `'سيتم جلب شروط الدفع من الطلبات إلى الفواتير كما هي'`
   - `'Payment Request is already created'` -> `'طلب الدفع تم إنشاؤه بالفعل'`
   - `'Payment Request took too long to respond. Please try requesting for payment again.'` -> `'استغرق طلب الدفع وقتاً طويلاً للاستجابة. يرجى محاولة طلب الدفع مرة أخرى.'`
   - `'Payment Requests cannot be created against: {0}'` -> `'لا يمكن إنشاء طلبات دفع مقابل: {0}'`
   - `'Please cancel and amend the Payment Entry'` -> `'يرجى إلغاء قيد الدفع وتعديله'`
   - `'Please cancel payment entry manually first'` -> `'يرجى إلغاء قيد الدفع يدوياً أولاً'`
   - `'Only 'Payment Entries' made against this advance account are supported.'` -> `'يتم دعم "قيود الدفع" المنشأة مقابل حساب الدفعة المقدمة هذا فقط.'`
   - `'Party Type and Party is required for Receivable / Payable account {0}'` -> `'نوع الطرف والطرف مطلوبان لحساب المدينين / الدائنين {0}'`
   - `'Please ensure {} account {} is a Receivable account.'` -> `'يرجى التأكد من أن حساب {} {} هو حساب مدينين.'`
   - `'Receivable/Payable Account: {0} doesn't belong to company {1}'` -> `'حساب المدينين/الدائنين: {0} لا ينتمي إلى الشركة {1}'`
   - `'Opening Purchase Invoices have been created.'` -> `'تم إنشاء فواتير الشراء الافتتاحية.'`
   - `'Opening Sales Invoices have been created.'` -> `'تم إنشاء فواتير المبيعات الافتتاحية.'`
   - `'Reference number of the invoice from the previous system'` -> `'الرقم المرجعي للفاتورة من النظام السابق'`

4. **Point of Sale (POS) Opening / Closing & Invoicing:**
   - `'Multiple POS Opening Entry'` -> `'قيود افتتاحية متعددة لنقطة البيع'`
   - `'No open POS Opening Entry found for POS Profile {0}.'` -> `'لم يتم العثور على قيد افتتاحي مفتوح لنقطة البيع لملف تعريف نقطة البيع {0}.'`
   - `'No POS Profile found. Please create a New POS Profile first'` -> `'لم يتم العثور على ملف تعريف نقطة بيع. يرجى إنشاء ملف تعريف نقطة بيع جديد أولاً'`
   - `'Outdated POS Opening Entry'` -> `'قيد افتتاحي منتهي الصلاحية لنقطة البيع'`
   - `'POS Opening Entry - {0} is outdated. Please close the POS and create a new POS Opening Entry.'` -> `'القيد الافتتاحي لنقطة البيع - {0} منتهي الصلاحية. يرجى إغلاق نقطة البيع وإنشاء قيد افتتاحي جديد لنقطة البيع.'`
   - `'POS Opening Entry Cancellation Error'` -> `'خطأ في إلغاء القيد الافتتاحي لنقطة البيع'`
   - `'POS Opening Entry cannot be cancelled as unconsolidated Invoices exists.'` -> `'لا يمكن إلغاء القيد الافتتاحي لنقطة البيع نظراً لوجود فواتير غير مجمعة.'`
   - `'POS Profile - {0} has multiple open POS Opening Entries. Please close or cancel the existing entries before proceeding.'` -> `'ملف تعريف نقطة البيع - {0} يحتوي على قيود افتتاحية مفتوحة متعددة لنقطة البيع. يرجى إغلاق أو إلغاء القيود الحالية قبل المتابعة.'`
   - `'POS Closing failed while running in a background process. You can resolve the {0} and retry the process again.'` -> `'فشل إغلاق نقطة البيع أثناء التشغيل في عملية خلفية. يمكنك معالجة {0} وإعادة محاولة العملية مرة أخرى.'`
   - `'POS Invoice is already consolidated'` -> `'فاتورة نقطة البيع مجمعة بالفعل'`
   - `'POS Invoice is not submitted'` -> `'فاتورة نقطة البيع غير مرحلة'`
   - `'POS Invoice should have the field {0} checked.'` -> `'يجب تحديد الحقل {0} في فاتورة نقطة البيع.'`
   - `'POS Invoices can't be added when Sales Invoice is enabled'` -> `'لا يمكن إضافة فواتير نقطة البيع عند تفعيل فاتورة المبيعات'`
   - `'POS Invoices will be consolidated in a background process'` -> `'سيتم تجميع فواتير نقطة البيع في عملية خلفية'`
   - `'POS Invoices will be unconsolidated in a background process'` -> `'سيتم إلغاء تجميع فواتير نقطة البيع في عملية خلفية'`
   - `'POS Profile is mandatory to mark this invoice as POS Transaction.'` -> `'ملف تعريف نقطة البيع إلزامي لتمييز هذه الفاتورة كمعاملة نقطة بيع.'`
   - `'POS Profile {0} cannot be disabled as there are ongoing POS sessions.'` -> `'لا يمكن تعطيل ملف تعريف نقطة البيع {0} نظراً لوجود جلسات نقطة بيع جارية.'`
   - `'POS Profile {} contains Mode of Payment {}. Please remove them to disable this mode.'` -> `'يحتوي ملف تعريف نقطة البيع {} على طريقة الدفع {}. يرجى إزالتها لتعطيل هذه الطريقة.'`
   - `'POS Profile {} does not belong to company {}'` -> `'ملف تعريف نقطة البيع {} لا ينتمي إلى الشركة {}'`
   - `'POS Profile {} does not exist.'` -> `'ملف تعريف نقطة البيع {} غير موجود.'`
   - `'POS Profile {} is disabled.'` -> `'ملف تعريف نقطة البيع {} معطل.'`
   - `'POS Profile doesn't match {}'` -> `'ملف تعريف نقطة البيع لا يطابق {}'`

5. **MT940 Electronic Bank Statements & Banking:**
   - `'Parsed file is not in valid MT940 format or contains no transactions.'` -> `'الملف الذي تم تحليله ليس بتنسيق MT940 صالح أو لا يحتوي على أي معاملات.'` (SWIFT MT940 electronic bank statement format).
   - `'No matches occurred via auto reconciliation'` -> `'لم تحدث أي مطابقات عبر التسوية التلقائية'`
   - `'On save, the Excluded Fee will be converted to an Included Fee.'` -> `'عند الحفظ، سيتم تحويل الرسوم المستبعدة إلى رسوم مشمولة.'`
   - `'Only one of Deposit or Withdrawal should be non-zero when applying an Excluded Fee.'` -> `'يجب أن يكون أحد حقلي الإيداع أو السحب فقط غير صفري عند تطبيق رسوم مستبعدة.'` (Deposit: إيداع, Withdrawal: سحب).
   - `'Plaid Link Updated'` -> `'تم تحديث رابط Plaid'`
   - `'Please add the Bank Account column'` -> `'يرجى إضافة عمود الحساب البنكي'`

6. **Pricing Rules & Recursive Discounts:**
   - `'Min Qty (As Per Stock UOM)'` -> `'الحد الأدنى للكمية (وفقاً لوحدة قياس المخزون)'`
   - `'Min Qty should be greater than Recurse Over Qty'` -> `'يجب أن يكون الحد الأدنى للكمية أكبر من كمية التكرار'`
   - `'Max discount allowed for item: {0} is {1}%'` -> `'الحد الأقصى للخصم المسموح به للصنف: {0} هو {1}%'`
   - `'Pricing Rule is first selected based on 'Apply On' field, which can be Item, Item Group or Brand.'` -> `'يتم تحديد قاعدة التسعير أولاً بناءً على حقل "تطبيق على"، والذي يمكن أن يكون صنفاً أو مجموعة أصناف أو علامة تجارية.'`
   - `'Pricing Rule is made to overwrite Price List / define discount percentage, based on some criteria.'` -> `'تُستخدم قاعدة التسعير لتجاوز قائمة الأسعار / تحديد نسبة الخصم، بناءً على معايير محددة.'`
   - `'Pricing Rules are further filtered based on quantity.'` -> `'يتم تصفية قواعد التسعير بشكل إضافي بناءً على الكمية.'`
   - `'Qty for which recursion isn't applicable.'` -> `'الكمية التي لا ينطبق عليها التكرار.'`
   - `'Recurse Over Qty cannot be less than 0'` -> `'لا يمكن أن تكون كمية التكرار أقل من 0'`
   - `'Recursive Discounts with Mixed condition is not supported by the system'` -> `'الخصومات التكرارية ذات الشروط المختلطة غير مدعومة في النظام'`
   - `'Product Price ID'` -> `'معرف سعر المنتج'`

7. **Tax Withholding (SOCPA / ZATCA Alignment):**
   - `'No Tax Withholding data found for the current posting date.'` -> `'لم يتم العثور على بيانات استقطاع ضريبي لتاريخ الترحيل الحالي.'` (Tax withholding: استقطاع ضريبي).
   - `'Only Deduct Tax On Excess Amount '` -> `'خصم الضريبة على المبلغ الزائد فقط '` (Tax withholding threshold mechanism; exact trailing space preserved).
   - `'Only payment entries with apply tax withholding unchecked will be considered for checking cumulative threshold breach'` -> `'سيتم فقط أخذ قيود الدفع التي لم يتم تحديد خيار تطبيق الاستقطاع الضريبي لها في الاعتبار للتحقق من تجاوز الحد التراكمي'`
   - `'No {0} Accounts found for this company.'` -> `'لم يتم العثور على حسابات {0} لهذه الشركة.'` (Tax Withholding Details report).

8. **Loyalty Programs:**
   - `'Loyalty Points will be calculated from the spent done (via the Sales Invoice), based on collection factor mentioned.'` -> `'سيتم احتساب نقاط الولاء من الإنفاق المحقق (عبر فاتورة المبيعات)، بناءً على عامل التحصيل المذكور.'` (Loyalty points: نقاط الولاء, collection factor: عامل التحصيل).
   - `'One customer can be part of only single Loyalty Program.'` -> `'يمكن لعميل واحد أن يكون جزءاً من برنامج ولاء واحد فقط.'`

9. **Accounting Dimensions, Cost Centers & Fixed Assets:**
   - `'Please create a new Accounting Dimension if required.'` -> `'يرجى إنشاء بعد محاسبي جديد إذا لزم الأمر.'`
   - `'Please set Accounting Dimension {} in {}'` -> `'يرجى تحديد البعد المحاسبي {} في {}'`
   - `'Main Cost Center {0} cannot be entered in the child table'` -> `'لا يمكن إدخال مركز التكلفة الرئيسي {0} في الجدول الفرعي'`
   - `'Please set the cost center field in {0} or setup a default Cost Center for the Company.'` -> `'يرجى تحديد حقل مركز التكلفة في {0} أو إعداد مركز تكلفة افتراضي للشركة.'`
   - `'Percentage Allocation should be equal to 100%'` -> `'يجب أن تكون نسبة التخصيص مساوية لـ 100%'`
   - `'Please set Fixed Asset Account in {} against {}.'` -> `'يرجى تحديد حساب الأصول الثابتة في {} مقابل {}.'` (Fixed Asset Account: حساب الأصول الثابتة).

10. **Deferred Accounting, Foreign Exchange & Financial Reporting:**
    - `'Please check Process Deferred Accounting {0} and submit manually after resolving errors.'` -> `'يرجى التحقق من معالجة المحاسبة المؤجلة {0} وترحيلها يدوياً بعد حل الأخطاء.'`
    - `'Removing rows without exchange gain or loss'` -> `'إزالة الصفوف التي لا تحتوي على أرباح أو خسائر صرف عملات'` (IAS 21 Foreign Exchange Accounting; exchange gain or loss: أرباح أو خسائر صرف عملات).
    - `'Optional. Used with Financial Report Template'` -> `'اختياري. يُستخدم مع قالب التقرير المالي'`
    - `'Missing required filter: {0}'` -> `'عنصر التصفية الإلزامي مفقود: {0}'`
    - `'Not able to find the earliest Fiscal Year for the given company.'` -> `'تعذر العثور على أقرب سنة مالية للشركة المحددة.'`
    - `'New revised budget created successfully'` -> `'تم إنشاء الميزانية التقديرية المعدلة الجديدة بنجاح'`

---

### 5. Placeholder and Quality Invariant Checks
- Multi-placeholder strings (`{0}`, `{1}`, `{}`) maintain 100% multiset parity with source strings across all rows.
- Exact edge whitespace parity is strictly preserved (e.g. `'New fiscal year created :- '` -> `'تم إنشاء سنة مالية جديدة :- '` and `'Only Deduct Tax On Excess Amount '` -> `'خصم الضريبة على المبلغ الزائد فقط '`).
- 0 leading or trailing whitespace mismatches across all candidate rows.
- 0 newlines, carriage returns, or control characters.
- 0 source-equal (untranslated) payload rows.
- 0 empty translations in proposed payload rows.

---

### Formal Verdict
**PASS** — The proposal package for W6-1 Accounts Batch 03 strictly satisfies all domain, accounting, and terminology requirements under ERPNext Accounts and the ERP Arabic glossary, preserves the 128 Site Overrides intact, correctly classifies `Period_from_date` as an `EXCEPTION-technical`, and is approved from the AI-A2 domain perspective.
