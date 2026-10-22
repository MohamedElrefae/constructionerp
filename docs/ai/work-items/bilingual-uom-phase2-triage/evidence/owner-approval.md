# Owner Approval Record — bilingual-uom-phase2-triage

**Work item:** `bilingual-uom-phase2-triage`  
**Base commit:** `5d96f12`  
**Date:** 2026-10-05  
**Authorized test site:** `v16.localhost` (`production_mutation_authorized: false`)  
**Approved proposal SHA-256:** `930b91cd2f5c64ec70e0cbaff0a998ea6423c29db901ac7779a8e626da39617a`  

---

## 1. Owner Approval Scope

The owner has reviewed and explicitly approved the following decisions for Tier 5I / UOM Phase 2+ triage:

1. **Approved Phase 2 Target Rows (30 rows)**:
   - **Phase 2A (29 Physical & Engineering Units)**: `Ampere`, `Centimeter`, `Cubic Centimeter`, `Cubic Foot`, `Cubic Meter`, `Cubic Yard`, `Foot`, `Gram`, `Horsepower`, `Hour`, `Inch`, `Joule`, `Kilojoule`, `Kilometer`, `Kilowatt`, `Meter`, `Milligram`, `Millimeter`, `Minute`, `Ounce`, `Pound`, `Second`, `Square Foot`, `Square Meter`, `Square Yard`, `Tesla`, `Watt`, `Week`, `Yard`.
   - **Phase 2B (1 Commercial Count Unit)**: `Pair`.
   - All 30 rows to be populated via standard `doc.save()` through the registered `enforce_bilingual_arabic_policy` hook with server-derived norm keys.

2. **Phase 2C Exclusions (204 rows)**:
   - Formally documented as deprioritized/excluded (0 writes, zero bulk-translation liability).

3. **Vendor & Pruned Fixtures (4 rows)**:
   - 2 Vendor fixtures (`_Test UOM`, `_Test UOM 1`) permanently excluded.
   - 2 Pruned test units (`Pint (US)`, `Acre`) remain unpopulated test noise.

4. **Zero App-Code Diff**:
   - Zero modifications to `apps/frappe` / `apps/erpnext`.
   - Zero modifications to shared framework files (`hooks.py`, `bilingual_service.py`, `bilingual_registry.json`).
   - `construction/fixtures/uom.json` remains untouched (already finalized in Phase 1).

---

## 2. Hard Gate Approval

- **Proposal Hash:** `930b91cd2f5c64ec70e0cbaff0a998ea6423c29db901ac7779a8e626da39617a`
- **Review Verdict:** APPROVE (30/30) in `review-ai-a2.md`
- **Status:** **APPROVED FOR GOVERNED APPLY**
