# Formal Review Verdict: PASS
**Role:** AI-A2 Independent Domain and Terminology Reviewer
**Scope:** Stage 6 — W6-1 Accounts Batch 04 (v16.localhost)
**Mode:** Strictly Read-Only Domain Evaluation
**Report Destination:** `/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a2-accounts-batch04-2026-09-27.md`

---

### 1. Cryptographic Hash & Batch Partition Verification
- **Scope CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch04_rows_2026-09-27.csv`
  - Expected SHA-256: `0286741911fbe377c0a723131611d8a91cbe7c943c59d307756d7e1f18cfae30`
  - Verified SHA-256: `0286741911fbe377c0a723131611d8a91cbe7c943c59d307756d7e1f18cfae30` (**MATCH**)
- **Proposal CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch04_proposal_2026-09-27.csv`
  - Expected SHA-256: `4c72e83b3d41476914dcf884a8798c51ec5f6e662500105509fc2b8aad6bc47a`
  - Verified SHA-256: `4c72e83b3d41476914dcf884a8798c51ec5f6e662500105509fc2b8aad6bc47a` (**MATCH**)
- **Site Recon JSON:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch04_site_recon_2026-09-27.json`
- **Total Rows in Scope:** 250 rows, partitioned strictly into:
  - `preserved-site-override`: 125 rows
  - `PROPOSED-payload`: 124 rows
  - `EXCEPTION-technical`: 1 row (`Rgt`)
  - Total: 125 + 124 + 1 = 250 rows.

---

### 2. Preservation of 125 Site Overrides
- Reconciled against `stage6_w601_accounts_batch04_site_recon_2026-09-27.json` from `v16.localhost`.
- All 125 site overrides are assigned disposition `preserved-site-override` with rationale `"Preserve the exact live v16.localhost Site Override; do not import or replace."`.
- Key live accounting overrides verified preserved verbatim include:
  - `'Report Line Items'` -> `'بنود التقرير'`
  - `'Report Template'` -> `'قالب التقرير'`
  - `'Reporting Currency Exchange Rate'` -> `'سعر صرف عملة التقارير'`
  - `'Repost Accounting Ledger'` -> `'إعادة نشر دفتر الأستاذ المحاسبي'`
  - `'Repost Accounting Ledger Items'` -> `'عناصر إعادة نشر دفتر الأستاذ المحاسبي'`
  - `'Repost Accounting Ledger Settings'` -> `'إعدادات إعادة نشر دفتر الأستاذ المحاسبي'`
  - `'Repost Allowed Types'` -> `'أنواع إعادة الترحيل المسموحة'`
  - `'Repost Error Log'` -> `'سجل أخطاء إعادة الترحيل'`
  - `'Repost Payment Ledger'` -> `'إعادة نشر دفتر أستاذ الدفع'`
  - `'Repost Payment Ledger Items'` -> `'عناصر إعادة نشر دفتر أستاذ الدفع'`
  - `'Repost Status'` -> `'حالة إعادة الترحيل'`
  - `'Request Parameters'` -> `'معايير الطلب'`
  - `'Return Against'` -> `'مرتجع مقابل'`
  - `'Revenue'` -> `'الإيراد'`
  - `'Reverse Sign'` -> `'عكس الإشارة'`
  - `'Revise Budget'` -> `'مراجعة الميزانية'`
  - `'Set Loyalty Program'` -> `'تعيين برنامج الولاء'`
- Zero alterations, overwrites, or regressions against existing live site overrides.

---

### 3. Classification of Technical Candidate ('Rgt')
- **Source Text:** `Rgt`
- **Location:** `erpnext/accounts/doctype/account/account.json:None; erpnext/setup/doctype/company/company.json:None`
- **Classification:** `EXCEPTION-technical`
- **Rationale:** `"Keep vendor code/symbol/markup content untouched — internal NestedSet right-bound column identifier, technical exception"`
- **Domain Audit:** Direct inspection confirms that in Frappe's NestedSet implementation, `lft` and `rgt` are the boundary integer coordinates defining node intervals in hierarchical trees (such as the Chart of Accounts and Company tree). In the DocType definitions of `Account` and `Company`, `Rgt` represents the raw label for this right-boundary integer field. Translating this developer/ORM structural artifact would introduce confusion, compromise architectural clarity, and offer zero UI value to end-users. Its classification as `EXCEPTION-technical` is accurate and verified.

---

### 4. Domain & Terminology Evaluation Across ERPNext Accounts Subsystems

The 124 proposed candidate translations were audited across all functional domains against ERPNext Accounts architecture, standard accounting principles (IFRS / SOCPA), and the ERP Arabic Glossary:

1. **General Ledger, Reposting & Chart of Accounts Principles:**
   - `'Root Type for {0} must be one of the Asset, Liability, Income, Expense and Equity'` -> `'يجب أن يكون النوع الجذري لـ {0} أحد الأنواع: الأصول، الخصوم، الدخل، المصروفات، وحقوق الملكية'` (Strictly conforms to the 5 fundamental elements of financial statements under IFRS Conceptual Framework and SOCPA: الأصول، الخصوم، الدخل، المصروفات، حقوق الملكية).
   - `'Reporting Currency Exchange Not Found'` -> `'سعر صرف عملة التقارير غير موجود'` (IAS 21 Presentation and Reporting Currency: عملة التقارير).
   - `'Repost has started in the background'`, `'Repost started in the background'`, `'Repost in background'`, `'Reposting in the background.'` -> `'بدأت إعادة الترحيل في الخلفية'`, `'إعادة الترحيل في الخلفية'`, `'تتم إعادة الترحيل في الخلفية.'` (Consistent usage of إعادة الترحيل for GL and payment reposting background processes).
   - `'Represents a Financial Year. All accounting entries and other major transactions are tracked against the Fiscal Year.'` -> `'يمثل السنة المالية. يتم تتبع جميع القيود المحاسبية والمعاملات الرئيسية الأخرى مقابل السنة المالية.'`
   - `'Rounding Loss Allowance should be between 0 and 1'` -> `'يجب أن يكون مخصص خسائر التقريب بين 0 و 1'` (Standard accounting allowance: مخصص خسائر التقريب).
   - `'Rows with Same Account heads will be merged on Ledger'` -> `'سيتم دمج الصفوف ذات بنود الحسابات المتطابقة في دفتر الأستاذ'` (بنود الحسابات / رؤوس الحسابات in the General Ledger).
   - `'The GL Entries and closing balances will be processed in the background, it can take a few minutes.'` -> `'ستتم معالجة قيود دفتر الأستاذ العام وأرصدة الإقفال في الخلفية، وقد يستغرق ذلك بضع دقائق.'` (GL Entries: قيود دفتر الأستاذ العام, closing balances: أرصدة الإقفال).
   - `'The GL Entries will be cancelled in the background, it can take a few minutes.'` -> `'سيتم إلغاء قيود دفتر الأستاذ العام في الخلفية، وقد يستغرق ذلك بضع دقائق.'`
   - `'This Account has '0' balance in either Base Currency or Account Currency'` -> `'هذا الحساب رصيده '0' إما بالعملة الأساسية أو بعملة الحساب'` (Base Currency: العملة الأساسية, Account Currency: عملة الحساب).
   - `'Unrealized Profit / Loss account for intra-company transfers'` -> `'حساب الأرباح / الخسائر غير المحققة للتحويلات داخل الشركة'` (Compliant with IFRS 10 consolidated financial statement intercompany eliminations: الأرباح / الخسائر غير المحققة).
   - `'Valid From must be after {0} as last GL Entry against the cost center {1} posted on this date'` -> `'يجب أن يكون حقل صالح من بعد {0} نظراً لترحيل آخر قيد دفتر أستاذ عام مقابل مركز التكلفة {1} في هذا التاريخ'`
   - `'Valuation rate for the item as per Sales Invoice (Only for Internal Transfers)'` -> `'سعر تقييم الصنف حسب فاتورة المبيعات (للتحويلات الداخلية فقط)'`
   - `'Use Legacy Controller For Period Closing Voucher'` -> `'استخدام المتحكم القديم لسند إقفال الفترة'` (Period Closing Voucher: سند إقفال الفترة).

2. **Journals & Accounting Dimensions:**
   - `'This filter will be applied to Journal Entry.'` -> `'سيتم تطبيق هذا المرشح على قيد اليومية.'` (Journal Entry: قيد اليومية).
   - `'Row {0}: {1} account already applied for Accounting Dimension {2}'` -> `'السطر {0}: تم تطبيق حساب {1} مسبقاً للبعد المحاسبي {2}'` (Accounting Dimension: البعد المحاسبي).
   - `'Restrict'` -> `'تقييد'` (Accounting Dimension Filter restriction behavior).
   - `'Track separate Income and Expense for product verticals or divisions.'` -> `'تتبع الدخل والمصروفات المنفصلة لقطاعات أو أقسام المنتجات.'` (Aligns with IFRS 8 Operating Segments for segmental reporting).

3. **POS Closing & Sales Invoicing:**
   - `'To cancel a {} you need to cancel the POS Closing Entry {}.'` -> `'لإلغاء {} تحتاج إلى إلغاء قيد إغلاق نقطة البيع {}.'` (POS Closing Entry: قيد إغلاق نقطة البيع).
   - `'To cancel this Sales Invoice you need to cancel the POS Closing Entry {}.'` -> `'لإلغاء فاتورة المبيعات هذه تحتاج إلى إلغاء قيد إغلاق نقطة البيع {}.'`
   - `'Sales Invoice does not have Payments'` -> `'فاتورة المبيعات لا تحتوي على دفعات'`
   - `'Sales Invoice is already consolidated'` -> `'فاتورة المبيعات مجمعة بالفعل'`
   - `'Sales Invoice is not created using POS'` -> `'فاتورة المبيعات لم يتم إنشاؤها باستخدام نقطة البيع'`
   - `'Sales Invoice is not submitted'` -> `'فاتورة المبيعات غير مرحلة'`
   - `'Sales Invoice mode is activated in POS. Please create Sales Invoice instead.'` -> `'وضع فاتورة المبيعات مفعل في نقطة البيع. يرجى إنشاء فاتورة مبيعات بدلاً من ذلك.'`
   - `'Transactions using Sales Invoice in POS are disabled.'` -> `'المعاملات باستخدام فاتورة المبيعات في نقطة البيع معطلة.'`

4. **Payments Reconciliation, Dunning & Bank Operations:**
   - `'Setting the account as a Company Account is necessary for Bank Reconciliation'` -> `'تعيين الحساب كحساب شركة ضروري للتسوية البنكية'` (Bank Reconciliation: التسوية البنكية).
   - `'Row {0}: Allocated amount {1} must be less than or equal to invoice outstanding amount {2}'` -> `'السطر {0}: يجب أن يكون المبلغ المخصص {1} أقل من أو يساوي المبلغ المستحق للفاتورة {2}'`
   - `'Row {0}: Allocated amount {1} must be less than or equal to remaining payment amount {2}'` -> `'السطر {0}: يجب أن يكون المبلغ المخصص {1} أقل من أو يساوي مبلغ الدفع المتبقي {2}'`
   - `'Row {0}: Payment Term is mandatory'` -> `'السطر {0}: شرط السداد إلزامي'`
   - `'Row({0}): Outstanding Amount cannot be greater than actual Outstanding Amount {1} in {2}'` -> `'السطر ({0}): لا يمكن أن يكون المبلغ المستحق أكبر من المبلغ المستحق الفعلي {1} في {2}'`
   - `'The Payment Request {0} is already paid, cannot process payment twice'` -> `'طلب الدفع {0} مدفوع بالفعل، لا يمكن معالجة الدفع مرتين'`
   - `'The allocated amount is greater than the outstanding amount of Payment Request {0}'` -> `'المبلغ المخصص أكبر من المبلغ المستحق لطلب الدفع {0}'`
   - `'The currency of invoice {} ({}) is different from the currency of this dunning ({}).'` -> `'عملة الفاتورة {} ({}) تختلف عن عملة إشعار المطالبة هذا ({}).'` (Dunning: إشعار المطالبة).
   - `'There were issues unlinking payment entry {0}.'` -> `'حدثت مشكلات أثناء إلغاء ربط قيد الدفع {0}.'` (Payment Entry: قيد الدفع).
   - `'This invoice has already been paid.'` -> `'تم سداد هذه الفاتورة بالفعل.'`
   - `'Transaction currency: {0} cannot be different from Bank Account({1}) currency: {2}'` -> `'عملة المعاملة: {0} لا يمكن أن تختلف عن عملة الحساب البنكي({1}): {2}'`
   - `'The Excluded Fee is bigger than the Deposit it is deducted from.'` -> `'الرسوم المستبعدة أكبر من الوديعة المخصومة منها.'`
   - `'Split Early Payment Discount Loss into Income and Tax Loss'` -> `'تقسيم خسارة خصم السداد المبكر إلى خسارة دخل وخسارة ضريبية'` (Early Payment Discount: خصم السداد المبكر).

5. **MT940 & Plaid / Banking Integrations:**
   - `'The uploaded file does not appear to be in valid MT940 format.'` -> `'الملف المرفوع لا يبدو بتنسيق MT940 صالح.'` (SWIFT MT940 standard electronic bank statement).
   - `'There was an issue connecting to Plaid's authentication server. Check browser console for more information'` -> `'حدثت مشكلة أثناء الاتصال بخادم مصادقة Plaid. تحقق من وحدة تحكم المتصفح لمزيد من المعلومات'`

6. **Pricing Rules:**
   - `'The following invalid Pricing Rules are deleted:'` -> `'تم حذف قواعد التسعير غير الصالحة التالية:'` (Pricing Rules: قواعد التسعير).
   - `'To not apply Pricing Rule in a particular transaction, all applicable Pricing Rules should be disabled.'` -> `'لعدم تطبيق قاعدة التسعير في معاملة معينة، يجب تعطيل جميع قواعد التسعير القابلة للتطبيق.'`
   - `'Threshold for Suggestion (In Percentage)'` -> `'حد الاقتراح (كنسبة مئوية)'`

7. **Tax Withholding (الاستقطاع الضريبي):**
   - `'Skipping Tax Withholding Category {0} as there is no associated account set for Company {1} in it.'` -> `'تخطي فئة الاستقطاع الضريبي {0} لعدم تعيين حساب مرتبط للشركة {1} فيها.'`
   - `'Tax Amount will be rounded on a row(items) level'` -> `'سيتم تقريب مبلغ الضريبة على مستوى السطر (الأصناف)'`
   - `'Tax Withholding Category {} against Company {} for Customer {} should have Cumulative Threshold value.'` -> `'يجب أن تحتوي فئة الاستقطاع الضريبي {} مقابل الشركة {} للعميل {} على قيمة الحد التراكمي.'`
   - `'Tax will be withheld only for amount exceeding the cumulative threshold'` -> `'سيتم حجز الضريبة فقط للمبلغ الذي يتجاوز الحد التراكمي'`
   - Complies fully with ZATCA and SOCPA standard tax withholding regulations (الاستقطاع الضريبي والحد التراكمي).

8. **Financial Report Templates & Financial Statement Terminology:**
   - `'Text displayed on the financial statement (e.g., 'Total Revenue', 'Cash and Cash Equivalents')'` -> `'النص المعروض في القائمة المالية (مثال: 'إجمالي الإيرادات'، 'النقد وما في حكمه')'` (Direct IAS 7 / SOCPA terminology: إجمالي الإيرادات، النقد وما في حكمه).
   - `'Type of financial statement this template generates'` -> `'نوع القائمة المالية التي ينشئها هذا القالب'`
   - `'Show negative values as positive (for expenses in P&L)'` -> `'إظهار القيم السالبة كموجبة (للمصروفات في قائمة الأرباح والخسائر)'`
   - `'Return on Asset Ratio'` -> `'نسبة العائد على الأصول'` (ROA).
   - `'Return on Equity Ratio'` -> `'نسبة العائد على حقوق الملكية'` (ROE).
   - `'Solvency Ratios'` -> `'نسب الملاءة المالية'`
   - `'Short-term Investments'` -> `'استثمارات قصيرة الأجل'`
   - `'Short-term Provisions'` -> `'مخصصات قصيرة الأجل'`
   - `'Revaluation Surplus'` -> `'فائض إعادة التقييم'` (Standard IAS 16 property, plant, and equipment revaluation surplus).
   - `'Updated {0} Financial Report Row(s) with new category name'` -> `'تم تحديث {0} صف(صفوف) تقرير مالي بالاسم الجديد للفئة'`
   - `'Used with Financial Report Template'` -> `'يُستخدم مع قالب التقرير المالي'`

9. **Fixed Assets, Depreciation & Inventory Integration:**
   - `'Row #{0}: Asset {1} cannot be sold, it is already {2}'` -> `'السطر رقم {0}: لا يمكن بيع الأصل {1}، فهو بالفعل {2}'`
   - `'Row #{0}: Asset {1} is already sold'` -> `'السطر رقم {0}: الأصل {1} مُباع بالفعل'`
   - `'Row #{0}: Return Against is required for returning asset'` -> `'السطر رقم {0}: حقل الإرجاع مقابل مطلوب لإرجاع الأصل'`
   - `'Row #{0}: You must select an Asset for Item {1}.'` -> `'السطر رقم {0}: يجب تحديد أصل للصنف {1}.'`
   - `'This schedule was created when Asset {0} was restored due to Sales Invoice {1} cancellation.'` -> `'تم إنشاء هذا الجدول الزمني عند استعادة الأصل {0} نتيجة إلغاء فاتورة المبيعات {1}.'`
   - `'This schedule was created when Asset {0} was returned through Sales Invoice {1}.'` -> `'تم إنشاء هذا الجدول الزمني عند إرجاع الأصل {0} من خلال فاتورة المبيعات {1}.'`
   - `'This schedule was created when Asset {0} was {1} through Sales Invoice {2}.'` -> `'تم إنشاء هذا الجدول الزمني عندما كان الأصل {0} {1} من خلال فاتورة المبيعات {2}.'`
   - `'Users with this role will be notified if the asset depreciation gets failed'` -> `'سيتم إخطار المستخدمين بهذا الدور في حال فشل إهلاك الأصل'` (إهلاك الأصل).

10. **Budgeting & Cost Centers:**
    - `'Total distributed amount {0} must be equal to Budget Amount {1}'` -> `'يجب أن يكون إجمالي المبلغ الموزع {0} مساوياً لمبلغ الميزانية {1}'`
    - `'Total distribution percent must equal 100 (currently {0})'` -> `'يجب أن تكون نسبة التوزيع الإجمالية مساوية لـ 100 (حالياً {0})'`
    - `'Total percentage against cost centers should be 100'` -> `'يجب أن يكون إجمالي النسبة المئوية مقابل مراكز التكلفة 100'`

---

### 5. Review Verdict
- **Verdict:** **PASS**
- **Recommendation:** AI-A2 certifies that Stage 6 W6-1 Accounts Batch 04 proposal complies with all IFRS/SOCPA accounting principles, maintains exact placeholder and affix parity, preserves all 125 live site overrides unchanged, and correctly classifies `Rgt` as an untranslated technical exception. Ready for AI quorum consolidation.
