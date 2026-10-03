# Scope Descriptor — bilingual-boq-p95-measurement

**Work item:** `bilingual-boq-p95-measurement`
**Branch:** `feature/bilingual-boq-p95-measurement`
**Base commit:** `2f74193` (19 active masters)
**Scope:** BOQ Header, BOQ Structure — Two-Tier SLA measurement only
**Date:** 2026-10-03
**Authority:** owner instruction given in session; transcribed by the agent

Closes the last two unmeasured rows in `bilingual-performance-sla.md` §4 (currently
"17 of 19 active masters"). **Measurement-only: no schema, registry, hook, print, or
service changes.** The finding in §1.2 is recorded for a follow-up work item, not
resolved here.

---

## 1. Starting state (verified on `v16.localhost`)

| Property | BOQ Header | BOQ Structure |
|---|---|---|
| rows | 23 | 59 |
| `is_tree` | 0 | **1** |
| `autoname` | `format:BOQ-{YYYY}-{####}` | `None` |
| `search_fields` (doctype JSON) | `project_name` | `parent_structure, boq_header, is_group` |
| `title_field` | `title` | `title` |
| registry `search.fields` | `title`, `title_ar` | `wbs_code`, `title`, `title_ar` |
| registry `code_field` | `null` | `wbs_code` |
| registry `tree.enabled` | `false` | `true` |
| **rows with `title_ar` populated** | **0 / 23** | **0 / 59** |
| ADR §4 tier today | `2B (prov.)` | `2B (prov.)` |

Both rows are `unmeasured` in §4 with the note *"unmeasured (print focus)"* — accurate,
because `bilingual-boq-masters` scoped print only.

## 1.1 Data quality

`title_ar` is unpopulated on every live row of both doctypes. Across all 19 active
masters only Account (81 rows), Task (1), and Warehouse (1) carry any Arabic values.

Consequence: the measurement exercises the Arabic *code path* (normalization, union,
ranking) against synthetic fixtures, not against stored Arabic BOQ titles. The harness
must create its own bilingual fixtures and tear them down. Recorded so that §4 row
figures are not read as reflecting production Arabic usage — there is none yet.

## 1.2 Finding — the BOQ UI path does not reach the bilingual union

Discovered while scoping. Recorded here because it bounds what §4's numbers mean.

BOQ link fields are routed away from `searchable_link_search`:

```javascript
// construction/public/js/overrides/ct_link_control.js:445-447
if (fieldname === "boq_header") {
    args.query = "construction.api.boq_link_queries.get_boq_headers";
} else if (fieldname === "boq_structure") {
    args.query = "construction.api.boq_link_queries.get_boq_structures";
}
```

Those endpoints search only:

| Endpoint | Columns searched |
|---|---|
| `get_boq_headers` | `h.name`, `h.title`, `h.project` |
| `get_boq_structures` | `s.name`, `s.title`, `s.wbs_code` |

`title_ar` does not appear anywhere in the 575-line `boq_link_queries.py`. Native
`frappe.desk.search.search_link` also omits it: `title_ar` is in no doctype's
`search_fields` (0 doctypes out of all construction doctypes checked), and native search
builds its `or_filters` from `name` + `title_field` + `search_fields` only.

Empirically confirmed on Account, the one master with real Arabic data:

```
Arabic fragment "استخدامات"
  native frappe.desk.search.search_link -> 0 hits
  construction...searchable_link_search -> 1 hit  (the Arabic-named account)
  native control, English "Application"  -> 10 hits
```

So for Account the governed path is the *only* path that finds Arabic. For BOQ neither
path finds it: the governed path is reachable by API but has no data (§1.1), and the
production UI path does not search `title_ar` at all.

Two observations, neither to be resolved in this work item:

1. `boq_link_control.js`'s header comment claims it *"Auto-applies
   SearchableDropdownEnhancer to all Link fields on every page"*. It does not call
   `searchable_link_search`; it builds its own dropdown over native `search_link`, with
   the BOQ cascade override above. The comment overstates reachability.
2. Registry `search.enabled: true` with `title_ar` in `search.fields` for both BOQ
   doctypes is therefore declared-but-unwired in the production BOQ dropdown.

**Follow-up required:** a work item must decide whether BOQ cascade search should union
`title_ar` (and whether `boq_link_queries` should take a normalized `title_ar_norm`
predicate), and whether `ct_link_control.js`'s comment should be corrected. Out of scope
here — changing search SQL would invalidate a "measurement-only" claim.

## 2. Scope

### A. Harness — `evidence/scripts/measure_boq_p95.py`

Mirrors the proven pattern (Asset Category, Payment Terms Template):

- `WARMUP = 5`, `SAMPLES = 50`, `PAGE_LENGTH = 20`
- alternating pair order (even baseline-first, odd bilingual-first), GC paused in the
  timed region
- nearest-rank P95 plus true median for both legs
- match-set equivalence asserted; leftover fixture count asserted `0`
- code hashes of `bilingual_service.py`, `searchable_dropdown/api/search.py`,
  `boq_link_queries.py` recorded in the output

Two legs, per doctype:

| Leg | Call |
|---|---|
| baseline | `frappe.desk.search.search_link(<doctype>, txt, page_length=20)` |
| bilingual | `searchable_link_search(<doctype>, txt, {}, 20)` |

### B. Fixtures

Synthetic bilingual rows created by the harness and deleted on exit, since §1.1 leaves no
Arabic data to measure. Must include:

- Arabic `title` values covering Alef variants, Taa Marbuta, tatweel
- for `BOQ Structure` only: a parent/child pair, because `is_tree = 1`
- a `wbs_code` value, because `code_field` is set on `BOQ Structure` and the union has
  three search fields there versus two on `BOQ Header`

### C. Tier assignment — measured, then written

Tier follows `bilingual-performance-sla.md` §2, which binds tiers to **baseline latency**:

| Condition | Tier | Gate |
|---|---|---|
| baseline `>= 1.0 ms` | 2A | `<= 1.15x`, `n=100`, min-of-rounds over five rounds |
| baseline `< 1.0 ms` | 2B | `<= 1.50x` documented, universal `<= 1.50 ms` absolute |

Both BOQ baselines are unknown — that is the point of the work item. `BOQ Header` and
`BOQ Structure` are searched over 23 and 59 rows with `title` + `name` + (`wbs_code` |
`project`), and `BOQ Structure` joins a parent self-link; the assumption that they land
sub-millisecond is currently just an assumption. **If either baseline measures
`>= 1.0 ms`, it is Tier 2A and must be re-measured at `n=100` with the min-of-rounds
method before §4 is updated.** Writing `2B` for a `>= 1.0 ms` baseline would be exactly
the provisional-to-unverified error §4 exists to eliminate.

### D. ADR update — only after measurement

`docs/ai/work-items/bilingual-performance-sla.md`:

- replace both `*unmeasured*` rows with measured baseline, governed, ratio, tier,
  relative gate, absolute gate
- retitle §4 from `17 of 19 active masters` to `19 of 19 active masters`
- drop the `(prov.)` tier markers and the `(print focus)` annotations
- add both measurement JSONs to §7 Evidence Sources

The governance capability ledger (`BILINGUAL_GOVERNANCE_PRINT_IMPORT_PERMISSION.md`)
already shows `✅ Tier 2B Bound` for both BOQ rows. **That cell is currently derived from
the provisional tier, not a measurement.** It must be corrected to match §4's measured
tier — if the measurement shows Tier 2A, the cell is wrong today.

### E. Evidence causal order

```
final measurement run -> capture output -> compute blob digests -> write manifest -> commit
```

Same ordering constraint as `§2.I` of prior descriptors. Determinism is not a substitute
for causal sequencing: the manifest must record digests of artefacts that already exist,
never predict them.

### F. Zero service edits

`construction/services/bilingual_service.py` and
`construction/searchable_dropdown/api/search.py`: **0 modified lines** against `2f74193`.
Also untouched: `boq_link_queries.py` (see §1.2 — it is the *subject* of a future work
item, not a change here), `boq_export_service.py`, print templates, `orchestrator/`,
vendor sources.

## 3. Invariants preserved

- `bilingual_service.py` / `search.py`: 0 modified lines
- `boq_link_queries.py`: 0 modified lines
- `boq_export_service.py` / print templates: 0 modified lines
- `apps/frappe` / `apps/erpnext`: 0 modified lines
- `orchestrator/`: 0 modified lines
- `erp-arabic-bilingual-data` evidence: 0 modified lines
- `bilingual_registry.json`: 0 modified lines — registry state and search fields unchanged
- All prior MANIFEST.json files: 0 modified lines (this work item adds its own)

## 4. Out of scope

- **Wiring `title_ar` into BOQ cascade search** — §1.2 follow-up, requires SQL design
- Correcting `ct_link_control.js`'s reachability comment — §1.2 follow-up
- Any schema, registry, or hook change
- Any print change
- Promotion or demotion of any registry state
- `Payment Term`, `Asset`, `Brand`, `Terms and Conditions` (deferred/candidate)
- `Company` (governance-gated on legal/tax statutory-name review)
- Activation of `narrative-unicode-policy` design
