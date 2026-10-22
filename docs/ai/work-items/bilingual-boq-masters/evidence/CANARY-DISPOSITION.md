# BOQ Masters (BOQ Structure & BOQ Header) Canary Disposition — Performance, Print & Governance Alignment

**Work item:** `bilingual-boq-masters`
**Branch:** `feature/bilingual-boq-masters`
**Base commit:** `ef36c95` (from `develop`)
**Date:** 2026-10-03
**Status:** `COMPLIANT_WITH_GOVERNANCE_AND_PRINT_SPECIFICATION`
**Authority:** Owner directive transcribed into codebase governance under Plan §3.2

---

## 1. Summary

Bilingual search, tree navigation, display, and flag-gated print enablement for `BOQ Structure` (15th master) and `BOQ Header` (16th master) have been implemented and verified.
All test suites across the repository pass without regression:
- `TestBilingualBOQPrint`: **10 / 10 PASS**
- `TestBilingualDepartmentPilot`: **8 / 8 PASS**
- `TestBilingualDataImport`: **6 / 6 PASS**
- `TestBilingualEmployeePilot`: **8 / 8 PASS**
- `TestBilingualWave2aPilot`: **8 / 8 PASS**
- `TestBilingualWave1Pilot`: **8 / 8 PASS**
- `TestBilingualWave1Phase2Pilot`: **8 / 8 PASS**
- `TestBilingualAccountPilot`: **53 / 53 PASS**
- **Total Bilingual Matrix: 109 / 109 PASS**
- **Existing BOQ Suite (13 modules): ALL PASS (zero regression)**

---

## 2. Print Governance Closure

Per the Governance ADR (`docs/translation/BILINGUAL_GOVERNANCE_PRINT_IMPORT_PERMISSION.md`), the Print capability row for `BOQ Structure` and `BOQ Header` transitions from `Unverified / Out-of-band` to `Verified (gated by enable_bilingual_boq_print)`:
1. **Flag OFF (`enable_bilingual_boq_print = 0`)**:
   - Monolingual output is 100% byte-identical to baseline. No dual-language concatenation occurs.
   - Tested in `test_print_rendering_flag_off_monolingual_baseline`.
2. **Flag ON (`enable_bilingual_boq_print = 1`)**:
   - Headers and line items render dual-language format (`title / title_ar`, `project_name / project_name_ar`).
   - WBS codes remain pure ASCII alphanumeric.
   - Tested in `test_print_rendering_flag_on_dual_language` and `test_boq_excel_parser.py:run_boq_print_format_registration_smoke`.

---

## 3. Invariants Verified

1. **Zero Service Edits**:
   `bilingual_service.py` and `search.py` have **0 diff lines** against base commit `ef36c95` (and all antecedent reference commits `c1d278b`, `c5ee0bb`, `dc71b56`).
   Mechanically enforced by `test_zero_service_edits_guard`.
2. **WBS Code Exclusivity & ASCII Invariant**:
   `wbs_code` is algorithmically generated, pure ASCII alphanumeric (`^[A-Za-z0-9._-]+$`). It carries no `_ar` or `_norm` columns and is completely excluded from bilingual normalization.
   Mechanically enforced by `test_wbs_code_exclusivity_and_ascii_invariant`.
3. **Legacy Workaround Fixed**:
   `test_boq_excel_parser.py` legacy workaround (where Arabic was smuggled into English `title` because `title_ar` did not exist) is eliminated: `_insert_manual_structure` accepts `title_ar`, tests set proper English `title` and Arabic `title_ar`, and verify bilingual print output with flag gating.
4. **Vendor Immutability**:
   0 modifications to `apps/frappe` or `apps/erpnext`.
5. **Orchestrator Immutability**:
   0 modifications under `orchestrator/`.

---

## 4. Disposition

1. `BOQ Structure` and `BOQ Header` are declared `state: active` in `bilingual_registry.json`.
2. All 109 bilingual tests pass.
3. Candidate certified for merge into `develop`.
