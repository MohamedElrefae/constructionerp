# Department Canary Disposition — Performance & SLA Alignment

**Work item:** `bilingual-department-master`
**Branch:** `feature/bilingual-department-master`
**Base commit:** `c1d278b` (from `develop`)
**Date:** 2026-10-03
**Status:** `COMPLIANT_WITH_TWO_TIER_SLA`
**Authority:** Owner directive transcribed into codebase governance under Plan §3.2

---

## 1. Summary

Bilingual search, tree navigation, and display enablement for `Department` (the 14th master) has been implemented and verified.
All test suites across the repository pass without regression:
- `TestBilingualDepartmentPilot`: **8 / 8 PASS**
- `TestBilingualDataImport`: **6 / 6 PASS**
- `TestBilingualEmployeePilot`: **8 / 8 PASS**
- `TestBilingualWave2aPilot`: **8 / 8 PASS**
- `TestBilingualWave1Pilot`: **8 / 8 PASS**
- `TestBilingualWave1Phase2Pilot`: **8 / 8 PASS**
- `TestBilingualAccountPilot`: **53 / 53 PASS**
- **Total: 99 / 99 PASS**

## 2. Search Latency Profile & Two-Tier SLA Alignment

Comparative search latency was measured in `department-p95-measurement.json` (work-item-local, 50 interleaved samples, 5 warmups, alternating pair order):

| DocType | baseline P95 | governed P95 | ratio | median base → governed | match sets | leftover |
|---|---|---|---|---|---|---|
| **Department** | 0.654 ms | 0.816 ms | 1.2477 | 0.569 → 0.758 ms | equal (12/12) | 0 |

### SLA Conformance
Per the Two-Tier Bilingual Search SLA recorded in `docs/ai/work-items/bilingual-performance-sla.md`:
1. **Tier 1 (Universal Absolute Ceiling $\le 1.50$ ms)**:
   `Department` bilingual P95 is **0.816 ms**, comfortably below the 1.50 ms universal ceiling.
2. **Tier 2B (Sub-millisecond baseline trade-off band $\le 1.50\times$)**:
   The relative ratio of **1.248×** is well within the $\le 1.50\times$ trade-off band, reflecting the fixed ~160 µs Python ranking and normalization overhead over a 0.654 ms SQL baseline (Amdahl's Law).

## 3. Invariants Verified

1. **Zero Service Edits**:
   `bilingual_service.py` and `search.py` have **0 diff lines** against base commit `c1d278b`.
   Mechanically enforced by `test_zero_service_edits_guard`.
2. **Tree Identity Invariant**:
   `Department.name` remains canonical ASCII identifier / company suffix.
   `Department.parent_department` self-link pointer remains intact.
   Arabic occupies exclusively `department_name_ar` and derived `department_name_ar_norm`.
   Verified by `test_tree_identity_invariant_and_rename_preservation`.
3. **Vendor Immutability**:
   0 modifications to `apps/frappe` or `apps/erpnext`.
4. **Orchestrator Immutability**:
   0 modifications under `orchestrator/`.

## 4. Disposition

1. `Department` is initially staged at `state: schema_installed`.
2. Upon verification and candidate certification, it is promoted to `state: active` as the 14th active master.
