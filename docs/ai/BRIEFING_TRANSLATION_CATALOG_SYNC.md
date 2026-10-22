# Handover & Briefing Letter: Translation Catalog Harmonization & UI Glossary Sync

**To:** OpenCode Autonomous Agent / Subagent Session (Session C)  
**From:** Antigravity Engineering Lane (Lead Verifier & Committer)  
**Date:** 2026-10-05  
**Subject:** Mission Briefing: Stage 6 Translation Catalog Harmonization & UI Terminology Sync  
**Target Repository:** `/home/mohamed/frappe-bench/apps/construction`  
**Target Site:** `v16.localhost`  
**Base Commit:** `234c024` (`develop` branch)  
**Work Item Path:** `docs/ai/work-items/bilingual-translation-catalog-sync/`  

---

## 1. Executive Summary & Objective

You are tasked with **harmonizing and synchronizing the system Translation Catalog (`tabTranslation`)** in accordance with the ratified bilingual master data and the 47 approved glossary terms.

Across Stage 6 (W6-1 to W6-7), over 4,300 system translations were cataloged. With the master data populations now finalized (Company `شركة الرفاعي للمقاولات العامة`, 14 Departments, 45 UOMs, 81 Accounts, 8 Items, Warehouses, Projects), several legacy UI translation strings exhibit slight terminology divergence from the approved business glossary.

Your mission is to:
1. Audit `tabTranslation` for language `ar`.
2. Cross-reference UI strings against:
   - The **47 approved glossary terms** (established in `bilingual-wave1-masters-population` and `bilingual-narrative-sanitizer`).
   - The ratified terminology for master data (Company, Department, UOM, Account, Cost Center, Warehouse, Project).
3. Identify and remediate contradictory or confusing translations in desk UI views, list views, and standard action buttons.
4. Provide a zero-write dry run, owner approval artifact, and post-sync verification.

---

## 2. Invariants & Governance Rules

1. **Role Division:**
   - OpenCode audits, prepares proposals, runs dry-run, applies changes, and generates logs.
   - Antigravity independently audits, verifies gates, and executes the local commit.
2. **Glossary Supremacy:**
   - The 47 approved terms in the bilingual glossary are authoritative. No arbitrary re-translation of established terms is permitted.
3. **Owner Confidentiality Policy (`docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`):**
   - Strictly local execution. Never push to remote git repositories or trigger public CI.
4. **Zero Vendor Code Edits:**
   - Do NOT edit any files under `apps/frappe` or `apps/erpnext`.
5. **No Broken Formatting Tokens:**
   - Ensure translation strings preserve all format specifiers (`{0}`, `%s`, HTML tags) without corruption or numeral inversion.
6. **Ephemeral Redis Protocol:**
   - Terminate Redis ports 11000/13000 immediately after test execution.

---

## 3. Scope of Work

### Step 1: Translation Catalog Inventory & Diff Audit
Develop a read-only audit script (`audit_translation_catalog.py`):
- Extract all `language = 'ar'` rows in `tabTranslation`.
- Flag entries conflicting with the 47 glossary terms or newly populated master labels.
- Output candidate deltas to a private proposal file (`sites/v16.localhost/private/translation-catalog-sync/proposal.json`).

### Step 2: Governed Apply Cycle
Following the standard bilingual governance pattern:
- AI-A2 review & owner approval artifact.
- Zero-write dry-run script.
- Apply script via `frappe.get_doc("Translation", ...).save()`.
- Post-sync verification proving zero format corruption and exact target matches.

### Step 3: Regression Verification
Run the standard regression matrix and lints to ensure no translation hook breaks.

---

## 4. Required Deliverables

Inside `docs/ai/work-items/bilingual-translation-catalog-sync/`:
1. `SCOPE.md` — scope descriptor and audit inventory.
2. `evidence/audit-translation-catalog.log` — read-only audit and delta inventory.
3. `evidence/dry-run.log` — zero-write execution log.
4. `evidence/apply.log` — applied updates log.
5. `evidence/post-sync-verification.log` — verification asserting consistency with glossary.
6. `evidence/gates.log` — 6 lints + reconciler (19/19) execution log.
7. `evidence/MANIFEST.json` — manifest #34 pinning all artefacts.

---

## 5. Handover Instructions

Once your apply and verification scripts pass:
- Terminate all Redis processes.
- Leave git working tree unstaged for Antigravity verification.
