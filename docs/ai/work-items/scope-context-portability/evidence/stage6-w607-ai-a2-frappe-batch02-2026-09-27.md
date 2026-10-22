# Stage 6 W6-7 Frappe Framework Remainder Batch 02 — AI-A2 Domain & Terminology Independent Review

**Reviewer:** AI-A2 Independent Domain and Terminology Reviewer
**Date:** 2026-09-27
**Cycle:** Stage 6 W6-7 Frappe Framework Remainder Batch 02
**Target Evidence Path:** `/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/scope-context-portability/evidence/stage6-w607-ai-a2-frappe-batch02-2026-09-27.md`
**Formal Verdict:** **PASS**

---

### 1. Cryptographic Hash & Artifact Integrity Verification

The exact SHA-256 digests, row counts, and structural partitions were verified against the scope definition, proposal artifacts, and test-site reconciliation outputs:

| Artifact | File Path | Expected SHA-256 | Verified SHA-256 | Status | Row Count |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Scope CSV** | `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w607_frappe_batch02_rows_2026-09-27.csv` | `cd6536bc0cb0b9db14214e55500ebadf3a525b2a1250147b9ad9b402e1e70be3` | `cd6536bc0cb0b9db14214e55500ebadf3a525b2a1250147b9ad9b402e1e70be3` | **MATCH** | 244 |
| **Proposal CSV** | `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w607_frappe_batch02_proposal_2026-09-27.csv` | `ec58c9c43f6708ae821e1eee404fd2207d4b5d65d323c14f14d93a7c69555b4a` | `ec58c9c43f6708ae821e1eee404fd2207d4b5d65d323c14f14d93a7c69555b4a` | **MATCH** | 244 |
| **Site Recon JSON** | `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w607_frappe_batch02_site_recon_2026-09-27.json` | References scope `cd6536bc...` | Validated (0 overrides, 244 missing) | **MATCH** | 244 |

- **Partition Breakdown:**
  - Preserved Site Overrides: **0 rows** (`preserved-site-override`)
  - Technical Exceptions: **1 row** (`EXCEPTION-technical`)
  - Proposed Payload Translations: **243 rows** (`PROPOSED-payload`)
  - Total: **244 rows** (0 + 1 + 243 = 244)
  - Cryptographic and row count integrity: **100% verified match**.

---

### 2. Verification of Preserved Site Overrides (Requirement 4)

Reconciled against `stage6_w607_frappe_batch02_site_recon_2026-09-27.json` (live `v16.localhost` `tabTranslation` query):

- **Exact Site Overrides Count:** `0`
- **Missing Runtime Count:** `244`
- **Active Site Overrides List:** `[]` (empty)
- **Domain Assessment:** PASS. None of the 244 scope candidate keys have existing runtime translations on `v16.localhost`. Zero overrides were identified, meaning no site overrides required preservation or risked being overwritten.

---

### 3. Verification of Technical Exception Classification (Requirement 3)

The single technical candidate was examined for proper classification and safety:

- **Source Text (Proposal CSV Line 223 / Table Row 222):** `{0} ${skip_list ? "" : type}`
- **Source Location:** `frappe/public/js/frappe/ui/toolbar/search_utils.js:217`
- **Classification:** `EXCEPTION-technical`
- **Proposed Translation:** *(empty)*
- **Domain Assessment:** **PASS**. This string is an upstream Frappe frontend bug where a raw ES6 JavaScript template literal (`${skip_list ? "" : type}`) was passed unparsed into the `__()` translation wrapper. Attempting to localize this fragment would corrupt client-side search autocomplete tokenization and lead to JavaScript runtime errors in the Desk toolbar. Preserving it empty under `EXCEPTION-technical` strictly adheres to Stage 6 governance principles.

---

### 4. Comprehensive Domain & Terminology Evaluation (Requirement 2)

All 243 proposed payload translations (`PROPOSED-payload`) were evaluated against standard ERP Arabic terminology, Frappe Framework v16 architecture, and enterprise software localization glossaries across the core domain areas:

#### 1. DocType & Child Table Architecture:
- `DocType` / `Parent DocType` $\rightarrow$ `نوع المستند` / `نوع مستند رئيسي` (Strictly avoids literal transliteration; aligns with standard Frappe Arabic core).
- `Child Table` $\rightarrow$ `جدول فرعي` (e.g. `The document type selected is a child table, so the parent document type is required.` $\rightarrow$ `نوع المستند المحدد هو جدول فرعي، لذا يلزم تحديد نوع المستند الرئيسي.`).
- `Custom DocType` / `Standard DocType` $\rightarrow$ `نوع المستند المخصص` / `نوع المستند القياسي`.
- `Virtual DocType` $\rightarrow$ `نوع المستند الافتراضي` (e.g. `Virtual DocType {} requires a static method called {} found {}` $\rightarrow$ `نوع المستند الافتراضي {} يتطلب دالة ثابتة تسمى {} تم العثور على {}`).
- `Naming Series` $\rightarrow$ `سلسلة التسمية` (e.g. `Set Naming Series options on your transactions.` $\rightarrow$ `تعيين خيارات سلسلة التسمية لمعاملاتك.`).
- `Property Setter` $\rightarrow$ `معدل الخصائص` (`Property Setter overrides a standard DocType or Field property` $\rightarrow$ `يقوم معدل الخصائص بتجاوز خاصية قياسية لنوع المستند أو الحقل`).

#### 2. Workspaces, Desk Tours & Navigation:
- `Workspace` $\rightarrow$ `مساحة عمل` (`User {0} does not have the permission to create a Workspace.` $\rightarrow$ `لا يملك المستخدم {0} الإذن لإنشاء مساحة عمل.`).
- `Workspace Manager` $\rightarrow$ `مدير مساحة العمل` (`You need to be Workspace Manager to delete a public workspace.` $\rightarrow$ `يجب أن تكون مدير مساحة العمل لحذف مساحة عمل عامة.`).
- `Desk Tour` / `Tour` $\rightarrow$ `الجولة` (`The next tour will start from where the user left off.` $\rightarrow$ `ستبدأ الجولة التالية من حيث توقف المستخدم.`).
- `Navbar` $\rightarrow$ `شريط التنقل` (`These announcements will appear inside a dismissible alert below the Navbar.` $\rightarrow$ `ستظهر هذه الإعلانات داخل تنبيه قابل للإغلاق أسفل شريط التنقل.`).

#### 3. Roles, Permissions & Access Control:
- `Role` $\rightarrow$ `الدور` (`The system provides many pre-defined roles. You can add new roles to set finer permissions.` $\rightarrow$ `يوفر النظام العديد من الأدوار المحددة مسبقًا. يمكنك إضافة أدوار جديدة لتعيين أذونات أكثر دقة.`).
- `System Manager` $\rightarrow$ `مدير النظام` (`Please contact your system manager to install correct version.` $\rightarrow$ `يرجى الاتصال بمدير النظام لتثبيت الإصدار الصحيح.`; `User {0} is disabled. Please contact your System Manager.` $\rightarrow$ `المستخدم {0} معطل. يرجى الاتصال بمدير النظام.`).
- `System Administrator` $\rightarrow$ `مسؤول النظام` (`Please ask 'System Administrator' to create the user for you.` $\rightarrow$ `يرجى مطالبة 'مسؤول النظام' بإنشاء المستخدم لك.`).
- `User Permissions` $\rightarrow$ `أذونات المستخدم` (`User Permissions are used to limit users to specific records.` $\rightarrow$ `تُستخدم أذونات المستخدم لتقييد المستخدمين بسجلات محددة.`).
- `Ignore User Permissions` $\rightarrow$ `تجاهل أذونات المستخدم`.
- `System user` $\rightarrow$ `مستخدم نظام` (`You need to be a system user to access this page.` $\rightarrow$ `يجب أن تكون مستخدم نظام للوصول إلى هذه الصفحة.`).

#### 4. Background Jobs, Scheduler & Worker Infrastructure:
- `Scheduler` $\rightarrow$ `المجدول` (`Scheduler can not be re-enabled when maintenance mode is active.` $\rightarrow$ `لا يمكن إعادة تمكين المجدول عندما يكون وضع الصيانة نشطًا.`; `Scheduler is inactive. Cannot import data.` $\rightarrow$ `المجدول غير نشط. لا يمكن استيراد البيانات.`).
- `Scheduled run` $\rightarrow$ `التشغيل المجدول` (`Status Updated. The email will be picked up in the next scheduled run.` $\rightarrow$ `تم تحديث الحالة. سيتم التقاط البريد الإلكتروني في التشغيل المجدول التالي.`).
- `Queued background jobs` $\rightarrow$ `وظائف خلفية ... في قائمة الانتظار` (`Too many queued background jobs ({0}). Please retry after some time.` $\rightarrow$ `وظائف خلفية كثيرة جدًا في قائمة الانتظار ({0}). يرجى إعادة المحاولة بعد بعض الوقت.`).
- `Job termination` $\rightarrow$ `إنهاء الوظيفة` (`This will terminate the job immediately and might be dangerous, are you sure?` $\rightarrow$ `سيؤدي هذا إلى إنهاء الوظيفة فورًا وقد يكون خطيرًا، هل أنت متأكد؟`).

#### 5. OAuth, OpenID Client & Authorization:
- `Authorization Server` $\rightarrow$ `خادم تفويض` (`Show Social Login Key as Authorization Server` $\rightarrow$ `إظهار مفتاح تسجيل الدخول الاجتماعي كخادم تفويض`).
- `Client policy / terms of service` $\rightarrow$ Clear, elegant terminology for OAuth consent dialogues (`URL that points to a human-readable policy document for the client. Should be shown to end-user before authorizing.` $\rightarrow$ `عنوان URL يشير إلى وثيقة سياسة مقروءة للعميل. ينبغي عرضها على المستخدم النهائي قبل التفويض.`).
- `API secret` $\rightarrow$ `سر واجهة برمجة التطبيقات` (`Store the API secret securely. It won't be displayed again.` $\rightarrow$ `احفظ سر واجهة برمجة التطبيقات بأمان. لن يتم عرضه مرة أخرى.`).

#### 6. Web Forms, Form Builder & Workflows:
- `Web Form` $\rightarrow$ `نموذج الويب` (`Standard Web Forms can not be modified, duplicate the Web Form instead.` $\rightarrow$ `لا يمكن تعديل نماذج الويب القياسية، قم بتكرار نموذج الويب بدلاً من ذلك.`; `There can be only 9 Page Break fields in a Web Form` $\rightarrow$ `يمكن أن يوجد 9 حقول فاصل صفحات فقط في نموذج الويب`).
- `Workflow` / `Workflow state` $\rightarrow$ `مسار العمل` / `حالة مسار العمل` (`This form is not editable due to a Workflow.` $\rightarrow$ `هذا النموذج غير قابل للتعديل بسبب مسار العمل.`; `Workflow state represents the current state of a document.` $\rightarrow$ `تمثل حالة مسار العمل الحالة الحالية للمستند.`).
- `Letter Head` / `Footer` $\rightarrow$ `الترويسة` / `التذييل`.

#### 7. Server Scripts & Technical Keywords:
- `Server Scripts` $\rightarrow$ `البرامج النصية للخادم` (`Server Scripts are disabled. Please enable server scripts from bench configuration.` $\rightarrow$ `البرامج النصية للخادم معطلة. يرجى تمكين البرامج النصية للخادم من تكوين bench.`).
- Technical variables and commands preserved exactly in original code format: `bench migrate`, `PATH`, `gzip`, `as_iterator`, `as_list=True`, `job_id`, `SELECT`, `WITH`, `push_relay_server_url`.

---

### 5. Review Summary & Formal Verdict

- **Cryptographic verification:** PASS (Both scope and proposal SHA-256 match perfectly).
- **Site override reconciliation:** PASS (0 overrides on live test site, matching partition).
- **Technical exceptions:** PASS (1 technical candidate `{0} ${skip_list ? "" : type}` correctly excluded with empty translation).
- **Domain terminology consistency:** PASS (DocType, Workspace, System Manager, System Administrator, Role, Child Table, Scheduler, Server Scripts, etc. 100% compliant with standard ERP Arabic glossary).
- **Formal Verdict:** **PASS**
