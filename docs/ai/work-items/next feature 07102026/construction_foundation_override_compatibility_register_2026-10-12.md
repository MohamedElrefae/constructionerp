# F24 — Framework override and hook compatibility register

**F25 source correction:** The [runtime/asset review](construction_foundation_runtime_asset_consistency_review_2026-10-12.md) corrects the version-source path, direct dispatcher-test inventory, hook/patch counts and protected report count below. Existing tests are acknowledged; no fresh test pass is claimed. Runtime compatibility and remaining matrix evidence stay open.

**Date:** 12 October 2026
**Candidate:** develop `c9e6803c5ac63073aeb0b166c779844d29051d8d` (source register; runtime behavior to be qualified on the F02 target)
**Program:** [Foundation master plan](construction_foundation_remediation_master_plan_2026-10-12.md) · [Work register](construction_foundation_work_register_2026-10-12.md) · [F03 inventory](construction_foundation_feature_route_inventory_2026-10-12.md)
**Status:** Register complete at source; per-override compatibility evidence on declared versions is **not** produced here (remaining F24 work)

## 1. Purpose and method

Every shipped change to upstream Frappe/ERPNext behavior is registered with its upstream target, purpose, authorization model, fallback behavior and test coverage, so that a supported vendor bump can be checked against a known surface (plan F24). This register was produced by reading `hooks.py`, the `construction/construction/overrides/` package, the overridden endpoint implementations, the import-time patch installation (`construction/__init__.py`), `patches.txt` and the client JS override files at the candidate above. No site, suite, migration or deployment was executed; "test present" below names an existing file, not a fresh run.

## 2. Declared version position

| Item | Value | Source |
|---|---|---|
| App version | `0.0.5` | **corrected per F25:** app-package root `construction/__init__.py` (repo-relative); the nested module `construction/construction/__init__.py` is docstring-only |
| Framework alignment target | Frappe v16.36.1 / ERPNext v16.37.0 (code comments are intentions; CI actually pins Frappe `81aadb9…` / ERPNext `2807c9f…` = 16.18.1 / 16.18.3 — see F25 §3) | `pyproject.toml`, F25 review |
| CI runtime | v16 install path; Python 3.14 runtime with Ruff `py310` conservative syntax rule | `.github/workflows/ci.yml` (F03/F25 records) |
| Local vendor checkout referenced during F03 | Frappe `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0` — a reference checkout, **not** a supported-version declaration | F03 inventory §10 |
| Supported-version claim | **v16 only.** No v15/v16 matrix is claimed by this register; declaring and testing a matrix is remaining F24 work | — |

## 3. Whitelisted-method overrides (5)

| Upstream target | Override (candidate) | Purpose | Authorization / contract | Fallback on failure | Existing tests | Remaining qualification |
|---|---|---|---|---|---|---|
| `frappe.core.doctype.user.user.switch_theme` | `construction/overrides/switch_theme_simple.py:13` | Construction-theme switching with API-compatible signature (`theme=`, legacy `theme_name` alias; disagreement rejected) | Session user only; Guest/empty refused; savepoint rollback + re-raise on error; never commits outside request | Vendor Select enum preserved (`Dark`/`Light`/`Automatic`) | `test_theme_e2e.py`, `test_theme_e2e_v2.py` (historical) | Signature drift + write-behavior check on declared v16; F15/F23 verify narrow theme-preference writes and audit |
| `frappe.utils.change_log.show_update_popup` | `construction/api/theme_api.py:3281` | Disable update popup | Whitelisted override endpoint | No-op return | — (trivial) | Confirm no other caller depends on vendor popup side effects; F24 |
| `frappe.translate.update_translations_for_source` | `construction/api/translation_tools.py:117` | Non-destructive translation source update (vendor version deletes rows) | `frappe.only_for("System Manager")`; validates/normalizes input | Returns error paths; no destructive fallback | `test_translation_catalog.py`, `test_translation_stabilization_gates.py` | Vendor signature drift check; F11/F22/F40 |
| `erpnext.accounts.doctype.account.account.update_account_number` | `construction/services/bilingual_service.py:676` | Governed Account identity rename: reason required, all vendor validations preserved, post-rename identity re-resolved server-side | `frappe.has_permission("Account","write")`; reason mandatory; scoped savepoint (caller's transaction untouched; no commit here) | Raises; vendor flow still reachable **through this wrapper only** (hook refuses direct field writes) | `test_stage7_bilingual_reports.py` (part) | Denied-path and idempotency evidence; F11/F22 |
| `frappe.desk.search.search_link` | `construction/api/desk_link_search.py:284` | Bilingual link search: Arabic queries use construction registry; Latin passthrough returns vendor object unchanged | Passthrough-first ordering; signature accepts vendor args incl. `ignore_user_permissions` | Vendor result object returned unchanged on non-bilingual path | `test_bilingual_desk_link_dispatch.py` (17 direct tests including vendor parity and non-admin denial); adjacent `test_transaction_link_search.py`; not run here | Permission-parity test vs vendor `search_link` (must not bypass link field permissions); F11/F12 |

## 4. DocType class overrides (1)

| Upstream class | Override | Purpose | Contract | Tests | Remaining qualification |
|---|---|---|---|---|---|
| `frappe.core.doctype.translation.translation.Translation` | `construction/overrides/translation.py:14` `CustomTranslation` | Catalog-aware translation editing: catalog rows preserved for review, edited values upserted to canonical runtime row; digest-based duplicate rejection; NUL rejection | Calls `super().validate()` first; custom fields guarded with `meta.has_field`; `on_update` upserts runtime value and invalidates caches | `test_translation_catalog.py`, `test_translation_stabilization_gates.py` | Vendor `validate` signature drift; `super()` chain behavior on vendor bumps; F22/F40/F24 |

## 5. Import-time monkey patch (report enforcement)

| Upstream target | Patch | Purpose | Failure model | Health probe | Remaining qualification |
|---|---|---|---|---|---|
| `frappe.desk.query_report.run` | `construction/overrides/report_guard.py` (minimal guard) upgraded by `construction/overrides/scope_report.py:91` `apply_report_monkeypatch()`; installed at import from `construction/__init__.py:35–75` | Enforce scope/company boundary on allowlisted financial/dashboard reports (11 financial + 4 dashboard = 15 per F03 §5) | **Fail-closed, staged:** guard install failure = fatal startup error (app refuses ready). Full-wrapper failure = degraded mode: protected reports raise `PermissionError`, incident logged | `scope_report.report_enforcement_health()`; installed-runner name check | This is the highest-compatibility-risk override: it replaces an upstream function at import time. Vendor signature drift for `query_report.run` must be tested on every supported bump; degraded-mode alerting must reach an operator channel; F11/F12 |

## 6. Permission and query hooks

| Hook | Registration | Target | Behavior notes | Remaining qualification |
|---|---|---|---|---|
| `permission_query_conditions` | `hooks.py:376–389`: `"*"` → `overrides/scope_query.py:73`; plus `overrides/boq_permissions.py:47` for BOQ Item, BOQ Structure, BOQ Item Stage, BOQ Quantity Revision, BOQ Cost Analysis, Variation Order | All list/report/chart queries; six BOQ children | Wildcard: Administrator/System Manager bypass; guests and unscoped users fail closed to `1=0` on scoped doctypes; settings-read failure fails closed; dynamic exclusion list read from Construction Settings (fails closed to empty). BOQ hook reuses `DatabaseQuery` match conditions instead of materializing headers; template Cost Analysis allowance | F11 matrix must prove deny paths server-side; F12 measures Option B + report dispositions; Option B flag default is 1 (F03) |
| `has_permission` | `hooks.py:391–401` → `boq_permissions.py:31` for the six BOQ children | Document-level authorization | Child authorization delegates to `BOQ Header` parent rights; re-checks the stored parent to prevent re-parenting a forbidden child; returns `True` only to let vendor checks continue, never grants | Denied-path evidence in F11; template/`is_template` path reviewed |
| `doc_events` | `hooks.py:258–372`: `"*": validate → overrides/scope_enforcement.py` | Every document save | Branch–company integrity (always) + scope-context containment (when enabled); service-only bypass token `frappe.flags.construction_scope_scope_bypass` and install/migrate/patch flags honored | `test_scope_context.py` (historical); F11 must verify the wildcard cannot be bypassed via HTTP/import; F15 reviews bypass token use |
| Transaction validation | Eight doctypes → `services/boq_transaction_validation.py` | PO, PR, PI, SI, Stock Entry, Timesheet, Journal Entry, Material Request | Cascade/attribution gates per F03 §4 | F09/F20 row-matrix evidence; F11 |
| Arabic policy + narrative sanitizer | ~25 master doctypes → `services/bilingual_service.enforce_bilingual_arabic_policy`; narrative subset → `services/narrative_sanitizer.validate_narrative_fields` | Account (plus cache-busting on update/trash/rename), Item, Customer, Supplier, Cost Center, Warehouse, Project, UOM, Employee, BOQ Structure, BOQ Header, Company, etc. | Confines Arabic-name writes to governed API; Account direct edits refused | F22/F24 owner-accepted Arabic flows; vendor master-upgrade regression |
| BOQ Item Stage lifecycle | `before_delete` → `services/boq_lifecycle.py` | Stage deletion guard | — | F09/F05 |

## 7. Client-side overrides (Desk JS)

Registered in `app_include_js`/`app_include_css` (`hooks.py:128–193`). These replace or wrap framework controls at runtime and are the main v15/v16 dual-compatibility surface.

| Asset | Upstream target | Purpose | Compatibility notes | Remaining qualification |
|---|---|---|---|---|
| `overrides/ct_link_control.js?v=17` | `frappe.ui.form.ControlsLink` auto-enhancement | Searchable Link fields app-wide | Cache-buster policy: bump `?v=` on change (AGENTS.md convention) | F22/F23 browser evidence on supported versions; G13 |
| `overrides/ct_select_control.js?v=2` | `ControlSelect` (native `<select>`) | Themed searchable dropdowns | DOM-selector fragility across versions | F22/F23 |
| `frappe_compat_patches.js?v=2`, `native_frappe_controls_compat.js?v=9` | Framework runtime patches | Desk compatibility (list/control affordances) | Order-sensitive loading (comments in hooks) | F22; document each patch's upstream target — currently implicit |
| `scope_context*.js` (5 files), `vfc_layout_engine.js?v=1.44`, `vite_layout_controls.js?v=1.21` | Framework form/list/report runtime | Scope selectors, VFC re-parenting, density/controls | Engine timing dependencies (150–250 ms) | F21/F23 qualification |
| `theme_loader_v24/v16`, `modern_theme.css` bundle | Desk theming/FOUC | Namespace theming without FOUC | `theme_loader_v16` is a documented no-op safety net | F23 theme stabilization |
| `searchable_dropdown/*` | Link control base class | Shared dropdown base loaded before overrides | Load-order dependency | F22 |

**Client override gap:** `frappe_compat_patches.js` and `native_frappe_controls_compat.js` do not declare their individual upstream targets; F24 must extract a per-patch list before any vendor bump test.

## 8. Site, brand and rendering hooks

| Hook | Registration | Purpose | Notes |
|---|---|---|---|
| `brand_html`, `login_page_title`, `website_context`, `email_css` | `hooks.py:207–217` | Branding for web/login/email | F39 README must not overstate white-label claims |
| `pdf_header_html` / `pdf_footer_html` | `hooks.py:221–222` → `theme_api.get_pdf_header/footer` | Branded PDF frames | Print/PDF qualification in F22 |
| `jinja` filter `bdi_join` | `hooks.py:224–228` | Narrative sanitization in templates | Used by narrative sanitizer service |
| `boot_session` / `extend_bootinfo` | `hooks.py:251–254` | Theme + scope context injection at boot | COV-08 guest boot check; F11/F15 |
| `after_install` / `after_migrate` | `hooks.py:412–451` (15 after_install / 18 after_migrate entries) | Theming, custom fields, roles, profiles, bilingual schema, translations | Order-sensitive; F31/F34 must compare against installed records (COV-09); repeated-run idempotence is F31 evidence |
| `patches.txt` | **38 patches through `v9_16.repair_legacy_translation_identity`** (candidate moved c9e6803c→1e46488; see §12) incl. `v6_8.add_boq_structure_wbs_unique_constraint` | Schema/data migrations | DDL-carrying patches (unique constraint) require F31 replay evidence — MariaDB DDL does not roll back with application transactions |

## 9. Standing compatibility rules for this candidate

1. Any touched CSS/JS registration bumps its `?v=` cache buster; bundle changes carry asset/hash and rollback evidence (F25).
2. A hook may never silently disable permission enforcement; the report monkey patch and wildcard scope hook must fail closed (current design) — preserved on every bump.
3. Supported versions are declared, then tested; an unsupported version must fail clearly or be excluded from product requirements (G13/F24). No blanket v15/v16 support claim.
4. Upstream signature drift for the five method overrides, the Translation class, and `query_report.run` is checked before adopting a vendor bump.
5. Simplifying/hiding an override requires an ADR and a test that the removed behavior is unreachable.

## 10. Open items from this register

| Item | Maps to |
|---|---|
| Candidate-bound full permission-parity matrix for `search_link` (direct dispatcher/vendor-equality/non-admin tests already exist; extend uncovered cases) | F11 |
| Per-patch upstream-target list for the two compat JS files | F24 |
| Report monkey-patch signature-drift test + degraded-mode operator alerting | F24/F11/F33 |
| doc_events wildcard bypass review (HTTP/import paths; bypass token) | F11/F15 |
| Theme switch override write-path evidence (own-profile only, narrow fields) | F15/F23 |
| Client override browser evidence on declared versions | F22/F23 |
| DDL patch (`v6_8` unique constraint) replay behavior | F31 |
| Retained uncommitted vendor modification `frappe/desk/doctype/sidebar/sidebar.py` (case-insensitive title/module compare) — disposition required, see §12 | F24/F13 |
| Vendor master hooks (bilingual policy/sanitizer on ~25 doctypes) regression on upgrade | F24/F31 |

## 11. Verification

- Read: `hooks.py` (full), `overrides/` (9 modules), `__init__.py`, the five overridden endpoint implementations, `patches.txt`, JS override inventory, plus F01/F03 documents. Startup checks remain passing (21+1 schema owners; context 11/0 — unchanged by this read-only session).
- Produced: this register only. No application file modified, no site queried, no suite run, no commit or push.

## 12. Environment-change addendum (2026-10-13) — candidate moved, vendor modified

**What changed outside this register’s candidate:** construction `c9e6803c` → `1e46488` ("fix(migrate): repair Arabic field prerequisites and legacy translation identities": 9 files — ci.yml +5 lines, patches.txt +v9_16, rewritten v8_6/v9_2 translation patches, rewritten `setup/translation_catalog_fields.py`, 2 new migration test files); bench vendor frappe `81aadb9` (16.18.1) → `2871914` (16.51.1), erpnext `2807c9f` (16.18.3) → `7474d9e` (16.50.0); bench environment reinstalled (`pip install -e`, yarn, `bench build`); both `v16.localhost` and `v16rehearsal.localhost` migrated. K-01/E11 reproduction files (`boq_header.js`, `boq_api.py`, `boq_import_service.py`, `erpnext-mcp-server/server.py`) and all `overrides/` modules are **untouched** — those findings stand. This register’s hook/override inventory is unaffected except the patches count above; CI facts (+1 workflow step) belong to F25’s re-check.

**Vendor modification — RESOLVED by revert with app-side fix (owner decision 2026-10-13, non-coder durable option):** the working-tree diff in `frappe/desk/doctype/sidebar/sidebar.py` (3+/2-, case-insensitive title/module compare) has been **reverted** (`git diff` on apps/frappe is empty). Root cause: the app is internally consistent in lowercase (`modules.txt`, all DocTypes, workspace, Module Def `construction`), but the converted Sidebar record carried display title `Construction`; the vendor check’s case-sensitive Python compare plus case-insensitive DB `exists()` produced a false-positive throw. Changing the record’s `module` was rejected (exact-match navigation linking in `pick_primary`); renaming the module everywhere was rejected (21+ DocTypes, high regression risk for a non-coder owner).

Applied fix (one source line + one-time data, no vendor change):
- Source: `construction/config/workspace_sidebar_items.json` title `Construction` → `Construction Home` (display label only; `module` stays `construction`, preserving all linking; durable for fresh sites via the every-migrate reconciler).
- Data (v16.localhost + v16rehearsal.localhost): Workspace Sidebar `Construction` deleted (no link references; reconciler recreates from fixed config); Sidebar record retitled to `Construction Home` (autoname `field:title` renamed the key consistently).
- Proof on both sites with original vendor code: Sidebar re-save triggers `validate_title_is_its_own` → passes (`Construction Home` matches no Module Def); full `bench migrate` passes (reconciler recreates Workspace Sidebar; convert patch does not re-run); site pong; BOQ counts unchanged (23/34/213/34). v16rehearsal.localhost required a temporary `developer_mode=1` for the record save (`validate_app_content` blocks Sidebar edits otherwise; deletes are allowed) — key removed afterwards, site restored to production-like state. Two stray bench-root log dirs from path misresolution removed.
- Vendor is clean; F24’s override position holds. ENV-D001 closed. The one-line app config change is uncommitted pending owner review/commit.

**Verification for this addendum (2026-10-13):** `git log/diff` on all three apps; `bench version`; site alive with BOQ counts unchanged (23/34/213/34); installed dependency versions satisfy the app’s five ranges with `pip check` clean except an unrelated virtualenv/filelock nit. No application file was modified by this review.

## 13. App-side sidebar title fix review — 13 October 2026

Reviewed source baseline: Construction `1e464889465554a62ee87074bd7bdf9ac7ab2204` plus uncommitted config title change; clean Frappe `2871914b69b6e14a4b023d9b7cc52dc3e269cc1b` and ERPNext `7474d9e786277383de1242ab882f16856d17a9c9`. [Review fingerprints](construction_foundation_sidebar_fix_review_2026-10-13.json) bind the exact files. No site request, migration or commit was performed during this review.

**Disposition:** retain the title change as a narrow existing-site validator-collision repair and leave it uncommitted for the F38 fix batch. Parsed JSON confirms only title changes; module, app and all navigation items match HEAD. The original vendor check accepts own-module title only by a case-sensitive comparison before checking Module Def existence; the distinct title avoids that particular collision. Title is also a Sidebar name/boot/URL identity because of field:title and rename_to_title; it is not solely decorative. The data retitle and link behavior require their reported runtime evidence.

**ENV-D001 remains closed for reverting the vendor edit.** Original vendor source is clean on both vendor checkouts. The owner reports Sidebar re-save and full migration success on v16.localhost/v16rehearsal.localhost. This reviewer did not rerun them. Unchanged record counts are useful checks but do not by themselves prove unchanged commercial values/history or fresh-site behavior.

| Review item | Source finding | Required F38/F24/F31 follow-up |
|---|---|---|
| F24-D002 — live/sidebar model compatibility | Current Frappe Workspace Sidebar controller explicitly calls the model an inert archive. The app reconciler creates/saves Workspace Sidebar, while vendor convert_sidebars is a patch which skips modules already having Sidebar. No app create/update path for the live Sidebar is present. | Qualify fresh-site creation and replay with current vendor; adapt the supported live model/JSON shape rather than relying on a historical conversion. Preserve legacy support intentionally and test navigation after config edits. The one-line title change alone does not prove modern live-sidebar reconciliation. |
| F24-D003 — hardcoded health identity | verify_workspace_visibility still looks for Workspace Sidebar named Construction and child parent Construction. The fixed config creates Construction Home. This health function logs errors and does not throw. | Derive the sidebar identity from the same configuration and check the supported active model. Test missing/empty/valid cases; a passing migrate is not a passing health check. |

No source implementation was added for these findings. Fresh/current-sidebar tests belong to engineering evidence and later consolidated owner UI acceptance, not a premature owner test session. ENV-D002 still requires a post-upgrade named baseline, fresh recoverable backup/restore evidence on a safe isolated target, outbound/versions/config re-check and F13 runtime qualification before further foundation mutation. A vendor patch no longer needs carrying; framework upgrade compatibility still requires qualified checks.
