# Scope Descriptor — bilingual-wave2a-classification-masters

**Work item:** `bilingual-wave2a-classification-masters`
**Branch:** new worktree from `feature/bilingual-wave1-masters` (`dc71b56`)
**Scope:** Item Group, Customer Group, Supplier Group, Territory, UOM
**Date:** 2026-10-02
**Authority:** owner instruction given in session; transcribed by the agent

Wave 2a. Wave 2b (transactional line-item documents) is explicitly deferred to its own
design cycle.

---

## 1. Purpose

Wave 1 established that the bilingual framework generalises: Phase 2 shipped three masters
with **zero** modified lines in `bilingual_service.py` and `search.py`, enforced by
`test_zero_service_edits_guard`. Wave 2a re-tests that claim on five structurally identical
classification masters. The classification and measurement hierarchy of the Wave 1 business
masters is currently half-localised: `Item` is bilingual but `Item Group` and `UOM` are not;
`Customer` is bilingual but `Customer Group` and `Territory` are not; `Supplier` is
bilingual but `Supplier Group` is not.

## 2. Starting state (verified on `v16.localhost`)

| DocType | in registry | `is_tree` | autoname | parent | canonical field | required | customs | rows |
|---|---|---|---|---|---|---|---|---|
| Item Group | no | 1 | `field:item_group_name` | `parent_item_group` | `item_group_name` | yes | 0 | 19 |
| Customer Group | no | 1 | `field:customer_group_name` | `parent_customer_group` | `customer_group_name` | yes | 0 | 7 |
| Supplier Group | no | 1 | `field:supplier_group_name` | `parent_supplier_group` | `supplier_group_name` | yes | 0 | 9 |
| Territory | no | 1 | `field:territory_name` | `parent_territory` | `territory_name` | yes | 0 | 9 |
| UOM | no | 0 | `field:uom_name` | — | `uom_name` | yes | 0 | 253 |

None are present in `bilingual_registry.json`. All have zero custom fields, a required
canonical English name field, and `autoname: field:<name>`.

## 3. Field naming

| DocType | Canonical English | Arabic display | Normalized key |
|---|---|---|---|
| Item Group | `item_group_name` | `item_group_name_ar` | `item_group_name_ar_norm` |
| Customer Group | `customer_group_name` | `customer_group_name_ar` | `customer_group_name_ar_norm` |
| Supplier Group | `supplier_group_name` | `supplier_group_name_ar` | `supplier_group_name_ar_norm` |
| Territory | `territory_name` | `territory_name_ar` | `territory_name_ar_norm` |
| UOM | `uom_name` | `uom_name_ar` | `uom_name_ar_norm` |

## 4. Scope

### A. Schema — idempotent patch `v9_4`

`construction/patches/v9_4/add_wave2a_classification_arabic_fields.py`, mirroring
`v9_2`/`v9_3`. Ten custom fields: five Arabic display fields (`insert_after` the canonical
English field, `translatable=0`) and five normalized keys (`hidden=1, read_only=1,
no_copy=1, translatable=0`). `execute()` idempotent with backfill; `revert()` removes all
ten. Register in `construction/patches.txt` after `v9_3`.

### B. Registry

Add entries for all five with `state: schema_installed`, `english_field`, `arabic_field`,
`norm_field`, `search.fields`, `tree.enabled`, and `code_field` per §5.

### C. Hooks

Attach `enforce_bilingual_arabic_policy` to `validate` for all five in
`construction/hooks.py`.

### D. Tree identity invariant

Non-negotiable, carried from Wave 1 Phase 2 §3.D:

1. `name` and the `parent_*` pointer remain the canonical English value. All four trees use
   `autoname: field:<name>`, so the PK **is** the English string — Arabic must never reach
   it.
2. Arabic occupies only the display field. It is never a PK, never a parent reference, and
   never an autoname input.
3. The existing `enforce_bilingual_arabic_policy` satisfies this without modification.

### E. Zero service edits

`bilingual_service.py` and `search.py` must have **zero** modified lines. Any edit
invalidates this candidate's primary claim.

### F. Tests

`construction/tests/test_bilingual_wave2a_pilot.py`, mirroring the Wave 1 Phase 2 suite:

- Patch idempotency and reversibility across all ten fields.
- `get_mapping` resolves `norm_field` for all five; fail-closed on a missing declared field.
- Server-authoritative norm derivation; poisoned `_norm` overwritten.
- Bidi control rejection on each Arabic field.
- **Tree identity invariant:** after writing Arabic, `name` and `parent_*` unchanged;
  `rename_doc` preserves Arabic and norm keys for all four trees and UOM.
- Search normalisation matches Alef/tatweel/diacritics for all five.
- Local P95 measurement for all five via the existing `measure_wave1_p95.py` harness,
  generalised. Absolute P95 expected sub-1.5 ms; ratios recorded with **no gate rule
  applied or claimed**.
- Guard test asserting `bilingual_service.py` and `search.py` are byte-identical to their
  Wave 1 blobs.

### G. State gate

All five remain `schema_installed` through this candidate. Promotion to `active` requires the
test suite to pass, matching the Wave 1 precedent (promoted in a separate commit).

## 5. `code_field` determination

Unlike Wave 1 Phase 2, where `Warehouse.code_field` had to become `null` and
`Cost Center` gained `cost_center_number`, these five have **no separate code column**:
verified, the only other `Data` field on each of the four trees is absent entirely. `UOM`
has `symbol` and `common_code`.

| DocType | `code_field` | rationale |
|---|---|---|
| Item Group | `null` | no separate code field exists |
| Customer Group | `null` | same |
| Supplier Group | `null` | same |
| Territory | `null` | same |
| UOM | `common_code` | exists as a `Data` field |

## 6. Out of scope

- Any change under `orchestrator/`.
- Any modification to `apps/frappe` or `apps/erpnext`.
- Any modification to `bilingual_service.py` or `search.py` (§E).
- **Employee** — excluded deliberately. It is `is_tree=1` but its PK is a `naming_series`
  key rather than `employee_name`, its English field is not required, it is
  security-scoped (leave/permission, `reports_to` org hierarchy), and its live data is
  3 `_Test` rows with a null hierarchy. Its identity and permission model needs its own
  design pass.
- `Brand` (2 rows, 0 references), `Item Attribute`, `Terms and Conditions` — too little
  live usage to prove behaviour.
- Wave 2b transactional documents: Sales Order, Purchase Receipt, Material Request,
  Journal Entry. Parent/child line-item bilingual design deferred.
- Arabic value population or backfill of business data.
- Any modification to `erp-arabic-bilingual-data` evidence, including the Stage-3 P95
  artifact.
