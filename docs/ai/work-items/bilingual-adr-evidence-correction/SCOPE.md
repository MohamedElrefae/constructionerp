# Scope Descriptor — bilingual-adr-evidence-correction

**Work item:** `bilingual-adr-evidence-correction`
**Branch:** `feature/bilingual-adr-evidence-correction`
**Base commit:** `a7086ef` (19 of 19 active masters measured)
**Scope:** `bilingual-performance-sla.md` §4 Department row and §7 Department binding
**Date:** 2026-10-03
**Authority:** owner instruction given in session; transcribed by the agent

Two factual defects in the two-tier SLA ADR, found by reconciling all 19 §4 rows against
the evidence artefacts §7 says they come from. **Documentation-only: no schema,
registry, hook, print, harness, measurement, or service change.**

Owner chose the factual correction only. The structural weaknesses the same sweep
surfaced are recorded in §3, not fixed here.

---

## 1. Defects

### 1.1 §4's Department row is unsourced

| | baseline | governed | ratio |
|---|---|---|---|
| `bilingual-performance-sla.md` §4, line 79 | 0.623 ms | 0.830 ms | 1.3327 |
| `bilingual-department-master/evidence/department-p95-measurement.json` — the artefact §7 binds for this row | **0.654 ms** | **0.816 ms** | **1.2477** |

The strings `0.623`, `0.830` and `1.3327` occur nowhere else in the repository: not in
any evidence artefact, scope descriptor, log, or script, either before or after
`9010731`, which introduced the line. They are not any nearest-rank quantile of the
committed 50-sample arrays — checked at every percentile from 50 to 100 for both legs.
The figures cannot be reconstructed from the committed evidence.

The other 18 §4 rows reconcile exactly against their cited sources. Account was checked
against `erp-arabic-bilingual-data/evidence/raw-logs/stage3/p95-measurement-wave1.json`
(`measured_baseline_p95_ms: 1.322`, `measured_bilingual_p95_ms: 1.482`,
`measured_ratio: 1.121`) — correct as written.

Gate outcome does not change: `1.2477` and `1.3327` both sit inside the Tier 2B `1.50x`
band and under the `1.50 ms` absolute ceiling. The defect is that the record disagrees
with its evidence — which is the one guarantee §4 exists to give.

### 1.2 §7 misstates the Department protocol

§7 binds `department-p95-measurement.json` as *Department master (`n=100` convergent
mean)*. The file records `samples: 50`, `warmup: 5` and
`statistic: nearest-rank P95 over interleaved samples; median = mean of middle two for
even n`. There is no `n=100` run and no convergent mean anywhere in it. The artefact has
exactly one committed version (`9404021`), always `0.654 / 0.816`.

---

## 2. Scope

### A. Corrections — `docs/ai/work-items/bilingual-performance-sla.md`

§4, Department row:

```diff
-| Department | 0.623 ms | 0.830 ms | 1.3327 | 2B | 1.50x OK | OK |
+| Department | 0.654 ms | 0.816 ms | 1.2477 | 2B | 1.50x OK | OK |
```

Tier and both gates are recomputed from the corrected figures rather than copied over:
baseline `0.654 < 1.0` → Tier 2B; relative `0.816 / 0.654 = 1.2477 <= 1.50` → OK;
absolute `0.816 <= 1.50` → OK. All three verdict cells remain as written.

§7, Department binding:

```diff
-| `bilingual-department-master/evidence/department-p95-measurement.json` | Department master (`n=100` convergent mean) |
+| `bilingual-department-master/evidence/department-p95-measurement.json` | Department master (`n=50` interleaved nearest-rank P95) |
```

### B. What must not change

- §1, §2, §3, §5, §6 — untouched.
- The other 18 §4 rows — byte-identical. Each verified against its cited source before
  this work item made any edit.
- The other ten §7 bindings — byte-identical, each verified:

| Binding | Verified protocol |
|---|---|
| Account (`stage3/p95-measurement-wave1.json`) | `n=100` min-of-rounds, `txt=CT-RP3-` — §7's `n=100` claim is correct |
| BOQ Header, BOQ Structure | `n=100`, 5-round min-of-rounds — correct as written |
| 16 wave/master artefacts | `n=50`, interleaved nearest-rank P95 — §7 makes no sample-width claim for these |

### C. Reconciliation evidence — `evidence/`

So the check is repeatable rather than asserted:

- `evidence/scripts/reconcile_adr_vs_evidence.py` — parses every §4 table row, locates
  its source artefact across all work-item evidence trees (including nested
  `raw-logs/` paths), recomputes ratio from the artefact, reports mismatches
- `evidence/reconciliation.log` — captured output of the final run against the corrected
  ADR: 19/19 rows sourced, `mismatched: 0`, `unsourced: 0`, `RESULT: PASS`
- `evidence/regression-matrix.log` — the final run of the canonical 133-test matrix
  (11 modules), all green
- `evidence/guard-module-observation.log` — the `construction.tests.test_bilingual_service`
  run and the `git diff` evidence that its single failure is pre-existing (§3 item 7)
- `evidence/MANIFEST.json` — digests of the above, the corrected ADR, and this SCOPE

---

## 3. Findings recorded, NOT fixed here

Owner selected the factual correction only. These surfaced from the same reconciliation
and each needs its own decision. Recorded so they are not lost.

1. **§4 mixes three measurement protocols.** 16 rows are interleaved nearest-rank P95 at
   `n=50`; 2 rows (BOQ Header, BOQ Structure) are min-of-rounds at `n=100` over five
   rounds; 1 row (Account) is min-of-rounds at `n=100` with `txt=CT-RP3-`. §5.3 states
   *"an `n=50` measurement cannot decide a 1.15x bound at this latency"*, yet 16 rows
   rest on `n=50`. Partly mitigated: those 16 are Tier 2B, judged against the looser
   `1.50x` band rather than `1.15x`.
2. **§2's additive-cost model is contradicted by §4.** §2 asserts a constant
   `~150-200 µs`. Measured overhead across the 19 rows spans `-0.228 .. +0.456 ms`; 12
   of 19 fall inside the stated band, 7 outside. BOQ Header (`-0.207`) and BOQ Structure
   (`-0.228`) are negative, and §4 now displays them with no explanation. Independently
   re-measured under both protocols: the negative sign is stable (`0.71-0.77x`), so it
   is a property of the query shapes, not of the statistic.
3. **The two legs issue different SQL, so the ratio is not pure overhead.** Baseline
   computes `IFNULL(1/NULLIF(LOCATE(...)))` as `_relevance` and orders by
   `_relevance DESC, idx DESC, lft/creation/modified DESC`. Governed issues plain
   `LIKE` with `ORDER BY modified DESC` and ranks in Python over `RANK_WINDOW`.
   Predicate sets differ too: governed adds `title_ar`/`title_ar_norm`, baseline adds
   `parent_structure`/`boq_header`/`project_name` and other doctype `search_fields`.
4. **Result sets diverge on production-shaped queries.** `match_sets_equal: true` in the
   artefacts holds only for the narrow `CT-*` fixture prefix both legs agree on. On real
   text: Account `Cash` -> 10/20 overlap, Item `e` -> 11/20, UOM `U` -> baseline 110
   rows vs governed 20 (governed caps at `page_length`).
5. **Account's §4 row does not reproduce today.** The canonical `n=100` protocol now
   measures `0.9208x` against a `2.475 ms` baseline, versus the recorded `1.1210x` at
   `1.322 ms`. §2's worked example `(1.322 + 0.160) / 1.322 = 1.121x` therefore no
   longer describes current behaviour.
6. **UOM tier-boundary risk — cleared by measurement.** UOM's recorded baseline
   `0.960 ms` sits 4% under the Tier 2A threshold, and a reading `>= 1.0 ms` would judge
   it at `1.15x`, where its `1.4750x` would fail. Re-measured at the canonical protocol:
   `1.254 ms -> Tier 2A`, ratio `0.668x`, passes `1.15x`. It passes under either tier,
   so §4's row is safe either way.
7. **Stale assertion in `test_bilingual_service.py`, pre-existing at `a7086ef`.**
   `TestRegistryLoadAndValidate.test_real_registry_loads_clean` asserts
   `data["doctypes"]["Item"]["state"] == "schema_installed"`. The committed registry has
   read `active` since Item was promoted for Wave 1 — where it is measured in §4 at
   `1.4524x` with `search.enabled: true`, so `active` is correct and the assertion is
   stale. Verified pre-existing rather than introduced here: this work item touches only
   `bilingual-performance-sla.md` plus new files under this work-item directory, and both
   `bilingual_registry.json` and `test_bilingual_service.py` show **0 diff** against
   `a7086ef`. It went unnoticed because the canonical 133-test regression matrix does not
   include `construction.tests.test_bilingual_service`; running that module surfaces
   exactly this one failure (37/38 pass). Fixing the assertion is a code change and is
   out of scope for a documentation-only correction — recorded here for an owner
   decision, with the run captured in `evidence/guard-module-observation.log`.

---

## 4. Invariants preserved

- `construction/services/bilingual_service.py` — 0 modified lines
- `construction/searchable_dropdown/api/search.py` — 0 modified lines
- `construction/data/bilingual/bilingual_registry.json` — 0 modified lines
- `construction/api/boq_link_queries.py`, `boq_export_service.py`, print templates,
  `orchestrator/` — 0 modified lines
- `apps/frappe`, `apps/erpnext` — 0 modified lines
- Every prior `MANIFEST.json` — 0 modified lines (this work item adds its own)
- Every other work item's evidence artefacts — 0 modified lines

## 5. Out of scope

- All six findings in §3 — recorded, each awaiting an owner decision
- Any harness authoring, measurement, or re-measurement of any master
- Any schema, registry, hook, patch, or print change
- `bilingual-boq-title-ar-wiring` — opened as a separate work item in the same session
- `Company` — governance-gated on legal/tax statutory-name review
- `narrative-unicode-policy` — `DEFERRED_PENDING_DESIGN`
- `Asset`, `Brand`, `Terms and Conditions` (deferred); `Payment Term` (candidate)

## 6. Evidence causal order

```
final test run -> capture log -> compute blob digests -> write manifest -> commit
```

Same ordering constraint as §2.E of prior descriptors. Determinism is not a substitute
for causal sequencing: the manifest must record digests of artefacts that already exist,
never predict them. The reconciliation log is captured from the final run of the script
against the corrected ADR, after §2.A is applied — so the log's `0 defects` statement
describes the committed state rather than a hoped-for one.
