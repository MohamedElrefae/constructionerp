# Schema Facts - Verified DocType Schemas

> Generated from live DocType JSON by `scripts/schema_drift_checker.py --update`.
> Do not hand-edit field tables. Update the DocType JSON, then regenerate this file.
> Last verified: 2026-08-19

## Summary

- Schema-owning DocTypes: 21
- Override-only DocType folders: 1
- Source path: `construction/construction/doctype/*/*.json`

| Folder | DocType | JSON | Fields | Notes |
|---|---|---|---:|---|
| `boq_cost_analysis` | BOQ Cost Analysis | `boq_cost_analysis.json` | 30 |  |
| `boq_cost_analysis_detail` | BOQ Cost Analysis Detail | `boq_cost_analysis_detail.json` | 11 | Child table |
| `boq_header` | BOQ Header | `boq_header.json` | 12 |  |
| `boq_import_batch` | BOQ Import Batch | `boq_import_batch.json` | 18 |  |
| `boq_item` | BOQ Item | `boq_item.json` | 48 |  |
| `boq_item_stage` | BOQ Item Stage | `boq_item_stage.json` | 16 |  |
| `boq_quantity_revision` | BOQ Quantity Revision | `boq_quantity_revision.json` | 35 |  |
| `boq_structure` | BOQ Structure | `boq_structure.json` | 31 |  |
| `construction_settings` | Construction Settings | `construction_settings.json` | 28 |  |
| `construction_theme` | Construction Theme | `construction_theme.json` | 94 |  |
| `costitem` | CostItem | `cost_item.json` | 9 |  |
| `direct_labor_designation` | Direct Labor Designation | `direct_labor_designation.json` | 2 | Child table |
| `form_layout_profile` | Form Layout Profile | `form_layout_profile.json` | 13 |  |
| `modern_theme_settings` | Modern Theme Settings | `modern_theme_settings.json` | 10 |  |
| `plantresource` | PlantResource | `plant_resource.json` | 5 |  |
| `resource_price_history` | Resource Price History | `resource_price_history.json` | 22 |  |
| `scope_report_access_log` | Scope Report Access Log | `scope_report_access_log.json` | 12 |  |
| `user_desk_theme` | User Desk Theme | `user_desk_theme.json` | 25 |  |
| `user_scope_context` | User Scope Context | `user_scope_context.json` | 10 |  |
| `variation_order` | Variation Order | `variation_order.json` | 18 |  |
| `vo_line` | VO Line | `vo_line.json` | 27 | Child table |
| `journal_entry` | Journal Entry | - | - | Override only; no local schema JSON |

## Critical Invariants

- `BOQ Item` uses `cost_item` as a `Data` field and must not define `item_code` or `item_name`.
- `BOQ Structure` must keep NestedSet fields: `lft`, `rgt`, `old_parent`, `is_group`, `wbs_code`.
- `CostItem` uses `cost_item_code`; it must not be confused with ERPNext `Item.item_code`.
- `PlantResource` uses `resource_code`, `equipment_type`, and hourly cost fields.
- `journal_entry` is override-only in this app; its schema belongs to ERPNext core.

## Field Snapshot

### BOQ Cost Analysis (`boq_cost_analysis/boq_cost_analysis.json`) - 30 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `naming_series` | Select | BCA-.YYYY.- | reqd |
| `title` | Data |  | reqd |
| `boq_item` | Link | BOQ Item |  |
| `boq_header` | Link | BOQ Header | read_only |
| `boq_structure` | Link | BOQ Structure | read_only |
| `project` | Link | Project | read_only |
| `company` | Link | Company | reqd |
| `analysis_status` | Select | Draft / Approved / Superseded | reqd |
| `cb_identity` | Column Break |  |  |
| `analysis_uom` | Link | UOM | reqd |
| `analysis_qty` | Float |  | reqd |
| `effective_date` | Date |  |  |
| `currency` | Link | Currency | reqd |
| `is_template` | Check |  |  |
| `template_name` | Data |  |  |
| `category` | Data |  |  |
| `description_ar` | Small Text |  |  |
| `sb_details` | Section Break |  |  |
| `details` | Table | BOQ Cost Analysis Detail | reqd |
| `sb_totals` | Section Break |  |  |
| `total_direct_cost` | Currency |  | read_only |
| `overhead_pct` | Percent |  |  |
| `profit_pct` | Percent |  |  |
| `total_unit_cost` | Currency |  | read_only |
| `cb_totals` | Column Break |  |  |
| `suggested_sell_rate` | Currency |  | read_only |
| `sb_approval` | Section Break |  |  |
| `approved_by` | Link | User | read_only |
| `approved_on` | Datetime |  | read_only |
| `remarks` | Small Text |  |  |

### BOQ Cost Analysis Detail (`boq_cost_analysis_detail/boq_cost_analysis_detail.json`) - 11 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `cost_stream` | Select | M / L / P / S / O | reqd |
| `item_code` | Link | Item | reqd |
| `item_name` | Data |  | read_only |
| `resource_uom` | Link | UOM | reqd |
| `qty_per_boq_unit` | Float |  | reqd |
| `wastage_pct` | Percent |  |  |
| `cost_rate` | Currency |  | reqd |
| `amount` | Currency |  | read_only |
| `rate_source` | Select | Manual / Import / Item Price / Last PI / Last PO / Weighted Average / Supplier-Specific / Project-Specific / Resource Price History / Template |  |
| `supplier` | Link | Supplier |  |
| `remarks` | Small Text |  |  |

### BOQ Header (`boq_header/boq_header.json`) - 12 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `project` | Data |  | reqd, hidden, read_only |
| `project_name` | Data |  | read_only |
| `boq_type` | Select | Tender / Contract / Variation |  |
| `status` | Select | Draft / Pricing / Frozen / Locked |  |
| `version` | Int |  |  |
| `title` | Data |  |  |
| `total_contract_value` | Currency |  | read_only |
| `total_estimated_value` | Currency |  | read_only |
| `total_budgeted_cost` | Currency |  | read_only |
| `total_revised_value` | Currency |  | read_only |
| `locked_by` | Link | User | hidden, read_only |
| `locked_date` | Datetime |  | hidden, read_only |

### BOQ Import Batch (`boq_import_batch/boq_import_batch.json`) - 18 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `boq_header` | Link | BOQ Header | reqd |
| `project` | Link | Project | read_only |
| `status` | Select | Preview / Committed / Failed / Cancelled |  |
| `import_mode` | Select | Structured / Semi-Structured / Flat |  |
| `source_file` | Attach |  |  |
| `source_file_name` | Data |  |  |
| `sheet_name` | Data |  |  |
| `sb_counts` | Section Break |  |  |
| `row_count` | Int |  |  |
| `section_count` | Int |  |  |
| `item_count` | Int |  |  |
| `ambiguous_count` | Int |  |  |
| `error_count` | Int |  |  |
| `warning_count` | Int |  |  |
| `sb_review` | Section Break |  |  |
| `errors_json` | Long Text |  |  |
| `warnings_json` | Long Text |  |  |
| `preview_json` | Long Text |  |  |

### BOQ Item (`boq_item/boq_item.json`) - 48 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `sb_identity` | Section Break |  |  |
| `structure` | Link | BOQ Structure | reqd, unique |
| `boq_header` | Link | BOQ Header | reqd |
| `item_type` | Select | Measured Work / Provisional Sum / Prime Cost / Daywork / Contingency / TBD |  |
| `cost_item` | Data |  |  |
| `cb_identity` | Column Break |  |  |
| `owner_page` | Data |  |  |
| `owner_ref_no` | Data |  |  |
| `owner_file_ref` | Data |  |  |
| `is_variation_item` | Check |  | read_only |
| `variation_order` | Link | Variation Order | read_only |
| `sb_import_traceability` | Section Break |  |  |
| `import_batch` | Link | BOQ Import Batch | read_only |
| `import_batch_id` | Data |  | read_only |
| `import_mode` | Select |  / Manual / Structured / Semi-Structured / Flat / Variation | read_only |
| `source_sheet_name` | Data |  | read_only |
| `source_row_no` | Int |  | read_only |
| `source_item_ref` | Data |  | read_only |
| `sb_quantity` | Section Break |  |  |
| `quantity` | Float |  |  |
| `unit` | Link | UOM |  |
| `factor` | Float |  |  |
| `has_stages` | Check |  |  |
| `cb_quantity` | Column Break |  |  |
| `est_unit_cost` | Currency |  | read_only |
| `est_unit_price` | Currency |  |  |
| `contract_unit_price` | Currency |  |  |
| `line_total` | Currency |  | read_only |
| `sb_quantity_revisions` | Section Break |  |  |
| `original_qty` | Float |  | read_only |
| `current_revised_qty` | Float |  | read_only |
| `current_revised_unit_price` | Currency |  | read_only |
| `last_quantity_revision` | Link | BOQ Quantity Revision | read_only |
| `cb_quantity_revisions` | Column Break |  |  |
| `sb_cost_estimation` | Section Break |  |  |
| `overhead_pct` | Percent |  |  |
| `profit_pct` | Percent |  |  |
| `cb_cost_estimation` | Column Break |  |  |
| `overhead_amount` | Currency |  | read_only |
| `profit_amount` | Currency |  | read_only |
| `calculated_sell_price` | Currency |  | read_only |
| `est_line_total` | Currency |  | read_only |
| `quantity_executed` | Float |  | hidden, read_only |
| `quantity_certified` | Float |  | hidden, read_only |
| `sb_future_bidding` | Section Break |  | hidden |
| `sb_future_cost_control` | Section Break |  | hidden |
| `sb_future_progress` | Section Break |  | hidden |
| `sb_future_payment` | Section Break |  | hidden |

### BOQ Item Stage (`boq_item_stage/boq_item_stage.json`) - 16 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `sb_identity` | Section Break |  |  |
| `boq_item` | Link | BOQ Item | reqd |
| `boq_header` | Link | BOQ Header | reqd |
| `project` | Link | Project | reqd, read_only |
| `boq_structure` | Link | BOQ Structure | reqd |
| `cb_identity` | Column Break |  |  |
| `stage_code` | Data |  |  |
| `stage_name` | Data |  | reqd |
| `stage_status` | Select | Not Started / In Progress / Completed / Certified / On Hold | reqd |
| `sb_quantities` | Section Break |  |  |
| `planned_qty` | Float |  |  |
| `measured_executed_qty` | Float |  |  |
| `certified_qty` | Float |  |  |
| `percent_complete` | Percent |  |  |
| `sb_notes` | Section Break |  |  |
| `description` | Small Text |  |  |

### BOQ Quantity Revision (`boq_quantity_revision/boq_quantity_revision.json`) - 35 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `sb_identity` | Section Break |  |  |
| `boq_header` | Link | BOQ Header | reqd |
| `boq_structure` | Link | BOQ Structure | reqd |
| `boq_item` | Link | BOQ Item | reqd |
| `variation_order` | Link | Variation Order |  |
| `cb_identity` | Column Break |  |  |
| `revision_date` | Date |  | reqd |
| `revision_type` | Select | Original Lock / New Variation Item / Increase Within 25% / Decrease Within 25% / Increase Above 25% / Decrease Above 25% / Omission | reqd |
| `status` | Select | Draft / Submitted / Approved / Rejected | reqd |
| `sb_quantity` | Section Break |  |  |
| `previous_qty` | Float |  | reqd |
| `revised_qty` | Float |  | reqd |
| `delta_qty` | Float |  | read_only |
| `delta_from_contract_qty` | Float |  | read_only |
| `cb_quantity` | Column Break |  |  |
| `change_pct` | Percent |  | read_only |
| `change_pct_from_contract` | Percent |  | read_only |
| `rate_change_triggered` | Check |  | read_only |
| `sb_pricing` | Section Break |  |  |
| `contract_unit_price` | Currency |  |  |
| `revised_unit_price` | Currency |  |  |
| `cb_pricing` | Column Break |  |  |
| `previous_value` | Currency |  | read_only |
| `revised_value` | Currency |  | read_only |
| `delta_value` | Currency |  | read_only |
| `sb_reason` | Section Break |  |  |
| `rate_change_justification` | Small Text |  |  |
| `reason` | Small Text |  |  |
| `cb_reason` | Column Break |  |  |
| `owner_page` | Data |  |  |
| `owner_ref_no` | Data |  |  |
| `owner_file_ref` | Data |  |  |
| `sb_approval` | Section Break |  |  |
| `approved_by` | Link | User | read_only |
| `approved_on` | Datetime |  | read_only |

### BOQ Structure (`boq_structure/boq_structure.json`) - 31 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `sb0` | Section Break |  |  |
| `title` | Data |  | reqd |
| `category` | Data |  |  |
| `wbs_code` | Data |  | read_only |
| `parent_structure` | Link | BOQ Structure |  |
| `boq_header` | Link | BOQ Header | reqd |
| `project` | Link | Project | read_only |
| `item_count` | Int |  | read_only |
| `total_contract_value` | Currency |  | read_only |
| `total_budgeted_cost` | Currency |  | read_only |
| `cb0` | Column Break |  |  |
| `is_group` | Check |  |  |
| `description` | Small Text |  |  |
| `description_ar` | Small Text |  |  |
| `is_variation_item` | Check |  | read_only |
| `variation_order` | Link | Variation Order | read_only |
| `sb_owner` | Section Break |  |  |
| `owner_page` | Data |  |  |
| `owner_ref_no` | Data |  |  |
| `owner_file_ref` | Data |  |  |
| `sb_import_traceability` | Section Break |  |  |
| `import_batch` | Link | BOQ Import Batch | read_only |
| `import_batch_id` | Data |  | read_only |
| `import_mode` | Select |  / Manual / Structured / Semi-Structured / Flat / Variation | read_only |
| `source_sheet_name` | Data |  | read_only |
| `source_row_no` | Int |  | read_only |
| `source_wbs_code` | Data |  | read_only |
| `wbs_generated_by_system` | Check |  | read_only |
| `lft` | Int |  | hidden, read_only |
| `rgt` | Int |  | hidden, read_only |
| `old_parent` | Link | BOQ Structure | hidden |

### Construction Settings (`construction_settings/construction_settings.json`) - 28 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `enable_scope_context` | Check |  |  |
| `option_b_section` | Section Break |  |  |
| `enable_option_b_report_access_bypass` | Check |  |  |
| `scope_dimensions_section` | Section Break |  |  |
| `enable_scope_company` | Check |  |  |
| `enable_scope_cost_center` | Check |  |  |
| `enable_scope_project` | Check |  |  |
| `enable_scope_department` | Check |  |  |
| `scope_filter_exclusions` | Small Text |  |  |
| `boq_cascade_section` | Section Break |  |  |
| `enable_boq_cascade_filtering` | Select | Off / On / Strict |  |
| `improve_now_rollout_section` | Section Break |  |  |
| `enable_boq_excel_import_preview` | Check |  |  |
| `enable_boq_excel_import_commit` | Check |  |  |
| `enable_boq_wbs_resequence` | Check |  |  |
| `enable_stage_measurement_ui` | Check |  |  |
| `enable_boq_scope_registry` | Check |  |  |
| `enable_bilingual_boq_print` | Check |  |  |
| `enable_variation_orders` | Check |  |  |
| `global_export_menu_section` | Section Break |  |  |
| `enable_global_export_menu` | Check |  |  |
| `vfc_debug_logging_section` | Section Break |  |  |
| `enable_vfc_debug_logging` | Check |  |  |
| `direct_labor_designations` | Table | Direct Labor Designation |  |
| `section_break_2` | Section Break |  |  |
| `scope_context_settings_help` | HTML | <div class="text-muted small"> /   <p><strong>Scope Context</strong> controls how users interact with multi-company, multi-cost-center environments.</p> /   <ul> /     <li>When enabled, users see Company/Cost Center/Project/Department selectors in the top bar.</li> /     <li>List views and form defaults respect the active scope.</li> /     <li>Use the Scope Dimensions section to choose which dimensions appear in the UI.</li> /     <li>Disable this to restore default Frappe behavior without uninstalling.</li> /   </ul> / </div> |  |
| `scope_hierarchy_section` | Section Break |  |  |
| `scope_hierarchy_ui` | HTML | <p class="text-muted">Loading scope hierarchy...</p> |  |

### Construction Theme (`construction_theme/construction_theme.json`) - 94 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `theme_name` | Data |  | reqd, unique |
| `emoji_icon` | Data |  |  |
| `is_active` | Check |  |  |
| `theme_type` | Select | Construction Light / Construction Dark / Custom Light / Custom Dark | reqd |
| `branding_section` | Section Break |  |  |
| `app_title` | Data |  |  |
| `logo_url` | Attach Image |  |  |
| `favicon` | Attach Image |  |  |
| `column_break_branding_1` | Column Break |  |  |
| `primary_color` | Color |  |  |
| `accent_color` | Color |  |  |
| `danger_color` | Color |  |  |
| `color_scheme` | Select | light / dark |  |
| `features_section` | Section Break |  |  |
| `disable_update_popup` | Check |  |  |
| `hide_help_menu` | Check |  |  |
| `column_break_1` | Column Break |  |  |
| `is_system_theme` | Check |  | read_only |
| `is_default_light` | Check |  |  |
| `is_default_dark` | Check |  |  |
| `description_section` | Section Break |  |  |
| `description` | Small Text |  |  |
| `general_tab` | Tab Break |  |  |
| `accent_primary` | Color |  | reqd |
| `accent_primary_hover` | Color |  |  |
| `accent_secondary` | Color |  |  |
| `column_break_general_1` | Column Break |  |  |
| `sidebar_bg` | Color |  | reqd |
| `surface_bg` | Color |  | reqd |
| `body_bg` | Color |  | reqd |
| `column_break_general_2` | Column Break |  |  |
| `text_primary` | Color |  | reqd |
| `text_secondary` | Color |  |  |
| `border_color` | Color |  |  |
| `login_page_tab` | Tab Break |  |  |
| `login_btn_bg` | Color |  |  |
| `login_btn_text` | Color |  |  |
| `login_btn_hover_bg` | Color |  |  |
| `login_btn_hover_text` | Color |  |  |
| `column_break_login_1` | Column Break |  |  |
| `login_page_bg_type` | Select |  / Solid Color / Background Image |  |
| `login_page_bg_color` | Color |  |  |
| `login_page_bg_image` | Attach Image |  |  |
| `column_break_login_2` | Column Break |  |  |
| `login_box_position` | Select |  / Default / Left / Right |  |
| `login_logo_inside_box` | Check |  |  |
| `login_page_title` | Data |  |  |
| `login_heading_text_color` | Color |  |  |
| `login_tab_bg_color` | Color |  |  |
| `buttons_tab` | Tab Break |  |  |
| `primary_btn_bg` | Color |  |  |
| `primary_btn_text` | Color |  |  |
| `primary_btn_hover_bg` | Color |  |  |
| `primary_btn_hover_text` | Color |  |  |
| `column_break_buttons_1` | Column Break |  |  |
| `secondary_btn_bg` | Color |  |  |
| `secondary_btn_text` | Color |  |  |
| `secondary_btn_hover_bg` | Color |  |  |
| `secondary_btn_hover_text` | Color |  |  |
| `tables_tab` | Tab Break |  |  |
| `table_header_bg` | Color |  |  |
| `table_header_text` | Color |  |  |
| `table_body_bg` | Color |  |  |
| `table_body_text` | Color |  |  |
| `column_break_tables_1` | Column Break |  |  |
| `hide_like_comment` | Check |  |  |
| `mobile_card_view` | Check |  |  |
| `widgets_tab` | Tab Break |  |  |
| `number_card_bg` | Color |  |  |
| `number_card_border` | Color |  |  |
| `number_card_text` | Color |  |  |
| `input_fields_tab` | Tab Break |  |  |
| `input_bg` | Color |  |  |
| `input_border` | Color |  |  |
| `input_text` | Color |  |  |
| `input_label_color` | Color |  |  |
| `navbar_tab` | Tab Break |  |  |
| `navbar_bg` | Color |  | reqd |
| `navbar_text_color` | Color |  |  |
| `footer_tab` | Tab Break |  |  |
| `footer_bg` | Color |  |  |
| `footer_text` | Color |  |  |
| `semantic_colors_tab` | Tab Break |  |  |
| `success_color` | Color |  |  |
| `warning_color` | Color |  |  |
| `error_color` | Color |  |  |
| `preview_tab` | Tab Break |  |  |
| `preview_colors` | JSON |  | read_only |
| `contrast_ratio` | Float |  | read_only |
| `advanced_tab` | Tab Break |  |  |
| `hide_help_button` | Check |  |  |
| `hide_search_bar` | Check |  |  |
| `hide_sidebar` | Check |  |  |
| `custom_css` | Code | CSS |  |

### CostItem (`costitem/cost_item.json`) - 9 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `cost_item_code` | Data |  | reqd, unique |
| `category` | Link | CostCategory |  |
| `title` | Data |  | reqd |
| `description` | Text |  |  |
| `unit` | Link | UOM | reqd |
| `base_productivity` | Float |  |  |
| `default_wastage_pct` | Percent |  |  |
| `status` | Select | Active / Deprecated / Pending Review |  |
| `total_direct_cost` | Currency |  | read_only |

### Direct Labor Designation (`direct_labor_designation/direct_labor_designation.json`) - 2 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `designation` | Link | Designation | reqd |
| `boq_requirement` | Select | Mandatory / Optional / Not Applicable | reqd |

### Form Layout Profile (`form_layout_profile/form_layout_profile.json`) - 13 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `reference_doctype` | Link | DocType | reqd |
| `profile_name` | Data |  | reqd |
| `cb_meta` | Column Break |  |  |
| `enabled` | Check |  |  |
| `is_default` | Check |  |  |
| `is_system` | Check |  | read_only |
| `sb_targeting` | Section Break |  |  |
| `for_role` | Link | Role |  |
| `for_user` | Link | User |  |
| `priority` | Int |  |  |
| `layout_version` | Int |  | reqd |
| `sb_layout` | Section Break |  |  |
| `sections_json` | JSON |  |  |

### Modern Theme Settings (`modern_theme_settings/modern_theme_settings.json`) - 10 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `default_light_theme` | Link | Construction Theme |  |
| `default_dark_theme` | Link | Construction Theme |  |
| `section_break_1` | Section Break |  |  |
| `allow_user_override` | Check |  |  |
| `enforce_contrast_check` | Check |  |  |
| `column_break_1` | Column Break |  |  |
| `theme_switcher_limit` | Int |  |  |
| `css_cache_ttl` | Int |  |  |
| `notes_section` | Section Break |  |  |
| `notes` | Text |  | read_only |

### PlantResource (`plantresource/plant_resource.json`) - 5 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `resource_code` | Data |  | reqd, unique |
| `equipment_type` | Data |  | reqd |
| `ownership_cost_hourly` | Currency |  |  |
| `operating_cost_hourly` | Currency |  |  |
| `mobilization_cost` | Currency |  |  |

### Resource Price History (`resource_price_history/resource_price_history.json`) - 22 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `naming_series` | Select | RPH-.YYYY.- | reqd |
| `item_code` | Link | Item | reqd |
| `item_name` | Data |  | read_only |
| `resource_type` | Select |  / Material / Labor / Plant / Subcontract / Overhead |  |
| `price_date` | Date |  | reqd |
| `rate` | Currency |  | reqd |
| `currency` | Link | Currency | reqd |
| `exchange_rate` | Float |  |  |
| `uom` | Link | UOM | reqd |
| `supplier` | Link | Supplier |  |
| `project` | Link | Project |  |
| `region` | Data |  |  |
| `company` | Link | Company | reqd |
| `sb_source` | Section Break |  |  |
| `source_doctype` | Data |  | read_only |
| `source_name` | Data |  | read_only |
| `source_row` | Data |  | read_only |
| `sb_status` | Section Break |  |  |
| `status` | Select | Active / Cancelled | reqd |
| `cancelled_by` | Data |  | read_only |
| `cancelled_on` | Datetime |  | read_only |
| `remarks` | Small Text |  |  |

### Scope Report Access Log (`scope_report_access_log/scope_report_access_log.json`) - 12 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `user` | Link | User | reqd |
| `report_name` | Data |  | reqd |
| `access_granted` | Check |  |  |
| `denial_reason` | Small Text |  |  |
| `scope_section` | Section Break |  |  |
| `company` | Data |  |  |
| `cost_center` | Data |  |  |
| `project` | Data |  |  |
| `department` | Data |  |  |
| `request_section` | Section Break |  |  |
| `request_path` | Data |  |  |
| `timestamp` | Datetime |  |  |

### User Desk Theme (`user_desk_theme/user_desk_theme.json`) - 25 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `user` | Link | User | reqd, unique |
| `inherit_from_site` | Check |  |  |
| `section_break_1` | Section Break |  |  |
| `light_theme` | Link | Construction Theme |  |
| `dark_theme` | Link | Construction Theme |  |
| `typography_section` | Section Break |  |  |
| `desk_font_family` | Select | System Default / Inter / Arial / Helvetica / Tahoma / Verdana / Trebuchet MS / Georgia / Times New Roman / Courier New / Roboto / Open Sans / Lato / Montserrat / Poppins / Noto Sans / Noto Sans Arabic / Cairo / Tajawal / Almarai |  |
| `desk_font_size` | Int |  |  |
| `desk_font_weight` | Select | 300 / 400 / 500 / 600 / 700 |  |
| `component_typography_section` | Section Break |  |  |
| `sidebar_font_family` | Select | Inherit / System Default / Inter / Arial / Helvetica / Tahoma / Verdana / Trebuchet MS / Georgia / Times New Roman / Courier New / Roboto / Open Sans / Lato / Montserrat / Poppins / Noto Sans / Noto Sans Arabic / Cairo / Tajawal / Almarai |  |
| `sidebar_font_size` | Int |  |  |
| `sidebar_font_weight` | Select | 300 / 400 / 500 / 600 / 700 |  |
| `navbar_font_family` | Select | Inherit / System Default / Inter / Arial / Helvetica / Tahoma / Verdana / Trebuchet MS / Georgia / Times New Roman / Courier New / Roboto / Open Sans / Lato / Montserrat / Poppins / Noto Sans / Noto Sans Arabic / Cairo / Tajawal / Almarai |  |
| `navbar_font_size` | Int |  |  |
| `navbar_font_weight` | Select | 300 / 400 / 500 / 600 / 700 |  |
| `form_font_family` | Select | Inherit / System Default / Inter / Arial / Helvetica / Tahoma / Verdana / Trebuchet MS / Georgia / Times New Roman / Courier New / Roboto / Open Sans / Lato / Montserrat / Poppins / Noto Sans / Noto Sans Arabic / Cairo / Tajawal / Almarai |  |
| `form_font_size` | Int |  |  |
| `form_font_weight` | Select | 300 / 400 / 500 / 600 / 700 |  |
| `list_font_family` | Select | Inherit / System Default / Inter / Arial / Helvetica / Tahoma / Verdana / Trebuchet MS / Georgia / Times New Roman / Courier New / Roboto / Open Sans / Lato / Montserrat / Poppins / Noto Sans / Noto Sans Arabic / Cairo / Tajawal / Almarai |  |
| `list_font_size` | Int |  |  |
| `list_font_weight` | Select | 300 / 400 / 500 / 600 / 700 |  |
| `menu_font_family` | Select | Inherit / System Default / Inter / Arial / Helvetica / Tahoma / Verdana / Trebuchet MS / Georgia / Times New Roman / Courier New / Roboto / Open Sans / Lato / Montserrat / Poppins / Noto Sans / Noto Sans Arabic / Cairo / Tajawal / Almarai |  |
| `menu_font_size` | Int |  |  |
| `menu_font_weight` | Select | 300 / 400 / 500 / 600 / 700 |  |

### User Scope Context (`user_scope_context/user_scope_context.json`) - 10 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `user` | Link | User | reqd, unique |
| `company` | Link | Company | reqd |
| `cost_center` | Link | Cost Center |  |
| `project` | Link | Project |  |
| `department` | Link | Department |  |
| `branch` | Link | Branch |  |
| `column_break_6` | Column Break |  |  |
| `scope_version` | Int |  | read_only |
| `last_active_at` | Datetime |  | read_only |
| `client_id` | Data |  |  |

### Variation Order (`variation_order/variation_order.json`) - 18 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `boq_header` | Link | BOQ Header | reqd |
| `project` | Link | Project | read_only |
| `vo_number` | Data |  | read_only |
| `vo_date` | Date |  | reqd |
| `status` | Select | Draft / Submitted / Approved by Engineer / Approved by Client / Rejected | reqd |
| `cb_approval` | Column Break |  |  |
| `description` | Small Text |  |  |
| `reason` | Small Text |  |  |
| `engineer_name` | Data |  |  |
| `engineer_approval_date` | Date |  | read_only |
| `client_approval_document` | Attach |  |  |
| `client_approval_ref` | Data |  |  |
| `client_approval_date` | Date |  | read_only |
| `sb_lines` | Section Break |  |  |
| `lines` | Table | VO Line |  |
| `sb_totals` | Section Break |  |  |
| `total_contract_delta` | Currency |  | read_only |
| `notes` | Text Editor |  |  |

### VO Line (`vo_line/vo_line.json`) - 27 fields

| Field | Type | Options | Flags |
|---|---|---|---|
| `line_type` | Select | Quantity Change / New Item / Omission | reqd |
| `boq_structure` | Link | BOQ Structure |  |
| `boq_item` | Link | BOQ Item |  |
| `wbs_code` | Data |  | read_only |
| `title` | Data |  |  |
| `unit` | Link | UOM |  |
| `contract_qty` | Float |  | read_only |
| `previous_qty` | Float |  | read_only |
| `revised_qty` | Float |  |  |
| `delta_qty` | Float |  | read_only |
| `delta_from_contract_qty` | Float |  | read_only |
| `change_pct_from_contract` | Percent |  | read_only |
| `abs_change_pct` | Percent |  | read_only |
| `rate_change_triggered` | Check |  | read_only |
| `contract_unit_price` | Currency |  | read_only |
| `revised_unit_price` | Currency |  |  |
| `rate_change_justification` | Small Text |  |  |
| `contract_line_value` | Currency |  | read_only |
| `revised_line_value` | Currency |  | read_only |
| `line_delta_value` | Currency |  | read_only |
| `owner_page` | Data |  |  |
| `owner_ref_no` | Data |  |  |
| `owner_file_ref` | Data |  |  |
| `created_boq_structure` | Link | BOQ Structure | read_only |
| `created_boq_item` | Link | BOQ Item | read_only |
| `created_quantity_revision` | Link | BOQ Quantity Revision | read_only |
| `notes` | Small Text |  |  |

## Validation Checklist

- [ ] Run `python3 scripts/schema_drift_checker.py` before agent planning.
- [ ] Run `python3 scripts/schema_drift_checker.py --update` only after reviewing intended schema changes.
- [ ] Run `python3 scripts/ai_context_check.py` after schema facts are regenerated.
