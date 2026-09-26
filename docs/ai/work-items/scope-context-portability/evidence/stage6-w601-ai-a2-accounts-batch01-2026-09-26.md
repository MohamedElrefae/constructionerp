# Formal Review Verdict: PASS
**Role:** AI-A2 Independent Domain and Terminology Reviewer
**Scope:** Stage 6 — W6-1 Accounts Batch 01 (v16.localhost)
**Session:** Read-Only Review

---

### 1. Cryptographic Hash Verification
- **Scope CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch01_rows_2026-09-24.csv`
  - Expected SHA-256: `4910a9e4a0e5f8dd0105d484171ac1dc68e173220a0bed27520fbfc5e8c090fd`
  - Verified SHA-256: `4910a9e4a0e5f8dd0105d484171ac1dc68e173220a0bed27520fbfc5e8c090fd` (**MATCH**)
- **Proposal CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch01_proposal_2026-09-24.csv`
  - Expected SHA-256: `226ff8b158a4a17bca77209d2e452fff9eff75fd6479324f3e020e6b24ab2b4e`
  - Verified SHA-256: `226ff8b158a4a17bca77209d2e452fff9eff75fd6479324f3e020e6b24ab2b4e` (**MATCH**)
- **Row Total:** 250 rows in scope, exactly partitioned into 147 `preserved-site-override` and 103 `PROPOSED-payload` (0 technical exceptions).

---

### 2. Preservation of 147 Site Overrides
- Reconciled against `docs/translation/stage6_w601_accounts_batch01_site_recon_2026-09-24.json`.
- All 147 site overrides are assigned disposition `preserved-site-override` with rationale `"Preserve the exact live v16.localhost Site Override; do not import or replace."`.
- Zero alterations, overwrites, or regressions detected against live site translations.

---

### 3. Key Accounting Terminology Verification
The core accounting terms were verified verbatim against Arabic accounting standards and Glossary v2.0:
- `'Cr'` -> `'دائن'` (Verified)
- `'Accrued Expenses'` -> `'مصروفات مستحقة'` (Verified)
- `'Chart Of Accounts'` -> `'دليل الحسابات'` (Verified)
- `'Capital Equipment'` -> `'معدات رأسمالية'` (Verified)

---

### 4. Domain & Terminology Evaluation Across ERPNext Accounts Subsystems

The 103 proposed candidate translations were audited across all ERPNext Accounts functional domains against ERPNext architecture and Glossary v2.0:

1. **General Ledger & Chart of Accounts:**
   - Accurate standard terminology: `'Cannot Resubmit Ledger entries for vouchers in Closed fiscal year.'` -> `'لا يمكن إعادة إرسال قيود دفتر الأستاذ للسندات في سنة مالية مغلقة.'`, `'Cannot convert to Group because Account Type is selected.'` -> `'لا يمكن التحويل إلى مجموعة لأن نوع الحساب محدد.'`.
   - Clear multi-currency party handling: `'Allow multi-currency invoices against single party account '` -> `'السماح بفواتير متعددة العملات مقابل حساب جهة واحد '`.
   - Credit Note workflow: `'Credit Note will update it's own outstanding amount, even if 'Return Against' is specified.'` -> `'سيقوم إشعار الدائن بتحديث مبلغه المستحق، حتى لو تم تحديد 'مرتجع مقابل'.'`.
2. **Bank Reconciliation:**
   - Robust reconciliation phrasing: `'A Reconciliation Job {0} is running for the same filters. Cannot reconcile now'` -> `'هناك مهمة تسوية {0} قيد التشغيل لنفس عوامل التصفية. لا يمكن التسوية الآن'`.
   - Automated processing: `'Auto Reconciliation has started in the background'` -> `'بدأت التسوية التلقائية في الخلفية'`, `'Bank Transaction {0} is already fully reconciled'` -> `'المعاملة البنكية {0} تمت تسويتها بالكامل بالفعل'`, and bank/cash isolation `'حساب البنك/النقدية {0} لا يتبع الشركة {1}'`.
3. **Cost Center Allocations:**
   - Proper hierarchical and allocation constraints: `'Cost Center is a part of Cost Center Allocation, hence cannot be converted to a group'` -> `'مركز التكلفة جزء من تخصيص مركز التكلفة، وبالتالي لا يمكن تحويله إلى مجموعة'`.
   - Overlap validation: `'Another Cost Center Allocation record {0} applicable from {1}, hence this allocation will be applicable upto {2}'` -> `'سجل تخصيص مركز تكلفة آخر {0} ينطبق من {1}، وبالتالي سيكون هذا التخصيص ساريا حتى {2}'`.
4. **Subscriptions:**
   - Accurate recurring billing terminology: `'Are you sure you want to restart this subscription?'` -> `'هل أنت متأكد من رغبتك في إعادة بدء هذا الاشتراك؟'`, `'Billing Interval in Subscription Plan must be Month to follow calendar months'` -> `'يجب أن تكون فترة الفوترة في خطة الاشتراك شهرا لاتباع الأشهر التقويمية'`.
5. **Budgeting:**
   - Exact parity with budget checks: `'(Purchase Order + Material Request + Actual Expense)'` -> `'(أمر الشراء + طلب المواد + المصروف الفعلي)'`.
   - Cumulative variance controls: `'Action if Accumulative Monthly Budget Exceeded on Cumulative Expense'` -> `'الإجراء عند تجاوز الميزانية الشهرية التراكمية للمصروف التراكمي'`.
6. **POS Invoices:**
   - Consistent point-of-sale terms: `'Cannot cancel POS Closing Entry'` -> `'لا يمكن إلغاء قيد إغلاق نقطة البيع'`, `'Create Payment Entry for Consolidated POS Invoices.'` -> `'إنشاء قيد دفع لفواتير نقاط البيع المجمعة.'`, `'Company {} does not match with POS Profile Company {}'` -> `'الشركة {} لا تتطابق مع شركة ملف تعريف نقطة البيع {}'`.
7. **Tax Withholding & Taxes:**
   - Appropriate regional tax vocabulary: `'Apply Tax Withholding Amount '` -> `'تطبيق مبلغ ضريبة الخصم '` (reflecting Egyptian/regional withholding tax terminology), `'A template with tax category {0} already exists. Only one template is allowed with each tax category'` -> `'يوجد بالفعل قالب بالفئة الضريبية {0}. يُسمح بقالب واحد فقط لكل فئة ضريبية'`.
8. **Currency Exchange:**
   - Accurate financial exchange mechanics: `'Allow Implicit Pegged Currency Conversion'` -> `'السماح بالتحويل الضمني للعملة المربوطة'`, `'At least one account with exchange gain or loss is required'` -> `'مطلوب حساب واحد على الأقل مع أرباح أو خسائر أسعار الصرف'`, `'Auto write off precision loss while consolidation'` -> `'الشطب التلقائي لفارق دقة التقريب أثناء الدمج'`.
9. **Financial Statements & Custom Reports:**
   - Accurate reporting terms: `'At least one row is required for a financial report template'` -> `'مطلوب صف واحد على الأقل لقالب التقرير المالي'`, `'Closing [Opening + Total] '` -> `'الإغلاق [الافتتاحي + الإجمالي] '`, `'Bold text for emphasis (totals, major headings)'` -> `'نص عريض للتأكيد (الإجماليات، العناوين الرئيسية)'`.
10. **Subcontracting Integration:**
    - Correct Egyptian and ERPNext convention: `'All items must be linked to a Sales Order or Subcontracting Inward Order for this Sales Invoice.'` -> `'يجب ربط جميع الأصناف بأمر بيع أو أمر توريد من الباطن لفاتورة المبيعات هذه.'` (utilizing `'من الباطن'`).

---

### 5. Governance, Format & Affix Integrity
- **Whitespace Parity:** 3 leading space strings (`' Amount'`, `' Name'`, `' Rate'`) and 7 trailing space strings (`'All Parties '`, `'Customer '`, `'Customer Name: '`, `'Customer: '`, `'Closing [Opening + Total] '`, `'Allow multi-currency invoices against single party account '`, `'Apply Tax Withholding Amount '`) have 100% affix parity.
- **Placeholders:** All multi-placeholder strings (`{0}`, `{1}`, `{2}`, `{}`) maintain strict multiset count and format parity.
- **Cleanliness:** No newlines, no blank proposed payloads, no source-equal strings.

---

### Formal Verdict
**PASS** — The proposal package strictly satisfies all domain, accounting, and terminology requirements under ERPNext Accounts and Glossary v2.0, preserves the 147 site overrides intact, and is approved from the AI-A2 domain perspective.
