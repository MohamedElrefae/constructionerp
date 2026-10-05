# Handover & Briefing Letter: UOM Phase 2C Catalog Closure & Formal Ratification

**To:** OpenCode Autonomous Agent / Subagent Session  
**From:** Antigravity Engineering Lane  
**Date:** 2026-10-05  
**Subject:** Mission Briefing: Finalizing UOM Phase 2C Catalog Closure & Governance Ratification  
**Target Repository:** `/home/mohamed/frappe-bench/apps/construction`  
**Target Site:** `v16.localhost`  
**Base Commit:** `3e871f0` (`develop` branch)  

---

## 1. Executive Summary & Context

You are tasked with **finalizing the UOM Phase 2C Catalog Closure and Formal Governance Ratification** for the ERP bilingual localization system.

The UOM localization stream has successfully completed all operational and physical unit translations:
- **Phase 1 (Tier 5F, `9ccb4cd`):** 15 core units populated (12 construction fixtures in `uom.json` enabled and bilingual, plus 3 active stock units: `Nos`, `Tonne`, `Box`).
- **Phase 2A & 2B (Tier 5I, `3e871f0`):** 30 units populated via standard `doc.save()` (29 engineering/physical units + 1 handling unit `Pair`).
- **Current Bilingual UOM Surface:** Exactly **45 units** are active, verified bilingual with server-derived normalization (`uom_name_ar_norm`).
- **Vendor Fixtures (2 units):** `_Test UOM` and `_Test UOM 1` are permanently excluded per fixture naming rules.
- **F4-Pruned Units (2 units):** `Pint (US)` and `Acre` (found only in draft test BOQs, excluded from production translations).
- **Phase 2C Remainder (204 units):** Non-construction, highly specialized scientific, radiological, astronomical, or obsolete imperial vendor units (e.g., `Becquerel`, `Barn`, `Curie`, `Farad`, `Gauss`, `Minim`, `Peck`, `Chain`, `Furlong`).

> [!IMPORTANT]
> **GOAL OF THIS WORK ITEM:**
> Do NOT translate any Phase 2C units. Translating 204 obscure scientific units creates unnecessary maintenance debt, pollutes desk link pickers, and invites translation errors.
> Your mission is to **formally ratify the permanent exclusion / deprecation** of these 204 units, conduct an operational safety check to prove zero live usage, and generate the final catalog closure record to mark the UOM localization lifecycle 100% complete.

---

## 2. Invariants & Rules of Engagement

1. **Owner Confidentiality Policy (`docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`):**
   - Strictly local execution. Do NOT push to remote repositories or initiate public CI.
   - If committing locally, always use:
     ```bash
     git -c core.hooksPath=/dev/null commit -m "..."
     ```
2. **Zero Vendor Modifications:**
   - Do NOT edit any file under `apps/frappe` or `apps/erpnext`.
3. **Do NOT Modify Frozen Fixtures:**
   - `construction/fixtures/uom.json` is byte-frozen at SHA `d6e27a01...` (already contains the 12 Phase 1 fixtures with `enabled: 1` and `uom_name_ar`). Do NOT modify this file.
4. **Zero Shared Code Changes:**
   - `bilingual_service.py`, `searchable_dropdown/api/search.py`, and hooks are byte-frozen.
5. **Redis Process Hygiene:**
   - Ephemeral Redis (`11000` queue, `13000` cache) should only run if executing tests requiring cache, and MUST be shut down immediately afterward. Never stage `dump.rdb`.
6. **Manifest Integrity:**
   - Existing 29 manifests in `docs/ai/work-items/*/evidence/MANIFEST.json` (290 artefacts) must remain valid. Any new evidence must be accompanied by its manifest.

---

## 3. Scope of Work for the OpenCode Session

### Step 1: Pre-Closure Verification & Cross-Referencing
Verify that none of the 204 Phase 2C units have active, non-test operational references in the database:
- Check `tabItem` where `stock_uom` IN (204 units).
- Check `tabBOQ Item` where `unit` IN (204 units).
- Check transactional tables (`tabSales Invoice Item`, `tabPurchase Order Item`, `tabStock Entry Detail`, `tabMaterial Request Item`).
- Expected result: **0 active production references**.

### Step 2: Formally Document Phase 2C Exclusions
In `docs/ai/work-items/bilingual-uom-phase2-triage/` (or a dedicated closure subfolder):
1. Compile the definitive alphabetical catalog of the 204 excluded units grouped by category:
   - Physical / Radiological / Particle (`Becquerel`, `Curie`, `Gray`, `Sievert`, `Barn`, etc.)
   - Electromagnetic / Optical (`Farad`, `Henry`, `Tesla`, `Weber`, `Candela`, `Lumen`, `Lux`, etc.)
   - Obsolete Imperial / Avoirdupois (`Chain`, `Furlong`, `League`, `Peck`, `Minim`, `Dram`, etc.)
   - Miscellaneous non-construction units.
2. Provide the explicit business and architectural justification for permanent exclusion:
   - Zero relevance to civil, structural, architectural, or MEP construction scopes.
   - Protection of desk search relevance (preventing false matches when searching in Arabic/English).
   - Minimization of localization governance overhead.

### Step 3: Owner Ratification & Governance Sign-Off Artifact
Generate `UOM_CATALOG_CLOSURE_RATIFICATION.md` recording:
- Total UOM count: 253.
- Populated & Verified: 45 (15 Phase 1 + 30 Phase 2A/2B).
- Fixtures / Test Pruned: 4 (2 vendor fixtures + 2 F4-pruned).
- Excluded & Ratified: 204 (Phase 2C).
- Formal closure declaration: UOM localization lifecycle is marked **CONCLUDED & SEALED**.

### Step 4: Verification & Regression Gates
Run the standard validation gates:
- Verify that `test_transaction_link_search.py` (20/20) and `test_bilingual_desk_link_dispatch.py` (17/17) pass cleanly.
- Verify manifest integrity across all work items.

---

## 4. Key Reference Documents & Evidence

- Triage Scope & Invariants: [`docs/ai/work-items/bilingual-uom-phase2-triage/SCOPE.md`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2-triage/SCOPE.md)
- Triage Inventory Log: [`docs/ai/work-items/bilingual-uom-phase2-triage/evidence/inventory-triage.log`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2-triage/evidence/inventory-triage.log)
- Post-Import Verification Log: [`docs/ai/work-items/bilingual-uom-phase2-triage/evidence/post-import-verification.log`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2-triage/evidence/post-import-verification.log)
- Owner Confidentiality Policy: [`docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/OWNER_CONFIDENTIALITY_POLICY.md)
