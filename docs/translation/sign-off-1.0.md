# Translation Sign-off 1.0

- **Version:** 1.0
- **Date:** 2026-09-01
- **Scope:** Frappe 16.18.1 + ERPNext 16.18.3 + Construction 0.0.5 (full ERP, 15,106 strings)
- **Glossary:** v2.0 (47 terms, schema v2)
- **Approved overrides:** 28 Released rows in `construction/data/translations/approved_ar_overrides.csv`

## Health
- Loader installed: true
- Has duplicates: false
- Has null digests: false
- Constraint present: true

## Batch Status
| Batch | Count | Released | Missing | QA Flags |
|-------|-------|----------|---------|----------|
| batch-01 construction accounting |  |  |  |  |
| batch-02 contracts |  |  |  |  |
| batch-03 BOQ |  |  |  |  |
| batch-04 purchasing |  |  |  |  |
| batch-05 core actions |  |  |  |  |
| batch-06 payroll |  |  |  |  |
| batch-07 manufacturing |  |  |  |  |
| batch-08 technical |  |  |  |  |

## Quorum
- A1 (Arabic localization): Approved
- A2 (Egyptian construction accountant / QS): Approved
- A3 (QA / forbidden terminology): Approved

## Deployment Checklist
- [ ] P0 backup verified
- [ ] Migration v8_6 applied
- [ ] Frappe ar.po restored (Add Child via Packaged Release)
- [ ] Health assert passed
- [ ] Review batches generated
