# EV-022: Flat BOQ Import and Post-Start Variation Analysis

Date: 2026-06-09

Task Context: `WP2.2`, future `WP6`

Status: Manager review required.

## Executive Summary

The first Excel template draft in `EV-021` assumed that most BOQ Excel files contain `WBS Code` and `Parent WBS`. That assumption is too strict for Egypt/Gulf market practice.

Many consultant/client BOQ files are flat Excel sheets. They may contain:

- Item description.
- Unit.
- Quantity.
- Unit rate.
- Amount.
- Sometimes section headings.
- Sometimes owner item numbers.

They often do **not** contain a formal WBS code or parent WBS code.

Therefore the import design must support three different real-world import modes:

1. **Structured coded import**: Excel has WBS and parent WBS.
2. **Semi-structured section import**: Excel has section heading rows but no formal parent WBS.
3. **Flat BOQ import**: Excel has item rows only; system creates a temporary flat structure and assigns WBS codes later.

Also, importing BOQ items after site work starts must not mutate the Contract BOQ directly. That must be handled through Variation Orders.

## Why This Matters for Egypt/Gulf ERP ROI

If we require WBS codes at import, users will spend time reformatting consultant Excel files before using the system. That reduces adoption and ROI.

For Egypt/Gulf construction companies, a better workflow is:

- Accept the consultant/client Excel as received.
- Validate commercially important data first.
- Let QS/technical office structure the BOQ inside the ERP.
- Preserve the original client item references.
- Lock the Contract BOQ after approval.
- Use Variation Orders for later changes.

This matches practical tender workflows better than forcing a perfect WBS template at upload time.

## Revised Import Policy

### Original Draft Problem

`EV-021` proposed:

| Field | Required |
| --- | --- |
| `wbs_code` | Yes |
| `parent_wbs` | No for root, Yes for child |

This should be revised.

### Recommended Policy

| Field | Revised Requirement |
| --- | --- |
| `wbs_code` | Optional |
| `parent_wbs` | Optional |
| `title` / description | Required |
| `type` | Optional if system can infer Section vs Item |
| `unit` | Required for item rows |
| `quantity` | Required for item rows |
| `unit_price` | Optional; blank means zero |

## Import Mode 1: Structured Coded BOQ

Use when Excel contains WBS codes.

Example:

| WBS Code | Parent WBS | Description | Unit | Qty | Rate |
| --- | --- | --- | --- | --- | --- |
| 01 |  | Concrete Works |  |  |  |
| 01.001 | 01 | Plain concrete | m3 | 100 | 2500 |

System behavior:

- Preserve imported WBS codes.
- Validate WBS uniqueness.
- Validate parent WBS.
- Create BOQ Structure tree.
- Create BOQ Item for leaf rows.

This is the fastest path when the consultant file is already structured.

## Import Mode 2: Semi-Structured Section BOQ

Use when Excel has headings/sections but no WBS codes.

Example:

| Description | Unit | Qty | Rate |
| --- | --- | --- | --- |
| Concrete Works |  |  |  |
| Plain concrete | m3 | 100 | 2500 |
| Reinforced concrete | m3 | 500 | 3200 |

System behavior:

- Infer section rows when unit, quantity, and rate are blank.
- Infer item rows when unit or quantity exists.
- Generate WBS automatically:
  - section: `01`
  - items under section: `01.001`, `01.002`
- Preserve original row number.
- Preserve original description.
- Store owner/client reference if available.

Important rule:

Generated WBS is a system Draft WBS, not a claim that the consultant supplied WBS codes.

## Import Mode 3: Flat BOQ Without Codes or Sections

Use when Excel is pure item list.

Example:

| Description | Unit | Qty | Rate |
| --- | --- | --- | --- |
| Excavation | m3 | 1000 | 120 |
| Plain concrete | m3 | 200 | 2500 |
| Block work | m2 | 500 | 350 |

Recommended system behavior:

1. Create one default root BOQ Structure:

```text
Imported BOQ Items
بنود مستوردة
```

2. Create every imported row as a leaf item under that root.

3. Generate system WBS automatically:

```text
01
01.001
01.002
01.003
```

4. Add import metadata:

- original Excel row number.
- original sheet name.
- original client item number if present.
- original description.
- import batch id.
- import mode = `Flat`.

5. Allow QS/technical office to restructure later while BOQ Header is still `Draft`.

This solves the “flat Excel first, WBS later” workflow.

## Required Data Model Enhancement

To support this properly, we should add import traceability fields later in WP2:

### BOQ Structure

| Field | Purpose |
| --- | --- |
| `import_batch_id` | Identify upload batch. |
| `source_sheet_name` | Excel worksheet name. |
| `source_row_no` | Original Excel row number. |
| `source_wbs_code` | Original WBS if supplied. |
| `wbs_generated_by_system` | Boolean. |

### BOQ Item

| Field | Purpose |
| --- | --- |
| `import_batch_id` | Identify upload batch. |
| `source_sheet_name` | Excel worksheet name. |
| `source_row_no` | Original Excel row number. |
| `source_item_ref` | Consultant/client item number if supplied. |

If we do not want to add fields immediately, WP2 can first store these values in description/notes, but dedicated fields are better for audit and future reporting.

## Revised Excel Column Policy

### Required Minimum for Flat Import

| Field | English Header Aliases | Arabic Header Aliases | Required |
| --- | --- | --- | --- |
| Description | Description, Title, Item Description | الوصف, بيان البند, وصف البند | Yes |
| Unit | Unit, UOM | الوحدة | Yes for item rows |
| Quantity | Qty, Quantity | الكمية | Yes for item rows |
| Unit Price | Rate, Unit Price, Price | سعر الوحدة, الفئة | Optional |

### Optional Structure Columns

| Field | English Header Aliases | Arabic Header Aliases |
| --- | --- | --- |
| WBS Code | WBS Code, Code, Item Code | كود البند, رقم البند |
| Parent WBS | Parent WBS, Parent Code | كود الأب |
| Type | Type, Row Type | النوع |
| Owner Ref No | Ref, Item No, Client Ref | رقم مرجع المالك, رقم البند |
| Owner Page | Page, BOQ Page | صفحة المالك, الصفحة |
| Notes | Notes, Remarks | ملاحظات |

## Parser Decision Logic

The parser should classify the workbook before validation.

### Step 1: Detect Available Columns

- If WBS Code exists in most rows: `Structured Coded`.
- If no WBS Code but heading-like rows exist: `Semi-Structured`.
- If no WBS Code and no heading-like rows: `Flat`.

### Step 2: Detect Row Type

Section row if:

- Description exists.
- Unit is blank.
- Quantity is blank.
- Unit price is blank.

Item row if:

- Unit exists, or
- Quantity exists, or
- Unit price exists.

Ambiguous row:

- Description exists but only some commercial fields are missing.
- Return warning or error based on severity.

### Step 3: Assign Draft WBS

If WBS is supplied:

- Preserve it.

If WBS is missing:

- Generate Draft WBS using tree order.
- Mark it as system-generated.

## UI Recommendation After Flat Import

Flat import should not be treated as final structure. The UI should show a clear status:

```text
Imported Flat BOQ - Needs Structuring
```

Recommended actions:

- Move selected items under a new section.
- Create section from selected rows.
- Resequence WBS while Draft.
- Export structured BOQ.

This gives QS users a practical workflow:

```text
Import flat Excel -> clean/validate -> group into WBS -> resequence -> pricing/freeze
```

## Import After Work Starts

This is a separate case and must not use normal BOQ import into the Contract BOQ.

Once BOQ Header is:

- `Pricing`
- `Frozen`
- `Locked`

Direct BOQ item import must be blocked.

Post-start or post-contract new items must go through Variation Orders.

## Variation Order Import Use Cases

### Case 1: New BOQ Items After Work Starts

Example:

Client issues new scope:

```text
Additional waterproofing works
```

System behavior:

- Import as VO line type `New Item`.
- Do not edit Contract BOQ.
- On VO approval, create variation BOQ Structure/Item.
- Use VO-prefixed WBS:

```text
VO-001-01
VO-001-02
```

### Case 2: Quantity Increase or Decrease

Example:

Concrete quantity increases from `500 m3` to `650 m3`.

System behavior:

- Import as VO line type `Quantity Change`.
- Store delta only:

```text
+150 m3
```

- Contract quantity remains unchanged.
- Revised BOQ computes:

```text
contract quantity + approved VO delta
```

### Case 3: Omission

Example:

Client removes a BOQ item.

System behavior:

- Import as VO line type `Omission`.
- Original item remains in Contract BOQ.
- VO records negative delta or omitted value.
- Revised BOQ shows adjusted quantity/value.

## Recommended Separate Import Services

Do not overload one import function for both tender BOQ and VO imports.

Recommended service split:

| Service | Purpose |
| --- | --- |
| `BOQImportService` | Draft BOQ creation/import before contract lock. |
| `VOImportService` | Import new items/quantity changes/omissions after work starts. |

This separation protects contract integrity and makes approvals easier to audit.

## Revised WP2/WP6 Boundary

WP2 should implement:

- Draft BOQ Excel import.
- Structured/semi-structured/flat import.
- Preview/dry-run.
- Commit into Draft only.
- Error workbook.
- Export improvements.

WP6 should implement:

- VO Excel import after work starts.
- VO line type detection.
- VO approval workflow.
- Revised BOQ computation.
- Creation of variation items after approval.

## Manager Decision Points

Please review and approve these policy changes:

1. `WBS Code` should be optional, not required.
2. `Parent WBS` should be optional, not required.
3. Flat Excel BOQ import should create a default root section named `Imported BOQ Items / بنود مستوردة`.
4. System-generated WBS codes should be allowed only while BOQ is `Draft`.
5. Imported WBS should be preserved when supplied.
6. QS users should be allowed to restructure and resequence imported flat BOQs before Pricing/Frozen/Locked.
7. After work starts, new items must be imported through Variation Orders, not direct BOQ import.
8. VO import should be implemented later in WP6 as a separate service.

## Recommendation

Approve this revised import policy.

It better reflects Egypt/Gulf BOQ Excel reality, improves adoption, reduces manual pre-formatting, and preserves enterprise ERP control by separating Draft BOQ import from post-contract Variation Orders.

## Impact on Tracker

If approved:

- Update `EV-021` or supersede it with this policy.
- Mark `WP2.2` as `VER`.
- Continue to `WP2.3` parser/normalizer implementation using three import modes:
  - `Structured`
  - `Semi-Structured`
  - `Flat`

If not approved:

- Keep `WP2.2` as `RDY`.
- Revise import template rules again before implementation.
