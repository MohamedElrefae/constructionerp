# Independent Linguistic Review Report: Stage 6 W6-7 Frappe Framework Remainder Batch 02

**Reviewer:** Subagent AI-A1 (Read-Only Independent Linguistic Auditor)
**Target Cycle:** Stage 6 W6-7 Frappe Framework Remainder Batch 02 (`v16.localhost`)
**Target Scope Date:** 2026-09-27
**Formal Verdict:** **PASS**
**Destination Evidence File:** `/home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/scope-context-portability/evidence/stage6-w607-ai-a1-frappe-batch02-2026-09-27.md`

---

### 1. Cryptographic Hash & Artifact Integrity Verification

The exact SHA-256 digests, row counts, and structural partitions were verified against the scope definition, proposal artifacts, and test-site reconciliation outputs:

| Artifact | File Path | Verified SHA-256 | Expected SHA-256 | Rows | Status |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Scope CSV** | `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w607_frappe_batch02_rows_2026-09-27.csv` | `cd6536bc0cb0b9db14214e55500ebadf3a525b2a1250147b9ad9b402e1e70be3` | `cd6536bc0cb0b9db14214e55500ebadf3a525b2a1250147b9ad9b402e1e70be3` | 244 | **MATCH / VERIFIED** |
| **Proposal CSV** | `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w607_frappe_batch02_proposal_2026-09-27.csv` | `ec58c9c43f6708ae821e1eee404fd2207d4b5d65d323c14f14d93a7c69555b4a` | `ec58c9c43f6708ae821e1eee404fd2207d4b5d65d323c14f14d93a7c69555b4a` | 244 | **MATCH / VERIFIED** |
| **Site Recon JSON** | `/home/mohamed/frappe-bench/apps/construction/docs/translation/stage6_w607_frappe_batch02_site_recon_2026-09-27.json` | References scope SHA `cd6536bc0cb0b9db14214e55500ebadf3a525b2a1250147b9ad9b402e1e70be3` | — | 244 | **MATCH / VERIFIED** |

#### Partition Breakdown:
- **Preserved Site Overrides:** 0 items (`preserved-site-override`)
- **Technical Exceptions:** 1 item (`EXCEPTION-technical`)
- **Proposed Payload Translations:** 243 items (`PROPOSED-payload`)
- **Total Data Rows Evaluated:** 244 rows (excluding header)
- **Integrity Status:** 100% cryptographic and structural parity across all artifacts.

---

### 2. Verification of Preserved Site Overrides (Requirement 4)

Reconciliation against `stage6_w607_frappe_batch02_site_recon_2026-09-27.json` confirms:
- `exact_site_overrides_count`: 0
- `site_overrides`: `[]`
- `missing_runtime_count`: 244
- Count of `preserved-site-override` rows in proposal CSV: **0**
- **Status:** **VERIFIED** — Exact parity with live site reconciliation facts.

---

### 3. Verification of Technical Exceptions (Requirement 3)

The single technical candidate was inspected for exact classification, empty translation cell, and justification rationale:

- **Source Text:** `{0} ${skip_list ? "" : type}`
- **Source Location:** `frappe/public/js/frappe/ui/toolbar/search_utils.js:217`
- **Classification:** `EXCEPTION-technical`
- **Proposed Translation:** *(empty string)*
- **Rationale:** Contains unresolved JavaScript template literal / ternary interpolation `${skip_list ? "" : type}` within a dynamic search utility string. Translating this token would cause client-side script corruption.
- **Status:** **VERIFIED** — Correctly classified as `EXCEPTION-technical` with an empty translation cell.

---

### 4. Comprehensive Linguistic Evaluation of 243 Proposed Payload Translations (Requirement 2)

All 243 candidate Arabic translations (`PROPOSED-payload`) were thoroughly reviewed across phonological, morphological (الصرف), syntactic (النحو), semantic, and stylistic standards for enterprise ERP and web frameworks:

#### Key Linguistic Dimensions Evaluated:
1. **Grammar & Syntax (النحو والتركيب):**
   - Consistent and precise application of accusative nunation (*tanwīn al-naṣb*) on adverbials and predicates (e.g., `تلقائيًا`, `نهائيًا`, `فارغًا`, `أولاً`, `مباشرة`, `بنجاح`).
   - Strict adherence to rules for hamzāt (*hamzat al-waṣl* vs. *hamzat al-qaṭ‘*), including accurate verbal nouns (e.g., `استيراد`, `استخدام`, `إنشاء`, `إرسال`, `إعادة`, `إلغاء`, `إدارة`, `إذن`, `إرفاق`, `إعداد`).
   - Sound passive and conditional constructions (e.g., `إذا لم تتم إعادة توجيهك...`, `لا يمكن تعديل {0} لأنه لم يتم إلغاؤه...`, `تعذر تحديد تنسيق...`).

2. **Morphological Concord & Agreement (المطابقة الإعرابية):**
   - Precise grammatical agreement between subjects, verbs, adjectives, demonstratives, and pronouns (e.g., feminine pronoun in `لا يمكن أن تكون دقة ({0}) لـ {1} أكبر من طولها ({2})` referring to `دقة`).
   - Proper number agreement for numerical constructions (e.g., `خلال {1} ثوانٍ`, `10 دقائق على الأقل`, `أنواع المستندات المخصصة الثلاثة`).

3. **ERP & Technical Framework Terminology Harmony:**
   - Framework entities and concepts translated consistently with established Frappe/ERP standards:
     - `DocType` / `Parent DocType` / `Child Table` $\rightarrow$ `نوع المستند`, `نوع المستند الرئيسي`, `الجدول الفرعي` / `جدول فرعي`.
     - `Letter Head` / `Footer` $\rightarrow$ `الترويسة`, `التذييل`.
     - `Property Setter` $\rightarrow$ `معدل الخصائص`.
     - `Naming Series` $\rightarrow$ `سلسلة التسمية`.
     - `Workflow` / `Workflow State` $\rightarrow$ `مسار العمل`, `حالة مسار العمل`.
     - `Workspace` / `Workspace Manager` $\rightarrow$ `مساحة العمل`, `مدير مساحة العمل`.
     - `User Permissions` $\rightarrow$ `أذونات المستخدم`.
     - `Rate limit` $\rightarrow$ `حد المعدل`.
     - `Deduplication` $\rightarrow$ `إلغاء التكرار`.
     - `Onboarding` $\rightarrow$ `التهيئة`.
   - Technical standards, environment keys, protocols, and database syntax are preserved verbatim:
     - `as_iterator`, `as_list=True`, `as_dict=True`
     - `push_relay_server_url`, `job_id`, `PATH`, `gzip`
     - `SELECT`, `WITH`, `COUNT`, `dict syntax`
     - `LDAP`, `OAuth`, `ISO 3166 ALPHA-2`, `JSON`, `PDF`, `CSV`

4. **Placeholder & Code-Syntax Parity:**
   - 100% preservation of positional, format, and template tokens (`{0}`, `{1}`, `{2}`, `{3}`, `{4}`, `{}`), backticks, and special characters.
   - Natural Arabic word ordering around placeholders without index permutation or skew.
   - Punctuation integrity: Arabic question mark (`؟`), Arabic comma (`،`), and English technical tokens inside code phrases.

---

### 5. Formal Verdict

**VERDICT: PASS**

The Stage 6 W6-7 Frappe Framework Remainder Batch 02 translation proposal (`stage6_w607_frappe_batch02_proposal_2026-09-27.csv`) meets all linguistic, grammatical, morphological, technical, and cryptographic governance criteria without defect. It is recommended for immediate integration.
