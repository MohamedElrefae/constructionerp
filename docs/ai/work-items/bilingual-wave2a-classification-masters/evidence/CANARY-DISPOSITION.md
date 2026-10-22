# Wave 2a Canary Disposition — Classification Masters P95 Artifact

**Work item:** `bilingual-wave2a-classification-masters`
**Branch:** `feature/bilingual-wave2a-classification`
**Base commit:** `dc71b56` (from `feature/bilingual-wave1-masters`)
**Date:** 2026-10-02
**Status:** `ACCEPTED_KNOWN_MISMATCH` — Wave 2a latency MEASURED and accepted as a documented trade-off
**Authority:** owner instruction given in session; transcribed by the agent

---

## 1. Summary

The Account bilingual search canary suite (`construction/tests/test_bilingual_account_pilot.py`) remains at **52 / 53**, where `test_comparative_p95_artifact_bound_and_gate` fails on the intentional code-hash mismatch originating from Wave 1 commit `81af417` (generalization of norm-field resolution), while `test_comparative_p95_live_measurement_is_balanced_and_bound` passes.

Wave 1 test suites continue to pass at **16 / 16** (`test_bilingual_wave1_pilot.py`: 8/8, `test_bilingual_wave1_phase2_pilot.py`: 8/8).
The Wave 2a test suite (`test_bilingual_wave2a_pilot.py`) passes at **8 / 8**, including the mechanically enforced zero-service-edits guard.

## 2. Wave 2a search latency profile: measured and accepted trade-off

Comparative search latency across all five Wave 2a classification masters was measured in
`wave2a-p95-measurement.json` (work-item-local; **no gate rule applied**).

| DocType | baseline P95 | governed P95 | ratio | median base → governed | match sets | leftover |
|---|---|---|---|---|---|---|
| Customer Group | 0.444 ms | 0.617 ms | 1.3896 | 0.422 → 0.599 ms | equal (12/12) | 0 |
| Item Group | 0.440 ms | 0.645 ms | 1.4659 | 0.425 → 0.608 ms | equal (12/12) | 0 |
| Supplier Group | 0.438 ms | 0.620 ms | 1.4155 | 0.420 → 0.598 ms | equal (12/12) | 0 |
| Territory | 0.445 ms | 0.622 ms | 1.3978 | 0.420 → 0.597 ms | equal (12/12) | 0 |
| UOM | 0.960 ms | 1.416 ms | 1.4750 | 0.559 → 0.802 ms | equal (12/12) | 0 |

- **Ratios:** 1.389–1.475× against a bare, unranked `frappe.get_list` baseline (matching the 1.31–1.45× profile observed in Wave 1).
- **Canonical rule:** none meets the 1.10× rule owned by `erp-arabic-bilingual-data`, which this artifact does not apply or claim.
- **Absolute ceiling:** all four classification trees demonstrate sub-0.65 ms P95 (0.617–0.645 ms); UOM (with 253 live database records) demonstrates 1.416 ms P95, comfortably below the predicted 1.5 ms ceiling.
- **Disposition:** the delta is the legitimate cost of Python-level relevance ranking (exact > prefix > substring) and bilingual label formatting over an unranked SQL query. **Accepted as a documented architectural trade-off.**
- All five doctypes report `match_sets_equal: true` and zero leftover fixtures.

## 3. Invariant verification

1. **Zero service edits:**
   `bilingual_service.py` and `search.py` have **0 diff lines** against base commit `dc71b56` (and commit `81af417`). Mechanically asserted by `test_zero_service_edits_guard`.
2. **Tree identity invariant:**
   All four tree doctypes (`Item Group`, `Customer Group`, `Supplier Group`, `Territory`) maintain canonical English strings as primary keys (`autoname: field:<name>`) and in `parent_*` tree links. Arabic resides strictly in `*_ar`. Mechanically asserted by `test_tree_identity_invariant_and_rename_preservation`.
3. **Vendor immutability:**
   Zero changes under `apps/frappe` or `apps/erpnext`.
4. **Orchestrator immutability:**
   Zero changes under `orchestrator/`.
5. **Foreign evidence isolation:**
   Zero changes under `docs/ai/work-items/erp-arabic-bilingual-data/` or `docs/ai/work-items/bilingual-wave1-masters/`.

## 4. Disposition

1. The Account hash mismatch is **accepted as a known, intentional consequence** of commit `81af417`.
2. Wave 2a classification master latency is **MEASURED** (§2) and **accepted as a documented architectural trade-off**.
3. All five Wave 2a masters remain registered at `state: schema_installed`. Promotion to `active` remains a separate owner-authorized declaration step.
