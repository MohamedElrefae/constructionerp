# Improve Now Execution Plan

Date: 2026-06-08

## Purpose

This is an approval plan before implementation. It covers the five high-market-value improvements selected for Egypt/Gulf construction ERP fit:

1. BOQ Excel import/export.
2. WBS stability and conversion rules.
3. Stage measurement/certification UI.
4. Scope context consistency across transaction DocTypes.
5. Arabic/English labels and print formats.

## Recommendation: One Program, Five Independent Work Packages

My recommendation is to run this as one coordinated program with five independent work packages.

Reason:

- These features share BOQ data, WBS structure, stage quantities, transaction attribution, and print/export outputs.
- Each work package can be reviewed and approved separately.
- Implementation should follow a strict order so later features do not depend on unstable foundations.

Recommended order:

1. WBS stability and conversion rules.
2. BOQ Excel import/export.
3. Stage measurement/certification UI.
4. Scope context consistency across transaction DocTypes.
5. Arabic/English labels and print formats.

## Approval Checklist

Before implementation, approve these policy decisions:

- WBS policy: immutable after creation, or Draft-only resequence.
- Leaf-to-group conversion policy when linked BOQ Item has stages or transactions.
- Import mode: create-only first, or update existing rows too.
- Stage lock policy in Frozen/Locked BOQs.
- Scope supported transaction matrix.
- Print language modes: English, Arabic, bilingual.
- Arabic numerals or Western numerals in Arabic print.

## Manager Review Amendments Integrated

The manager review verdict is `Approve with amendments`. These amendments are now part of this plan:

- Add a WBS race-condition fix, not only a uniqueness check.
- Add a concrete WBS migration/health-check path before any unique constraint.
- Block forced BOQ Item deletion when stages or transaction rows exist.
- Treat BOQ import as the main build effort and export as hardening.
- Fix export depth calculation performance before large BOQ rollout.
- Add import file-size/row-count limits and async import threshold.
- Document stage row locking behavior and require a Frozen/Locked edit policy decision.
- Add stage delete safety for referenced stages.
- Formalize transaction registry and verify Journal Entry Account compatibility.
- Add Arabic PDF font prerequisite, RTL Excel API, print-format registration, and Arabic numeral policy.
- Add performance tests and pre-migration health checks to the integrated test plan.

## Feature Gating and Compatibility

Implementation should include rollout controls so partially completed features are not exposed too early.

Recommended gates:

- `enable_boq_excel_import_preview`
- `enable_boq_excel_import_commit`
- `enable_boq_wbs_resequence`
- `enable_stage_measurement_ui`
- `enable_boq_scope_registry`
- `enable_bilingual_boq_print`

Compatibility checks:

- Confirm behavior on the active Frappe version before using `NestedSet`, `rebuild_tree`, `get_pdf`, and child-table custom fields.
- Add a compatibility note in each implementation PR if behavior differs between Frappe v15 and v16.
- The global `*` validate hook for scope enforcement must not be changed in a way that breaks non-BOQ DocTypes; gate any behavioral change behind `enable_boq_scope_registry`.

---

# Work Package 1: WBS Stability and Conversion Rules

## Current State

`BOQ Structure` is a Frappe `NestedSet` with generated `wbs_code`. Leaf nodes automatically create `BOQ Item`. Deleting leaf nodes deletes linked items.

Current risks:

- WBS codes are count-based and may collide under concurrent inserts.
- Group-to-leaf conversion does not create a BOQ Item.
- Leaf-to-group conversion does not safely handle an existing BOQ Item.
- Deleting a leaf can force-delete a BOQ Item even if transactions reference it.
- There is no clear policy for immutable WBS codes versus resequenced display codes.

## Target Outcome

WBS should be stable, auditable, and safe enough for BOQ import, export, measurements, certificates, and transaction attribution.

## Functional Plan

1. Define WBS policy.
   - Recommendation: allow resequence only while BOQ Header is `Draft`.
   - Freeze WBS codes from `Pricing` onward.

2. Add WBS uniqueness guard.
   - `wbs_code` must be unique inside one `boq_header`.
   - Empty `wbs_code` is not allowed after insert.
   - Add unique constraint on `BOQ Structure(boq_header, wbs_code)` if existing data can pass migration checks.

3. Fix WBS generation race condition.
   - Do not rely only on a unique constraint.
   - Generate sibling sequence inside a transaction.
   - Lock the sibling set or parent row before calculating the next sequence.
   - If a collision still occurs, fail clearly and retry from UI/API rather than silently overwriting.

4. Add pre-migration WBS health check.
   - Detect duplicate `(boq_header, wbs_code)`.
   - Detect missing/blank WBS codes.
   - Detect broken parent references.
   - Detect orphan BOQ Items without a valid Structure.
   - Add the unique constraint only after the health check passes or a repair patch is approved.

5. Make group/leaf conversion safe.
   - `convert_group_to_ledger`: allow only if no children, then create linked BOQ Item if missing.
   - `convert_ledger_to_group`: allow only if linked BOQ Item has no stages and no transaction references.
   - Block conversion when BOQ Header is `Frozen` or `Locked`.

6. Protect linked BOQ Items.
   - Before deleting a leaf, check stages and transaction row references.
   - Block deletion if references exist.
   - Move reference checks before destructive delete behavior.
   - Avoid `force=True` deletion unless the safety checks prove no references exist.
   - Place the reference check in `before_delete`, not inside `on_trash`, so a thrown exception does not leave the nested-set tree in a broken state.

7. Add Draft-only resequence tool.
   - Server method: `resequence_wbs(boq_header)`.
   - Recompute by tree order.
   - Log before/after WBS mapping.
   - Treat resequence as a privileged operation that writes read-only `wbs_code` fields intentionally.
   - Do not run resequence through ordinary user save flow.

## Tests

Server tests:

- Create root/group/leaf tree and verify WBS code format.
- Duplicate WBS under same BOQ is blocked.
- Same WBS under different BOQs is allowed if policy permits.
- Group with children cannot convert to leaf.
- Empty group converts to leaf and creates BOQ Item.
- Leaf with stages cannot convert to group.
- Leaf with transaction row cannot convert to group.
- Leaf with transaction row cannot be deleted.
- Delete leaf with active Purchase Order row is blocked.
- Resequence succeeds in Draft.
- Resequence is blocked in Pricing/Frozen/Locked.
- Concurrent leaf inserts under the same parent produce distinct WBS codes or one clear retryable failure.

Migration tests:

- Existing duplicate WBS records are detected before unique constraint.
- Migration does not delete existing BOQ Structure records.
- Broken `lft/rgt` and orphaned BOQ Items are reported by health check.

Manual QA:

- Add, delete, and convert nodes in tree view.
- Verify BOQ Item creation/removal behavior.
- Verify WBS sorting in list and export.

## Deliverables

- Updated BOQ Structure controller.
- Optional migration/patch for uniqueness.
- Resequence server method.
- Tests for conversion, delete safety, and resequence.

---

# Work Package 2: BOQ Excel Import/Export

## Current State

Export is implemented for Excel and PDF and already includes column config merging, tree data assembly, Excel generation, PDF generation, and grand total calculation. Import service currently returns a placeholder response and does not parse/create BOQ data.

Therefore, this work package is asymmetrical:

- Import is a real build track.
- Export is a hardening, performance, privacy, and bilingual-formatting track.

## Target Outcome

Excel import/export should support real consultant BOQ workflows common in Egypt/Gulf: Excel template import, validation preview, error report, full BOQ creation, and reliable export for review.

## Functional Plan

1. Define import modes.
   - Use one service method with `dry_run=True/False`.
   - `dry_run=True`: parse file, validate rows, return preview/errors, do not write.
   - `dry_run=False`: validate and create records.
   - Recommendation: first release supports create/import into Draft BOQ only.

2. Define template columns.
   - WBS Code
   - Parent WBS
   - Title
   - Type: Section / Item
   - Unit
   - Quantity
   - Unit Price
   - Factor
   - Notes
   - Owner Page
   - Owner Ref No
   - Owner File Ref

3. Parse Excel safely using `openpyxl`.
   - Required columns exist.
   - WBS Code required and unique in file.
   - Parent WBS exists in file or already exists in BOQ.
   - Section rows cannot have price/quantity.
   - Item rows require unit and positive quantity.
   - Factor defaults to 1.
   - Numeric fields reject invalid text.
   - Type values allow English/Arabic aliases, including `Section`, `Item`, `قسم`, and `بند`.
   - Confirm `openpyxl` availability in the bench environment and declare/verify dependency handling.
   - During `dry_run=True`, validate parent WBS references against an in-memory set/tree of rows in the file, not only against the database, because no records have been written yet.

4. Add preview result.
   - Total rows.
   - Section count.
   - Item count.
   - Error count.
   - Warning count.
   - Proposed create count.
   - Preview tree ordered by WBS.

5. Create records.
   - Require BOQ Header status `Draft`.
   - Create BOQ Structure group rows first.
   - Create leaf BOQ Structure rows.
   - Auto-created BOQ Items are then updated with unit, quantity, price, factor, owner fields.
   - Explicitly rebuild the nested set after batch insert if controller hooks are bypassed.
   - Recalculate header totals.
   - Protect against duplicate import into the same Draft BOQ by checking WBS before create.

6. Generate import error report.
   - Original rows plus `Error` and `Warning` columns.

7. Harden export.
   - Add Arabic/bilingual labels option.
   - Add RTL Excel sheet option.
   - Add currency formatting.
   - Add section subtotals.
   - Add metadata: company, project, BOQ, version, status, date, prepared by.
   - Keep exported files private by default unless intentionally public.
   - Fix depth calculation performance by precomputing parent/depth data instead of one DB call per node.
   - Normalize PDF and Excel privacy behavior and avoid exposing private files through public URLs.

8. Add import limits and async path.
   - Define max synchronous row count.
   - Define max file size.
   - For large BOQs, enqueue background import and expose status/progress.
   - Generate downloadable error report for failed background imports.

## Tests

Import unit tests:

- Valid template parses successfully.
- Missing required column fails.
- Duplicate WBS fails.
- Missing parent WBS fails.
- Item without unit fails.
- Item with negative quantity fails.
- Section with unit price fails.
- Factor blank defaults to 1.
- Arabic type aliases parse correctly.
- Import blocked when BOQ is Pricing/Frozen/Locked.
- Duplicate import into same Draft BOQ does not create duplicate WBS rows.

Import integration tests:

- Import creates correct BOQ Structure tree.
- Import creates linked BOQ Items for leaves.
- Imported quantities/prices update BOQ Items.
- Header totals recalculate.
- Nested-set `lft/rgt` are valid after import.
- Validation-only mode creates no records.
- Large import over threshold is queued or blocked with clear message.

Export tests:

- Header Excel exports configured columns.
- Full BOQ Excel exports tree order.
- Section rows omit item-only values.
- Section subtotals and grand total are correct.
- PDF export renders full BOQ.
- Arabic/RTL export option renders labels and alignment correctly.
- Export of 500+ row BOQ completes within acceptable time.
- Deep WBS export avoids N+1 parent-depth queries.
- Excel and PDF privacy behavior is consistent.

Manual QA:

- Upload valid BOQ file from form.
- Upload invalid BOQ file and download error report.
- Export Excel and compare to imported structure.
- Export PDF and inspect page breaks.

## Deliverables

- Real `BOQImportService`.
- Import preview API.
- Import error report generator.
- Enhanced export formatting.
- Tests and sample fixtures.

---

# Work Package 3: Stage Measurement and Certification UI

## Current State

`BOQ Item Stage` has planned quantity, measured executed quantity, certified quantity, percent complete, parent context validation, stage code auto-numbering, and concurrency protection for planned distribution through a `SELECT ... FOR UPDATE` lock. It does not yet behave like a formal measurement/certification workflow in the UI.

## Target Outcome

Stage UI should support site measurement and certification in a way that can later feed payment certificates/IPCs.

## Functional Plan

1. Split stage form into clear groups.
   - Parent Context.
   - Stage Identity.
   - Planning.
   - Site Measurement.
   - Certification.
   - Attachments/References.

2. Add read-only parent summary.
   - Parent BOQ Item quantity.
   - Total planned quantity.
   - Remaining planned quantity.
   - Total measured quantity.
   - Total certified quantity.
   - Remaining uncertified quantity.

3. Add status-sensitive field rules.
   - Draft/Pricing: planning fields editable.
   - Frozen/Locked: planning distribution locked.
   - Measurement fields may remain editable if progress tracking after lock is approved.
   - Certification fields editable only for authorized roles.
   - Required approval decision: after `Frozen` or `Locked`, should measured/certified progress remain editable?
   - Recommendation: lock planning fields in Frozen/Locked, but allow measured/certified progress by authorized roles.
   - Use field-level `permlevel` for certification fields if role separation is required.

4. Add list view indicators.
   - Over-planned.
   - Measured not certified.
   - Completed.
   - Certification status.

5. Add bulk stage creation.
   - Dialog to create stages by names or percentage split.
   - Validate total planned quantity.

6. Prepare for payment certificates.
   - Query endpoint for certifiable stages.
   - Certification status.
   - Cumulative quantity support.

7. Add stage delete safety.
   - Block deleting a stage referenced by any transaction row.
   - Block deleting certified stages unless an authorized reversal policy is approved.
   - Note: transaction-reference delete safety is already partially implemented through the BOQ Item Stage `before_delete` lifecycle hook; this work package should verify that guard and add the certified-stage policy check.

8. Implement bulk creation as server-backed operation.
   - Client dialog collects stage names/splits.
   - Server method validates total distribution and creates stages transactionally.

## Tests

Server tests:

- Planned quantity cannot be negative.
- Measured quantity cannot be negative.
- Certified quantity cannot be negative.
- Certified quantity cannot exceed measured quantity.
- Percent complete must be 0 to 100.
- Draft/Pricing total planned cannot exceed item quantity.
- Frozen/Locked total planned must equal item quantity.
- Parent context is auto-filled from BOQ Item.
- Mismatched BOQ Header/Structure/Project is blocked.
- Stage referenced by transaction row cannot be deleted.
- Certified stage cannot be deleted unless reversal policy permits it.
- Planned distribution concurrency lock prevents two simultaneous over-allocations.

Permission/role tests:

- Site Engineer can update measured fields if approved.
- Accountant cannot update measurement fields if not approved.
- Project Manager/QS can update certification fields.
- Planning fields blocked in Frozen/Locked.
- Certification fields require approved role/permlevel.

Client/UI tests:

- Selecting BOQ Item populates BOQ Header and Structure.
- Changing Project clears incompatible fields.
- Parent summary displays correct quantities.
- List indicators appear correctly.
- Bulk stage creation validates split totals.

Manual QA:

- Create stages for one BOQ Item.
- Try over-planning.
- Measure partial execution.
- Certify less than measured.
- Verify list and form summaries.

## Deliverables

- Improved BOQ Item Stage form layout/profile.
- Optional new stage fields.
- Summary API.
- List indicators.
- Tests for stage measurement/certification behavior.

---

# Work Package 4: Scope Context Consistency Across Transaction DocTypes

## Current State

Scope context exists for list filtering, form defaults, BOQ link queries, and BOQ transaction row validation. Transaction doctypes currently include Purchase Order, Purchase Receipt, Purchase Invoice, Sales Invoice, Stock Entry, Timesheet, Journal Entry, and Material Request.

## Target Outcome

Scope behavior should be consistent between list views, form defaults, link field queries, server validation, and save/submit behavior.

## Functional Plan

1. Define supported transaction matrix.
   - Parent fields: company, project, cost_center.
   - Child table field.
   - Child row fields: boq_header, boq_structure, boq_item, boq_item_stage.
   - Gate rule: direct expense, progress billing, direct labor, etc.
   - Explicitly verify Journal Entry Account child fields exist and work differently from item child tables.

2. Create a single server registry.
   - Child table name.
   - BOQ fields.
   - Project source.
   - Company source.
   - Gate rule.
   - Allowed statuses.
   - Gate rule enum examples: `direct_expense`, `progress_billing`, `direct_labor`, `always_allowed`, `disabled`.

3. Align client queries with server rules.
   - Allowed BOQ statuses.
   - Scope dimensions.
   - Gate rules.
   - Project/company consistency.
   - Allow allowed-status override per gate rule where future certificates/progress billing require it.

4. Add scope drift protection.
   - Server validation always wins.
   - User alert explains what changed.
   - Reload only when needed.

5. Add audit visibility.
   - Log auto-corrected BOQ attribution old/new values.
   - Decide whether users receive a visible alert for auto-correction or only server/audit log.

6. Standardize opt-out behavior.
   - Local list opt-out is okay for convenience.
   - Server enforcement must never be bypassed.
   - Non-construction transactions remain valid when no BOQ Item is selected.

## Tests

Server validation tests for each supported transaction DocType:

- Row with BOQ Item auto-fills BOQ Header and Structure.
- BOQ Item in Draft/Pricing is blocked for transaction attribution.
- BOQ Item in Frozen/Locked is allowed.
- Project mismatch is blocked.
- BOQ Item Stage without BOQ Item is blocked.
- Stage that belongs to different BOQ Item is blocked.
- Company/scope mismatch is blocked where applicable.
- Journal Entry Account rows with BOQ fields validate without crashing ordinary Journal Entries.

Client query tests:

- BOQ Header query respects scope.
- BOQ Structure query depends on selected BOQ Header.
- BOQ Item query depends on BOQ Header and Structure.
- BOQ Stage query depends on BOQ Item.
- Gate closed hides/clears BOQ fields.

List view tests:

- Scope filters apply to doctypes with matching fields.
- Cost center descendant expansion works.
- Scope change refreshes active list.
- Local opt-out affects only list filtering.

Regression tests:

- Existing transaction without BOQ fields still saves.
- Non-construction transactions are not forced into BOQ attribution.
- Server validation remains active if JS fails.
- Construction Settings or equivalent rollout setting does not weaken server validation unexpectedly.

## Deliverables

- Transaction scope matrix document.
- Central transaction registry.
- Aligned client/server filtering.
- Tests across all supported transaction DocTypes.

---

# Work Package 5: Arabic/English Labels and Print Formats

## Current State

Arabic translation files exist. Print templates are currently basic English-oriented HTML. Print/PDF styling exists but is not yet a full bilingual construction print system.

## Target Outcome

Arabic/English labels and print formats should support Egypt/Gulf sales demos and real operation: bilingual output, RTL alignment, readable BOQ tables, and professional PDF/print layouts.

## Functional Plan

1. Define language modes.
   - English print.
   - Arabic print.
   - Bilingual print.
   - Recommendation: build bilingual mode because many Egypt/Gulf companies operate with mixed Arabic/English documents.
   - Recommendation: use Western numerals by default in Arabic financial tables, with optional Arabic-Indic numerals only if approved.

2. Translate core BOQ labels.
   - BOQ Header, BOQ Structure, BOQ Item, BOQ Item Stage.
   - WBS Code, Project, BOQ Type, Status, Version.
   - Quantity, Unit, Unit Price, Factor, Line Total.
   - Total Contract Value, Total Estimated Value, Total Budgeted Cost.
   - Planned Qty, Measured Qty, Certified Qty, Percent Complete.
   - Owner Ref No, Owner Page, Owner File Ref.

3. Improve BOQ Header print.
   - Company logo/name.
   - Project/client/consultant.
   - BOQ metadata.
   - Totals.
   - Prepared/Reviewed/Approved signature blocks.
   - Export date and user.

4. Improve full BOQ print.
   - Repeating page header.
   - WBS hierarchy.
   - Section rows.
   - Item rows.
   - Section subtotals.
   - Grand total.
   - Optional owner reference columns.
   - Page numbers.

5. RTL and bilingual layout.
   - Arabic mode uses `dir="rtl"`.
   - Right-aligned labels.
   - Arabic font stack.
   - Bilingual label pattern: `WBS Code / كود البند`.
   - Numeric financial columns stay consistently aligned.
   - Use prebuilt labels per export mode rather than concatenating labels inside templates.

6. Excel Arabic/RTL export.
   - Arabic labels.
   - Bilingual labels.
   - RTL worksheet view.
   - Use `worksheet.sheet_view.rightToLeft = True` through `openpyxl`.
   - Proper font.
   - Currency format.

7. Add Arabic PDF prerequisites.
   - Verify deployment server has Arabic-capable font such as Noto Naskh Arabic, Cairo, or Amiri.
   - Decide font loading/embedding strategy for `wkhtmltopdf`.
   - Add a preflight check or deployment note.

8. Register selectable print formats.
   - Decide whether bilingual templates are registered as Frappe `Print Format` JSON records, export-service templates, or both.
   - Ensure BOQ Header UI can select the desired language mode.

## Tests

Translation tests:

- Core BOQ labels exist in Arabic PO.
- No missing translation for print labels.
- Translation compilation succeeds.

Template tests:

- English BOQ Header print renders.
- Arabic BOQ Header print renders with `dir="rtl"`.
- Bilingual BOQ Header print renders.
- English full BOQ print renders.
- Arabic full BOQ print renders.
- Long Arabic BOQ title wraps without overflow.
- Arabic PDF visual tests are skipped or marked if required fonts are missing.

Export tests:

- Excel English labels correct.
- Excel Arabic labels correct.
- Excel bilingual labels correct.
- RTL worksheet flag applied for Arabic mode.
- PDF contains expected Arabic labels.
- Arabic text is written correctly into Excel cells.
- Western numeral default is respected unless Arabic-Indic option is enabled.

Browser/visual QA:

- Print preview on desktop.
- PDF screenshot first page.
- PDF screenshot page with table rows.
- Confirm no overlapping text.

## Deliverables

- Translation updates.
- Translation compilation step, such as `bench build --app construction` or the deployment-equivalent PO/MO/asset compilation flow.
- Print template updates.
- Export label mode support.
- RTL/bilingual print styling.
- Visual QA artifacts.

---

# Integrated Test Plan

## Automated Test Groups

Run after implementation:

1. BOQ model tests:
   - Header status/totals.
   - Structure WBS/conversion.
   - Item pricing/costing.
   - Stage measurement/certification.

2. Import/export tests:
   - Valid import.
   - Invalid import.
   - Error report.
   - Excel/PDF export.

3. Scope tests:
   - Transaction validation.
   - Query filters.
   - Scope drift.

4. Translation/print tests:
   - Arabic labels.
   - Print template render.
   - PDF generation.

5. Performance tests:
   - Import 500+ rows.
   - Export 1000-row BOQ.
   - Export deep WBS tree without excessive DB queries.

6. Migration/health tests:
   - Duplicate WBS preflight.
   - Missing WBS preflight.
   - Broken `lft/rgt` detection.
   - Orphan BOQ Item detection.

## Manual Acceptance Demo

Demo scenario:

1. Create Draft BOQ Header.
2. Import Excel BOQ.
3. Verify WBS tree and BOQ Items.
4. Resequence WBS in Draft and verify the tree again.
5. Move BOQ to Pricing/Frozen.
6. Create stages and measurement/certification values.
7. Create Purchase/Sales/Timesheet rows with BOQ attribution under scope context.
8. Export English and Arabic/Bilingual BOQ Excel.
9. Export English and Arabic/Bilingual BOQ PDF.
10. Confirm blocked actions:
    - Invalid WBS conversion.
    - Import into Frozen BOQ.
    - Over-certified stage.
    - Transaction attribution to Draft BOQ.
    - Project/scope mismatch.

## Estimated Implementation Sequence

1. WBS rules and tests.
2. Import parser and validation preview.
3. Import create flow and export hardening.
4. Stage UI and measurement summary.
5. Scope registry and transaction consistency tests.
6. Arabic/bilingual print/export labels.
7. End-to-end manual demo and visual QA.

## Final Recommendation

Approve the five work packages separately, but implement them in the order above. WBS stability must come before import. Import/export and stage measurement should come before Arabic print polish, because print/export quality depends on stable data and labels.

This sequence gives the best ROI because it improves the existing BOQ foundation into something closer to Egypt/Gulf construction ERP expectations without jumping prematurely into new payment certificate or subcontractor modules.

## Manager Review Decision Summary

Immediate planning approval:

- WP1 WBS stability. The `before_delete` placement note is now included and should be enforced during implementation.
- WP2 BOQ import/export, with import as the main build. The dry-run in-memory validation note is now included.
- WP3 stage measurement/certification UI after stage lock policy is approved. Existing stage transaction-reference delete safety should be verified, then certified-stage deletion policy added.

Conditional items resolved in this plan:

- WP4 now has `enable_boq_scope_registry` and an explicit guard for the global `*` validate hook.
- WP5 now includes translation compilation as a deliverable, plus font availability, print format registration, and numeral policy requirements.

Final package status:

- WP1: full planning approval.
- WP2: full planning approval.
- WP3: full planning approval once stage lock policy is approved.
- WP4: planning condition closed; implementation still requires JE Account compatibility verification before code changes.
- WP5: planning condition closed; implementation still requires Arabic font/printer environment verification before visual QA.
