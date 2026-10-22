# F03 — Construction feature and route source inventory

**Date:** 12 October 2026  
**Candidate:** develop `c9e6803c5ac63073aeb0b166c779844d29051d8d`  
**Status:** Source inventory completed; F03 remains **In progress** until installed-site metadata, effective permissions and usable routes are reconciled.  
**Classification:** Confidential — internal engineering

Related: [master plan](construction_foundation_remediation_master_plan_2026-10-12.md) · [work register](construction_foundation_work_register_2026-10-12.md) · [F01 gap ledger](construction_foundation_gap_ledger_2026-10-12.md) · [machine-readable source inventory](construction_foundation_source_inventory_2026-10-12.json).

## 1. Scope and evidence

This inventory was generated through static Python AST/JSON inspection and source reads, without importing app modules or connecting to a site. It records 21 schema owners; one Journal Entry override directory; 108 decorated module/document methods; 26 global Desk JS registrations; six global Desk CSS registrations; eight form, four list and two tree JS hook entries; five method overrides; 34 explicit document-event keys; one workspace definition; one Desk Page; five print-format definitions; and 16 enable-prefixed settings controls. Source fingerprints cover 71 files. A file or hook entry is not proof of deployment, browser loading or authorization.

Source routes below are conventional candidates for Desk validation, not observed routes on a named UAT site. Child-table DocTypes are accessed through parent forms. Permissions listed come from source JSON; installed roles, User Permissions, shares, custom overrides and scope configuration may change effective access. The localhost and historical v16 sites are not assumed to be this program's UAT target.

Method decorators and literal caller references are discovery evidence only. An endpoint with no direct permission signal may delegate to a guarded helper; a visible guard can still be incomplete. F11 verifies actual allow/deny behavior. Literal caller scans exclude test files and do not resolve dynamic method names. Framework document REST, imports, report execution and runtime monkey patches create additional entry points beyond these 108 definitions.

## 2. Construction-owned forms and source role permissions

Rights are abbreviated only by displaying source key names. Routes/roles require site reconciliation; no new role is granted by this inventory.

| Schema | Source access surface | Source roles and rights | Test / work mapping |
|---|---|---|---|
| BOQ Cost Analysis — [boq_cost_analysis.json](../../../../construction/construction/doctype/boq_cost_analysis/boq_cost_analysis.json) | /app/boq-cost-analysis (submittable) | System Manager: amend,cancel,create,delete,email,export,print,read,report,share,submit,write; Construction Owner: amend,cancel,create,delete,email,export,print,read,report,share,submit,write; Project Manager: amend,cancel,create,email,export,print,read,report,share,submit,write; Site Engineer: email,export,print,read,report; Accountant: email,export,print,read,report; Read-Only: read | UI-16–23; F18/F19 additions |
| BOQ Cost Analysis Detail — [boq_cost_analysis_detail.json](../../../../construction/construction/doctype/boq_cost_analysis_detail/boq_cost_analysis_detail.json) | Through parent table | Child table / no standalone permission rows | UI-16–18,23 via parent |
| BOQ Header — [boq_header.json](../../../../construction/construction/doctype/boq_header/boq_header.json) | /app/boq-header | System Manager: create,delete,email,export,print,read,report,share,write; Construction Owner: create,delete,email,export,print,read,report,share,write; Project Manager: create,email,export,print,read,report,share,write; Site Engineer: email,export,print,read,report; Accountant: email,export,print,read,report; Read-Only: read | UI-08,12,13,29,35,50–52 |
| BOQ Import Batch — [boq_import_batch.json](../../../../construction/construction/doctype/boq_import_batch/boq_import_batch.json) | /app/boq-import-batch | System Manager: create,delete,email,export,print,read,report,share,write; Construction Owner: create,email,export,print,read,report,share,write; Project Manager: email,export,print,read,report; Read-Only: read | UI-50,51,53 |
| BOQ Item — [boq_item.json](../../../../construction/construction/doctype/boq_item/boq_item.json) | /app/boq-item | System Manager: create,delete,email,export,print,read,report,share,write; Construction Owner: create,delete,email,export,print,read,report,share,write; Project Manager: create,email,export,print,read,report,write; Site Engineer: email,export,print,read,report,write; Accountant: email,export,print,read,report; Read-Only: read | UI-10–13,16–23,30–35 |
| BOQ Item Stage — [boq_item_stage.json](../../../../construction/construction/doctype/boq_item_stage/boq_item_stage.json) | /app/boq-item-stage | System Manager: create,delete,email,export,print,read,report,share,write; Construction Owner: create,delete,email,export,print,read,report,share,write; Project Manager: create,email,export,print,read,report,write; Site Engineer: create,email,export,print,read,report,write; Accountant: email,export,print,read,report; Read-Only: read | UI-24–28,37–44; COV-05 |
| BOQ Quantity Revision — [boq_quantity_revision.json](../../../../construction/construction/doctype/boq_quantity_revision/boq_quantity_revision.json) | /app/boq-quantity-revision | System Manager: create,delete,email,export,print,read,report,share,write; Construction Owner: create,delete,email,export,print,read,report,share,write; Project Manager: create,email,export,print,read,report,share,write; Site Engineer: email,export,print,read,report; Accountant: email,export,print,read,report; Read-Only: read | UI-30–36 |
| BOQ Structure — [boq_structure.json](../../../../construction/construction/doctype/boq_structure/boq_structure.json) | /app/boq-structure | System Manager: create,delete,email,export,print,read,report,share,write; Construction Owner: create,delete,email,export,print,read,report,share,write; Project Manager: create,email,export,print,read,report,share,write; Site Engineer: read; Accountant: read; Read-Only: read | UI-09,11–14,34,51; COV-04 |
| Construction Settings — [construction_settings.json](../../../../construction/construction/doctype/construction_settings/construction_settings.json) | /app/construction-settings (Single) | System Manager: create,delete,email,export,print,read,report,share,write | UI-02,06,43 |
| Construction Theme — [construction_theme.json](../../../../construction/construction/doctype/construction_theme/construction_theme.json) | /app/construction-theme | System Manager: create,delete,email,print,read,share,write; Administrator: create,delete,email,print,read,share,write; All: read | UI-61,62 |
| CostItem — [cost_item.json](../../../../construction/construction/doctype/costitem/cost_item.json) | /app/costitem | System Manager: create,delete,email,export,print,read,report,share,write; Construction Owner: create,delete,email,export,print,read,report,share,write; Project Manager: create,email,export,print,read,report,share,write | UI-54; deployment/scaffold disposition |
| Direct Labor Designation — [direct_labor_designation.json](../../../../construction/construction/doctype/direct_labor_designation/direct_labor_designation.json) | Through parent table | Child table / no standalone permission rows | UI-02,43 via settings |
| Form Layout Profile — [form_layout_profile.json](../../../../construction/construction/doctype/form_layout_profile/form_layout_profile.json) | /app/form-layout-profile | System Manager: create,delete,email,export,print,read,report,share,write; All: read | UI-63–65 |
| Modern Theme Settings — [modern_theme_settings.json](../../../../construction/construction/doctype/modern_theme_settings/modern_theme_settings.json) | /app/modern-theme-settings (Single) | System Manager: create,read,write; All: read | UI-61,62 |
| PlantResource — [plant_resource.json](../../../../construction/construction/doctype/plantresource/plant_resource.json) | /app/plantresource | System Manager: create,delete,email,export,print,read,report,share,write | UI-54; deployment/scaffold disposition |
| Resource Price History — [resource_price_history.json](../../../../construction/construction/doctype/resource_price_history/resource_price_history.json) | /app/resource-price-history | System Manager: create,delete,email,export,print,read,report,share,write; Construction Owner: email,export,print,read,report; Project Manager: email,export,print,read,report | UI-15,38,40,46; F18/F19 additions |
| Scope Report Access Log — [scope_report_access_log.json](../../../../construction/construction/doctype/scope_report_access_log/scope_report_access_log.json) | /app/scope-report-access-log | System Manager: email,export,print,read,report,share; Auditor: email,export,print,read,report | UI-06 |
| User Desk Theme — [user_desk_theme.json](../../../../construction/construction/doctype/user_desk_theme/user_desk_theme.json) | /app/user-desk-theme | System Manager: create,delete,email,print,read,share,write; All: create,delete,read,write,if_owner | UI-61,62 |
| User Scope Context — [user_scope_context.json](../../../../construction/construction/doctype/user_scope_context/user_scope_context.json) | /app/user-scope-context | System Manager: create,delete,email,export,print,read,report,share,write; All: create,if_owner,read,write | UI-03–06 |
| Variation Order — [variation_order.json](../../../../construction/construction/doctype/variation_order/variation_order.json) | /app/variation-order | System Manager: create,delete,email,export,print,read,report,share,write; Construction Owner: create,email,export,print,read,report,share,write; Project Manager: create,email,export,print,read,report,share,write; Site Engineer: create,email,export,print,read,report,share,write | UI-29–36; COV-03 |
| VO Line — [vo_line.json](../../../../construction/construction/doctype/vo_line/vo_line.json) | Through parent table | Child table / no standalone permission rows | UI-29–36 via parent |

**Journal Entry:** ERPNext owns its schema. Construction supplies validation/integration behavior via hooks and its override-only folder; UI-44/F20/F24 must verify native balance/posting rules and construction row attribution. BOQ Item uses free-text `cost_item` and a `structure` link; it is not an ERPNext stock Item and is not a Header child table.

## 3. Desk navigation, pages, print surfaces and fixtures

### bilingual-report-viewer

Source candidate route `/app/bilingual-report-viewer`; [bilingual_report_viewer.json](../../../../construction/construction/page/bilingual_report_viewer/bilingual_report_viewer.json). Page role metadata: []. Empty page-role metadata does not grant report/company access; `localized_report` enforces its own boundary. Mapping: UI-57/58, F11/F12/F22.

### Construction workspace

[construction.json](../../../../construction/workspace/construction/construction.json). Source links: BOQ Header, BOQ Structure, BOQ Item, BOQ Item Stage, BOQ Import Batch, BOQ Cost Analysis, Resource Price History, Variation Order, BOQ Quantity Revision, Construction Theme, Modern Theme Settings, User Desk Theme, Form Layout Profile, User Scope Context, Construction Settings, Scope Report Access Log.

Source shortcuts: .

The v16 sidebar config lists Construction, BOQ Header, BOQ Structure, BOQ Item, BOQ Item Stage, Variation Order, Construction Theme, Modern Theme Settings, User Desk Theme, User Scope Context, Construction Settings. Workspace, sidebar, `desk_links` and install/migrate reconcilers are separate navigation sources; compare all with the chosen site before changing shortcuts. Cost analysis/price history appear in the workspace but not every sidebar source. This is a source difference, not a proven missing navigation defect. F21 reconciles intended role shortcuts.

| Print definition | Parent | Verification mapping |
|---|---|---|
| Construction Bilingual Material Request — [bilingual_material_request.json](../../../../construction/print_format/bilingual_material_request/bilingual_material_request.json) | Material Request | UI-52 for BOQ; UI-60 for four native commercial formats; F22 |
| Construction Bilingual Purchase Order — [bilingual_purchase_order.json](../../../../construction/print_format/bilingual_purchase_order/bilingual_purchase_order.json) | Purchase Order | UI-52 for BOQ; UI-60 for four native commercial formats; F22 |
| Construction Bilingual Sales Invoice — [bilingual_sales_invoice.json](../../../../construction/print_format/bilingual_sales_invoice/bilingual_sales_invoice.json) | Sales Invoice | UI-52 for BOQ; UI-60 for four native commercial formats; F22 |
| Construction Bilingual Stock Entry — [bilingual_stock_entry.json](../../../../construction/print_format/bilingual_stock_entry/bilingual_stock_entry.json) | Stock Entry | UI-52 for BOQ; UI-60 for four native commercial formats; F22 |
| BOQ Print Format — [boq_print_format.json](../../../../construction/print_format/boq_print_format/boq_print_format.json) | BOQ Header | UI-52 for BOQ; UI-60 for four native commercial formats; F22 |

Two fixture JSON files exist (UOM and Construction Theme). The hooks fixture declaration exports system Construction Theme records; source file presence does not prove every fixture is loaded. Install/migration setup also creates print formats, bilingual/custom fields, roles, profiles and navigation. F31/F34 must compare these with actual site records.

## 4. All eight registered transaction paths

Each native form is an existing ERPNext surface with construction custom fields added to its child rows. Common chain: `boq_header → boq_structure → boq_item → boq_item_stage`; `boq_selection_scope_type` is hidden provenance. Row gates and source defaults require site validation. Frozen and Locked are source-allowed transaction BOQ statuses; deployed flags/cascade strictness still need inspection.

| Native parent / child table | Construction applicability | Lifecycle hooks | Coverage |
|---|---|---|---|
| Purchase Order — items / Purchase Order Item | expense_category = Direct | validate; capture price on submit; mark price history cancelled on cancel | UI-38; F11/F20 |
| Purchase Receipt — items / Purchase Receipt Item | expense_category = Direct | validate | UI-39; F11/F20 |
| Purchase Invoice — items / Purchase Invoice Item | expense_category = Direct | validate; capture/cancel price history | UI-40; F11/F20 |
| Sales Invoice — items / Sales Invoice Item | is_progress_billing = 1 | validate | UI-41; F11/F20 |
| Stock Entry — items / Stock Entry Detail | expense_category = Direct | validate | UI-42; F11/F20 |
| Timesheet — time_logs / Timesheet Detail | designation in configured Direct Labor Designations | validate | UI-43; F11/F20 |
| Journal Entry — accounts / Journal Entry Account | expense_category = Direct | validate | UI-44; F11/F20 |
| Material Request — items / Material Request Item | expense_category = Direct | validate; VO linkage/invariant setup | UI-37; COV-03; F11/F20 |

Other native dependencies: Company/Cost Center/Project/Task, Item/resources/UOM, accounts and warehouse masters, buying/selling invoices, payments and Budget. Applicable RFQ/quotation/quality/asset flows are in UI-07/45–49; their vendor forms/reports are outside the Construction schema count. They still need configured fixtures and scope/finance validation.

## 5. Reports, existing services and missing interface evidence

| Surface | Source-defined contents | Boundary / completion work |
|---|---|---|
| Protected financial reports (11) | Accounts Payable, Accounts Payable Summary, Accounts Receivable, Accounts Receivable Summary, Balance Sheet, Budget Variance Report, Cash Flow, General Ledger, Profit and Loss Statement, Project-wise Profitability, Trial Balance | Native report/company/scope handling; UI-55, F11/F12 |
| Protected dashboard/report set (4) | Fixed Asset Register, Purchase Analytics, Purchase Order Trends, Purchase Receipt Trends | Native report/company/scope handling; UI-56, F11/F12 |
| Bilingual API allowlist (8) | General Ledger, Trial Balance, Accounts Receivable, Balance Sheet, Profit and Loss Statement, Accounts Receivable Summary, Accounts Payable Summary, Cash Flow | Native Report and Company access before vendor execution; viewer UI-57/58, F22; add Accounts Receivable aging comparison |
| Cost-report services (5) | get_boq_cost_analysis_summary; get_boq_item_cost_vs_contract; get_resource_requirement_summary; get_resource_price_history; get_boq_items_missing_analysis | No source Desk query-report definitions found under the Construction module; F19 supplies usable read-only views with permissions and limits |
| Cost database/repricing API | download template; import_cost_database; reprice_cost_analyses | No literal method callers found in shipped Desk JS/JSX scan; F18 confirms deployed interfaces then completes narrow UI |
| Rollup audit | Internal read-only service; no customer page defined | Administrator restriction retained; F10 technical audit/F19 appropriately restricted view |

**Coverage correction:** the earlier UI pack names seven bilingual comparisons but the actual source API allowlist includes **Accounts Receivable** as an eighth report. Add it; it is not interchangeable with Accounts Receivable Summary. The four bilingual commercial print formats and BOQ format remain separate surfaces.

Resource requirement summary currently uses the contract-quantity planning basis with factor, wastage and batch normalization. Do not label it a revised-quantity procurement forecast. Likewise, a generic invoice attribution field does not establish a certificate/retention module.

## 6. Settings and source defaults

These are schema defaults, not observed current values. Record site values and enabled/disabled behavior before test execution; settings cannot be treated as authorization grants.

| Control | Source type / default | F-package |
|---|---|---|
| enable_scope_context | Check / 1 | F11/F12 |
| enable_option_b_report_access_bypass | Check / 1 | F11/F12 |
| enable_scope_company | Check / 1 | F11/F12 |
| enable_scope_cost_center | Check / 1 | F11/F12 |
| enable_scope_project | Check / 1 | F11/F12 |
| enable_scope_department | Check / 0 | F11/F12 |
| enable_boq_cascade_filtering | Select / Off | F05/F06/F09/F20 |
| enable_boq_excel_import_preview | Check / 0 | F16/F17/F18 |
| enable_boq_excel_import_commit | Check / 0 | F16/F17/F18 |
| enable_boq_wbs_resequence | Check / 0 | F05/F06/F09/F20 |
| enable_stage_measurement_ui | Check / 0 | F05/F06/F09/F20 |
| enable_boq_scope_registry | Check / 0 | F11/F12 |
| enable_bilingual_boq_print | Check / 0 | F22/F23 |
| enable_variation_orders | Check / 0 | F05/F06/F09/F20 |
| enable_global_export_menu | Check / 1 | F22/F23 |
| enable_vfc_debug_logging | Check / 0 | F22/F23 |

Also inspect active scope dimensions, Scope Filter Exclusions and Direct Labor Designations. `feature_flags.py` validates seven rollout flag names separately from other settings. A rollout flag being present does not prove that its UI, endpoint or disabled-state guard is correctly wired.

## 7. Custom fields, translation governance and setup hooks

| Setup function / source | Literal field definitions discovered | Work |
|---|---|---|
| _get_boq_custom_fields_for_doctype — [install.py:303](../../../../construction/install.py) | expense_category (Select), boq_header (Link), boq_structure (Link), boq_item (Link), boq_item_stage (Link), boq_selection_scope_type (Select), is_progress_billing (Check), designation (Data) | F03/F20/F31/F34; confirm installed targets/defaults/permissions |
| _hide_legacy_expense_category_field — [install.py:436](../../../../construction/install.py) | expense_category () | F03/F20/F31/F34; confirm installed targets/defaults/permissions |
| setup_branch_company_field — [install.py:1012](../../../../construction/install.py) | company (), company (Link) | F03/F20/F31/F34; confirm installed targets/defaults/permissions |
| setup_variation_order_custom_field — [install.py:1036](../../../../construction/install.py) | custom_variation_order (), custom_variation_order (Link) | F03/F20/F31/F34; confirm installed targets/defaults/permissions |
| setup_item_construction_fields — [install.py:1409](../../../../construction/install.py) | item_name_ar (Data), is_construction_resource (Check), construction_resource_type (Select), default_cost_stream (Select), default_wastage_pct (Percent), default_productivity_qty_per_day (Float), labor_trade_designation (Link), linked_asset (Link) | F03/F20/F31/F34; confirm installed targets/defaults/permissions |

The bilingual registry supplies governed identity/search/display mappings for 23 source entries: Account, Item, Customer, Supplier, Cost Center, Warehouse, Project, Item Group, Customer Group, Supplier Group, Territory, UOM, Employee, Department, BOQ Structure, BOQ Header, Task, Asset Category, Payment Terms Template, Brand, Terms and Conditions, Asset, Company. Inspect actual custom fields through `bilingual_schema` setup; registry entries are not independent app DocTypes. Translation catalog fields and runtime overrides are another setup surface. F11/F22/F24/F31/F40 cover these policies; no account identity rename or catalog write is assumed safe from frontend visibility.

| Hook | Source registration | Coverage |
|---|---|---|
| boot_session | "construction.api.theme_api.add_theme_to_boot" | F11/F12/F23/F24 |
| extend_bootinfo | "construction.boot.extend_bootinfo" | F11/F12/F23/F24 |
| override_doctype_class | {"Translation": "construction.overrides.translation.CustomTranslation"} | F11/F12/F23/F24 |
| permission_query_conditions | {"expression": "{'*': 'construction.overrides.scope_query.add_scope_conditions', **{doctype: 'construction.overrides.boq_permissions.boq_parent_query_conditions' for doctype in ('BOQ Item', 'BOQ Structure', 'BOQ Item Stage', 'BOQ Quantity Revision', 'BOQ Cost Analysis', 'Variation Order')}}"} | F11/F12/F23/F24 |
| has_permission | {"expression": "{doctype: 'construction.overrides.boq_permissions.has_boq_parent_permission' for doctype in ('BOQ Item', 'BOQ Structure', 'BOQ Item Stage', 'BOQ Quantity Revision', 'BOQ Cost Analysis', 'Variation Order')}"} | F11/F12/F23/F24 |
| method override | frappe.core.doctype.user.user.switch_theme → construction.overrides.switch_theme_simple.switch_theme | F11/F12/F22/F24 |
| method override | frappe.utils.change_log.show_update_popup → construction.api.theme_api.ignore_update_popup | F11/F12/F22/F24 |
| method override | frappe.translate.update_translations_for_source → construction.api.translation_tools.update_translations_for_source_safe | F11/F12/F22/F24 |
| method override | erpnext.accounts.doctype.account.account.update_account_number → construction.services.bilingual_service.governed_rename_account | F11/F12/F22/F24 |
| method override | frappe.desk.search.search_link → construction.api.desk_link_search.search_link | F11/F12/F22/F24 |

Explicit event targets: *, Purchase Order, Purchase Receipt, Purchase Invoice, Stock Entry, Timesheet, Journal Entry, Sales Invoice, Material Request, BOQ Item Stage, Account, Item, Customer, Supplier, Cost Center, Warehouse, Project, Item Group, Customer Group, Supplier Group, Territory, UOM, Employee, Department, BOQ Structure, BOQ Header, Task, Asset Category, Payment Terms Template, Payment Term, Brand, Terms and Conditions, Asset, Company. Wildcard validate adds broader scope/branch checks; named BOQ permission hooks add parent authorization. Native account/bilingual/narrative hooks cover more than the 21 custom schemas and need positive/denied paths. Method and class overrides are only part of the global framework surface; report wrappers installed at import time must be reconciled separately.

After-install and after-migrate registrations are retained in the JSON inventory, together with patch declarations. They were not executed. Setup function presence is not proof of installed fields, roles, indexes, print formats or source schema migration.

## 8. Registered assets and form extensions

All entries below are hook registrations from this candidate. Site build identity, cache behavior and actual browser network loading remain pending F02/F25. A disk file not registered here may still load via a page, dynamic require, bundle or native DocType convention; it is not automatically dead code.

| Surface | Registration | Source file existence |
|---|---|---|
| app_include_js | /assets/construction/js/boq_export_columns.js?v=1 | Present |
| app_include_js | /assets/construction/js/print_settings_dialog.js | Present |
| app_include_js | /assets/construction/js/construction_export_menu.js | Present |
| app_include_js | /assets/construction/js/generic_export_menu.js?v=1 | Present |
| app_include_js | /assets/construction/js/theme_loader_v24.js?v=2.6.2 | Present |
| app_include_js | /assets/construction/js/typography_settings.js?v=21 | Present |
| app_include_js | /assets/construction/js/searchable_dropdown/utils.js | Present |
| app_include_js | /assets/construction/js/searchable_dropdown/searchable_dropdown.js?v=1 | Present |
| app_include_js | /assets/construction/js/overrides/ct_select_control.js?v=2 | Present |
| app_include_js | /assets/construction/js/overrides/ct_link_control.js?v=17 | Present |
| app_include_js | /assets/construction/js/theme_loader_v16.js?v=2 | Present |
| app_include_js | /assets/construction/js/scope_context.js?v=3 | Present |
| app_include_js | /assets/construction/js/frappe_compat_patches.js?v=2 | Present |
| app_include_js | /assets/construction/js/scope_context_ui.js?v=5 | Present |
| app_include_js | /assets/construction/js/scope_context_list_filter.js?v=3 | Present |
| app_include_js | /assets/construction/js/scope_context_form_defaults.js?v=3 | Present |
| app_include_js | /assets/construction/js/vfc_config.js?v=1 | Present |
| app_include_js | /assets/construction/js/scope_context_report_filters.js?v=4 | Present |
| app_include_js | /assets/construction/js/ct_list_view_config.js?v=1 | Present |
| app_include_js | /assets/construction/js/sidebar_accordion.js?v=1 | Present |
| app_include_js | /assets/construction/js/translation_list_tools.js?v=6 | Present |
| app_include_js | /assets/construction/js/boq_filters.js?v=8 | Present |
| app_include_js | /assets/construction/js/filter_fix.js?v=11 | Present |
| app_include_js | /assets/construction/js/native_frappe_controls_compat.js?v=9 | Present |
| app_include_js | /assets/construction/js/vite_layout_controls.js?v=1.21 | Present |
| app_include_js | /assets/construction/js/vfc_layout_engine.js?v=1.44 | Present |
| app_include_css | /assets/construction/css/modern_theme.css?v=2.5.9 | Present |
| app_include_css | /assets/construction/css/scope_context.css?v=2 | Present |
| app_include_css | /assets/construction/css/vite_extensions.css?v=1.3 | Present |
| app_include_css | /assets/construction/css/vite_form_override.css?v=1.5 | Present |
| app_include_css | /assets/construction/css/vite_list_override.css?v=1.3 | Present |
| app_include_css | /assets/construction/css/vfc_sections.css?v=1.6 | Present |
| doctype_js / BOQ Header | construction/construction/doctype/boq_header/boq_header.js | Source path candidate present |
| doctype_js / BOQ Item | construction/construction/doctype/boq_item/boq_item.js | Source path candidate present |
| doctype_js / BOQ Item Stage | construction/construction/doctype/boq_item_stage/boq_item_stage.js | Source path candidate present |
| doctype_js / Construction Settings | construction/construction/doctype/construction_settings/construction_settings.js | Source path candidate present |
| doctype_js / Scope Report Access Log | construction/construction/doctype/scope_report_access_log/scope_report_access_log.js | Source path candidate present |
| doctype_js / User Desk Theme | construction/construction/doctype/user_desk_theme/user_desk_theme.js | Source path candidate present |
| doctype_js / Variation Order | construction/construction/doctype/variation_order/variation_order.js | Source path candidate present |
| doctype_js / Account | public/js/bilingual/account_form.js | Source path candidate present |
| doctype_list_js / Item | construction/public/js/item_list.js | Source path candidate present |
| doctype_list_js / BOQ Item | construction/construction/doctype/boq_item/boq_item_list.js | Source path candidate present |
| doctype_list_js / BOQ Structure | construction/construction/doctype/boq_structure/boq_structure_list.js | Source path candidate present |
| doctype_list_js / Variation Order | construction/construction/doctype/variation_order/variation_order_list.js | Source path candidate present |
| doctype_tree_js / BOQ Structure | construction/construction/doctype/boq_structure/boq_structure_tree.js | Source path candidate present |
| doctype_tree_js / Account | public/js/bilingual/account_tree.js | Source path candidate present |

Website/login/email/print styling is separately registered through web_include_css/js, brand/login context, email_css, print_css and PDF header/footer hooks. JSON inventory preserves these. Verify anonymous website/login behavior and privileged-theme boundaries separately from authenticated Desk. Source `get_user_theme_for_boot` is guest-enabled; this is an explicit review surface, not a demonstrated disclosure.

## 9. Decorated method inventory — all 108 definitions

Module-method candidates normally use `/api/method/<identity>`; document methods run through a document-method path with parent permissions. The global report wrapper and override registrations may also route vendor methods here. Methods without explicit decorator methods use framework defaults that must be confirmed on the chosen runtime. No HTTP request was sent.

“Caller refs” counts exact dotted-identity references in non-test source; dynamic/short document calls can be absent from that scan. “Guard signals” are literal hints in the function body, not an authorization assessment. Full decorators, arguments, flags, file/line and caller locations are in the JSON artifact.

| Identity / kind | Source | Declared HTTP methods / guest | Caller refs | Body guard signals | Work mapping |
|---|---|---|---:|---|---|
| construction.api.bilingual_reports.localized_report | [bilingual_reports.py:155](../../../../construction/api/bilingual_reports.py) | "framework default; verify runtime"; guest=False | 1 | frappe.only_for | F12/F19/F22 |
| construction.api.boq_api.get_children | [boq_api.py:22](../../../../construction/api/boq_api.py) | "framework default; verify runtime"; guest=False | 1 | require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.add_node | [boq_api.py:86](../../../../construction/api/boq_api.py) | ["POST"]; guest=False | 1 | has_permission, require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.create_boq_node | [boq_api.py:115](../../../../construction/api/boq_api.py) | ["POST"]; guest=False | 0 | has_permission, require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.advance_boq_status | [boq_api.py:133](../../../../construction/api/boq_api.py) | ["POST"]; guest=False | 1 | require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.export_boq_header_pdf | [boq_api.py:157](../../../../construction/api/boq_api.py) | "framework default; verify runtime"; guest=False | 1 | has_permission, require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.export_boq_header_excel | [boq_api.py:176](../../../../construction/api/boq_api.py) | "framework default; verify runtime"; guest=False | 1 | has_permission, require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.export_boq_excel | [boq_api.py:195](../../../../construction/api/boq_api.py) | "framework default; verify runtime"; guest=False | 3 | has_permission, require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.export_boq_pdf | [boq_api.py:214](../../../../construction/api/boq_api.py) | "framework default; verify runtime"; guest=False | 3 | has_permission, require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.import_boq_excel | [boq_api.py:233](../../../../construction/api/boq_api.py) | ["POST"]; guest=False | 1 | require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.generate_boq_import_error_report | [boq_api.py:249](../../../../construction/api/boq_api.py) | "framework default; verify runtime"; guest=False | 0 | require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.bulk_update_boq_item_stages | [boq_api.py:267](../../../../construction/api/boq_api.py) | ["POST"]; guest=False | 0 | has_permission | F05/F06/F09/F16/F20 |
| construction.api.boq_api.create_variation_order | [boq_api.py:310](../../../../construction/api/boq_api.py) | ["POST"]; guest=False | 1 | has_permission, require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.transition_variation_order | [boq_api.py:345](../../../../construction/api/boq_api.py) | ["POST"]; guest=False | 1 | has_permission | F05/F06/F09/F16/F20 |
| construction.api.boq_api.get_variation_order_summary | [boq_api.py:416](../../../../construction/api/boq_api.py) | "framework default; verify runtime"; guest=False | 1 | require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.is_variation_orders_enabled | [boq_api.py:439](../../../../construction/api/boq_api.py) | "framework default; verify runtime"; guest=False | 2 | None matched; inspect delegated helpers | F05/F06/F09/F16/F20 |
| construction.api.boq_api.get_revised_boq_view | [boq_api.py:447](../../../../construction/api/boq_api.py) | "framework default; verify runtime"; guest=False | 1 | require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.create_material_request_for_vo | [boq_api.py:460](../../../../construction/api/boq_api.py) | ["POST"]; guest=False | 1 | has_permission, require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.get_boq_tree_summary | [boq_api.py:576](../../../../construction/api/boq_api.py) | "framework default; verify runtime"; guest=False | 0 | require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.get_boq_structure_summary | [boq_api.py:597](../../../../construction/api/boq_api.py) | "framework default; verify runtime"; guest=False | 0 | require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_api.get_boq_header_scope_context | [boq_api.py:638](../../../../construction/api/boq_api.py) | "framework default; verify runtime"; guest=False | 0 | require_boq_access | F05/F06/F09/F16/F20 |
| construction.api.boq_link_queries.get_boq_scope_token | [boq_link_queries.py:74](../../../../construction/api/boq_link_queries.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F12/F20 |
| construction.api.boq_link_queries.log_boq_scope_drift | [boq_link_queries.py:80](../../../../construction/api/boq_link_queries.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F12/F20 |
| construction.api.boq_link_queries.get_scope_projects | [boq_link_queries.py:94](../../../../construction/api/boq_link_queries.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F11/F12/F20 |
| construction.api.boq_link_queries.get_allowed_transaction_boq_statuses | [boq_link_queries.py:131](../../../../construction/api/boq_link_queries.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F11/F12/F20 |
| construction.api.boq_link_queries.get_boq_headers | [boq_link_queries.py:137](../../../../construction/api/boq_link_queries.py) | "framework default; verify runtime"; guest=False | 6 | None matched; inspect delegated helpers | F11/F12/F20 |
| construction.api.boq_link_queries.get_boq_structures | [boq_link_queries.py:177](../../../../construction/api/boq_link_queries.py) | "framework default; verify runtime"; guest=False | 5 | None matched; inspect delegated helpers | F11/F12/F20 |
| construction.api.boq_link_queries.get_boq_items | [boq_link_queries.py:248](../../../../construction/api/boq_link_queries.py) | "framework default; verify runtime"; guest=False | 4 | None matched; inspect delegated helpers | F11/F12/F20 |
| construction.api.boq_link_queries.get_boq_item_stages | [boq_link_queries.py:309](../../../../construction/api/boq_link_queries.py) | "framework default; verify runtime"; guest=False | 2 | None matched; inspect delegated helpers | F11/F12/F20 |
| construction.api.boq_link_queries.get_variation_orders | [boq_link_queries.py:376](../../../../construction/api/boq_link_queries.py) | "framework default; verify runtime"; guest=False | 0 | has_permission | F11/F12/F20 |
| construction.api.boq_link_queries.get_vo_line_boq_items | [boq_link_queries.py:448](../../../../construction/api/boq_link_queries.py) | "framework default; verify runtime"; guest=False | 1 | has_permission | F11/F12/F20 |
| construction.api.boq_link_queries.get_variation_structures | [boq_link_queries.py:521](../../../../construction/api/boq_link_queries.py) | "framework default; verify runtime"; guest=False | 0 | has_permission | F11/F12/F20 |
| construction.api.cost_database_api.import_cost_database | [cost_database_api.py:13](../../../../construction/api/cost_database_api.py) | ["POST"]; guest=False | 0 | has_permission | F14/F18 |
| construction.api.cost_database_api.download_cost_database_template | [cost_database_api.py:68](../../../../construction/api/cost_database_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F14/F18 |
| construction.api.cost_database_api.reprice_cost_analyses | [cost_database_api.py:117](../../../../construction/api/cost_database_api.py) | ["POST"]; guest=False | 0 | has_permission | F14/F18 |
| construction.api.desk_link_search.search_link | [desk_link_search.py:284](../../../../construction/api/desk_link_search.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F12/F24 |
| construction.api.export_api.export_doctype_excel | [export_api.py:63](../../../../construction/api/export_api.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F14/F22 |
| construction.api.export_api.export_doctype_list_excel | [export_api.py:107](../../../../construction/api/export_api.py) | "framework default; verify runtime"; guest=False | 1 | has_permission | F11/F14/F22 |
| construction.api.export_api.export_doctype_pdf | [export_api.py:156](../../../../construction/api/export_api.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F14/F22 |
| construction.api.export_api.export_doctype_list_pdf | [export_api.py:200](../../../../construction/api/export_api.py) | "framework default; verify runtime"; guest=False | 1 | has_permission | F11/F14/F22 |
| construction.api.modern_form_api.get_form_config | [modern_form_api.py:27](../../../../construction/api/modern_form_api.py) | "framework default; verify runtime"; guest=False | 0 | _require_system_manager | F11/F26 |
| construction.api.modern_form_api.get_document | [modern_form_api.py:91](../../../../construction/api/modern_form_api.py) | "framework default; verify runtime"; guest=False | 0 | _require_system_manager | F11/F26 |
| construction.api.modern_form_api.create_document | [modern_form_api.py:132](../../../../construction/api/modern_form_api.py) | "framework default; verify runtime"; guest=False | 0 | _require_system_manager | F11/F26 |
| construction.api.modern_form_api.update_document | [modern_form_api.py:174](../../../../construction/api/modern_form_api.py) | "framework default; verify runtime"; guest=False | 0 | _require_system_manager, has_permission | F11/F26 |
| construction.api.modern_form_api.delete_document | [modern_form_api.py:222](../../../../construction/api/modern_form_api.py) | "framework default; verify runtime"; guest=False | 0 | _require_system_manager, has_permission | F11/F26 |
| construction.api.modern_form_api.validate_field | [modern_form_api.py:253](../../../../construction/api/modern_form_api.py) | "framework default; verify runtime"; guest=False | 1 | _require_system_manager | F11/F26 |
| construction.api.modern_form_api.search_link | [modern_form_api.py:307](../../../../construction/api/modern_form_api.py) | "framework default; verify runtime"; guest=False | 1 | _require_system_manager | F11/F26 |
| construction.api.scope_context_api.set_scope_context | [scope_context_api.py:256](../../../../construction/api/scope_context_api.py) | "framework default; verify runtime"; guest=False | 1 | validate_scope | F11/F12 |
| construction.api.scope_context_api.get_scope_hierarchy_detail | [scope_context_api.py:403](../../../../construction/api/scope_context_api.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F12 |
| construction.api.scope_context_api.quick_create | [scope_context_api.py:502](../../../../construction/api/scope_context_api.py) | "framework default; verify runtime"; guest=False | 0 | has_permission | F11/F12 |
| construction.api.scope_context_api.get_active_scope_summary | [scope_context_api.py:514](../../../../construction/api/scope_context_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F11/F12 |
| construction.api.scope_context_api.get_project_display_name | [scope_context_api.py:533](../../../../construction/api/scope_context_api.py) | "framework default; verify runtime"; guest=False | 1 | has_permission | F11/F12 |
| construction.api.scope_context_api.get_scope_dimension_permissions | [scope_context_api.py:579](../../../../construction/api/scope_context_api.py) | "framework default; verify runtime"; guest=False | 1 | has_permission | F11/F12 |
| construction.api.theme_api.get_effective_desk_theme | [theme_api.py:11](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.get_available_themes | [theme_api.py:233](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.get_user_theme_settings | [theme_api.py:257](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.save_user_theme_settings | [theme_api.py:285](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.get_modern_theme_settings | [theme_api.py:334](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 0 | has_permission | F15/F22/F23 |
| construction.api.theme_api.save_modern_theme_settings | [theme_api.py:360](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 0 | has_permission | F15/F22/F23 |
| construction.api.theme_api.get_theme_css_variables | [theme_api.py:418](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.save_user_mode | [theme_api.py:488](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 2 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.set_user_theme | [theme_api.py:2305](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.list_available_themes | [theme_api.py:2371](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.get_theme_css | [theme_api.py:2451](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.preview_theme | [theme_api.py:2695](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.get_user_construction_theme | [theme_api.py:2740](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.get_user_theme_for_boot | [theme_api.py:2806](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=True | 0 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.get_user_typography_settings | [theme_api.py:3050](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.save_user_typography_settings | [theme_api.py:3090](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.theme_api.ignore_update_popup | [theme_api.py:3281](../../../../construction/api/theme_api.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.api.translation_tools.update_translations_for_source_safe | [translation_tools.py:117](../../../../construction/api/translation_tools.py) | "framework default; verify runtime"; guest=False | 1 | frappe.only_for | F11/F22/F40 |
| construction.api.translation_tools.seed_missing_arabic_translations | [translation_tools.py:164](../../../../construction/api/translation_tools.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F11/F22/F40 |
| construction.api.translation_tools.get_missing_arabic_translation_sources | [translation_tools.py:177](../../../../construction/api/translation_tools.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F22/F40 |
| construction.api.translation_tools.get_placeholder_arabic_translation_sources | [translation_tools.py:185](../../../../construction/api/translation_tools.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F22/F40 |
| construction.api.translation_tools.normalize_translation_keys | [translation_tools.py:205](../../../../construction/api/translation_tools.py) | "framework default; verify runtime"; guest=False | 1 | frappe.only_for | F11/F22/F40 |
| construction.api.translation_tools.apply_glossary_corrections | [translation_tools.py:251](../../../../construction/api/translation_tools.py) | "framework default; verify runtime"; guest=False | 1 | frappe.only_for | F11/F22/F40 |
| construction.api.translation_tools.import_review_queue | [translation_tools.py:313](../../../../construction/api/translation_tools.py) | "framework default; verify runtime"; guest=False | 1 | frappe.only_for | F11/F22/F40 |
| construction.api.translation_tools.get_translation_catalog_stats | [translation_tools.py:406](../../../../construction/api/translation_tools.py) | "framework default; verify runtime"; guest=False | 1 | frappe.only_for | F11/F22/F40 |
| construction.api.translation_tools.sync_translation_catalog | [translation_tools.py:428](../../../../construction/api/translation_tools.py) | "framework default; verify runtime"; guest=False | 1 | frappe.only_for | F11/F22/F40 |
| construction.api.translation_tools.reset_catalog_overrides | [translation_tools.py:599](../../../../construction/api/translation_tools.py) | "framework default; verify runtime"; guest=False | 0 | frappe.only_for | F11/F22/F40 |
| construction.api.translation_tools.search_arabic_translations | [translation_tools.py:648](../../../../construction/api/translation_tools.py) | "framework default; verify runtime"; guest=False | 0 | frappe.only_for | F11/F22/F40 |
| construction.construction.api.layout_api.get_active_layout | [layout_api.py:35](../../../../construction/construction/api/layout_api.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F23 |
| construction.construction.api.layout_api.save_layout | [layout_api.py:116](../../../../construction/construction/api/layout_api.py) | "framework default; verify runtime"; guest=False | 1 | _require_system_manager | F11/F23 |
| construction.construction.api.layout_api.list_layouts | [layout_api.py:184](../../../../construction/construction/api/layout_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F11/F23 |
| construction.construction.api.layout_api.delete_my_personal_layout | [layout_api.py:210](../../../../construction/construction/api/layout_api.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F23 |
| construction.construction.api.layout_api.delete_layout | [layout_api.py:237](../../../../construction/construction/api/layout_api.py) | "framework default; verify runtime"; guest=False | 0 | _require_system_manager | F11/F23 |
| construction.construction.api.layout_api.validate_layout | [layout_api.py:261](../../../../construction/construction/api/layout_api.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F11/F23 |
| BOQStructure.convert_group_to_ledger (document method) | [boq_structure.py:210](../../../../construction/construction/doctype/boq_structure/boq_structure.py) | "framework default; verify runtime"; guest=False | 0 | check_permission | F05/F06 |
| BOQStructure.convert_ledger_to_group (document method) | [boq_structure.py:223](../../../../construction/construction/doctype/boq_structure/boq_structure.py) | "framework default; verify runtime"; guest=False | 0 | check_permission | F05/F06 |
| construction.insert_translations.get_arabic_translation_drift | [insert_translations.py:198](../../../../construction/insert_translations.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F11/F22/F40 |
| construction.insert_translations.get_arabic_translation_seed_status | [insert_translations.py:206](../../../../construction/insert_translations.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F11/F22/F40 |
| construction.overrides.scope_report._scope_aware_run | [scope_report.py:821](../../../../construction/overrides/scope_report.py) | ["GET", "POST"]; guest=False | 0 | has_permission | F03/F11/F24 |
| construction.overrides.switch_theme.switch_theme | [switch_theme.py:20](../../../../construction/overrides/switch_theme.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.overrides.switch_theme_simple.switch_theme | [switch_theme_simple.py:13](../../../../construction/overrides/switch_theme_simple.py) | "framework default; verify runtime"; guest=False | 2 | None matched; inspect delegated helpers | F15/F22/F23 |
| construction.searchable_dropdown.api.search.searchable_link_search | [search.py:11](../../../../construction/searchable_dropdown/api/search.py) | "framework default; verify runtime"; guest=False | 5 | None matched; inspect delegated helpers | F11/F12/F24 |
| construction.searchable_dropdown.api.search.get_recent_items | [search.py:266](../../../../construction/searchable_dropdown/api/search.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F11/F12/F24 |
| construction.services.bilingual_service.get_account_identity | [bilingual_service.py:356](../../../../construction/services/bilingual_service.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F22/F24 |
| construction.services.bilingual_service.set_account_name_ar | [bilingual_service.py:372](../../../../construction/services/bilingual_service.py) | "framework default; verify runtime"; guest=False | 1 | has_permission | F11/F22/F24 |
| construction.services.bilingual_service.governed_rename_account | [bilingual_service.py:676](../../../../construction/services/bilingual_service.py) | "framework default; verify runtime"; guest=False | 2 | has_permission | F11/F22/F24 |
| construction.services.bilingual_service.record_account_rename_reason | [bilingual_service.py:748](../../../../construction/services/bilingual_service.py) | "framework default; verify runtime"; guest=False | 0 | has_permission | F11/F22/F24 |
| construction.services.bilingual_service.get_account_tree_children | [bilingual_service.py:961](../../../../construction/services/bilingual_service.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F22/F24 |
| construction.services.boq_wbs_health.run_wbs_health_check | [boq_wbs_health.py:40](../../../../construction/services/boq_wbs_health.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F05/F10 |
| construction.services.transaction_link_search.search_transactions | [transaction_link_search.py:220](../../../../construction/services/transaction_link_search.py) | "framework default; verify runtime"; guest=False | 1 | None matched; inspect delegated helpers | F11/F12/F24 |
| construction.services.wbs_generator.resequence_wbs | [wbs_generator.py:123](../../../../construction/services/wbs_generator.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F05/F10 |
| construction.translation_service.get_translation_health_api | [translation_service.py:821](../../../../construction/translation_service.py) | "framework default; verify runtime"; guest=False | 0 | frappe.only_for | F11/F22/F40 |
| construction.translation_service.assert_translation_health_api | [translation_service.py:827](../../../../construction/translation_service.py) | "framework default; verify runtime"; guest=False | 0 | frappe.only_for | F11/F22/F40 |
| construction.translation_service.diagnose_translation | [translation_service.py:833](../../../../construction/translation_service.py) | "framework default; verify runtime"; guest=False | 0 | frappe.only_for | F11/F22/F40 |
| construction.translation_service.diagnose_translation_api | [translation_service.py:945](../../../../construction/translation_service.py) | "framework default; verify runtime"; guest=False | 0 | None matched; inspect delegated helpers | F11/F22/F40 |

Legacy `modern_form_api` methods remain source-decorated but explicitly restricted to System Manager; active native/VFC forms are the supported architecture. Another `switch_theme.py` method exists while the hooks map theme switching to `switch_theme_simple.py`; do not assume every source method is the live hook consumer. `workspace_api.update_construction_workspace` is a setup helper without a whitelist decorator and is not included as a direct HTTP method.

## 10. MCP/tooling and correction to UAT-D005

The MCP bridge is a separate runtime with tools for BOQ header/tree, scope context, themes, layout, schema, document/list and guarded SELECT. DocType/SQL allowlists are not per-user document permissions. Audit header/tree/list/SQL tools under F11/F27 against intended identity and scope; a filtered `get_all` query alone does not enforce Frappe permissions. Prefer permission-aware retrieval plus explicit parent/document authorization, or justify and test a bounded lower-level query after those checks.

The F01 handoff asserted that `doc.get("items", [])` always produces `items: []`. That exact symptom was unsupported. Local Frappe `BaseDocument.get(self, key, filters=None, limit=None, default=None)` treats the second argument as filters, and the empty list is falsy; therefore the default remains None. A pure-Python probe executed the extracted, inspected method with an empty object and returned **None**; iterating it raised **TypeError: 'NoneType' object is not iterable**. This probe imported no Frappe/app module and connected to no site. It proves the local expression behavior only, not the deployed bridge outcome.

Local Frappe checkout reference: `81aadb9ba1bc07abccd8f720af80f4f2fb4a68a0`, method at `frappe/model/base_document.py:327`. It is not a supported/deployed runtime declaration for this program. BOQ Header lacks a child items field and BOQ Item has a Header link, so the schema mismatch remains confirmed regardless of symptom. Correct the defect record; preserve the earlier assertion as superseded, not a runtime reproduction.

K-01 remains a source caller/API-default trace: the Import Excel handler omits `dry_run`; preview returns success and the handler displays success. Actual UI outcome and record counts are still owed on the isolated F16 target. F16-R/F27-R remain Not Run for actual UI/bridge reproduction.

## 11. Additional coverage discovered by F03

These are required coverage additions or decisions, not newly confirmed runtime defects. F43 assigns final UI IDs and scripts; F11 supplies API/denied-path evidence for engineering-only tools.

| Coverage ref | Source-discovered behavior | Required acceptance / mapping |
|---|---|---|
| COV-01 | Bilingual API has eight reports, including Accounts Receivable aging | Add populated native-versus-viewer aging comparison, period/scope/error/export checks; UI-57 extension, F22/F43 |
| COV-02 | Governed Account Arabic identity/rename endpoints and bilingual native masters | Allowed/denied Arabic-name change and reasoned identity rename, preserved ledger references, cache/search/prints; separate from UI-59 lookup smoke; F11/F22/F24 |
| COV-03 | Approved VO → Create → Create Material Request button | Correct draft rows/linkage, missing resource mapping behavior, repeat request/idempotency, permissions and cancel/replacement lifecycle; F06/F20/F43 |
| COV-04 | Structure group/ledger conversion; WBS resequence and health endpoints | Eligible/unlinked versus blocked/linked conversion, subtree/rollup integrity, guarded resequence and disabled flag; service-only route disposition where no UI caller exists; F05/F10/F43 |
| COV-05 | Bulk stage update endpoint behind enable_stage_measurement_ui | Batch failure atomicity, certification/locked-policy denial and UI availability classification; F09/F11/F43 |
| COV-06 | Translation catalog/review/normalization/glossary/runtime override operations | Admin allow/deny, dry-run where offered, changed wording in Arabic, key/provenance preservation and reset; F11/F22/F40/F43 |
| COV-07 | Generic document/list exports distinct from BOQ exports | Native invoice/master selected/list filters, file access, scope, bounds and bilingual output; UI-52/60 extensions, F11/F14/F22 |
| COV-08 | Guest theme boot, website/login/print hooks and dormant decorated methods | Minimal guest responses and no privileged mutation/disclosure; supported versus dormant method dispositions; F11/F15/F23/F24/F26 |
| COV-09 | Install-created metadata versus source JSON defaults | Compare fields, roles, workspaces/sidebars, print formats, indexes and settings with authorized UAT site; F02/F03/F31/F34 |
| COV-10 | Existing cost services and resource library lack established Desk caller evidence | Complete F18/F19 interfaces and their added UAT cases; preserve existing service semantics and permissions |

## 12. Installed-site reconciliation still required to close F03

Once F01 names the people/site and F02 confirms safe access, use read-only metadata checks on that named target:

1. Record installed Construction/Frappe/ERPNext/build versions and customizations, not only source HEAD.
2. Enumerate effective DocType fields/roles, User Permissions and relevant shares; compare every source schema and native integration field.
3. Enumerate actual workspace/sidebar/page/report/print records, their disabled/role state and default formats; identify custom site scripts absent from the repo.
4. Record all flag values, scope dimensions/exclusions, Direct Labor Designations and profile/theme records.
5. Verify actual asset resolution, page loading and callable method registrations without executing business mutations; retain status/permission evidence.
6. Map every additional active customization or missing promised route to a task, script and owner; confirm exclusions explicitly.
7. Complete the site columns in the owner results inventory, review with Mohamed, and then close F03 against that exact candidate/site.

No installed-site column has been fabricated. This source inventory can unblock independent scope/test design while F02 remains pending; it cannot certify a deployable feature map or mark F03 complete.

## 13. Verification and files read

Both local startup checks passed: schema facts 21 owners + one override; context 11 passes, zero failures. Git HEAD remains the recorded candidate; existing source modifications were absent. Local tracking refs show 0 ahead/0 behind, with no network fetch performed. All 108 discovered decorator definitions parsed without syntax errors. Source JSON/roles, hook registrations, API/module/document definitions, client literal references, custom field setup, settings, report sets and artifacts were reconciled structurally; links/tables and counts were checked.

Read the repository AGENTS/Professional Engineering Standard/context index/workflow/current session/schema summary, F01 gap ledger and defect records, master/register, hooks, DocType/Page/Workspace/Print JSON, relevant API and service modules, custom-field/install setup, sidebar/bilingual registry, bridge source and local BaseDocument.get implementation. The JSON artifact lists 71 exact source-file hashes plus the vendor-method probe hash. No application change, site/database request, business suite, migration, commit, push, deployment or calendar booking occurred. The isolated Python expression probe is explicitly identified above.
