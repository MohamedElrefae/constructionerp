# Independent Linguistic Review Report: W6-1 Accounts Batch 01 (v16.localhost)
**Reviewer:** Subagent AI-A1 (Read-Only Linguistic Auditor)
**Target Cycle:** W6-1 Accounts Batch 01 (Owner-Approved scope on `v16.localhost`)
**Verdict:** **PASS**

---

### 1. Cryptographic Hash & Artifact Verification
The exact SHA-256 hashes and file metrics were verified against the scope files, reconciliation output, and proposal artifacts:

- **Scope CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch01_rows_2026-09-24.csv`
  - **Verified SHA-256:** `4910a9e4a0e5f8dd0105d484171ac1dc68e173220a0bed27520fbfc5e8c090fd`
  - **Row Count:** 250 rows (252 lines including CSV header and trailing newline)
  - **File Size:** 41,963 bytes
  - **Status:** **MATCH / VERIFIED**

- **Proposal CSV:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch01_proposal_2026-09-24.csv`
  - **Verified SHA-256:** `226ff8b158a4a17bca77209d2e452fff9eff75fd6479324f3e020e6b24ab2b4e`
  - **Row Count:** 250 rows (252 lines including CSV header and trailing newline)
  - **File Size:** 86,137 bytes
  - **Status:** **MATCH / VERIFIED**

- **Reconciliation JSON:** `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w601_accounts_batch01_site_recon_2026-09-24.json`
  - Scope reference SHA-256: `4910a9e4a0e5f8dd0105d484171ac1dc68e173220a0bed27520fbfc5e8c090fd`
  - Partition: 103 missing runtime keys + 147 site overrides = 250 total rows.
  - **Status:** **MATCH / VERIFIED**

---

### 2. Comprehensive Linguistic Evaluation of 103 Proposed Arabic Translations
All 103 candidate translations (`PROPOSED-payload`) were thoroughly reviewed across accounting domain conventions, grammar, syntax, morphology, readability, punctuation, and placeholder integrity:

1. **Accounting & Financial Terminological Accuracy:**
   - Standard accounting terms are accurately rendered according to accepted Middle Eastern and international Arabic accounting standards:
     - `Chart Of Accounts` -> `"دليل الحسابات"`
     - `Accrued Expenses` -> `"مصروفات مستحقة"`
     - `Cr` -> `"دائن"`
     - `Capital Equipment` -> `"معدات رأسمالية"`
     - `Auto write off precision loss while consolidation` -> `"الشطب التلقائي لفارق دقة التقريب أثناء الدمج"`
     - `Allow Implicit Pegged Currency Conversion` -> `"السماح بالتحويل الضمني للعملة المربوطة"`
     - `At least one account with exchange gain or loss is required` -> `"مطلوب حساب واحد على الأقل مع أرباح أو خسائر أسعار الصرف"`
     - `Apply Tax Withholding Amount ` -> `"تطبيق مبلغ ضريبة الخصم "`
     - `Closing [Opening + Total] ` -> `"الإغلاق [الافتتاحي + الإجمالي] "`

2. **Grammatical & Morphological Correctness (النحو والصرف):**
   - **Dual Concord:** Row 78: `"Company and Posting Date is mandatory"` -> `"الشركة وتاريخ الترحيل إلزاميان"` correctly employs the dual predicate (`إلزاميان`) agreeing with the compound subject.
   - **Feminine Concord:** Rows 76–77: `"Company is mandatory"` -> `"الشركة إلزامية"`; Row 81: `"Company {0} added multiple times"` -> `"تمت إضافة الشركة {0} عدة مرات"`.
   - **Accusative Predicate (خبر كان/تكون):** Row 58: `"Billing Interval in Subscription Plan must be Month to follow calendar months"` -> `"يجب أن تكون فترة الفوترة في خطة الاشتراك شهرا لاتباع الأشهر التقويمية"` (`شهرا` is correctly in the accusative case).
   - **Tanwin & Spelling:** Tanwin al-nasb (`حسابا آخر`, `شهرا`, `بدلا من ذلك`, `تلقائيا`, `حاليا`) and hamzat al-wasl/qat' (`استخدم`, `إضافة`, `إلغاء`, `إنشاء`) are applied accurately throughout.

3. **Syntax & Natural UI Flow (الأسلوب والوضوح):**
   - User action confirmation dialogues are natural and respectful:
     - `"Are you sure you want to restart this subscription?"` -> `"هل أنت متأكد من رغبتك في إعادة بدء هذا الاشتراك؟"`
     - `"Are you sure you want to revise this budget? The current budget will be cancelled and a new draft will be created."` -> `"هل أنت متأكد من رغبتك في تعديل هذه الميزانية؟ سيتم إلغاء الميزانية الحالية وإنشاء مسودة جديدة."`
   - Progress and async indicators use appropriate gerund forms:
     - `"Creating Purchase Invoices ..."` -> `"جار إنشاء فواتير الشراء ..."`
     - `"Creating Sales Invoices ..."` -> `"جار إنشاء فواتير المبيعات ..."`
   - Breadcrumb sequences preserve arrow indicators and logical hierarchy:
     - `"Customer > Customer Group > Territory"` -> `"العميل > مجموعة العملاء > المنطقة"`

4. **Multi-Placeholder Multiset Parity:**
   - 11 complex strings carry multiple placeholders (`{0}`, `{1}`, `{2}`, `{3}`, `{}`), e.g.:
     - `Bank Account {} in Bank Transaction {} is not matching with Bank Account {}` -> `الحساب البنكي {} في المعاملة البنكية {} لا يتطابق مع الحساب البنكي {}`
     - `Another Budget record '{0}' already exists against {1} '{2}' and account '{3}' with overlapping fiscal years.` -> `يوجد بالفعل سجل ميزانية آخر '{0}' مقابل {1} '{2}' والحساب '{3}' مع سنوات مالية متداخلة.`
   - All placeholders are strictly preserved, ordered, and formatted without corruption or transposition.

---

### 3. Whitespace Affix Parity Check
All edge-whitespace entries in the proposal were verified for exact leading and trailing whitespace parity:

- **Leading Spaces (3 entries):**
  1. `' Amount'` -> `' المبلغ'` (Exact: 1 leading space)
  2. `' Name'` -> `' الاسم'` (Exact: 1 leading space)
  3. `' Rate'` -> `' السعر'` (Exact: 1 leading space)

- **Trailing Spaces (7 entries):**
  1. `'All Parties '` -> `'كل الجهات '` (Exact: 1 trailing space)
  2. `'Customer '` -> `'العميل '` (Exact: 1 trailing space)
  3. `'Customer Name: '` -> `'اسم العميل: '` (Exact: 1 trailing space)
  4. `'Customer: '` -> `'العميل: '` (Exact: 1 trailing space)
  5. `'Closing [Opening + Total] '` -> `'الإغلاق [الافتتاحي + الإجمالي] '` (Exact: 1 trailing space)
  6. `'Allow multi-currency invoices against single party account '` -> `'السماح بفواتير متعددة العملات مقابل حساب جهة واحد '` (Exact: 1 trailing space)
  7. `'Apply Tax Withholding Amount '` -> `'تطبيق مبلغ ضريبة الخصم '` (Exact: 1 trailing space)

- **Result:** **10/10 strict parity (0 violations).**

---

### 4. Verification of 147 Preserved-Site-Override Entries
- Verified that all 147 entries marked with `preserved-site-override` in the proposal CSV match the test-site reconciliation JSON (`stage6_w601_accounts_batch01_site_recon_2026-09-24.json`) `site_overrides` list verbatim.
- Verified that each preserved override row carries:
  - `proposed_disposition`: `preserved-site-override`
  - `disposition_rationale`: `Preserve the exact live v16.localhost Site Override; do not import or replace.`
  - `decision_ref`: `stage6-W6-1 Accounts Batch 01 pending-owner-approval 2026-09-24`
- No live site overrides are overwritten, altered, or marked for replacement.

---

### 5. Formal Verdict
**FINAL VERDICT: PASS**
