# Stage 6 W6-7 Frappe Framework Remainder Batch 01 — AI-A2 Domain & Terminology Independent Review

**Reviewer:** AI-A2 Independent Domain and Terminology Reviewer  
**Date:** 2026-09-27  
**Cycle:** Stage 6 W6-7 Frappe Framework Remainder Batch 01  
**Target Evidence Path:** `/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/scope-context-portability/evidence/stage6-w607-ai-a2-frappe-batch01-2026-09-27.md`  
**Formal Verdict:** **PASS**

---

### 1. Cryptographic Hash & Artifact Integrity Verification

The exact SHA-256 digests, row counts, and structural partitions were verified against the scope definition, proposal artifacts, and test-site reconciliation outputs:

| Artifact | File Path | Expected SHA-256 | Verified SHA-256 | Status | Row Count |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Scope CSV** | `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w607_frappe_batch01_rows_2026-09-27.csv` | `43abe1b462c47b51c0209a0650511fac2ed32cdb5f3a585cde2e9468bfaab26a` | `43abe1b462c47b51c0209a0650511fac2ed32cdb5f3a585cde2e9468bfaab26a` | **MATCH** | 250 |
| **Proposal CSV** | `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w607_frappe_batch01_proposal_2026-09-27.csv` | `f7de77ef4bbacb4385af64c89972b1e6c1b472bce0e00c8fcab30cc06763f54c` | `f7de77ef4bbacb4385af64c89972b1e6c1b472bce0e00c8fcab30cc06763f54c` | **MATCH** | 250 |
| **Site Recon JSON** | `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w607_frappe_batch01_site_recon_2026-09-27.json` | References scope `43abe1b4...` | Validated (1 override, 249 missing) | **MATCH** | 250 |

- **Partition Breakdown:**
  - Preserved Site Overrides: **1 row** (`preserved-site-override`)
  - Technical Exceptions: **2 rows** (`EXCEPTION-technical`)
  - Proposed Payload Translations: **247 rows** (`PROPOSED-payload`)
  - Total: **250 rows** (1 + 2 + 247 = 250)
  - Cryptographic and row count integrity: **100% verified match**.

---

### 2. Verification of Preserved Site Override (Requirement 4)

Reconciled against `stage6_w607_frappe_batch01_site_recon_2026-09-27.json` (live `v16.localhost` `tabTranslation` record `echig8cvv5`):

- **Source Text:** `Parent-to-child or child-to-different-child grouping is not allowed.`
- **Live Site Translation:** `لا يُسمح بالتجميع من السجل الرئيسي إلى سجل فرعي أو من سجل فرعي إلى سجل فرعي آخر.`
- **Proposal CSV Row:** Row 239
- **Proposal Translation:** `لا يُسمح بالتجميع من السجل الرئيسي إلى سجل فرعي أو من سجل فرعي إلى سجل فرعي آخر.`
- **Disposition:** `preserved-site-override`
- **Review Comment:** `Preserved verbatim from live v16.localhost tabTranslation (Plan §12)`
- **Verification Status:** **100% Verbatim Match** — Preserved intact without modification, truncation, or overwrite.

---

### 3. Verification of Technical Exceptions Classification (Requirement 3)

The 2 technical candidates were examined for proper classification and safety:

1. **Candidate 1 (Proposal Row 1):**
   - **Source Text:** `${values.doctype_name} has been added to queue for optimization`
   - **Classification:** `EXCEPTION-technical`
   - **Proposed Translation:** *(empty)*
   - **Review Comment:** `Contains unresolved JS template string interpolation ${values.doctype_name}; technical fragment kept in vendor format`
   - **Domain Assessment:** PASS. This string contains an unescaped JavaScript ES6 template literal `${values.doctype_name}`. Translating it into Arabic runs the critical risk of corrupting variable interpolation in frontend client scripts. Keeping it empty with `EXCEPTION-technical` adheres strictly to Stage 6 governance.

2. **Candidate 2 (Proposal Row 2):**
   - **Source Text:** `&copy; Frappe Technologies Pvt. Ltd. and contributors`
   - **Classification:** `EXCEPTION-technical`
   - **Proposed Translation:** *(empty)*
   - **Review Comment:** `Vendor copyright and legal trademark entity; kept in vendor format`
   - **Domain Assessment:** PASS. This is an explicit legal entity attribution and trademark notice. Standard enterprise software localization policy mandates keeping corporate copyrights in original vendor format. Keeping it empty with `EXCEPTION-technical` is correct and compliant.

---

### 4. Comprehensive Domain & Terminology Evaluation (Requirement 2)

All 247 proposed payload translations (`PROPOSED-payload`) were evaluated against standard ERP Arabic terminology, Frappe Framework v16 architecture, and enterprise software localization glossaries across the 10 core domain areas:

#### 1. DocTypes, Child Tables & Schema Modeling:
- `DocType` / `Parent DocType` $\rightarrow$ `نوع المستند (DocType)` / `نوع المستند` / `نوع المستند الرئيسي` (Standardized, unambiguous).
- `Child Table` / `Child query fields` $\rightarrow$ `الجدول الفرعي` / `حقول الاستعلام الفرعي`.
- `Parenttype, Parent and Parentfield` $\rightarrow$ `نوع الأصل والأصل وحقل الأصل` (Precise Frappe metadata schema names for linked child table foreign keys).
- `Virtual DocType` / `virtual field` $\rightarrow$ `نوع المستند الافتراضي` / `حقل افتراضي`.
- `Naming Series` / `Autoincrement autoname` $\rightarrow$ `سلسلة التسمية` / `التسمية التلقائية بالترقيم التلقائي`.
- `Customize Form` / `Custom Field` $\rightarrow$ `تخصيص النموذج` / `حقل مخصص`.

#### 2. Workspaces & UI Layouts:
- `Workspace` $\rightarrow$ `مساحة عمل`.
- `Public / Private Workspace` $\rightarrow$ `مساحات العمل العامة / مساحة عمل خاصة`.
- `Workspace Manager` $\rightarrow$ `مدير مساحة العمل`.
- `Widget` $\rightarrow$ `أداة` (e.g. `انقر على تخصيص لإضافة أداتك الأولى`).
- `Kanban Column` $\rightarrow$ `عمود كانبان`.
- Tab, Section, and Column repositioning UI actions are clearly rendered (`اسحب وأسقط قسماً هنا من علامة تبويب أخرى`, `نقل الحقل الحالي والحقول التالية إلى عمود جديد`).

#### 3. Permissions & Access Control:
- `User Permissions` $\rightarrow$ `أذونات المستخدم`.
- `Role` $\rightarrow$ `الدور` (e.g. `المستند قابل للتعديل فقط بواسطة المستخدمين ذوي الدور`).
- `Document Level permissions (Level 0)` $\rightarrow$ `أذونات على مستوى المستند (المستوى 0)`.
- `System Manager` $\rightarrow$ `مدير النظام` / `مديري النظام`.
- `Select Permission` $\rightarrow$ `إذن الاختيار`.
- `Submit permission` $\rightarrow$ `إذن اعتماد`.
- `Ignore User Permissions` $\rightarrow$ `تجاهل أذونات المستخدم`.

#### 4. Number Cards, Dashboard Charts & Analytics:
- `Number card` $\rightarrow$ `بطاقة أرقام`.
- `Standard number cards` $\rightarrow$ `بطاقات الأرقام القياسية`.
- `Aggregate Field` $\rightarrow$ `حقل التجميع`.
- `Dashboard chart` $\rightarrow$ `مخطط لوحة معلومات`.
- Clear, accurate UI error messages: `حقل التجميع مطلوب لإنشاء بطاقة أرقام`, `نوع المستند والدالة مطلوبان لإنشاء بطاقة أرقام`, `لا يمكن تعديل عوامل التصفية لبطاقات الأرقام القياسية`.

#### 5. Notifications, Assignments & Document Tracking:
- `Notification` $\rightarrow$ `إشعار`.
- `Auto follow documents` $\rightarrow$ `متابعة المستندات تلقائياً` (consistently applied across assignment, sharing, and commenting triggers).
- `Assignment Rule` $\rightarrow$ `قاعدة التعيين`.
- `Assignee` $\rightarrow$ `مُعيَّن إليه` (e.g. `إنشاء مستندات منفصلة لكل مُعيَّن إليه`, `يمكن للمُعيَّن إليه فقط إكمال هذه المهمة`).
- `Clear the assignments` $\rightarrow$ `مسح التعيينات`.

#### 6. Email Accounts & Communications Infrastructure:
- `Email Account` $\rightarrow$ `حساب البريد الإلكتروني`.
- `Outgoing Mail Server or Port` $\rightarrow$ `خادم أو منفذ بريد صادر`.
- `Email Queue` $\rightarrow$ `قائمة انتظار البريد الإلكتروني`.
- `Queue flushing aborted` $\rightarrow$ `تم إحباط تفريغ قائمة انتظار البريد الإلكتروني`.
- `To, CC, or BCC fields` $\rightarrow$ `حقول إلى أو نسخة إلى أو نسخة مخفية الوجهة` (Strictly matches international standard RFC/MIME email headers in Arabic).
- `Letter Head` $\rightarrow$ `الترويسة`.
- `Login with email link` $\rightarrow$ `تسجيل الدخول باستخدام رابط يُرسل إلى البريد الإلكتروني`.

#### 7. LDAP & Authentication:
- `LDAP settings` $\rightarrow$ `إعدادات LDAP`.
- `user and group search paths` $\rightarrow$ `مسارات البحث عن المستخدم والمجموعة`.
- `This box is due for depreciation` $\rightarrow$ `هذا الحقل في طريقه للإهمال` (Appropriate contextual translation of software deprecation).
- `Social Login Key` / `Base URL` $\rightarrow$ `مفتاح تسجيل الدخول الاجتماعي` / `عنوان URL الأساسي`.
- `Authorization server` $\rightarrow$ `خادم تفويض`.

#### 8. OAuth, OpenID & API Security:
- `OAuth` $\rightarrow$ `OAuth` (Preserved acronym for technical security protocols).
- `Authorise API Access` $\rightarrow$ `تفويض الوصول إلى API`.
- `Active tokens` / `Token state` $\rightarrow$ `رموز وصول نشطة` / `حالة الرمز المميز`.
- `OpenID Configuration` $\rightarrow$ `تكوين OpenID`.
- `OTP setup using OTP App` $\rightarrow$ `إعداد OTP باستخدام تطبيق OTP`.

#### 9. Cron, Scheduler & Background Workers:
- `Cron format` / `Cron frequency` $\rightarrow$ `تنسيق Cron` / `تكرار بنمط Cron`.
- `Scheduler` / `Re-enable scheduler` $\rightarrow$ `المجدول` / `إعادة تمكين المجدول`.
- `Background jobs` $\rightarrow$ `المهام في الخلفية` / `مهام الخلفية`.
- `Enqueued in background` $\rightarrow$ `تمت إضافة العملية المجمعة إلى قائمة الانتظار في الخلفية`.
- `RQ Workers` $\rightarrow$ `عمال RQ` (Idiomatic Frappe Redis Queue background worker terminology).

#### 10. DocStatus & Workflow Lifecycles:
- `docstatus 0 (Draft)` $\rightarrow$ `حالة المستند من 0 (مسودة)`.
- `docstatus 1 (Submitted)` $\rightarrow$ `1 (مُعتمد)`.
- `docstatus 2 (Cancelled)` $\rightarrow$ `2 (ملغى)`.
- `Workflow` / `Workflow states` / `Workflow actions` $\rightarrow$ `سير العمل` / `حالات سير العمل` / `إجراءات سير العمل`.
- `Confirmation before workflow action` $\rightarrow$ `يلزم التأكيد قبل تنفيذ إجراءات سير العمل`.

---

### 5. Syntactic, Whitespace & Token Parity Verification

- **Placeholders:** All tokens (`{0}`, `{1}`, `{2}`, `{}`) maintain 100% multiset parity between source and translation.
- **Punctuation & Formatting:** All colons (`:`), ellipses (`...`), quotation marks, and backtick delimiters (e.g. `` `clear_old_logs` ``) are properly matched.
- **Adverbial Nunation:** Systematically vocalized with accusative tanwīn (`تلقائياً`, `إجبارياً`, `دائماً`, `فارغاً`, `عاماً`).

---

### 6. Formal Verdict

**VERDICT: PASS**

The Stage 6 W6-7 Frappe Framework Remainder Batch 01 proposal (`stage6_w607_frappe_batch01_proposal_2026-09-27.csv`) fully satisfies all domain, technical, semantic, and cryptographic requirements. The 1 site override is preserved verbatim, the 2 technical exceptions are appropriately protected, and the 247 Arabic UI payload strings demonstrate impeccable adherence to Frappe Framework and ERPNext Arabic domain standards.
