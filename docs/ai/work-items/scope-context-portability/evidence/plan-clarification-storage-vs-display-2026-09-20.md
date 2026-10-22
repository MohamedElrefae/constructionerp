# Plan Clarification: Storage vs Visible Bilingual Display (2026-09-20)

## Trigger

During local-site testing the owner observed that the Arabic name field appears only in
the Chart of Accounts tree and not across the rest of the application. Investigation
confirms this is the expected result of the delivery sequence, and reveals that the plan
did not state the storage/display separation explicitly. The plan is revised accordingly.

## Live-site facts (non-production test site `v16.localhost`)

| Fact | Observed |
|---|---|
| `Account-account_name_ar` custom field | exists (`Data`, label `Account Name (Arabic)`) |
| `in_list_view` / `in_standard_filter` | `0` / `0` |
| Property Setters on `Account.account_name_ar` | none |
| Account metadata | `is_tree=1`; no `title_field` |
| `construction/construction/doctype/account/account.js` | absent |
| Account values populated by Stage 4 | 81 / 81 |

Related custom fields already exist on other DocTypes (Customer, Supplier, Item) with
Arabic labels, but the shared display resolver that would surface them is not built.

## Interpretation

- **Stage 4 is a data migration.** It populated `account_name_ar` for all 81 in-scope
  accounts and produced an independently verified proposal, bundle and payload. It does
  not add any user-visible bilingual rendering.
- **Visible rendering is Stage 3** (D2 account form identity section, D3 registry/service,
  localized tree label renderer, search/tree adapters) **and Stage 7** (bilingual reports,
  exports, print). None of these are complete.
- Therefore a site where the Arabic name appears in the raw account tree but nowhere else
  is consistent with the plan, not evidence that Stage 4 failed.

## Plan revision

- The Stage 3 and Stage 4 rows in the §11 delivery table now carry explicit annotations:
  Stage 3 provides the user-visible Arabic name; Stage 4 is data-only and must not be
  accepted as visible bilingual acceptance.
- New §11.1 "Data storage versus visible bilingual display" defines the separation and the
  rule that a Stage 4 acceptance record covers storage and evidence only.
- The §21 status table now distinguishes "Stage 4 data migration (complete)" from "visible
  bilingual display (not started)".

## Boundary

No code or ERP data was changed by this clarification. It is a documentation and status
correction only.
