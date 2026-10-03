# Scope Descriptor — bilingual-boq-title-ar-wiring

**Work item:** `bilingual-boq-title-ar-wiring`
**Branch:** `feature/bilingual-boq-title-ar-wiring`
**Base commit:** `0f5be0d` (develop clean, ADR corrected, 19/19 rows reconcile)
**Scope:** `boq_link_queries.get_boq_headers` / `get_boq_structures`, `ct_link_control.js`, `hooks.py`
**Date:** 2026-10-03
**Status:** APPROVED — Decision §3.1 Option A (Search-only) approved, Decision §3.2 (search_fields untouched) approved
**Authority:** owner instruction given in session; transcribed by the agent

Follow-up recorded by `bilingual-boq-p95-measurement` §1.2 and re-opened by the owner in
the session that corrected the ADR. **Implemented and merged at `dfeace3`**: the two
cascade endpoints now search `title_ar` (raw `txt`) and `title_ar_norm` (normalized
`txt`), `hooks.py` cache buster advanced to `?v=17`, and the `ct_link_control.js`
header comment corrected to match the code.

---

## 1. Finding

BOQ's production dropdown never reaches the bilingual union. Registry declares
`search.enabled: true` with `title_ar` in `search.fields` for both BOQ doctypes, but the
UI routes around `searchable_link_search`:

```javascript
// construction/public/js/overrides/ct_link_control.js:445-447
if (fieldname === "boq_header") {
    args.query = "construction.api.boq_link_queries.get_boq_headers";
} else if (fieldname === "boq_structure") {
    args.query = "construction.api.boq_link_queries.get_boq_structures";
}
```

Those endpoints search only:

| Endpoint | SELECT | LIKE disjunction |
|---|---|---|
| `get_boq_headers` | `h.name, h.title, h.project` | `h.name`, `h.title`, `h.project` |
| `get_boq_structures` | `s.name, s.title, s.wbs_code` | `s.name`, `s.title`, `s.wbs_code` |

`title_ar` appears nowhere in the 575-line `boq_link_queries.py`. Native
`frappe.desk.search.search_link` also cannot find it: `title_ar` is in **no** doctype's
`search_fields`, and native search builds `or_filters` only from `name` +
`title_field` + `search_fields`.

### 1.1 Schema is already in place

| Property | BOQ Header | BOQ Structure |
|---|---|---|
| `title_ar` | present (patch `v9_7`) | present (patch `v9_7`) |
| `title_ar_norm` | present | present |
| registry `norm_field` | `title_ar_norm` | `title_ar_norm` |
| registry `search.enabled` | `true` | `true` |
| registry `search.fields` | `title`, `title_ar` | `wbs_code`, `title`, `title_ar` |
| rows with `title_ar` populated | **0 / 23** | **0 / 59** |
| `show_title_field_in_link` | **1** | **1** |

`title_ar_norm` is derived server-authoritatively on every save by the bilingual hook
(`bilingual_service.py`, norm derivation on `before_validate`), so a `title_ar_norm`
predicate stays correct without client cooperation.

### 1.2 Empirically, all three paths miss Arabic today

Arabic fragment `كميات` against the live site:

```
native  frappe.desk.search.search_link   -> 0 hits
governed searchable_link_search          -> 0 hits
production get_boq_structures            -> 0 hits
production get_boq_headers               -> 0 hits
```

All four are 0 because §1.1 leaves no Arabic BOQ data — not because the predicates are
wrong. The contrast that *does* discriminate is Account, the one master with real Arabic:

```
Arabic fragment "استخدامات"
  native search_link        -> 0 hits
  governed link_search      -> 1 hit
  native control, English   -> 10 hits
```

**Consequence for this work item:** every test must create its own bilingual fixtures and
tear them down. There is no production Arabic to assert against.

### 1.3 Callers

Seven call sites pass these two endpoints as `args.query`, all through
`frappe.desk.search.search_link`:

| File | Lines |
|---|---|
| `public/js/overrides/ct_link_control.js` | 445, 447 |
| `public/js/boq_filters.js` | 409, 416, 439, 449 |
| `construction/doctype/boq_item/boq_item.js` | 30, 37 |
| `construction/doctype/boq_item_stage/boq_item_stage.js` | 132, 141 |

### 1.4 Column-shape constraint — appending is safe, inserting is not

Rows returned by these endpoints pass through `frappe.desk.search.build_for_autosuggest`
(search.py:340-367). Because both BOQ doctypes have `show_title_field_in_link = 1`, the
**first** branch runs:

```python
label = item[1]                       # 2nd SELECT column becomes the dropdown label
item[1] = item[0]                     # then overwritten with name
autosuggest_row = {"value": item[0], "description": to_string(item[1:]), "label": label}
```

- `value` is always column 0 (`name`).
- `label` is always column 1 (`title`) — **unless** column 1 is replaced by the endpoint.
- Everything from column 2 onward is flattened into `description`.

Therefore **appending** `title_ar` as the last column is inert to `value`/`label` and
lands Arabic in `description`. **Inserting** it at position 1 would silently switch the
dropdown label to Arabic for every session, including English. The JS consumers read
`item.value` / `item.label` by name (`ct_link_control.js:554-555`), not by index.

---

## 2. Proposed design

### A. Search-only wiring (Approved)

1. `get_boq_headers` — extend the `WHERE` disjunction and `SELECT`:

```sql
SELECT h.name, h.title, h.project, h.title_ar
...
AND (h.name LIKE %(txt)s OR h.title LIKE %(txt)s
     OR h.project LIKE %(txt)s
     OR h.title_ar LIKE %(txt)s OR h.title_ar_norm LIKE %(norm_txt)s)
```

2. `get_boq_structures` — likewise, with `s.title_ar` / `s.title_ar_norm` alongside
   `s.wbs_code`.

3. Normalized bind parameter — add `values["norm_txt"] = f"%{normalize_arabic(txt or '')}%"`
   via read-only import of `normalize_arabic` from `construction.services.bilingual_service`.
   This ensures Alef-variants, tatweel, and diacritics match correctly against the normalized
   column (matching `search.py:136`).

4. `ct_link_control.js` header comment — correct the claim that it *"Auto-applies
   SearchableDropdownEnhancer to all Link fields on every page"*. It does not call
   `searchable_link_search`; it builds its own dropdown over native `search_link`, with
   the BOQ cascade override above.

5. Cache-buster bump — bump `hooks.py:158` from `ct_link_control.js?v=16` to `?v=17`
   per AGENTS.md §4.4.

All SQL stays parameterized per AGENTS.md §4.1.

**What this delivers:** Arabic-named BOQ rows become findable from the BOQ dropdown.
**What it does not deliver:** the dropdown *label* stays the English `title`; Arabic only
appears in `description`.

### B. Bilingual label (Deferred per Decision §3.1)

To prefer the Arabic label for Arabic sessions — matching
`searchable_link_search._format_label` behaviour — the endpoint would have to return the
localised title at **column 1**, computed server-side from `frappe.local.lang` and
falling back to `title` when `title_ar` is empty. That inverts §1.4's safety property:
column 1 then drives `label`, so the fallback chain has to be exact or English sessions
show Arabic.

---

## 3. Decisions settled

### 3.1 Search-only, or bilingual label too?

| | Option A | Option B |
|---|---|---|
| Arabic becomes searchable | yes | yes |
| Arabic shown as dropdown label | no (`description` only) | yes, for Arabic sessions |
| Touches `boq_link_queries` label contract | no | yes — column 1 becomes localised |
| Risk | low | must reproduce `_format_label`'s fallback chain |
| Duplicates governed logic | no | partially |

**Decision: Option A approved by owner.** Search-only wiring preserves dropdown label stability and column contracts.

### 3.2 Should `title_ar` also be added to doctype `search_fields`?

Adding it to the doctype JSON would make **native** `search_link` find Arabic everywhere,
not just through these two endpoints — closing the gap for any caller that does not go
through the cascade. **But it changes the baseline leg** of the Two-Tier SLA: §4's BOQ
Header (`0.851 ms`) and BOQ Structure (`0.985 ms`) rows were measured against native
`search_link` with today's `search_fields`, and the predicate set is part of what makes
that baseline what it is. Changing it invalidates both rows and forces re-measurement.

**Decision: Untouched (approved by owner).** Doctype `search_fields` remains untouched; baselines for BOQ Header and BOQ Structure remain valid without re-measurement. Any future doctype search_fields change is deferred to a separate work item paired with a §4 re-measurement.

### 3.3 Is backfilling `title_ar` in scope?

0/23 and 0/59 rows carry Arabic. Without data the change is unobservable in production
until someone enters Arabic titles.

**Recommendation: no.** Translation/backfill is a data task (`erp-arabic-bilingual-data`
territory), not a wiring task. Tests use fixtures per §1.2.

---

## 4. Tests

`construction/tests/test_boq_link_queries.py` (9 existing tests) must stay green, plus:

- Arabic fragment with a synthetic bilingual fixture → `get_boq_headers` /
  `get_boq_structures` return the row; without the wiring they do not (fail-closed proof)
- English fragment → identical results before and after the change
- column shape: returned row length and, through `build_for_autosuggest`, `value` and
  `label` unchanged for both endpoints
- `title_ar_norm` predicate matches an Alef-variant / tatweel / diacritic form of the
  query while the raw `title_ar` would not
- fixtures torn down; `cleanup.leftover == 0`
- `ct_link_control.js` comment change has no behavioural test — it is a comment

## 5. Invariants preserved

- `construction/services/bilingual_service.py` — 0 modified lines
- `construction/searchable_dropdown/api/search.py` — 0 modified lines
- `bilingual_registry.json` — 0 modified lines (registry already declares the fields)
- Doctype JSON `search_fields` — 0 modified lines (§3.2 deliberately separate)
- `bilingual-performance-sla.md` §4 — untouched unless §3.2 is chosen
- `apps/frappe`, `apps/erpnext` — 0 modified lines
- All foreign work-item `MANIFEST.json` files — 0 modified lines

## 6. Out of scope

- §3.2 — doctype `search_fields` change and the §4 re-measurement it forces
- §3.3 — Arabic data backfill
- Any schema, hook, patch, or print change
- Promotion/demotion of any registry state
- `Company` (legal/tax gated), `narrative-unicode-policy` (`DEFERRED_PENDING_DESIGN`)
- The six structural findings recorded in
  `bilingual-adr-evidence-correction/SCOPE.md` §3

## 7. Evidence causal order

```
final test run -> capture log -> compute blob digests -> write manifest -> commit
```

Same ordering constraint as prior descriptors. Because §1.2 leaves no Arabic data, the
test log is the only proof the wiring works; it must be captured after the final
implementation edit and before the manifest is written.

---

## 8. Amendments (post-completion)

`evidence/MANIFEST.json` pins `construction/hooks.py`, a **living** artefact. The
pin was correct at completion and last matched at `46aa201`; it went stale when
later work items legitimately modified `hooks.py`. Re-pinned on 2026-10-03 so that
repository-wide `HEAD` verification passes. The work item's own evidence
(`test_boq_link_queries.log`, `regression-matrix.log`, `reconciliation.log`) is
unchanged.

| Artefact | Last matching pin | Why it moved |
|---|---|---|
| `construction/hooks.py` | `5d1376f64dd0ec365e809d308140087e80c43cce1645681e6cabfa6e817f1fc3` (at `46aa201`) | narrative-sanitizer hooks, `?v=1` cache buster for `searchable_dropdown.js`, and other legitimate `hooks.py` changes |

Use `git show 46aa201:construction/hooks.py` to recover the completion-time bytes.

### 8.1 Re-pin by `bilingual-brand-master` (2026-10-03)

| Artefact | Re-pinned from | Why it moved |
|---|---|---|
| `construction/hooks.py` | `71e3b32963525a46f7e2e83d42871eb158415e53d51ba4ec523ca760235a5c72` | living file; `Brand` `doc_events` registration added (finding F1 in `bilingual-brand-master/SCOPE.md` §3.1) |

New digest recorded as an `amendments[]` entry in `evidence/MANIFEST.json`; this work
item's evidence logs are unchanged.


### 8.2 Re-pin by `bilingual-asset-master` (2026-10-04)

Digests are recorded as `amendments[]` entries in `evidence/MANIFEST.json`;
this work item's own evidence logs are unchanged.

| Artefact | Why it moved |
|---|---|
| `construction/hooks.py` | living file; `Asset` `doc_events` single-hook registration added (F1, `bilingual-asset-master/SCOPE.md` §2.3) |
