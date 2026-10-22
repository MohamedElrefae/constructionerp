# Letter to the Team: Form Config Review and Next Layout Engine Direction

Date: 2026-05-28

Team,

I reviewed the current Construction app implementation, the form configuration walkthrough under `/home/mohamed/frappe-bench/forms config `, and the proposed "Advanced Form Layout Engine" report. This note summarizes what is already working, what the report gets right, what needs correction, and how I recommend we move forward.

## Current Working State

The app already has a functional Vite-style Form Config layer.

The current implementation is loaded globally from `construction/hooks.py` through:

- `vite_extensions.css`
- `vite_form_override.css`
- `vite_list_override.css`
- `vite_layout_controls.js`

The active controller is:

- `construction/public/js/vite_layout_controls.js`

It currently provides:

- A global `Form Config` button on Frappe forms.
- A slide-in panel with three tabs: `Layout`, `Fields`, and `Presets`.
- Global 1, 2, and 3 column density using CSS classes.
- Field visibility toggles using `frappe.model.user_settings`.
- Hard-coded presets for `BOQ Header`, `BOQ Item`, and `BOQ Item Stage`.
- Automatic attachment through `frappe.ui.form.on("*")`.

The related walkthrough and task tracker correctly describe this as completed Phase 1 and Phase 2 work.

## Important Findings From the Repo

### 1. BOQ Header Is Flat

`BOQ Header` currently has no explicit `Section Break` fields in the DocType JSON. Its fields are rendered as one flat form sequence:

- `project`
- `project_name`
- `boq_type`
- `status`
- `version`
- `title`
- financial totals
- lock fields

This supports the report's point that BOQ Header needs dynamic section grouping if we do not want to modify the DocType JSON.

### 2. BOQ Item Already Has Native Sections

`BOQ Item` is not flat. It already has native sections:

- `Identity and Linkage`
- `Quantity and Pricing`
- `Cost Estimation`
- several future placeholder sections

The business request is therefore not just "add sections" for BOQ Item. The real need is to control the order and grouping of existing fields in a workflow-first way, for example:

1. BOQ Header / Structure
2. Item Type / Cost Item
3. Quantities
4. Pricing
5. Owner References

This is still a valid requirement, but the report should state clearly that BOQ Item already has sections and needs workflow reorganization.

### 3. Current Presets Contain Stale Fieldnames

The current `BOQ Item` preset uses fieldnames such as:

- `wbs_code`
- `title`
- `type`
- `stage`

These do not match the current `BOQ Item` DocType, which uses fieldnames such as:

- `structure`
- `boq_header`
- `item_type`
- `cost_item`
- `quantity`
- `unit`
- `factor`
- `contract_unit_price`
- `line_total`

The current `BOQ Item Stage` preset also references:

- `completion_percentage`
- `remarks`

The current DocType uses:

- `percent_complete`
- `description`

Before building the next layout engine, we should fix or validate the existing preset registry. Otherwise, the team may think a preset is controlling a field when the field does not exist.

### 4. The Current Form Config Is UI-Level, Not a Layout Engine

The current feature changes presentation and visibility. It does not change the source order of fields, assign fields to named sections, or store role-based layout profiles in the database.

Current persistence is split:

- Column density: `localStorage`, browser-specific.
- Hidden fields and selected preset: `frappe.model.user_settings`, user-specific and server-backed.

That is enough for the current panel, but not enough for role-based shared layouts.

### 5. Attachment Is Duplicated for Some Forms

`vite_layout_controls.js` already attaches globally through `frappe.ui.form.on("*")`.

`BOQ Header` and `BOQ Item` also call `frappe.require("/assets/construction/js/vite_layout_controls.js")` and manually attach `ViteFormConfig`.

The `_vfc_attached` guard reduces the risk of duplicate UI, but before expanding this system we should choose one attachment path. The cleanest path is global attachment from `hooks.py`, with DocType-specific behavior handled by registry/config.

## Consultant Recommendation

The proposed Form Layout Engine is the right direction, but it should be framed as a controlled overlay on top of Frappe's native renderer.

We should not replace Frappe controls or attempt to render fields ourselves. Frappe should render the form normally first. Then our engine can safely reorganize existing field wrappers using `frm.fields_dict[fieldname].wrapper`.

This keeps native behavior intact:

- permissions
- mandatory rules
- read-only rules
- depends-on behavior
- link queries
- field events
- validation
- child table controls

## Recommended Architecture Adjustment

Rename the proposed DocType from `Form Layout Config` to `Form Layout Profile`.

Suggested fields:

| Field | Purpose |
|---|---|
| `reference_doctype` | Target DocType |
| `profile_name` | User-facing layout profile name |
| `enabled` | Allow disabling without deletion |
| `is_default` | Candidate default layout |
| `for_role` | Optional role targeting |
| `for_user` | Optional personal override |
| `priority` | Deterministic conflict resolution |
| `layout_version` | Future schema migration |
| `sections_json` | Stored layout definition |
| `is_system` | Protect seeded layouts |

The layout JSON should include a top-level version and an unassigned-field policy:

```json
{
  "version": 1,
  "unassigned_policy": "append",
  "sections": [
    {
      "id": "sec_identity",
      "label": "Identity",
      "column_count": 2,
      "sort_order": 1,
      "visible": true,
      "collapsible": false,
      "collapsed_by_default": false,
      "fields": [
        {
          "fieldname": "boq_header",
          "col": 1,
          "sort_order": 1,
          "visible": true
        }
      ]
    }
  ]
}
```

## Required Validation Before Save

Any backend API must validate the layout before saving:

- Reject duplicate field assignments.
- Warn or ignore fieldnames that no longer exist.
- Auto-append new DocType fields that are not assigned.
- Do not allow required fields to be hidden by normal users.
- Preserve Frappe-controlled hidden/read-only behavior.
- Allow only 1, 2, or 3 columns for the first version.

## Recommended Delivery Plan

### Step 0: Stabilize Current Form Config

Before starting the layout engine:

- Fix stale preset fieldnames for `BOQ Item`.
- Fix stale preset fieldnames for `BOQ Item Stage`.
- Remove duplicate manual attach calls from DocType controllers if global attach is kept.
- Add a guard that ignores unknown preset fields and logs them once.

### Step 1: Technical MVP

Build the database-backed layout engine for two DocTypes only:

- `BOQ Header`
- `BOQ Item`

Scope:

- New `Form Layout Profile` DocType.
- Python API for load/save/validate/list.
- Runtime JS layout engine that moves existing Frappe field wrappers.
- Manual JSON editing in Frappe form.
- No drag-and-drop UI yet.

Success criteria:

- BOQ Header can render as named sections without changing its DocType JSON.
- BOQ Item can render in workflow order.
- Missing/new fields do not break the form.
- Existing link queries, field events, mandatory validation, and save behavior continue working.

### Step 2: Sections Tab

After the MVP proves stable:

- Add a fourth `Sections` tab to the Form Config panel.
- Allow section reorder.
- Allow field reorder.
- Allow moving fields between sections.
- Allow per-section column count.
- Add up/down controls for mobile instead of relying only on drag-and-drop.

### Step 3: Seeded Role Profiles

Ship default profiles only after the engine is stable:

- BOQ Header - Default
- BOQ Header - Manager
- BOQ Header - Engineer
- BOQ Item - Default
- BOQ Item - Engineer Workflow
- BOQ Item - Accountant View
- BOQ Item Stage - Default

## Revised Estimate

The original 13 working day estimate is possible but optimistic.

Recommended estimate:

| Phase | Scope | Estimate |
|---|---|---:|
| Stabilize current Form Config | Fix presets, attach path, unknown-field guard | 1 day |
| Backend profile DocType and API | DocType, permissions, validation | 2-3 days |
| Runtime layout engine MVP | Re-parent wrappers, fallback, cache | 3-4 days |
| Hardening | dependencies, hidden fields, child tables, mobile, RTL | 2-3 days |
| Sections editor UI | Drag/drop or ordered controls | 4-5 days |
| Seed profiles and documentation | Default profiles and user guide | 1-2 days |

Production-ready range: 13-18 working days.

Technical MVP range: 6-8 working days after current preset cleanup.

## Decision Needed

My recommendation is to approve the concept, but split approval into two gates:

1. Approve the technical MVP for `BOQ Header` and `BOQ Item`.
2. Approve the visual drag-and-drop editor only after the MVP proves that Frappe field wrappers can be reorganized safely in our app.

The current Form Config work is a good foundation. The next step should be disciplined: clean the existing registry, introduce a database-backed profile model, validate layouts server-side, and preserve Frappe's native form controls while changing only their visual grouping and order.

