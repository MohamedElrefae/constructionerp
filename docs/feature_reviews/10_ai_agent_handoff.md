# AI Agent Handoff: Construction ERP Improve Now Program

Date: 2026-06-10

Workspace: `/home/mohamed/frappe-bench`

Primary app: `/home/mohamed/frappe-bench/apps/construction`

Target site used for verification: `v16.localhost`

## Handoff Purpose

The user needs another AI agent to continue implementation because current usage limits were reached. This document gives the next agent the operating context, progress state, evidence trail, known blockers, and exact next actions.

The canonical task tracker is:

`/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/09_improve_now_task_tracker.md`

The canonical evidence log is:

`/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/evidence_log.md`

The next agent must keep the tracker honest: do not mark a task `VER` unless implementation, verification, and an evidence artifact exist.

## User Goal

Improve the existing construction ERP features for Egypt/Gulf market fit and enterprise construction ERP ROI. The current approved program covers:

1. WBS stability and conversion rules.
2. BOQ Excel import/export.
3. Stage measurement/certification UI.
4. Scope context consistency across transaction DocTypes.
5. Arabic/English labels and print formats.
6. Variation Orders for post-lock BOQ changes.

The user specifically required a task tracker so work is verified end-to-end, not reported as complete based only on implementation messages.

## Strategic Product Policy Already Agreed

The WBS/BOQ execution-phase policy is recorded in:

`/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/EV-009-variation-order-architecture.md`

Core policy:

- Contract BOQ is immutable from Pricing/Frozen/Locked onward.
- Draft WBS can be resequenced only through a privileged controlled method.
- Post-lock scope changes must go through Variation Orders, not direct edits.
- VO new items use VO-prefixed WBS codes.
- Revised BOQ is a computed view: Contract BOQ plus approved VO deltas.
- Stage measurements must eventually validate against revised quantities once VO support exists.

WP6 Variation Orders is scheduled after WP3. It does not block WP1-WP5.

## Current Progress Summary

Program gate `G0` is verified.

Phase 0 tasks `T0.1` to `T0.6` are verified.

WP1 status:

- `WP1.1` to `WP1.10`: `VER`

WP2 status:

- `WP2.1` to `WP2.13`: `VER`

WP3 status:

- `WP3.1` to `WP3.8`: `VER`

WP4 status:

- `WP4.1` to `WP4.7`: `VER`

WP5 status:

- `WP5.1` to `WP5.9`: `VER`

WP6 status:

- `WP6.1` to `WP6.11`: `VER`
- `WP6.12`: `VER` (browser QA completed in `EV-056`)

Gates status:

- `G0`: `VER`
- `G1`: `VER`
- `G2`: `VER`
- `G3`: `VER`
- `G4`: `VER`
- `G5`: `VER`
- `G6`: `VER`

## Important Existing Dataset

On `v16.localhost`, evidence `EV-005` recorded:

- 4 BOQ Headers.
- 6 BOQ Structures.
- 2 BOQ Items.
- 2 BOQ Item Stages.
- Arabic BOQ data exists.
- Material Request `MAT-MR-2026-00003` has child row `f6bo5qbusm` linked to:
  - BOQ Header `BOQ-2026-0006`
  - BOQ Structure `rvetpphgb9`
  - BOQ Item `اسقف خرسانية`
  - Stage `BOQ-STG-00008`

This existing linked dataset is useful for delete-safety verification.

Additionally, WP6 browser QA created persistent test data on `v16.localhost`:

- BOQ Header `BOQ-2026-0274` (Locked) with VO test data.
- Variation Orders `BOQ-2026-0274-VO-001` (Quantity Change, Approved by Engineer), `BOQ-2026-0274-VO-002` (New Item, Approved by Client), `BOQ-2026-0274-VO-003` (Omission, Draft).
- Variation BOQ Structure `0tnpbchusm` (`Waterproofing membrane`, WBS `VO-002-01`).
- Variation BOQ Item `BOQI-BOQ-2026-0274-0276`.

## Files Changed or Added

Main implementation files changed:

- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.json`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item/boq_item.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.js`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_item_stage/boq_item_stage.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_structure/boq_structure.json`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/construction_settings/construction_settings.json`
- `/home/mohamed/frappe-bench/apps/construction/construction/install.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/patches.txt`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/boq_lifecycle.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/boq_operational.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/boq_export_service.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/boq_import_service.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/boq_transaction_validation.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/wbs_generator.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/templates/boq_header_print.html`
- `/home/mohamed/frappe-bench/apps/construction/construction/templates/boq_print_format.html`

New implementation files:

- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/boq_import_batch/`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/variation_order/`
- `/home/mohamed/frappe-bench/apps/construction/construction/construction/doctype/vo_line/`
- `/home/mohamed/frappe-bench/apps/construction/construction/patches/v6_8/`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/boq_scope_registry.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/boq_wbs_health.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/feature_flags.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/services/variation_orders.py`

New test/smoke files:

- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_wbs_health.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_wbs_generation.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_structure_delete_safety.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_structure_conversion.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_wbs_resequence.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_excel_parser.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_boq_helpers.py`
- `/home/mohamed/frappe-bench/apps/construction/construction/tests/test_variation_orders.py`

Planning and evidence docs:

- `/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/`
- `/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/`

## Implemented Technical Behavior

### Feature Flags

Added seven rollout flags to `Construction Settings`, all default `false`:

- `enable_boq_excel_import_preview`
- `enable_boq_excel_import_commit`
- `enable_boq_wbs_resequence`
- `enable_stage_measurement_ui`
- `enable_boq_scope_registry`
- `enable_bilingual_boq_print`
- `enable_variation_orders`

Runtime helper:

`construction.services.feature_flags.get_flags`

### WBS Health

Service:

`construction.services.boq_wbs_health.run_wbs_health_check`

Checks include duplicate WBS codes, blank WBS codes, missing/bad parents, broken nested set bounds, orphan BOQ Items, and item/header/group/leaf inconsistencies.

### Unique WBS Constraint

Unique index:

`unique_boq_header_wbs_code` on `tabBOQ Structure(boq_header, wbs_code)`

Helper:

`construction.services.boq_wbs_health.ensure_wbs_unique_constraint`

The helper is called from:

- migration patch `patches/v6_8/add_boq_structure_wbs_unique_constraint.py`
- `install.py`
- `BOQ Structure.on_doctype_update`

### Race-Safe WBS Generation

`BOQStructure.generate_wbs_code()` now:

- locks BOQ Header row for root-level generation.
- locks parent BOQ Structure for child generation.
- reads sibling WBS rows `FOR UPDATE`.
- assigns max last segment plus one.

Expected format:

- root: `01`
- child group: `01.01`
- child leaf: `01.001`

### Delete Safety

Leaf delete safety runs first in `BOQStructure.on_trash()` before linked BOQ Item deletion.

Important Frappe v16 nuance: Frappe delete flow calls `on_trash` before link validation; there is no earlier reliable controller `before_delete` hook in the path inspected. Evidence is in `EV-014`.

The old unsafe linked BOQ Item deletion using `force=True` was removed.

### Conversion Safety

`convert_group_to_ledger()`:

- Draft-only.
- no-op if already leaf.
- blocks if the group has children.
- creates linked BOQ Item if missing.

`convert_ledger_to_group()`:

- Draft-only.
- no-op if already group.
- runs delete-safety guard.
- blocks if stages or transaction references exist.

### Controlled Resequence

Public method:

`construction.services.wbs_generator.resequence_wbs(boq_header)`

Controls:

- requires `enable_boq_wbs_resequence = 1`.
- requires `System Manager`.
- requires BOQ Header status `Draft`.
- locks BOQ Header row.
- uses two-phase temporary WBS codes first, then final tree-order codes, to avoid unique-index collisions during swaps.
- writes before/after audit `Comment` on the BOQ Header.

Legacy `WBSGenerator.regenerate_all(boq_header)` now calls the safe internal resequence path without flag/role/status/audit controls, preserving migration use.

### Variation Orders

`Variation Order` and `VO Line` DocTypes are implemented with:

- Sequential VO numbering per BOQ Header (`VO-001`, `VO-002`, ...).
- Status workflow: `Draft` -> `Submitted` -> `Approved by Engineer` -> `Approved by Client`.
- Signed client PDF required before final client approval.
- Line types: `Quantity Change`, `New Item`, `Omission`.
- FIDIC-style 25 percent rate trigger enforced server-side.
- `get_revised_qty(boq_item)` and `get_revised_boq_rows(boq_header)` services.
- New approved VO items create `BOQ Structure` and `BOQ Item` with `is_variation_item = 1` and VO-prefixed WBS codes.
- Stage distribution validation uses revised quantities after approved VOs.
- Revised BOQ columns added to Excel and PDF export.

## Verification Evidence Created

Evidence files:

- `EV-007-wbs-health-v16-localhost.md`
- `EV-008-wbs-policy-input.md` - superseded
- `EV-009-variation-order-architecture.md`
- `EV-011-feature-flags.md`
- `EV-012-wbs-unique-constraint.md`
- `EV-013-wbs-race-safe-generation.md`
- `EV-014-boq-structure-delete-safety.md`
- `EV-015-boq-structure-conversion-safety.md`
- `EV-016-wbs-resequence.md`
- `EV-017-wp1-verification-bundle.md`
- `EV-019-wp1-browser-tree-qa.md`
- `EV-020` through `EV-053` for WP2-WP5
- `EV-054-current-feature-test-hardening.md`
- `EV-055-wp6-variation-order-foundation.md`
- `EV-056-wp6-browser-qa.md`
- `EV-057-program-closure.md`
- `EV-058-security-privacy-review.md`
- `EV-059-clean-site-migration.md`
- `EV-060-pre-commit-hygiene.md`
- `EV-061-frappe-cloud-deployment-plan.md`

Most recent final health check result:

```json
{
  "boq_header": null,
  "healthy": true,
  "summary": {
    "structures_checked": 6,
    "items_checked": 2,
    "issue_count": 0,
    "by_type": {},
    "by_severity": {}
  },
  "issues": []
}
```

## Useful Verification Commands

Run from `/home/mohamed/frappe-bench`.

Health:

```bash
bench --site v16.localhost execute construction.services.boq_wbs_health.run_wbs_health_check
```

Feature flags:

```bash
bench --site v16.localhost execute construction.services.feature_flags.get_flags
```

VO tests:

```bash
bench --site v16.localhost run-tests --app construction --module construction.tests.test_variation_orders --skip-before-tests --lightmode
```

Full construction lightmode:

```bash
bench --site v16.localhost run-tests --app construction --skip-before-tests --lightmode
```

Migration:

```bash
bench --site v16.localhost migrate
```

Standard Frappe tests currently expected to be blocked:

```bash
bench --site v16.localhost run-tests --app construction --module construction.tests.test_boq_wbs_resequence --skip-before-tests
```

Known blocker:

```text
Year start date or end date is overlapping with Fiscal Year 2025-2026.
```

## Current Blockers

### Standard Frappe Test Runner

The Frappe/ERPNext test runner is blocked by existing ERPNext bootstrap data, not by the construction tests themselves. Record as environment issue unless the user wants the test-site data cleaned/fixed.

### Gate Promotion Resolved

`G2`, `G3`, and `G6` promoted to `VER` on 2026-06-10 because all underlying WP tasks have recorded evidence and no technical blockers remain.

### Deferred Theme/v6.0 Migration Test Debt (`EV-054`)

Full construction lightmode run still shows failures from deferred Construction Theme and v6.0 migration test debt. Decide whether to:
- Keep deferred (current stance), or
- Promote to release-blocking and fix before any gate moves to `ACC`.

## Program Closure

The Improve Now program (WP1–WP6) is closed as of 2026-06-10 with `EV-057`.

All gates `G0` through `G6` are `VER`. All work package tasks are `VER`.

Theme/migration test debt is deferred to post-release **WP7** (see tracker).

## Manager Review Response

**2026-06-10:** Engineering Manager issued **APPROVED with 7 conditions**:

1. **Security/Privacy Review** (`EV-058`) — RESOLVED. Status-transition-only approval accepted as v1 risk; backlog ticket created for future `required_role` hook.
2. **Clean-Site Migration** (`EV-059`) — ACCEPTED WITH CAVEAT. Staging deploy is the de facto clean-site test; do not skip it.
3. **Pre-Commit Hygiene** (`EV-060`) — RESOLVED. Branch policy: `release/v6.8` from `develop`; tag `v6.8.0` on merge to `main`.
4. **Deploy Plan** (`EV-061`) — RESOLVED. Staged flag enablement approved; backup retention confirmation required; rollback drill required on staging (`EV-062`).

**Manager sign-off:**
- Code (WP1–WP6): ✅ APPROVED
- Commit to `develop`: ✅ APPROVED
- Merge to `release/v6.8`: ✅ APPROVED
- Tag `v6.8.0`: ✅ APPROVED
- Deploy to staging: ✅ APPROVED
- Deploy to production: ✅ APPROVED (after staging smoke green + 24h soak)
- Enable flags G1–G6: ✅ APPROVED (one gate per 24–48h)

## Post-Commit Status

- `release/v6.8` branch created from `develop`.
- Commit `ebc82f7` pushed: 144 files, 14087 insertions(+), 308 deletions(-).
- Local post-commit smoke on `v16.localhost` passed (6/6 tests, documented in `EV-062`).

## Recommended Next Agent Steps

1. Read `09_improve_now_task_tracker.md` and `evidence/evidence_log.md`.
2. Deploy `release/v6.8` to Frappe Cloud staging (`construction-staging.frappe.cloud`).
3. Run post-deploy smoke and rollback drill on staging; update `EV-062`.
4. Confirm backup retention with Cloud admin (Condition 4.1).
5. After manager confirms staging is green + 24h soak, proceed to production deploy.
6. Keep feature flags default `false`; enable one gate at a time (24–48h between each).
7. Only start **WP7** (Theme & Migration Test Hardening) if explicitly asked, or after the BOQ/VO release is complete.

## Cautions for Next Agent

- Do not revert unrelated files, especially ERPNext files modified by previous `bench migrate` side effects.
- Avoid parallel mutating Frappe smoke checks; one parallel run caused a cleanup deadlock. Run mutating smoke checks serially.
- Keep all disposable smoke helpers cleaning up after themselves.
- If a smoke run fails during cleanup, run the related cleanup helper before proceeding.
- Do not mark `VER` based only on code changes.
- Preserve the Egypt/Gulf enterprise construction ERP policy: Contract BOQ immutable; post-lock scope changes through VOs.

## Current Git Status in Construction App

At handoff time, `git -C apps/construction status --short` showed:

```text
 M construction/api/boq_api.py
 M construction/construction/doctype/boq_item/boq_item.json
 M construction/construction/doctype/boq_item/boq_item.py
 M construction/construction/doctype/boq_item_stage/boq_item_stage.js
 M construction/construction/doctype/boq_item_stage/boq_item_stage.py
 M construction/construction/doctype/boq_structure/boq_structure.json
 M construction/construction/doctype/boq_structure/boq_structure.py
 M construction/construction/doctype/construction_settings/construction_settings.json
 M construction/construction/doctype/user_scope_context/test_user_scope_context.py
 M construction/install.py
 M construction/locale/ar.po
 M construction/patches.txt
 M construction/services/boq_accounting.py
 M construction/services/boq_export_service.py
 M construction/services/boq_import_service.py
 M construction/services/boq_lifecycle.py
 M construction/services/boq_operational.py
 M construction/services/boq_transaction_validation.py
 M construction/services/wbs_generator.py
 M construction/templates/boq_header_print.html
 M construction/templates/boq_print_format.html
 M construction/tests/test_boq_integration.py
 M construction/tests/test_boq_item_stage.py
 M construction/tests/test_boq_properties.py
 M construction/tests/test_transaction_validation.py
?? construction/construction/doctype/boq_import_batch/
?? construction/construction/doctype/boq_item_stage/boq_item_stage_list.js
?? construction/construction/doctype/variation_order/
?? construction/construction/doctype/vo_line/
?? construction/patches/v6_8/
?? construction/services/boq_scope_registry.py
?? construction/services/boq_wbs_health.py
?? construction/services/feature_flags.py
?? construction/services/variation_orders.py
?? construction/tests/test_boq_excel_parser.py
?? construction/tests/test_boq_helpers.py
?? construction/tests/test_boq_structure_conversion.py
?? construction/tests/test_boq_structure_delete_safety.py
?? construction/tests/test_boq_wbs_generation.py
?? construction/tests/test_boq_wbs_health.py
?? construction/tests/test_boq_wbs_resequence.py
?? construction/tests/test_variation_orders.py
?? docs/feature_reviews/
```

## Final Instruction to Next Agent

Continue from the tracker, not from memory. The tracker and evidence log are the source of truth. The immediate job is to resolve the open gate-promotion and deferred-debt decisions with the user; no further implementation is required unless the user explicitly asks for it.
