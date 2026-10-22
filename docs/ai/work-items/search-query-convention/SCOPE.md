# Scope Descriptor — search-query-convention

**Work item:** `search-query-convention`
**Branch:** `develop`
**Status:** `DOCUMENTED` — latent defect recorded, **no application source changed**; owner decision 2026-10-03: keep dormant
**Base commit:** `db5d23e` (transactional link resolution landed, guards in place)
**Date:** 2026-10-03
**Authority:** owner directive in session after evidence review of defect D4
**Scope:** record of D4 (custom-query calling convention), its two independent defects, the
wiring audit that makes it dormant, and the preconditions for ever wiring it.

---

## 1. Finding — D4 has two independent defects

Neither is fixed here. Both are recorded because both would fire on the **first** attempt to
route a browser Link field through the master custom query.

### D4a — positional argument shift

`frappe/desk/search.py` `search_widget` invokes a custom query as:

```python
return frappe.call(query, doctype, txt, searchfield, start, page_length, filters,
                   as_dict=as_dict, reference_doctype=..., ignore_user_permissions=...,
                   link_fieldname=...)
```

`frappe.call` (`frappe/__init__.py:1122-1129`) is `fn(*args, **get_newargs(fn, kwargs))` —
**kwargs are filtered to the callee's signature, positional args are never re-bound.**
`searchable_link_search(doctype, txt, filters, page_length, search_fields, display_format, …)`
therefore receives:

| slot | `search_widget` sends | lands on | effect |
|---|---|---|---|
| 1 | `doctype` | `doctype` | ok |
| 2 | `txt` | `txt` | ok |
| 3 | `searchfield` (`'name'`) | `filters` | client filters **silently dropped** (`'name'` is not JSON → `{}`) |
| 4 | `start` (`0`) | `page_length` | clamped to **1** result |
| 5 | `page_length` (`20`) | `search_fields` | coerced to `['20']` → `effective_fields == []` |
| 6 | `filters` (dict) | `display_format` | a dict where a format string is expected |

`as_dict` has no parameter to bind to and is discarded.

### D4b — return-row shape

`search_link` unconditionally ends with `return build_for_autosuggest(results, doctype=doctype)`,
and `build_for_autosuggest` indexes `item[0]` on **tuples**. `searchable_link_search` returns
`[{"value", "label", "description"}]` dicts, so the call raises:

```
File "frappe/desk/search.py", line 62, in search_link
    return build_for_autosuggest(results, doctype=doctype)
File "frappe/desk/search.py", line 366, in build_for_autosuggest
    label = _(item[0]) if meta.translated_doctype else item[0]
KeyError: 0
```

**D4b fires even with correct keyword arguments** — fixing the argument order alone is
insufficient. Any future dispatcher must convert rows to tuples.

Evidence: `evidence/reproduce_d4.log` sections A (mapping), B (`frappe.call` semantics),
C (live `KeyError` through the genuine entry point).

---

## 2. Why it has never fired — wiring audit

Evidence: `evidence/reproduce_d4.log` section D.

- `hooks.py app_include_js` loads `utils.js` and `searchable_dropdown.js` (26 JS files scanned).
- **No loaded file instantiates the enhancer.** The only `new SearchableDropdownEnhancer`
  call sites are inside `searchable_dropdown.js` itself (its own `enhance()` helper);
  call sites outside that module: **NONE**.
- The three files that *would* wire it — `searchable_dropdown/config/{customer_supplier,
  journal_entry,sales_invoice}.js` — are registered in **no** hook list.
- `construction/searchable_dropdown/hooks.py` declares `desk_include_js` / `whitelisted_methods`
  but is an app-style hooks file Frappe **never loads** (only the app-root `construction/hooks.py`
  is read).
- Every Python caller of `searchable_link_search` is a unit/integration test or a P95 harness,
  all invoked with **keyword** arguments — which is why 171/171 matrix tests stay green.
- The live browser custom-query path belongs to `boq_link_queries.*`, whose signature is
  **canonical** (`doctype, txt, searchfield, start, page_len, filters`) and whose rows are
  **tuples** (`frappe.db.sql(...)` without `as_dict`) — both conventions respected.

Consequence: D4 is **latent**. It is not an outage, and no user-visible behaviour changes by
leaving it unfixed.

---

## 3. Decision (owner, 2026-10-03)

**Keep dormant. Document only.**

| Option | Disposition | Reason |
|---|---|---|
| 1 — canonical sidecar dispatcher | **deferred** | correct shape for the problem, but nothing calls the path; build it only alongside wiring |
| 2 — RFC amending `construction/searchable_dropdown/api/search.py` | **rejected** | would reopen ratified **D1** (`transactional-link-resolution/SCOPE.md` §3: "the zero-service-edit invariant does not end") to repair a path with no caller |

Also recorded: the transactional sidecar's client route
(`searchable_dropdown.js` `setCustomQuery()` → `search_transactions`) sits inside the same
dormant class, so it is **NOT WIRED** either — see
`transactional-link-resolution/SCOPE.md` §8. The endpoint itself is live, whitelisted, and
covered by 18/18 unit tests; only the browser path is inert.

---

## 4. Preconditions if wiring is ever approved

A later work item must satisfy **all** of:

1. Ship a dispatcher whose signature is the canonical `search_widget` positional order and
   which delegates to `searchable_link_search` by **keyword**, extracting `search_fields` /
   `display_format` from `filters`.
2. Fix **D4b** as well: return tuples (or otherwise satisfy `build_for_autosuggest`).
   The transactional sidecar has the same shape issue and must be fixed in the same pass.
3. Register the config files and bump the `?v=` cache busters (AGENTS.md §4.4).
4. Test through the genuine entry point (`frappe.desk.search.search_link`), not the callee
   directly — direct calls are exactly what hid this defect.
5. Re-run the canonical matrix and re-pin every manifest affected by the changed artefacts.

---

## 5. Invariants preserved

- **Triad at 0 diff**: `bilingual_service.py`, `search.py`, `bilingual_registry.json` untouched.
- **No application source changed** by this work item — evidence script and documentation only.
- Read-only evidence: the reproduction script opens no writes and mutates no site data.

## 6. Out of scope

- Fixing D4a or D4b (deferred, §4).
- Wiring `SearchableDropdownEnhancer` or registering `searchable_dropdown/config/*.js`.
- `Asset` / `Brand` / `Terms and Conditions` (deferred ledgers) and `Company` (GATED).

## 7. Evidence causal order

```
reproduction script -> capture log (2>&1) -> compute SHA-256 digests -> MANIFEST.json -> commit
```

`.gitignore:27` ignores `*.log` in the app repo — the log must be `git add -f`.
Verify digests against `git show HEAD:<path>`, never `os.walk`.
