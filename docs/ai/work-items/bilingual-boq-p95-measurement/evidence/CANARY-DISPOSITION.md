# BOQ Masters (BOQ Header & BOQ Structure) Canary Disposition — Two-Tier SLA Measurement

**Work item:** `bilingual-boq-p95-measurement`
**Branch:** `feature/bilingual-boq-p95-measurement`
**Base commit:** `2f74193` (from `develop`)
**Date:** 2026-10-03
**Status:** `COMPLIANT_WITH_TWO_TIER_SLA`
**Authority:** Owner directive transcribed into codebase governance under Plan §3.2

---

## 1. Summary

The performance measurement gap for `BOQ Header` and `BOQ Structure` (closing the last two unmeasured active masters in `bilingual-performance-sla.md` §4) has been executed using a dedicated multi-round harness (`n=100`, 5 rounds, 500 samples per side per doctype).

Both doctypes demonstrate full compliance with the Two-Tier Bilingual Search SLA:
- **Zero breach of Tier 1 Universal Absolute Ceiling ($\le 1.50$ ms)**.
- **Zero breach of relative overhead gates** (governed search is ~23–24% faster than baseline across both doctypes).
- Clean teardown verified with zero leftover fixtures.

---

## 2. Search Latency Profile & Two-Tier SLA Alignment

Measured via work-item-local harness `measure_boq_p95.py` across 5 rounds of $n=100$ interleaved samples (5 warmups per round, alternating pair order, paused GC, nearest-rank P95):

| DocType | Baseline P95 (min-of-rounds) | Governed P95 (min-of-rounds) | Ratio | Tier | Relative Gate | Absolute Gate | Mean Baseline $\to$ Governed P95 | Match Sets | Leftover |
|---|---|---|---|---|---|---|---|---|---|
| **BOQ Header** | 0.851 ms | 0.644 ms | **0.7568×** | 2B | 1.50x OK | OK | 0.932 $\to$ 0.698 ms | equal (12/12) | 0 |
| **BOQ Structure** | 0.985 ms | 0.757 ms | **0.7685×** | 2B | 1.50x OK | OK | 1.047 $\to$ 0.795 ms | equal (12/12) | 0 |

### SLA Conformance & Tier Analysis
1. **Tier 1 (Universal Absolute Ceiling $\le 1.50$ ms)**:
   - `BOQ Header`: Governed P95 is **0.644 ms** (min-of-rounds) / **0.698 ms** (mean).
   - `BOQ Structure`: Governed P95 is **0.757 ms** (min-of-rounds) / **0.795 ms** (mean).
   - Both are well below the 1.50 ms threshold.
2. **Tier 2 Relative Gates**:
   - Under canonical min-of-rounds benchmarking (ADR §1 & §2), both baseline latencies are sub-millisecond (**0.851 ms** and **0.985 ms**), confirming **Tier 2B**.
   - Note on high-water baseline: In individual rounds, `BOQ Structure`'s baseline touched 1.07–1.09 ms (mean 1.047 ms). Even if classified under Tier 2A's $\ge 1.0$ ms boundary, the measured ratio of **0.7685×** (and mean ratio 0.7593×) is well within Tier 2A's $\le 1.15\times$ gate.
   - In all interpretations, bilingual search outperforms native link search because `searchable_link_search` avoids Frappe's monolithic query overhead.

---

## 3. Invariants Verified

1. **Zero Service Edits**:
   `bilingual_service.py` and `search.py` have **0 diff lines** against base commit `2f74193`.
2. **Measurement-Only Discipline**:
   Zero modifications to `bilingual_registry.json`, `hooks.py`, patches, print templates, or `boq_link_queries.py`.
3. **Census Closure**:
   Closes the two unmeasured rows in `bilingual-performance-sla.md` §4, moving the census from **17 of 19** to **19 of 19 active masters empirically measured**.
4. **Scope Findings Preserved**:
   The finding that production BOQ dropdowns currently route to `boq_link_queries.py` without searching `title_ar` is formally recorded in `SCOPE.md` §1.2 for subsequent SQL design.

---

## 4. Disposition

1. Both `BOQ Header` and `BOQ Structure` are certified as measured and compliant with the Two-Tier Bilingual Search SLA.
2. `bilingual-performance-sla.md` §4 and §7 updated to record the empirical profiles and measurement artefacts.
