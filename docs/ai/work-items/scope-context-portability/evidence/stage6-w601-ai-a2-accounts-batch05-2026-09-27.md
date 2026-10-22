# Formal Review Verdict: PASS
**Role:** AI-A2 Independent Domain and Terminology Reviewer
**Scope:** Stage 6 — W6-1 Accounts Batch 05 (Final 56 rows of W6-1 Accounts domain)
**Mode:** Strictly Read-Only Domain Evaluation
**Report Destination:** `/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/scope-context-portability/evidence/stage6-w601-ai-a2-accounts-batch05-2026-09-27.md`

---

### 1. Cryptographic Hash & Batch Partition Verification
- **Scope CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch05_rows_2026-09-27.csv`
  - Expected SHA-256: `10c2f94face1a476350e386dd0d176045a13fc8b800f3fb90cd5806cf41353c7`
  - Verified SHA-256: `10c2f94face1a476350e386dd0d176045a13fc8b800f3fb90cd5806cf41353c7` (**MATCH**)
- **Proposal CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch05_proposal_2026-09-27.csv`
  - Expected SHA-256: `74fedcf4313d4dff102755cc054cd1cfc3d28ce45705a6e686a9380f47c51c70`
  - Verified SHA-256: `74fedcf4313d4dff102755cc054cd1cfc3d28ce45705a6e686a9380f47c51c70` (**MATCH**)
- **Site Recon JSON:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch05_site_recon_2026-09-27.json`
- **Total Rows in Scope:** 56 rows (concluding the entire W6-1 Accounts domain), partitioned strictly into:
  - `preserved-site-override`: 14 rows
  - `EXCEPTION-technical`: 2 rows (`exchangerate.host`, `frankfurter.dev`)
  - `PROPOSED-payload`: 40 rows
  - Total: 14 + 2 + 40 = 56 rows.

---

### 2. Preservation of 14 Site Overrides
- Reconciled against `stage6_w601_accounts_batch05_site_recon_2026-09-27.json` from `v16.localhost`.
- All 14 site overrides are assigned disposition `preserved-site-override` with rationale `"Preserve the exact live v16.localhost Site Override; do not import or replace."`.
- Live accounting overrides verified preserved verbatim:
  1. `'Value Type'` -> `'نوع القيمة'` (`erpnext/accounts/doctype/financial_report_row/financial_report_row.json`)
  2. `'Value of New Capitalized Asset'` -> `'قيمة الأصل المرسمَل الجديد'` (`erpnext/accounts/report/asset_depreciations_and_balances/asset_depreciations_and_balances.py`)
  3. `'Value of New Purchase'` -> `'قيمة الشراء الجديد'` (`erpnext/accounts/report/asset_depreciations_and_balances/asset_depreciations_and_balances.py`)
  4. `'Value of Scrapped Asset'` -> `'قيمة الأصل المخرد'` (`erpnext/accounts/report/asset_depreciations_and_balances/asset_depreciations_and_balances.py`)
  5. `'Value of Sold Asset'` -> `'قيمة الأصل المباع'` (`erpnext/accounts/report/asset_depreciations_and_balances/asset_depreciations_and_balances.py`)
  6. `'View Account Coverage'` -> `'عرض تغطية الحساب'` (`erpnext/accounts/doctype/financial_report_template/financial_report_template.js`)
  7. `'Voucher Name'` -> `'اسم السند'` (`erpnext/accounts/doctype/tax_withheld_vouchers/tax_withheld_vouchers.json`)
  8. `'Voucher-wise Balance'` -> `'الرصيد حسب السند'` (`erpnext/accounts/report/voucher_wise_balance/voucher_wise_balance.json`)
  9. `'WIP Composite Asset'` -> `'أصل مركب تحت التشغيل'` (`erpnext/accounts/doctype/purchase_invoice_item/purchase_invoice_item.json`)
  10. `'Waiting for payment...'` -> `'بانتظار الدفع...'` (`erpnext/accounts/doctype/pos_invoice/pos_invoice.js`)
  11. `'Warnings'` -> `'تحذيرات'` (`erpnext/accounts/doctype/financial_report_template/financial_report_validation.py`)
  12. `'Withdrawal'` -> `'سحب'` (`erpnext/accounts/doctype/bank_transaction/bank_transaction.json`)
  13. `'Write Off Limit'` -> `'حد الشطب'` (`erpnext/accounts/doctype/pos_profile/pos_profile.json`)
  14. `'Zero Balance'` -> `'رصيد صفري'` (`erpnext/accounts/doctype/exchange_rate_revaluation_account/exchange_rate_revaluation_account.json`)
- Zero alterations, regressions, or overwrites against existing live site overrides.

---

### 3. Classification of Technical Candidates ('exchangerate.host', 'frankfurter.dev')
- **Candidates:**
  1. `exchangerate.host`
  2. `frankfurter.dev`
- **Location:** `erpnext/accounts/doctype/currency_exchange_settings/currency_exchange_settings.json:None`
- **Classification:** `EXCEPTION-technical`
- **Rationale:** `"Keep vendor code/symbol/markup content untouched — external service domain name / API hostname, technical exception"`
- **Domain Audit:** Direct inspection confirms that in ERPNext Currency Exchange Settings, `exchangerate.host` and `frankfurter.dev` are external third-party API service hostnames / internet domain names used for automated currency conversion rates. Translating, transliterating, or localizing these hostnames into Arabic would corrupt service identification and degrade software usability. Leaving them untranslated under `EXCEPTION-technical` is accurate, standard-compliant, and fully verified.

---

### 4. Domain & Terminology Evaluation Across ERPNext Accounts Subsystems

The 40 proposed candidate translations were audited across all functional accounting domains against ERPNext Accounts architecture, standard accounting principles (IFRS / SOCPA), and the ERP Arabic Glossary:

1. **Budgets & Managerial Cost Accounting:**
   - `'variance'` -> `'انحراف'` (Standard managerial accounting and budgeting term for variances from budget under IFRS/SOCPA).
   - `'{0} Budget for Account {1} against {2} {3} is {4}. It is already exceeded by {5}.'` -> `'ميزانية {0} للحساب {1} مقابل {2} {3} هي {4}. لقد تم تجاوزها بالفعل بمقدار {5}.'` (All 6 placeholders preserved in precise semantic positions; accurate budget overrun terminology).
   - `'{0} Budget for Account {1} against {2} {3} is {4}. It will be exceeded by {5}.'` -> `'ميزانية {0} للحساب {1} مقابل {2} {3} هي {4}. سيتم تجاوزها بمقدار {5}.'` (Exact prospective overrun phrasing).

2. **Cost Centers & Allocation Hierarchies:**
   - `'{0} cannot be used as a Main Cost Center because it has been used as child in Cost Center Allocation {1}'` -> `'لا يمكن استخدام {0} كمركز تكلفة رئيسي لأنه مستخدم كفرعي في توزيع مركز التكلفة {1}'` (Main Cost Center: مركز تكلفة رئيسي, child: فرعي, Cost Center Allocation: توزيع مركز التكلفة).
   - `'{0} {1}: Cost Center is required for 'Profit and Loss' account {2}.'` -> `'{0} {1}: مركز التكلفة مطلوب لحساب 'الأرباح والخسائر' {2}.'` (Mandatory cost center assignment for P&L income/expense accounts).
   - `'{0} {1}: Cost Center {2} is a group cost center and group cost centers cannot be used in transactions'` -> `'{0} {1}: مركز التكلفة {2} هو مركز تكلفة رئيسي ولا يمكن استخدام مراكز التكلفة الرئيسية في المعاملات'` (Group cost centers cannot accept transactional postings).
   - `'Warning!'` -> `'تحذير!'` (Punctuation and affix parity maintained).

3. **Chart of Accounts Hierarchy & Corporate Structure:**
   - `'{0} {1}: Account {2} is a Group Account and group accounts cannot be used in transactions'` -> `'{0} {1}: الحساب {2} هو حساب رئيسي ولا يمكن استخدام الحسابات الرئيسية في المعاملات'` (Fundamental accounting rule: group/parent accounts are consolidation nodes and cannot accept direct transactional GL entries).
   - `'Wrong Company'` -> `'شركة غير صحيحة'`
   - `'Wrong Template'` -> `'قالب غير صحيح'`
   - `'{} is a child company.'` -> `'{} هي شركة تابعة.'` (Subsidiary/child company terminology in consolidated accounting under IFRS 10).
   - `'{} {} is already linked with another {}'` -> `'{} {} مرتبط بالفعل بـ {} آخر'`
   - `'{} {} is already linked with {} {}'` -> `'{} {} مرتبط بالفعل بـ {} {}'`

4. **Financial Reporting & Asset Valuation:**
   - `'Value as on'` -> `'القيمة كما في'` (Standard balance sheet / asset report valuation phrasing: as on date).
   - `'{0} view is currently unsupported in Custom Financial Report.'` -> `'عرض {0} غير مدعوم حالياً في التقرير المالي المخصص.'`

5. **Point of Sale (POS) Lifecycle:**
   - `'You can add the original invoice {} manually to proceed.'` -> `'يمكنك إضافة الفاتورة الأصلية {} يدوياً للمتابعة.'`
   - `'You need to cancel POS Closing Entry {} to be able to cancel this document.'` -> `'يجب إلغاء قيد إقفال نقطة البيع {} لتتمكن من إلغاء هذا المستند.'` (POS Closing Entry: قيد إقفال نقطة البيع).
   - `'{0} cannot be changed with opened Opening Entries.'` -> `'لا يمكن تغيير {0} مع وجود قيود افتتاحية مفتوحة.'` (Opening Entries: قيود افتتاحية).
   - `'{0} is added multiple times on rows: {1}'` -> `'تمت إضافة {0} عدة مرات في الصفوف: {1}'`
   - `'{0} is open. Close the POS or cancel the existing POS Opening Entry to create a new POS Opening Entry.'` -> `'{0} مفتوح. أغلق نقطة البيع أو ألغِ قيد افتتاح نقطة البيع الحالي لإنشاء قيد افتتاح جديد.'` (POS Opening Entry: قيد افتتاح نقطة البيع).

6. **Period Closing & Accounting Periods:**
   - `'You cannot create a {0} within the closed Accounting Period {1}'` -> `'لا يمكنك إنشاء {0} ضمن الفترة المحاسبية المغلقة {1}'` (Accounting Period: الفترة المحاسبية).
   - `'You cannot {0} this document because another Period Closing Entry {1} exists after {2}'` -> `'لا يمكنك {0} هذا المستند نظراً لوجود قيد إقفال فترة آخر {1} بعد {2}'` (Period Closing Entry: قيد إقفال فترة).

7. **Bank Reconciliation & Banking Transactions:**
   - `'Voucher {0} is over-allocated by {1}'` -> `'السند {0} مخصص بشكل زائد بمقدار {1}'`
   - `'{0} Transaction(s) Reconciled'` -> `'تمت تسوية {0} معاملة'` (Natural Arabic pluralization and syntax for reconciliation count).
   - `'{0} {1} Partially Reconciled'` -> `'{0} {1} تمت تسويته جزئياً'`
   - `'{0} {1} is allocated twice in this Bank Transaction'` -> `'{0} {1} مخصص مرتين في هذه المعاملة البنكية'`
   - `'{} {} is not affecting bank account {}'` -> `'{} {} لا يؤثر على الحساب البنكي {}'`

8. **Payment Ledger, Payment Terms & Ledger Reposting:**
   - `'{0} account is not of company {1}'` -> `'الحساب {0} لا يتبع الشركة {1}'`
   - `'{0} account is not of type {1}'` -> `'الحساب {0} ليس من النوع {1}'`
   - `'{0} cannot be zero'` -> `'لا يمكن أن يكون {0} صفراً'`
   - `'{0} has been modified after you pulled it. Please pull it again.'` -> `'تم تعديل {0} بعد سحبه. يرجى سحبه مرة أخرى.'`
   - `'{0} will be given as discount.'` -> `'سيتم منح {0} كخصم.'`
   - `'{0}% of total invoice value will be given as discount.'` -> `'سيتم منح {0}% من إجمالي قيمة الفاتورة كخصم.'`
   - `'{0} {1} not allowed to be reposted. Modify {2} to enable reposting.'` -> `'غير مسموح بإعادة ترحيل {0} {1}. عدّل {2} لتمكين إعادة الترحيل.'`
   - `'{0} {1} is not in any active Fiscal Year'` -> `'{0} {1} ليس في أي سنة مالية نشطة'`

9. **Loyalty Points, Sales Invoices & Return Invoices:**
   - `'You can't redeem Loyalty Points having more value than the Total Amount.'` -> `'لا يمكنك استبدال نقاط ولاء ذات قيمة أكبر من المبلغ الإجمالي.'` (Redeem Loyalty Points: استبدال نقاط ولاء, Total Amount: المبلغ الإجمالي).
   - `'to unallocate the amount of this Return Invoice before cancelling it.'` -> `'لإلغاء تخصيص مبلغ فاتورة المرتجع هذه قبل إلغائها.'` (Return Invoice: فاتورة المرتجع, unallocate: إلغاء تخصيص).
   - `'dated {0}'` -> `'بتاريخ {0}'`
   - `'subscription is already cancelled.'` -> `'الاشتراك ملغى بالفعل.'`
   - `'You cannot enable both the settings '{0}' and '{1}'.'` -> `'لا يمكنك تفعيل كلا الإعدادين '{0}' و '{1}'.'`

---

### 5. Review Verdict
- **Verdict:** **PASS**
- **Recommendation:** AI-A2 certifies that Stage 6 W6-1 Accounts Batch 05 proposal strictly satisfies all domain requirements:
  1. Full compliance with standard IFRS/SOCPA accounting principles and ERP Arabic terminology.
  2. Complete preservation of all 14 live site overrides with zero alterations or regressions.
  3. Proper classification of the 2 API hostnames (`exchangerate.host`, `frankfurter.dev`) as untranslated `EXCEPTION-technical`.
  4. Precise placeholder, quote, and punctuation parity across all 40 proposed payloads.
  The proposal successfully completes the final batch of W6-1 Accounts and is ready for quorum consolidation and release.
