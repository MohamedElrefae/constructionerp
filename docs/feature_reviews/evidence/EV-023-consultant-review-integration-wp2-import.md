# EV-023: Consultant Review Integration for Flat BOQ Import

Date: 2026-06-09

Task Context: `WP2.2`, precondition for `WP2.3`

Review Source:

```text
/home/mohamed/.codex/attachments/00bea6ce-0626-4c83-ac41-30099aee23e7/pasted-text.txt
```

Status: Required specification update before implementation.

## Executive Conclusion

The consultant review approves the policy direction in `EV-022`, but correctly identifies that the policy is not yet safe to implement directly.

The revised decision is:

```text
EV-022 policy direction: approved with conditions.
WP2.3 implementation: blocked until parser heuristics, multi-batch behavior, traceability fields, and restructuring UX are specified.
```

This means:

- Do not return to the strict `WBS Code required` model from `EV-021`.
- Do not start coding the flat import parser from `EV-022` as-is.
- Create a hardened implementation spec first.

## What Changes from EV-021 and EV-022

### EV-021 Status

`EV-021` is now superseded for import policy because it required `WBS Code` and `Parent WBS`.

It remains useful only for:

- structured import columns,
- export alignment,
- numeric rules,
- status restrictions.

### EV-022 Status

`EV-022` remains the correct market and architecture policy:

- WBS Code optional.
- Parent WBS optional.
- structured, semi-structured, and flat import modes.
- Draft-only direct BOQ import.
- post-start imports through Variation Orders.

But it must be hardened before `WP2.3`.

## Consultant Findings Accepted

The following consultant findings are accepted and should be integrated into the implementation plan.

### 1. Parser Heuristics Must Be Deterministic

The rule:

```text
description exists + unit blank + quantity blank + unit price blank = Section
```

is not enough.

It can misclassify:

- project title rows,
- contractor/client name rows,
- blank spacer rows,
- subtotal rows,
- total rows,
- merged heading rows,
- notes rows,
- provisional-sum narrative rows.

Implementation must include an ambiguous-row stage and preview confirmation before commit.

### 2. Flat Import Needs a Restructuring Workflow

Flat import without WBS is valuable only if QS users can structure the BOQ afterward.

Minimum required workflow before releasing flat commit:

- import flat items under a selected or new root section,
- create section from selected rows,
- move selected imported items under a section,
- resequence WBS while Draft,
- show import mode and source row metadata so QS can trace the original Excel.

If this UI is not ready, flat import commit should remain behind a feature flag or limited to preview.

### 3. Multi-Batch Imports Must Avoid WBS Collisions

Flat imports must not always generate:

```text
01
01.001
01.002
```

If a BOQ Header already has structures, import must use an existing Draft-safe WBS generation path and allocate the next available sequence.

Recommended behavior:

- If importing under an existing section: generate children under that section using current max sibling sequence.
- If creating a new root: generate next available root code based on existing root WBS codes.
- Never bypass the unique `(boq_header, wbs_code)` constraint.

### 4. Heading-Like Row Detection Must Be Defined

Suggested deterministic rule:

A row may be inferred as a section only when:

1. Description/title is non-empty.
2. Unit is blank or not a known UOM.
3. Quantity is blank or zero.
4. Unit price/rate is blank or zero.
5. The row is followed by at least one item row before the next section/total row.
6. The row is not detected as title, note, subtotal, grand total, or page/header metadata.

Rows that partially match must be marked `Ambiguous`, not silently imported.

### 5. VO Import Questions Must Be Captured Now

Even though VO import belongs to WP6, these questions should be recorded now:

- Should VO import use a separate template from Draft BOQ import?
- Does import create a new Draft VO or import into an existing Draft VO?
- Who authors the Excel: consultant, client, QS, subcontractor?
- How are imported lines mapped to original BOQ items for quantity changes/omissions?
- How does the signed-PDF approval gate interact with imported VO lines?

## Revised Import Modes

### Mode A: Structured

User/system detects WBS column present.

Behavior:

- Preserve supplied WBS.
- Validate parent WBS when supplied.
- Allow missing parent only for root rows.
- Create tree exactly as supplied when valid.

### Mode B: Semi-Structured

No WBS column, but parser detects credible section rows.

Behavior:

- Show preview with inferred section/item classification.
- User must confirm or correct ambiguous rows before commit.
- Generate system WBS in Draft.
- Store `import_mode = Semi-Structured`.

### Mode C: Flat

No WBS column and no reliable section rows.

Behavior:

- User chooses import target:
  - existing Draft BOQ section, or
  - new root section name.
- If user does not provide a root name, default to:

```text
Imported BOQ Items / بنود مستوردة
```

- Generate system WBS under the chosen target.
- Store `import_mode = Flat`.
- Require QS restructuring before Pricing/Frozen/Locked if the company wants final WBS grouping.

## Required Data Model Before WP2 Commit

The consultant recommended dedicated fields from day one. This is accepted.

### BOQ Structure Fields

| Field | Type | Required Purpose |
| --- | --- | --- |
| `import_batch_id` | Data or Link | Identify upload batch. |
| `import_mode` | Select | `Structured`, `Semi-Structured`, `Flat`, `Manual`, `Variation`. |
| `source_sheet_name` | Data | Source worksheet. |
| `source_row_no` | Int | Source Excel row. |
| `source_wbs_code` | Data | Original WBS if supplied. |
| `wbs_generated_by_system` | Check | True when system generated WBS. |

### BOQ Item Fields

| Field | Type | Required Purpose |
| --- | --- | --- |
| `import_batch_id` | Data or Link | Identify upload batch. |
| `import_mode` | Select | `Structured`, `Semi-Structured`, `Flat`, `Manual`, `Variation`. |
| `source_sheet_name` | Data | Source worksheet. |
| `source_row_no` | Int | Source Excel row. |
| `source_item_ref` | Data | Consultant/client item number. |

### Optional Future DocType

Consider a dedicated `BOQ Import Batch` DocType if the import workflow needs:

- uploaded file link,
- imported by,
- import date,
- target BOQ,
- import mode,
- preview/commit status,
- error report attachment,
- row counts.

Recommendation: create `BOQ Import Batch` in WP2 if it is not too heavy. If schedule is tight, use `import_batch_id` as generated Data first, but do not lose row-level metadata.

## Required Preview Behavior

Before commit, preview must show:

- detected import mode,
- detected header row,
- rows classified as Section/Item/Ambiguous/Ignored,
- generated target WBS codes,
- target parent/root section,
- blocking errors,
- warnings,
- duplicate descriptions allowed as distinct rows unless other keys conflict,
- skipped rows and reason.

Commit should be blocked while any row is `Ambiguous` unless the user explicitly resolves it or marks it ignored.

## Header Row Policy

For first implementation, do not require row 1 only.

Recommended approach:

- Auto-detect header row within the first 20 rows.
- Score candidate rows by known English/Arabic aliases.
- Require at least two recognized business columns:
  - description/title,
  - unit,
  - quantity,
  - unit price/rate,
  - WBS/code,
  - owner ref.
- If no reliable header row is found, return a clear error and ask user to use the template.

This better supports real consultant Excel files with title rows above the table.

## Duplicate Description Policy

Duplicate descriptions in flat BOQs are common and must not be treated as errors.

Policy:

- Import duplicate descriptions as separate items.
- Preserve source row number.
- Warn only if description, unit, quantity, and rate are all identical and adjacent, because that may be accidental duplication.

## Merged Cell and RTL Policy

For Arabic-only and government/client sheets:

- Read merged-cell values by expanding the top-left merged value across the merged range during parsing.
- Support Arabic aliases.
- Support RTL worksheet display in generated templates and error reports.
- Do not rely on visual cell direction for parsing; parse values and headers.

## Multi-Batch Import Policy

Manager decision needed, but recommended default:

1. User must choose import target:
   - new root section, or
   - existing BOQ Structure group.
2. If new root:
   - root name is user-editable.
   - system generates next root WBS sequence.
3. If existing section:
   - imported rows become children under that section.
   - system generates next child WBS sequences.
4. Each import creates a unique import batch id.

This supports separate civil/MEP/finishing files without WBS collision.

## Restructuring UX Minimum Scope

Before enabling flat import commit for users, provide at least one of these:

### Minimum Server/Admin Path

- create section,
- move selected BOQ Structures to section,
- resequence WBS,
- preserve import metadata.

### Preferred UI Path

- list imported rows by batch,
- select rows,
- create section from selected rows,
- move rows to existing section,
- resequence,
- preview new WBS before saving.

If preferred UI is too large for WP2, keep flat commit behind admin/limited rollout and release preview first.

## Tracker Impact

Recommended tracker changes:

1. Keep `WP2.2` as `RDY`, not `VER`, until manager approves the hardened spec.
2. Add a new pre-implementation task before `WP2.3`:

```text
WP2.2A Harden BOQ Excel import implementation spec: parser heuristics, header detection, multi-batch target behavior, traceability fields, and flat restructuring UX.
```

3. `WP2.3` depends on `WP2.2A`.
4. Add data model task before commit:

```text
WP2.2B Add import traceability fields and optional BOQ Import Batch model.
```

5. `WP2.6` commit depends on restructuring path or explicit decision to keep flat commit limited.

## Manager Approval Checklist

The manager should approve the following before coding:

| Decision | Recommended Answer |
| --- | --- |
| Make WBS optional | Yes |
| Make Parent WBS optional | Yes |
| Support structured/semi-structured/flat modes | Yes |
| User chooses import mode or auto-detect? | Auto-detect plus user confirmation |
| Header row detection | Auto-detect first 20 rows |
| Duplicate descriptions | Allow, preserve row metadata |
| Multi-batch target | User selects new root or existing section |
| Default flat root name | Editable, default `Imported BOQ Items / بنود مستوردة` |
| Traceability fields | Dedicated fields from day one |
| BOQ Import Batch DocType | Recommended |
| Flat commit release | Only with restructuring path, or keep behind flag |
| VO import | Separate WP6 service/template |

## Final Recommendation

Accept the consultant review.

Do not implement `WP2.3` directly from `EV-022`. First approve this hardened specification and update the tracker so parser and data model work are explicit.

This approach protects ROI:

- Users can import real-world flat Excel files.
- QS teams can structure BOQs after import.
- Contract BOQ integrity remains protected.
- VO import remains properly separated for post-start changes.
