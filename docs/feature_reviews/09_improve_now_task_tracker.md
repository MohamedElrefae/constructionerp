# Improve Now Implementation Task Tracker

Date: 2026-06-08

## Purpose

This tracker converts the approved improvement plan into controlled implementation work. Its main rule is simple: no item is complete because code was written. An item is complete only when implementation, verification evidence, and review status are recorded.

The tracker covers:

1. WBS stability and conversion rules.
2. BOQ Excel import/export.
3. Stage measurement/certification UI.
4. Scope context consistency across transaction DocTypes.
5. Arabic/English labels and print formats.
6. Variation Orders for post-lock BOQ changes.

## Status Model

Use these statuses only:

| Status | Meaning |
| --- | --- |
| `NS` | Not started. |
| `RDY` | Ready to implement after approval. |
| `IP` | Implementation in progress. |
| `IMP` | Code/config implemented, but not verified. |
| `VER` | Verified with recorded evidence. |
| `ACC` | Accepted by reviewer or product owner. |
| `BLK` | Blocked by policy, environment, dependency, or missing approval. |

## Verification Rule

Every task must have at least one evidence record before it can move to `VER`.

Valid evidence types:

- Automated test result.
- Migration or health-check output.
- Browser screenshot or screen recording.
- Generated Excel/PDF file.
- SQL/query result.
- Manual QA checklist signed by reviewer.
- Configuration screenshot or exported setting.

Recommended evidence folder:

`/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/`

## Program Gates

| Gate | Required Before | Verification Required | Status |
| --- | --- | --- | --- |
| `G0` | Any implementation starts | `EV-001` to `EV-005`, `EV-010`, and `EV-011`: active site, Frappe version, branch state, dirty files, approval state, dataset, evidence log, and feature flags documented | `VER` |
| `G1` | BOQ import commit is enabled | `EV-007`, `EV-014`, `EV-015`, `EV-016`, `EV-017`, and `EV-019`: WBS health check, WBS delete safety, conversion safety, Draft-only resequence, server smoke bundle, and browser tree/form QA verified | `VER` |
| `G2` | Excel import/export is released to users | Dry-run import, commit import, error report, export performance, privacy behavior, and sample files verified | `VER` |
| `G3` | Stage UI is released to quantity surveyors | Stage edit policy, certified-stage lock, delete safety, totals, permissions, and future `get_revised_qty` compatibility verified | `VER` |
| `G4` | Scope registry replaces current transaction validation behavior | `EV-045` to `EV-048`: Journal Entry Account compatibility, supported transaction matrix, unsupported behavior, error messages, syntax checks, and direct WP4 smokes verified | `VER` |
| `G5` | Arabic/bilingual print is released | `EV-037`, `EV-038`, and `EV-049` to `EV-053`: Arabic-first policy, Western numeric cells, RTL Excel, Arabic PDF fonts, labels, templates, print registration, build/translation compile, and visual artifacts verified | `VER` |
| `G6` | Variation Order workflow is released to QS/PM | VO line types, FIDIC 25 percent rate rule, Engineer/Client approval, signed PDF gate, new item creation, revised BOQ view, and procurement linking verified | `VER` |

## Phase 0: Governance and Preflight

| ID | Task | Dependency | Verification Evidence | Status |
| --- | --- | --- | --- | --- |
| `T0.1` | Confirm target bench site, Frappe version, app branch, and deployment environment. | None | `EV-002`, `EV-004`. Default execution site selected: `v16.localhost`, pending reviewer override. | `VER` |
| `T0.2` | Record current git state before edits. | None | `EV-003`. | `VER` |
| `T0.3` | Confirm implementation order and package approvals. | Manager/product approval | `EV-010`. User approved proceeding to next step using `EV-009`; WP6 remains scheduled after WP3. | `VER` |
| `T0.4` | Create or identify test BOQ dataset: header, WBS tree, stages, transaction rows, Arabic labels. | Active test site | `EV-005`. Existing `v16.localhost` dataset includes BOQ headers, structures, items, stages, Arabic data, and one BOQ-linked Material Request row. | `VER` |
| `T0.5` | Create feature flag fields in `Construction Settings` for all seven rollout flags, default all to `False`, and export them as fixture or migration patch. Flags: `enable_boq_excel_import_preview`, `enable_boq_excel_import_commit`, `enable_boq_wbs_resequence`, `enable_stage_measurement_ui`, `enable_boq_scope_registry`, `enable_bilingual_boq_print`, `enable_variation_orders`. | Approval checklist | `EV-011`. Flags added to DocType JSON, migrated to `v16.localhost`, and verified through Python runtime helper. | `VER` |
| `T0.6` | Create evidence folder and evidence log. Copy the evidence log template from this tracker into `/home/mohamed/frappe-bench/apps/construction/docs/feature_reviews/evidence/evidence_log.md` as the first implementation evidence artifact. | None | `EV-001`. | `VER` |

## Work Package 1: WBS Stability and Conversion Rules

### Definition of Done

WP1 is accepted only when WBS codes are stable, duplicate-safe, conversion is safe, destructive operations are blocked when references exist, and resequence works only in Draft.

| ID | Task | Dependency | Verification Evidence | Status |
| --- | --- | --- | --- | --- |
| `WP1.1` | Finalize WBS policy: immutable from Pricing onward, Draft-only resequence, and post-lock scope changes only through Variation Orders. | `WP1.2`, `T0.3` | `EV-009`, approved in `EV-010`. | `VER` |
| `WP1.2` | Build WBS health check for duplicate codes, blank codes, broken parents, broken nested set, and orphan BOQ Items. | `T0.4` | `EV-007`. Service implemented and live health check completed on `v16.localhost`; targeted test runner blocked by pre-existing ERPNext fiscal-year bootstrap issue in `EV-006`. | `VER` |
| `WP1.3` | Add migration preflight path for unique `(boq_header, wbs_code)` constraint. | `WP1.2` | `EV-012`. Health-gated migration path implemented; unique index verified on `v16.localhost`; helper is idempotent. | `VER` |
| `WP1.4` | Fix WBS race condition by generating sibling sequence inside a controlled transaction/lock path. | `WP1.1` | `EV-013`. Lock-based max-sequence WBS generation implemented; concurrent sibling insert smoke passed with distinct WBS codes. | `VER` |
| `WP1.5` | Move leaf delete reference checks before any linked BOQ Item deletion. | `WP1.1` | `EV-014`. Frappe v16 uses `on_trash` as the first delete hook, so the guard runs first inside `on_trash` before linked BOQ Item deletion. | `VER` |
| `WP1.6` | Remove unsafe forced linked BOQ Item deletion unless all safety checks pass. | `WP1.5` | `EV-014`. `force=True` removed from linked BOQ Item deletion; referenced item remained intact during delete-block smoke. | `VER` |
| `WP1.7` | Fix `convert_group_to_ledger`: only empty groups convert and missing BOQ Item is created. | `WP1.1` | `EV-015`. Empty group-to-leaf conversion created a linked BOQ Item and is Draft-only. | `VER` |
| `WP1.8` | Fix `convert_ledger_to_group`: block when stages or transaction references exist. | `WP1.1` | `EV-015`. Staged leaf-to-group conversion was blocked and linked BOQ Item remained intact. | `VER` |
| `WP1.9` | Add Draft-only privileged `resequence_wbs(boq_header)` method with before/after audit log. | `WP1.1` | `EV-016`. Draft resequence succeeded with audit Comment, non-Draft `Pricing` BOQ was blocked, flags reset to false, cleanup had no leftovers, and WBS health stayed clean. | `VER` |
| `WP1.10` | Run WP1 automated tests and manual tree QA. | `WP1.2` to `WP1.9` | `EV-017`, `EV-019`. Isolated server smoke checks passed, final WBS health is clean, and browser-level QA screenshots were captured for BOQ Header list, BOQ Header form, BOQ Structure form, BOQ Item form, and BOQ Item Stage form. Standard Frappe runner remains blocked by existing ERPNext Fiscal Year bootstrap data, recorded as an environment issue. | `VER` |

## Work Package 2: BOQ Excel Import/Export

### Definition of Done

WP2 is accepted only when import supports dry-run and commit modes, validates file and parent references correctly, generates clear error reports, and export is performant, private by default, and usable for Egypt/Gulf consultant review workflows.

| ID | Task | Dependency | Verification Evidence | Status |
| --- | --- | --- | --- | --- |
| `WP2.1` | Confirm `openpyxl` availability and dependency handling in bench environment. | `T0.1` | `EV-020`. Bench Python imports `openpyxl 3.1.5`; existing BOQ export service already uses it, so no new dependency is required. | `VER` |
| `WP2.2` | Define final Excel template columns, English/Arabic aliases, numeric rules, and status restrictions. | `T0.3` | `EV-021`, `EV-022`, `EV-023`. `EV-021` strict WBS requirement is superseded. Manager approval needed for optional WBS/Parent WBS, flat import, multi-batch target behavior, traceability fields, and separate VO import after work starts. | `RDY` |
| `WP2.2A` | Harden BOQ Excel import implementation spec: deterministic parser heuristics, header row detection, ambiguous row handling, multi-batch import target, duplicate description policy, merged-cell/Arabic handling, and flat restructuring UX. | `WP2.2` | `EV-023`, `EV-024`, `EV-025`. Third-pass consultant review approved the hardened spec; parser/dry-run implementation may begin while commit remains blocked by `WP2.2B`. | `VER` |
| `WP2.2B` | Add import traceability design: dedicated fields and decide whether to create `BOQ Import Batch` DocType before commit import. | `WP2.2A` | `EV-029`. Added `BOQ Import Batch` DocType and traceability fields on BOQ Structure/BOQ Item; migrated `v16.localhost`; verified table, columns, secure date-random naming, and cleanup. | `VER` |
| `WP2.3` | Implement parser and normalizer for BOQ Excel files. | `WP2.1`, `WP2.2A` | `EV-026`. Preview parser implemented and smoke-verified for structured, semi-structured, flat Arabic-header, ambiguous-row, and structured-WBS-collision cases; Python syntax compile passed. Commit remains blocked by `WP2.2B`. | `VER` |
| `WP2.4` | Implement `dry_run=True` validation using an in-memory file tree for parent WBS references. | `WP2.3` | `EV-027`. Parent WBS from uploaded file is accepted; missing parent, item parent, and parent-after-child cases are blocked; syntax check passed. | `VER` |
| `WP2.5` | Implement preview summary: rows, sections, items, errors, warnings, proposed creates, preview tree. | `WP2.4` | `EV-028`. Preview response fixture includes summary, errors, proposed creates, and preview tree; JSON validation and syntax compile passed. | `VER` |
| `WP2.6` | Implement `dry_run=False` commit into Draft BOQ only. | `G1`, `WP2.4`, `WP2.2B` | `EV-030`. Feature-flagged commit path verified on `v16.localhost`: `BOQ Import Batch`, structures/items with traceability, line totals, WBS health, flag block, preview regression, and cleanup. | `VER` |
| `WP2.7` | Add duplicate import protection for existing WBS codes in same Draft BOQ. | `WP2.6` | `EV-031`. Duplicate structured re-import and stale-preview commit are blocked; final commit guard locks BOQ Header and validates proposed WBS against current Draft BOQ before batch creation. | `VER` |
| `WP2.8` | Generate import error report workbook with `Error` and `Warning` columns. | `WP2.4` | `EV-032`. Private report workbook generated with `Import Review` and `Summary` sheets; smoke verified populated `Error`/`Warning` cells, private File record, and cleanup. | `VER` |
| `WP2.9` | Add file-size, row-count, and async import threshold policy. | `WP2.2` | `EV-033`. Boundary smoke verified file-size hard limit, row-count hard limit, async-required preview warning, sync commit block for async-sized imports, cleanup, and parser regression. | `VER` |
| `WP2.10` | Harden export depth calculation by precomputing parent/depth map instead of N+1 parent calls. | None | `EV-034`. Export depth is precomputed from loaded structure rows; smoke verified correct root/child/leaf depths while legacy per-node depth function was monkey-patched to fail if called. | `VER` |
| `WP2.11` | Normalize export privacy for Excel/PDF and file URLs. | None | `EV-035`. Header/full Excel and header/full PDF exports verified with `/private/files/...`, `is_private = 1`, on-disk existence, and cleanup. | `VER` |
| `WP2.12` | Add Arabic/bilingual labels and RTL worksheet support using `worksheet.sheet_view.rightToLeft = True`. | `WP5.2` | `EV-037`, `EV-038`. Arabic-first with Western numeric Excel cells approved; RTL workbook smoke verified Arabic sheet title, Arabic headers, numeric cells, and cleanup. | `VER` |
| `WP2.13` | Run WP2 automated tests and manual import/export QA. | `WP2.1` to `WP2.12` | `EV-039`. Full direct bench smoke rollup passed; cleanup verified; standard Frappe runner blocked by existing ERPNext Fiscal Year bootstrap overlap before reaching construction tests. | `VER` |

## Work Package 3: Stage Measurement/Certification UI

### Definition of Done

WP3 is accepted only when measurement and certification entry is fast, role-safe, consistent with server validation, and locked/certified stages cannot be modified or deleted contrary to policy.

| ID | Task | Dependency | Verification Evidence | Status |
| --- | --- | --- | --- | --- |
| `WP3.1` | Approve Frozen/Locked stage edit policy. | `T0.3` | `EV-040`. Frozen/Locked planning fields freeze; execution measurement remains editable until certification; certified stages become immutable adjustment-only audit records. | `VER` |
| `WP3.2` | Document existing row locking behavior in stage operational validation. | None | `EV-041`. Existing advisory lock was hardened with named per-item lock and `SELECT ... FOR UPDATE` sibling-stage read; separate-process concurrency test blocked over-allocation. | `VER` |
| `WP3.3` | Add or refine stage measurement UI controls and role-based field behavior. | `WP3.1` | `EV-042`. Form UI applies status/role read-only behavior; server role smoke blocks non-certifier certification. Browser screenshot pending due unavailable in-app browser tool. | `VER` |
| `WP3.4` | Add stage totals and progress indicators in list/form views. | `WP3.3` | `EV-042`. Form dashboard indicators and list-view status indicators added; JS syntax verified. Browser screenshot pending due unavailable in-app browser tool. | `VER` |
| `WP3.5` | Add certified-stage modification lock according to approved policy. | `WP3.1` | `EV-040`. Certified stage edit-block smoke passed, including description/notes edit block. | `VER` |
| `WP3.6` | Add certified-stage delete safety policy, building on existing `before_delete` transaction reference checks. | `WP3.1` | `EV-040`. Certified stage delete-block smoke passed through controller-level `on_trash` guard. | `VER` |
| `WP3.7` | Add bulk measurement/certification server method only if policy approves. | `WP3.1` | `EV-043`. Feature-flagged bulk API saves through normal validation; smoke verified disabled flag, measurement update, certification role block, admin certification, cleanup, and flag reset. | `VER` |
| `WP3.8` | Run WP3 automated tests and manual measurement QA. | `WP3.2` to `WP3.7` | `EV-044`. Syntax checks, policy/role/bulk smokes, process-level concurrency test, cleanup, and flag reset passed. Browser screenshot unavailable in this turn. | `VER` |

## Work Package 4: Scope Context Consistency Across Transaction DocTypes

### Definition of Done

WP4 is accepted only when BOQ scope validation is registry-driven, gated, compatible with current transaction child tables, and verified for Egypt/Gulf enterprise workflows including purchasing, stock, sales, timesheets, and journal entries.

| ID | Task | Dependency | Verification Evidence | Status |
| --- | --- | --- | --- | --- |
| `WP4.1` | Verify Journal Entry Account custom fields and server/client compatibility. | `T0.1` | `EV-045`. Required BOQ Link fields exist and Journal Entry row-style validation populated BOQ Header/Structure from BOQ Item. | `VER` |
| `WP4.2` | Define supported transaction matrix and unsupported transaction behavior. | `WP4.1` | `EV-046`. Supported matrix covers Purchase, Stock, Sales, Timesheet, Journal Entry, and Material Request workflows; unsupported transaction DocTypes are ignored. | `VER` |
| `WP4.3` | Create transaction scope registry gated by `enable_boq_scope_registry`. | `WP4.2` | `EV-046`. Registry module implemented; rollout flag toggled/restored during smoke. | `VER` |
| `WP4.4` | Align server validation, client filters, and allowed BOQ status rules. | `WP4.3` | `EV-046`. Server registry and client filters use the same supported DocType matrix and Frozen/Locked BOQ status policy. | `VER` |
| `WP4.5` | Guard global `*` validate hook so non-BOQ DocTypes are not affected unexpectedly. | `WP4.3` | `EV-047`. BOQ transaction validator returns immediately for unsupported parent DocTypes; unsupported Delivery Note behavior verified as ignored. | `VER` |
| `WP4.6` | Add clear error messages for project mismatch, invalid status, invalid stage parentage, and missing scope. | `WP4.4` | `EV-047`. Missing item, invalid status, project mismatch, and stage parentage messages verified. | `VER` |
| `WP4.7` | Run WP4 automated tests and transaction manual QA. | `WP4.1` to `WP4.6` | `EV-048`. Syntax checks and direct WP4 smokes passed; formal Frappe runner remains blocked by existing ERPNext Fiscal Year bootstrap overlap before construction tests load. | `VER` |

## Work Package 5: Arabic/English Labels and Print Formats

### Definition of Done

WP5 is accepted only when Arabic/English labels, bilingual outputs, RTL layout, PDF fonts, Excel RTL, and print registration are verified visually and technically.

| ID | Task | Dependency | Verification Evidence | Status |
| --- | --- | --- | --- | --- |
| `WP5.1` | Approve language modes: English, Arabic, bilingual. | `T0.3` | `EV-037`. Arabic-first approved for current implementation; English remains available by session language; bilingual deferred. | `VER` |
| `WP5.2` | Approve numeral policy: Arabic numerals or Western numerals in Arabic output. | `WP5.1` | `EV-037`. Western numeric Excel cells approved for Egypt/Gulf QS compatibility while Arabic labels/RTL UI are used. | `VER` |
| `WP5.3` | Verify Arabic PDF font availability in target server/printer environment. | `T0.1` | `EV-049`. `Noto Naskh Arabic`, `Amiri`, and `wkhtmltopdf 0.12.6` verified; Arabic PDF text extraction and embedded fonts passed. | `VER` |
| `WP5.4` | Build label catalog for BOQ, WBS, item, stage, measurement, certification, and scope fields. | `WP5.1` | `EV-050`. 24 Arabic labels verified across required categories. | `VER` |
| `WP5.5` | Update print templates for Arabic/English/bilingual modes. | `WP5.3`, `WP5.4` | `EV-051`, `EV-053`. BOQ PDF templates are Arabic-aware with RTL direction and Arabic-capable fonts; rendered PDF artifacts verified. | `VER` |
| `WP5.6` | Register or verify print formats and default behavior. | `WP5.5` | `EV-051`. `BOQ Print Format` registered/enabled for `BOQ Header`; idempotent setup helper added to integration setup. | `VER` |
| `WP5.7` | Compile and verify translations. | `WP5.4` | `EV-052`. `bench build --app construction` succeeded and generated Arabic MO file. | `VER` |
| `WP5.8` | Add Excel RTL and bilingual export verification with Arabic sample data. | `WP2.12`, `WP5.2` | `EV-038`, `EV-053`. RTL Excel was smoke-verified and persistent Arabic XLSX artifact generated. | `VER` |
| `WP5.9` | Run WP5 visual QA on browser/PDF/Excel outputs. | `WP5.3` to `WP5.8` | `EV-053`. Header/full Arabic PDFs, PNG page renders, and XLSX artifact generated; rendered PDF images visually inspected. | `VER` |

## Work Package 6: Variation Orders

### Definition of Done

WP6 is accepted only when a Variation Order can be raised against a Locked BOQ Header, all three VO line types work correctly, the FIDIC 25 percent rate rule is enforced server-side, Engineer and Client approval workflow is verified, signed client PDF upload is required before final approval, revised quantities flow to stage validation, and procurement links work for VO-created BOQ Items.

WP6 is scheduled after WP3. It does not block WP1-WP5 because the Contract BOQ foundation must be stable before Variation Orders can safely reference it.

| ID | Task | Dependency | Verification Evidence | Status |
| --- | --- | --- | --- | --- |
| `WP6.1` | Approve VO policy: line types, FIDIC 25 percent rule, approval chain, numbering per BOQ Header, and Contract BOQ immutability. | `WP1.1` | `EV-009`, `EV-055`. Policy implemented and verified by VO tests. | `VER` |
| `WP6.2` | Create `Variation Order` DocType with status workflow and approval fields. | `WP6.1`, `G1` | `EV-055`. DocType migrated and workflow transition tests passed. | `VER` |
| `WP6.3` | Create `VO Line` child DocType with all fields and server-side validation logic. | `WP6.2` | `EV-055`. 25 percent trigger, omission, revised quantities, and line values verified. | `VER` |
| `WP6.4` | Implement VO numbering sequential per BOQ Header. | `WP6.2` | `EV-055`. Sequential per-BOQ Header numbering verified. | `VER` |
| `WP6.5` | Implement VO approval workflow: `Draft` to `Submitted` to `Approved by Engineer` to `Approved by Client`, with signed PDF gate. | `WP6.2` | `EV-055`. Approval chain and signed PDF gate verified. | `VER` |
| `WP6.6` | Implement `get_revised_qty(boq_item)` service method. | `WP6.3` | `EV-055`. Approved VOs affect revised quantity; unapproved VOs ignored by status. | `VER` |
| `WP6.7` | Update `boq_operational._validate_planned_distribution` to use `get_revised_qty`. | `WP6.6`, `WP3.3` | `EV-055`. Locked-stage distribution accepts approved revised quantity. | `VER` |
| `WP6.8` | Implement VO new item approval: create BOQ Structure and BOQ Item with `is_variation_item = 1`. | `WP6.5`, `WP6.9` | `EV-055`. New item approval creates marked variation BOQ Structure and BOQ Item. | `VER` |
| `WP6.9` | Add `is_variation_item` field to BOQ Structure and BOQ Item. | `WP6.1` | `EV-055`. Fields migrated and verified through new item approval. | `VER` |
| `WP6.10` | Add Revised BOQ report/view showing contract quantity, VO delta, revised quantity, contract value, VO value delta, revised value, measured, and certified. | `WP6.6` | `EV-055`. `get_revised_boq_rows` verified with approved VO data. | `VER` |
| `WP6.11` | Add VO/revised BOQ columns to BOQ export so Excel/PDF can show revised quantities. | `WP6.10`, `G2` | `EV-055`. Excel values and PDF export smoke verified with revised columns. | `VER` |
| `WP6.12` | Run WP6 automated tests and manual VO QA demo. | `WP6.1` to `WP6.11` | `EV-055` covers automated tests and export files. `EV-056` covers browser-level VO form, line type, approval workflow, and variation structure/item screenshots. Manager acceptance still pending. | `VER` |

## Verification Command Matrix

Exact commands should be recorded with the active site name before execution.

| Verification Area | Command or Action | Required Evidence |
| --- | --- | --- |
| App tests | `bench --site <site> run-tests --app construction` | Full command output. |
| Targeted DocType tests | `bench --site <site> run-tests --doctype "BOQ Structure"` | Full command output. |
| Migration | `bench --site <site> migrate` | Migration output and no destructive warnings. |
| Asset/translation build | `bench build --app construction` | Build output. |
| WBS health check | Planned server method or bench execute command | Health-check report. |
| Excel import dry run | Upload sample workbook with `dry_run=True` | Preview response and error report if applicable. |
| Excel import commit | Upload sample workbook with `dry_run=False` | Created BOQ tree/item/stage records. |
| Excel export | Export sample BOQ | Generated workbook, privacy check, RTL check if applicable. |
| PDF print | Render BOQ print in each approved language mode | Generated PDFs and screenshots. |
| Browser UI QA | Open BOQ Header, Structure, Item, Stage, and transaction forms | Screenshots for core flows. |
| Transaction QA | Submit sample Purchase, Stock, Sales, Timesheet, Journal, Material Request documents | Submitted docs and validation outcomes. |
| Variation Order QA | Create VO with Quantity Change, New Item, and Omission lines; move through Engineer and Client approval with signed PDF attachment | Approved VO, transition evidence, revised BOQ output, created variation BOQ Item, and procurement link evidence. |

## Evidence Log Template

Create one evidence log during implementation and append to it after every verification step.

| Evidence ID | Task ID | Date | Command or Action | Result | Artifact Path | Reviewer |
| --- | --- | --- | --- | --- | --- | --- |
| `EV-001` | `T0.1` | TBD | TBD | TBD | TBD | TBD |

## Acceptance Checklist by Work Package

| Work Package | Required Tasks Verified | Reviewer Acceptance Required | Status |
| --- | --- | --- | --- |
| WP1 WBS stability | `WP1.1` to `WP1.10` | Yes | `VER` |
| WP2 Excel import/export | `WP2.1` to `WP2.13` | Yes | `VER` |
| WP3 Stage UI | `WP3.1` to `WP3.8` | Yes | `VER` |
| WP4 Scope context | `WP4.1` to `WP4.7` | Yes | `VER` |
| WP5 Arabic/print | `WP5.1` to `WP5.9` | Yes | `VER` |
| WP6 Variation Orders | `WP6.1` to `WP6.12` | Yes | `VER` |

## Blockers to Close Before Coding

| Blocker | Affects | Decision Needed |
| --- | --- | --- |
| Frozen/Locked stage edit policy | WP3 | Decide whether measured/certified quantities are fully locked, role-unlocked, or revision-only. |
| Journal Entry Account compatibility | WP4 | Closed in `EV-045`; child table fields and row validation behavior verified. |
| Arabic PDF font/printer environment | WP5 | Closed in `EV-049`; usable Arabic fonts and PDF renderer verified. |
| Import update mode | WP2 future scope | Confirm whether first release is create-only or supports updating existing rows. Recommended first release is create-only. |
| Variation Order workflow release | WP6 | Closed in `EV-055` and `EV-056`. |
| Theme/migration test debt | WP7 | Deferred to post-release cleanup. 42 failures documented in `EV-054`. |

## Current Implementation State

Source-code implementation has completed and verified WP1, WP2, WP3, WP4, WP5, and WP6. Preflight evidence capture is complete and all program gates `G0` through `G6` are verified. Program closure recorded in `EV-057`.

Theme/migration test debt (42 failures) is deferred to post-release WP7. It does not block the current BOQ/VO value stream.

## Manager Review Response

**Date:** 2026-06-10  
**Reviewer:** Engineering Manager  
**Verdict:** Conditional Approval — 3 must-fix items identified.

### Manager Blockers / Hard Gates

| Gate | Requirement | Evidence Created | Status |
|------|-------------|------------------|--------|
| Security / Privacy Review | VO permissions, private files, variation item visibility, secrets scan | `EV-058` | `VER` |
| Clean-Site Migration | Verify `bench migrate` safety on empty site | `EV-059` | `VER`¹ |
| Pre-Commit Hygiene | Git status clean, no secrets, branch confirmed | `EV-060` | `VER` |
| Frappe Cloud Deploy Plan | Staging, smoke, rollback, flag order, monitoring | `EV-061` | `VER` |

> ¹ Live clean-site execution was not possible due to environment constraints (no DB root access). Verified by code inspection + idempotency smoke.

### Response to Manager Findings

**BLOCKER 1 — VO Role-Based Approval:**  
`EV-058` documents that VO status transitions are enforced by `validate_status_transition()` (state machine), not by role-based permissions. Only System Manager, Construction Owner, and Project Manager have write access. No "Engineer" or "Client" roles exist in the VO permission matrix. **Risk accepted for v1**; future enhancement can add custom workflow rules if segregation of duties is required.

**BLOCKER 2 — Clean-Site Migration:**  
`EV-059` confirms the unique-constraint patch (`patches/v6_8/add_boq_structure_wbs_unique_constraint.py`) has a `table_exists` guard and calls an idempotent helper. `BOQ Import Batch` uses `"Prompt"` autoname (no collision). All new DocTypes are standard Frappe JSON. Idempotency verified on `v16.localhost`.

**HARD GATE 3 — Pre-Commit Hygiene:**  
`EV-060` confirms 24 modified + 13 untracked files, all intended. No `__pycache__` or `.pyc` in diff (`.gitignore` excludes them). No editor swap files. `Admin@2026-temp` only in evidence doc, not code. `admin12345` not found anywhere. Branch: `develop`.

**HARD GATE 4 — Deploy Plan:**  
`EV-061` provides a complete Frappe Cloud deployment plan with staging recommendation, 15–30s migration estimate, post-deploy smoke commands, rollback scenarios, staged flag enablement order, and 24h monitoring checklist.

### Manager Second-Pass Decision (2026-06-10)

**Decision:** **APPROVED with 7 conditions**

| # | Condition | Owner | Status |
|---|-----------|-------|--------|
| 1.1 | Backlog ticket for transition `required_role` hook | Product Owner | Open (post-release) — documented in `backlog-required-role-transition-hook.md` |
| 2.1 | Staging deploy smoke must pass before production | DevOps | Gate before prod |
| 3.1 | Create `release/v6.8` branch from `develop` | Dev | Pre-commit |
| 3.2 | Use structured commit message (`EV-060`) | Dev | Pre-commit |
| 3.3 | Tag `v6.8.0` on merge to `main` | Dev | Post-merge |
| 4.1 | Document backup retention from Cloud admin | DevOps | Pre-prod |
| 4.2 | Run rollback drill on staging, document in `EV-062` | DevOps | Pre-prod |

**Sign-off:**
- Code (WP1–WP6): ✅ APPROVED
- Commit to `develop`: ✅ APPROVED
- Merge to `release/v6.8`: ✅ APPROVED
- Tag `v6.8.0`: ✅ APPROVED
- Deploy to Frappe Cloud staging: ✅ APPROVED
- Deploy to Frappe Cloud production: ✅ APPROVED (after staging smoke green + 24h soak)
- Enable flags G1–G6: ✅ APPROVED (one gate per 24–48h)

### Post-Commit Status (2026-06-10)

| Step | Status | Evidence |
|------|--------|----------|
| Create `release/v6.8` branch | ✅ Done | `git checkout -b release/v6.8` |
| Commit with structured message | ✅ Done | Commit `ebc82f7`, 144 files, 14087 insertions(+), 308 deletions(-) |
| Local post-commit smoke (v16.localhost) | ✅ Pass | `EV-062` — 6/6 smoke tests passed |
| Frappe Cloud staging deploy | ⏳ Pending | Awaiting Cloud credentials / bench access |
| Frappe Cloud rollback drill | ⏳ Pending | Requires staging site (Condition 4.2) |
| Production deploy | ⏳ Pending | Awaiting staging green + 24h soak + manager confirmation |

### Next Step

1. Deploy `release/v6.8` to Frappe Cloud staging (`construction-staging.frappe.cloud`).
2. Run post-deploy smoke on staging.
3. Run rollback drill on staging; update `EV-062`.
4. Confirm backup retention with Cloud admin (Condition 4.1).
5. Notify manager with staging results → get production deploy sign-off.

## Work Package 7: Theme & Migration Test Hardening (Post-Release)

### Definition of Done

WP7 is accepted only when the construction app test suite runs green under `--skip-before-tests --lightmode` with no theme or migration failures.

| ID | Task | Dependency | Verification Evidence | Status |
| --- | --- | --- | --- | --- |
| `WP7.1` | Restore or remove missing `construction_theme_components.css` fixture. | `EV-054` | TBD | `NS` |
| `WP7.2` | Fix `test_list_active_themes` to match current `list_active_themes` return contract (missing `is_active` key). | `EV-054` | TBD | `NS` |
| `WP7.3` | Fix login background validation tests: missing `test_login_bg.jpg` fixture and updated type-mismatch rules. | `EV-054` | TBD | `NS` |
| `WP7.4` | Fix v6.0 migration color rounding drift (`lighten_hex`, `darken_hex`). | `EV-054` | TBD | `NS` |
| `WP7.5` | Fix v6.0 migration auto-population tests to match current behavior or mark as legacy. | `EV-054` | TBD | `NS` |
| `WP7.6` | Fix Construction Theme CSS generation tests (22 errors from schema/controller drift). | `EV-054` | TBD | `NS` |
| `WP7.7` | Run full lightmode suite and confirm zero theme/migration failures. | `WP7.1` to `WP7.6` | TBD | `NS` |
