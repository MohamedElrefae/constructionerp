# Scope Descriptor — bilingual-asset-category-master

**Work item:** `bilingual-asset-category-master`
**Branch:** `feature/bilingual-asset-category-master`
**Base commit:** `04dfe35` (17 active masters)
**Scope:** Asset Category
**Date:** 2026-10-02
**Authority:** owner instruction given in session; transcribed by the agent

Master #18. Wave 2 of `ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md` §3.2, which
specifies: existing name field, matching Arabic name field, asset ID / item link, with the
note *"Validate fixed-asset reports."*

---

## 1. Starting state (verified on `v16.localhost`)

| Property | Value |
|---|---|
| `autoname` | `field:asset_category_name` |
| `is_tree` | 0 |
| `istable` | 0 |
| live rows | 2 (`Computers`, `Equipment`) |
| existing custom fields | none |
| `asset_category_name` | Data, required |
| child tables | `Asset Finance Book`, `Asset Category Account` |

This is the same shape as the five classification masters already shipped
(`Item Group`, `Customer Group`, `Supplier Group`, `Territory`, `Department`): a required
English name field with `autoname: field:<name>`, no existing custom fields.

## 2. Scope

### A. Schema — idempotent patch `v9_9`

`construction/patches/v9_9/add_asset_category_arabic_fields.py`, mirroring `v9_8`.

| Field | Properties |
|---|---|
| `asset_category_name_ar` | Data, `insert_after` = `asset_category_name`, `translatable=0` |
| `asset_category_name_ar_norm` | Data, `hidden=1`, `read_only=1`, `no_copy=1`, `translatable=0` |

`execute()` idempotent with backfill; `revert()` removes both. Registered in
`construction/patches.txt` after `v9_8`.

### B. Registry

| Key | Value |
|---|---|
| `state` | `schema_installed` |
| `english_field` | `asset_category_name` |
| `arabic_field` | `asset_category_name_ar` |
| `norm_field` | `asset_category_name_ar_norm` |
| `code_field` | `null` — no separate code column exists |
| `identity_field` | `name` |
| `search.fields` | `["asset_category_name", "asset_category_name_ar"]` |
| `tree.enabled` | `false` — `is_tree=0` |

### C. Hooks

Attach `enforce_bilingual_arabic_policy` to `validate` for `Asset Category` in
`construction/hooks.py`.

### D. Identity invariant

`name` **is** the English value (`autoname: field:asset_category_name`), so the ASCII-PK
invariant applies exactly as for the classification trees: Arabic must never reach `name`.
`enforce_bilingual_arabic_policy` satisfies this unmodified.

### E. Explicitly excluded

| Excluded | Reason |
|---|---|
| `Asset` | Deferred. Zero live rows and zero linked `Item` references, so any search measurement would rest entirely on synthetic fixtures — thinner than the `Employee` (3 rows) and `Task` (3 rows with hierarchy) precedents. Beyond thin data, ERPNext `Asset` is a financial capitalisation entity requiring a linked `is_fixed_asset=1` Item, depreciation accounts and finance-book settings; treating it as a name master would blur the Wave 2b transactional boundary. |
| `Asset Category Account` | Child table. Numeric GL account rows, not a name master. Same shape as `BOQ Item` under `BOQ Header`. |
| `Asset Finance Book` | Child table. Per-company finance configuration. |
| `status` (on Asset) | `Select` controlled vocabulary, belonging to the static translation catalog. |

`Asset` joins `Brand` and `Terms and Conditions` in the deferred ledger: doctypes whose live
usage is too thin to support a credible measurement.

### F. Zero service edits

`construction/services/bilingual_service.py` and
`construction/searchable_dropdown/api/search.py` must have **zero** modified lines. Also
untouched: `boq_export_service.py` and the print templates (print is out of scope).
This is the eighteenth consecutive candidate asserting the invariant.

### G. Tests

`construction/tests/test_bilingual_asset_category_pilot.py`, mirroring the prior pattern:

- Patch idempotency and reversibility for both fields.
- `get_mapping` resolves `norm_field`; fail-closed on a missing declared field.
- Server-authoritative norm derivation; a poisoned `asset_category_name_ar_norm` is
  overwritten.
- Bidi control rejection on `asset_category_name_ar`.
- Identity invariant: after writing Arabic, `name` is unchanged; `rename_doc` preserves
  `asset_category_name_ar` and `asset_category_name_ar_norm`.
- Search normalisation across Alef / Taa Marbuta / tatweel variants.
- Guard test asserting `bilingual_service.py` and `search.py` are byte-identical to `04dfe35`.

### H. Thin-data note

Only 2 live rows exist (`Computers`, `Equipment`). Unlike `Employee` and `Task`, there is no
hierarchy or linked party to exercise. Synthetic fixtures will carry search verification, and
this is recorded so latency figures are not read as representative of production
`Asset Category` volume.

### I. Evidence causal order

Artefacts are produced in this order, with no step reordered:

```
final pilot test run -> capture log -> compute blob digests -> write manifest -> commit
```

A manifest must never be written before the log it records. Determinism is not a substitute
for causal sequencing.

### J. State gate

`Asset Category` remains `schema_installed` through this candidate. Promotion to `active`
requires the suite to pass.

## 3. Invariants preserved

- `bilingual_service.py` / `search.py`: 0 modified lines
- `boq_export_service.py` / print templates: 0 modified lines
- `apps/frappe` / `apps/erpnext`: 0 modified lines
- `orchestrator/`: 0 modified lines
- `erp-arabic-bilingual-data` evidence: 0 modified lines

## 4. Out of scope

- `Asset` (deferred; see §2.E)
- Any child table of `Asset Category`
- Any modification under `orchestrator/` or vendor sources.
- Any modification to the print subsystem.
- Promotion of any registry state to `active`.
- `Company` (governance-gated on legal/tax statutory-name review).
- `Payment Terms Template` (parent/child narrative shape; see the Wave 2b §10 deferral).
