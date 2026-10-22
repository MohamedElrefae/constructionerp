# F25 — Runtime, packaging and asset source consistency review

**Date:** 12 October 2026  
**Candidate:** develop `c9e6803c5ac63073aeb0b166c779844d29051d8d`  
**Status:** Source/configuration review completed; **F25 In progress**. Dependency resolution, reproducible package/build, installed runtime and browser evidence remain owed.  
**Classification:** Confidential — internal

Related: [master plan](construction_foundation_remediation_master_plan_2026-10-12.md) · [work register](construction_foundation_work_register_2026-10-12.md) · [F24 register](construction_foundation_override_compatibility_register_2026-10-12.md) · [F03 inventory](construction_foundation_feature_route_inventory_2026-10-12.md) · [JSON evidence](construction_foundation_runtime_asset_evidence_2026-10-12.json).

## 1. Result and qualification boundary

The configured CI vendor pins and current Construction dependency ranges do **not** describe one satisfiable runtime: all five directly declared Construction dependency ranges are disjoint from those in CI-pinned Frappe. Resolve this with F13 before claiming a coherent build or security-qualified candidate. The separate dependency-audit job uses Python 3.10 while the app requires 3.14. Version metadata also differs between the current Flit build path and legacy setup.py.

All 37 global asset-hook registrations (including repeated web/email/print references) point to existing source files. That does not prove deployed URLs, build freshness or browser behavior. Eleven form/list/tree hook paths do not exist under the local vendor's module-relative resolver; native DocType loading supplies corresponding source files and can mask these redundant/bad registrations. Avoid a blind prefix correction that would load the same script twice.

No pip/npm install, dependency resolver, package build, bench build, site query, browser test, business suite, migration, remote CI run, commit or push was performed. Inspection used Python 3.14.5 for TOML/JSON/AST and pure version-range comparison. Local vendor checkouts are reference sources matching CI pins; they are not an observed deployed environment.

## 2. Runtime and tool policy

| Surface | Source configuration / evidence | Interpretation / action |
|---|---|---|
| Construction Python runtime | pyproject.toml: `>=3.14,<3.15` | Declared install/runtime range; qualify on exact 3.14 interpreter and selected vendor commits |
| Source syntax/lint policy | Ruff `target-version=py310`; owner requires conservative 3.10 quote syntax | May coexist with runtime 3.14. Retain convention; it is not a v15 or Python 3.10 runtime claim |
| Business CI Python | ci.yml uses Python 3.14 | Matches Construction's declared range; actual candidate run still owed |
| Linter Python | linter.yml uses Python 3.10 for pre-commit/source gates | A separate lint host can be intentional; record tool compatibility and avoid assuming it validates runtime dependencies |
| Dependency-audit Python | linter.yml deps-vulnerable-check: Python 3.10, then `pip-audit --desc on .` | Audit/resolve against the declared 3.14 runtime or a reviewed target lock; current job host cannot establish the supported app environment |
| Node | Business CI Node 24, check-latest true; pinned Frappe package.json requires >=24 | Major aligned; capture exact patch/tool/build identity for reproducibility |
| Database/Redis in CI | MariaDB 10.11 tag; Redis alpine tag | Configuration, not deployment/capacity proof; consider image digest recording for reproducible candidate qualification |
| Test packages | pytest 9.0.3 / hypothesis 6.155.1 installed by CI; JS uses npm ci | Source configuration only; dependency installation and resulting test execution unobserved here |

Keep the v16 qualification boundary in the F24 register. No v15 compatibility matrix is inferred. Runtime/syntax/tool policies should be explained consistently in README, onboarding and CI notes; changing the owner syntax convention is unnecessary to fix the actual resolver mismatch.

## 3. CI-pinned vendor sources versus target dependency ranges

The business CI pins Frappe `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0` and ERPNext `2807c9f08fff3f161c0a2e10745a26aa6331ffd5`. The local checkouts have those exact commits and declare versions **16.18.1** and **16.18.3**. The app comments instead describe dependency alignment with **Frappe 16.36.1 / ERPNext 16.37.0**. Those comments are intentions, not evidence that CI installs those versions.

Both app pyproject.toml and requirements.txt declare the five newer ranges below. Frappe's pinned pyproject.toml declares the older ranges. Compatible-release bounds were compared directly from their three-component `~=` declarations; no package index or resolver was consulted.

| Dependency | Construction interval | CI-pinned Frappe interval | Shared versions |
|---|---|---|---|
| cryptography | >=50.0.0,<50.1.0 | >=46.0.3,<46.1.0 | None |
| pyOpenSSL | >=26.4.0,<26.5.0 | >=26.0.0,<26.1.0 | None |
| Pillow | >=12.3.0,<12.4.0 | >=12.2.0,<12.3.0 | None |
| sqlparse | >=0.6.0,<0.7.0 | >=0.5.5,<0.6.0 | None |
| sql_metadata | >=3.0.1,<3.1.0 | >=2.19.0,<2.20.0 | None |

**F25-D001 — S1 foundation blocker:** these declarations cannot all be satisfied in the same environment. The exact failure/warning emitted by a build has not been reproduced; Bench/pip can leave conflicting installed distributions depending on operation order, so a green install message would not settle coherence. F13 must choose and verify compatible vendor/app constraints with the agreed security targets; F25 then rebuilds and records the actual resolved inventory and dependency metadata check. Do not blindly downgrade security targets or update only CI refs without qualified override/financial regressions.

The linter workflow checks out the same vendor commits for localization catalogs. Any later vendor alignment must update and requalify both business and catalog gates, preserving immutable historical evidence. Prior Run 11 counts describe their old candidate/runtime; no new pass follows from configuration presence.

### Further CI reproducibility obligations

Business CI installs unpinned `uv`/`frappe-bench`, initializes the moving version-16 branch before fetching the explicit Frappe commit, uses action tags and container tags, and selects the latest Node patch in major 24. The linter fetches Semgrep rules from a moving branch. Capture exact tool/image/rule versions and eliminate unnecessary moving-branch bootstrap where required for reproducibility; do not label these choices vulnerabilities without reachability evidence. This task has not downloaded anything or changed any workflow.

## 4. Package metadata and delivery inspection

| Path | Source fact | Required reconciliation |
|---|---|---|
| PEP 517 build | pyproject.toml selects Flit; module name construction; version is dynamic | Current package version source is root construction/__init__.py, literal 0.0.5 |
| Legacy setup.py | Uses setuptools, hardcodes version 0.1.0 and different description/contact; reads requirements.txt lines | Document current canonical build path; remove ambiguity safely if legacy installation is still offered. Do not silently change version history |
| Nested construction/construction/__init__.py | Module docstring; no version literal | F24's version-source path was incorrect; correct it to root construction/__init__.py |
| Flit sdist exclusions | orchestrator/ and tests_offline/ | These two exclusions are not a complete privacy/delivery audit |
| Setuptools find_packages exclusions | orchestrator, orchestrator.*, tests_offline, tests_offline.* | Package discovery rules differ from sdist/resource inclusion; setup.py contains no explicit full artifact privacy inventory |
| requirements.txt | Includes bare frappe plus the same five app dependency ranges; opening “only dependency” comment is obsolete | Clarify Bench-managed exact vendor sources versus app constraints; prevent an unreviewed framework-package install path |
| Root frontend build config | No root package.json, yarn.lock or vite.config.js/ts found | Do not describe an observed app-specific Vite build pipeline without an actual configuration/run |
| Source bundle entry | construction/public/js/construction.bundle.js imports print/export menu modules | Frappe bundle entry exists; generated output/hash/registration still require build evidence |

**F25-D003 — metadata/documentation consistency:** Flit version 0.0.5 and setup.py version 0.1.0 differ; AGENTS/onboarding describe a Vite hashed bundle without source-build configuration supporting that claim. Current global hooks load raw JS, including VFC/layout controls. Existing React files are retained legacy paths under ADR-008; source presence is not an active product flow. Reconcile the user/developer documentation with the supported build and record how the source bundle is used, without introducing a new toolchain.

**Handoff to F28:** source configuration facts are now available for packaging work. Actual wheel/sdist file lists, deployment export privacy, resources and installation behavior remain unmeasured. Build only in an approved isolated output/runtime and inspect artifact contents; do not infer what a customer receives from exclusions. A Git checkout obtained via bench get-app includes repository content even where Python packaging excludes it. No repository split, source publication or license change was performed.

## 5. Assets and cache keys

Counts: 26 Desk JS and six Desk CSS; web JS/CSS, email and print registrations make 37 hook entries with repetitions. Every mapped source file exists and was hashed in the JSON artifact. F25/F22/F23 still owe generated/symlink resolution, HTTP status/content/hash, browser loading order, cache behavior and native form usability.

| Hook | Registered URL | Source bytes | Manual version |
|---|---|---:|---|
| app_include_js | /assets/construction/js/boq_export_columns.js?v=1 | 4312 | 1 |
| app_include_js | /assets/construction/js/print_settings_dialog.js | 23528 | None |
| app_include_js | /assets/construction/js/construction_export_menu.js | 6039 | None |
| app_include_js | /assets/construction/js/generic_export_menu.js?v=1 | 14589 | 1 |
| app_include_js | /assets/construction/js/theme_loader_v24.js?v=2.6.2 | 34601 | 2.6.2 |
| app_include_js | /assets/construction/js/typography_settings.js?v=21 | 30401 | 21 |
| app_include_js | /assets/construction/js/searchable_dropdown/utils.js | 2625 | None |
| app_include_js | /assets/construction/js/searchable_dropdown/searchable_dropdown.js?v=1 | 4590 | 1 |
| app_include_js | /assets/construction/js/overrides/ct_select_control.js?v=2 | 13262 | 2 |
| app_include_js | /assets/construction/js/overrides/ct_link_control.js?v=17 | 23724 | 17 |
| app_include_js | /assets/construction/js/theme_loader_v16.js?v=2 | 834 | 2 |
| app_include_js | /assets/construction/js/scope_context.js?v=3 | 11255 | 3 |
| app_include_js | /assets/construction/js/frappe_compat_patches.js?v=2 | 6964 | 2 |
| app_include_js | /assets/construction/js/scope_context_ui.js?v=5 | 9193 | 5 |
| app_include_js | /assets/construction/js/scope_context_list_filter.js?v=3 | 4149 | 3 |
| app_include_js | /assets/construction/js/scope_context_form_defaults.js?v=3 | 2373 | 3 |
| app_include_js | /assets/construction/js/vfc_config.js?v=1 | 749 | 1 |
| app_include_js | /assets/construction/js/scope_context_report_filters.js?v=4 | 14120 | 4 |
| app_include_js | /assets/construction/js/ct_list_view_config.js?v=1 | 3555 | 1 |
| app_include_js | /assets/construction/js/sidebar_accordion.js?v=1 | 1052 | 1 |
| app_include_js | /assets/construction/js/translation_list_tools.js?v=6 | 8577 | 6 |
| app_include_js | /assets/construction/js/boq_filters.js?v=8 | 21667 | 8 |
| app_include_js | /assets/construction/js/filter_fix.js?v=11 | 22121 | 11 |
| app_include_js | /assets/construction/js/native_frappe_controls_compat.js?v=9 | 21006 | 9 |
| app_include_js | /assets/construction/js/vite_layout_controls.js?v=1.21 | 70105 | 1.21 |
| app_include_js | /assets/construction/js/vfc_layout_engine.js?v=1.44 | 49615 | 1.44 |
| app_include_css | /assets/construction/css/modern_theme.css?v=2.5.9 | 146350 | 2.5.9 |
| app_include_css | /assets/construction/css/scope_context.css?v=2 | 1040 | 2 |
| app_include_css | /assets/construction/css/vite_extensions.css?v=1.3 | 2597 | 1.3 |
| app_include_css | /assets/construction/css/vite_form_override.css?v=1.5 | 26890 | 1.5 |
| app_include_css | /assets/construction/css/vite_list_override.css?v=1.3 | 10847 | 1.3 |
| app_include_css | /assets/construction/css/vfc_sections.css?v=1.6 | 10811 | 1.6 |
| web_include_js | /assets/construction/js/theme_loader_v24.js?v=2.6.2 | 34601 | 2.6.2 |
| web_include_css | /assets/construction/css/modern_theme.css?v=2.5.8 | 146350 | 2.5.8 |
| web_include_css | /assets/construction/css/email_theme.css | 1698 | None |
| email_css | /assets/construction/css/email_theme.css | 1698 | None |
| print_css | /assets/construction/css/print_theme.css | 1891 | None |

**F25-D005 — cache policy qualification:** three Desk JS entries have no manual version (`print_settings_dialog.js`, `construction_export_menu.js`, searchable-dropdown `utils.js`), while ADR-007 broadly says all assets use `?v=`. Email/print CSS are also unversioned. Desk modern_theme.css has 2.5.9 and web uses 2.5.8 for the same source. Different URLs can serve the same file; these facts do not prove stale assets. Specify and test invalidation for each surface, then narrow the policy wording or correct actual stale-cache behavior. Do not automatically convert every asset to hashed bundles.

Locally required SortableJS exists in the source vendor directory. Source-level file resolution is recorded; no CDN availability assumption or download was needed. The user-visible Form Config path uses native/VFC scripts in global hooks rather than the retained React layout implementation.

## 6. Form/list/tree hook resolution

Local pinned Frappe's `desk/form/meta.py:get_code_files_via_hooks` joins each registered path to the app module path. Many Construction registrations repeat the leading construction segment. The table shows the resulting paths relative to the app repo; this is deterministic source/path inspection, not a site metadata request.

| Hook / DocType | Local vendor-resolved path | File exists | Native convention can supply same behavior |
|---|---|---|---|
| doctype_js / BOQ Header | construction/construction/construction/doctype/boq_header/boq_header.js | No | Source counterpart available; qualify loading |
| doctype_js / BOQ Item | construction/construction/construction/doctype/boq_item/boq_item.js | No | Source counterpart available; qualify loading |
| doctype_js / BOQ Item Stage | construction/construction/construction/doctype/boq_item_stage/boq_item_stage.js | No | Source counterpart available; qualify loading |
| doctype_js / Construction Settings | construction/construction/construction/doctype/construction_settings/construction_settings.js | No | Source counterpart available; qualify loading |
| doctype_js / Scope Report Access Log | construction/construction/construction/doctype/scope_report_access_log/scope_report_access_log.js | No | Source counterpart available; qualify loading |
| doctype_js / User Desk Theme | construction/construction/construction/doctype/user_desk_theme/user_desk_theme.js | No | Source counterpart available; qualify loading |
| doctype_js / Variation Order | construction/construction/construction/doctype/variation_order/variation_order.js | No | Source counterpart available; qualify loading |
| doctype_js / Account | construction/public/js/bilingual/account_form.js | Yes | Separate custom hook path |
| doctype_list_js / Item | construction/construction/public/js/item_list.js | Yes | Separate custom hook path |
| doctype_list_js / BOQ Item | construction/construction/construction/doctype/boq_item/boq_item_list.js | No | Source counterpart available; qualify loading |
| doctype_list_js / BOQ Structure | construction/construction/construction/doctype/boq_structure/boq_structure_list.js | No | Source counterpart available; qualify loading |
| doctype_list_js / Variation Order | construction/construction/construction/doctype/variation_order/variation_order_list.js | No | Source counterpart available; qualify loading |
| doctype_tree_js / BOQ Structure | construction/construction/construction/doctype/boq_structure/boq_structure_tree.js | No | Source counterpart available; qualify loading |
| doctype_tree_js / Account | construction/public/js/bilingual/account_tree.js | Yes | Separate custom hook path |

**F25-D004 — 11 unresolved redundant registrations:** seven form hooks, three list hooks and one tree hook resolve to absent paths. Frappe `Meta.add_code` also loads the normal DocType JS/list/tree filenames, and `_add_code` skips absent files; this explains how the corresponding Construction source forms can still load. Account bilingual form/tree and Item list hook paths resolve. F25 must verify the actual meta/assets for each affected form and choose one intended loader. Merely stripping the prefix can double-load existing native scripts. Browser checks must cover buttons/events and Save after any repair. Severity is provisional S2 maintenance/qualification, not a claim that eleven forms currently fail.

## 7. JS tests and lock evidence

construction/tests/package.json and package-lock.json root dependencies/devDependencies agree; lockfile version is 3. Source package requests fast-check ^3.0.0 and Playwright/@playwright/test ^1.60.0; resolved lock entries are fast-check 3.23.2 and Playwright/@playwright/test 1.60.0. Business CI uses npm ci and a Node test entry file. None of these packages was installed or executed here.

A test package lock is not an application frontend/runtime lock, a vulnerability clearance or proof that browser tests run. F35/F36 must map actual runner cases and exit statuses to this candidate. F25 should retain generated asset hashes and exact Node/package-manager identity with the final build.

## 8. Corrections to the F24 handoff

The compatibility register remains useful, but several source assertions need correction:

| Prior assertion | Source-confirmed correction | Remaining work |
|---|---|---|
| No direct dispatcher/permission test exists | test_bilingual_desk_link_dispatch.py has 17 direct tests, including vendor-result equality, get_list-versus-get_all enforcement and non-admin denial; full CI matrix references the module | Re-run exact candidate and complete intended permission-parity/user-permission/signature matrix. Do not mark F24-D001 closed from source alone |
| App version from nested module | Root construction/__init__.py has 0.0.5; nested module has no version | Align metadata/docs as above |
| 14 install/migrate steps each | hooks.py has 15 after_install and 18 after_migrate entries | Per-step installed state/replay qualification remains F31/F34 |
| 23 patches through v8_7 | patches.txt has 37 entries, through v9_15.version_boq_cost_basis | Preserve all patch history and qualify schema/data replay |
| Report guard affects 11 reports | Source protected set includes 11 financial plus four dashboard reports (15 total) | Preserve report-specific scope/auth qualification; account for native runtime wrappers |

The existing non-admin test is narrower than a complete customer role/company/link-field parity matrix. Keep F24-D001 as an evidence/extension task, with corrected wording and existing file references. No test was run in this review.

## 9. Issue register and completion queue

| Issue | Evidence class / impact | Required next action | Package |
|---|---|---|---|
| F25-D001 | Confirmed disjoint dependency declarations for current CI pins; S1 runtime-coherence blocker | Resolve coordinated vendor/app constraints, exact rebuild and metadata check, then qualified regressions | F13/F25/F35 |
| F25-D002 | Audit job Python 3.10 versus app runtime 3.14; S2 audit-evidence gap | Run supported-target audit/lock workflow; keep conservative syntax lint separate | F13/F25 |
| F25-D003 | Version/build/documentation metadata differ; S2 maintainability | Canonical Flit version/build policy and accurate dependency/frontend docs | F25/F39/F41 |
| F25-D004 | 11 hook paths absent under local resolver but native counterparts exist; provisional S2 | Site meta/browser inspection; select single loader; test no double execution | F25/F24/F23 |
| F25-D005 | Manual-cache policy differs from some registrations; provisional S2 | Define/test invalidation and reconcile ADR/docs/version keys | F25/F22/F23 |

Do not mark F25 complete until: F13 selects a coherent runtime; isolated build/package succeeds; resolved dependencies and assets are recorded; hook loading and cache behavior are observed; relevant native/UI regressions pass; documentation is corrected and the candidate/rollback identity is retained. Source-only packaging facts can support F28 inventory while those gates remain open. No next business feature is authorized by this review.

## 10. Verification and files read

Source/TOML/JSON/AST inspections establish these facts; all five version-range pairs were disjoint, JS lock roots match, all 37 global asset entries resolve to source files, and 11 of 14 form/list/tree hook paths do not resolve under the local vendor algorithm. The app source and referenced vendor files were fingerprinted. Counts and Markdown links/tables were verified; no runtime result is implied.

Read current AGENTS, Professional Engineering Standard, context index, workflow, session memory and applicable F24/F25/F28 plan/register sections; pyproject.toml, requirements.txt, setup.py, root/nested __init__, CI/linter/pre-commit configuration, ADR-007/008, hooks, asset/form files, JS package/lock, source bundle/layout scripts, README/onboarding, patches and direct dispatcher tests. Local vendor metadata and Meta/read_file source were read as reference checkouts. JSON records 66 app-source/config hashes and separate vendor hashes. Startup schema check passed 21 owners + one override; context check passed 11/0. HEAD remains c9e6803c; pending documents/memory changes are preserved. No application source or site data changed.
