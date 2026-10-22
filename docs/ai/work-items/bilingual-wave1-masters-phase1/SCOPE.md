# Scope Descriptor — bilingual-wave1-masters-phase1

**Work item:** `bilingual-wave1-masters-phase1`
**Branch:** `feature/bilingual-wave1-masters`
**Base commit:** `10887841bf887b5dac769f98633f7a1926b07bda` (fast-forward from `develop`)
**Scope:** Item, Customer, Supplier bilingual enablement
**Date:** 2026-10-01
**Authority:** owner instruction given in session; transcribed by the agent

Phase 1 of a two-phase programme. Phase 2 covers Cost Center, Warehouse and Project and is a
separate candidate.

---

## 1. Starting state (verified on `v16.localhost`)

| DocType | registry state | English | Arabic (exists) | `_norm` (exists) | rows / Arabic populated |
|---|---|---|---|---|---|
| Account | `active` | `account_name` | `account_name_ar` | `account_name_ar_norm` | 2102 / 81 |
| Item | `schema_installed` | `item_name` | `item_name_ar` | **no** | 43 / 0 |
| Customer | `schema_installed` | `customer_name` | `customer_name_in_arabic` | **no** | 12 / 0 |
| Supplier | `schema_installed` | `supplier_name` | `supplier_name_in_arabic` | **no** | 10 / 0 |
| Cost Center | `planned` | `cost_center_name` | — | — | Phase 2 |
| Warehouse | `planned` | `warehouse_name` | — | — | Phase 2 |
| Project | `planned` | `project_name` | — | — | Phase 2 |

**Counting note.** Account shows 2102 total rows with 81 Arabic values populated. An earlier
Elrefae-company-scoped query returned 86 rows / 81 populated; the company filter is therefore
not the discriminator for Arabic coverage, and the unfiltered count is used here. The
governing fact for this candidate is the delta: Account has a norm field and 81 populated
values, while Item, Customer and Supplier have neither.

Arabic fields are app-created **Custom Field** rows, not vendor `DocField` rows. Vendor
sources under `apps/frappe` and `apps/erpnext` are immutable; all schema work uses
`create_custom_field()`.

**Defect this candidate fixes.** `bilingual_service.py:66` hardcodes
`AR_NORM_FIELD = "account_name_ar_norm"`. Six call sites across `bilingual_service.py`
(lines 292, 310, 387, 767) and `searchable_dropdown/api/search.py` (lines 105, 116, 117)
consume it. For Item, Customer and Supplier `meta.has_field("account_name_ar_norm")` is
`False`, so the derived key is never written and normalized search is silently disabled.
Arabic search for Alef variants (`أ`/`إ`/`آ`/`ا`), Taa Marbuta/Haa (`ة`/`ه`) and tatweel
(`ـ`) silently misses matches. This is the parity gap Account does not have.

## 2. Scope

### A. Schema — idempotent patch

New `construction/patches/v9_2/add_wave1_arabic_norm_fields.py`, mirroring
`construction/patches/v9_1/add_account_arabic_norm_field.py` (idempotent, `revert()`,
`create_custom_field()`, hidden/read-only/no-copy, backfill-then-verify).

| DocType | Field | Label |
|---|---|---|
| Item | `item_name_ar_norm` | Item Name Arabic (Search Key) |
| Customer | `customer_name_in_arabic_norm` | Customer Name in Arabic (Search Key) |
| Supplier | `supplier_name_in_arabic_norm` | Supplier Name in Arabic (Search Key) |

Register `construction.patches.v9_2.add_wave1_arabic_norm_fields` in
`construction/patches.txt` (append after the `v9_1` line).

Zero row-level backfill is required: all three doctypes currently have zero populated Arabic
values. The backfill path must still exist and be exercised by tests against seeded rows.

### B. Registry

Add optional `norm_field` to `construction/data/bilingual/bilingual_registry.json` for Item,
Customer and Supplier, and declare `account_name_ar_norm` for Account so the mapping is
uniform and explicit rather than implied by a constant.

### C. Service generalization

1. `get_mapping` (`bilingual_service.py:152`) — extend the resolution tuple to include
   `norm_field`:
   ```python
   for key in ("english_field", "arabic_field", "code_field", "identity_field", "norm_field"):
   ```
   Fail-closed semantics apply to `norm_field` exactly as to the existing four: a mapping in
   state `active` or `schema_installed` that declares a `norm_field` absent from live
   metadata raises. `planned` mappings return `None` before this loop and are unaffected.
   An omitted or `null` `norm_field` resolves to `None` without a missing-field violation.
2. Replace all six `AR_NORM_FIELD` references with the resolved per-doctype value, including
   the write paths at lines 292 and 310 and the projection key at line 387.
3. Retire the module constant once no call site remains.
4. `searchable_dropdown/api/search.py` — consume the resolved `norm_field` rather than
   importing `AR_NORM_FIELD`.

`get_mapping` returns a memoized dict, so a resolved `norm_field` is available to every
consumer without a second metadata lookup.

### D. Behaviour

- Form identity section (`Identity / الهوية`) on all three doctypes.
- Server-side rejection of bidi control and isolate characters in identity fields, per the
  registry `unicode_policy` `identity_rejected` list.
- Server-authoritative write of the normalized key: client-supplied `_norm` values are
  overwritten, never trusted.
- Search projection across code, English, Arabic and normalized fields, preserving the
  existing ASCII-query skip for the Arabic predicate.

### E. Tests

New `construction/tests/test_bilingual_wave1_pilot.py`, mirroring
`construction/tests/test_bilingual_account_pilot.py`, and including at minimum:

- Patch idempotency: create, re-run, assert single Custom Field and no duplicate column.
- Norm derivation is server-authoritative: attempt to write a poisoned `_norm` value
  directly and assert it does not survive a subsequent governed write.
- Normalized matching: seeded Alef/Taa-Marbuta/tatweel variants match an unaccented query.
- Bidi-control rejection on each identity field.
- Form identity section presence for all three doctypes.
- Registry consistency: each mapping's declared fields exist in live metadata; a deliberately
  broken mapping raises.

### F. Registry state gate

Item, Customer and Supplier remain `schema_installed` through this candidate. Promotion to
`active` requires the full suite to pass and is out of scope here. Status follows evidence.

## 3. Out of scope

- Any change under `orchestrator/`.
- Any modification to `apps/frappe` or `apps/erpnext`.
- Cost Center, Warehouse, Project (Phase 2).
- Promotion of any registry state to `active`.
- Arabic value population or backfill of business data.
- Changes to `ar.po`, localization catalogs, or any Stage-2 evidence.

## 4. Deployment note

Because `norm_field` is fail-closed for `schema_installed` mappings, the patch must run before
the registry declares the field. Deploying the registry change without the patch raises at
mapping resolution. Sequence: patch first, then registry.
