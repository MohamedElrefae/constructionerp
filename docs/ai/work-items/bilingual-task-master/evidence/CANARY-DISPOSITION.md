# Task Canary Disposition — Performance & SLA Alignment

**Work item:** `bilingual-task-master`
**Branch:** `feature/bilingual-task-master`
**Base commit:** `abffaaa` (from `develop`)
**Date:** 2026-10-03
**Status:** `COMPLIANT_WITH_TWO_TIER_SLA`
**Authority:** Owner directive transcribed into codebase governance under Plan §3.2

---

## 1. Summary

Bilingual search, tree navigation, and display enablement for `Task` (the 17th master) has been implemented and verified.
All test suites across the repository pass without regression:
- `TestBilingualTaskPilot`: **8 / 8 PASS**
- `TestBilingualBOQPrint`: **10 / 10 PASS**
- `TestBilingualDepartmentPilot`: **8 / 8 PASS**
- `TestBilingualDataImport`: **6 / 6 PASS**
- `TestBilingualEmployeePilot`: **8 / 8 PASS**
- `TestBilingualWave2aPilot`: **8 / 8 PASS**
- `TestBilingualWave1Pilot`: **8 / 8 PASS**
- `TestBilingualWave1Phase2Pilot`: **8 / 8 PASS**
- `TestBilingualAccountPilot`: **53 / 53 PASS**
- **Total Bilingual Matrix: 117 / 117 PASS**

---

## 2. Search Latency Profile & Two-Tier SLA Alignment

Comparative search latency was measured in `task-p95-measurement.json` (work-item-local, 50 interleaved samples, 5 warmups, alternating pair order):

| DocType | baseline P95 | governed P95 | ratio | median base → governed | match sets | leftover |
|---|---|---|---|---|---|---|
| **Task** | 0.466 ms | 0.654 ms | 1.4034 | 0.428 → 0.435 ms | equal (12/12) | 0 |

### SLA Conformance
Per the Two-Tier Bilingual Search SLA recorded in `docs/ai/work-items/bilingual-performance-sla.md`:
1. **Tier 1 (Universal Absolute Ceiling $\le 1.50$ ms)**:
   `Task` bilingual P95 is **0.654 ms**, comfortably below the 1.50 ms universal ceiling.
2. **Tier 2B (Sub-millisecond baseline trade-off band $\le 1.50\times$)**:
   The relative ratio of **1.403×** is well within the $\le 1.50\times$ trade-off band, reflecting the fixed ~188 µs Python ranking and normalization overhead over a 0.466 ms SQL baseline (Amdahl's Law).

---

## 3. Invariants Verified

1. **Zero Service Edits**:
   `bilingual_service.py` and `search.py` have **0 diff lines** against base commit `abffaaa` (seventeenth consecutive candidate).
   Mechanically enforced by `test_zero_service_edits_guard`.
2. **Tree Identity Invariant & Naming Series**:
   `Task.name` remains canonical naming series ASCII (`TASK-.YYYY.-.#####`).
   `Task.parent_task` self-link pointer remains intact and pure ASCII.
   Arabic occupies exclusively `subject_ar` and derived `subject_ar_norm`.
   Verified by `test_identity_invariant_and_tree_preservation`.
3. **Exclusions Strictly Respected**:
   `status` (Select, controlled vocabulary) remains unmapped in registry.
   `description` (Text Editor, narrative rich-text) remains unmapped.
   `project` foreign-key join remains excluded from link search path.
4. **Thin-Data Precondition Recorded**:
   3 rows live baseline data recorded in §1 of Scope Descriptor.
5. **Vendor & Orchestrator Immutability**:
   0 modifications to `apps/frappe`, `apps/erpnext`, or `orchestrator/`.

---

## 4. Disposition

1. `Task` is declared `state: active` in `bilingual_registry.json` as the 17th active master.
2. Candidate certified for merge into `develop`.
