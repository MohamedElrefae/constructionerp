# Scope Descriptor — bilingual-payment-terms-template-master

**Work item:** `bilingual-payment-terms-template-master`
**Branch:** `feature/bilingual-payment-terms-template-master`
**Base commit:** `2cbe71a` (18 active masters)
**Scope:** Payment Terms Template
**Date:** 2026-10-03
**Authority:** owner instruction given in session; transcribed by the agent

Master #19. Wave 3 of `ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md` §3.2 —
financial terms, mapped narrowly.

---

## 1. Starting state (verified on `v16.localhost`)

| Property | Value |
|---|---|
| `autoname` | `field:template_name` |
| `is_tree` | 0 |
| `istable` | 0 |
| live rows | 3 (`_Test Payment Term Template`, `_Test Payment Term Template 1`, `_Test Payment Term Template 3`) |
| existing custom fields | none |
| `template_name` | Data, **reqd=0**, `translatable=0` |
| `terms` | Table, **reqd=1** → `Payment Terms Template Detail` |

### 1.1 Two deviations from the classification-master precedent

The six prior classification masters (`Item Group`, `Customer Group`, `Supplier Group`,
`Territory`, `Department`, `Asset Category`) all share `reqd=1` on the English name field and
an empty child region. This doctype does not, and the scope is written around the difference.

**(a) `template_name` is schema-optional but naming-enforced.**

`reqd=0` in meta, yet `autoname: field:template_name` routes through
`frappe/model/naming.py`, which throws `"{0} is required"` when `_field_autoname` returns
empty. The field is therefore required by *naming*, not by *schema*.

Consequence for the invariant: identity still holds for every live row — `name ==
template_name` in all 3 — but the guarantee is weaker than Asset Category's, because an
API path that sets an explicit `name` alongside an empty `template_name` would produce
`name != template_name` without violating schema validation. The pilot test asserts the
invariant over the naming path and records this distinction rather than presenting it as
schema-enforced.

**(b) `terms` is a mandatory child table.**

A parent cannot be saved without at least one `Payment Terms Template Detail` row, each
needing `invoice_portion` (Float, reqd) and `due_date_based_on` (Select, reqd), plus a
`payment_term` Link. Every pilot fixture therefore writes child rows as a mechanical
necessity — child rows that carry narrative `description` text and are themselves
out of scope for mapping. Fixture construction is in-scope for the test file; the child
schema is not in scope for the registry.

## 2. Scope

### A. Schema — idempotent patch `v9_10`

`construction/patches/v9_10/add_payment_terms_template_arabic_fields.py`, mirroring `v9_9`.

| Field | Properties |
|---|---|
| `template_name_ar` | Data, `insert_after` = `template_name`, `translatable=0` |
| `template_name_ar_norm` | Data, `hidden=1`, `read_only=1`, `no_copy=1`, `translatable=0` |

`execute()` idempotent with backfill; `revert()` removes both. Registered in
`construction/patches.txt` after `v9_9`.

### B. Registry

| Key | Value |
|---|---|
| `state` | `schema_installed` (promoted after the suite passes — §2.J) |
| `english_field` | `template_name` |
| `arabic_field` | `template_name_ar` |
| `norm_field` | `template_name_ar_norm` |
| `code_field` | `null` |
| `identity_field` | `name` |
| `search.fields` | `["template_name", "template_name_ar"]` |
| `tree.enabled` | `false` |

### C. Hooks

Attach `enforce_bilingual_arabic_policy` to `validate` for `Payment Terms Template` in
`construction/hooks.py`.

### D. Identity invariant

`name` is derived from `template_name`, so Arabic must never reach `name`.
`enforce_bilingual_arabic_policy` satisfies this; §1.1(a) records the weaker guarantee.

### E. Explicitly excluded

| Excluded | Reason |
|---|---|
| `Payment Terms Template Detail` | Child table. Carries contractual narrative (`description`, Small Text) and financial rows (`invoice_portion`, `due_date_based_on`), not a name. Deferred to `narrative-unicode-policy` for the text and excluded as a child table for the rest. **4 live rows across all 3 parents — actively in use**, which makes it a stronger deferral candidate than an empty child table: `Asset Category Account` had none. |
| `Payment Term` | Separate standalone doctype, not a child. `autoname: field:payment_term_name`, 4 live rows (`_Test COD`, `_Test EONM`, `_Test N30`, `_Test N30 1`). Unmapped in this cycle; its `description` (Small Text) is deferred under `narrative-unicode-policy`, and its name field is out of scope here by owner instruction. Candidate for a future cycle, not architecturally blocked. |
| `allocate_payment_based_on_payment_terms` | Check control, not a name. |
| Narrative fields generally | `narrative-unicode-policy` (`DEFERRED_PENDING_DESIGN`), committed at `2cbe71a`. |

### F. Zero service edits

`construction/services/bilingual_service.py` and
`construction/searchable_dropdown/api/search.py` must have **zero** modified lines against
`2cbe71a`. Also untouched: `boq_export_service.py`, print templates, `orchestrator/`,
vendor sources. Nineteenth consecutive candidate asserting the invariant.

### G. Tests

`construction/tests/test_bilingual_payment_terms_template_pilot.py`:

- Patch idempotency and reversibility.
- Fixture creates a parent **with a required detail row**, then tears both down — proving
  fixture cleanup does not orphan child rows.
- `get_mapping` resolves `norm_field`; fail-closed on a missing declared field.
- Server-authoritative norm derivation; poisoned `template_name_ar_norm` overwritten.
- Bidi control rejection on `template_name_ar`.
- Identity invariant over the naming path: empty `template_name` raises via `autoname`
  (the §1.1(a) behaviour), Arabic write leaves `name` unchanged, and `rename_doc`
  preserves both Arabic fields.
- Search normalisation across Alef / Taa Marbuta / tatweel variants.
- Guard test asserting `bilingual_service.py` and `search.py` are byte-identical to
  `2cbe71a`.

### H. Data-quality note

All 3 live parents are ERPNext `_Test*` fixtures, and all 4 child rows hang off them.
Unlike `Asset Category`'s `Computers` / `Equipment`, none is business configuration. Search
measurement will rest entirely on synthetic fixtures — thinner than `Employee` (3 rows) and
`Task` (3 rows with hierarchy). Recorded so latency figures are not read as representing
production `Payment Terms Template` volume.

### I. Evidence causal order

```
final pilot test run -> capture log -> compute blob digests -> write manifest -> commit
```

No step reordered. Determinism is not a substitute for causal sequencing.

### J. State gate

`Payment Terms Template` remains `schema_installed` through the candidate. Promotion to
`active` requires the suite to pass.

## 3. Invariants preserved

- `bilingual_service.py` / `search.py`: 0 modified lines
- `boq_export_service.py` / print templates: 0 modified lines
- `apps/frappe` / `apps/erpnext`: 0 modified lines
- `orchestrator/`: 0 modified lines
- `erp-arabic-bilingual-data` evidence: 0 modified lines
- `narrative-unicode-policy` SCOPE: 0 modified lines

## 4. Out of scope

- `Payment Terms Template Detail` (child; narrative deferred)
- `Payment Term` (separate doctype; candidate for a later cycle)
- Any modification under `orchestrator/` or vendor sources
- Any modification to the print subsystem
- Promotion of any registry state to `active`
- `Company` (governance-gated on legal/tax statutory-name review)
- Activation of `narrative-unicode-policy` design
