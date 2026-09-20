# Stage 3 Implementation Plan — Bilingual Display (D2/D3 + C2/E1)

**Work item:** erp-arabic-bilingual-data
**Stage:** 3 (Bilingual registry, display resolver, account form section, localized tree)
**Status:** SUPERSEDED — audit found Stage 3 already implemented (see below); no build needed
**Author:** agent, for owner review
**Date:** 2026-09-20

> **Superseded 2026-09-20:** the post-plan audit discovered a substantially complete
> Stage 3 already present, uncommitted, in `apps/construction` on branch
> `feature/erp-arabic-bilingual-data` (registry + service, tree/form JS, hooks wiring,
> 96 passing tests, live-verified). It was committed as `0d96cdc` and merged with the
> Stage 4 work into `feature/bilingual-integration` (`13bc927`), test guard added and
> Account registry promoted (`550feca`), all pushed to origin. This plan is retained
> for its extension-point analysis only; do not implement from it.

---

## 1. Problem

Stage 4 stored the Arabic account names (`account_name_ar`, 81/81) but the application
does not display them. Live-site facts:

- `Account-account_name_ar` exists (`Data`, label `Account Name (Arabic)`), `in_list_view=0`,
  `in_standard_filter=0`, no Property Setters.
- `construction/construction/doctype/account/account.js` does not exist.
- No `Account` tree JS override is registered in `doctype_tree_js`.
- There is no shared display resolver; other DocTypes (Item, Customer, Supplier) also have
  Arabic fields that are not surfaced.

This stage makes the stored Arabic names visible, using Construction-owned extensions only
(no ERPNext/Frappe vendor edits), per plan §6 (C) and §7 (D).

## 2. Confirmed extension points (verified in source)

| Need | Hook | Evidence |
|---|---|---|
| Account form section | `doctype_js` | `construction/hooks.py:99`; ERPNext `account.js` uses `frappe.ui.form.on("Account", …)` with `refresh`, and calls `update_account_number` for safe renames |
| Locale-aware tree label | `doctype_tree_js` + tree `get_label` override | Frappe `public/js/frappe/ui/tree.js:257 get_node_label`; `get_label` bypasses the default `title + (label)` rendering that would leak the English name |
| Server display/search | new whitelisted API + service | plan §6 C2/C3 |
| Asset registration | `app_include_js`, cache `?v=` bump | `construction/hooks.py:134` |

The default tree renderer at `tree.js:261` does
`node.title + " <span class='text-muted'>(node.label)</span>"`, which is exactly why a
naive Arabic `title` still exposes the English document name. The plan requires a custom
label renderer; `get_label` is that renderer.

## 3. Deliverables

### 3.1 C1/C2 — Bilingual registry and display resolver (Python)

New files:
- `construction/services/bilingual_registry.py` — allowlisted, schema-validated mapping of
  DocType → {identity_field, english_field, arabic_field, code_field, parent_field}. Starts
  with **Account** only; `active` entries are validated against live metadata on load and
  raise on mismatch; `planned` entries (Item, Customer, Supplier) log a warning.
- `construction/services/bilingual_display.py`:
  - `get_display(doctype, name, language)` → `{value, title, title_en, title_ar, translation_missing}` per C2.
  - `resolve_many(doctype, names, language)` — single batched query (no N+1).
  - `search(doctype, txt, language, filters, limit)` — parameterized Query Builder, allowlisted fields only, Alef/Tatweel/diacritic normalization on a derived key (never stored).
  - `validate_unicode(value)` — reject bidi control chars U+202A–U+202E, U+2066–U+2069, U+200F, U+200E, U+061C.
  - Never use Arabic as the identity/FK; identity = stored `name`.

### 3.2 C3/C4 — API + linked display

New file:
- `construction/api/bilingual_api.py` (whitelisted):
  - `get_displays(doctype, names, language=None)`
  - `search(doctype, txt, language=None, filters=None)`
  - Enforces the same permission/scope rules as standard ERPNext queries (delegates to
    `frappe.has_permission`; reuses `overrides/scope_query` behaviour where applicable).

Presentation-only: these endpoints return localized titles; canonical data continues to use
stable identifiers.

### 3.3 D2 — Localized tree label

New file:
- `construction/construction/doctype/account/account_tree.js`
  - Registered in `hooks.py` `doctype_tree_js`.
  - Overrides the Account treeview `get_label` (or wraps `on_node_render`) so the rendered
    label is:
    - Arabic session: `1000 — استخدامات الأموال (الأصول)`
    - English session: `1000 — Application of Funds (Assets)`
    - Admin "Both": two lines / both names.
  - **Never** changes `node.label` / `node.value` (route identity, parent/child, drag/move).
  - Arabic cached per tree load via one `get_displays` call for the visible nodes.
  - Browser regression: route identity, expansion, balances, drag/move, `Dr`/`Cr`, mixed
    Arabic/Latin, no English leak in Arabic session, no Arabic leak in English session.

### 3.4 D3 — Account Identity form section

New file:
- `construction/construction/doctype/account/account.js`
  - Registered in `hooks.py` `doctype_js`.
  - Injects a top-level **Account Identity / هوية الحساب** section for saved non-root
    accounts: Account Number; Name (English); Name (Arabic); localized previews; translation
    completeness/status; **Edit identity** action; change reason; audit history.
  - Root accounts: remain locked per ERPNext; the section explains why (no bypass).
  - Arabic field is **read-only on the form** (owner decision); edits go through the API.
  - English name/number continue to use ERPNext's `update_account_number`; Construction must
    not bypass accounting safeguards.

### 3.5 Write path (owner decision: read-only + API)

New whitelisted endpoint:
- `set_account_name_ar(account, arabic_name, reason)`:
  - Requires `write` on Account and an explicit non-empty reason.
  - `validate_unicode` on the value (rejects bidi controls).
  - Writes only `account_name_ar` via `frappe.db.set_value(..., update_modified=False)`.
  - Never renames the document, parents, codes, or English name.
  - Records an audit row (see 3.6) and invalidates any localized-title cache.
  - Both REST and form paths validated (the form calls this API only).

### 3.6 E1 — Policy, permissions, audit

- Document rename policies: Arabic = `localized_only`; English/number = `validated_rename`
  (delegated to `update_account_number`).
- Field-level security via the read-only form + permission-checked API. If direct form write
  is ever enabled, it must use `permlevel` + matching Custom DocPerm and be tested on both
  REST and form paths.
- Audit: reuse/extend an identity-change log DocType (new `Bilingual Name Change` child or
  a Construction log) recording account, old/new Arabic, actor, reason, timestamp, and the
  originating request id.

## 4. Tests

- **Python (offline, non-Frappe-importing package):** registry validation, fallback rules
  (Arabic→English and English→Arabic), `translation_missing`, Unicode/bidi rejection,
  normalization key, batched resolution (no N+1), permission denial, scope filters, search
  allowlist.
- **Frappe integration tests (`construction/tests`):** endpoint permission matrix, write
  API audit row, no-rename invariant, root protection.
- **Browser regression (documented manual + scripted where available):** tree label per
  language, no cross-language leak, route identity stability, identity section behaviour.

## 5. Sequencing and gates

1. C1/C2 service + tests (no UI).
2. C3 API + permission/scope tests.
3. D2 tree label + browser regression.
4. D3 form section + write API + audit.
5. E1 policy/permissions documentation.
6. Owner review gate before merge/deploy. Separate authorization before any deploy.

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Tree renderer leaks English | Use `get_label` override; test English appears only in English session |
| Rename breaks ledger links | Arabic edit is `localized_only`; never call rename; invariant test |
| Permission bypass via new API | Delegate to `frappe.has_permission`; test REST + form; audit every write |
| N+1 on large trees | Batched `resolve_many`; measure before adding cache |
| Bidi/spoofing in Arabic values | `validate_unicode` rejects control chars on write |
| Vendor-drift breakage | Construction-owned files only; inventory ERPNext deltas before deploy |

## 7. Explicit non-goals (this stage)

- No report/print/CSV localization (plan C4/Stage 7, needs the extension-point spike).
- No Item/Customer/Supplier rollout (Stage 5/7); registry entries remain `planned`.
- No production deployment and no push; test-site only unless separately authorized.
- No change to the frozen Stage 4 artifacts or evidence.

## 8. Approval requested

Owner: approve this plan as the Stage 3 scope, or amend it. On approval I will implement in
the sequence above, run all suites, verify on `v16.localhost`, and record evidence. Any
deviation that expands authority (direct form writes, report overrides, production deploy)
returns for a separate decision.
