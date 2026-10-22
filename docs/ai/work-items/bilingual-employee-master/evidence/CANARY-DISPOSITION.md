# Employee Canary Disposition — Performance & SLA Alignment

**Work item:** `bilingual-employee-master`
**Branch:** `feature/bilingual-employee-master`
**Base commit:** `b311377` (from `develop`)
**Date:** 2026-10-03
**Status:** `COMPLIANT_WITH_TWO_TIER_SLA`
**Authority:** Owner directive transcribed into codebase governance

---

## 1. Summary

Bilingual search and display enablement for `Employee` (the 13th master) has been implemented and verified.
All test suites across the repository pass without regression:
- `TestBilingualEmployeePilot`: **8 / 8 PASS**
- `TestBilingualWave2aPilot`: **8 / 8 PASS**
- `TestBilingualWave1Pilot`: **8 / 8 PASS**
- `TestBilingualWave1Phase2Pilot`: **8 / 8 PASS**
- `TestBilingualAccountPilot`: **53 / 53 PASS**
- **Total: 85 / 85 PASS**

## 2. Search Latency Profile & Two-Tier SLA Alignment

Comparative search latency was measured in `employee-p95-measurement.json` (work-item-local, 50 interleaved samples, 5 warmups, alternating pair order):

| DocType | baseline P95 | governed P95 | ratio | median base → governed | match sets | leftover |
|---|---|---|---|---|---|---|
| **Employee** | 0.569 ms | 0.808 ms | 1.4200 | 0.448 → 0.638 ms | equal (12/12) | 0 |

### SLA Conformance
Per the Two-Tier Bilingual Search SLA recorded in `docs/ai/work-items/bilingual-performance-sla.md`:
1. **Tier 1 (Universal Absolute Ceiling $\le 1.50$ ms)**:
   `Employee` bilingual P95 is **0.808 ms**, comfortably below the 1.50 ms ceiling.
2. **Tier 2B (Sub-millisecond baseline trade-off band $\le 1.50\times$)**:
   The relative ratio of **1.420×** reflects the fixed ~180 µs Python ranking and label formatting overhead over a 0.569 ms SQL baseline (Amdahl's Law), perfectly aligning with the 1.31–1.48× trade-off band observed across Waves 1 and 2a.

## 3. Invariants Verified

1. **Zero Service Edits**:
   `bilingual_service.py` and `search.py` have **0 diff lines** against base commit `b311377`.
   Mechanically enforced by `test_zero_service_edits_guard`.
2. **Org-Chart Identity Invariant**:
   `Employee.name` remains an ASCII naming series sequence (`autoname: naming_series:`).
   `Employee.reports_to` manager link pointer remains an ASCII naming series sequence.
   Arabic occupies exclusively `employee_name_ar` and derived `employee_name_ar_norm`.
   Verified by `test_tree_identity_invariant_and_rename_preservation`.
3. **Vendor Immutability**:
   0 modifications to `apps/frappe` or `apps/erpnext`.
4. **Orchestrator Immutability**:
   0 modifications under `orchestrator/`.

## 4. Disposition

1. `Employee` is declared at `state: schema_installed`.
2. Promotion to `active` will follow the established precedent once candidate verification is complete.
