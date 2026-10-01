# Scope Descriptor — bilingual-wave1-masters-phase2

**Work item:** `bilingual-wave1-masters-phase2`
**Branch:** `feature/bilingual-wave1-masters` (continues Phase 1; not merged to `develop`)
**Base commit:** `81af417deda3566956ed3f25bc1463f55088d1ea` (Phase 1 implementation)
**Scope:** Cost Center, Warehouse, Project bilingual enablement
**Date:** 2026-10-02
**Authority:** owner instruction given in session; transcribed by the agent

Phase 2 of a two-phase programme. Its primary objective is to prove the Phase 1
generalization: **zero modifications to `bilingual_service.py` or `search.py`**.

---

## 1. Starting state (verified on `v16.localhost`)

| DocType | registry state | `is_tree` | Arabic field | `_norm` | rows |
|---|---|---|---|---|---|
| Cost Center | `planned` | **1** | absent | absent | 47 |
| Warehouse | `planned` | **1** | absent | absent | 117 |
| Project | `planned` | 0 | absent | absent | 11 |

Cost Center and Warehouse carry zero custom fields. Project carries one unrelated field
(`branch`).

## 2. Registry corrections required before promotion

The `planned` registry entries misdescribe live schema in two ways. Both must be corrected
in the same candidate that flips state, because `get_mapping` fails closed for
`schema_installed` mappings whose declared fields are absent.

### 2.1 `code_field`

| DocType | Currently declared | Verified live schema | Correction |
|---|---|---|---|
| Cost Center | `cost_center_name` | `cost_center_number` **exists**; `cost_center_name` is the node label, not a code | → `cost_center_number` |
| Warehouse | `warehouse_code` | **absent** | → `null` |
| Project | `null` | `project_code` **absent** | stays `null` (already correct) |

Without these corrections, promoting Warehouse would raise
`ValidationError: missing code_field (warehouse_code)` at mapping resolution.

### 2.2 `tree.enabled`

Cost Center and Warehouse are `is_tree=1`. The registry asserts `false`. Set
`tree.enabled: true` for both so the mapping describes live schema honestly. Project stays
`false`.

### 2.3 State transition

`planned` → `schema_installed` for all three. Promotion to `active` remains out of scope
and requires the account-pilot P95 canary to be re-pinned under its owning work item.

## 3. Scope

### A. Schema — idempotent patch `v9_3`

`construction/patches/v9_3/add_wave1_phase2_arabic_fields.py`, mirroring `v9_2`. Six custom
fields across three doctypes:

| DocType | Display field | Norm companion |
|---|---|---|
| Cost Center | `cost_center_name_ar` | `cost_center_name_ar_norm` |
| Warehouse | `warehouse_name_ar` | `warehouse_name_ar_norm` |
| Project | `project_name_ar` | `project_name_ar_norm` |

Display fields insert after the canonical English field. Norm companions are
`hidden=1, read_only=1, no_copy=1, translatable=0`, matching `v9_2`. `execute()` is
idempotent with backfill; `revert()` removes all six. Register in `construction/patches.txt`
after `v9_2`.

### B. Registry

Apply §2.1–2.3. Declare `norm_field` for all three alongside the corrected `code_field`.

### C. Hooks

Attach `enforce_bilingual_arabic_policy` to `validate` for Cost Center, Warehouse and
Project in `construction/hooks.py`, matching the Phase 1 pattern.

### D. Tree identity invariant (non-negotiable)

Cost Center and Warehouse are trees. Their primary key `name` is referenced by
`parent_cost_center` / `parent_warehouse` and is generated from the canonical English fields:

- `CostCenter.autoname` → `get_autoname_with_number(cost_center_number, cost_center_name, company)`
- `Warehouse.autoname` → `warehouse_name + " - " + company.abbr`

Therefore:

1. `name`, `parent_cost_center`, `parent_warehouse`, `cost_center_name`, `cost_center_name_number`,
   `warehouse_name` and `warehouse_name_number` remain ASCII / language-neutral identity.
2. Arabic occupies only the display field. It is never a PK, never a parent reference, and
   never an autoname input.
3. The existing `enforce_bilingual_arabic_policy` satisfies this without modification: it
   validates and derives the Arabic fields only, and never writes to identity fields.
4. Tree-view Arabic label overlay (e.g. an `xgettext`-style children wrapper analogous to
   `get_account_tree_children`) is a **UI presentation concern outside this candidate**. It
   may be added later without altering the master data contract.

### E. Zero service edits

`construction/services/bilingual_service.py` and
`construction/searchable_dropdown/api/search.py` must have **zero** modified lines in this
candidate. The Phase 1 generalization — `norm_field` resolution in `get_mapping`, the
fail-closed loop, `enforce_bilingual_arabic_policy`, and the `ar_field and norm_field` guard
in `bilingual_or_filters` — must handle all three doctypes unmodified. A Phase 2 diff touching
either file invalidates this candidate's primary claim.

### F. Tests

New `construction/tests/test_bilingual_wave1_phase2_pilot.py`, mirroring the Phase 1 suite:

- Patch idempotency and reversibility across all six fields.
- `get_mapping` resolves `norm_field` for all three; fail-closed when a declared field is
  absent.
- Norm derivation is server-authoritative; a poisoned `_norm` is overwritten.
- Bidi control rejection on each Arabic field.
- **Tree identity invariant:** after writing Arabic to a Cost Center and Warehouse node,
  `name` and `parent_*` are unchanged; `rename_doc` preserves Arabic and norm keys.
- Search normalization matches Alef/tatweel variants for all three.
- A guard test asserting `bilingual_service.py` and `search.py` are byte-identical to their
  `81af417` blobs.

### G. State gate

All three remain `schema_installed`. No promotion to `active` in this candidate.

## 4. Out of scope

- Any change under `orchestrator/`.
- Any modification to `apps/frappe` or `apps/erpnext`.
- Any modification to `bilingual_service.py` or `search.py` (§E).
- Tree-view Arabic label overlay.
- Promotion of any registry state to `active`.
- Arabic value population or backfill of business data.
- Re-pinning the Stage-3 P95 canary (owned by `erp-arabic-bilingual-data`).
- Merge to `develop`; Wave 1 presents a single candidate at completion.
