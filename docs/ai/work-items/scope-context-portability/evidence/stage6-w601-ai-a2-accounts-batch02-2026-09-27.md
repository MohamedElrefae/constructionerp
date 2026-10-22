# Formal Review Verdict: PASS
**Role:** AI-A2 Independent Domain and Terminology Reviewer
**Scope:** Stage 6 — W6-1 Accounts Batch 02 (v16.localhost)
**Mode:** Strictly Read-Only Domain Evaluation
**Report Destination:** `/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a2-accounts-batch02-2026-09-27.md`

---

### 1. Cryptographic Hash & Batch Partition Verification
- **Scope CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch02_rows_2026-09-24.csv`
  - Expected SHA-256: `dc9b6c022c01a5cfcad5c6934c58a3ba74cc091f17676b607d50a96ab0d60e4e`
  - Verified SHA-256: `dc9b6c022c01a5cfcad5c6934c58a3ba74cc091f17676b607d50a96ab0d60e4e` (**MATCH**)
- **Proposal CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch02_proposal_2026-09-26.csv`
  - Expected SHA-256: `e0fac4c67787aba3c5ac50b52a9f21625360da0693f7b17e77dbf7a315e7567e`
  - Verified SHA-256: `e0fac4c67787aba3c5ac50b52a9f21625360da0693f7b17e77dbf7a315e7567e` (**MATCH**)
- **Site Recon JSON:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch02_site_recon_2026-09-26.json`
- **Total Rows in Scope:** 250 rows, partitioned strictly into:
  - `preserved-site-override`: 160 rows
  - `PROPOSED-payload`: 89 rows
  - `EXCEPTION-technical`: 1 row (`Lft`)
  - Total: 160 + 89 + 1 = 250 rows.

---

### 2. Preservation of 160 Site Overrides
- Reconciled against `stage6_w601_accounts_batch02_site_recon_2026-09-26.json` from `v16.localhost`.
- All 160 site overrides are assigned disposition `preserved-site-override` with rationale `"Preserve the exact live v16.localhost Site Override; do not import or replace."`.
- Key live accounting overrides verified preserved verbatim include:
  - `'Debit Amount in Reporting Currency'` -> `'مبلغ المدين بعملة التقارير'`
  - `'Debit Amount in Transaction Currency'` -> `'مبلغ المدين بعملة المعاملة'`
  - `'Debt Equity Ratio'` -> `'نسبة الدين إلى حقوق الملكية'`
  - `'Debtor Turnover Ratio'` -> `'معدل دوران المدينين'`
  - `'Default Account'` -> `'الحساب الافتراضي'`
  - `'Default Advance Account'` -> `'حساب الدفعة المقدمة الافتراضي'`
  - `'Deferred Expense Account'` -> `'حساب المصروف المؤجل'`
  - `'Deferred Revenue and Expense'` -> `'الإيرادات والمصروفات المؤجلة'`
  - `'Delete Accounting and Stock Ledger Entries on deletion of Transaction'` -> `'حذف قيود المحاسبة والمخزون عند حذف المعاملة'`
  - `'Dimension-wise Accounts Balance Report'` -> `'تقرير رصيد الحسابات حسب البُعد'`
  - `'Direct Expense'` -> `'مصروف مباشر'`
  - `'Disable Rounded Total'` -> `'تعطيل الإجمالي المقرب'`
  - `'Ledger Health'` -> `'صحة دفتر الأستاذ'`
  - `'Ledger Merge'` -> `'دمج دفتر الأستاذ'`
  - `'Liquidity Ratios'` -> `'نسب السيولة'`
- Zero alterations, regressions, or overwrites against existing live site overrides.

---

### 3. Classification of Technical Candidate ('Lft')
- **Source Text:** `Lft`
- **Location:** `erpnext/accounts/doctype/account/account.json:None; erpnext/setup/doctype/company/company.json:None`
- **Classification:** `EXCEPTION-technical`
- **Rationale:** `"Internal NestedSet tree column name (lft); preserved untranslated."`
- **Domain Audit:** Frappe uses modified preorder tree traversal (`NestedSet`) where `lft` and `rgt` represent internal tree traversal bounds. In DocType `Account` and `Company`, `Lft` is a core internal structural column. Leaving it untranslated prevents schema corruption and maintains architectural integrity. The classification as `EXCEPTION-technical` is accurate and verified.

---

### 4. Domain & Terminology Evaluation Across ERPNext Accounts Subsystems

The 89 proposed candidate translations were audited across all ERPNext Accounts functional domains against ERPNext architecture, IFRS / standard accounting principles, and the ERP Arabic Glossary:

1. **General Ledger, Accounting Settings & Ledger Health:**
   - `'Debit Note will update it's own outstanding amount, even if 'Return Against' is specified.'` -> `'سيقوم إشعار المدين بتحديث المبلغ المستحق الخاص به، حتى في حال تحديد 'مرتجع مقابل'.'` (Accurate terminology for Debit Note: إشعار مدين, outstanding amount: المبلغ المستحق, return against: مرتجع مقابل).
   - `'Debit-Credit Mismatch'` / `'Debit-Credit mismatch'` -> `'عدم تطابق بين المدين والدائن'` (Standard GL balance validation).
   - `'Debtor/Creditor'` -> `'مدين/دائن'` and `'Debtor/Creditor Advance'` -> `'دفعة مقدمة لمدين/دائن'` (Standard balance sheet party / advance concepts).
   - `'Discrepancy between General and Payment Ledger'` -> `'تضارب بين دفتر الأستاذ العام ودفتر أستاذ المدفوعات'` (Accurate distinction between General Ledger and Payment Ledger).
   - `'Do you still want to enable immutable ledger?'` -> `'هل ما زلت ترغب في تفعيل دفتر الأستاذ غير القابل للتعديل؟'` (Precise terminology for immutable ledger architecture).
   - `'Document Type already used as a dimension'` -> `'نوع المستند مستخدم بالفعل كبُعد'` (Accounting dimension terminology).
   - `'Heads (or groups) against which Accounting Entries are made and balances are maintained.'` -> `'الحسابات الرئيسية (أو المجموعات) التي يتم إنشاء القيود المحاسبية مقابلها والاحتفاظ بأرصدتها.'`
   - `'Individual GL Entry cannot be cancelled.'` -> `'لا يمكن إلغاء قيد دفتر أستاذ عام فردي.'`
   - `'Invalid amount in accounting entries of {} {} for Account {}: {}'` -> `'مبلغ غير صالح في القيود المحاسبية لـ {} {} للحساب {}: {}'`
   - `'Import Chart of Accounts from a csv file'` -> `'استيراد شجرة الحسابات من ملف csv'`
   - `'From Fiscal Year cannot be greater than To Fiscal Year'` -> `'السنة المالية 'من' لا يمكن أن تكون أكبر من السنة المالية 'إلى''`
   - `'Enabling this will allow creation of multi-currency invoices against single party account in company currency'` -> `'تفعيل هذا الخيار سيسمح بإنشاء فواتير متعددة العملات مقابل حساب طرف واحد بعملة الشركة'`
   - `'Drops existing SQL Procedures and Function setup by Accounts Receivable report'` -> `'حذف الإجراءات والدوال المخزنة الحالية في SQL الخاصة بتقرير الذمم المدينة'` (Accurate translation of Accounts Receivable as الذمم المدينة).

2. **Currency Exchange & Foreign Currency Operations:**
   - `'Gain/Loss accumulated in foreign currency account. Accounts with '0' balance in either Base or Account currency'` -> `'الأرباح/الخسائر المتراكمة في حساب العملة الأجنبية. الحسابات ذات الرصيد '0' إما بالعملة الأساسية أو بعملة الحساب'` (Precise accounting distinction between Base Currency: العملة الأساسية, Account Currency: عملة الحساب, and Exchange Gain/Loss: الأرباح/الخسائر المتراكمة).

3. **Banking Statements, MT940, & Bank Guarantees:**
   - `'Enter the Bank Guarantee Number before submitting.'` -> `'أدخل رقم خطاب الضمان البنكي قبل الإرسال.'` (Standard Arab banking terminology: خطاب الضمان البنكي).
   - `'Enter the name of the Beneficiary before submitting.'` -> `'أدخل اسم المستفيد قبل الإرسال.'` (Beneficiary: المستفيد).
   - `'Enter the name of the bank or lending institution before submitting.'` -> `'أدخل اسم البنك أو مؤسسة الإقراض قبل الإرسال.'`
   - `'Failed to parse MT940 format. Error: {0}'` -> `'فشل تحليل تنسيق MT940. الخطأ: {0}'` and `'Import MT940 Fromat'` -> `'استيراد بتنسيق MT940'` (SWIFT MT940 electronic bank statement format).
   - `'Error in party matching for Bank Transaction {0}'` -> `'خطأ في مطابقة الطرف للمعاملة البنكية {0}'`
   - `'Included fee is bigger than the withdrawal itself.'` -> `'الرسوم المشمولة أكبر من مبلغ السحب نفسه.'` (Withdrawal: السحب).
   - `'Interest on Fixed Deposits'` -> `'فوائد الودائع لأجل'` (Standard banking term for fixed-term deposits: الودائع لأجل).
   - `'Invoices and Payments have been Fetched and Allocated'` -> `'تم جلب الفواتير والمدفوعات وتخصيصها'` (Payment reconciliation tool workflow).

4. **Pricing Rules & Discounts:**
   - `'Discount (%) on Price List Rate with Margin'` -> `'نسبة الخصم (%) على سعر قائمة الأسعار مع هامش الربح'`
   - `'Discount Percentage can be applied either against a Price List or for all Price List.'` -> `'يمكن تطبيق نسبة الخصم إما على قائمة أسعار محددة أو على جميع قوائم الأسعار.'`
   - `'Discount on Price List Rate (%)'` -> `'الخصم على سعر قائمة الأسعار (%)'`
   - `'Discounts to be applied in sequential ranges like buy 1 get 1, buy 2 get 2, buy 3 get 3 and so on'` -> `'خصومات تُطبق في نطاقات متسلسلة مثل اشترِ 1 واحصل على 1، اشترِ 2 واحصل على 2، اشترِ 3 واحصل على 3 وهكذا'`
   - `'Even if there are multiple Pricing Rules with highest priority, then following internal priorities are applied:'` -> `'حتى لو وُجدت قواعد تسعير متعددة بأعلى أولوية، يتم تطبيق الأولويات الداخلية التالية:'`
   - `'How Pricing Rule is applied?'` -> `'كيف يتم تطبيق قاعدة التسعير؟'`
   - `'If multiple Pricing Rules continue to prevail, users are asked to set Priority manually to resolve conflict.'` -> `'إذا استمر تعارض قواعد تسعير متعددة، يُطلب من المستخدمين تحديد الأولوية يدوياً لحل التعارض.'`
   - `'Free Item Rate'` -> `'سعر الصنف المجاني'` and `'If rate is zero then item will be treated as "Free Item"'` -> `'إذا كان السعر صفراً، فسيُعامل الصنف على أنه "صنف مجاني"'`
   - `'Don't Enforce Free Item Qty'` -> `'عدم إلزام كمية الصنف المجاني'`
   - `'Item Code > Item Group > Brand'` -> `'كود الصنف > مجموعة الأصناف > العلامة التجارية'`

5. **Dunning & Subscriptions:**
   - `'For dunning fee and interest'` -> `'لرسوم التذكير بالدفع والفائدة'` (Dunning fee: رسوم التذكير بالدفع / المطالبة, Interest: الفائدة).
   - `'Force-Fetch Subscription Updates'` -> `'فرض جلب تحديثات الاشتراك'`

6. **Loyalty Programs:**
   - `'Don't Create Loyalty Points'` -> `'عدم إنشاء نقاط ولاء'`
   - `'If Auto Opt In is checked, then the customers will be automatically linked with the concerned Loyalty Program (on save)'` -> `'إذا تم تحديد الانضمام التلقائي، فسيتم ربط العملاء تلقائياً ببرنامج الولاء المعني (عند الحفظ)'`
   - `'If unlimited expiry for the Loyalty Points, keep the Expiry Duration empty or 0.'` -> `'إذا كانت نقاط الولاء غير محددة الصلاحية، اترك مدة انتهاء الصلاحية فارغة أو 0.'`
   - `'In the case of multi-tier program, Customers will be auto assigned to the concerned tier as per their spent'` -> `'في حالة البرامج متعددة المستويات، سيتم تعيين العملاء تلقائياً للمستوى المعني وفقاً لحجم إنفاقهم'`

7. **Financial Report Templates & Financial Presentation:**
   - `'Descriptive name for your template (e.g., 'Standard P&L', 'Detailed Balance Sheet')'` -> `'اسم وصفي لنموذجك (مثال: 'قائمة الأرباح والخسائر القياسية'، 'الميزانية العمومية التفصيلية')'` (Standard P&L: قائمة الأرباح والخسائر القياسية, Detailed Balance Sheet: الميزانية العمومية التفصيلية).
   - `'Disable template to prevent use in reports'` -> `'تعطيل النموذج لمنع استخدامه في التقارير'`
   - `'Financial Report Template {0} is disabled'` -> `'نموذج التقرير المالي {0} معطل'`
   - `'Financial Report Template {0} not found'` -> `'لم يتم العثور على نموذج التقرير المالي {0}'`
   - `'Hide this line if amount is zero'` -> `'إخفاء هذا السطر إذا كان المبلغ صفراً'`
   - `'How this line gets its data'` -> `'كيف يحصل هذا السطر على بياناته'`
   - `'How to format and present values in the financial report (only if different from column fieldtype)'` -> `'كيفية تنسيق وعرض القيم في التقرير المالي (فقط إذا كانت مختلفة عن نوع حقل العمود)'`
   - `'If enabled, this row's values will be displayed on financial charts'` -> `'إذا تم التفعيل، فستُعرض قيم هذا السطر في المخططات البيانية المالية'`
   - `'Indentation level: 0 = Main heading, 1 = Sub-category, 2 = Individual accounts, etc.'` -> `'مستوى الإزاحة: 0 = العنوان الرئيسي، 1 = الفئة الفرعية، 2 = الحسابات الفردية، إلخ.'`
   - `'Italic Text'` -> `'نص مائل'` and `'Italic text for subtotals or notes'` -> `'نص مائل للمجاميع الفرعية أو الملاحظات'`
   - `'Ignore Is Opening check for reporting'` -> `'تجاهل علامة 'رصيد افتتاحي' لإعداد التقارير'`
   - `'Ignore Voucher Type filter and Select Vouchers Manually'` -> `'تجاهل تصفية نوع السند وتحديد السندات يدوياً'`
   - `'Include Default FB Assets'` -> `'تضمين أصول دفتر المالية الافتراضي'` (Finance Book Assets: أصول دفتر المالية).
   - `'Include Returned Invoices (Stand-alone)'` -> `'تضمين فواتير المرتجعات (المستقلة)'`

8. **Fixed Assets, Depreciation & Impairment:**
   - `'Depreciation eliminated via reversal'` -> `'تم استبعاد الإهلاك عبر القيد العكسي'` (Asset retirement / reversal terminology).
   - `'Impairment'` -> `'اضمحلال القيمة'` (Complies with IAS 36 Impairment of Assets standard Arabic terminology).

9. **Deferred Accounting (Revenue & Expenses):**
   - `'Deferred accounting failed for some invoices:'` -> `'فشلت المحاسبة المؤجلة لبعض الفواتير:'`
   - `'Documents: {0} have deferred revenue/expense enabled for them. Cannot repost.'` -> `'المستندات: {0} مفعل لها الإيراد/المصروف المؤجل. لا يمكن إعادة الترحيل.'`
   - `'Error while processing deferred accounting for {0}'` -> `'خطأ أثناء معالجة المحاسبة المؤجلة لـ {0}'`

10. **POS, Taxes, & Invoicing:**
    - `'If enabled, ledger entries will be posted for change amount in POS transactions'` -> `'إذا تم التفعيل، فسيتم ترحيل قيود دفتر الأستاذ لمبلغ الباقي في معاملات نقطة البيع'`
    - `'If enabled, the consolidated invoices will have rounded total disabled'` -> `'إذا تم التفعيل، فسيتم تعطيل تقريب الإجمالي في الفواتير المجمعة'`
    - `'If checked, the tax amount will be considered as already included in the Paid Amount in Payment Entry'` -> `'إذا تم التحديد، فسيُعتبر مبلغ الضريبة مشمولاً بالفعل في المبلغ المدفوع في سند الصرف/القبض'` (Payment Entry: سند الصرف/القبض).
    - `'If enabled, user will be alerted before resetting posting date to current date in relevant transactions'` -> `'إذا تم التفعيل، فسيتم تنبيه المستخدم قبل إعادة ضبط تاريخ الترحيل إلى التاريخ الحالي في المعاملات ذات الصلة'`
    - `'Generate E-Invoice'` -> `'إنشاء فاتورة إلكترونية'`
    - `'Issue a debit note with 0 qty against an existing Sales Invoice'` -> `'إصدار إشعار مدين بكمية 0 مقابل فاتورة مبيعات موجودة'`

11. **Budgeting & Distribution:**
    - `'Distribute Equally'` -> `'توزيع بالتساوي'`
    - `'Helps you distribute the Budget/Target across months if you have seasonality in your business.'` -> `'يساعدك على توزيع الميزانية/المستهدف عبر الأشهر إذا كانت أعمالك تتسم بالموسمية.'`

---

### 5. Placeholder and Quality Invariant Checks
- Multi-placeholder strings (`{0}`, `{1}`, `{}`) maintain 100% multiset parity with source strings.
- 0 leading or trailing whitespace mismatches across all candidate rows.
- 0 newlines, carriage returns, or control characters.
- 0 source-equal (untranslated) payload rows.
- 0 empty translations in proposed payload.

---

### Formal Verdict
**PASS** — The proposal package for W6-1 Accounts Batch 02 strictly satisfies all domain, accounting, and terminology requirements under ERPNext Accounts and the ERP Arabic glossary, preserves the 160 Site Overrides intact, correctly classifies `Lft` as an `EXCEPTION-technical`, and is approved from the AI-A2 domain perspective.
