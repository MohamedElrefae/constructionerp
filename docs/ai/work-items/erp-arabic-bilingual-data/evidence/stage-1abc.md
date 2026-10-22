# Stages 1A/1B/1C — Builder evidence (2026-09-04, TARGET_SITE=v16.localhost)

## 1A — Searchable-dropdown defensive projection

- Regression test `test_missing_optional_field_does_not_empty_valid_search` added to
  `construction/searchable_dropdown/tests/test_search_api.py`.
- Live probe DISPROVED the suspected failure: `frappe.get_list("Account", ...,
  fields=[...,"account_name_ar"])` returns rows (unknown SELECT fields dropped by
  framework), exit 0 — no silent `[]` on this Frappe version.
- Hardening applied anyway in `construction/searchable_dropdown/api/search.py`:
  `effective_fields` resolved once via `get_meta().has_field()` and shared by OR
  conditions, SELECT projection, and `_format_label`.
- Results: `test_search_api` 13/13 OK; `test_integration` 6/6 OK (exit 0).

## 1B — Account.account_name_ar schema

- New idempotent patch `construction/patches/v8_8/add_account_arabic_name_field.py`,
  registered in `construction/patches.txt`. Data / visible / `translatable=0` /
  `insert_after=account_name` / no index. ERPNext `account.json` untouched. No values set.
- Executed on test site via `bench --site v16.localhost execute ...execute` (exit 0);
  `tabAccount` now ends with `account_name_ar`.
- New `construction/tests/test_bilingual_account_schema.py`: 5/5 OK —
  field definition, DB column, meta after cache refresh, double-execute idempotency,
  Arabic-only write leaves `name`/`account_name` unchanged (test value cleaned up).

## 1C — Screenshot/common UI containment (code only)

- `tabTranslation` query: 5/6 labels exist (`Desktop`, `Workspaces`, `Edit Sidebar`,
  `Toggle Theme`, `Toggle Full Width`) as `ct_app=frappe`, Pending catalog rows,
  empty `translated_text`. `Typography Settings`: 0 rows — extraction gap.
- Ownership: `Typography Settings` is Construction-owned
  (`construction/public/js/typography_settings.js`, `__()`-wrapped) but absent from
  Construction `ar.po`. Fixed by appending the msgid with source reference
  (msgstr left empty — proposal, not translation). Vendor `.po` files untouched.
- `sync_translation_catalog(apps=["construction"], dry_run=False)` → created 1 row;
  verified `Typography Settings / ct_app=construction / Pending / catalog entry`.
- RELEASE GATE BLOCKED (stop gate 8): all six rows Pending; quorum
  (Pending→Linguistic Reviewed→Domain Reviewed→QA Passed→Released) requires named
  A1/A2/A3 reviewers. Builder proposed/released no Arabic text. Fresh-Arabic-session
  rendering proof is pending that human release.
