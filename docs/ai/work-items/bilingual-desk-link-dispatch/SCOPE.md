# Scope Descriptor — bilingual-desk-link-dispatch

**Work item:** `bilingual-desk-link-dispatch`
**Branch:** `develop`
**Base commit:** `4341542`
**Date:** 2026-10-04
**Status:** `COMPLETE` — A1–A6 dispatch live, 19-module / 234-test matrix, all four P95 cases compliant
**Authority:** owner lane selection in session (Option A — Desk Link dispatch), under Plan §3.2;
decision **A6** approved in session after the A3 shape was measured non-compliant (§10)
**Scope:** Tier 4 — make Arabic typeable into **standard desk Link fields** end to end, using the
already-proven backend (23 registered masters), without editing `apps/frappe`, `apps/erpnext`,
the D5 code triad, or any client JavaScript.

---

## 1. The gap this closes

Tiers 1–3 shipped and are proven: server-authoritative normalization, Unicode/BiDi rejection,
the Two-Tier SLA, 23 masters registered `active`, a zero-diff transactional sidecar, and an
18-module / 217-test matrix. None of that is reachable by a human being:

- A stock desk Link control invokes `method: "frappe.desk.search.search_link"`
  (`frappe/public/js/frappe/form/controls/link.js:474`, `frappe/public/js/frappe/db.js:135`).
- That RPC resolves through `frappe.handler.execute_cmd` →
  `frappe.override_whitelisted_method(cmd)` (`frappe/handler.py:67`) and
  `frappe/api/v2.py:36`, and it searches **English columns only**.
- Our bilingual search is reachable only through our own endpoints and the `searchable_dropdown`
  wrapper, which is not the mechanism a stock Link field uses.

Consequence: every Arabic lookup in a standard form is currently a dead end, so the whole
Tier 1–3 investment shows **zero customer-visible value** in daily desk use.

## 2. Defect D4 — two independent defects, both dormant

Recorded in `docs/ai/work-items/search-query-convention/SCOPE.md` §1; neither has ever fired
because no custom query is registered anywhere (`standard_queries` appears nowhere in this app).

- **D4a — positional argument shift.** `search_widget` invokes a custom query as
  `frappe.call(query, doctype, txt, searchfield, start, page_length, filters, as_dict=…, …)`.
  `frappe.call` re-binds **kwargs only** (`frappe/__init__.py:1122-1129`); positional slots are
  never re-bound. Calling our callee positionally therefore lands `searchfield` on `filters`,
  `start` on `page_length`, `page_length` on `search_fields`, `filters` on `display_format`.
- **D4b — return-row shape.** `search_link` ends with `build_for_autosuggest(results, doctype)`
  (`frappe/desk/search.py:59-65`), which indexes `item[0]` / `item[1:]` and therefore requires
  **tuples** (`frappe/desk/search.py:339+`). Our callees return `{"value","label","description"}`
  dicts → `KeyError: 0`.

`build_for_autosuggest` exists nowhere in this repository — it is vendor code, so the D5 triad
is not implicated.

## 3. Decisions

### A1 — mechanism: `override_whitelisted_methods` on `frappe.desk.search.search_link`

`hooks.py` already uses this vendor-respecting extension point four times
(`hooks.py:233-241`, including the governed `update_account_number` wrapper). We add:

```python
"frappe.desk.search.search_link": "construction.api.desk_link_search.search_link",
```

**Why not the `standard_queries` hook** (`frappe/desk/search.py:104-107`, the mechanism the
original §4.1 preconditions assumed): when `search_widget` receives a custom query it returns
`frappe.call(query, …)` **immediately** (`frappe/desk/search.py:112-130`), so the vendor's own
permission, filter, title-field and ordering logic is skipped entirely and our query would have
to reimplement it for English as well as Arabic. That duplicates vendor behaviour on the most
widely called search path in the product. With A1 the English path *is* the vendor function.

### A2 — no client changes, therefore no cache-buster churn

The stock Link control already posts to the overridden method, so the wiring needs **zero**
JavaScript. `scripts`/`app_include_js` are untouched and per AGENTS.md §4.4 `?v=` parameters are
bumped only for modified JS — there are none.

### A3 — dispatch, fail-closed, and the Latin gate (Arabic branch superseded by A6)

1. Mirror the vendor signature exactly, so `get_newargs` filtering behaves identically.
2. If the doctype is **not** in the registry (or the entry is not `active`): return the vendor
   result unchanged — one dict lookup, no behaviour change, no measurable cost.
3. If `txt` contains **no** Arabic characters: return the vendor result unchanged. This makes
   the non-bilingual path a literal passthrough, which is how SLA non-regression is proven.
4. ~~Otherwise: vendor rows first, then Arabic rows, de-duplicated and capped.~~ **Superseded
   by A6**: the A3 merge shape was implemented, measured, and found non-compliant on the
   Arabic path (§10); it survives only as the documented fallback for queries the vendor must
   own (A6.3).

Arabic rows must satisfy `build_for_autosuggest`, so the dispatcher converts dicts → tuples and
the vendor formatter is reused for both halves; we never hand-write autosuggest shapes.

### A4 — permissions

Our bilingual query uses `frappe.get_list`
(`construction/searchable_dropdown/api/search.py:151,166,279`), which enforces role and user
permissions, unlike the vendor default's hand-written SQL (`frappe/desk/search.py:219`). The
dispatcher must never fall back to `frappe.get_list`, and `ignore_user_permissions` must keep
being validated by the vendor path (`validate_ignore_user_permissions`,
`frappe/desk/search.py:254+)` rather than being re-implemented.

### A5 — one tuple-conversion boundary

`as_autosuggest_rows` is the single place dict rows become tuples, used by the master dispatcher
and by the transactional sidecar rows, so neither path can reach `build_for_autosuggest`
unconverted (D4b). The sidecar module itself stays unedited (its JS consumer is unchanged).

### A6 — Arabic queries skip the vendor baseline (owner-approved amendment)

**Problem.** The A3 shape (vendor baseline, then merge) pays for *two* searches and cannot fit
the universal 1.50 ms ceiling: measured **1.789 ms / 2.5412×** on Company and
**2.505 ms / 1.9374×** on UOM (§10, runs 1–2), while the Latin path stayed compliant.

**Rule.** For an Arabic query on an `active` registry entry, the registry half runs *alone*
over a plan built by `arabic_plan()`:

1. **Vendor fields folded in.** `vendor_search_fields(doctype)` reproduces both vendor match
   shapes — the SQL `or_filters` set (`frappe/desk/search.py:169-179`: `name` + title field +
   search fields) and the standard field list a translated doctype is regex-filtered over
   (`frappe/desk/search.py:321-336`, `227-236`) — and travels as `search_fields`, which
   `searchable_link_search` already unions with the registry fields in its single `get_list`.
   This is what makes the skip lossless: a probe over all 23 entries showed the registry
   `search.fields` alone covers the vendor set for only **13/23** doctypes, so folding closes
   the other 10 (BOQ Header/Structure, Cost Center, Customer, Customer Group, Item, Item Group,
   Project, Supplier, Territory) with **no registry edit**.
2. **Vendor constraints mirrored.** `include_disabled` is honoured and stripped, and the
   endpoint's `enabled = 1` / `disabled != 1` filters (`frappe/desk/search.py:181-185`) are
   re-applied when the doctype has those columns, so a disabled Warehouse/Account/Item cannot
   reappear through the Arabic path.
3. **Documented fallbacks — the vendor owns the result, no merge:**
   - `query` set (custom search) or no Arabic → passthrough (A3.2–A3.3).
   - registry miss / unreadable → passthrough, fail-closed (A3.2).
   - explicit `searchfield` → vendor result returned unchanged; an Arabic merge could not be
     restricted to that one field, and broadening it would violate the client's field scope.
   - filters the registry half cannot apply faithfully (list-shaped tuples, unparseable JSON)
     → vendor result returned unchanged; injecting unfiltered Arabic rows would be *looser*
     than the query asked for.
   - `ignore_user_permissions` set → vendor call first (its A4 validation must run), then the
     registry half merges; those rows are role-permission checked, so the union is no broader
     than the validated vendor result.
4. **Latency hygiene.** `_registry_data()` memoizes the registry parse request-scoped with the
   same mtime/size signature check as `bilingual_service.get_registry`, keyed by the loader
   function object so the fail-closed patch tests still consult their patched loader (§10 run 4
   shows why: without it Company sat at 1.5561×).

Ranking on the Arabic path is the registry's (relevance + modified), as in Tier 3; the Latin
path keeps vendor relevance ordering unchanged.

## 4. Preconditions recorded in `search-query-convention/SCOPE.md` §4 — disposition

| # | Recorded precondition | How this item satisfies it |
|---|---|---|
| 1 | Dispatcher whose signature is the canonical `search_widget` positional order, delegating to `searchable_link_search` **by keyword**, extracting `search_fields`/`display_format` from `filters` | Satisfied: the dispatcher takes `(doctype, txt, searchfield, start, page_length, filters, *, as_dict, reference_doctype, ignore_user_permissions, link_fieldname)` — exactly the slots `search_widget` sends — and re-binds everything by keyword. Config is read from `filters` when the client supplies it, otherwise from `bilingual_registry.json`. |
| 2 | Fix D4b: return tuples; the transactional sidecar has the same shape issue | Satisfied: the dispatcher returns tuples, and the sidecar's dict rows are routed through the same conversion helper so neither path can reach `build_for_autosuggest` unconverted. |
| 3 | Register config files and bump `?v=` | **Not applicable under A1/A2** — no JS file is added or modified. Recorded rather than silently dropped. |
| 4 | Test through the genuine entry point, not the callee | Satisfied: tests exercise `frappe.handler.execute_cmd("frappe.desk.search.search_link", …)` (the RPC the browser actually uses), assert the hook binding resolves to our dotted path, and unit-test the dispatcher in canonical positional order. Direct callee calls alone are explicitly insufficient. |
| 5 | Re-run the canonical matrix and re-pin every affected manifest | Satisfied: matrix re-run captured as evidence (19 modules / 234 tests); every manifest pinning `hooks.py` or the matrix script is re-pinned with an `amendments[]` entry and a matching SCOPE note. |

## 5. Invariants preserved

- **D5 code triad at 0 diff**: `construction/services/bilingual_service.py`,
  `construction/searchable_dropdown/api/search.py`, and `bilingual_registry.json` are inputs to
  this work item, not outputs. `searchable_link_search` is called, never edited;
  `construction/services/bilingual_registry.py` is read (and memoized around), never edited.
- **Vendor boundary**: no file under `apps/frappe` or `apps/erpnext` is modified.
- **No JS changes** (A2), hence no `?v=` bumps.
- **Registry is not modified**: the 23-master registry keeps its role as the single source of
  truth for which doctypes are bilingual; this item only *consumes* it. A6 needs no
  `search.fields` growth because the vendor fields are folded in at query time.
- **Two-Tier SLA non-regression**: the English path is a literal passthrough (A3.3) and the
  Arabic path is measured with the established harness (5 rounds × n=100, min-of-rounds
  nearest-rank P95) against the same tier ceilings — all four cases compliant (§9, §10).
- **Authorization**: no path may return rows the requesting user cannot read (A4); the registry
  half fail-closes to an empty result for a user without read permission.

## 6. Tests

`construction/tests/test_bilingual_desk_link_dispatch.py` — **17/17 OK**:

- Hook binding resolves to the dispatcher; registry-miss and unreadable-registry return vendor
  output unchanged (fail-closed); non-`active` state returns vendor output unchanged.
- Canonical positional call (simulating `search_widget`'s exact slot order) re-binds correctly —
  the executable proof that D4a cannot fire.
- Dict → tuple conversion accepted by the real `build_for_autosuggest`, including transactional
  sidecar rows — the executable proof that D4b cannot fire.
- Genuine entry point via `handler.execute_cmd` for an Arabic query and for a Latin query.
- Latin-query passthrough is byte-identical to vendor output; unregistered doctype likewise.
- **A6**: the vendor baseline is *not* invoked for an Arabic query and *is* invoked for Latin
  and unregistered queries (spy on the module-level vendor import).
- **A6**: the folded `search_fields` reach the registry half exactly as
  `vendor_search_fields("Item")` computes them (name, item_name, description, item_group,
  customer_code).
- **A6**: `enabled`/`disabled` constraints are mirrored (UOM `enabled = 1`, Account
  `disabled != 1`).
- **A6 end-to-end**: an Item matched only through `Item.description` — a field the registry does
  not declare — is returned by the stock endpoint *and* by the Arabic path.
- **A6 fallbacks**: explicit `searchfield` and list-shaped filters keep the vendor result
  unchanged (no broadening merge).
- **Permission (AGENTS.md §4.7)**: a no-role user gets an empty result through the Arabic path
  while the same query returns rows for Administrator (the triad fail-closes
  `PermissionError` to `[]` at `search.py:220`).
- Registry, matrix, reconciler, digests — the established evidence pipeline (§9).

## 7. Out of scope

- Tier 5A financial report wrappers and Tier 5B production data population.
- Transaction doctypes (excluded from the table registry by `bilingual-wave2b-transactions`;
  the sidecar remains their mechanism).
- `search-query-convention` D4 itself is not "fixed" in vendor code — it is **made unreachable**
  by design. The latent defect record stays authoritative for any future custom-query wiring.
- Any `bilingual_registry.json`, triad, or client-script change.

## 8. Evidence causal order

final test run → capture log (`2>&1`) → `git add -f` the `.log` → compute SHA-256 digests →
`evidence/MANIFEST.json` → commit. Verify against `git show HEAD:<path>` (or `:path` for the
staged index), never via `os.walk`.

---

## 9. Results (2026-10-04, evidence pinned in `evidence/MANIFEST.json`)

| Check | Result |
|---|---|
| Pilot module `test_bilingual_desk_link_dispatch` | **17/17 OK** |
| Regression matrix `run_bilingual_regression_matrix.sh` | **234/234 across 19 modules** |
| ADR vs evidence reconciler | **19/19 PASS** |
| Invariant guard (D5 split) | code diad byte-identical to 7 refs; registry untouched (23 masters, 0 diff); `test_transaction_link_search` **20/20** |
| Hook binding | `override_whitelisted_method("frappe.desk.search.search_link")` → `construction.api.desk_link_search.search_link` |
| Latin passthrough (A3.3) | vendor result object returned unchanged on both doctype classes (identity asserted in-test; P95 ratio 0.9771× Company / 0.9822× UOM) |
| P95 / two-tier SLA (confirmation run) | **all four cases compliant**: Arabic Company 0.732 → 0.927 ms (**1.2664×**), Arabic UOM 1.306 → 1.207 ms (**0.9242×**), Latin Company **0.9771×**, Latin UOM **0.9822×**; worst absolute 1.382 ms ≤ 1.50 ms |
| A6 vendor skip | Arabic query → 0 vendor calls; Latin/unregistered → vendor called (spy) |
| A6 field folding | Item `description`-only match returned by both endpoints (superset proven end-to-end) |
| A6 constraint mirroring | UOM `enabled = 1`, Account `disabled != 1` present in the registry query filters |
| A6 fallbacks | `searchfield` and list-filters → vendor result byte-identical (no broadening) |
| Non-admin permission | no-role user → `[]`; Administrator control → rows |
| Site migration | none — no patch, no schema change; registry not modified |
| Cleanup | 0 leftover UOM, Company and Item fixtures after every run |

## 10. Latency disclosure — every run, nothing discarded

| # | Artefact | Shape | Headline | Verdict |
|---|---|---|---|---|
| 1 | `desk-link-p95-pre-a6-run.log` | A3, 2 cases (UOM only) | Arabic 1.9441× / 2.537 ms; Latin 1.0149× | Arabic **NON-COMPLIANT** → prompted A6 |
| 2 | `desk-link-p95-pre-a6-confirm.log` | A3, 4 cases | Arabic Company 2.5412× / 1.789 ms; Arabic UOM 1.9374× / 2.505 ms; Latin compliant | Arabic **NON-COMPLIANT** on both doctype classes → owner approved A6 |
| 3 | `registry-only-candidate.log` | decision input: A6 cost if adopted | 0.722× / 0.878 ms, subset contract held | COMPLIANT if adopted |
| 4 | `desk-link-p95-post-a6-pre-memo-run.log` | A6 without the registry memo | Arabic Company 1.5561× / 1.192 ms (absolute OK, ratio over); others compliant | motivated `_registry_data()` memo |
| 5 | `desk-link-p95-run.log` | A6 + memo, first run | 1.2554× / 0.9031× / 1.0458× / 1.0319× | all four compliant |
| 6 | `desk-link-p95-confirm.log` | A6 + memo, **authoritative** | 1.2664× / 0.9242× / 0.9771× / 0.9822× | all four compliant; JSON below is this run |

Method for every run: 5 rounds × n=100 interleaved samples, alternating order, 5 warmups per
round, GC paused in the timed region, min-of-rounds nearest-rank P95, Tier 2A ≥ 1.0 ms ⇒ ≤1.15×
otherwise Tier 2B ≤1.50×, universal ceiling ≤1.50 ms. `desk-link-p95-measurement.json` holds the
confirmation run with all five per-round P95 values per side, both match sets, and the code
hashes of `desk_link_search.py`, `hooks.py`, the triad and the registry.

Supporting evidence: `registry-field-coverage-probe.log` / `.json` (13/23 coverage that A6's
field folding closes) and `registry-only-candidate.log` / `.json` (decision input).

## 11. Implementation notes (worth carrying forward)

- The stock endpoint's `filters.append([doctype, "enabled", "=", 1])` at
  `frappe/desk/search.py:181-185` is reached through `meta.get("fields", {…default…})`, which is
  truthy for every doctype — the vendor *always* appends both constraints and relies on
  `strict=False` to drop them where the columns do not exist. Mirroring must therefore key on
  `meta.has_field(...)`, not on the vendor's apparent condition.
- `searchable_link_search` fail-closes `frappe.PermissionError` to `[]`
  (`search.py:220-221`) while re-raising `ValidationError`; the permission test asserts the
  observable outcome (no rows leak) rather than the exception type.
- UOM, Item Group, Customer Group, Supplier Group and Territory are `translated_doctype`, so the
  vendor path there is *fetch-all + Python regex* rather than SQL `LIKE`; folding
  `get_std_fields_list` into `search_fields` covers that shape too, and it is also why UOM's
  baseline (~1.3 ms) is heavier than an ordinary doctype's (~0.7 ms).

---

## 12. Amendments (post-completion)

### 12.1 Re-pin by bilingual-financial-reports (2026-10-04)

Digests are recorded as `amendments[]` entries in `evidence/MANIFEST.json`;
this work item's own evidence logs are unchanged.

| Artefact | Why it moved |
|---|---|
| `construction/hooks.py` | living file; `Account` `doc_events` mapping-cache bust hooks added — `on_update` / `on_trash` / `after_rename` → `construction.services.report_bilingual_extension.bust_account_mapping_cache` (R7, `bilingual-financial-reports`) |
| `scripts/run_bilingual_regression_matrix.sh` | shared runner expanded to **21 modules / 258 tests** (`test_stage4_report_extension`, `test_stage7_bilingual_reports`) |
