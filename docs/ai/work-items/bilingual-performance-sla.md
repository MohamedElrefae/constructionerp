# Architectural Decision Record — Two-Tier Bilingual Search SLA

**Status:** APPROVED (owner decision, 2026-10-02)
**Applies to:** all active bilingual masters
**Authority:** owner directive, transcribed into repository governance
**Supersedes:** the single relative ceiling in
`erp-arabic-bilingual-data/evidence/raw-logs/stage3/p95-measurement.json` (`<= baseline * 1.10`)
**Related:** `erp-arabic-bilingual-data/evidence/raw-logs/stage3/p95-measurement-wave1.json`

---

## 1. Context

Two measurement facts forced this decision.

**The relative ceiling is not stable at small baselines.** The Stage-3 re-pin re-measured
`Account` at `n=100` per round (5 rounds, 500 samples per side) instead of the historical
`n=50`. Round spread collapsed from **0.580 ms to 0.019 ms** — roughly a 30x variance reduction —
and the true ratio became **1.1210**, not the 1.062–1.087 that noisy single runs suggested.

At `n=50` the nearest-rank P95 tail rests on **two** samples, so a single scheduler event of
50–100 µs moves the statistic. The preserved Stage-3 artefact recorded 1.071, but **four of its
five rounds individually exceeded 1.10** (0.986, 1.184, 1.190, 1.190, 1.190); the recorded pass
came from min-of-rounds selection landing favourably. A 10% ceiling on a ~1.3 ms query admits
only ~130 µs for the entire Python localisation stack, which is the same order as the
measurement noise. **The 1.10x ceiling was statistically undecidable at this baseline.**

**The other eleven masters sit far outside 1.10x.** Wave 1 and Wave 2a recorded ratios of
1.3092–1.4750 — every one exceeding the old ceiling.

**Measurement scope and production query shape.** The empirical parity asserted across
evidence manifests (`match_sets_equal: true`) is measured against canonical synthetic fixture
prefixes (`CT-*`) where baseline and governed queries scan identical records. For unanchored
production queries, the governed pipeline applies multi-lingual ranking (`exact > prefix > substring`)
and limits results to `page_length`, intentionally providing localized relevance rather than
reproducing Frappe's raw SQL ordering.

**Frozen calibration pins.** The figures recorded in §4 represent frozen baseline calibration
pins bound to the immutable evidence artefacts enumerated in §7 (e.g. Account at 1.322 ms / 1.482 ms).
While subsequent execution in different environments or under database state variations may fluctuate
absolute latencies, the committed artefacts serve as the authoritative baseline for governance.

## 2. Why the ratios diverge: Amdahl's Law and SQL divergence

On standard single-table master scans, the bilingual stack costs an almost **constant ~150–200 µs**:
dynamic registry resolution, server-authoritative normalisation, bidi validation,
Python-level relevance ranking (`exact > prefix > substring`), and bilingual label synthesis.

A constant additive cost divided by a smaller denominator produces a larger ratio:

```
Account            (1.322 + 0.160) / 1.322 = 1.121x   sub-1.5 ms absolute
Classification     (0.420 + 0.180) / 0.420 = 1.428x   sub-0.65 ms absolute
```

A percentage-only ceiling therefore **penalises faster queries**. Holding a 0.42 ms
baseline to 1.10x demands the entire Python stack fit in 42 µs, which is not achievable in
interpreted Python. In absolute terms those masters are more than twice as fast as `Account`.

**Unified root cause: the two legs issue materially different SQL.** The comparison between
native Frappe `search_link` and the governed `searchable_dropdown` cascade is not an isolated diff
on identical SQL statements:
- Native Frappe `search_link` computes `IFNULL(1/NULLIF(LOCATE(...)))` as SQL `_relevance`, orders
  by `_relevance DESC, idx DESC, lft/creation/modified DESC`, and filters across auxiliary doctype
  `search_fields` (e.g. `parent_structure`, `project_name`).
- The governed bilingual search issues simpler `LIKE` queries with `ORDER BY modified DESC` and
  delegates multi-lingual ranking and candidate pruning to Python over `RANK_WINDOW`.

Because of this architectural divergence, the additive cost model applies primarily to simple
single-table lookups. For composite or deeply-indexed doctypes (such as `BOQ Header` and `BOQ Structure`),
the baseline SQL overhead is heavier than the governed SQL query, leading to *negative* relative
overhead (-0.207 ms, -0.228 ms; ratios 0.7568x and 0.7685x). Both easily satisfy Tier 1 (<= 1.50 ms)
and Tier 2B (<= 1.50x).

## 3. The two-tier structure

### Tier 1 — universal absolute ceiling (primary gate)

**Every** bilingual master search must achieve **<= 1.50 ms P95** in a production-equivalent
environment. No exceptions, no tiering. This is the gate that actually bounds user-visible
latency.

### Tier 2 — relative overhead, selected by baseline latency

| Sub-tier | Baseline P95 | Relative gate | Enforcement |
|---|---|---|---|
| **2A** | >= 1.0 ms (`Account`) | **<= 1.15x** min-of-rounds P95, `n=100` | `test_comparative_p95_artifact_bound_and_gate` |
| **2B** | < 1.0 ms (eleven masters) | **<= 1.50x** documented architectural trade-off band | work-item-local evidence manifests |

Tier 2 never relaxes Tier 1. A master may satisfy its relative band and still breach the
absolute ceiling, which fails the programme.

Tier 2 measures an end-to-end framework execution comparison between native Frappe `search_link`
and the governed `searchable_dropdown` cascade, rather than an isolated micro-benchmark on identical SQL.

## 4. Measured state — all 19 active masters

Derived from the committed evidence artefacts and re-verified at this commit.

| DocType | baseline P95 | governed P95 | ratio | tier | relative gate | absolute |
|---|---|---|---|---|---|---|
| Account | 1.322 ms | 1.482 ms | 1.1210 | 2A | 1.15x OK | OK |
| Asset Category | 0.451 ms | 0.626 ms | 1.3880 | 2B | 1.50x OK | OK |
| BOQ Header | 0.851 ms | 0.644 ms | 0.7568 | 2B | 1.50x OK | OK |
| BOQ Structure | 0.985 ms | 0.757 ms | 0.7685 | 2B | 1.50x OK | OK |
| Cost Center | 0.558 ms | 0.811 ms | 1.4534 | 2B | 1.50x OK | OK |
| Customer | 0.487 ms | 0.686 ms | 1.4086 | 2B | 1.50x OK | OK |
| Customer Group | 0.444 ms | 0.617 ms | 1.3896 | 2B | 1.50x OK | OK |
| Department | 0.654 ms | 0.816 ms | 1.2477 | 2B | 1.50x OK | OK |
| Employee | 0.569 ms | 0.808 ms | 1.4200 | 2B | 1.50x OK | OK |
| Item | 0.767 ms | 1.114 ms | 1.4524 | 2B | 1.50x OK | OK |
| Item Group | 0.440 ms | 0.645 ms | 1.4659 | 2B | 1.50x OK | OK |
| Payment Terms Template | 0.472 ms | 0.655 ms | 1.3877 | 2B | 1.50x OK | OK |
| Project | 0.544 ms | 0.730 ms | 1.3419 | 2B | 1.50x OK | OK |
| Supplier | 0.480 ms | 0.675 ms | 1.4063 | 2B | 1.50x OK | OK |
| Supplier Group | 0.438 ms | 0.620 ms | 1.4155 | 2B | 1.50x OK | OK |
| Task | 0.466 ms | 0.654 ms | 1.4034 | 2B | 1.50x OK | OK |
| Territory | 0.445 ms | 0.622 ms | 1.3978 | 2B | 1.50x OK | OK |
| UOM (253 rows) | 0.960 ms | 1.416 ms | 1.4750 | 2B | 1.50x OK | OK |
| Warehouse | 0.595 ms | 0.779 ms | 1.3092 | 2B | 1.50x OK | OK |

**All 19 active masters measured. Zero masters breach their relative gate. Zero breach the absolute ceiling.**

## 5. Standing decisions

1. The **15 ms absolute floor remains REJECTED**. It permitted a 1000% regression and would
   have masked exactly the kind of slow degradation a gate exists to catch.
2. The **1.10x ceiling is RETIRED**, not weakened — it was statistically undecidable at
   sub-2 ms baselines.
3. **1.15x with `n=100`** is canonical for Tier 2A. Sample width is part of the gate: an `n=50`
   measurement cannot decide a 1.15x bound at this latency. Tier 2B's 1.50x band uses `n=50`
   interleaved nearest-rank P95 across standard masters, which is statistically adequate to
   detect regressions beyond 1.50x on sub-millisecond queries (BOQ Header and Structure were
   evaluated under `n=100` 5-round min-of-rounds).
4. Tier 2B's 1.50x band is a **documented architectural trade-off**, not a performance target.
   It records the measured cost of Python-level ranking on sub-millisecond baselines.
5. **UOM tier boundary**: UOM's baseline (0.960 ms) sits near the 1.0 ms Tier 2A threshold.
   An ad-hoc local observation under the canonical `n=100` protocol measured a 1.254 ms baseline
   with ratio 0.668x, passing both Tier 2B (<= 1.50x) and Tier 2A (<= 1.15x). This observation
   is noted as unpinned context; §4 retains its committed 0.960 ms evidence binding.

## 6. Known gap

Tier 2B is **documented, not test-enforced**. Only Tier 2A has a test
(`test_comparative_p95_artifact_bound_and_gate`); the Tier 2B masters are governed by
their committed evidence manifests. A future wave that regresses `Item Group` beyond 1.50x
would not fail any suite — it would require re-reading the artefacts.

Closing that gap needs a test that re-derives Tier 2B against the local measurement harness.
That is follow-up work and is not blocked by this ADR.

## 7. Evidence sources

| Source | Binds |
|---|---|
| `erp-arabic-bilingual-data/.../stage3/p95-measurement-wave1.json` | Account, `n=100`, additive supersession of the `n=50` baseline |
| `erp-arabic-bilingual-data/.../stage3/p95-measurement.json` | preserved Stage-3 baseline, `n=50`, superseded not overwritten |
| `bilingual-wave1-masters/evidence/wave1-p95-measurement.json` | six Wave 1 masters |
| `bilingual-wave2a-classification-masters/evidence/wave2a-p95-measurement.json` | five Wave 2a masters |
| `bilingual-employee-master/evidence/employee-p95-measurement.json` | Employee master |
| `bilingual-department-master/evidence/department-p95-measurement.json` | Department master (`n=50` interleaved nearest-rank P95) |
| `bilingual-task-master/evidence/task-p95-measurement.json` | Task master |
| `bilingual-asset-category-master/evidence/asset-category-p95-measurement.json` | Asset Category master |
| `bilingual-payment-terms-template-master/evidence/payment-terms-template-p95-measurement.json` | Payment Terms Template master |
| `bilingual-boq-p95-measurement/evidence/boq-header-p95-measurement.json` | BOQ Header master (`n=100` 5-round min-of-rounds) |
| `bilingual-boq-p95-measurement/evidence/boq-structure-p95-measurement.json` | BOQ Structure master (`n=100` 5-round min-of-rounds) |