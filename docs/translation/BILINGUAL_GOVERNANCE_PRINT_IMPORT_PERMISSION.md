# Architectural Decision Record — Bilingual Capability Governance (Plan §3.2)

**Status:** APPROVED (owner decision, 2026-10-03)
**Applies to:** all thirteen active bilingual masters and all planned wave extensions
**Authority:** owner directive and implementation contract under `docs/translation/ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md`
**Reference:** Plan §3.2 requirement:
> *"No Wave 2 or 3 field is created until its display, search, print, import, permission, and rename behavior is specified in the registry."*

---

## 1. Context and Problem Statement

Section 3.2 of the End-to-End Bilingual Plan establishes an explicit gating precondition for expanding bilingual master-data coverage: every bilingual master must have its **Display, Search, Permission, Rename, Import, and Print** behaviors specified, bounded, and verified.

Prior to this decision, the programme had:
1. Implemented and empirically bounded bilingual **Search** under a dedicated Two-Tier SLA ADR (`docs/ai/work-items/bilingual-performance-sla.md` @ `b311377`).
2. Implemented language-aware fallback chains for **Display** across 13 masters.
3. Implemented permission checks and asymmetric write confinement for **Permission**.
4. Test-asserted primary key immutability and metadata preservation during **Rename**.

However:
- The **Data Import** behavior had not been explicitly exercised in dedicated automated bulk tests to confirm that the `validate` hook reliably intercepts rows processed by Frappe's bulk `Importer` (`insert()` / `save()`).
- The **Print** capability remained ambiguous: while physical Arabic columns exist on document instances and are accessible to Jinja templates, standard ERPNext print formats do not automatically generate dual-column or dual-header bilingual layouts.

To avoid asserting unverified capabilities, this ADR establishes the definitive governance ledger and specification for all six capabilities.

---

## 2. Specification and Verification Status of the Six Capabilities

### 2.1 Capability 1: Display
- **Status:** **VERIFIED & OPERATIONAL**
- **Specification:**
  - Standard session fallback chains are defined in `bilingual_registry.json` and executed via `bilingual_service.display_name(doctype, name, lang)`:
    - Arabic sessions (`ar`): `[arabic, english, identity]`
    - English sessions (`en`): `[english, arabic, identity]`
  - Where an Arabic translation is absent, the system transparently falls back to the canonical English name, then to the system identity (primary key).
  - Desk views, forms, breadcrumbs, and link formatters consume this fallback chain.
- **Verification:**
  - Automated test coverage across all active masters: `Account`, `Item`, `Customer`, `Supplier`, `Cost Center`, `Warehouse`, `Project`, `Item Group`, `Customer Group`, `Supplier Group`, `Territory`, `UOM`, `Employee`.
  - Zero null or empty labels rendered when either language is populated.

### 2.2 Capability 2: Search
- **Status:** **VERIFIED & BOUNDED (GOVERNED UNDER TWO-TIER SLA)**
- **Specification:**
  - Link field auto-complete and dropdown searches route through `search_bilingual` and `searchable_link_search`.
  - Queries match against both ASCII/English source text and normalized Arabic text stored in `*_ar_norm` (or `*_in_arabic_norm`).
  - Normalization removes diacritics (tashkeel), tatweel/kashida, and normalizes Alef/Yaa/Taa-marbuta variations (أ/إ/آ -> ا, ة -> ه, ى -> ي).
- **Performance SLA:**
  - Governed by ADR `docs/ai/work-items/bilingual-performance-sla.md`:
    - **Tier 1 (Universal):** P95 $\le 1.50$ ms absolute latency ceiling across all 13 masters.
    - **Tier 2A (Relative Gate):** $\le 1.15\times$ baseline P95 for baseline $\ge 1.0$ ms (`Account`).
    - **Tier 2B (Documented Trade-Off Band):** $\le 1.50\times$ overhead ratio for sub-millisecond baselines, recognizing the fixed ~150–200 µs Python ranking and normalization overhead (governed by Amdahl's Law).
- **Verification:**
  - 85/85 tests passing; 18/18 content-addressed evidence manifests resolvable against repository blobs via `git cat-file blob`.

### 2.3 Capability 3: Permission
- **Status:** **VERIFIED & CONFINED**
- **Specification:**
  - Dual-layer permission enforcement:
    1. **Document-Level Permissions:** Frappe's standard Role Permission Manager (RPM) governs access to parent documents. Users without `read` permission on the master DocType cannot read bilingual fields; users without `write` permission cannot modify them.
    2. **Programmatic Accessor Confinement:** The programmatic accessor `bilingual_service.read_identity(doctype, name)` executes `doc.has_permission("read")`. If unauthorized, it raises `frappe.PermissionError`.
    3. **Write Policy Asymmetry:**
       - **Account (Financial Master):** Direct form/REST writes to `account_name_ar` are prohibited. Modifications require a signed one-time token issued by the governed endpoint `set_account_name_ar` (`enforce_account_arabic_policy`). New Account creation cannot carry Arabic names.
       - **Operational & Classification Masters:** Business records allow standard form, REST, and CSV import writes for operational agility, but validate string safety on every save path.
- **Verification:**
  - Tested in `test_bilingual_account_pilot.py` and master-specific suites.

### 2.4 Capability 4: Rename
- **Status:** **VERIFIED & TEST-ASSERTED**
- **Specification:**
  - All bilingual master DocTypes preserve immutable canonical ASCII identifiers or serials for document primary keys (`name`), such as `item_code` for `Item`, autoname serials for `Employee`, or account numbers for `Account`.
  - Calling `frappe.rename_doc` updates foreign key references across dependent ledgers while preserving the document's Arabic name and its `_norm` search key completely intact and synchronized.
- **Verification:**
  - Mechanically asserted across all pilot suites via `test_rename_doc_preserves_arabic_and_norm_keys` and `test_tree_identity_invariant_and_rename_preservation`.

### 2.5 Capability 5: Data Import (Bulk Insert & Update)
- **Status:** **VERIFIED & TEST-ASSERTED**
- **Specification:**
  - Frappe's bulk `Data Import` engine (`frappe.core.doctype.data_import.importer.Importer`) processes records by executing `new_doc.insert()` for new rows and `updated_doc.save()` for existing rows.
  - Because `insert()` and `save()` trigger Frappe's standard `validate` hook, `construction.services.bilingual_service.enforce_bilingual_arabic_policy` runs unconditionally on every imported row.
  - Three load-bearing invariants are enforced during bulk data import:
    1. **Server-Authoritative Normalization:** Any client-supplied `_norm` field in the import file (including poisoned search keys) is ignored and overwritten with the server-derived `_normalize_arabic()` output.
    2. **Bidi and Control Character Neutralization:** Any imported row containing forbidden bidi controls (`U+202A`–`U+202E`, `U+2066`–`U+2069`, `U+200E`, `U+200F`, `U+061C`), C0/C1 controls, DEL, or NUL in identity fields triggers `frappe.ValidationError`. The specific row fails, triggers a database transaction rollback, logs an error in `Data Import Log`, and prevents dirty or malicious data from entering the database.
    3. **Financial Account Immutability on Insert:** Importing a new `Account` with an Arabic name is rejected with `frappe.PermissionError`, enforcing the invariant that new accounts must first be established within the chart of accounts before Arabic labeling is applied via governed operations.
- **Verification:**
  - Verified empirically and mechanically in `construction/tests/test_bilingual_data_import.py` (6/6 passing tests covering new inserts, poisoned norm overwrite, bidi rejection, updates, and Account insertion asymmetry).

### 2.6 Capability 6: Print
- **Status:** **DOCUMENTED AS UNVERIFIED & OUT-OF-BAND**
- **Specification:**
  - Physical columns (`*_ar`, `*_in_arabic`) reside directly on the respective DocType database tables and are accessible within custom Jinja print templates (e.g. `{{ doc.item_name_ar or doc.item_name }}`).
  - Standard ERPNext print formats (e.g. Standard Item / Customer / Account print layouts) do not out-of-the-box render dual-column bilingual headers or localized Arabic typography.
  - While the Construction module provides an experimental toggle `enable_bilingual_boq_print` for BOQ documents, there is **no automated test suite asserting PDF/HTML bilingual rendering** for standard ERPNext masters.
- **Governance Rule:**
  - Print capability for bilingual masters is formally certified as **UNVERIFIED / OUT-OF-BAND**.
  - Maintainers, users, and deployment workflows must not assume out-of-the-box bilingual printing for standard masters. Bilingual print requirements must be implemented via explicitly authored, client-specific custom print formats.

---

## 3. Capability Status Ledger across Active Masters

| Master | Display | Search | Permission | Rename | Import | Print |
|---|---|---|---|---|---|---|
| **Account** | ✅ Verified | ✅ Tier 2A Bound | ✅ Governed Token | ✅ Tested | ✅ Blocked on New | ⚠️ Out-of-band |
| **Item** | ✅ Verified | ✅ Tier 2B Bound | ✅ Generic RPM | ✅ Tested | ✅ Verified | ⚠️ Out-of-band |
| **Customer** | ✅ Verified | ✅ Tier 2B Bound | ✅ Generic RPM | ✅ Tested | ✅ Verified | ⚠️ Out-of-band |
| **Supplier** | ✅ Verified | ✅ Tier 2B Bound | ✅ Generic RPM | ✅ Tested | ✅ Verified | ⚠️ Out-of-band |
| **Cost Center** | ✅ Verified | ✅ Tier 2B Bound | ✅ Generic RPM | ✅ Tested | ✅ Verified | ⚠️ Out-of-band |
| **Warehouse** | ✅ Verified | ✅ Tier 2B Bound | ✅ Generic RPM | ✅ Tested | ✅ Verified | ⚠️ Out-of-band |
| **Project** | ✅ Verified | ✅ Tier 2B Bound | ✅ Generic RPM | ✅ Tested | ✅ Verified | ⚠️ Out-of-band |
| **Item Group** | ✅ Verified | ✅ Tier 2B Bound | ✅ Generic RPM | ✅ Tested | ✅ Verified | ⚠️ Out-of-band |
| **Customer Group** | ✅ Verified | ✅ Tier 2B Bound | ✅ Generic RPM | ✅ Tested | ✅ Verified | ⚠️ Out-of-band |
| **Supplier Group** | ✅ Verified | ✅ Tier 2B Bound | ✅ Generic RPM | ✅ Tested | ✅ Verified | ⚠️ Out-of-band |
| **Territory** | ✅ Verified | ✅ Tier 2B Bound | ✅ Generic RPM | ✅ Tested | ✅ Verified | ⚠️ Out-of-band |
| **UOM** | ✅ Verified | ✅ Tier 2B Bound | ✅ Generic RPM | ✅ Tested | ✅ Verified | ⚠️ Out-of-band |
| **Employee** | ✅ Verified | ✅ Tier 2B Bound | ✅ Generic RPM | ✅ Tested | ✅ Verified | ⚠️ Out-of-band |

---

## 4. Consequences and Invariants

1. **Zero Unverified Assertions:** No wave summary or certification may claim that bilingual Print is verified. Print remains marked as out-of-band until dedicated test fixtures render and assert bilingual layout geometry.
2. **Import Security:** Bulk imports via ERPNext Data Import are fully protected against search-poisoning attacks and bidi-spoofing attacks without requiring external validation tools or pre-import sanitizers.
3. **Zero Service Edit Invariant Preserved:** This governance specification and the accompanying test suite `test_bilingual_data_import.py` require zero edits to `bilingual_service.py` and `search.py`, strictly maintaining the zero-diff invariant against baseline commits.
