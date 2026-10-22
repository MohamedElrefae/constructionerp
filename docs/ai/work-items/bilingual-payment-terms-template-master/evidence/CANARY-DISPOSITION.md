# Payment Terms Template Canary Disposition — Performance & SLA Alignment

**Work item:** `bilingual-payment-terms-template-master`
**Branch:** `feature/bilingual-payment-terms-template-master`
**Base commit:** `2cbe71a` (from `develop`)
**Date:** 2026-10-03
**Status:** `COMPLIANT_WITH_TWO_TIER_SLA`
**Authority:** Owner directive transcribed into codebase governance under Plan §3.2

---

## 1. Summary

Bilingual search, validation, and display enablement for `Payment Terms Template` (the 19th master) has been implemented and verified.
All test suites across the repository pass without regression:
- `TestBilingualPaymentTermsTemplatePilot`: **8 / 8 PASS**
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
- **Total Bilingual Matrix: 133 / 133 PASS**

---

## 2. Search Latency Profile & Two-Tier SLA Alignment

Comparative search latency was measured in `payment-terms-template-p95-measurement.json` (work-item-local, 50 interleaved samples, 5 warmups, alternating pair order):

| DocType | baseline P95 | governed P95 | ratio | median base → governed | match sets | leftover |
|---|---|---|---|---|---|---|
| **Payment Terms Template** | 0.472 ms | 0.655 ms | 1.3877 | 0.452 → 0.637 ms | equal (12/12) | 0 parent, 0 child |

### SLA Conformance
Per the Two-Tier Bilingual Search SLA recorded in `docs/ai/work-items/bilingual-performance-sla.md`:
1. **Tier 1 (Universal Absolute Ceiling $\le 1.50$ ms)**:
   `Payment Terms Template` bilingual P95 is **0.655 ms**, comfortably below the 1.50 ms universal ceiling.
2. **Tier 2B (Sub-millisecond baseline trade-off band $\le 1.50\times$)**:
   The relative ratio of **1.388×** is well within the $\le 1.50\times$ trade-off band, reflecting the fixed ~183 µs Python ranking and normalization overhead over a 0.472 ms SQL baseline (Amdahl's Law).

---

## 3. Invariants Verified

1. **Zero Service Edits**:
   `bilingual_service.py` and `search.py` have **0 diff lines** against base commit `2cbe71a` (nineteenth consecutive candidate).
   Mechanically enforced by `test_zero_service_edits_guard`.
2. **Identity Invariant & Naming Path**:
   `Payment Terms Template.name` uses `field:template_name` and remains pure ASCII / English.
   Arabic occupies exclusively `template_name_ar` and derived `template_name_ar_norm`.
   Verified by `test_identity_invariant_and_rename_preservation`.
3. **Mandatory Child Table Fixture Hygiene**:
   Mandatory child table `Payment Terms Template Detail` rows are created during fixtures and verified completely clean with zero orphan leakage on teardown.
4. **Exclusions & Scope Boundaries Strictly Respected**:
   Child table `Payment Terms Template Detail` (contractual narrative and schedule rows) remains unmapped in registry, deferred under `narrative-unicode-policy` (committed at `2cbe71a`).
   Standalone doctype `Payment Term` remains unmapped in this cycle.
5. **Data Quality Condition Recorded**:
   3 live test parent rows and 4 child rows in production baseline recorded in §H of Scope Descriptor.
6. **Vendor & Orchestrator Immutability**:
   0 modifications to `apps/frappe`, `apps/erpnext`, or `orchestrator/`.

---

## 4. Disposition

1. `Payment Terms Template` is declared `state: active` in `bilingual_registry.json` as the 19th active master.
2. Candidate certified for merge into `develop`.
