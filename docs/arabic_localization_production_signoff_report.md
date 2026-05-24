# Arabic Localization Production Sign-off Report

Date: 2026-05-24  
Prepared for: Management / Production Release Review  
Scope: Frappe Core, ERPNext, and Construction Arabic UI localization  
Validation site: `v16.localhost`

## Executive Summary

Arabic localization coverage is now complete at the catalog level for all three active application scopes:

| App | Total Arabic PO Messages | Translated | Empty | Fuzzy |
|---|---:|---:|---:|---:|
| Frappe | 5,902 | 5,902 | 0 | 0 |
| ERPNext | 8,997 | 8,997 | 0 | 0 |
| Construction | 351 | 351 | 0 | 0 |

The system no longer has empty Arabic PO entries for Frappe, ERPNext, or Construction. Arabic DB translation overrides are also active and validated.

Current DB override status:

| Metric | Value |
|---|---:|
| Arabic DB Translation rows | 294 |
| Validation result | Passed |
| Issues reported | 0 |

Validation command:

```bash
bench --site v16.localhost execute construction.scripts.check_arabic_localization.execute
```

Validation result:

```text
ok: true
issues: []
arabic_translation_count: 294
```

## What Was Completed This Session

### 1. Critical Accounting/UI Terms Corrected

The highest-risk semantic issues were corrected in DB overrides:

| Source Text | Final Arabic | Reason |
|---|---|---|
| Submit | ترحيل | ERPNext submit means posting/finalizing, not sending. |
| Submitted | تم الترحيل | Aligns with Submit. |
| Save and Submit | حفظ وترحيل | Aligns with Submit. |
| Journal Entry | قيد اليومية | Correct accounting Arabic terminology. |
| Party | الجهة | More natural business Arabic for counterparty/entity. |
| Party Type | نوع الجهة | Aligns with Party. |

### 2. ERPNext Reviewed Translation Import Completed

A reviewed ERPNext glossary/import workflow was used first.

Files involved:

- `apps/construction/docs/erpnext_ar_missing_review.csv`
- `apps/construction/docs/erpnext_ar_missing_review_filled.csv`
- `apps/erpnext/erpnext/locale/ar.po`

Result:

- 2,064 reviewed exact-match ERPNext strings were applied before the final coverage pass.
- These included high-impact ERP labels, DocType names, reports, workspace headers, accounting, stock, buying, selling, assets, manufacturing, and project terms.

### 3. Full Frappe and ERPNext Coverage Completed

After reviewed imports, a deterministic full-coverage pass filled all remaining Arabic PO gaps:

| App | Remaining Entries Filled |
|---|---:|
| Frappe | 2,997 |
| ERPNext | 2,278 |

The fill process prioritizes:

1. Reviewed glossary entries.
2. Existing Arabic DB Translation overrides.
3. Deterministic draft Arabic generation for long-tail strings.
4. Source-text fallback for risky code-like or placeholder-sensitive strings.

### 4. Translation Files Compiled

Arabic `.mo` files were compiled successfully:

```bash
bench compile-po-to-mo --app frappe
bench compile-po-to-mo --app erpnext
```

Generated/updated runtime files:

- `sites/assets/locale/ar/LC_MESSAGES/frappe.mo`
- `sites/assets/locale/ar/LC_MESSAGES/erpnext.mo`

Cache was cleared:

```bash
bench --site v16.localhost clear-cache
```

### 5. Safety Checks Performed

Placeholder set parity was checked after the full coverage pass.

Result:

```text
Frappe placeholder set mismatches: 0
ERPNext placeholder set mismatches: 0
Construction placeholder set mismatches: 0
```

This means translated strings preserve required runtime placeholders such as:

- `{0}`, `{1}`, `{name}`
- `%s`, `%d`
- `%(name)s`

Entries with real missing placeholder sets were reverted to source text to avoid runtime formatting errors.

## Current Repository Artifacts

### New / Updated Construction Documentation

- `docs/global_arabic_localization_tracker.md`
- `docs/global_arabic_catalog_stats.csv`
- `docs/frappe_ar_missing_review.csv`
- `docs/erpnext_ar_missing_review.csv`
- `docs/erpnext_ar_missing_review_filled.csv`
- `docs/arabic_localization_production_signoff_report.md`

### New / Updated Tooling

- `construction/scripts/global_arabic_translation_review.py`

Important functions:

```bash
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.export_stats
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.export_missing_reviews
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.fill_review_from_glossary
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.fill_remaining_po
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.import_review
```

### Core PO Files Updated

- `apps/frappe/frappe/locale/ar.po`
- `apps/erpnext/erpnext/locale/ar.po`
- `apps/construction/construction/locale/ar.po`

## Production Sign-off Status

Catalog coverage is complete, but production sign-off should not rely on coverage numbers alone.

Current status:

| Area | Status | Notes |
|---|---|---|
| Empty Arabic strings | Complete | 0 empty entries across Frappe, ERPNext, Construction. |
| Arabic DB overrides | Complete for current scope | 294 rows validated. |
| Critical accounting terminology | Complete | Submit/Journal Entry fixed. |
| Placeholder safety | Passed | No placeholder set mismatches. |
| Compile validation | Passed | Frappe and ERPNext Arabic MO generated. |
| Browser QA | Pending | Required before production approval. |
| Human review of draft-filled long-tail strings | Pending | Required for quality sign-off. |
| Business/domain terminology approval | Pending | Required from finance/operations stakeholder. |

## Key Caveat

The final Frappe and ERPNext long-tail fill used deterministic draft Arabic for strings that did not have reviewed exact translations.

This was done to achieve complete Arabic UI coverage and avoid English gaps in production. It is technically safe from a runtime perspective because placeholders were checked, but it is not equivalent to a full human translation review.

Examples of strings that need human review:

- Long help text.
- Field descriptions.
- Error and validation messages.
- HTML help blocks.
- Setup wizard text.
- Rare manufacturing, stock, tax, and accounting edge-case messages.

## Recommended Production Review Plan

### Phase 1: Smoke Test Arabic UI

Goal: confirm the app renders correctly in Arabic without obvious broken UI.

Required tester:

- Internal functional tester or implementation consultant.

Recommended steps:

1. Log in as an Arabic-language user.
2. Open Desk.
3. Confirm sidebar, search, workspace names, buttons, dialogs, and list views render in Arabic.
4. Open these modules:
   - Accounting
   - Stock
   - Buying
   - Selling
   - Projects
   - Assets
   - Manufacturing
   - Construction
5. Check desktop and mobile viewport widths.
6. Confirm there are no layout-breaking labels, overlapped buttons, or unreadable long Arabic strings.

Acceptance criteria:

- No blank labels.
- No obvious English in primary workflows.
- No broken dialogs or failed page loads.
- No severe text overflow in main screens.

### Phase 2: Business Workflow QA

Goal: verify Arabic terminology in real ERP workflows.

Required testers:

- Finance/accounting reviewer.
- Inventory/operations reviewer.
- Construction business owner or project manager.

Recommended workflows:

| Area | Workflow |
|---|---|
| Accounting | Create Journal Entry, Sales Invoice, Purchase Invoice, Payment Entry. |
| Selling | Create Customer, Quotation, Sales Order, Delivery Note, Sales Invoice. |
| Buying | Create Supplier, Supplier Quotation, Purchase Order, Purchase Receipt, Purchase Invoice. |
| Stock | Create Item, Warehouse, Stock Entry, Stock Reconciliation. |
| Projects | Create Project, Task, Timesheet. |
| Assets | Create Asset and review depreciation-related forms/reports. |
| Manufacturing | Review BOM, Work Order, Material Request, Job Card if used. |
| Construction | Review custom Construction doctypes, dashboards, and workflows. |

Acceptance criteria:

- Critical business terms are understandable to Arabic users.
- Accounting terms are correct in context.
- Submit/Cancel/Amend status terminology is not misleading.
- Reports and filters can be used without switching to English.

### Phase 3: Long-tail Translation Review

Goal: review draft-filled strings for quality before final sign-off.

Recommended method:

1. Export current Arabic PO catalogs.
2. Prioritize review by user visibility:
   - Field labels.
   - Error messages.
   - Descriptions/help text.
   - HTML help blocks.
   - Setup wizard strings.
3. Review by module owner:
   - Finance reviews accounting and tax strings.
   - Stock/operations reviews inventory and warehouse strings.
   - Project team reviews construction/project strings.
   - System admin reviews Frappe framework/admin strings.
4. Correct translations in PO files or through the CSV import workflow.
5. Recompile PO files.
6. Re-run validation.

Recommended commands:

```bash
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.export_stats
bench --site v16.localhost execute construction.scripts.global_arabic_translation_review.export_missing_reviews
bench compile-po-to-mo --app frappe
bench compile-po-to-mo --app erpnext
bench --site v16.localhost execute construction.scripts.check_arabic_localization.execute
bench --site v16.localhost clear-cache
```

Acceptance criteria:

- No high-severity mistranslations in accounting, stock, sales, buying, or construction workflows.
- No placeholder or formatting errors.
- No English appears in common user journeys unless it is a technical identifier, code, URL, or proper noun.

### Phase 4: Regression Test English Users

Goal: confirm Arabic localization changes did not affect English users.

Steps:

1. Log in as an English-language user.
2. Open the same modules and workflows.
3. Confirm English UI remains normal.
4. Create and submit one sample transactional document in English.

Acceptance criteria:

- English UI is unchanged.
- No Arabic appears for English users unless data itself is Arabic.
- Transactional workflows still submit successfully.

## Production Go / No-Go Checklist

Use this checklist before final release:

| Check | Required | Status |
|---|---|---|
| Arabic PO empty count is zero | Yes | Done |
| Arabic PO fuzzy count is zero | Yes | Done |
| Frappe Arabic MO compiled | Yes | Done |
| ERPNext Arabic MO compiled | Yes | Done |
| Construction Arabic MO/current app localization verified | Yes | Done |
| DB Translation override validation passes | Yes | Done |
| Placeholder safety check passes | Yes | Done |
| Arabic Desk smoke test completed | Yes | Pending |
| Arabic core ERP workflow QA completed | Yes | Pending |
| Finance terminology approval | Yes | Pending |
| Construction terminology approval | Yes | Pending |
| English regression smoke test completed | Yes | Pending |
| Final stakeholder sign-off recorded | Yes | Pending |

## Risks and Mitigations

| Risk | Level | Mitigation |
|---|---|---|
| Draft-filled long-tail translation is awkward or too literal | Medium | Human review by module priority. |
| Accounting term mistranslation in rare validation messages | Medium | Finance reviewer signs off accounting workflows and reports. |
| Long Arabic labels break mobile layout | Medium | Browser QA at desktop and mobile widths. |
| HTML help text has awkward Arabic ordering | Low/Medium | Review HTML/help blocks after core workflows. |
| Technical strings should remain English | Low | Code-like entries are protected or reverted to source text when risky. |
| English users affected by Arabic DB overrides | Low | Validate with English user; Frappe translations are language-scoped. |

## Recommended Sign-off Owners

| Area | Owner |
|---|---|
| Overall release approval | Product / Project Manager |
| Accounting terminology | Finance Lead |
| Stock and purchasing terminology | Operations / Procurement Lead |
| Sales terminology | Sales Operations Lead |
| Construction terminology | Construction Business Owner |
| Technical validation | Engineering |
| Browser QA | QA / Implementation Consultant |

## Management Conclusion

The Arabic localization work has reached technical full coverage:

- No empty Arabic PO strings remain.
- No fuzzy Arabic PO entries remain.
- Arabic DB overrides are validated.
- Frappe and ERPNext Arabic runtime catalogs compile successfully.

The remaining work is quality sign-off, not coverage completion. Production release can proceed after Arabic browser QA, business terminology review, and English regression testing are completed and approved by the responsible stakeholders.
