# Handoff: Egyptian Construction Cost Database Build

**Target Agent:** Online AI agent tasked with researching Egyptian construction cost data sources and structuring a seed/importable cost database for our Construction ERP app.  
**App:** Construction ERP (Frappe/ERPNext custom app), repo `/home/mohamed/frappe-bench/apps/construction`, branch `develop`.  
**Date:** 2026-06-29  
**Status:** Phase 1 estimation engine implemented, code-reviewed, and passing tests. This handoff is for the **data-layer build**.  
**Update 2026-08-19:** Phase 2 (import API + Excel template generator) is implemented and reviewed on branch `feat/cost-database-phase2` (restored from WIP snapshot `edccbf3` + review fixes: template `category`/`description_ar` fields, `category` alias collision, import idempotency). Import is idempotent — re-importing the same file skips identical price rows and upserts draft templates. See `IMPLEMENTATION.md` Phase 2 section.  
**Source of Truth Hierarchy:** Live DocType JSON / Python > `docs/ai/SCHEMA_FACTS.md` > this handoff > attached research notes. If this handoff conflicts with live code, live code wins.

---

## 1. Goal

Build an **importable Egyptian construction cost database** that seeds our existing estimation engine. The agent must:

1. Research and cite reliable Egyptian cost data sources (URLs, access dates, reliability ratings).
2. Define canonical seed schemas that map cleanly to our existing DocTypes.
3. Produce seed CSVs/Excel template for resources, BOQ items, rate-analysis recipes, and price history.
4. Recommend a safe Excel import workflow.

**Do not redesign the estimation engine.** Feed the engine that already exists.

---

## 2. What Already Exists — Do Not Rebuild

### 2.1 `Resource Price History` DocType
**Path:** `construction/construction/doctype/resource_price_history/`

This is the auditable price ledger. Every price you find should land here (tagged by source).

| Field | Type | Purpose | Notes |
|-------|------|---------|-------|
| `naming_series` | Select | `RPH-.YYYY.-` | Auto-generated |
| `item_code` | Link → Item | Resource (material, labor, plant) | Required |
| `item_name` | Data (fetch) | Auto-fetched from Item | Read-only |
| `resource_type` | Select | `Material` / `Labor` / `Plant` / `Subcontract` / `Overhead` | Must match Item custom field |
| `price_date` | Date | Effective date of the price | Required |
| `rate` | Currency | Price per UOM | Required |
| `currency` | Link → Currency | Defaults to `EGP` | Required |
| `exchange_rate` | Float | Local currency rate if foreign currency used | Defaults to 1.0 |
| `uom` | Link → UOM | Unit of measure | Required |
| `supplier` | Link → Supplier | Optional source | |
| `project` | Link → Project | Optional project scope | |
| `region` | Data | Geographic region (Cairo, Alexandria, etc.) | New field; do not abuse `project` |
| `company` | Link → Company | Mandatory scope dimension | Required |
| `source_doctype` | Data | `Purchase Invoice`, `Purchase Order`, `Import`, `Manual`, etc. | Read-only in UI; importer sets server-side |
| `source_name` | Data | Document/batch reference | Read-only in UI |
| `source_row` | Data | Row reference | Read-only in UI |
| `status` | Select | `Active` / `Cancelled` | Required |
| `cancelled_by` / `cancelled_on` | Data / Datetime | Audit fields | Read-only |
| `remarks` | Small Text | Free-text notes | |

**Permissions:**
- `System Manager` — full create/read/write/delete/report/export
- `Construction Owner` — read/report/export
- `Project Manager` — read/report/export
- No write access for `Site Engineer` or `Accountant` on this DocType.

### 2.2 `BOQ Cost Analysis` + `BOQ Cost Analysis Detail`
**Path:** `construction/construction/doctype/boq_cost_analysis/`

This is where the Egyptian **Rate Analysis (تحليل الأسعار)** lives.

- `BOQ Cost Analysis` = one analysis per BOQ Item (one unit of work).
- `BOQ Cost Analysis Detail` = the recipe rows (resources × quantities × wastage).

Key fields on `BOQ Cost Analysis`:

| Field | Type | Purpose |
|-------|------|---------|
| `naming_series` | Select | `BCA-.YYYY.-` |
| `title` | Data | Human-readable title |
| `boq_item` | Link → BOQ Item | The BOQ item being analyzed | Required |
| `boq_header` | Link → BOQ Header | Fetched from BOQ Item | Read-only |
| `boq_structure` | Link → BOQ Structure | Fetched from BOQ Item | Read-only |
| `project` | Link → Project | Fetched from BOQ Header | Read-only |
| `company` | Link → Company | Required |
| `analysis_status` | Select | `Draft` / `Approved` / `Superseded` / `Cancelled` |
| `analysis_uom` | Link → UOM | UOM of the BOQ item unit | Required |
| `analysis_qty` | Float | Usually `1` for "per unit" analysis | Required |
| `currency` | Link → Currency | Required |
| `is_template` | Check | If `1`, this is a reusable template not tied to a live BOQ Item |
| `template_name` | Data | Name of the template (when `is_template=1`) |
| `details` | Table | `BOQ Cost Analysis Detail` child rows |
| `total_direct_cost` | Currency | Sum of detail amounts |
| `overhead_pct` | Percent | Overhead on direct cost |
| `profit_pct` | Percent | Profit on (direct + overhead) |
| `total_unit_cost` | Currency | Direct + OH + Profit |
| `suggested_sell_rate` | Currency | Same as `total_unit_cost` by default |

Detail row fields (`BOQ Cost Analysis Detail`):

| Field | Type | Purpose |
|-------|------|---------|
| `cost_stream` | Select | `M` / `L` / `P` / `S` / `O` |
| `item_code` | Link → Item | Resource |
| `item_name` | Data (fetch) | Auto-fetched |
| `resource_uom` | Link → UOM | Resource UOM |
| `qty_per_boq_unit` | Float | How much of this resource per 1 unit of BOQ item |
| `wastage_pct` | Percent | Wastage applied to qty |
| `cost_rate` | Currency | Unit rate **at import/approval time** |
| `amount` | Currency | `qty × cost_rate × (1 + wastage/100)`; read-only |
| `rate_source` | Select | `Manual` / `Item Price` / `Last PI` / `Last PO` / `Resource Price History` |
| `supplier` | Link → Supplier | Optional |
| `remarks` | Small Text | |

**Important — stored vs. dynamic pricing:**
- `cost_rate` is stored on the detail row at the time the analysis is created/approved.
- The app **does not** automatically reprice detail rows when Cement changes in `Resource Price History`.
- To update prices, the user must create a new analysis version (or run a repricing tool in a future phase).

Calculations already implemented:

```
detail.amount = qty_per_boq_unit * cost_rate * (1 + wastage_pct / 100)
total_direct_cost = SUM(detail.amount)
unit_direct = total_direct_cost / analysis_qty
overhead_amount = unit_direct * overhead_pct / 100
profit_amount = (unit_direct + overhead_amount) * profit_pct / 100
total_unit_cost = unit_direct + overhead_amount + profit_amount
```

On approval, the analysis writes `BOQ Item.est_unit_cost = total_unit_cost` and refreshes BOQ Header totals. The BOQ Item then recalculates its own `overhead_amount`, `profit_amount`, `calculated_sell_price`, and `est_line_total` using **its own** `overhead_pct` and `profit_pct`. Make sure these percentages are aligned between the analysis and the BOQ Item.

### 2.3 `Item` Custom Fields (Construction Resources)
**Patch:** `construction/construction/patches/v8_0/add_item_construction_fields.py`  
**Also set up in:** `construction/install.py::setup_item_construction_fields()`

These fields are added to ERPNext `Item` so it can act as a construction resource:

| Field | Type | Purpose |
|-------|------|---------|
| `item_name_ar` | Data | Arabic item name for bilingual reports |
| `is_construction_resource` | Check | Flag this Item as a construction resource |
| `construction_resource_type` | Select | `Material` / `Labor` / `Plant` / `Subcontract` / `Overhead` |
| `default_cost_stream` | Select | `M` / `L` / `P` / `S` / `O` |
| `default_wastage_pct` | Percent | Default wastage for this resource |
| `default_productivity_qty_per_day` | Float | Labor/equipment productivity |
| `labor_trade_designation` | Link → Designation | For labor resources |
| `linked_asset` | Link → Asset | For plant resources |

### 2.4 `BOQ Item`
**Path:** `construction/construction/doctype/boq_item/boq_item.py`

- Each BOQ Item is a **specification line**, not an ERPNext Item.
- It links to `BOQ Structure` (WBS) and `BOQ Header`.
- It stores cost fields: `est_unit_cost`, `est_unit_price`, `contract_unit_price`, `overhead_pct`, `profit_pct`, `overhead_amount`, `profit_amount`, `calculated_sell_price`, `est_line_total`, `line_total`.
- `item_type` is a Select field: `Measured Work`, `Provisional Sum`, etc. **Do not store work descriptions here.**

**Schema gap — bilingual BOQ items:**
- `BOQ Item` does not currently have `description_en` / `description_ar` fields.
- The description lives on `BOQ Structure` (`title` + `description`).
- For bilingual BOQ items, recommend adding `description_ar` to `BOQ Structure` (or to `BOQ Item`) in a future schema hardening phase. Until then, seed data should keep Arabic descriptions in a separate column for later migration.

### 2.5 Services Already Available
- `construction.services.resource_price_service`
  - `get_suggested_rate(item_code, supplier=None, project=None, company=None, region=None, as_of_date=None)`
    - Priority: Last PI → Last PO → Last other `Resource Price History` (Import, Manual, etc.) → ERPNext Item Price.
    - Optional `as_of_date` for price-locking scenarios.
  - `capture_price_from_purchase_document(doc)` — on_submit hook for PO/PI
  - `cancel_price_history_for_document(doc)` — on_cancel hook
- `construction.services.boq_cost_analysis_service`
  - `get_approved_analysis_for_boq_item(boq_item)`
  - `get_approved_analysis_total_direct_cost(boq_item)`
  - `refresh_boq_header_budget_totals(boq_header)`
- `construction.services.boq_report_service`
  - `get_boq_cost_analysis_summary(boq_header)`
  - `get_boq_item_cost_vs_contract(boq_header)`
  - `get_resource_requirement_summary(boq_header)`
  - `get_resource_price_history(item_code, supplier, region, from_date, to_date)`
  - `get_boq_items_missing_analysis(boq_header)`

---

## 3. Core Concept: Egyptian Rate Analysis (تحليل الأسعار)

Do **not** store a static price per BOQ item. Egyptian construction prices are volatile. Store the **recipe**:

- **Resources** = raw inputs (Cement, Sand, Steel, Mason day, Mixer hour).
- **BOQ Items** = final work items ("1 m³ Reinforced Concrete Column", "10 cm Red Brick Wall").
- **Rate Analysis** = how much of each resource is needed per one unit of the BOQ item.

When a resource price changes, a user creates a new `BOQ Cost Analysis` version for affected BOQ items. Approval of the new version updates live estimates.

---

## 4. Required Data Schema (Map to Our App)

Use this schema when designing seed files. Each row must map cleanly to existing DocTypes.

### 4.1 `resources.csv` → ERPNext `Item` + `Resource Price History`

| Column | Example | Maps To | Required |
|--------|---------|---------|----------|
| `resource_code` | `MAT-CEM-001` | `Item.item_code` | Yes |
| `name_en` | Portland Cement | `Item.item_name` | Yes |
| `name_ar` | أسمنت بورتلاندي | `Item.item_name_ar` | Recommended |
| `resource_type` | Material | `Item.construction_resource_type` | Yes |
| `cost_stream` | M | `Item.default_cost_stream` | Yes |
| `uom` | Ton | `Item.stock_uom`, `Resource Price History.uom` | Yes |
| `unit_price_egp` | 3500 | `Resource Price History.rate` | Yes |
| `currency` | EGP | `Resource Price History.currency` | Yes (default EGP) |
| `exchange_rate` | 1.0 | `Resource Price History.exchange_rate` | Yes (default 1.0) |
| `company` | _Test Estimation Company | `Resource Price History.company` | Yes |
| `price_date` | 2026-06-01 | `Resource Price History.price_date` | Yes |
| `region` | Cairo | `Resource Price History.region` | Recommended |
| `source_doctype` | Import | `Resource Price History.source_doctype` | Yes |
| `source_name` | Ministry of Housing June 2026 | `Resource Price History.source_name` | Yes |
| `source_row` | 1 | `Resource Price History.source_row` | Optional |
| `supplier` | (optional) | `Resource Price History.supplier` | Optional |
| `remarks` | Monthly bulletin avg | `Resource Price History.remarks` | Optional |

Resource type enum (must match exactly):
- `Material` → cost stream `M`
- `Labor` → cost stream `L`
- `Plant` → cost stream `P`
- `Subcontract` → cost stream `S`
- `Overhead` → cost stream `O`

### 4.2 `boq_items.csv` → Master / Template Data

**Current schema limitation:** `BOQ Item` requires a `boq_header` and a `structure`, and `structure` is unique per header. You cannot cleanly maintain a global BOQ Item master table today.

**Recommended approach:** Use `BOQ Cost Analysis.is_template = 1` with `template_name` populated. A template analysis carries the rate-analysis recipe without being tied to a live BOQ Item. Later, a user can copy a template analysis to a real BOQ Item.

| Column | Example | Maps To | Required |
|--------|---------|---------|----------|
| `template_name` | `01-CONC-PLN` | `BOQ Cost Analysis.template_name` | Yes for templates |
| `description_en` | Plain Concrete (Blinding) | `BOQ Cost Analysis.title` or notes | Yes |
| `description_ar` | خرسانة عادية نظافة | Notes / future `BOQ Structure.description_ar` | Recommended |
| `category` | Concrete Works | Notes / future category field | Recommended |
| `uom` | m³ | `BOQ Cost Analysis.analysis_uom` | Yes |
| `overhead_pct` | 12 | Default for template + BOQ Item | Yes |
| `profit_pct` | 8 | Default for template + BOQ Item | Yes |
| `currency` | EGP | `BOQ Cost Analysis.currency` | Yes |

**Do not map `description_en` to `BOQ Item.item_type`.** `item_type` is a Select field (`Measured Work`, `Provisional Sum`, etc.).

### 4.3 `rate_analysis.csv` → `BOQ Cost Analysis Detail`

| Column | Example | Maps To | Required |
|--------|---------|---------|----------|
| `template_name` / `boq_item_code` | `01-CONC-PLN` | Links recipe to template or live BOQ item | Yes |
| `resource_code` | `MAT-CEM-001` | `BOQ Cost Analysis Detail.item_code` | Yes |
| `qty_per_boq_unit` | 0.250 | `BOQ Cost Analysis Detail.qty_per_boq_unit` | Yes |
| `wastage_pct` | 5 | `BOQ Cost Analysis Detail.wastage_pct` | Yes (default 0) |
| `cost_stream` | M | `BOQ Cost Analysis Detail.cost_stream` | Yes |
| `cost_rate` | 3500 | `BOQ Cost Analysis Detail.cost_rate` | Yes |
| `rate_source` | Resource Price History | `BOQ Cost Analysis Detail.rate_source` | Yes |
| `supplier` | (optional) | `BOQ Cost Analysis Detail.supplier` | Optional |
| `remarks` | (optional) | `BOQ Cost Analysis Detail.remarks` | Optional |

### 4.4 `price_history.csv` → `Resource Price History`

Same columns as `resources.csv`, but with multiple historical rows per resource. Used for volatility tracking and `as_of_date` lookups.

---

## 5. Egyptian Data Sources to Research

The agent must search these sources and evaluate which are scrapable, have public PDFs, or can be manually transcribed. **Every source must be cited with URL and access date.** Mark low-trust sources as "reference only — do not use as default seed price."

### 5.1 Official / Government (High Trust)
1. **Ministry of Housing and Urban Communities (وزارة الإسكان)**  
   - Publishes monthly building-material price bulletins.  
   - Look for PDFs titled "أسعار مواد البناء" or "نشرة أسعار مواد البناء".  
   - Use OCR or manual entry for top 50–100 materials.

2. **Engineering Authority of the Armed Forces (الهيئة الهندسية للقوات المسلحة)**  
   - Standard rate-analysis guides: "تحليل أسعار بنود المقاولات".  
   - Often shared as PDFs on engineering forums or Scribd.

3. **Central Agency for Public Mobilization and Statistics (CAPMAS)**  
   - `capmas.gov.eg` — construction cost indices and material price indexes.

### 5.2 Commercial / Aggregator Platforms (Medium Trust)
1. **engpricelist.com** — Egyptian engineering price aggregator for materials and services.
2. **Cement company sites** (Suez Cement, Lafarge Egypt, Beni Suef Cement) — published price lists.
3. **Steel producer sites** (Ezz Steel, Beshay Steel) — rebar price announcements.

### 5.3 Reference Documents (Low Trust — Reference Only)
1. **Scribd / Engineering Facebook groups** for "كتاب تحليل أسعار" or "Excel تحليل أسعار".
2. **OLX Egypt / El Waseet** — spot market prices (volatility checks only).
3. **CSI MasterFormat** adapted to Egyptian practice.

### 5.4 What to Extract First (Priority Order)
1. Top 50 most common BOQ items: Earthworks, Concrete, Reinforcement, Blockwork, Plastering, Flooring, Painting, MEP.
2. Their resource recipes from Egyptian standard rate analyses.
3. Current resource prices for: Cement, Sand, Aggregate, Steel rebar, Bricks, Paint, Tiles, Copper wire, PVC pipes, Labor trades, Equipment (mixer, vibrator, compactor, crane day).

---

## 6. Seed Data Examples (Illustrative Only)

> **All prices below are placeholders for schema illustration.** Do not treat them as verified June 2026 market prices. Replace with values from cited sources.

### 6.1 Resources

| resource_code | resource_type | cost_stream | name_en | name_ar | uom | unit_price_egp | currency | exchange_rate | company | region | price_date | source_doctype | source_name |
|---------------|---------------|-------------|---------|---------|-----|----------------|----------|---------------|---------|--------|------------|----------------|-------------|
| MAT-CEM-001 | Material | M | Portland Cement | أسمنت بورتلاندي | Ton | 3,500 | EGP | 1.0 | _Test Estimation Company | Cairo | 2026-06-01 | Import | Ministry of Housing June 2026 |
| MAT-SAND-001 | Material | M | Clean Sand | رمل نظيف | m³ | 400 | EGP | 1.0 | _Test Estimation Company | Cairo | 2026-06-01 | Import | Ministry of Housing June 2026 |
| MAT-AGG-001 | Material | M | Gravel / Aggregate | زلط / سن | m³ | 500 | EGP | 1.0 | _Test Estimation Company | Cairo | 2026-06-01 | Import | Ministry of Housing June 2026 |
| MAT-STEEL-001 | Material | M | Reinforcement Steel | حديد تسليح | Ton | 45,000 | EGP | 1.0 | _Test Estimation Company | Cairo | 2026-06-01 | Import | Ezz Steel June 2026 |
| LAB-MASON-001 | Labor | L | Mason | عامل بناء / مبيض | Day | 250 | EGP | 1.0 | _Test Estimation Company | Cairo | 2026-06-01 | Import | Market survey June 2026 |
| PLT-MIXER-001 | Plant | P | Concrete Mixer | خلاطة خرسانة | Hour | 80 | EGP | 1.0 | _Test Estimation Company | Cairo | 2026-06-01 | Import | Market survey June 2026 |

### 6.2 BOQ Item Templates

| template_name | description_en | description_ar | uom | overhead_pct | profit_pct | currency |
|---------------|----------------|----------------|-----|--------------|------------|----------|
| 01-CONC-PLN | Plain Concrete (Blinding) 10 cm | خرسانة عادية نظافة 10 سم | m³ | 12 | 8 | EGP |
| 01-CONC-RC-COL | Reinforced Concrete Columns | خرسانة مسلحة أعمدة | m³ | 12 | 8 | EGP |
| 02-WALL-BRK-10 | 10 cm Red Brick Wall | حائط طوب أحمر 10 سم | m² | 10 | 8 | EGP |

### 6.3 Rate Analysis Recipe Example: Plain Concrete (Blinding) per 1 m³

| template_name | resource_code | qty_per_boq_unit | wastage_pct | cost_stream | cost_rate | rate_source |
|---------------|---------------|------------------|-------------|-------------|-----------|-------------|
| 01-CONC-PLN | MAT-CEM-001 | 0.250 | 3 | M | 3,500 | Resource Price History |
| 01-CONC-PLN | MAT-SAND-001 | 0.500 | 5 | M | 400 | Resource Price History |
| 01-CONC-PLN | MAT-AGG-001 | 0.800 | 5 | M | 500 | Resource Price History |
| 01-CONC-PLN | LAB-MASON-001 | 0.500 | 0 | L | 250 | Resource Price History |
| 01-CONC-PLN | LAB-HELP-001 | 1.000 | 0 | L | 150 | Resource Price History |
| 01-CONC-PLN | PLT-MIXER-001 | 0.250 | 0 | P | 80 | Resource Price History |

Expected direct cost calculation (illustrative):
```
Cement: 0.250 × 3,500 × 1.03 = 901.25
Sand:   0.500 × 400   × 1.05 = 210.00
Aggregate: 0.800 × 500 × 1.05 = 420.00
Mason:  0.500 × 250          = 125.00
Helper: 1.000 × 150          = 150.00
Mixer:  0.250 × 80           =  20.00
Direct Cost per m³           = 1,826.25 EGP
+ OH 12% = 219.15
+ Profit 8% on (1,826.25 + 219.15) = 163.64
Total Unit Cost ≈ 2,209.04 EGP/m³
```

---

## 7. Excel Import Feature Specification

The user explicitly wants an **Import from Excel** feature. Here is the recommended design.

### 7.1 Import Workbook Structure
A single `.xlsx` workbook with **three mandatory sheets** and one optional sheet:

1. **Resources** — maps to `Item` + `Resource Price History`
2. **BOQItemTemplates** — maps to `BOQ Cost Analysis` with `is_template=1`
3. **RateAnalysis** — maps to `BOQ Cost Analysis Detail`
4. **PriceHistory** (optional) — historical prices

Add a hidden metadata cell/sheet (`_Metadata`):
- `schema_version` = `1.0`
- `generated_by` = app name + version
- `import_mode` = `validate_only` or `import`

The generated template workbook includes this metadata sheet hidden by default.

### 7.2 Validation Rules
- `resource_code` must be unique within the Resources sheet.
- `uom` values must exist in ERPNext `UOM` master; if missing, create them during import.
- `resource_type` must be one of: Material, Labor, Plant, Subcontract, Overhead.
- `cost_stream` must be one of: M, L, P, S, O and consistent with `resource_type`.
- `template_name` in RateAnalysis must exist in BOQItemTemplates sheet.
- `resource_code` in RateAnalysis must exist in Resources sheet.
- `qty_per_boq_unit` must be ≥ 0.
- `wastage_pct` must be between 0 and 100.
- `currency` defaults to `EGP`; if missing, read from Company master.
- `company` must exist in `Company` master.
- `exchange_rate` defaults to `1.0`.

### 7.3 Import Workflow
1. User uploads `.xlsx` via the whitelisted endpoint: `construction.api.cost_database_api.import_cost_database`.
2. Backend parses sheets using `openpyxl`.
3. **Dry-run / validation stage:** Validate all rows and produce a report (errors, warnings, counts). Do not create records yet.
4. On user confirmation:
   - Stage 1: Create/update ERPNext `Item` records with construction custom fields.
   - Stage 2: Create `Resource Price History` rows with `source_doctype = "Import"` and `source_name = <filename>`.
   - Stage 3: Create `BOQ Cost Analysis` drafts with `is_template=1` and detail rows from RateAnalysis sheet.
5. Do **not** auto-submit analyses unless an explicit `auto_submit=1` flag is passed.
6. Return a summary: rows processed, errors, warnings, record names created.

### 7.3.1 Implemented Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `construction.api.cost_database_api.import_cost_database` | POST (multipart) | Upload and import/validate a cost database workbook. |
| `construction.api.cost_database_api.download_cost_database_template` | GET | Download a blank or sample `.xlsx` template. |

Both endpoints are whitelisted (`@frappe.whitelist()`). Import execution requires `create` permission on `Resource Price History`.

### 7.4 Permission Requirements
- Endpoint must be whitelisted with `@frappe.whitelist()`.
- Restrict import execution to `System Manager` and `Construction Owner`.
- Max file size: 10 MB (configurable).

### 7.5 Template Download
Implemented in `construction.services.cost_database_service.generate_cost_database_template(mode)` and exposed via `download_cost_database_template(mode)`.

Provide two modes:
- **Sample template** (`mode=sample`) — pre-filled with illustrative Egyptian resources, BOQ item templates, and rate-analysis recipes (e.g., Plain Concrete Blinding).
- **Blank template** (`mode=blank`) — headers and validation only.

Generated workbook includes:
- Header rows with blue styling explaining each column.
- Dropdown data validation for `resource_type`, `cost_stream`, and `rate_source`.
- Hidden `_Metadata` sheet with `schema_version`, `generated_by`, and `import_mode`.
- `PriceHistory` sheet ready for historical price rows.

### 7.6 Column Aliases (Common Egyptian Excel Formats)
Support these aliases to reduce manual reformatting:

| Canonical | Common Aliases |
|-----------|----------------|
| `resource_code` | `code`, `كود المورد`, `resource_id` |
| `name_en` | `name`, `name_en`, `الاسم انجليزي`, `description_en` |
| `name_ar` | `name_ar`, `الاسم عربي`, `description_ar` |
| `resource_type` | `type`, `نوع المورد`, `category` |
| `cost_stream` | `stream`, `cost_stream`, `تصنيف التكلفة` |
| `uom` | `unit`, `وحدة`, `uom` |
| `unit_price_egp` | `price`, `السعر`, `unit_price`, `rate` |
| `price_date` | `date`, `التاريخ`, `effective_date` |
| `region` | `region`, `المنطقة`, `location`, `city` |
| `boq_item_code` / `template_name` | `item_code`, `boq_code`, `كود البند` |
| `qty_per_boq_unit` | `quantity`, `الكمية`, `coef`, `qty` |
| `wastage_pct` | `wastage`, `الهالك`, `loss`, `wastage_percent` |
| `cost_rate` | `rate`, `سعر الوحدة`, `unit_cost` |

---

## 8. Localization Requirements for Egypt

### 8.1 Bilingual Support
- Every resource must have both English and Arabic names (`Item.item_name` and `Item.item_name_ar`).
- BOQ item Arabic descriptions are a **known schema gap**; store them in the seed file for future migration to `BOQ Structure.description_ar` or `BOQ Item.description_ar`.
- Reports should be able to print Arabic descriptions on BOQs and cost sheets.

### 8.2 Regional Pricing
Egypt has significant regional price variance:
- Cairo / Giza
- Alexandria
- Delta (Tanta, Mansoura)
- Upper Egypt (Assiut, Sohag, Luxor)
- New Administrative Capital
- New Alamein
- Sinai / Red Sea

Use the dedicated `Resource Price History.region` field. Do not use `project` for region.

### 8.3 Overhead & Profit (عمارة وربح)
- Typical overhead: 10–15%
- Typical profit: 5–10%
- Total OH&P often 15–20% of direct cost.
- These are already modeled in `BOQ Cost Analysis` and `BOQ Item`.

### 8.4 Price Volatility & Locking
- `Resource Price History` tracks price changes over time.
- `get_suggested_rate()` supports an optional `as_of_date` parameter to fetch the latest price as of a specific date.
- Users can lock a project's price list to a specific date; imported prices must carry accurate `price_date` values for this to work.

### 8.5 Units Commonly Used in Egypt
| Resource | UOM |
|----------|-----|
| Cement | Ton, 50kg bag |
| Sand | m³ |
| Aggregate | m³ |
| Steel | Ton |
| Bricks | 1000 bricks, piece |
| Labor | Day, Hour |
| Equipment | Hour, Day |
| Paint | Liter, kg, m² coverage |
| Tiles | m², piece |

Ensure these UOMs exist in ERPNext master or are created during import.

---

## 9. Integration Points with Existing Engine

When building the import/data pipeline, respect these integration points:

1. **Resource creation** must populate ERPNext `Item` + construction custom fields.
2. **Price updates** must create `Resource Price History` rows (do not overwrite Item price silently).
3. **Rate analysis import** must create `BOQ Cost Analysis` drafts with `is_template=1`.
4. **Approval** is a separate user action; do not auto-submit unless explicitly requested.
5. **BOQ Item `fetch_cost_data`** reads from approved `BOQ Cost Analysis`; therefore imported analyses must be approved to affect live estimates.
6. **Existing PO/PI hooks** will continue to capture real transaction prices into `Resource Price History`; imported prices must be clearly tagged with `source_doctype = "Import"`.
7. **Suggested rates** now use all `Resource Price History` rows, including `Import` and `Manual`, not just PO/PI.

---

## 10. Deliverables Expected from This Agent

1. **Data Source Report** — list of reachable Egyptian cost data sources with URLs, reliability score, update frequency, scrapability, and access dates.
2. **Seed Data Package**:
   - `resources.csv` with 50–100 Egyptian resources and current prices.
   - `boq_item_templates.csv` with 50 common Egyptian BOQ items.
   - `rate_analysis.csv` with recipes linking items to resources.
   - `price_history.csv` with at least one historical row per resource.
3. **Excel Template** — `cost_database_template.xlsx` with the three mandatory sheets, validation, and sample/blank modes.
4. **Import API Specification** — recommended endpoint signature, permission requirements, validation rules, and dry-run behavior.
5. **Automated Import Validation Report** — sample output format listing errors, warnings, and row counts.
6. **Gap Analysis** — what data is missing / unreliable and needs manual entry or partnership.

---

## 11. Constraints & Non-Negotiables

1. **Do not query `CostItem` or `PlantResource`** — these are deprecated. Use `Item` + construction custom fields.
2. **All SQL must be parameterized** — no f-string SQL in any implementation.
3. **Preserve `Direct Labor Designation`** — do not modify that DocType.
4. **Currency handling** — default to EGP; use `exchange_rate` for foreign currency.
5. **Scope dimensions** — every `Resource Price History` row must have a `company`; `project` is optional; `region` is the geographic dimension.
6. **Do not auto-approve imported analyses** unless the user explicitly opts in.
7. **Data must be bilingual** where possible (English + Arabic).
8. **Use standard ERPNext UOMs**; create new UOMs only when necessary.
9. **Resource type enum is fixed:** Material, Labor, Plant, Subcontract, Overhead.
10. **Cost stream enum is fixed:** M, L, P, S, O.

---

## 12. Data Flow Summary

```
Egyptian Sources (PDFs, websites, Excel)
         ↓
   Seed CSVs / Excel Template
         ↓
   Import API — dry-run validation first
         ↓
   ERPNext Item  ←  Resources sheet
   Resource Price History  ←  Resources / Price History sheets
   BOQ Cost Analysis (Draft, is_template=1) + Details  ←  BOQItemTemplates + RateAnalysis sheets
         ↓
   User approval (or auto_submit=1) → BOQ Item.est_unit_cost updated → BOQ Header totals refreshed
         ↓
   PO/PI transactions continuously update Resource Price History
         ↓
   get_suggested_rate() uses PI → PO → Import/Manual → Item Price
```

---

## 13. Suggested First Sprint

1. **Week 1:** Research and catalog Egyptian data sources; produce `resources.csv` for top 50 materials/labor/equipment with Cairo prices.
2. **Week 2:** Produce `boq_item_templates.csv` + `rate_analysis.csv` for top 50 Egyptian BOQ items using standard rate-analysis recipes.
3. **Week 3:** Build Excel template and draft import API specification.
4. **Week 4:** Load seed data into a test site, run validation, and produce gap analysis.

---

*End of handoff. This document should be read together with `docs/ai/active/PLAN.md`, `docs/ai/active/IMPLEMENTATION.md`, `docs/ai/active/FINAL_DIFF.md`, and `docs/ai/SCHEMA_FACTS.md`.*
