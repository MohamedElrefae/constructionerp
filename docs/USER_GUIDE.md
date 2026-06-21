# Construction ERP — End-to-End User Guide
# Enterprise Workflow: Company → Cost Center → Project → BOQ

**Version:** 1.1
**Date:** 2026-06-21 (VFC Phase 3 stabilization + full reset)
**Branch:** `develop`
**Tested by:** Playwright UI Runner + Browser QA + VFC test suite
**Status:** All features verified — 27/27 VO test + 72/72 cascade blocker assertions passed

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
9. [Form Layout Engine (VFC) — Layout Customization](#9-form-layout-engine-vfc--layout-customization)
10. [Administration — Settings & Diagnostics](#10-administration--settings--diagnostics)
11. [Quick Reference — Feature Checklist](#11-quick-reference--feature-checklist)

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

If users need to switch projects freely without scope restrictions:

1. Navigate to **Construction Settings**
2. In the **Scope Filter Exclusions** field (under Scope Dimensions), add `Project` on a new line
3. **Save**

**Verify:** Open a BOQ Header form — the Project dropdown now shows all projects, not just the scoped one. The Permission Error popup on BOQ Header new form is resolved.

### 1.4 Scope Drift Protection

**What it does:** If you change your scope context mid-session and try to save a form, the system detects the change and alerts you with "Your scope context has changed. Reloading form to prevent invalid attribution." The form auto-reloads with the new scope.

**Verify:** Open a form, change your scope in the top bar, then try to save. The alert appears and the form reloads. An audit log entry is created under **Error Log** for admin review.

---

## 2. BOQ Header — Create & Lock

### 2.1 Create BOQ Header

1. Navigate to **BOQ Header → New**
2. Fill in:
   - **Title:** e.g. "QA Test BOQ"
   - **Project:** select your project (pre-filled if scope context is active)
   - **BOQ Type:** Tender / Contract
3. **Save**

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
   - **Title:** e.g. "C25 Concrete Foundation"
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
| 10 | Go to **BOQ Quantity Revision** list | New revision: Type = "Increase Above 25%", Delta = 26 |
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
| 5 | Go to BOQ Item list for this header | Omitted item hidden from dropdowns (exclude_zero_revised active) |

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

## 9. Form Layout Engine (VFC) — Layout Customization

The Form Layout Engine (VFC) lets you customise how fields are arranged on any form. You can group fields into named sections, choose a column density, hide unwanted fields, and save your layout as a personal profile.

### 9.1 Access

1. Open any form (e.g., Sales Invoice, BOQ Header, User Scope Context)
2. Click the **pencil icon** in the form toolbar (top-right)
3. The **Layout Controls** panel opens as a dialog modal

### 9.2 Sections Editor

- **Current Sections** tab shows the form's current layout sections
- **Add Section:** Enter a section name and click **Add**
- **Remove Section:** Click the × icon on a section header
- **Add Field to Section:** Select a field from the dropdown and click **Add**
- **Remove Field:** Click the × icon on a field badge
- Changes are applied when you click **Apply & Save**

### 9.3 Density Control

- Choose **1 column**, **2 columns** (default), or **3 columns** grid layout
- Fields are distributed left-to-right, top-to-bottom
- Density is saved to your browser's localStorage immediately

### 9.4 Hidden Fields

- **Hidden Fields** tab shows all fields on the form with checkboxes
- Uncheck a field to hide it from the form
- Hidden fields are saved per-user per-DocType
- Fields hidden by Frappe's own dependency rules (e.g., `depends_on`) cannot be unhidden

### 9.5 Presets

- **Presets** tab lets you save and load named layout profiles
- **Save Current As:** Name the current layout configuration (sections + hidden fields) and save it
- **Apply:** Select a saved preset from the list to apply it immediately
- Presets are stored in your browser's localStorage

### 9.6 Revert to Default/Native

- Click **Revert to Default/Native** button at the bottom of the panel
- This resets:
  - **Density** → back to the profile-defined default
  - **Hidden fields** → all VFC-hidden fields are restored
  - **Preset** → reset to "Default"
  - **Personal layout** → your personal `for_user` profile is deleted (server-side)
- After revert, the form refreshes immediately
- Non-admin users can always revert their own personal layout

### 9.7 Profile Persistence

- Layout profiles are stored server-side as **Form Layout Profile** records
- System Administrators see a **Sections Editor** tab for creating/sharing profiles
- Regular users see only **Current Sections** (read-only) and personal overrides
- Personal overrides (`for_user` profiles) persist until explicitly reverted

## 10. Administration — Settings & Diagnostics

### 10.1 Construction Settings Reference

| Setting | Location | Purpose |
|---------|----------|---------|
| Enable Scope Context | Main tab | Master switch for scope filtering |
| Scope Dimensions (Company/Cost Center/Project/Department) | Scope Dimensions section | Which dimensions appear in top bar |
| Scope Filter Exclusions | Scope Dimensions section | DocTypes exempt from scope SQL injection (one per line) |
| Enable BOQ Cascade Filtering | BOQ Cascade section | Off / On / Strict — controls dropdown filtering |
| Enable Variation Orders | Improve Now section | Master switch for VO functionality |
| Direct Labor Designations | Improve Now section | Designations eligible for Timesheet BOQ gates |

### 10.2 Cache Bust Verification

When a new version is deployed, verify assets are loaded fresh:

1. Open DevTools → **Network** tab
2. Refresh the page
3. Find these files and check version params:

| File | Expected Version |
|------|-----------------|
| `modern_theme.css` | `?v=2.5.6` |
| `ct_link_control.js` | `?v=13` |
| `boq_filters.js` | `?v=5` |
| `filter_fix.js` | `?v=7` |
| `scope_context_form_defaults.js` | `?v=3` |

### 9.3 Scope Drift Audit Log

When a scope drift is detected during save, an entry is created in the **Error Log** (search "BOQ Scope Drift"). The log includes:
- User who triggered the drift
- Form type and name being saved
- Previous and current scope tokens

Admins can review these to identify users who frequently change scope mid-session.

---

## 10. Quick Reference — Feature Checklist

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

### Form Layout Engine (VFC)
- [ ] Layout icon visible in the form toolbar (pencil icon) — opens Sections Editor
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
| Scope Context (14 tests) | `construction/tests/test_scope_context.py` | All passing |
| Gate Transitions (3 tests) | `construction/tests/test_transaction_validation.py` | All passing |
| Cross-App Review | `docs/CROSS_APP_CONSISTENCY_REVIEW.md` | 100% readiness |

## Appendix B — Known Constraints

1. **Collapsed grid rows:** Visual blocker (dimming) works for collapsed rows, but the `__ct_boq_blocked` engine flag is only set when the row is expanded. This is a Frappe framework limitation — `gridRow.fields_dict` is only populated for open rows.

2. **BOQ Structure `is_group=0` filter:** Only leaf structures appear in item dropdowns. Users must create leaf structures before attaching items. Use the **Quick Create Structure** button on the BOQ Item form to create one without navigating away.

3. **Onboarding banner:** Dismissed permanently after clicking "Got it" or after first save. Clear localStorage key `ct_boq_stage_onboarding_dismissed` to show it again.

---

*End of User Guide. For developer reference, see `docs/CROSS_APP_CONSISTENCY_REVIEW.md` and `docs/PHASE1_CASCADE_BLOCKER_IMPLEMENTATION_PLAN.md`.*
