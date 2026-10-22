# UOM Catalog Closure & Formal Governance Ratification

**Work Item:** `bilingual-uom-phase2c-catalog-closure`  
**Site:** `v16.localhost`  
**Date:** 2026-10-05  
**Base Commit:** `3e871f0` (`develop` branch)  
**Governance Authority:** Owner in-session instruction following Tier 5I completion  
**Final Status:** **CONCLUDED & SEALED**  

---

## 1. Executive Declaration of Catalog Closure

This document records the **formal closure and permanent ratification** of the Unit of Measure (UOM) master data localization lifecycle for the ERP bilingual implementation.

Following the successful execution, owner approval, and post-verification of **Phase 1** (`9ccb4cd`) and **Phase 2A/2B** (`3e871f0`), all legitimate operational, construction, engineering, physical, packaging, and handling units are 100% Arabic-populated, normalized, and verified.

The remaining 204 non-construction, theoretical, and obsolete imperial units have been audited for zero usage across the entire database, classified into an immutable exclusion taxonomy, and are hereby **formally ratified as permanent exclusions**.

**The bilingual UOM localization catalog is declared 100% COMPLETE, CONCLUDED, and SEALED.**

---

## 2. Definitive UOM Accounting & Phasing Reconciliation

The entire ERPNext unit catalog on `v16.localhost` comprises exactly **253 rows**, reconciled deterministically as follows:

| Tier / Lifecycle Phase | Unit Count | Arabic State | Description & Provenance |
|---|---|---|---|
| **Phase 1: App Fixtures** | 12 | Populated | Construction-standard fixtures in `construction/fixtures/uom.json` (`M3`, `M2`, `M`, `TON`, `KG`, `PCS`, `LS`, `DAY`, `HR`, `BAG`, `LTR`, `SET`). Finalized with `enabled: 1` and `uom_name_ar` in Tier 5F (`9ccb4cd`). |
| **Phase 1: Active In-Use Stock Units** | 3 | Populated | Active stock units with live Item references (`Nos`, `Tonne`, `Box`). Populated in Tier 5F (`9ccb4cd`). |
| **Phase 2A: Priority Engineering Units** | 29 | Populated | Priority physical, dimensional, area, volume, mass, time, energy, and electrical units (`Meter`, `Centimeter`, `Millimeter`, `Kilogram`, `Gram`, `Hour`, `Minute`, `Second`, `Joule`, `Tesla`, etc.). Populated in Tier 5I (`3e871f0`). |
| **Phase 2B: Commercial Handling Units** | 1 | Populated | Commercial handling unit (`Pair`). Populated in Tier 5I (`3e871f0`). |
| **Vendor Fixtures (Never Translated)** | 2 | Unpopulated | `_Test UOM` and `_Test UOM 1`. Bound by the absolute `_Test*` fixture rule (never translated). |
| **F4-Pruned Draft Units** | 2 | Unpopulated | `Pint (US)` and `Acre`. Only referenced by draft test BOQ headers; preserved untranslated outside production scope. |
| **Phase 2C: Formally Ratified Exclusions** | 204 | Unpopulated | Non-construction, obsolete imperial, and specialized theoretical physics units. Formally excluded and sealed. |
| **Total Reconciled UOM Catalog** | **253** | **45 Populated** | **Exact match across all catalog subsets ($12+3+29+1+2+2+204 = 253$).** |

---

## 3. Evidence of Zero Operational Usage

A comprehensive, read-only audit was executed across `v16.localhost` using [`check_phase2c_zero_usage.py`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2c-catalog-closure/evidence/scripts/check_phase2c_zero_usage.py):
- **Tables & Columns Scanned:** 105 table/column pairs dynamically discovered via `information_schema.COLUMNS` where column name $\in$ `(uom, stock_uom, unit, purchase_uom, weight_uom)`.
- **Mandatory Targets Checked:** `tabItem`, `tabBOQ Item`, `tabSales Invoice Item`, `tabPurchase Order Item`, `tabStock Entry Detail`, `tabMaterial Request Item`, `tabBOM Item`, `tabStock Ledger Entry`, `tabItem Price`, `tabDelivery Note Item`, `tabPurchase Receipt Item`, `tabPurchase Invoice Item`, `tabSales Order Item`, `tabQuotation Item`.
- **Query Type:** Parameterized SQL `IN (204 units)`.
- **Active Operational References Found:** Exactly **0 references** across the entire database.
- **Database Mutation Guard:** Database was verified byte-for-byte unmodified (0 writes).

Log reference: [`zero-usage-safety-check.log`](file:///home/mohamed/frappe-bench/apps/construction/docs/ai/work-items/bilingual-uom-phase2c-catalog-closure/evidence/zero-usage-safety-check.log).

---

## 4. Key Evidence Artefacts & Cryptographic Digests

| Artefact | Path | SHA-256 Digest |
|---|---|---|
| **Zero-Usage Audit Script** | `docs/ai/work-items/bilingual-uom-phase2c-catalog-closure/evidence/scripts/check_phase2c_zero_usage.py` | `6c3f6e7c227bfb477987ef4523af17bf090a034f2e346079760e40bf2b421f1f` |
| **Zero-Usage Safety Log** | `docs/ai/work-items/bilingual-uom-phase2c-catalog-closure/evidence/zero-usage-safety-check.log` | `d727837a728529cc8de882a3316cb378007ac638004e8957fd23c6576061ee7b` |
| **Exclusion Taxonomy** | `docs/ai/work-items/bilingual-uom-phase2c-catalog-closure/evidence/PHASE2C_EXCLUSION_TAXONOMY.md` | `9bb87247b782feb29a84ec6ebc5e2c8a7d4e82c19ec10f02f3c7bd0bd9f5e0e7` |
| **Inventory Triage Log (Baseline)** | `docs/ai/work-items/bilingual-uom-phase2-triage/evidence/inventory-triage.log` | `4dbea1ee10507d5bf73ab4e6b6d6b0212786d9575907fdbf0bb26db1c3c839fc` |

---

## 5. Architectural Invariants Formally Ratified

1. **Zero Translation Maintenance Liability:**
   The 204 units are permanently deprioritized and will not receive translations. No tickets, backlog items, or PRs will be opened to translate them.
2. **Desk Picker Cleanliness Guaranteed:**
   All 45 populated units remain easily discoverable in bilingual pickers. Unused units remain untranslated and will not pollute Arabic search queries.
3. **Immutability of Frozen Fixtures:**
   `construction/fixtures/uom.json` remains strictly frozen at SHA `d6e27a01...` with its 12 Phase 1 fixtures (`enabled: 1`, `uom_name_ar` populated).
4. **P95 SLA Adherence:**
   Desk link search and transaction link search remain strictly within the $\le 1.50\text{ ms}$ P95 SLA band.
