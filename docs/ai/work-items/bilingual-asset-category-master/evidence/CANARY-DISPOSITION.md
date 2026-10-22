# Asset Category Canary Disposition — Performance & SLA Alignment

**Work item:** `bilingual-asset-category-master`
**Branch:** `feature/bilingual-asset-category-master`
**Base commit:** `04dfe35` (from `develop`)
**Date:** 2026-10-03
**Status:** `COMPLIANT_WITH_TWO_TIER_SLA`
**Authority:** Owner directive transcribed into codebase governance under Plan §3.2

---

## 1. Summary

Bilingual search, validation, and display enablement for `Asset Category` (the 18th master) has been implemented and verified.
All test suites across the repository pass without regression:
- `TestBilingualAssetCategoryPilot`: **8 / 8 PASS**
- `TestBilingualTaskPilot`: **8 / 8 PASS**
- `TestBilingualBOQPrint`: **10 / 10 PASS**
- `TestBilingualDepartmentPilot`: **8 / 8 PASS**
- `TestBilingualDataImport`: **6 / 6 PASS**
- `TestBilingualEmployeePilot`: **8 / 8 PASS**
- `TestBilingualWave2aPilot`: **8 / 8 PASS**
- `TestBilingualWave1Pilot`: **8 / 8 PASS**
- `TestBilingualWave1Phase2Pilot`: **8 / 8 PASS**
- `TestBilingualAccountPilot`: **53 / 53 PASS**
- **Total Bilingual Matrix: 125 / 125 PASS**

---

## 2. Search Latency Profile & Two-Tier SLA Alignment

Comparative search latency was measured in `asset-category-p95-measurement.json` (work-item-local, 50 interleaved samples, 5 warmups, alternating pair order):

| DocType | baseline P95 | governed P95 | ratio | median base → governed | match sets | leftover |
|---|---|---|---|---|---|---|
| **Asset Category** | 0.451 ms | 0.626 ms | 1.3880 | 0.417 → 0.599 ms | equal (12/12) | 0 |

### SLA Conformance
Per the Two-Tier Bilingual Search SLA recorded in `docs/ai/work-items/bilingual-performance-sla.md`:
1. **Tier 1 (Universal Absolute Ceiling $\le 1.50$ ms)**:
   `Asset Category` bilingual P95 is **0.626 ms**, comfortably below the 1.50 ms universal ceiling.
2. **Tier 2B (Sub-millisecond baseline trade-off band $\le 1.50\times$)**:
   The relative ratio of **1.388×** is well within the $\le 1.50\times$ trade-off band, reflecting the fixed ~175 µs Python ranking and normalization overhead over a 0.451 ms SQL baseline (Amdahl's Law).

---

## 3. Invariants Verified

1. **Zero Service Edits**:
   `bilingual_service.py` and `search.py` have **0 diff lines** against base commit `04dfe35` (eighteenth consecutive candidate).
   Mechanically enforced by `test_zero_service_edits_guard`.
2. **Identity Invariant & Naming Field Preservation**:
   `Asset Category.name` uses `field:asset_category_name` and remains pure ASCII / English.
   Arabic occupies exclusively `asset_category_name_ar` and derived `asset_category_name_ar_norm`.
   Verified by `test_identity_invariant_and_rename_preservation`.
3. **Exclusions & Scope Boundaries Strictly Respected**:
   Child tables `Asset Category Account` (accounts) and `Asset Finance Book` remain unmapped.
   `Asset` transactional entity deferred to protect Wave 2b boundary.
4. **Thin-Data Precondition Recorded**:
   2 rows live baseline data recorded in §1 of Scope Descriptor.
5. **Vendor & Orchestrator Immutability**:
   0 modifications to `apps/frappe`, `apps/erpnext`, or `orchestrator/`.

---

## 4. Disposition

1. `Asset Category` is declared `state: active` in `bilingual_registry.json` as the 18th active master.
2. Candidate certified for merge into `develop`.
