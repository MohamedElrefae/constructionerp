# EV-037 - WP5.1/WP5.2 Language and Numeral Policy Approval

Date: 2026-06-09

## Scope

Resolved the policy block identified in `EV-036`.

## Approved Policy

### WP5.1 Language Mode

Approved for current implementation:

- Arabic-first when the requesting Frappe session language is `ar`.
- English output remains available when the session language is not Arabic.
- Bilingual side-by-side output is deferred to later WP5 print/template work.

### WP5.2 Numeral Policy

Approved for Excel exports:

- Keep Excel numeric cells as real numeric values using Western digits.
- Do not convert BOQ quantities, prices, totals, or WBS numeric segments into Arabic-Indic string cells in WP2.12.

## Reason

The user confirmed the Egypt/Gulf QS workflow assumption:

> Most QS software in Egypt uses Western digits in cells with Arabic UI.

This preserves Excel formula, sorting, filtering, and downstream QS software compatibility while still providing Arabic labels and RTL worksheet presentation.

## Acceptance

- `WP5.1 = VER`
- `WP5.2 = VER`
- `WP2.12` dependency is unblocked.
