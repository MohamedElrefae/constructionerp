# Engineering Verification Report — Construction ERP vs USER_GUIDE v1.3

**Author:** Head of Engineering (independent verification)
**Date:** 2026-08-22
**Method:** Live source code audit only — no reliance on prior reports or evidence files.
All claims traced to `file:line`. All test suites re-executed fresh during this review.

**Verdict: GO for UAT handoff, conditional on User Guide v1.4 corrections (Section D).**
The application is functionally sound; every core workflow verified end-to-end in code
and 158 automated tests pass fresh. The User Guide contains a small number of
inaccurate feature descriptions that must be corrected before it is handed to users.

---

## A. Fresh Test Execution (this review, site `localhost`)

| Suite | Claimed | Fresh Result |
|---|---|---|
| Scope Context integration (T-001…T-017) | 17/17 | **17/17 PASS ✅** |
| Transaction Validation | 13/13 | **13/13 PASS ✅** |
| BOQ Link Queries | 9/9 | **9/9 PASS ✅** |
| Quantity Revisions | 30/30 | **30/30 PASS ✅** |
| Variation Orders | 23/23 | **23/23 PASS ✅** |
| Cost Analysis Engine | 17/17 | **17/17 PASS ✅** |
| Cost Database API | 10/10 | **10/10 PASS ✅** |
| VFC Backend | 39/39 | **39/39 PASS ✅** |

Note: the standard `bench run-tests` preloader is currently broken by the
environment mix (frappe develop + erpnext 16.18.3 — fixture chain requests a
non-existent `Payment Gateway` DocType, and stale `_Test Company` / `Main - E`
cost-center data pollutes both sites). Suites were executed via plain `unittest`
inside bench context to bypass the preloader. Recommend repairing the fixture
chain and cleaning `_Test Company` records from both sites before CI use.

## B. Section-by-Section Traceability

### §1 Scope Context — CONFIRMED
- Settings fields exact (`construction_settings.json`: `enable_scope_context` L40,
  dimension checks L66–93, `scope_filter_exclusions` L94–100).
- Cascading top-bar selectors with lft/rgt descendant expansion (`scope_context_ui.js:47–60, 111–182`).
- Wildcard query injection with admin bypass, NestedSet expansion, dynamic exclusions
  (`hooks.py:251-253`, `overrides/scope_query.py:48–50, 78, 96–104`).
- Drift protection alert + Error Log audit entry confirmed (`boq_link_queries.py:77–86`,
  title "BOQ Scope Drift"); T-014 passes fresh.
- Nuance: Redis cache covers UI/boot hierarchy payload only (`api/scope_context_api.py`);
  permission-query path uses per-process memory caches.

### §2 BOQ Header — MOSTLY CONFIRMED (see D-1, D-2)
- Advance Status Draft→Pricing→Frozen→Locked with locked_by/locked_date population:
  CONFIRMED (`boq_header.js:436-466`, `api/boq_api.py:93-118`, `boq_header.py:67-85`).
- Actions → Variation Orders filtered list: CONFIRMED (`boq_header.js:509-516`) but
  visible at all statuses, not Locked-only (only "New Variation Order" is gated) — D-2.

### §3 BOQ Structure — CONFIRMED
- NestedSet WBS tree (`nsm_parent_field: parent_structure`), inline node rollups
  (`boq_structure_tree.js:62-104`, data `api/boq_api.py:25-43`), list columns present.
- Zero-value rollup segments are omitted from labels (guide example shows "0.00").

### §4 BOQ Item — CONFIRMED
- Leaf-only validation verbatim (`boq_item.py:53-59`); schema matches AGENTS.md facts;
  breadcrumb headline (`boq_item.js:98-109`, shows raw project ID);
  Quick Create Leaf Structure dialog with auto-select (`boq_item.js:130-175, 227-233`).

### §5–6 Cascade Blocker — CONFIRMED
- Red/orange engine real: accent `--ct-danger #dc2626`, blocked `--ct-warning #d97706`
  (`filter_fix.js:339,347`; dropdown click suppressed at `ct_link_control.js:620-622`).
- Stage 4-step cascade, clear-downstream, accent persists after save
  (`boq_item_stage.js:44-72, 199-204, 210-226`).
- VO accent-only + Locked-only header list (`variation_order.js:38-53`,
  `boq_link_queries.py:61-67`). Onboarding banner + localStorage key + progress
  indicators confirmed (banner additionally requires `frm.is_new()`).

### §7 Grid Blocker — CONFIRMED client-side (server note below)
- Exactly 8 transaction DocTypes wired (`boq_filters.js:4-13`, `hooks.py:230-245`);
  gate fields match guide table incl. `is_progress_billing` and Timesheet designations
  from boot (`boot.py:42-46`); registry mirrors gates (`boq_scope_registry.py:21-36`).
- Collapsed-row dimming opacity 0.65 + not-allowed cursor (`filter_fix.js:371-381`),
  flag limitation as documented in Appendix B.
- Parent project change clears/re-blocks all rows (`boq_filters.js:636-648`).
- Note: server-side `validate_document` enforces attribution consistency rules
  (stage→item→header chain, Locked/Frozen status, project match) but does NOT enforce
  the client gate fields; gates remain client-side UX guidance.

### §8 Variation Orders — ALL 8 CLAIMS CONFIRMED
- Flag + Locked gating server-side both API and controller (`boq_api.py:309-320`,
  `variation_order.py:66-67`); statuses/options exactly as documented
  (`variation_order.json:69`); PDF gate enforced server-side incl. `.pdf` suffix check
  (`variation_order.py:96-104`); P0-1 server-side diff guard after Engineer Approval
  (`variation_order.py:117-153`); auto-revision on final approval with delta +
  "Increase Above 25%" typing (`quantity_revisions.py:297-307`,
  `boq_quantity_revision.py:72-75`); justification thresholds (`vo_line.py:133-138`);
  omission zeroes qty and filters omitted items from dropdowns via
  `exclude_zero_revised` (`vo_line.py:51-52`, `boq_link_queries.py:266-267`);
  New Item creates Structure+Item with `is_variation_item=1`, original_qty=0, no
  item_code (`variation_order.py:183-217`); totals preserved
  (`boq_header.py:101`) with idempotency guards (`quantity_revisions.py:243-249`);
  rejection available at every pre-final stage.

### §9 Cost Estimation Engine — CONFIRMED (2 notes)
- Item custom fields seeded idempotently (`install.py:1147-1247`); PO/PI submit capture
  + cancel marking Cancelled-never-deleted (`resource_price_service.py:106-187`).
- Formulas exact: amount = qty×rate×(1+wastage%); unit direct ÷ Analysis Qty;
  profit compounds on (direct+overhead); suggested_sell_rate mirrors total
  (`boq_cost_analysis.py:58-77`).
- Single-Approved invariant with Supersede + restore-on-cancel and header refresh
  (`boq_cost_analysis.py:79-138`); non-template rejection message verbatim (:33).
- Rate priority Last PI → Last PO → Last Price History → Item Price, cancelled rows
  excluded (`resource_price_service.py:6-49`). Flags: fallback scans max 20 history rows
  before exclusion; `project` arg accepted but unused as filter.
- Permissions: RPH matrix matches guide; Site Engineer read-only on analyses.
  Note: analyses grant Construction Owner full and Project Manager create/submit —
  broader than the guide's "read/report/export" sentence (which describes RPH only).

### §10 Cost Database Import — CONFIRMED line-by-line (1 defect)
- Template generation blank/sample with 4 visible sheets + hidden `_Metadata`,
  Egyptian sample data, DataValidation dropdowns for resource_type/cost_stream/rate_source
  (`cost_database_service.py:545-657, 666-740, 743-777`).
- Arabic + alias headers map (`COLUMN_ALIASES :118-144`) incl. كود المورد، السعر، نوع المورد.
- Import endpoint: file+company required, dry_run/auto_submit/region/price_date options,
  create-permission gate (`cost_database_api.py:11-54`).
- Validation rules, dry-run creates nothing, Items upsert flagged as resources, RPH rows
  `source_doctype="Import"`, Draft templates updated in place, Submitted skipped with
  warning, created/updated/skipped payload separation — all verified (:146-325, 354-537).
- Bulk reprice draft-only with documented filter set using the rate-priority service
  (:16-110). **Defect D-3 below.**

### §11 VFC Layout Engine — PARTIAL (doc drift concentrated here)
- Form Config grid button on every form, floating draggable panel, runtime wrapper
  re-parenting, density 1/2/3 saved immediately to localStorage, Form Layout Profile
  server persistence with for_user overrides + role/default resolution, ~60s client
  cache, revert deletes personal profile server-side (non-admin allowed): CONFIRMED.
- Drag-and-drop between sections is REAL (bundled SortableJS).

### §12 Administration — CONFIRMED
- All five cache-bust versions in `hooks.py` match the guide table exactly.
- Settings reference table matches schema. Scope Drift Error Log verified.

## C. Test Environment Findings
1. `bench run-tests` fixture preloader broken (Payment Gateway DocType missing in
   erpnext v16 fixtures chain) — environment issue, suites pass when run directly.
2. Stale ERPNext `_Test Company` / `Main - E` cost-center pollution exists on BOTH
   `localhost` and `v16.localhost` sites — clean before CI/UAT data setup.

## D. Required Corrections Before Handoff

**D-1 (High — guide incorrect / feature gap):** Guide §2.1 & §6.2 claim a red project
accent + "Select Project first" pill on the BOQ Header form. In reality the Project
field is hidden on BOQ Header (`boq_header.json` hidden:1; `boq_header.js:51-55`
hides wrapper) and the accent helpers there are dead code (`setFieldAccent` defined
`boq_header.js:7-31`, never called). Decision needed: implement visible guidance or
rewrite §2.1/§6.2 to state project comes exclusively from Scope Context.

**D-2 (Medium — doc):** "Actions → Variation Orders" appears at every status; only
New VO creation is Locked-gated. Adjust §2.3 wording.

**D-3 (Medium — code defect):** `bulk_reprice_analyses` advertises a `resource_type`
filter, but `BOQ Cost Analysis Detail` has no `resource_type` field, so passing it
silently matches zero rows (`cost_database_service.py:63-64` + row match `:74`;
schema verified). Fix by deriving resource type from the linked Item's
`construction_resource_type`, or drop the parameter from §10.6 until supported.

**D-4 (Medium — doc):** VFC Presets §11.5: no user-defined "Save Current As" naming
exists — presets are a hardcoded registry covering only BOQ Header, BOQ Item,
BOQ Item Stage; storage is server-side user settings, not localStorage. Rewrite.

**D-5 (Low — doc):** §11.2 "Add Field to Section: select field from dropdown and Add"
does not exist — placement is drag-and-drop (+ arrow buttons) only.

**D-6 (Low — doc/UX):** Regular users get the full editable Sections UI; enforcement
happens only at save and the PermissionError is not surfaced to the user
(`vite_layout_controls.js:793-797, 815-832`). Either render read-only for non-admins
or surface the save error.

**D-7 (Low — doc):** §11.6 "form refreshes immediately" after Revert is inaccurate —
no document reload occurs; residual VFC-hidden native shells persist visually until
the next real refresh.

**D-8 (Low — schema/doc):** Resource Price History `resource_type` is optional in
JSON (no reqd:1) though §9.2 lists it under required manual-entry fields. Align one way.

**D-9 (Info — roles):** Roles referenced in permissions (Construction Owner,
Project Manager, Site Engineer) are never seeded by app code, and ERPNext's standard
role spells "Projects Manager". Ensure roles exist in production DB before go-live.

**D-10 (Cosmetic):** Title not mandatory on BOQ Header; BOQ Type has a third option
"Variation"; breadcrumb shows raw project ID rather than display name; tree rollup
labels omit zero segments; stage banner requires a NEW form (not merely first visit).
Update guide examples accordingly.

## E. GM Handoff Summary
- Core enterprise workflows (Scope Context, WBS/BOQ, cascade UX, VO lifecycle with
  server-side P0-1 and PDF gates, cost estimation math with supersede invariant,
  Excel import with idempotency, layout personalization with server persistence)
  are implemented, guarded server-side where it matters, and proven by 158 fresh tests.
- No blocker-level defects found. One genuine code defect (D-3), one feature-vs-doc
  conflict requiring an owner decision (D-1), and documentation corrections (D-4..D-10).
- Recommended sequence: apply guide v1.4 corrections + D-3 fix + role seeding (D-9),
  then release the guide to UAT users.

## F. Remediation Record (2026-08-22)

| ID | Resolution | Evidence |
|---|---|---|
| D-1 | RESOLVED (doc-corrected). Project on BOQ Header confirmed hidden-by-design with server-side Scope Context enforcement; guide §2.1/§6.2/§13 rewritten; dead accent helpers removed from `boq_header.js` (node --check OK) | USER_GUIDE v1.4 |
| D-2 | RESOLVED — §2.1/§2.3 wording clarified (VO list button any status; creation Locked-gated) | USER_GUIDE v1.4 |
| D-3 | FIXED in code — `resource_type` filter now resolves via Item `construction_resource_type` (`cost_database_service.py`); regression test added; Cost Analysis Engine suite **18/18 PASS** fresh | test_bulk_reprice_resource_type_filter |
| D-4..D-7 | RESOLVED — §11 rewritten (drag-only placement, built-in presets, server-side storage, revert refresh caveat, System Manager save gate); Appendix B constraints #6 added | USER_GUIDE v1.4 |
| D-8 | RESOLVED — §9.2 required-field list corrected (resource_type optional/recommended) | USER_GUIDE v1.4 |
| D-9 | RESOLVED — `seed_construction_roles()` added to `install.py` and wired into `after_install` + `after_migrate` (`hooks.py`). Seeds **Construction Owner**, **Project Manager**, **Site Engineer** idempotently. Decision: the app's "Project Manager" role follows the DocType JSONs (source of truth) and is deliberately distinct from ERPNext's standard "Projects Manager"; documented in code. Verified live: deletion + re-seed recreates the role; permission suite 18/18 PASS |
| Lint | RESOLVED — `in_standard_filter` reset to 0 on BOQ Cost Analysis.company, Resource Price History.project/company; lint now reports **PASS (0 violations, 19 DocTypes)** |
| D-10 | RESOLVED in checklist wording; cosmetic items noted | USER_GUIDE v1.4 |

Post-fix regression runs: Cost Database API 10/10 ✅, Quantity Revisions 30/30 ✅,
Cost Analysis Engine 18/18 ✅. Scope metadata lint: PASS (0 violations).
