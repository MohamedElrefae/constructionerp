# Scope & Architectural Decision — bilingual-wave2b-transactions

**Work item:** `bilingual-wave2b-transactions`
**Branch:** `feature/bilingual-wave2b-transactions`
**Base commit:** `6c67e33` (Wave 2a tip)
**Date:** 2026-10-02
**Authority:** owner instruction given in session; transcribed by the agent
**Outcome:** `EXCLUDED_FROM_REGISTRY` — architectural boundary recorded, no code changed

This work item is a **scope determination**, not an implementation. No candidate payload, no
registry entries, no patch, no service changes.

---

## 1. Question

Twelve masters are `active` in the bilingual registry. Should the four transactional
doctypes be added?

| DocType | submittable | autoname | parent rows | child rows | child doctype |
|---|---|---|---|---|---|
| Sales Order | yes | `naming_series:` | 476 | 476 | Sales Order Item |
| Purchase Receipt | yes | `naming_series:` | 476 | 952 | Purchase Receipt Item |
| Material Request | yes | `naming_series:` | 628 | 942 | Material Request Item |
| Journal Entry | yes | `naming_series:` | 1430 | 2860 | Journal Entry Account |

## 2. Determination

**All four are deliberately excluded from the row-level bilingual registry.** Each is a
transaction with no Arabic identity of its own. The registry's contract is that every entry
names real Arabic columns physically present on that doctype; these have none, and the two
alternatives that could manufacture one are both rejected below.

## 3. Why they cannot be registered — mechanical proof

### 3.1 Schema validation

`construction/services/bilingual_registry.py` validates every entry, regardless of state:

```python
for field in ("english_field", "arabic_field", "identity_field"):
    if not isinstance(cfg.get(field), str) or not cfg[field]:
        errors.append(f"bilingual-registry-field: {dt}.{field} missing")
```

### 3.2 Fail-closed resolution

`construction/services/bilingual_service.py:get_mapping` resolves each declared field against
live metadata and refuses a mapping whose fields are absent:

```python
if field and (field == "name" or meta.has_field(field)):
    resolved[key] = field
else:
    resolved[key] = None
    if field:
        missing.append(f"{key} ({field})")
if missing and cfg.get("state") in ("active", "schema_installed"):
    raise frappe.ValidationError(...)
```

### 3.3 The three-way bind

There is no registry state meaning "this doctype has no Arabic column of its own." Every
option fails:

| Attempt | Result |
|---|---|
| omit or null `arabic_field` | `bilingual-registry-field: Sales Order.arabic_field missing` |
| declare `customer_name_ar` | `ValidationError: missing arabic_field (customer_name_ar)` — not a local column |
| declare `"name"` | passes both checks, but presents an ASCII naming series (`SO-2026-00012`) as the Arabic field |

The third is the dangerous one: it would satisfy every mechanical check while misrepresenting
`SO-2026-00012` as Arabic. It is rejected on correctness grounds, not on validation grounds.

## 4. Why linked-party search cannot be delivered by configuration

`searchable_link_search` executes against a single table with no relational join.

**Search.** `or_filters` compile to predicates on the target table. An Arabic string held in
`tabCustomer.customer_name_ar` cannot be matched against `tabSales Order`, which stores only
the foreign-key literal. No registry entry expresses a join.

**Display.** `_format_label` (`search.py:231`) builds the label from `doc.get(field)` on the
local row:

```python
format_kwargs = {"name": doc.get("name", "")}
for field in search_fields:
    format_kwargs[field] = doc.get(field, "")
```

`doc.get("customer")` yields the FK literal, never the linked record's Arabic name.

Verified live party links, all pointing at masters that are already `active`: `Sales Order` →
`customer`, `cost_center`, `project`, `set_warehouse`, `company`; `Purchase Receipt` →
`supplier`, `cost_center`, `project`, `set_warehouse`, `company`; `Material Request` →
`customer`, `set_from_warehouse`, `set_warehouse`, `company`; `Journal Entry` → `company`,
`stock_asset_account`, `periodic_entry_difference_account`.

## 5. Rejected alternative A — denormalise the party Arabic field

Adding a cached `customer_name_ar` / `supplier_name_ar` column to the transaction parents
would give each an authentic `arabic_field` and satisfy the contract.

**Rejected.** It introduces a cache of another row's data onto a `naming_series` submittable
document, with three defects:

1. **Staleness without invalidation.** Nothing re-propagates when `Customer.customer_name_ar`
   changes. A transaction would print a customer name that is no longer true.
2. **Submission-time mutation.** Re-deriving on every save conflicts with Frappe's `docstatus`
   locking. Deriving only in Draft leaves submitted rows carrying whatever was true at
   submission; deriving on submission needs `allow_on_submit` semantics designed for a
   derived cache.
3. **Audit risk.** A stale Arabic party name on a posted Sales Order or Journal Entry is
   wrong data on a financial record.

**Principle applied:** wrong Arabic on a financial document is a worse failure than absent
Arabic. A missing feature degrades gracefully; a stale cache asserts something false.

## 6. Rejected alternative B — service-layer link resolution

Extending `search.py` to follow Link fields and project the linked doctype's `arabic_field`
would deliver genuine Arabic transaction search and display.

**Rejected for this work item.** It is the first real modification to
`bilingual_service.py` / `search.py`, ending the zero-service-edit invariant that has held
across two waves and twelve masters. It also changes the query shape inside `RANK_WINDOW` — a
single-table bound whose overflow semantics were deliberately made loud rather than silently
truncating. Extending it to a multi-table path requires that semantics be redesigned, not
retrofitted.

Vendor-layer resolution via ERPNext DocType `get_query` is unavailable: `apps/erpnext` is
immutable under the vendor boundary.

## 7. Preserved path forward

If transactional bilingual search is later required, **Option B above** is the route, and it
must be scoped as its own work item with all three of the following:

1. **An RFC renegotiating the zero-service-edit invariant**, stating plainly that the invariant
   ends and why the trade is worth it.
2. **A deliberate `RANK_WINDOW` design** covering multi-table candidate windows and the
   overflow-throw contract, with tests for the boundary.
3. **A matched-set equivalence proof** per doctype, as recorded in
   `bilingual-wave1-masters/evidence/wave1-p95-measurement.json`.

Transactional bilingual search is therefore **deferred, not rejected**.

## 8. What users get today

A user searching in Arabic into a Customer, Supplier, Item Group, Cost Center, Project or
Warehouse dropdown gets Arabic results, because those twelve masters are `active` with
normalized search keys. Transactions are reachable from those parties through standard
filtered lists.

The capability that is **not** delivered is typing Arabic directly into a transaction search
box. That gap is recorded in §7 rather than papered over.

## 9. Invariants preserved

- `bilingual_service.py` and `search.py`: **0 modified lines** versus `6c67e33`
- `apps/frappe` / `apps/erpnext`: **0 modified lines**
- `orchestrator/`: **0 modified lines**
- `erp-arabic-bilingual-data` evidence: **0 modified lines**
- Registry: unchanged; twelve masters remain `active`

## 10. Line-item Arabic (`description_ar`) — explicitly out of scope

Deferred with the transactional question and for an additional reason. Line-item `description`
is **narrative** text, not an **identity** field. The registry's `unicode_policy` already
distinguishes them:

- `identity_rejected` — forbids C0/C1/DEL, bidi embedding/override/isolate (U+202A–U+202E,
  U+2066–U+2069), LRM, RLM, ALM
- `narrative_rejected` — forbids C0/DEL and bidi embedding/override/isolate, but **permits**
  LRM/RLM as documented direction marks

Narrative policy has never been exercised; all twelve active masters use identity fields.
Introducing it requires its own design pass covering whether Arabic line descriptions are
inherited from `Item.item_name_ar` or user-authored, and the submittable lifecycle questions
in §5. Journal Entry Account additionally has no `description` field at all.
