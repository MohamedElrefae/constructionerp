# EV-025: WP2 Final Pre-Implementation Approval

Date: 2026-06-09

Task: `WP2.2A`

Review Source:

```text
/home/mohamed/.codex/attachments/cf721550-6078-40a0-98f4-c3d90fac63e1/pasted-text.txt
```

## Review Verdict

The third-pass software consultant review approved `EV-024` and confirmed:

```text
WP2.3 parser implementation may begin.
```

## Approved Specification Chain

| Evidence | Role |
| --- | --- |
| `EV-021` | Original Excel template spec; superseded for strict WBS import policy but retained for export/numeric references. |
| `EV-022` | Market/architecture policy: WBS optional, flat/semi/structured import, VO import separated. |
| `EV-023` | Hardened parser, multi-batch, traceability, restructuring, and data model conditions. |
| `EV-024` | Final ambiguous-row UX, import mode override, WBS collision, header detection, and batch-id decisions. |

## Approved WP2.2A Decisions

- Ambiguous rows use preview review table contract.
- Commit requires explicit per-row resolutions for ambiguous rows.
- No silent global ignore for ambiguous rows.
- Import mode is auto-detected and user-confirmed, with override allowed.
- Structured import WBS collisions are blocking errors; supplied WBS codes are not renumbered.
- Header row detection scans the first 20 rows and requires at least 2 of 6 anchor groups.
- Batch id fallback format is `BOQIMP-YYYYMMDD-<8char>`.
- Parser/dry-run work can begin before the `BOQ Import Batch` DocType decision.
- Commit remains blocked until `WP2.2B` is complete.

## Non-Blocking Implementation Notes

The consultant asked the WP2.3 developer to define/test:

- confidence mapping rules,
- header-row edge case where only optional columns match,
- override from `Flat` to `Semi-Structured`,
- cryptographically safe random suffix for future batch id work.

## Tracker Decision

`WP2.2A` can move to `VER`.

`WP2.3` can start for parser/normalizer and dry-run preview only.

`WP2.6` commit remains blocked by `WP2.2B`.
