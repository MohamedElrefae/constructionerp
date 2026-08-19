# Construction ERP — End-to-End User Guide
# Enterprise Workflow: Company → Cost Center → Project → BOQ

**Version:** 1.3
**Date:** 2026-08-20 (deployment-readiness remediation)
**Branch:** `develop`
**Tested by:** Playwright UI Runner + Browser QA + VFC test suite + cost-analysis engine suite
**Status:** Release validation passed — VO 23/23, Quantity Revisions 30/30, Transaction Validation 13/13, BOQ Link Queries 9/9, Scope Context 17/17, Cost Database 10/10, Cost Analysis Engine 17/17, and VFC 39/39

---

## Table of Contents

1. [Setup — Scope Context](#1-setup--scope-context)
2. [BOQ Header — Create & Lock](#2-boq-header--create--lock)
3. [BOQ Structure — WBS Tree](#3-boq-structure--wbs-tree)
4. [BOQ Item — Line Items](#4-boq-item--line-items)
5. [BOQ Item Stage — Measurement](#5-boq-item-stage--measurement)
6. [Cascade Blocker — Visual Guidance](#6-cascade-blocker--visual-guidance)
7. [Transaction Forms — Grid Blocker](#7-transaction-forms--grid-blocker)
8. [Variation Orders — Full Lifecycle](#8-variation-orders--full-lifecycle)
9. [Cost Estimation Engine (Phase 1)](#9-cost-estimation-engine-phase-1)
10. [Cost Database Import (Phase 2)](#10-cost-database-import-phase-2)
11. [Form Layout Engine (VFC) — Layout Customization](#11-form-layout-engine-vfc--layout-customization)
12. [Administration — Settings & Diagnostics](#12-administration--settings--diagnostics)
13. [Quick Reference — Feature Checklist](#13-quick-reference--feature-checklist)

---

## 1. Setup — Scope Context

### 1.1 Activate Scope Context

1. Navigate to **Construction Settings** (search in AwesomeBar)
2. Check **Enable Scope Context**
3. Check the dimensions you want active: Company, Cost Center, Project, Department
4. **Save**

**What happens:** The top bar now shows cascading scope selectors (Company → Cost Center → Project → Department). List views and forms will filter data to your selected scope.

### 1.2 Select Your Scope

1. In the top bar, click the **Company** dropdown → select your company
2. **Cost Center** dropdown auto-populates with your company's cost centers → select one
3. **Project** dropdown auto-populates → select your project
4. **Department** auto-populates if applicable

**Verify:** After selection, open any list view (e.g., BOQ Header list). Only records matching your scope appear. Open a new form — Project field is pre-filled from your scope.

### 1.3 Scope Filter Exclusions (Admin)

Use exclusions only when a DocType should be omitted from Scope Context's list-query filtering:

1. Navigate to **Construction Settings**
2. In the **Scope Filter Exclusions** field (under Scope Dimensions), add `Project` on a new line
3. **Save**

**Verify:** Lists for excluded DocTypes no longer receive the Scope Context SQL filter. This setting does not change BOQ Header project defaults or validation; use the active scope to create a BOQ Header.

### 1.4 Scope Drift Protection

**What it does:** If you change your scope context mid-session and try to save a form, the system detects the change and alerts you with "Your scope context has changed. Reloading form to prevent invalid attribution." The form auto-reloads with the new scope.

**Verify:** Open a form, change your scope in the top bar, then try to save. The alert appears and the form reloads. An audit log entry is created under **Error Log** for admin review.

---

## 2. BOQ Header — Create & Lock

### 2.1 Create BOQ Header

1. Navigate to **BOQ Header → New**
2. Fill in:
   - **Title:** e.g. "QA Test BOQ"
   - **Project:** automatically populated from your active Scope Context
   - **BOQ Type:** Tender / Contract
3. **Save**

**Note:** With Scope Context enabled, select the project in the top bar before creating the header. When Scope Context is disabled, integrations and imports may supply the project's internal value directly; the BOQ Header form does not expose a project selector.

**Visual cues:** If Project is empty, a **red accent border** appears on the Project field with a pill badge "Select Project first". After selecting a project, the accent clears.

### 2.2 WBS Tree

After saving the BOQ Header, open **BOQ Structure → Tree** to inspect the hierarchy. Each structure node carries its own rollup inline:

```
01 — Site Works (2 items · 9,000.00 · 0.00)
  01.01 — Excavation (1 item · 5,000.00 · 0.00)
  01.02 — Concrete (1 item · 4,000.00 · 0.00)
```

**Verify:** Create structures and items (sections 3-4 below), then open **BOQ Structure → Tree**. The tree updates automatically, and the totals stay attached to each node instead of appearing as a separate summary banner.

### 2.3 Lock the BOQ

1. On the BOQ Header form, click **Actions → Advance Status**
2. Progress through: **Draft → Pricing → Frozen → Locked**
3. After each step, **Save**

**Verify:** Status shows **Locked**, `Locked By` and `Locked Date` fields are populated. Only Locked headers appear in Variation Order dropdowns.

---

## 3. BOQ Structure — WBS Tree

### 3.1 Create Structure Groups

1. Navigate to **BOQ Structure → New**
2. Fill in:
   - **BOQ Header:** select your BOQ Header
   - **Title:** e.g. "Site Works"
   - **Is Group:** ✅ checked (this is a folder, not a leaf)
3. **Save**

### 3.2 Create Leaf Structures (for items)

1. Navigate to **BOQ Structure → New**
2. Fill in:
   - **BOQ Header:** select your BOQ Header
   - **Parent Structure:** select "Site Works" (parent group)
   - **Title:** e.g. "Excavation"
   - **Is Group:** ❌ unchecked (this is a leaf — items attach here)
3. **Save**

**Important:** BOQ Items can only be linked to **leaf structures** (`is_group=0`). If you try to save an item linked to a group structure, the system will reject it with: *"BOQ Item can only be linked to leaf nodes (is_group=0)."*

### 3.3 BOQ Structure Inline Rollups

On the BOQ Structure tree, the node label itself shows the rollup for that node's subtree. The tree does not use a separate summary banner.

Each node shows its own inline totals, and the BOQ Structure list includes ordinary `Item Count`, `Total Contract Value`, and `Total Budgeted Cost` columns.

---

## 4. BOQ Item — Line Items

### 4.1 Create BOQ Item

1. Navigate to **BOQ Item → New**
2. Fill in:
   - **BOQ Header:** select your BOQ Header
   - **Structure:** select a leaf structure (e.g. "Excavation")
   - **Cost Item:** e.g. "C25 Concrete Foundation"
   - **Quantity:** 100
   - **Unit:** Nos
   - **Contract Unit Price:** 50
3. **Save**

### 4.2 Breadcrumb Navigation

After saving, the BOQ Item form headline shows a breadcrumb:
```
VO QA Project → BOQ-2026-0646 → 01.01-Excavation → BOQI-BOQ-2026-0646-0001
```

This helps you understand your position in the hierarchy at a glance.

### 4.3 Quick Create Structure from BOQ Item

If you're on the BOQ Item form, have a BOQ Header selected, but no leaf structures exist yet:

1. Click the **Create → Create Leaf Structure** button
2. A dialog opens — enter Title and optional WBS Code
3. Click **Create**
4. The structure is created, and the `structure` field auto-selects the new node

**No more navigating away just to create a structure.**

---

## 5. BOQ Item Stage — Measurement

### 5.1 Onboarding Banner (First Visit)

When you open the BOQ Item Stage form for the first time, a **blue onboarding banner** appears at the top:

> "Start with **Project** → **BOQ Header** → **BOQ Structure** → **BOQ Item**. Each field unlocks the next."

- Click **"Got it"** to dismiss permanently
- Or just **save** the form — the banner auto-dismisses after first save

### 5.2 Create BOQ Item Stage

1. Navigate to **BOQ Item Stage → New**
2. Fill in the cascade fields: **Project → BOQ Header → BOQ Structure → BOQ Item**
3. Enter measurement data: **Planned Qty**, **Measured Executed Qty**, **Certified Qty**, **% Complete**
4. **Save**

The stage progress indicators appear showing Measured %, Certified %, and Progress %.

---

## 6. Cascade Blocker — Visual Guidance

This system guides you through cascading selection fields with **color-coded visual feedback**:

| State | Visual | Meaning |
|-------|--------|---------|
| **Red accent** | Red border + "Select X first" pill badge | This is the **active step** — select this field next |
| **Orange blocked** | Orange border, muted dropdown, not-openable | This field is **locked** until parent fields are filled |
| **Normal** | No special styling | Field is ready for use |

### 6.1 BOQ Item Stage — Full Cascade Verification

**Test: Open `/app/boq-item-stage/new`**

| Step | Action | Expected Visual |
|------|--------|-----------------|
| 1 | Open new form | `project` = red accent, `boq_header`/`boq_structure`/`boq_item` = orange blocked |
| 2 | Select Project | `project` = normal, `boq_header` = red accent, `boq_structure`/`boq_item` = orange blocked |
| 3 | Select BOQ Header | `project`/`boq_header` = normal, `boq_structure` = red accent, `boq_item` = orange blocked |
| 4 | Select BOQ Structure | `project`/`boq_header`/`boq_structure` = normal, `boq_item` = red accent |
| 5 | Select BOQ Item | All fields normal |

**Clear test:** Clear `boq_structure` → `boq_item` clears + re-blocks. Clear `boq_header` → both clear + re-block. Clear `project` → everything returns to empty blocked state.

**Dropdown click test:** When a field is orange-blocked, clicking its dropdown does NOT open. When accented (red), the dropdown opens normally.

### 6.2 BOQ Header — Project Accent

**Test: Open `/app/boq-header/new`**

- If scope pre-fills project → **no accent** (correct — project is already set)
- If project is empty → **red accent** + "Select Project first" pill badge
- Select a project → accent clears immediately
- Clear the project → accent reappears

### 6.3 Variation Order — BOQ Header Accent

**Test: Open `/app/variation-order/new`**

- `boq_header` shows **red accent** when empty (accent-only — dropdown is NOT blocked)
- Pill badge: "Select BOQ Header first"
- Open dropdown → only **Locked** BOQ Headers appear
- Select a Locked header → accent clears

---

## 7. Transaction Forms — Grid Blocker

The cascade blocker also works inside **child table grid rows** across 8 transaction DocTypes:

Purchase Order, Purchase Receipt, Purchase Invoice, Sales Invoice, Stock Entry, Timesheet, Journal Entry, Material Request

### 7.1 Gate Mechanism

Each transaction row has a **gate field** that must be opened before BOQ fields become active:

| DocType | Gate Field | Gate Value |
|---------|------------|------------|
| Purchase Order | `expense_category` | "Direct" |
| Purchase Receipt | `expense_category` | "Direct" |
| Purchase Invoice | `expense_category` | "Direct" |
| Sales Invoice | `is_progress_billing` | ✅ checked |
| Stock Entry | `expense_category` | "Direct" |
| Timesheet | `designation` | In `direct_labor_designations` list |
| Journal Entry | `expense_category` | "Direct" |
| Material Request | `expense_category` | "Direct" |

### 7.2 Test: Material Request Grid

1. Navigate to **Material Request → New**
2. Add a row in the **Items** child table
3. Leave `expense_category` as default (not "Direct")
   - **Expected:** All BOQ fields (`boq_header`, `boq_structure`, `boq_item`, `boq_item_stage`) are visually muted — no accent, no blocker
4. Set `expense_category` to **"Direct"**
   - **Expected:** Cascade blocker activates — `boq_header` shows "Select Project first", downstream fields blocked
5. Select BOQ Header → BOQ Structure → BOQ Item → BOQ Item Stage
   - **Expected:** Each step shows the same accent/blocker progression as the master form

### 7.3 Collapsed Row Visual Blocker

When grid rows are **collapsed** (not expanded for editing) and have blocked BOQ fields:

- The entire row appears **slightly dimmed** (opacity 65%)
- Hovering shows a **not-allowed cursor** on BOQ field columns
- Expanding the row shows the full blocker/accent guidance

**Test:** Create a Material Request with multiple items, set `expense_category = "Direct"`, collapse all rows. Observe the dimming. Expand a row — the full accent/blocker guidance appears.

### 7.4 Project Change Re-Blocks All Rows

**Test:** Open a Material Request with items that have BOQ fields filled. Clear the parent **Project** field.

- **Expected:** All rows' BOQ fields clear and show blocker states. Set a new project → all rows update their guidance.

---

## 8. Variation Orders — Full Lifecycle

### 8.1 Prerequisites

- BOQ Header with status **Locked**
- At least one BOQ Item under a leaf structure
- Feature flag **Enable Variation Orders** checked in Construction Settings

### 8.2 Part 1: Quantity Increase VO

| Step | Action | Verify |
|------|--------|--------|
| 1 | On Locked BOQ Header, click **Actions → Variation Orders** | VO list appears |
| 2 | Create new VO: BOQ Header = your locked BOQ, Reason = "Quantity increase" | VO saved |
| 3 | Add VO Line: Line Type = **Quantity Change**, BOQ Item = select your item | Item auto-populates |
| 4 | Set Revised Qty = 126, Revised Unit Price = 60 | Values saved |
| 5 | Add Rate Change Justification if qty change > 25% | Justification field visible |
| 6 | Status → **Submitted** → Save | Status updated |
| 7 | Status → **Approved by Engineer** → Save | Engineer Approval Date populated |
| 8 | **Verify:** Try editing Revised Qty → **blocked** (read-only after Engineer Approval) | P0-1 enforcement working |
| 9 | Status → **Approved by Client** → upload PDF → Save | Client Approval Date populated |
| 10 | Go to **BOQ Quantity Revision** list | New revision: Type = "Increase Above 25%", **Delta Quantity** = 26 |
| 11 | Open the BOQ Item | Original Qty = 100 (unchanged), Current Revised Qty = 126 |

### 8.3 Part 2: Quantity Decrease VO

| Step | Action | Verify |
|------|--------|--------|
| 1 | Create new VO: Reason = "Quantity decrease" | |
| 2 | VO Line: Line Type = Quantity Change, BOQ Item = same item, Revised Qty = 90 | |
| 3 | Submit → Engineer Approve → Client Approve | Status transitions work |
| 4 | Open BOQ Item | Current Revised Qty = 90 |
| 5 | BOQ Quantity Revision list | 3 revisions exist (Original Lock + Increase + Decrease) |

### 8.4 Part 3: Omission VO

| Step | Action | Verify |
|------|--------|--------|
| 1 | Create new VO: Reason = "Omit item" | |
| 2 | VO Line: Line Type = **Omission**, BOQ Item = item to omit | Revised Qty auto-set to 0 |
| 3 | Submit → Engineer Approve → Client Approve | |
| 4 | Open BOQ Item | Current Revised Qty = 0, Original Qty unchanged |
| 5 | Go to a transaction or VO item dropdown for this header | Omitted item is hidden from selectable BOQ Item dropdowns. |

### 8.5 Part 4: New Variation Item VO

| Step | Action | Verify |
|------|--------|--------|
| 1 | Create new VO: Reason = "Add new scope item" | |
| 2 | VO Line: Line Type = **New Item**, BOQ Structure = select group structure | |
| 3 | Fill Title, Unit, Revised Qty, Revised Unit Price | No Item Code field needed |
| 4 | Submit → Engineer Approve → Client Approve | |
| 5 | Open VO Line | Created BOQ Item and Created BOQ Structure are populated |
| 6 | Open the created BOQ Item | Is Variation Item = ✅, Original Qty = 0, Current Revised Qty = your value |

### 8.6 Part 5: Totals & Idempotency

| Step | Action | Verify |
|------|--------|--------|
| 1 | Open BOQ Header | Total Contract Value = original sum, Total Revised Value > Total Contract Value |
| 2 | Open an already-approved VO, click Save again (no changes) | No duplicate revisions created |
| 3 | BOQ Header → Actions → Variation Orders | All VOs appear in list |

---

## 9. Cost Estimation Engine (Phase 1)

The Cost Estimation Engine builds **resource-based unit rates** for your BOQ Items. Instead of typing a lump-sum estimated cost, you break each BOQ Item down into resources (materials, labor, plant, subcontract, overhead) with quantities, wastage, and rates — and the engine rolls the rate up with overhead and profit.

### 9.1 Key Concepts

| Concept | What it is |
|---------|-----------|
| **Resource** | A standard ERPNext **Item** flagged as a construction resource (custom fields: *Is Construction Resource*, *Construction Resource Type*, *Default Cost Stream*, *Item Name (Arabic)*). Not a stock item. |
| **Resource Price History** | The auditable price ledger. Every price (from Purchase Orders, Purchase Invoices, imports, or manual entry) lands here as a dated, sourced row. |
| **BOQ Cost Analysis** | A submittable document holding the resource breakdown for one BOQ Item — or a reusable **template** (no BOQ Item). |
| **Cost Stream** | Classification letter: **M** Material, **L** Labor, **P** Plant, **S** Subcontract, **O** Overhead. |

### 9.2 Resource Price History — The Price Ledger

**Automatic capture:** When you **submit** a Purchase Invoice or Purchase Order, a price-history row is created for every item row (rate, UOM, date, supplier, company, source document + row). When you **cancel** the document, those rows are marked **Cancelled** — never deleted — so the audit trail survives.

**Manual entry:** Navigate to **Resource Price History → New** and fill:

- **Item Code** (the resource), **Resource Type**, **Rate**, **Currency**, **UOM**
- **Price Date**, **Company** (required)
- Optional: **Supplier**, **Project**, **Region** (e.g. Cairo, Alexandria), **Remarks**
- **Status** defaults to **Active**

**Verify:** Submit a Purchase Invoice for a resource item, then open the Resource Price History list filtered by that item — a new Active row exists with Source DocType = Purchase Invoice. Cancel the invoice — the row flips to Cancelled.

**Permissions:** System Manager has full access. Construction Owner and Project Manager can read/report/export. Site Engineer has no create/write access.

### 9.3 Create a BOQ Cost Analysis for a BOQ Item

1. Navigate to **BOQ Cost Analysis → New**
2. Fill in the header:
   - **Title**, **BOQ Item** (required for non-template analyses), **Company**
   - **Analysis UOM**, **Analysis Qty** (the quantity this breakdown prices), **Currency**
   - **Overhead %** and **Profit %**
3. Add detail rows in the **Details** table. For each resource:

| Field | Meaning |
|-------|---------|
| Cost Stream | M / L / P / S / O |
| Item Code | The resource (Item) |
| Resource UOM | Unit of the resource |
| Qty per BOQ Unit | Resource quantity per 1 unit of the BOQ item |
| Wastage % | e.g. 3% — inflates the amount |
| Cost Rate | Unit rate for the resource |
| Rate Source | Manual, Import, Last PI, Last PO, Item Price, Resource Price History, … |

4. **Save**. Totals auto-calculate:
   - Row amount = `qty × rate × (1 + wastage%)`
   - **Total Direct Cost** = Σ row amounts (divided by Analysis Qty for unit cost)
   - **Total Unit Cost** = direct + overhead + profit → also shown as **Suggested Sell Rate**
5. **Submit** to approve. On approval:
   - The BOQ Item's **Est. Unit Cost** is updated with the analysis Total Unit Cost
   - The BOQ Header budget totals refresh
   - Any previously approved analysis for the same BOQ Item becomes **Superseded** — only one **Approved** analysis per BOQ Item at any time

**Verify:** Approve a second analysis for the same BOQ Item — the first flips to Superseded. Cancel the new one — the prior analysis is automatically restored to Approved and the BOQ Item cost is refreshed.

**Non-template validation:** Saving a non-template analysis without a BOQ Item is rejected: *"BOQ Item is required for non-template analyses."*

### 9.4 Rate Suggestion Priority

When rates are suggested or repriced (Phase 2 import, bulk reprice), the engine resolves each resource's rate in this order:

1. **Last PI** — latest active price from a submitted Purchase Invoice
2. **Last PO** — latest from a submitted Purchase Order
3. **Last Price History** — latest active row from any other source (Import, Manual…)
4. **Item Price** — standard ERPNext buying price list

Supplier, company, **region**, and as-of date filters are respected when provided. Cancelled rows are always excluded.

### 9.5 Estimation Reports (service layer)

The engine ships five service-level report functions (see `construction/services/boq_report_service.py`): analysis summary per BOQ Header, cost vs. contract per item, resource requirement summary, resource price history query, and missing-analysis items. These power backend queries and the Phase 2 export tooling; UI report wiring is planned for a later phase.

---

## 10. Cost Database Import (Phase 2)

Phase 2 adds an **Excel-based cost database workflow**: download a template, fill it with your resources / BOQ item templates / rate-analysis recipes, and import it. The import creates Items, price-history rows, and reusable analysis templates — and it is **idempotent**: re-importing the same file never duplicates data.

### 10.1 Download the Excel Template

Open in your browser (or API client) while logged in:

```
/api/method/construction.api.cost_database_api.download_cost_database_template?mode=blank
```

Use `mode=sample` for a pre-filled illustrative Egyptian cost database (cement, sand, aggregate, steel, mason, helper, mixer + plain concrete / RC column / brick wall templates with full rate recipes).

The workbook contains:

| Sheet | Purpose |
|-------|---------|
| **Resources** | One row per resource: code, names (EN/AR), type, stream, UOM, unit price, currency, exchange rate, company, region, price date, source, supplier, remarks |
| **BOQItemTemplates** | One row per BOQ item template: template name, descriptions (EN/AR), category, UOM, overhead %, profit %, currency |
| **RateAnalysis** | Resource recipes per template: template name, resource code, qty per BOQ unit, wastage %, cost stream, cost rate, rate source, supplier, remarks |
| **PriceHistory** | Same columns as Resources — reserved for dated price updates |
| **_Metadata** (hidden) | Template version info |

Dropdown validation is built in for `resource_type`, `cost_stream`, and `rate_source`. **Arabic column headers are accepted** on import (e.g. `كود المورد`, `السعر`, `نوع المورد`) alongside the English names and common aliases (`code`, `price`, `unit`…).

### 10.2 Fill the Template

Required columns per sheet:

- **Resources:** `resource_code`, `name_en`, `resource_type`, `cost_stream`, `uom`, `unit_price_egp`
- **BOQItemTemplates:** `template_name`, `description_en`, `uom`, `overhead_pct`, `profit_pct`
- **RateAnalysis:** `template_name`, `resource_code`, `qty_per_boq_unit`, `cost_stream`, `cost_rate`

Rules enforced at import: resource types must be Material/Labor/Plant/Subcontract/Overhead; cost streams must be M/L/P/S/O (mismatch with the resource type produces a warning); `wastage_pct` must be 0–100; every RateAnalysis row must reference a template and resource that exist in the workbook.

### 10.3 Import — Dry Run First

POST the file to:

```
/api/method/construction.api.cost_database_api.import_cost_database
```

Multipart form fields:

| Field | Required | Meaning |
|-------|----------|---------|
| `file` | ✅ | The .xlsx workbook |
| `company` | ✅ | Target company for prices and templates |
| `dry_run` | — | `1` = validate only, create nothing (recommended first pass) |
| `auto_submit` | — | `1` = submit created templates (Approved) instead of leaving Draft |
| `region` | — | Default region for rows without one |
| `price_date` | — | Default price date (YYYY-MM-DD) for rows without one |

**Permission:** you need **create** permission on Resource Price History (System Manager by default).

**Always dry-run first:** run with `dry_run=1`, review the returned `errors`/`warnings`, fix the workbook, then re-run with `dry_run=0`.

### 10.4 What the Import Creates

- **Items** — new Items flagged as construction resources (type, stream, Arabic name) or existing Items updated in place
- **Resource Price History** — one Active row per resource price, tagged `source_doctype = Import` with the file name and your region/price-date defaults
- **BOQ Cost Analysis templates** — Draft (or Submitted with `auto_submit=1`) analyses with `Is Template = 1`, holding the imported rate recipes, category, and Arabic description

### 10.5 Idempotency — Safe Re-Imports

Re-importing the same workbook is safe:

- **Identical price rows are skipped** (same item, date, rate, currency, UOM, company, region, supplier, source) — no duplicates
- **Draft templates are updated in place** (details replaced with the workbook's recipe)
- **Submitted templates are skipped** with a warning — approved templates are never silently mutated

The result payload separates `records_created`, `records_updated`, and `records_skipped`, so you always know exactly what happened.

**Verify:** Import a workbook, note the created counts. Import the identical file again — created counts are 0, price rows appear in `records_skipped`, templates in `records_updated`. Change one price and re-import — exactly one new price-history row is appended and the draft template's rate updates; still only one template exists.

### 10.6 Bulk Repricing After New Prices

Once new prices land in the ledger (imports, POs, PIs), update your Draft analyses in one call:

```
POST /api/method/construction.api.cost_database_api.reprice_cost_analyses
{"company": "Your Company", "dry_run": false}
```

Optional filters: `boq_header`, `boq_item`, `item_code`, `resource_type`, `cost_stream`, `region`, `as_of_date`. Only **Draft** analyses are repriced — Approved analyses must be superseded by a new version, never silently mutated. Use `dry_run: true` to preview how many rows would change.

---

## 11. Form Layout Engine (VFC) — Layout Customization

The Form Layout Engine (VFC) lets you customise how fields are arranged on any form. You can group fields into named sections, choose a column density, hide unwanted fields, and save your layout as a personal profile.

### 11.1 Access

1. Open any form (e.g., Sales Invoice, BOQ Header, User Scope Context)
2. Click the **Form Config** button (grid icon, top-right)
3. The **Layout Controls** panel opens as a dialog modal

### 11.2 Sections Editor

- **Sections** tab shows the form's current layout sections
- **Add Section:** Enter a section name and click **Add**
- **Remove Section:** Click the × icon on a section header
- **Add Field to Section:** Select a field from the dropdown and click **Add**
- **Remove Field:** Click the × icon on a field badge
- Changes are applied when you click **Apply & Save**

### 11.3 Density Control

- Choose **1 column**, **2 columns** (default), or **3 columns** grid layout
- Fields are distributed left-to-right, top-to-bottom
- Density is saved to your browser's localStorage immediately

### 11.4 Hidden Fields

- **Hidden Fields** tab shows all fields on the form with checkboxes
- Uncheck a field to hide it from the form
- Hidden fields are saved per-user per-DocType
- Fields hidden by Frappe's own dependency rules (e.g., `depends_on`) cannot be unhidden

### 11.5 Presets

- **Presets** tab lets you save and load named layout profiles
- **Save Current As:** Name the current layout configuration (sections + hidden fields) and save it
- **Apply:** Select a saved preset from the list to apply it immediately
- Presets are stored in your browser's localStorage

### 11.6 Revert to Default/Native

- Click **Revert to Default/Native** button at the bottom of the panel
- This resets:
  - **Density** → back to the profile-defined default
  - **Hidden fields** → all VFC-hidden fields are restored
  - **Preset** → reset to "Default"
  - **Personal layout** → your personal `for_user` profile is deleted (server-side)
- After revert, the form refreshes immediately
- Non-admin users can always revert their own personal layout

### 11.7 Profile Persistence

- Layout profiles are stored server-side as **Form Layout Profile** records
- System Administrators see a **Sections Editor** tab for creating/sharing profiles
- Regular users see only **Sections** (read-only) and personal overrides
- Personal overrides (`for_user` profiles) persist until explicitly reverted

## 12. Administration — Settings & Diagnostics

### 12.1 Construction Settings Reference

| Setting | Location | Purpose |
|---------|----------|---------|
| Enable Scope Context | Main tab | Master switch for scope filtering |
| Scope Dimensions (Company/Cost Center/Project/Department) | Scope Dimensions section | Which dimensions appear in top bar |
| Scope Filter Exclusions | Scope Dimensions section | DocTypes exempt from scope SQL injection (one per line) |
| Enable BOQ Cascade Filtering | BOQ Cascade section | Off / On / Strict — controls dropdown filtering |
| Enable Variation Orders | Improve Now section | Master switch for VO functionality |
| Direct Labor Designations | Improve Now section | Designations eligible for Timesheet BOQ gates |

### 12.2 Cache Bust Verification

When a new version is deployed, verify assets are loaded fresh:

1. Open DevTools → **Network** tab
2. Refresh the page
3. Find these files and check version params:

| File | Expected Version |
|------|-----------------|
| `modern_theme.css` | `?v=2.5.7` |
| `ct_link_control.js` | `?v=16` |
| `boq_filters.js` | `?v=8` |
| `filter_fix.js` | `?v=11` |
| `scope_context_form_defaults.js` | `?v=3` |

### 12.3 Scope Drift Audit Log

When a scope drift is detected during save, an entry is created in the **Error Log** (search "BOQ Scope Drift"). The log includes:
- User who triggered the drift
- Form type and name being saved
- Previous and current scope tokens

Admins can review these to identify users who frequently change scope mid-session.

---

## 13. Quick Reference — Feature Checklist

### Scope Context
- [ ] Top bar shows cascading scope selectors
- [ ] List views filter to selected scope
- [ ] New forms pre-fill scope values
- [ ] Scope drift alert on save after scope change
- [ ] Project field accent on any new form with empty project
- [ ] Dynamic whitelist excludes specified DocTypes

### BOQ Cascade Blocker
- [ ] Red accent on active step field
- [ ] Orange blocked + dropdown locked on blocked fields
- [ ] Pill badge with "Select X first" on blocked/accented fields
- [ ] Clearing parent field clears + re-blocks all downstream
- [ ] Accent persists after save if field still empty (not gated on `is_new()`)
- [ ] Grid rows show accent/blocker in child tables
- [ ] Collapsed rows show dimmed visual state
- [ ] Grid rows re-block on child project change

### Variation Orders
- [ ] Only Locked BOQ Headers appear in VO dropdown
- [ ] VO Lines locked after Engineer Approval (P0-1)
- [ ] Quantity Change: auto-creates revision with delta + rate change detection
- [ ] Omission: auto-sets qty to 0, hides item from future dropdowns
- [ ] New Item: creates BOQ Item + Structure, no Item Code required
- [ ] Totals: Original contract value unchanged, revised value reflects VOs
- [ ] Idempotency: re-saving approved VO creates no duplicate revisions
- [ ] Client Approval: PDF upload required, rejection possible at any stage

### Cost Estimation Engine (Phase 1)
- [ ] PO/PI submission auto-creates Active Resource Price History rows; cancel marks them Cancelled (never deleted)
- [ ] Manual price entry works with region, supplier, and project fields
- [ ] Analysis detail rows compute amount = qty × rate × (1 + wastage%)
- [ ] Total Unit Cost = direct + overhead + profit; Suggested Sell Rate mirrors it
- [ ] Submitting an analysis updates BOQ Item Est. Unit Cost and header budget totals
- [ ] Only one Approved analysis per BOQ Item — previous becomes Superseded
- [ ] Cancelling an approved analysis restores the prior Superseded one
- [ ] Non-template analysis without BOQ Item is rejected
- [ ] Rate suggestion order: Last PI → Last PO → Last Price History → Item Price
- [ ] Site Engineer cannot create/write analyses or price history

### Cost Database Import (Phase 2)
- [ ] Blank and sample templates download with 4 visible sheets + hidden `_Metadata`
- [ ] Dropdown validation present for resource_type / cost_stream / rate_source
- [ ] Arabic and alias column headers are accepted on import
- [ ] Dry run validates and creates nothing; reports errors/warnings
- [ ] Import creates Items (flagged as construction resources), price rows (source = Import), and Draft templates
- [ ] `auto_submit=1` submits created templates
- [ ] Re-import of the identical file creates nothing (skips/upserts only)
- [ ] Re-import with a changed price appends exactly one new price row and updates the draft template
- [ ] Submitted templates are skipped on re-import, never mutated
- [ ] Bulk reprice touches Draft analyses only; dry_run preview available

### Form Layout Engine (VFC)
- [ ] Form Config button visible in the form toolbar (grid icon) — opens Sections Editor
- [ ] **Sections Editor tab:** Drag fields between sections, create/rename/remove sections
- [ ] **Density control tab:** Choose 1, 2, or 3-column grid layout
- [ ] **Hidden fields tab:** Toggle individual field visibility via checkboxes
- [ ] **Presets tab:** Name and save layout configurations, apply from a list
- [ ] **Revert button:** Fully resets density, hidden fields, preset, and personal layout to default/native
- [ ] Non-admin users can revert their own personal layout via the revert button
- [ ] Changes persist across page reload (localStorage + server-side profile)
- [ ] Form refreshes immediately after Apply or Revert

### Admin
- [ ] Construction Settings: Scope Filter Exclusions configurable
- [ ] Error Log: Scope Drift events logged for audit
- [ ] WBS Tree panel visible on BOQ Header form
- [ ] Quick Create Structure available on BOQ Item form
- [ ] Onboarding banner on first BOQ Item Stage visit

---

## Appendix A — Test Evidence

The following automated and manual test evidence is available:

| Test Suite | Location | Result |
|------------|----------|--------|
| VO Quantity Revision (27 steps) | `docs/feature_reviews/evidence/ev_067_ui_tests/VO_QUANTITY_REVISION_MANUAL_TEST.md` | 27/27 ✅ |
| Screenshots | `docs/feature_reviews/evidence/ev_067_ui_tests/*.png` | 11 captures |
| Scope Context (17 tests) | `construction/tests/test_scope_context.py` | 17/17 integration checks |
| Transaction validation + gate transitions (13 tests) | `construction/tests/test_transaction_validation.py` | 13/13 ✅ |
| BOQ Link Queries (9 tests) | `construction/tests/test_boq_link_queries.py` | 9/9 ✅ |
| Quantity Revisions (30 tests) | `construction/tests/test_quantity_revisions.py` | 30/30 ✅ |
| Cost Estimation Engine (17 tests) | `construction/tests/test_cost_analysis_engine.py` | 17/17 ✅ |
| Cost Database API (10 tests) | `construction/tests/test_cost_database_api.py` | 10/10 ✅ |
| VFC Backend (39 tests) | `construction/tests/test_vfc_backend.py` | 39/39 ✅ |
| Cross-App Review | `docs/CROSS_APP_CONSISTENCY_REVIEW.md` | 100% readiness |

## Appendix B — Known Constraints

1. **Collapsed grid rows:** Visual blocker (dimming) works for collapsed rows, but the `__ct_boq_blocked` engine flag is only set when the row is expanded. This is a Frappe framework limitation — `gridRow.fields_dict` is only populated for open rows.

2. **BOQ Structure `is_group=0` filter:** Only leaf structures appear in item dropdowns. Users must create leaf structures before attaching items. Use the **Quick Create Structure** button on the BOQ Item form to create one without navigating away.

3. **Onboarding banner:** Dismissed permanently after clicking "Got it" or after first save. Clear localStorage key `ct_boq_stage_onboarding_dismissed` to show it again.

4. **Cost database templates are a library, not auto-applied:** Imported BOQ Cost Analysis templates (`Is Template = 1`) hold reusable rate recipes. Applying a template's rates to a live BOQ Item analysis is currently a manual copy step; automated template application is planned for a later phase.

5. **Estimation reports are service-layer only:** The five estimation report functions (§9.5) are backend services. They are not yet wired as Desk query reports.

---

*End of User Guide. For developer reference, see `docs/CROSS_APP_CONSISTENCY_REVIEW.md` and `docs/PHASE1_CASCADE_BLOCKER_IMPLEMENTATION_PLAN.md`.*
