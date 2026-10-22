# Construction ERP Chart of Accounts

## Implementation and Handover Report

**Prepared:** 2026-08-23  
**Company currency:** EGP  
**Target platform:** Frappe / ERPNext  
**Purpose:** Construction company ERP accounting setup and Chart of Accounts import

---

## 1. Executive Summary

The existing construction Chart of Accounts was a good construction-specific starting point, but it was not complete for a production ERPNext implementation. It lacked several ERPNext control accounts required for perpetual inventory, fixed assets, tax processing, subcontracting, deferred accounting, and Company defaults.

A complete construction-oriented importer file was created:

**[Construction_COA_Import_EGP.csv](/home/mohamed/frappe-bench/outputs/construction_coa_import/Construction_COA_Import_EGP.csv)**

The final tree contains:

- 144 accounts.
- 5 root accounts.
- 27 group accounts.
- 117 ledger accounts.
- Valid eight-column ERPNext Chart of Accounts Importer format.
- Valid parent account and parent account number relationships.
- EGP currency assigned to all ledger accounts.
- Construction-specific contract revenue, retention, subcontractor, project cost, site cost, and project WIP accounts.
- ERPNext control accounts for inventory, taxes, fixed assets, deferred accounting, exchange differences, round-off, and received-not-billed transactions.

The original source exports were not modified.

---

## 2. Source Files Reviewed

### Original construction export

[Account_List_Export.csv](/home/mohamed/Downloads/Account_List_Export.csv)

Findings:

- 56 accounts.
- Construction-specific direct costs and contract accounts were present.
- Missing multiple ERPNext operational control accounts.
- 55 of 56 rows had blank Account Category.
- All rows had Include in Gross set to No.
- No valid Bank ledger account type.
- No Stock Adjustment account.
- No Stock Received But Not Billed account.
- No Asset Received But Not Billed account.
- No Capital Work in Progress account.
- No Round Off, Write Off, Exchange, Deferred Revenue, Deferred Expense, or Disposal accounts.
- Missing Service Received But Not Billed for subcontracting and non-stock services.

### Global export

[Account_List_Export global.csv](/home/mohamed/Downloads/Account_List_Export%20global.csv)

Findings:

- 81 accounts.
- More complete than the construction export for inventory and ERPNext standard controls.
- Still not a complete ERPNext standard tree.
- Did not contain a real bank ledger account; it contained a bank group only.
- Did not provide all construction-specific contract, retention, project-cost, or subcontractor accounts.
- Its account numbers conflicted with the construction numbering design.

The global tree was therefore used as a reference, not copied directly.

---

## 3. ERPNext and Construction Design Decisions

### 3.1 Preserve the construction accounting model

The final tree preserves the construction structure for:

- Contract revenue.
- Civil, structural, MEP, and finishing revenue.
- Variation orders and claims.
- Certified progress claims.
- Customer retention receivable.
- Customer advances.
- Subcontractor costs.
- Subcontractor retention payable.
- Direct labour.
- Direct materials.
- Site equipment and site operating costs.
- Project transportation, testing, permits, and engineering costs.

### 3.2 Add ERPNext control accounts

The following ERPNext control account types were added:

- Bank.
- Cash.
- Receivable.
- Payable.
- Stock.
- Stock Adjustment.
- Stock Received But Not Billed.
- Asset Received But Not Billed.
- Service Received But Not Billed.
- Fixed Asset.
- Accumulated Depreciation.
- Capital Work in Progress.
- Depreciation.
- Tax.
- Temporary.
- Round Off.
- Round Off for Opening.
- Cost of Goods Sold.
- Expenses Included In Asset Valuation.
- Expenses Included In Valuation.

### 3.3 Avoid excessive account proliferation

Projects, sites, branches, departments, and BOQ lines should not normally be created as separate ledger accounts. They should be handled through:

- Company.
- Cost Center.
- Project.
- Branch.
- Department.
- BOQ Item accounting dimension.

The construction app already uses BOQ Item as the Phase 1 accounting dimension:

[BOQ accounting dimension ADR](/home/mohamed/frappe-bench/apps/construction/docs/ADR-001-accounting-dimension.md)

---

## 4. Final Chart Structure

### Assets — 1000

- Current Assets.
- Cash in Hand.
- Bank Accounts.
- Customer Receivables.
- Contract Receivables.
- Customer Retention Receivable.
- Unbilled Contract Work.
- Employee Advances.
- Supplier Advances.
- Security Deposits and Guarantees.
- Stock Assets.
- Construction Materials.
- Electrical and Mechanical Materials.
- Finishing Materials.
- Fuel and Lubricants.
- Spare Parts.
- Site Tools and Supplies.
- Stock Work in Progress.
- Prepaid Expenses.
- Deferred Expenses.
- Tax Assets.
- Input VAT.
- Withholding Tax Receivable.
- Fixed Assets.
- Construction Equipment.
- Vehicles.
- Mechanical Equipment.
- Electrical Equipment.
- Furniture and Fixtures.
- Office Equipment and Computers.
- Buildings.
- Software.
- Accumulated Depreciation.
- Capital Work in Progress.
- Long-term Investments.
- Temporary Opening Account.

### Liabilities — 2000

- Current Liabilities.
- Suppliers.
- Payroll Payable.
- Customer Advances / Contract Liabilities.
- Subcontractor Retention Payable.
- Accrued Expenses.
- Service Received But Not Billed.
- Other Current Liabilities.
- Stock Liabilities.
- Stock Received But Not Billed.
- Asset Received But Not Billed.
- Duties and Taxes.
- Output VAT.
- Withholding Tax Payable.
- Corporate Income Tax Payable.
- Social Insurance Payable.
- Other Taxes and Fees Payable.
- Loans and Financing.
- Long-term and Short-term Loans.
- Bank Overdraft.
- Non-current Liabilities.
- Long-term Provisions.
- Employee Benefits Obligations.
- Deferred Contract Revenue.

### Equity — 3000

- Capital.
- Reserves.
- Opening Balance Equity.
- Retained Earnings.
- Dividends Paid.
- Revaluation Surplus.

### Income — 4000

- General Contract Revenue.
- Civil Works Revenue.
- Structural Works Revenue.
- MEP Works Revenue.
- Finishing Works Revenue.
- Variation Order Revenue.
- Claims and Additional Works Revenue.
- Material and Service Sales.
- Interest Income.
- Gain on Asset Disposal.
- Exchange Gain.
- Discounts Earned.
- Miscellaneous Income.

### Expenses — 5000

- Direct Project Costs.
- Direct Labour.
- Direct Materials Consumed.
- Subcontractor Costs.
- Site Equipment.
- Direct Site Expenses.
- Site Transportation.
- Project Testing and Quality Control.
- Project Permits and Engineering Consultancy.
- Project Insurance and Guarantees.
- Inventory and Valuation Costs.
- Cost of Materials Issued to Projects.
- Expenses Included in Asset Valuation.
- Expenses Included in Valuation.
- Stock Adjustment.
- Administrative and General Expenses.
- Administrative Salaries.
- Office Rent.
- Utilities.
- Office Maintenance.
- Telephone and Internet.
- Stationery and Printing.
- Travel and Transportation.
- Legal and Professional Fees.
- Marketing and Commissions.
- General Insurance.
- Entertainment.
- Miscellaneous Expenses.
- Depreciation.
- Bank Charges.
- Interest Expense.
- Exchange Gain/Loss.
- Unrealized Exchange Gain/Loss.
- Unrealized Profit/Loss.
- Bad Debt and Write-off.
- Income Tax Expense.
- Gain/Loss on Asset Disposal.
- Round Off.
- Round Off for Opening.
- Discounts Allowed.
- Impairment.
- Deferred Expense Amortization.

---

## 5. Recommended Company Defaults After Import

Set these in **Company > Default Accounts** after the Chart of Accounts import.

| Company field | Account number | Account |
|---|---:|---|
| Default Bank Account | 1121 | البنك الرئيسي - EGP |
| Default Cash Account | 1111 | النقدية بالصندوق - الرئيسي |
| Default Receivable Account | 1210 | العملاء |
| Default Payable Account | 2110 | الموردون |
| Default Income Account | 4101 | إيرادات عقود عامة |
| Default Expense / COGS Account | 5210 | تكلفة المواد المنصرفة للمشروعات |
| Default Inventory Account | 1310 | مواد إنشائية |
| Stock Received But Not Billed | 2210 | مخزون مستلم غير مفوتر |
| Stock Adjustment Account | 5240 | تسوية المخزون |
| Asset Received But Not Billed | 2211 | أصول مستلمة غير مفوترة |
| Accumulated Depreciation Account | 1690 | مجمع إهلاك الأصول الثابتة |
| Depreciation Expense Account | 5510 | إهلاك الأصول |
| Capital Work in Progress Account | 1691 | أعمال رأسمالية تحت التنفيذ |
| Provisional Account | 2160 | خدمات مستلمة غير مفوترة |
| Default Advance Received Account | 2130 | دفعات مقدمة من العملاء |
| Default Advance Paid Account | 1270 | دفعات مقدمة للموردين |
| Round Off Account | 5600 | فروق تقريب الحسابات |
| Round Off for Opening | 5610 | فروق تقريب الأرصدة الافتتاحية |
| Write Off Account | 5570 | شطب ديون ومصروفات معدومة |
| Payment Discount Account | 5620 | خصومات مسموحة |
| Exchange Gain/Loss Account | 5540 | أرباح وخسائر فروق العملة |
| Unrealized Exchange Gain/Loss | 5550 | أرباح وخسائر فروق العملة غير المحققة |
| Unrealized Profit/Loss | 5560 | أرباح وخسائر غير محققة |
| Default Deferred Revenue | 2610 | إيرادات عقود مؤجلة |
| Default Deferred Expense | 1440 | مصروفات مؤجلة |
| Asset Disposal Account | 5590 | أرباح وخسائر بيع الأصول |

The advance accounts are required only when separate advance-party accounting is enabled.

---

## 6. Post-Import Configuration

The eight-column ERPNext importer cannot import every Account field. Configure the following after import:

### Account Categories

Assign appropriate categories to the accounts, especially:

- Cash and Cash Equivalents.
- Trade Receivables.
- Other Receivables.
- Stock Assets.
- Other Current Assets.
- Trade Payables.
- Other Current Liabilities.
- Current Tax Liabilities.
- Tangible Assets.
- Cost of Goods Sold.
- Other Direct Costs.
- Operating Expenses.
- Revenue from Operations.
- Share Capital.
- Reserves and Surplus.

### Tax configuration

Create and test Sales Taxes and Charges Templates and Purchase Taxes and Charges Templates for:

- Standard VAT.
- Zero-rated supplies, if applicable.
- Exempt supplies, if applicable.
- Input VAT.
- Output VAT.
- Withholding tax.
- Retention deductions.
- Construction progress claims.

Tax rates are deliberately not included in the CSV. Rates and tax treatment must be approved for the company’s jurisdiction and contract types before production use.

### Stock configuration

Configure:

- Perpetual Inventory.
- Default Inventory Account.
- Stock Adjustment Account.
- Stock Received But Not Billed.
- Stock valuation method.
- Warehouse accounts.
- Item Group defaults.
- Warehouse-specific stock accounts if required.

### Construction configuration

Configure:

- Cost Centers by company, branch, and project.
- Project records.
- BOQ Item accounting dimension.
- Direct expense category for project transactions.
- Direct labour designations.
- Project and BOQ validation rules.
- Subcontractor purchasing and service receipt workflow.

---

## 7. Recommended Testing Scenarios

Before production use, test the following end-to-end transactions:

1. Create a bank account and cash account.
2. Create a customer and post a customer invoice.
3. Create a progress claim / contract invoice.
4. Record customer advance.
5. Record customer retention.
6. Create a supplier and purchase construction materials.
7. Submit Purchase Receipt before Purchase Invoice.
8. Confirm posting to Stock Received But Not Billed.
9. Issue materials from stock to a project.
10. Confirm project cost and BOQ attribution.
11. Record subcontractor service receipt before invoice.
12. Confirm Service Received But Not Billed.
13. Record subcontractor retention.
14. Post stock adjustment.
15. Purchase a construction asset.
16. Confirm Asset Received But Not Billed.
17. Create an asset and run depreciation.
18. Capitalize CWIP into a fixed asset.
19. Dispose of an asset.
20. Post exchange difference and unrealized exchange difference.
21. Post round-off and opening-balance round-off.
22. Post an opening balance through Temporary Opening and Opening Balance Equity.
23. Run Trial Balance, General Ledger, Balance Sheet, Profit and Loss, Stock Ledger, Stock and Account Value Comparison, Accounts Receivable, and Accounts Payable reports.

---

## 8. Import Safety Rules

### Use only for a new or empty company

ERPNext’s Chart of Accounts Importer is designed for a company without posted GL transactions. The importer can remove existing company accounts and related account templates before creating the new tree.

Relevant local ERPNext source:

- [Importer validation](/home/mohamed/frappe-bench/apps/erpnext/erpnext/accounts/doctype/chart_of_accounts_importer/chart_of_accounts_importer.py:50)
- [Importer operation](/home/mohamed/frappe-bench/apps/erpnext/erpnext/accounts/doctype/chart_of_accounts_importer/chart_of_accounts_importer.py:76)
- [Existing-account deletion logic](/home/mohamed/frappe-bench/apps/erpnext/erpnext/accounts/doctype/chart_of_accounts_importer/chart_of_accounts_importer.py:448)

Before importing:

1. Take a full database backup.
2. Confirm the target Company has no posted GL entries.
3. Confirm the Company currency is EGP.
4. Import the CSV through Chart of Accounts Importer.
5. Confirm all five root accounts exist.
6. Set Company defaults using the table above.
7. Configure tax templates manually.
8. Configure Account Categories.
9. Run the testing scenarios.

### Existing company with transactions

Do not use the full importer on an active company. Add missing accounts individually or execute a controlled migration with a backup, staging database, and account-mapping plan.

---

## 9. Egypt Tax Configuration Note

The ERPNext local country fixture contains an Egypt tax seed named GST at 10%:

[ERPNext Egypt tax fixture](/home/mohamed/frappe-bench/apps/erpnext/erpnext/setup/setup_wizard/data/country_wise_tax.json:540)

This seed should not be treated as final statutory configuration. The Egyptian Tax Authority publishes the VAT law and subsequent amendments on its official website:

- [Egyptian VAT Law No. 67 of 2016](https://www.eta.gov.eg/sites/default/files/2024-02/Law-english-no.67-2016.pdf.pdf?form=MG0AV3)
- [Egyptian Tax Authority VAT laws and amendments](https://www.eta.gov.eg/ar/content/qwanyn-aldrybt-ly-alqymt-almdaft)

Obtain tax-adviser approval for current VAT rates, construction-contract treatment, retention, withholding, and progress-claim tax timing before production configuration.

---

## 10. Validation Result

The final file passed these checks:

- Exactly 8 importer columns.
- 144 data rows.
- No duplicate account numbers.
- No duplicate account names.
- Five valid root types: Asset, Liability, Equity, Income, Expense.
- All parent account numbers exist.
- All parent names match their parent numbers.
- All group accounts have blank currency.
- All ledger accounts have EGP currency.
- All account types are valid ERPNext account types.
- All mandatory ERPNext account types are present.

Validation result: **PASS**.

---

## 11. Final Deliverables

- [Construction_COA_Import_EGP.csv](/home/mohamed/frappe-bench/outputs/construction_coa_import/Construction_COA_Import_EGP.csv)
- This report: `/home/mohamed/frappe-bench/outputs/construction_coa_import/Construction_COA_Analysis_Report.md`

The original exports remain unchanged and can be retained as historical reference files.
