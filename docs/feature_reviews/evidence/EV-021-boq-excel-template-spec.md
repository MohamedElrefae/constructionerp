# EV-021: BOQ Excel Template Spec

Date: 2026-06-09

Task: `WP2.2`

Status: Proposed for reviewer approval.

## Purpose

Define the Excel import/export template policy before implementing parser, dry-run, commit, and error report logic.

This spec is tuned for Egypt/Gulf BOQ workflows where consultants and quantity surveyors commonly exchange BOQs in Excel with WBS/item hierarchy, Arabic descriptions, units, quantities, rates, and owner reference columns.

## Import Modes

| Mode | Flag | Behavior |
| --- | --- | --- |
| Preview / dry run | `enable_boq_excel_import_preview` | Parse and validate workbook, return errors/warnings/preview tree, create no records. |
| Commit | `enable_boq_excel_import_commit` | Create/update Draft BOQ structures/items only after successful validation. |

Commit is allowed only when:

- BOQ Header status is `Draft`.
- `G1` is verified.
- Preview validation has no blocking errors.
- Feature flag `enable_boq_excel_import_commit` is enabled.

## Worksheet Policy

Primary worksheet name:

```text
BOQ
```

Accepted aliases:

```text
BOQ
Bill of Quantities
جدول الكميات
مقايسة
```

Header row:

- Default row: row `1`.
- Future enhancement can support detecting the header row after title rows, but initial implementation should require row `1` for predictable validation.

## Required Columns

| Canonical Field | English Header | Arabic Header | Required | Applies To | Notes |
| --- | --- | --- | --- | --- | --- |
| `wbs_code` | WBS Code | كود البند | Yes | Section, Item | Imported as user-supplied Draft WBS; must be unique within uploaded file and target BOQ. |
| `parent_wbs` | Parent WBS | كود الأب | No for root, Yes for child | Section, Item | Can reference a WBS row earlier in the same file or an existing Draft BOQ structure. |
| `title` | Title / Description | الوصف | Yes | Section, Item | Arabic and English text accepted. |
| `type` | Type | النوع | Yes | Section, Item | Accepted values listed below. |
| `unit` | Unit | الوحدة | Required for Item | Item | Optional/blank for Section. |
| `quantity` | Quantity | الكمية | Required for Item | Item | Positive number for measured items. |
| `unit_price` | Unit Price | سعر الوحدة | Optional for Item | Item | Zero allowed; blank treated as zero. |
| `factor` | Factor | المعامل | Optional | Item | Blank defaults to `1`. |

## Optional Columns

| Canonical Field | English Header | Arabic Header | Applies To | Notes |
| --- | --- | --- | --- | --- |
| `owner_page` | Owner Page | صفحة المالك | Section, Item | Consultant/tender page reference. |
| `owner_ref_no` | Owner Ref No | رقم مرجع المالك | Section, Item | Consultant/tender item reference. |
| `owner_file_ref` | Owner File Ref | مرجع ملف المالك | Section, Item | Drawing/spec/file reference. |
| `notes` | Notes | ملاحظات | Section, Item | Store as description or import note; exact field mapping to be confirmed during WP2.3. |

## Accepted Type Values

Section/group:

```text
Section
Group
Header
قسم
مجموعة
بند رئيسي
```

Leaf/item:

```text
Item
Measured Item
بند
بند مقاس
```

The parser should normalize these to:

- `Section` -> `BOQ Structure.is_group = 1`
- `Item` -> `BOQ Structure.is_group = 0` plus linked `BOQ Item`

## Numeric Rules

- `quantity`, `unit_price`, and `factor` must be numeric when provided.
- Arabic thousands/decimal separators should be normalized where practical:
  - `1,234.50`
  - `1٬234٫50`
  - `1234,50` should be accepted only if unambiguous.
- Negative quantity is blocked.
- Negative unit price is blocked for the initial implementation.
- Factor blank means `1`.
- Factor must be greater than `0`.
- Section rows must not carry quantity, unit price, or factor values except blank/zero.

## WBS and Parent Rules

- `wbs_code` is required for every row.
- Duplicate `wbs_code` inside the uploaded file is a blocking error.
- Duplicate `wbs_code` already existing in the target BOQ is a blocking error for commit.
- `parent_wbs` can reference:
  - a previous row in the same workbook, or
  - an existing BOQ Structure in the same Draft BOQ Header.
- A row cannot reference itself as parent.
- Parent must be a Section/group.
- Root rows have blank `parent_wbs`.
- The initial implementation should not resequence imported WBS codes automatically. Resequence remains a separate controlled Draft-only action.

## Status Restrictions

| BOQ Header Status | Preview | Commit |
| --- | --- | --- |
| Draft | Allowed | Allowed when commit flag is enabled |
| Pricing | Allowed for analysis only | Blocked |
| Frozen | Allowed for analysis only | Blocked |
| Locked | Allowed for analysis only | Blocked |

Preview against non-Draft BOQs is useful for consultant comparison but must not mutate the Contract BOQ.

## Error and Warning Policy

Blocking errors:

- Missing required column.
- Missing required cell value.
- Duplicate WBS.
- Missing parent.
- Parent is not a Section/group.
- Invalid numeric value.
- Item missing unit.
- Item quantity less than or equal to zero.
- Section carrying item-only commercial values.
- Commit attempted against non-Draft BOQ.

Warnings:

- Unknown optional column ignored.
- Blank unit price treated as zero.
- Blank factor treated as one.
- Arabic/English type alias normalized.
- Parent exists in database but not in uploaded file.

## Preview Response Requirements

Dry-run response should include:

- `success`
- `dry_run`
- `boq_header`
- `row_count`
- `section_count`
- `item_count`
- `error_count`
- `warning_count`
- `errors`
- `warnings`
- `proposed_creates`
- `preview_tree`

## Commit Result Requirements

Commit response should include:

- `success`
- `dry_run = false`
- `boq_header`
- `created_structures`
- `created_items`
- `skipped_rows`
- `warnings`
- `health`

After commit, run WBS health check for the affected BOQ Header.

## Export Alignment

Export should keep the same canonical columns where possible:

- WBS Code
- Parent WBS
- Title / Description
- Type
- Unit
- Quantity
- Unit Price
- Factor
- Line Total
- Owner Page
- Owner Ref No
- Owner File Ref
- Notes

Arabic/bilingual/RTL export enhancements remain linked to WP2.12 and WP5, but this import spec reserves Arabic aliases now so the parser is market-ready.

## Review Decision Needed

Reviewer should approve or change:

1. Whether `Parent WBS` is required for all non-root rows.
2. Whether imported WBS codes should be preserved exactly in Draft.
3. Whether non-Draft preview should be allowed.
4. Whether negative rates/quantities are always blocked.
5. Whether row `1` must be the header row for the first release.

## Recommendation

Approve this spec for WP2.3-WP2.8. It is conservative, aligns with consultant Excel workflows in Egypt/Gulf markets, and protects the Contract BOQ immutability policy already approved in WP1.
