# F24 — Framework override compatibility, working-tree review (evidence)

Date: 2026-10-14 · Site: `v16rehearsal.localhost` · Framework: frappe 16.51.1 / erpnext 16.50.0
Method: source register (F24 §1-8, candidate c9e6803c) re-checked against the **current working
tree**, not only the earlier inventory — including the File hooks/download override added for
F11/F12, the BOQ permission gates as they now read, the F19 report adapters, and the new
Sidebar fixture.

## 1. `override_whitelisted_methods` (6) — signature compatibility vs installed framework

| Vendor target (installed) | Vendor signature | App override | App signature | Verdict |
|---|---|---|---|---|
| `frappe.core.doctype.user.user.switch_theme` | `(theme: str)` | `overrides/switch_theme_simple.switch_theme` | `(theme=None, theme_name=None)` | compatible superset: accepts every vendor call; `theme_name` legacy alias rejected on disagreement; Guest refused; savepoint rollback + re-raise |
| `frappe.utils.change_log.show_update_popup` | `()` | `api/theme_api.ignore_update_popup` | `()` | exact; no-op return |
| `frappe.translate.update_translations_for_source` | `(source=None, translation_dict=None)` | `api/translation_tools.update_translations_for_source_safe` | `(source=None, translation_dict=None)` | exact; System Manager only, non-destructive |
| `erpnext.accounts.doctype.account.account.update_account_number` | `(name, account_name, account_number=None, from_descendant=False)` | `services/bilingual_service.governed_rename_account` | `(name, account_name, account_number=None, reason=None, from_descendant=False)` | compatible superset: `reason` required by the wrapper (governed rename), all vendor validations preserved |
| `frappe.desk.search.search_link` | `(doctype, txt, query=None, filters=None, page_length=10, searchfield=None, reference_doctype=None, ignore_user_permissions=False, *, link_fieldname=None)` | `api/desk_link_search.search_link` | same shape | compatible; Latin/unregistered passthrough returns the vendor object unchanged; Arabic path folds vendor search fields + enabled/disabled constraints into one permission-aware `get_list` |
| `frappe.handler.download_file` | `(file_url: str)` | `overrides/file_download.download_file` | `(file_url: str)` | exact; BOQ-attached files checked against the parent document's read, everything else delegates to the vendor runner including guest/public behavior |

`override_doctype_class`: `Translation` → `overrides/translation.CustomTranslation`
(MRO `CustomTranslation → Translation → Document`, verified). Calls `super().validate()`
first; custom fields guarded by `meta.has_field`.

## 2. Report monkeypatch — health on the live site

`construction/__init__.py` installs the fail-closed guard first (fatal startup on failure),
then upgrades to the full `_scope_aware_run` wrapper. Measured on the rehearsal site:

- `report_enforcement_health()` → `installed True, fail_closed_guard False, runner
  _scope_aware_run, degraded False`
- live `query_report.run.__name__` = `_scope_aware_run`; `override_whitelisted_method` for
  both `download_file` and `search_link` resolves to the app paths above.

Signature note (not drift): the live wrapper presents `(*args, **kwargs)` while the captured
original is the full 9-parameter signature. The wrapper normalises positional/keyword/dict/
JSON-string/`None` filters and writes them back in the caller's own form, so no
`got multiple values for argument 'filters'` path exists. Protected set unchanged:
11 financial + 4 dashboard = 15 (`report_guard.ALLOWED_REPORTS`).

## 3. Permission and query hooks (current tree)

- `permission_query_conditions`: wildcard `*` → `scope_query.add_scope_conditions`
  (Administrator/System Manager bypass; guests + unscoped users get `1=0` on scoped
  doctypes; settings-read failure fails closed; dynamic exclusions fail closed to empty;
  cost-center NestedSet expansion with corrupt-tree fallback to exact match), plus
  `boq_permissions.boq_parent_query_conditions` for the six BOQ children (reuses the
  framework's own `DatabaseQuery("BOQ Header").build_match_conditions()` — verified present
  as `(self, as_condition=True)` on the installed framework — instead of materialising
  headers; Cost Analysis template allowance preserved).
- `has_permission`: the six BOQ children → `has_boq_parent_permission` (returns True only
  to let vendor checks continue, never grants; re-checks the stored parent against
  re-parenting; VO/stage/analysis parent-read exceptions with the controller-level
  integrity rules cited in code), `BOQ Header` → `has_boq_header_permission` (scope
  boundary on direct reads/writes), `File` → `has_file_parent_permission` (BOQ-attached
  reads/writes/deletes delegate to the parent; every other file returns True to the role
  system).
- `doc_events`: wildcard `*` validate → `scope_enforcement.validate` (branch–company
  integrity always; scope containment when enabled; Administrator / System Manager /
  install-migrate / service-bypass-token paths as documented), eight transaction doctypes →
  `boq_transaction_validation`, bilingual policy + narrative sanitizer on ~25 masters,
  stage `before_delete` lifecycle guard.

## 4. F19 report adapters — RPC boundary, not an override

`construction/api/construction_reports.py` (`report_view` / `report_export` /
`integrity_view`) does not replace any vendor function. It is the only customer RPC boundary
for the five estimation services: allowlisted report identifier, scalar filters, required
Company scope (`has_permission("Company", "read", doc=company, throw=True)`), header match
check, per-row document authorization (`_readable*`), bounded paging (50/200) and exports
(2,000 cap, private File attached to the header, covered by the F11 file guard). Finance
ledgers excluded; integrity is an Administrator-only passthrough. F21-D002's fix
(`RPH.name` selected; `_readable_rph` refuses unidentified rows) lives at this boundary.

## 5. Sidebar fixture — app-backed, importable, live-matching

`construction/construction/sidebar/construction_home/construction_home.json`:
30 items (`DocType` / `Page` / `Workspace` link types only — all valid `Sidebar Item`
`link_type` values); `app=construction, module=construction, name=Construction Home,
standard=1`. Path matches `import_file.get_file_path("construction", "sidebar",
"construction_home")`, and the site row reads `standard=1, app=construction,
module=construction` with 30 items — the undocumented site-made row is gone.
No code, fixture, test or user-facing doc links to `/app/construction-home`
(F22-D007 closed as an unsupported Sidebar slug; canonical entry `/app/construction`).

## 6. Client-side overrides

Registered in `app_include_js`/`app_include_css` (`hooks.py:128–193`). Behavioural evidence
for the surfaces that matter to this program exists: F22 (Arabic/RTL, translated errors,
dialogs, exports) and F23 (theme apply + persistence, VFC density/visibility persistence and
reset, dependent fields, permission-controlled `certified_qty`). The register's standing gap
remains: `frappe_compat_patches.js` / `native_frappe_controls_compat.js` do not declare
per-patch upstream targets — still open, carried as F24-D001 below.

## 7. Test evidence (this review)

| Suite | Result |
|---|---|
| `test_option_a_plus` | OK |
| `test_bilingual_desk_link_dispatch` (17 vendor-parity/dispatch tests) | OK |
| `test_translation_catalog` | OK |
| `test_scope_and_measurement_policy` (5) | OK after F22-D008 fix (see §8) |
| `test_vo_approval_parent_gate` (5) | OK |
| `test_f21_price_history_row_auth` (9), `test_f22_arabic_coverage` (4), `test_project_display_name_authorization` (6), `test_cost_analysis_engine` (38) | OK (re-confirmed) |
| `test_security_audit_remediation` (24) | 2 failures, both teardown hygiene (approved Quantity Revisions cannot be deleted by design; the test leaves residue it then cannot clean) — not an override break; recorded as F24-D002 |
| `test_scope_context` | old-style function tests, no TestCase — runner reports no tests; noted, not claimed |

## 8. Findings

**F22-D008 applied to the suite (owner carry-forward):** `test_missing_scope_denies` in
`test_scope_and_measurement_policy.py` used `f04-readonly`, which gained a valid scope for
F21-D001. It now uses the dedicated `f23-scopeless@v16rehearsal.local` account (Site
Engineer, Company user permission, no scope context). Suite 5/5.

**F24-D001 (carried, was register §10):** per-patch upstream-target list for the two compat
JS files still missing. No new evidence; remains the precondition for any vendor-bump test.

**F24-D002 (new):** `test_security_audit_remediation` teardown cannot delete approved
Quantity Revisions (the controller correctly refuses). The test needs a fixture that stays
deletable or a cleanup path that respects the guard. Not an override defect; queued for F38.

## 9. Status

F24 **Engineering verified for the working tree**: all six whitelisted overrides are
signature-compatible with frappe 16.51.1 / erpnext 16.50.0, the Translation subclass chains
correctly, the report wrapper is healthy (not degraded), the permission/query/doc-event
hooks match their documented fail-closed contracts, the report adapters stay a bounded RPC
surface rather than a vendor replacement, and the Sidebar ships from the repo with the site
row matching. Owner acceptance stays in the consolidated final block.
