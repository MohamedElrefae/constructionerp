# EV-024: WP2 Second-Pass Review and Ambiguous Row UX Decision

Date: 2026-06-09

Task Context: `WP2.2A`, `WP2.2B`, `WP2.3`

Review Source:

```text
/home/mohamed/.codex/attachments/134157ec-a2f2-4f66-a15f-c96ebf70348f/pasted-text.txt
```

Status: Integrated into implementation plan. Manager approval still required before coding.

## Executive Conclusion

The second-pass software consultant review approves `EV-023` with one remaining blocking item:

```text
Ambiguous-row resolution UX must be concretely defined before WP2.3 parser implementation begins.
```

This document resolves that item as an implementation decision and clarifies three secondary items:

1. Structured import WBS collision behavior.
2. User confirmation/override behavior for import mode.
3. Import batch id format if `BOQ Import Batch` is deferred.

## Accepted Review Findings

The second-pass review confirms that `EV-023` successfully addressed the first-pass concerns:

- parser heuristics hardened,
- flat restructuring workflow scoped,
- multi-batch WBS collision addressed,
- heading-like row detection made deterministic,
- VO import questions recorded for WP6,
- `import_mode` added,
- traceability fields accepted as dedicated fields,
- editable default root section accepted.

The only remaining blocker is the pre-commit ambiguous-row resolution mechanism.

## Decision 1: Ambiguous-Row Resolution UX

### Approved Direction

Use a **preview-first review table contract** as the primary UX/API design.

The parser must never silently commit ambiguous rows.

### Preview Behavior

Dry run returns each parsed row with:

| Field | Purpose |
| --- | --- |
| `row_no` | Source Excel row number. |
| `sheet_name` | Worksheet name. |
| `raw_values` | Original parsed cell values. |
| `detected_type` | `Section`, `Item`, `Ambiguous`, or `Ignored`. |
| `confidence` | `High`, `Medium`, `Low`. |
| `reason_codes` | Machine-readable reasons for classification. |
| `display_reason` | User-facing explanation. |
| `proposed_parent` | Target parent/root if known. |
| `proposed_wbs_code` | Generated or supplied WBS preview. |
| `blocking` | Whether commit is blocked until resolved. |

### Commit Behavior

Commit accepts an optional `row_resolutions` payload.

Each resolution must include:

| Field | Values |
| --- | --- |
| `row_no` | Source Excel row. |
| `resolved_type` | `Section`, `Item`, or `Ignore`. |
| `target_parent_wbs` or `target_parent_structure` | Optional, when user assigns a parent. |
| `note` | Optional resolution note. |

Commit is blocked if:

- any row remains `Ambiguous`,
- any ambiguous row is not resolved,
- a resolution conflicts with required fields,
- user tries to commit with `Ignore ambiguous rows` without explicit row list.

### Why This Design

This is stronger than a simple "ignore ambiguous rows" toggle and safer than requiring users to re-upload a workbook for every ambiguity.

It also supports both:

- a future interactive UI table, and
- an API-only first implementation where the frontend sends `row_resolutions`.

### Error Workbook Fallback

`WP2.8` should still generate an error/review workbook with a column:

```text
Resolution
```

Allowed values:

```text
Section
Item
Ignore
```

This workbook is a fallback for consultant-heavy workflows, but it should not replace the preview table contract.

## Decision 2: Import Mode Confirmation and Override

The system should auto-detect import mode but allow user override before commit.

Detected modes:

- `Structured`
- `Semi-Structured`
- `Flat`

Preview response must include:

```json
{
  "detected_import_mode": "Flat",
  "allowed_import_modes": ["Structured", "Semi-Structured", "Flat"],
  "requires_user_confirmation": true
}
```

Commit must include:

```json
{
  "confirmed_import_mode": "Flat"
}
```

If `confirmed_import_mode` differs from the detected mode, the parser should rerun validation under the confirmed mode before commit.

## Decision 3: Structured Import WBS Collision Behavior

For Mode A / `Structured` import:

- Supplied WBS codes must be preserved.
- If a supplied WBS collides with an existing BOQ Structure in the same Draft BOQ Header, commit is blocked.
- The system must not automatically renumber supplied WBS codes in structured mode.

Reason:

Structured import means the file author intentionally supplied codes. Auto-changing them would break audit and consultant/client references.

Allowed exception:

- If the colliding existing structure belongs to the same import batch and the future workflow explicitly supports update/re-import, that can be designed later.
- Initial WP2 implementation should be create-only and block collisions.

## Decision 4: Header Row Detection Score

Header row detection should scan the first 20 rows.

Accepted header row if at least **2** of these **6 anchor groups** are recognized:

1. Description/title aliases.
2. Unit/UOM aliases.
3. Quantity aliases.
4. Unit price/rate aliases.
5. WBS/code aliases.
6. Owner/client reference aliases.

If more than one row qualifies, choose the highest score. If tied, choose the earliest row and add a warning.

If no row qualifies, return a blocking error asking the user to use the template or manually select the header row in a future UI.

## Decision 5: Import Batch ID Format

If `BOQ Import Batch` DocType is not implemented immediately, `import_batch_id` must be a UUID-style string generated at import time.

Recommended format:

```text
BOQIMP-<YYYYMMDD>-<8-char-random>
```

Example:

```text
BOQIMP-20260609-a1b2c3d4
```

This avoids collisions across multiple files and is readable in support/debugging.

If `BOQ Import Batch` DocType is implemented, the DocType name can use the same naming pattern.

## Decision 6: BOQ Import Batch Timing

The consultant clarified:

```text
BOQ Import Batch decision does not block WP2.3 parser work.
```

Accepted.

Tracker implication:

- `WP2.3` may proceed after `WP2.2A` is approved.
- `WP2.6` commit must not proceed until `WP2.2B` data model/import batch decision is implemented or explicitly deferred with UUID fields.

## Updated WP2 Dependency Recommendation

Recommended implementation sequence:

1. `WP2.2A`: approve hardened parser/UX spec.
2. `WP2.3`: implement parser and normalizer for dry-run preview.
3. `WP2.4`: implement dry-run validation with in-memory parent tree.
4. `WP2.5`: implement preview response including ambiguous row table contract.
5. `WP2.2B`: implement traceability fields / import batch decision before commit.
6. `WP2.6`: implement Draft-only commit.

This allows parser work to start before final commit data model work, while still protecting database integrity.

## Manager Approval Checklist

Manager should approve:

| Decision | Recommendation |
| --- | --- |
| Ambiguous-row UX | Preview review table contract with explicit row resolutions. |
| Ignore ambiguous rows | Only by explicit per-row resolution, not global silent toggle. |
| Error workbook fallback | Yes, in WP2.8. |
| User import mode control | Auto-detect plus user confirmation and override before commit. |
| Structured WBS collision | Blocking error; do not renumber supplied WBS. |
| Header row detection | First 20 rows; at least 2 of 6 anchor groups. |
| Batch id if no DocType | UUID-style `BOQIMP-YYYYMMDD-random`. |
| BOQ Import Batch DocType | Does not block parser; must be resolved before commit. |

## Final Recommendation

Approve `EV-023` and this `EV-024` decision document.

After approval:

- mark `WP2.2A` as `VER`,
- update `WP2.3` dependency to `WP2.2A` only for parser/dry-run work,
- keep commit tasks dependent on `WP2.2B`,
- begin parser implementation with structured/semi-structured/flat preview only.
