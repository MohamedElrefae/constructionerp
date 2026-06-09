# EV-036 - WP2.12 Dependency Block

Date: 2026-06-09

## Scope

Reviewed `WP2.12` before implementation.

## Finding

`WP2.12` depends on `WP5.2`, but:

- `WP5.1` language mode policy is still `NS`.
- `WP5.2` numeral policy is still `NS`.

## Reason This Requires Approval

Arabic/bilingual Excel output for Egypt/Gulf construction buyers needs an approved output policy before implementation:

- English only
- Arabic only
- Bilingual English/Arabic
- Western numerals in Arabic output: `1, 2, 3`
- Arabic-Indic numerals in Arabic output: `١، ٢، ٣`

Implementing RTL workbook behavior without this policy risks producing outputs that do not match consultant/client expectations.

## Acceptance Impact

`WP2.12 = BLK`

Blocked pending approval of `WP5.1` and `WP5.2`.
