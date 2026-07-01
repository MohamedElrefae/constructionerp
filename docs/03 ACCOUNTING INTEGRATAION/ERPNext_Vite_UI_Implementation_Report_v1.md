# End-to-End Technical Implementation Report
# ERPNext v16 Construction App — Vite UI Integration

**Prepared for:** Software Consultant Review & Approval  
**Prepared by:** Kimi (Software Consultant)  
**Date:** 2026-05-28  
**Version:** 1.0 — UI Stream Only  
**Classification:** Internal — Requires Consultant Approval Before Execution

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current System State](#2-current-system-state)
3. [Problem Statement](#3-problem-statement)
4. [Vite UI Integration — Strategy](#4-vite-ui-integration--strategy)
5. [Implementation Roadmap](#5-implementation-roadmap)
6. [Risk Assessment & Mitigation](#6-risk-assessment--mitigation)
7. [Resource Requirements](#7-resource-requirements)
8. [Success Criteria](#8-success-criteria)
9. [Approval Checklist](#9-approval-checklist)
10. [Appendices](#10-appendices)

---

## 1. Executive Summary

This report addresses a critical user experience gap in the **Elrefae Construction ERP** running on **ERPNext v16.18.3 + Frappe v16.18.1**:

**The Gap:** The existing Vite + MUI accounting system delivers an "alive and vibrant" user experience with card-style forms, gradient buttons, blue accent sections, and smooth animations. ERPNext v16's default forms feel rigid, outdated, and visually disconnected from this standard.

**The Goal:** Replicate the Vite app's visual language inside ERPNext v16 forms, lists, and dialogs — without fighting Frappe's layout engine or creating maintenance debt.

**The Core Insight:**
> **"Make ERPNext look like Vite, but think like ERPNext."**

Do not replicate the Vite app's React-driven layout engine (drag-and-drop reordering, per-field width toggles, dynamic DOM manipulation). Instead, skin ERPNext's stable schema-driven forms to match Vite's visual language, then add smart layout controls that work within Frappe's constraints.

**Consultant Recommendation:** Approve a **3-Phase, 14-Day implementation** starting with environment stabilization, followed by visual foundation, then smart layout controls.

---

## 2. Current System State

### 2.1 Environment

| Property | Value | Status |
|----------|-------|--------|
| Bench Path | `/home/mohamed/frappe-bench` | ✅ |
| ERPNext Version | `16.18.3` | ✅ |
| Frappe Version | `16.18.1` | ✅ |
| Python Version | `3.14.5` | ✅ |
| Site | `v16.localhost` | ✅ |
| `developer_mode` | **Disabled** | ⚠️ **BLOCKER** |
| Scheduler | **Disabled** | ⚠️ **BLOCKER** |
| Git Branch | `develop` (8 uncommitted files) | ⚠️ |

### 2.2 Installed Apps

| App | Version | Branch | Purpose |
|-----|---------|--------|---------|
| `frappe` | `16.18.1` | `version-16` | Framework core |
| `erpnext` | `16.18.3` | `version-16` | GL, AP, AR, Projects, Stock |
| `construction` | `0.0.4` | `develop` | Custom construction ERP |

### 2.3 Construction App — Existing UI Assets

**CSS Files:** 16 theme files in `public/css/`  
**JS Files:** 20+ files in `public/js/` (theme loaders, scope context, BOQ filters, overrides)  
**Custom DocTypes:** 12 (BOQ Header, BOQ Item, BOQ Structure, BOQ Item Stage, CostItem, Construction Settings, Construction Theme, Modern Theme Settings, User Desk Theme, User Scope Context, Direct Labor Designation, PlantResource)  
**Overrides:** `scope_enforcement.py`, `scope_query.py`, `switch_theme.py`  
**Services:** `boq_accounting.py`, `boq_lifecycle.py`, `boq_transaction_validation.py`, `boq_operational.py`, etc.

### 2.4 Vite App — Source of Truth for UI

| Property | Value |
|----------|-------|
| Repository | `https://github.com/MohamedElrefae/accounting-system` |
| Framework | React 18.2.0 + TypeScript |
| Build Tool | Vite 7.1.2 |
| UI Library | Material UI (MUI) v5.15.15 |
| State | Zustand |
| Forms | React Hook Form + Zod/Yup |
| Animations | Framer Motion |
| Tables | MUI X DataGrid 8.13.1 |
| Backend | Supabase |

**Key Visual Characteristics:**
- **Primary Color:** `#2076FF` (bright blue)
- **Background (Dark):** `#181A20`
- **Surface (Dark):** `#23272F`
- **Font:** Segoe UI, Tahoma, Geneva, Verdana
- **Buttons:** Gradient (`linear-gradient(135deg, #2076FF, darker shade)`), hover `translateY(-2px)` + shadow
- **Inputs:** Rounded `8px`, focus ring `0 0 0 3px rgba(32,118,255,0.12)`
- **Sections:** Card-style with `border-left: 4px solid #2076FF`, uppercase title, letter-spacing
- **Tables:** Sticky header, alternating rows, hover highlight
- **Animations:** Fade-slide `200ms`, button hover `0.2s ease`

### 2.5 BOQ System — Form Context

The BOQ Header, BOQ Item, BOQ Structure, and BOQ Item Stage forms are the **primary user-facing surfaces** that must match the Vite app's visual language. These forms are used daily by project managers, site engineers, and accountants.

**Current Form Issues:**
- Flat design with no elevation or card separation
- Basic inputs with no focus ring or hover state
- Static buttons with no gradient or transform
- Section headers are plain text with no visual hierarchy
- No status visualization at form level
- Tables in child rows look like spreadsheets, not modern data grids

---

## 3. Problem Statement

### 3.1 UI Problem

**Observation:** The Vite + MUI accounting system delivers an "alive and vibrant" user experience that has received positive client feedback. ERPNext v16's default forms feel rigid, outdated, and inconsistent with this visual language.

**Specific Gaps:**
1. **Visual Mismatch:** ERPNext default forms use flat design, muted colors, and basic inputs. The Vite app uses gradient buttons, card sections, blue accent borders, and rich shadows.
2. **Layout Rigidity:** ERPNext forms are schema-driven (DocType JSON defines field order and columns). The Vite app has dynamic 1/2/3 column layouts, drag-and-drop reordering, and per-field width toggles.
3. **Interaction Polish:** The Vite app has smooth animations (fade-slide, hover transforms, focus rings). ERPNext defaults are static.
4. **Dark Mode:** The Vite app has a refined dark mode (`#181A20` background, `#23272F` surfaces). ERPNext's dark mode is functional but not visually aligned.

### 3.2 Constraint Analysis

**What We Cannot Change (Frappe Architecture):**
- HTML structure of forms (schema-driven, server-rendered)
- Field order (defined in DocType JSON)
- Column count per section (defined in DocType JSON)
- Form controller lifecycle (Frappe manages `onload`, `refresh`, `validate`)

**What We Can Change (Override Points):**
- CSS styling of every visible element (colors, fonts, shadows, borders, radii)
- Field visibility via `frm.toggle_display()`
- Custom buttons and actions via client scripts
- Form intros and messages via `frm.set_intro()`
- CSS class injection via client scripts

### 3.3 Risk of Replicating Vite Layout Engine in ERPNext

| Vite Feature | ERPNext Feasibility | Risk if Attempted |
|-------------|---------------------|-------------------|
| **Drag-and-drop field reordering** | ❌ Not practical | DOM manipulation breaks on every Frappe re-render. Every ERPNext update will break it. High maintenance debt. |
| **True dynamic columns per field** | ❌ Not practical | Would require overriding Frappe's layout engine. Fragile and upgrade-unsafe. |
| **Per-field fullWidth toggle** | ⚠️ Partially possible | Can toggle CSS classes, but breaks on form refresh. High maintenance. |
| **Panel resize responsiveness** | ❌ Not possible | Frappe doesn't have resizable panels. |

**Recommendation:** Do not attempt to replicate the Vite layout engine. Replicate the **visual output** using CSS, and replace the layout controls with **smart presets** that work within Frappe's constraints.

---

## 4. Vite UI Integration — Strategy

### 4.1 Strategy Name: "Vite Visual Skin + Frappe Smart Layout"

**Philosophy:** Do not fight Frappe's layout engine. Skin it to look like the Vite app, then add smart controls that work *within* Frappe's constraints.

### 4.2 What We Replicate (Visual)

| Element | Vite App Characteristic | ERPNext Override Method |
|---------|--------------------------|------------------------|
| **Page Background** | `#181A20` dark / `#F5F6FA` light | CSS variable `--vite-bg` on `.page-container` |
| **Form Container** | Card with `12px` radius, `0 4px 12px rgba(0,0,0,0.1)` shadow | `.form-page` styling |
| **Section Headers** | Uppercase, `14px`, `700` weight, blue left border `4px solid #2076FF` | `.section-head` override |
| **Section Cards** | `16px` padding, `8px` radius, `1px solid #393C43` border | `.form-section` override |
| **Input Fields** | `10px 14px` padding, `8px` radius, focus ring `0 0 0 3px rgba(32,118,255,0.12)` | `.form-control` override |
| **Labels** | Uppercase, `13px`, `600` weight, `#8D94A2` color | `.control-label` override |
| **Primary Buttons** | Gradient `135deg #2076FF → darker`, hover `translateY(-2px)` + shadow | `.btn-primary` override |
| **Secondary Buttons** | Surface bg, border, hover border-color change | `.btn-secondary` override |
| **Danger Buttons** | Gradient red, hover shadow | `.btn-danger` override |
| **Toolbar** | Sticky, surface bg, bottom border, shadow | `.page-head` override |
| **Status Pills** | Rounded full, color-coded background, `12px` font | `.indicator-pill` override |
| **Tabs** | Active tab has blue bottom border `2px` | `.form-tabs-list` override |
| **Grid/Child Tables** | Sticky header, alternating rows, hover highlight | `.grid-body`, `.grid-heading-row` override |
| **Modals** | `16px` radius, heavy shadow, surface bg | `.modal-content` override |
| **Alerts/Messages** | Color-coded background with border | `.form-message` override |
| **Sidebar** | Surface bg, right border | `.layout-side-section` override |
| **Animations** | Fade-slide `250ms`, button hover `200ms` | CSS `@keyframes` + transitions |
| **Typography** | Segoe UI family, specific size/weight hierarchy | CSS font-family + size overrides |

### 4.3 What We Do NOT Replicate (Layout Engine)

- ❌ **Drag-and-drop field reordering** — Too fragile. Frappe re-renders forms frequently; DOM manipulation will break.
- ❌ **True dynamic columns per field** — Frappe's layout engine generates `.form-column` divs based on DocType schema. Cannot change per-field without schema changes.
- ❌ **Per-field fullWidth toggle** — High maintenance. CSS class toggles break on refresh.
- ❌ **Panel resize responsiveness** — Frappe doesn't have resizable panels.

### 4.4 What We Replace With (Smart Controls)

| Vite Feature | ERPNext Replacement | How It Works | Stability |
|-------------|---------------------|-------------|-----------|
| **Drag-and-drop reordering** | **View Presets** | One-click switches between Manager/Engineer/Accountant/Compact views using `frm.toggle_display()` | 95% — uses native Frappe API |
| **Dynamic 1/2/3 columns** | **Column Density Toggle** | CSS class toggle (`vite-density-1-col`, `vite-density-2-col`, `vite-density-3-col`) overrides `.form-column` width | 90% — pure CSS, survives refresh |
| **Per-field visibility toggle** | **Field Visibility Panel** | Dialog with checkboxes for every field. Persists to user settings. | 95% — uses `toggle_display()` |
| **Section grouping** | **Card-style Sections** | Pure CSS — `.form-section` styled as cards with blue accent border | 100% — no JS required |

### 4.5 Implementation Files

| # | File | Purpose | Load Order |
|---|------|---------|------------|
| 1 | `vite_design_tokens.css` | CSS custom properties (colors, fonts, spacing, shadows, animations) | First |
| 2 | `vite_form_override.css` | Global form styling (sections, inputs, buttons, tabs, grid, modals, alerts, sidebar) | After tokens |
| 3 | `vite_list_override.css` | List view styling (headers, rows, filters, empty states) | After form |
| 4 | `vite_layout_enhancements.js` | Client script enhancements (view presets, column density, field visibility, status banners) | Per-DocType |

### 4.6 CSS Architecture

**Loading Order in `hooks.py` (CRITICAL):**
```python
app_include_css = [
    # Existing theme files (keep in current order)
    "/assets/construction/css/modern_theme.css",
    # ... other existing CSS ...

    # Vite Design System — MUST load LAST to win cascade
    "/assets/construction/css/vite_design_tokens.css",
    "/assets/construction/css/vite_form_override.css",
    "/assets/construction/css/vite_list_override.css",
]
```

**Selector Strategy:**
- Use `.vite-form .form-page` (added via client script `onload`) instead of `body[data-route^="Form/"]`
- This is more specific and less fragile across Frappe updates
- Dialog forms automatically inherit because the class is on the form wrapper

### 4.7 View Presets — Detailed Specification

**Purpose:** Replace drag-and-drop reordering with role-based form layouts.

**Presets for BOQ Header:**

| Preset | Visible Fields | Hidden Fields | Target User |
|--------|---------------|-------------|-------------|
| **Default (All Fields)** | All | None | Admin / Power User |
| **Manager View** | project, status, title, total_contract_value, total_estimated_value, total_budgeted_cost, locked_by, locked_date, version | boq_type, items, remarks | Project Manager |
| **Engineer View** | project, title, items, status, boq_type | total_contract_value, total_estimated_value, total_budgeted_cost, locked_by, locked_date | Site Engineer |
| **Accountant View** | project, title, total_contract_value, total_estimated_value, total_budgeted_cost, status | boq_type, version, items, remarks | Accountant |
| **Compact** | project, title, status | All others | Mobile / Quick View |

**Implementation:**
```javascript
// In boq_header.js
frappe.ui.form.on("BOQ Header", {
    refresh: function(frm) {
        frm.add_custom_button(__("View Presets"), function() {
            const d = new frappe.ui.Dialog({
                title: __("Form Layout Preset"),
                fields: [{
                    fieldtype: "Select",
                    label: __("Preset"),
                    fieldname: "preset",
                    options: [
                        "Default (All Fields)",
                        "Manager View (Summary Only)",
                        "Engineer View (Quantities + Stages)",
                        "Accountant View (Costs + Values)",
                        "Compact (Minimal)"
                    ],
                    default: getUserPreset("BOQ Header")
                }],
                primary_action: function(values) {
                    applyLayoutPreset(frm, values.preset);
                    saveUserPreset("BOQ Header", values.preset);
                    d.hide();
                }
            });
            d.show();
        }, __("Actions"));
    }
});
```

**Persistence:** Store in `tabUser` custom field or via `frappe.boot.user` settings. Do NOT use `localStorage` alone — it won't sync across devices.

### 4.8 Column Density Toggle — Detailed Specification

**Purpose:** Give users control over form width without breaking Frappe's layout engine.

**Modes:**
- **1-Column:** All fields stack vertically (mobile-friendly, focused)
- **2-Column:** Default Frappe behavior (balanced)
- **3-Column:** Dense layout for wide screens (maximum information density)

**CSS Implementation:**
```css
.vite-density-1-col .form-column {
    width: 100% !important;
    flex: 0 0 100% !important;
    max-width: 100% !important;
}

.vite-density-3-col .form-column {
    width: 33.333% !important;
    flex: 0 0 33.333% !important;
    max-width: 33.333% !important;
}

@media (max-width: 1200px) {
    .vite-density-3-col .form-column {
        width: 50% !important;
        flex: 0 0 50% !important;
        max-width: 50% !important;
    }
}

@media (max-width: 768px) {
    .vite-density-1-col .form-column,
    .vite-density-2-col .form-column,
    .vite-density-3-col .form-column {
        width: 100% !important;
        flex: 0 0 100% !important;
        max-width: 100% !important;
    }
}
```

**Persistence:** `localStorage` is acceptable here because it's a pure visual preference, not business logic.

### 4.9 Field Visibility Panel — Detailed Specification

**Purpose:** Let users hide fields they don't need, reducing cognitive load.

**UI:** Dialog with checkboxes for every non-section field.

**Persistence:** Server-side via custom API (not just localStorage).

**Safety:** Only affects `toggle_display()` — never removes fields from the DOM. Survives form refreshes.

### 4.10 Status Banner — Detailed Specification

**Purpose:** Replicate Vite app's status chips at the top of forms.

**Design:**
- Full-width banner inside `frm.set_intro()`
- Left: Icon (emoji or Lucide-style SVG)
- Center: Status label + value
- Right: Meta chips (version, locked by, date)
- Color-coded background based on status

**Statuses:**
| Status | Icon | Background | Text |
|--------|------|-----------|------|
| Draft | 📝 | Gray chip bg | Gray text |
| Pricing | 💰 | Blue chip bg | Blue text |
| Frozen | ❄️ | Orange chip bg | Orange text |
| Locked | 🔒 | Green chip bg | Green text |

### 4.11 Frappe v16 Compatibility Assessment

| Aspect | Frappe v16 Status | Our Approach | Risk |
|--------|-------------------|------------|------|
| CSS Custom Properties | Native support | Use extensively | Low |
| Tailwind Integration | v16 uses Tailwind | Our CSS overrides Tailwind where needed | Medium |
| Form HTML Structure | Stable since v14 | Selector-based overrides | Low |
| Dark Mode | `data-theme="dark"` | Our tokens switch with this attribute | Low |
| Dialog Forms | Separate render path | Scoped CSS handles both | Low |
| Mobile Responsive | Built-in | Our media queries enhance | Low |
| Existing Theme Files | 16 CSS + 20 JS | Load Vite CSS LAST | Medium |

---

## 5. Implementation Roadmap

### Phase 0: Environment Stabilization (Days 1–2)

**Goal:** Fix blockers so development can proceed safely.

| Task | Command | Verification |
|------|---------|------------|
| Enable developer_mode | `echo '{"developer_mode": 1}' > site_config.json` | Can customize DocTypes from UI |
| Enable scheduler | `bench --site v16.localhost enable-scheduler` | `bench doctor` shows active |
| Git hygiene | `git commit -m "pre-roadmap" && git checkout -b feature/vite-ui` | On `feature/vite-ui` branch |
| Run migration | `bench --site v16.localhost migrate` | No errors |
| Build assets | `bench build` | CSS/JS compile without errors |

**Deliverable:** Clean environment ready for UI development.

---

### Phase 1: Visual Foundation (Days 3–8)

**Goal:** Make ERPNext forms look like the Vite app.

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 3 | Create `vite_design_tokens.css` | Agent | CSS variables file with exact Vite values |
| 3 | Create `vite_form_override.css` | Agent | Form styling file (12 sections) |
| 4 | Create `vite_list_override.css` | Agent | List styling file |
| 4 | Update `hooks.py` (load order) | Agent | Vite CSS registered LAST |
| 5 | Test full-page forms (BOQ Header) | User | Screenshot comparison with Vite app |
| 5 | Test dialog forms (New BOQ) | User | Screenshot comparison |
| 6 | Test dark/light mode toggle | User | Both modes match Vite |
| 6 | Test mobile viewport | User | Responsive OK at 375px |
| 7 | Verify no regressions in existing theme | User | Dropdowns, sidebar, scope context intact |
| 8 | Performance test | User | Form load < 3s, no layout thrashing |

**Deliverable:** ERPNext forms visually match Vite app (≥ 80% match via CSS alone).

---

### Phase 2: Smart Layout Controls (Days 9–14)

**Goal:** Add user-controlled layout features within Frappe constraints.

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 9 | Implement View Presets for BOQ Header | Agent | 5 presets working |
| 9 | Implement View Presets for BOQ Item | Agent | 3 presets working |
| 10 | Implement Column Density toggle (1/2/3) | Agent | CSS + JS toggle |
| 10 | Implement Field Visibility panel | Agent | Dialog + server persistence |
| 11 | Add status banner to BOQ Header | Agent | Color-coded status chip |
| 11 | Add section icons to BOQ Item | Agent | Visual section headers |
| 12 | Test all controls on full page | User | Presets switch correctly |
| 12 | Test all controls on dialog | User | Dialog forms unaffected |
| 13 | Test on mobile + tablet | User | Responsive behavior OK |
| 13 | Regression test existing features | User | Scope context, dropdowns, sidebar intact |
| 14 | Performance test (1000 fields) | User | < 3s load time |
| 14 | Commit to branch, document | Agent | Clean commit, README updated |

**Deliverable:** Forms have smart layout controls (≥ 95% functional satisfaction compared to Vite app).

---

## 6. Risk Assessment & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Vite CSS conflicts with existing 16 CSS files** | High | High | Load Vite CSS LAST in hooks.py. Use scoped selectors (`.vite-form`). Test every existing feature after CSS load. |
| **Frappe v16 update breaks CSS selectors** | Medium | High | Use stable class names only (`.form-control`, `.btn`, `.section-head`). Avoid internal Frappe classes. |
| **Performance degradation with many CSS/JS files** | Medium | Medium | Audit total asset size. Minimize animations. Use CSS variables instead of repeated values. |
| **Frappe Cloud blocks custom CSS injection** | Low | Critical | Test on Frappe Cloud staging early (Phase 2, Day 12). If blocked, switch to Frappe's native theming API. |
| **Arabic RTL breaks with new CSS** | Medium | Medium | Test all forms in RTL mode. Use logical properties (`inline-start` instead of `left`). |
| **Existing scope context / dropdown overrides break** | Medium | High | Regression test scope context navbar, searchable dropdowns, and sidebar after every CSS/JS change. |
| **Mobile viewport unusable with 3-column density** | Low | Medium | Media query forces 1-column below 768px regardless of density setting. |
| **Client expects drag-and-drop despite recommendation** | Medium | Medium | Document why it was excluded (Section 3.3). Demonstrate that View Presets are faster and more reliable. |

---

## 7. Resource Requirements

### 7.1 Development Resources

| Resource | Requirement | Notes |
|----------|-------------|-------|
| **Local AI Agent** | Continuous | Primary implementer for code generation |
| **Human Reviewer** | 2 hours/day | Verify screenshots, test responsiveness, approve changes |
| **ERPNext Instance** | Local bench | Development and testing |
| **Vite App Reference** | Running instance or screenshots | Visual comparison during UI phase |

### 7.2 Time Estimate

| Phase | Duration | Effort (Agent) | Effort (User) |
|-------|----------|---------------|--------------|
| 0. Environment | 2 days | 4 hours | 2 hours |
| 1. Visual Foundation | 6 days | 24 hours | 12 hours |
| 2. Smart Layout | 6 days | 24 hours | 10 hours |
| **Total** | **14 days** | **52 hours** | **24 hours** |

### 7.3 Dependencies

| Dependency | Status | Action |
|------------|--------|--------|
| `developer_mode` | ⚠️ Disabled | Enable in Phase 0 |
| Scheduler | ⚠️ Disabled | Enable in Phase 0 |
| Git branch | ⚠️ Dirty | Commit + branch in Phase 0 |
| Vite app source | ✅ Available | `https://github.com/MohamedElrefae/accounting-system` |

---

## 8. Success Criteria

### 8.1 Visual Match Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| 1 | Form visual match ≥ 80% | Side-by-side screenshot comparison with Vite app |
| 2 | Dark mode matches Vite dark mode | Color picker verification (±5% tolerance) |
| 3 | Light mode matches Vite light mode | Color picker verification (±5% tolerance) |
| 4 | All existing theme features work | Dropdowns, sidebar, scope context, searchable selects |
| 5 | Mobile responsive | Forms usable on 375px width |
| 6 | Tablet responsive | Forms usable on 768px width |
| 7 | Load time < 3s | Chrome DevTools Network tab |

### 8.2 Smart Controls Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| 1 | View Presets switch in < 1s | Stopwatch test |
| 2 | All 5 BOQ Header presets work | Visual inspection |
| 3 | Preset preference persists across sessions | Log out → log in → verify |
| 4 | Column Density works on all forms | 1-col / 2-col / 3-col visual inspection |
| 5 | Column Density persists in localStorage | Refresh page → verify |
| 6 | Field Visibility panel shows all fields | Dialog opens, all fields listed |
| 7 | Hidden fields stay hidden after refresh | Refresh → verify |
| 8 | Status banner shows correct color/icon | Each BOQ status tested |
| 9 | No JavaScript errors in console | DevTools Console check |

### 8.3 Stability Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| 1 | No regressions in existing 16 CSS + 20 JS files | Full regression test |
| 2 | Scope context navbar intact | Visual + functional test |
| 3 | Searchable dropdowns work | Open dropdown → search → select |
| 4 | Sidebar navigation works | Collapse/expand, route changes |
| 5 | Form validation still works | Submit invalid form → verify errors |
| 6 | Print preview unaffected | Print BOQ → verify layout |

---

## 9. Approval Checklist

**For Software Consultant Review:**

### 9.1 Strategy Approval

- [ ] **Vite UI Strategy** approved: CSS-only visual skin + smart layout controls (skip drag-and-drop)
- [ ] **Unified Roadmap** approved: 3 phases, 14 days, UI-only scope
- [ ] **Risk Mitigation** approved: CSS load order, scoped selectors, no DOM manipulation

### 9.2 Technical Approval

- [ ] **Design Tokens** approved: Exact hex values, fonts, spacing from Vite app
- [ ] **CSS Selector Strategy** approved: `.vite-form` class instead of `body[data-route]`
- [ ] **View Presets** approved: Manager/Engineer/Accountant/Compact for BOQ Header
- [ ] **Column Density** approved: CSS class toggle (1/2/3 col) with responsive breakpoints
- [ ] **Field Visibility** approved: Dialog + server-side persistence
- [ ] **Status Banner** approved: Color-coded, icon-based, meta chips

### 9.3 Implementation Approval

- [ ] **Phase 0** approved: Environment stabilization commands
- [ ] **Phase 1** approved: CSS files + hooks.py registration
- [ ] **Phase 2** approved: Client scripts for presets, density, visibility, banners

### 9.4 Go/No-Go Decision

| Decision | Criteria |
|----------|----------|
| **GO** | All checkboxes above marked. Consultant signs off. |
| **CONDITIONAL GO** | Most checkboxes marked, with documented exceptions and mitigation plans. |
| **NO-GO** | Critical gaps identified. Return to planning. |

**Consultant Signature:** _________________  **Date:** _________________

---

## 10. Appendices

### Appendix A: Vite App Design Tokens (Exact Values)

```css
/* Core Brand */
--vite-primary: #2076FF;
--vite-primary-hover: #4A90FF;
--vite-success: #21C197;
--vite-warning: #FFC048;
--vite-error: #DE3F3F;

/* Dark Mode Surfaces */
--vite-bg: #181A20;
--vite-surface: #23272F;
--vite-border: #393C43;
--vite-field-bg: #23272F;
--vite-text: #EDEDED;
--vite-text-secondary: #8D94A2;
--vite-heading: #FAFAFA;

/* Light Mode Surfaces */
--vite-bg-light: #F5F6FA;
--vite-surface-light: #FFFFFF;
--vite-border-light: #E2E6ED;
--vite-field-bg-light: #F1F3F7;
--vite-text-light: #181C23;
--vite-text-secondary-light: #70778A;
--vite-heading-light: #14213D;

/* Shape */
--vite-radius-sm: 6px;
--vite-radius-md: 8px;
--vite-radius-lg: 12px;
--vite-radius-xl: 16px;

/* Shadows */
--vite-shadow-card: 0 2px 8px rgba(0,0,0,0.08);
--vite-shadow-form: 0 4px 12px rgba(0,0,0,0.1);
--vite-shadow-button-hover: 0 6px 16px color-mix(in oklab, black 15%, transparent);
--vite-shadow-modal: 0 20px 40px color-mix(in oklab, black 35%, transparent);

/* Typography */
--vite-font: "Segoe UI", "Tahoma", "Geneva", "Verdana", sans-serif;
--vite-font-mono: "Courier New", monospace;
```

### Appendix B: View Preset Configurations

**BOQ Header Presets:**

```javascript
const BOQ_HEADER_PRESETS = {
    "Default (All Fields)": {
        show: ["project", "boq_type", "status", "title", "version", 
               "total_contract_value", "total_estimated_value", "total_budgeted_cost",
               "locked_by", "locked_date", "items", "remarks"],
        hide: []
    },
    "Manager View (Summary Only)": {
        show: ["project", "status", "title", "total_contract_value", 
               "total_estimated_value", "total_budgeted_cost", "locked_by", "locked_date", "version"],
        hide: ["boq_type", "items", "remarks"]
    },
    "Engineer View (Quantities + Stages)": {
        show: ["project", "title", "items", "status", "boq_type"],
        hide: ["total_contract_value", "total_estimated_value", "total_budgeted_cost", 
               "locked_by", "locked_date", "version", "remarks"]
    },
    "Accountant View (Costs + Values)": {
        show: ["project", "title", "total_contract_value", "total_estimated_value", 
               "total_budgeted_cost", "status"],
        hide: ["boq_type", "version", "items", "remarks", "locked_by", "locked_date"]
    },
    "Compact (Minimal)": {
        show: ["project", "title", "status"],
        hide: ["boq_type", "version", "total_contract_value", "total_estimated_value",
               "total_budgeted_cost", "locked_by", "locked_date", "items", "remarks"]
    }
};
```

### Appendix C: File Inventory — New & Modified

**New Files:**
1. `construction/public/css/vite_design_tokens.css`
2. `construction/public/css/vite_form_override.css`
3. `construction/public/css/vite_list_override.css`

**Modified Files:**
4. `construction/construction/hooks.py` — Add CSS to `app_include_css` (load LAST)
5. `construction/construction/doctype/boq_header/boq_header.js` — Add view presets, column density, status banner
6. `construction/construction/doctype/boq_item/boq_item.js` — Add view presets, section icons

### Appendix D: Testing Matrix

| Test Case | Phase 1 | Phase 2 | Environment |
|-----------|---------|---------|-------------|
| Full-page form visual match | ✅ | — | Local v16 |
| Dialog form visual match | ✅ | — | Local v16 |
| Dark mode toggle | ✅ | — | Local v16 |
| Light mode toggle | ✅ | — | Local v16 |
| Mobile responsive (375px) | ✅ | — | Local v16 |
| Tablet responsive (768px) | ✅ | — | Local v16 |
| View Preset switch | — | ✅ | Local v16 |
| Column Density toggle | — | ✅ | Local v16 |
| Field Visibility panel | — | ✅ | Local v16 |
| Status banner colors | — | ✅ | Local v16 |
| Existing dropdowns work | ✅ | ✅ | Local v16 |
| Scope context navbar intact | ✅ | ✅ | Local v16 |
| Sidebar navigation works | ✅ | ✅ | Local v16 |
| Form validation works | ✅ | ✅ | Local v16 |
| Print preview unaffected | ✅ | ✅ | Local v16 |
| Arabic RTL forms | ✅ | ✅ | Local v16 |
| No console errors | ✅ | ✅ | Local v16 |

### Appendix E: CSS Load Order Diagram

```
ERPNext Page Load:
    ↓
Frappe Core CSS (Tailwind + SCSS)
    ↓
ERPNext Core CSS
    ↓
Construction App Existing CSS (modern_theme.css, etc.)
    ↓
[CRITICAL: Vite CSS MUST load here, LAST]
    ↓
vite_design_tokens.css  ← CSS variables
    ↓
vite_form_override.css  ← Form styling
    ↓
vite_list_override.css  ← List styling
    ↓
[Result: Vite selectors win the cascade]
```

### Appendix F: Responsive Breakpoints

| Breakpoint | Width | Column Behavior | Density Behavior |
|------------|-------|-----------------|------------------|
| Mobile | < 768px | 1 column forced | All densities → 1-col |
| Tablet | 768–1200px | 2 columns max | 3-col → 2-col |
| Desktop | > 1200px | Up to 3 columns | 1/2/3 col respected |

---

*End of Report*

**Report prepared by:** Kimi, Software Consultant  
**Review requested by:** [Client Name]  
**Next action:** Consultant review → Approval checklist completion → Phase 0 execution
