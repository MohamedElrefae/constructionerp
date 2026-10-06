# Handover & Briefing Letter: Production Migration & Readiness Gate Audit

**To:** OpenCode Autonomous Agent / Subagent Session  
**From:** Antigravity Engineering Lane  
**Date:** 2026-10-05  
**Subject:** Mission Briefing: Production Migration & Readiness Gate Audit (Consolidated Apply Runner & Verification)  
**Target Repository:** `/home/mohamed/frappe-bench/apps/construction`  
**Target Site:** Production / Target Site Deployment  
**Source Baseline:** `v16.localhost` (Commit: `3e871f0` on `develop`)  

---

## 1. Executive Summary & Objective

You are tasked with leading the **Production Migration & Readiness Gate Audit** stream for the ERP bilingual localization system.

All bilingual master data, taxonomies, and reports have been fully developed, reviewed, owner-approved, applied, and verified on the authorized development/test site (`v16.localhost`). The current governance gate is:
```yaml
production_mutation_authorized: false
```

Your mission is to bridge the gap between development verification and production readiness:
1. Conduct a rigorous **Readiness Gate Audit** evaluating all architectural, security, and schema prerequisites.
2. Build an **Idempotent, Transaction-Safe Production Migration Runner** that unifies the approved proposals across all completed tiers into a single, executable, fail-closed script.
3. Establish the **Pre-Flight and Post-Flight Verification Protocol** ensuring zero data loss, zero tree corruption, and instant rollback capability on production.

---

## 2. Inventory of Populated Bilingual Surfaces on `v16.localhost`

The verified master dataset on `v16.localhost` consists of:

| Surface / DocType | Populated Rows | Provenance & Rules |
|---|---|---|
| **Account** | 81 rows | Wave-1 (Tier 5B). Standard chart of accounts hierarchy. |
| **Item** | 8 rows | Wave-1 Phase 2 (Tier 5C). Construction stock & service items. |
| **Warehouse** | 6 rows | Wave-1 Phase 2 (Tier 5C). Project site & central stores. |
| **Project** | 5 rows | Wave-1 Phase 2 (Tier 5C). Active contracting projects. |
| **Cost Center** | 3 rows | Wave-1 Phase 2 (Tier 5C). Main operating cost centers. |
| **Item Group** | 6 rows | Wave-2 Groups (Tier 5D). Root handled via R3b workaround. |
| **Customer Group** | 5 rows | Wave-2 Groups (Tier 5D). Root handled via R3b workaround. |
| **Supplier Group** | 8 rows | Wave-2 Groups (Tier 5D). Root handled via R3b workaround. |
| **Territory** | 4 rows | Wave-2 Groups (Tier 5D). Root handled via R3b workaround. |
| **Department** | 14 rows | Tier 5G (`5d96f12`). Root `All Departments` (R3b) + 13 Elrefae operational departments. |
| **Company** | 1 row | Tier 5H (`1f55a4a`). `Elrefae` $\rightarrow$ `شركة الرفاعي للمقاولات العامة`. |
| **UOM** | 45 rows | Tier 5F (`9ccb4cd`) & Tier 5I (`3e871f0`). 15 Phase 1 + 30 Phase 2A/2B physical & packaging units. |

*Total Populated Bilingual Entities:* **196 master records**.

---

## 3. Strict Architectural & Governance Invariants

1. **Owner Confidentiality Policy (`docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`):**
   - Strictly local execution. Do NOT push to remote repositories or initiate public CI.
   - If committing locally, always use:
     ```bash
     git -c core.hooksPath=/dev/null commit -m "..."
     ```
2. **Zero Vendor Code Modifications:**
   - Absolute rule: Never modify files under `apps/frappe` or `apps/erpnext`.
3. **Idempotence & Fail-Closed Safety:**
   - The production migration runner must be fully idempotent: running it once, twice, or ten times produces the exact same end state without errors or duplicate writes.
   - All migrations must execute within a database transaction (`frappe.db.begin()`). Any unexpected exception or failed assertion must trigger `frappe.db.rollback()` immediately with zero partial writes.
4. **Server-Derived Normalization Invariant:**
   - Client scripts must never write directly to `*_name_ar_norm`. Normalization is strictly derived server-side upon `doc.save()` by `enforce_bilingual_arabic_policy`.
5. **Handling Known Vendor Quirks:**
   - **R3b Root NSM Quirk:** In ERPNext, root nodes of tree DocTypes (`Item Group`, `Customer Group`, `Supplier Group`, `Territory`, `Department`) have empty parents. Standard `NestedSet` logic can fail when saving root nodes. Use the disclosed, documented workaround (`frappe.in_test` guard or scoped root handling) to update root Arabic fields without triggering tree parent-reassignment traps.
6. **Privacy Rule (R4):**
   - Raw Arabic values and migration logs must be managed under private site storage (`sites/<site-name>/private/production-migration/`).

---

## 4. Key Deliverables for this Work Item

### Deliverable A: Production Readiness Audit Report
Create `docs/ai/work-items/production-migration-readiness/evidence/READINESS_AUDIT.md`:
- **Schema Readiness:** Verify that all target DocTypes have the required custom fields (`*_name_ar`, `*_name_ar_norm`) installed via custom field fixtures.
- **Database Collation & Encoding:** Verify `utf8mb4` encoding across all target tables.
- **Backup Verification Protocol:** Assert that automated pre-migration database snapshot/backup exists before any script execution.
- **Dependency & Hook Verification:** Ensure `enforce_bilingual_arabic_policy` hook is properly registered in `hooks.py`.

### Deliverable B: Consolidated Production Migration Runner
Create a unified runner script (e.g. `scripts/run_production_bilingual_migration.py` or within `docs/ai/work-items/production-migration-readiness/evidence/scripts/`):
- Accepts CLI arguments: `--site <site_name>`, `--dry-run`, `--force`.
- **Pre-flight assertions:**
  - Site exists and is accessible.
  - Backup timestamp verified.
  - Required schema fields present.
- **Consolidated Apply Logic:**
  - Iterates through the 12 populated DocTypes in topological dependency order (Company $\rightarrow$ Cost Center $\rightarrow$ Warehouse $\rightarrow$ Groups $\rightarrow$ Department $\rightarrow$ UOM $\rightarrow$ Item $\rightarrow$ Account).
  - Performs `doc.save()` preserving existing metadata, timestamps, and tree relationships.
  - Applies R3b workaround exclusively on the known root nodes.
- **Dry-run mode:**
  - Performs full lookup and mock transformations, printing a complete delta summary with **0 database writes**.

### Deliverable C: Post-Migration Verification Script
Create `verify_production_bilingual_migration.py`:
- Asserts exact record counts for each DocType.
- Asserts zero NULL or empty `*_name_ar_norm` on populated records.
- Verifies tree integrity (`lft` / `rgt` indices) across all NestedSets.
- Runs probe searches using `bilingual_search` to verify that desk link resolution works instantaneously.

### Deliverable D: Manifest & Evidence Record
- Maintain living `MANIFEST.json` pinning all scripts and evidence artefacts with sha256 digests.

---

## 5. Reference Files & Baseline Evidence

- UOM Phase 2 Triage Scope: [`docs/ai/work-items/bilingual-uom-phase2-triage/SCOPE.md`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2-triage/SCOPE.md)
- Department Phase 1 Scope: [`docs/ai/work-items/bilingual-department-phase1-population/SCOPE.md`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-department-phase1-population/SCOPE.md)
- Company Phase 1 Scope: [`docs/ai/work-items/bilingual-company-phase1-population/SCOPE.md`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-company-phase1-population/SCOPE.md)
- Owner Confidentiality Policy: [`docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/OWNER_CONFIDENTIALITY_POLICY.md)
- Transaction Link Search Service: [`construction/services/transaction_link_search.py`](file:///home/mohamed/frappe-bench/apps/construction/construction/services/transaction_link_search.py)
