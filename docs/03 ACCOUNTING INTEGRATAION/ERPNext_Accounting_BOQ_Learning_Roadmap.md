# ERPNext Accounting + BOQ Integration — Structured Learning Roadmap

**For:** Civil Engineering Company (Elrefae, EGP)  
**Current Stack:** ERPNext v16.18.3 + Frappe v16.18.1 + Custom Construction App  
**Target:** Frappe Cloud v16 Production  
**Learning Style:** Concept mastery + AI-agent implementation  
**Prepared by:** Software Consultant (Kimi)  
**Date:** 2026-05-28

---

## Executive Summary

You have built a **construction-grade BOQ system** inside ERPNext with:
- WBS tree structures (BOQ Structure)
- Multi-stage cost buildup (cost + overhead + profit = sell price)
- Status lifecycle (Draft → Pricing → Frozen → Locked)
- Accounting Dimension injection (BOQ Item into GL/SI/PI/JE)
- Transaction validation (project match, status gate, cascade fields)
- Scope context filtering (company/cost_center/project)

**What is missing:** The accounting engine that turns BOQ data into money movement.

This roadmap solves that in **5 phases**, each with:
- **Learn:** What you need to understand (explained for a civil engineer)
- **Build:** What your AI agent codes
- **Validate:** How you verify it works

---

## Phase 0: Environment Stabilization (Do This First)

> **Why:** Your local bench has `developer_mode` disabled and scheduler off. You cannot build accounting features without these.

### 0.1 Enable Developer Mode
```bash
# Run on your local bench
cd /home/mohamed/frappe-bench/sites/v16.localhost
echo '{"developer_mode": 1}' > site_config.json
bench --site v16.localhost clear-cache
bench restart
```

### 0.2 Enable Scheduler
```bash
bench --site v16.localhost enable-scheduler
```

### 0.3 Git Hygiene
```bash
cd /home/mohamed/frappe-bench/apps/construction
git add -A
git commit -m "pre-accounting-roadmap: save current state"
git checkout -b feature/accounting-bridge
```

### 0.4 Run Migration
```bash
bench --site v16.localhost migrate
```

### 0.5 Verify
- [ ] Can you now edit DocTypes from UI? (Check a standard DocType → Menu → Customize)
- [ ] Is scheduler active? (`bench doctor` should show scheduler active)
- [ ] Are you on `feature/accounting-bridge` branch?

---

## Phase 1: ERPNext Accounting Foundations (Week 1)

> **Goal:** Understand how ERPNext moves money before you connect your BOQ to it.
> **Analogy for Civil Engineers:** Think of the Chart of Accounts as your **Master Cost Breakdown Structure** — just like your BOQ WBS, but for money instead of concrete and steel.

### 1.1 Chart of Accounts (CoA) — The WBS of Money

**Concept:**
ERPNext uses a tree-structured Chart of Accounts. Every financial transaction posts to a leaf account. Accounts are grouped into:
- **Assets** (what you own: cash, bank, receivables, stock, equipment)
- **Liabilities** (what you owe: loans, payables, taxes)
- **Equity** (owner investment, retained earnings)
- **Income** (revenue from projects)
- **Expenses** (project costs, overhead, salaries)

**Your Context:**
Your company `Elrefae` already exists with basic accounts. You need construction-specific accounts:

| Account Code | Account Name | Group | Type | Purpose |
|-------------|-------------|-------|------|---------|
| 4100 | Project Revenue | Income | Group | Parent for all project income |
| 4110 | Progress Billing Revenue | Income | Leaf | Revenue from certified progress |
| 4120 | Variation Order Revenue | Income | Leaf | Revenue from BOQ variations |
| 5100 | Project Direct Costs | Expenses | Group | Parent for all direct costs |
| 5110 | Material Costs | Expenses | Leaf | Concrete, steel, finishes |
| 5120 | Labor Costs | Expenses | Leaf | Site wages, subcontractor labor |
| 5130 | Equipment Costs | Expenses | Leaf | Plant hire, fuel, maintenance |
| 5140 | Subcontractor Costs | Expenses | Leaf | Subcontractor invoices |
| 5200 | Project Overhead | Expenses | Group | Indirect project costs |
| 5210 | Site Supervision | Expenses | Leaf | Engineers, supervisors |
| 5220 | Site Utilities | Expenses | Leaf | Water, electricity, site office |
| 5300 | General Overhead | Expenses | Group | Company-level overhead |
| 5310 | Office Rent | Expenses | Leaf | HQ rent |
| 5320 | Administrative Salaries | Expenses | Leaf | Office staff |

**Exercise:**
1. Log into ERPNext → Accounting → Chart of Accounts
2. Add the accounts above under your `Elrefae` company
3. Set the correct `Account Type` for each (e.g., "Cost of Goods Sold" for material costs, "Income Account" for revenue)

**Agent Task:**
Add to `construction/install.py` a new function `setup_construction_chart_of_accounts()` that auto-creates these accounts on install/migrate using `frappe.new_doc("Account")`.

---

### 1.2 Journal Entries (JE) — The Universal Transaction

**Concept:**
Every financial event in ERPNext eventually becomes a **Journal Entry** — a collection of debit/credit lines that must balance to zero.

**Double-Entry Analogy:**
| Your World | Accounting World |
|-----------|-----------------|
| BOQ Item has quantity | JE line has debit or credit amount |
| WBS code | Cost Center / Project code |
| Cost buildup (cost + OH + profit) | Multi-line JE splitting cost vs. revenue |

**Key Exercise:**
Create a manual JE for a simple scenario:
> "Paid EGP 10,000 for concrete materials for Project PROJ-0001"

| Account | Debit (EGP) | Credit (EGP) | Cost Center | Project |
|---------|------------|-------------|-------------|---------|
| 5110 - Material Costs | 10,000 | | PROJ-0001 | PROJ-0001 |
| 1110 - Cash | | 10,000 | | |

**In ERPNext:**
1. Accounting → Journal Entry → New
2. Entry Type: "Journal Entry"
3. Add two rows in "Accounts" table
4. Notice how ERPNext auto-validates that Debit = Credit

**Agent Task:**
Add a button to BOQ Header: **"Create Budget Journal Entry"**
- When BOQ status moves to `Locked`, auto-generate a JE that:
  - Debits `Work in Progress` (Asset) for total budgeted cost
  - Credits `Project Budget Reserve` (Liability) for total budgeted cost
- This establishes the project budget in the GL.

---

### 1.3 Sales Invoice (SI) — Billing Your Client

**Concept:**
A Sales Invoice tells your client: "You owe us money for this work." In construction, this is typically:
- **Progress Billing** (monthly/interim certificates)
- **Final Invoice** (upon completion)
- **Variation Invoice** (for approved changes)

**Your BOQ Context:**
Your BOQ already has `contract_unit_price` and `line_total`. A Sales Invoice should pull from BOQ Item Stage's `certified_qty` multiplied by `contract_unit_price`.

**Exercise:**
1. Create a manual Sales Invoice for EGP 50,000
2. Link it to Project PROJ-0001
3. Add an Item row (create a generic "Progress Billing" Item if needed)
4. Check the GL Entry it creates (Accounting → Chart of Accounts → 1310 Debtors — you will see +50,000)
5. Check the Project dashboard — the invoice amount should appear

**Agent Task:**
Add a button to BOQ Header: **"Generate Progress Invoice"**
- Fetches all BOQ Items where `quantity_certified > 0`
- Creates a Sales Invoice with:
  - Customer = Project's customer (need to add Customer link to Project or BOQ Header)
  - Items = BOQ Items with certified quantities
  - Unit Price = `contract_unit_price`
  - Project = BOQ Header's project
  - BOQ attribution fields auto-populated

---

### 1.4 Purchase Invoice (PI) — Paying Suppliers

**Concept:**
A Purchase Invoice records what you owe suppliers. In construction:
- Material suppliers (concrete, steel)
- Subcontractors
- Equipment hire

**Your BOQ Context:**
Your transaction validation already ensures that Purchase Invoices can be tagged with BOQ references. Now you need to ensure the PI posts costs to the correct expense accounts.

**Exercise:**
1. Create a Purchase Invoice for EGP 8,000 (concrete supplier)
2. In the Items table, select an Item that maps to "Material Costs" expense account
3. Tag it with BOQ Header, BOQ Item, and BOQ Item Stage
4. Submit and check GL Entries

**Agent Task:**
Enhance `boq_accounting.py`:
- When a Purchase Invoice is submitted with BOQ attribution, validate that the Item's expense account matches the BOQ Item's `item_type`
- If mismatch, warn or auto-correct based on a mapping table in Construction Settings.

---

### 1.5 Payment Entry (PE) — Money In/Out

**Concept:**
Payment Entries record actual cash movement:
- **Receive:** Client pays your Sales Invoice
- **Pay:** You pay a supplier's Purchase Invoice

**Exercise:**
1. Create a Payment Entry against the Sales Invoice from 1.3
2. Create a Payment Entry against the Purchase Invoice from 1.4
3. Observe how the GL updates (Debtors decreases, Bank increases)

**Agent Task:**
Add a dashboard to BOQ Header showing:
- Total Invoiced (sum of linked Sales Invoices)
- Total Received (sum of Payment Entries against those invoices)
- Total Committed (sum of linked Purchase Invoices)
- Total Paid (sum of Payment Entries against purchase invoices)
- Net Cash Position = Received - Paid

---

### 1.6 Bank Reconciliation

**Concept:**
Match your ERPNext transactions against your actual bank statements. Critical for cash flow accuracy.

**Exercise:**
1. Create a Bank Account in Chart of Accounts (if not exists)
2. Upload or manually enter a bank statement line
3. Reconcile the Payment Entries from 1.5 against the statement

**Agent Task:**
Not urgent — can be learned after core integration is complete.

---

### Phase 1 Validation Checklist

- [ ] Chart of Accounts has construction-specific accounts
- [ ] Can create a Journal Entry and see it in GL Entry
- [ ] Can create a Sales Invoice linked to a Project
- [ ] Can create a Purchase Invoice with BOQ attribution
- [ ] Can create Payment Entries and see cash position
- [ ] Understand that every transaction = GL Entry

---

## Phase 2: Project-Based Accounting + BOQ Integration (Week 2)

> **Goal:** Connect your BOQ system to ERPNext's native project accounting.

### 2.1 ERPNext Projects Module Deep Dive

**Concept:**
ERPNext `Project` is more than a label. It tracks:
- **Total Sales Amount** (from linked Sales Invoices)
- **Total Cost** (from linked Purchase Invoices, Timesheets, Stock Entries)
- **Gross Margin** = Sales - Cost
- **Timesheets** (labor hours)
- **Tasks** (project milestones)

**Your Context:**
Your BOQ Header already requires a Project link. This is perfect — you just need to ensure all BOQ-tagged transactions flow into the Project's cost/revenue totals.

**Exercise:**
1. Open Project PROJ-0001
2. Check the "Financials" section — it should show totals from linked invoices
3. Create a Timesheet for 40 hours of site supervision, link to PROJ-0001
4. See how Timesheet costs appear in Project costing

**Agent Task:**
Ensure that when a BOQ-tagged transaction is submitted, the Project financials update correctly. This should happen automatically via ERPNext's native hooks, but verify:
- Sales Invoice with `project = PROJ-0001` → appears in Project Sales
- Purchase Invoice with `project = PROJ-0001` → appears in Project Cost
- Timesheet with `project = PROJ-0001` → appears in Project Cost

---

### 2.2 Cost Centers & Accounting Dimensions

**Concept:**
- **Cost Center:** A department or division (e.g., "Site A", "Site B", "HQ")
- **Accounting Dimension:** A custom slice of your data (e.g., BOQ Item, Project Phase)

You already have:
- BOQ Item as an Accounting Dimension (injected into all accounting doctypes)
- Project as standard dimension
- Cost Center in User Scope Context

**Exercise:**
1. Create Cost Centers: "Site Operations", "Project Management", "Equipment"
2. Create a Journal Entry and assign different lines to different Cost Centers
3. Run the "General Ledger" report filtered by Cost Center

**Agent Task:**
Add Cost Center auto-assignment logic:
- Based on BOQ Item's `item_type`, auto-suggest Cost Center:
  - "Measured Work" → "Site Operations"
  - "Daywork" → "Site Operations"
  - "Provisional Sum" → "Project Management"
  - "Prime Cost" → "Site Operations"
- Store mapping in Construction Settings.

---

### 2.3 Budgeting Against BOQ

**Concept:**
Your BOQ already has `total_budgeted_cost` and `total_contract_value`. This IS your project budget. You need to surface it in ERPNext's native budget reports.

**Current Gap:**
- `total_budgeted_cost` is calculated but not pushed to any GL budget account.
- `quantity_executed` and `quantity_certified` are hidden and unpopulated.

**Agent Task:**
Implement **Budget Journal Entry** (from Phase 1 Agent Task) plus:

```python
# In boq_header.py, enhance on_update when status == "Locked":

def on_update(self):
    if self.status == "Locked" and self.has_value_changed("status"):
        # 1. Lock metadata
        self.db_set("locked_by", frappe.session.user)
        self.db_set("locked_date", frappe.utils.now())

        # 2. Create Budget JE
        create_budget_journal_entry(self)

        # 3. Create Project Budget record (optional, for native reporting)
        create_project_budget(self)

def create_budget_journal_entry(boq):
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = boq.company or "Elrefae"
    je.project = boq.project
    je.posting_date = frappe.utils.today()
    je.user_remark = f"Budget established for BOQ {boq.name}"

    # Debit: Work in Progress (Asset) — create this account first
    je.append("accounts", {
        "account": "1310 - Work in Progress",
        "debit_in_account_currency": boq.total_budgeted_cost,
        "project": boq.project,
    })

    # Credit: Project Budget Reserve (Liability/Equity) — create this account
    je.append("accounts", {
        "account": "2200 - Project Budget Reserve",
        "credit_in_account_currency": boq.total_budgeted_cost,
        "project": boq.project,
    })

    je.submit()
```

---

### 2.4 Populating Progress Fields

**Current Gap:** `quantity_executed` and `quantity_certified` on BOQ Item are hidden and empty.

**Concept:**
- **Executed:** Quantity actually built/measured on site (from Stock Entries, Timesheets)
- **Certified:** Quantity approved by client/engineer (from Purchase Receipts, certified measurements)

**Agent Task:**
Create a server function that aggregates from transactions:

```python
def update_boq_progress(boq_item_name):
    item = frappe.get_doc("BOQ Item", boq_item_name)

    # Sum executed from Stock Entries + Timesheets
    stock_qty = frappe.db.sql("""
        SELECT COALESCE(SUM(qty), 0) FROM `tabStock Entry Detail`
        WHERE boq_item = %s AND docstatus = 1
    """, boq_item_name)[0][0]

    timesheet_qty = frappe.db.sql("""
        SELECT COALESCE(SUM(hours), 0) FROM `tabTimesheet Detail`
        WHERE boq_item = %s AND docstatus = 1
    """, boq_item_name)[0][0]

    # Sum certified from Purchase Receipts
    certified_qty = frappe.db.sql("""
        SELECT COALESCE(SUM(qty), 0) FROM `tabPurchase Receipt Item`
        WHERE boq_item = %s AND docstatus = 1
    """, boq_item_name)[0][0]

    item.quantity_executed = stock_qty + timesheet_qty
    item.quantity_certified = certified_qty
    item.save()
```

Unhide these fields in `boq_item.json` (change `hidden` to 0).

---

### Phase 2 Validation Checklist

- [ ] Project dashboard shows actual costs from tagged transactions
- [ ] Cost Centers are assigned and filterable in GL reports
- [ ] BOQ Lock creates a Budget JE
- [ ] BOQ Item shows live `quantity_executed` and `quantity_certified`
- [ ] Can run "General Ledger" filtered by Project + BOQ Item

---

## Phase 3: Automated Accounting Bridge (Week 3)

> **Goal:** Make BOQ events automatically generate accounting documents.
> **This is the highest-value phase.**

### 3.1 Progress Billing Automation

**Workflow:**
1. Site engineer measures work → updates `quantity_executed`
2. Client certifies → updates `quantity_certified`
3. Accountant clicks **"Generate Progress Invoice"** on BOQ Header
4. System creates Sales Invoice for all newly certified quantities

**Agent Task:**

```python
@frappe.whitelist()
def generate_progress_invoice(boq_header_name):
    boq = frappe.get_doc("BOQ Header", boq_header_name)

    if boq.status not in ["Frozen", "Locked"]:
        frappe.throw("BOQ must be Frozen or Locked to invoice.")

    # Find customer from Project
    customer = frappe.db.get_value("Project", boq.project, "customer")
    if not customer:
        frappe.throw("Project must have a Customer to generate invoice.")

    si = frappe.new_doc("Sales Invoice")
    si.customer = customer
    si.project = boq.project
    si.company = boq.company or "Elrefae"
    si.currency = "EGP"

    for item in boq.items:
        if item.quantity_certified > item.quantity_invoiced:  # need to add this field
            qty_to_invoice = item.quantity_certified - item.quantity_invoiced

            si.append("items", {
                "item_code": "Progress Billing",  # create this Item in Item master
                "item_name": f"{item.structure} - {item.item_type}",
                "description": f"BOQ Item {item.name}: Progress billing",
                "qty": qty_to_invoice,
                "rate": item.contract_unit_price,
                "amount": qty_to_invoice * item.contract_unit_price,
                "income_account": "4110 - Progress Billing Revenue",
                "cost_center": get_cost_center_for_item_type(item.item_type),
                "project": boq.project,
                "boq_header": boq.name,
                "boq_item": item.name,
            })

            # Mark as invoiced
            item.quantity_invoiced = item.quantity_certified

    if not si.items:
        frappe.throw("No new certified quantities to invoice.")

    si.save()
    return si.name
```

**Required:**
- Add `quantity_invoiced` field to BOQ Item (hidden, default 0)
- Add `customer` field to Project (or use existing if ERPNext v16 has it)
- Create a generic "Progress Billing" Item in Item master

---

### 3.2 Cost Accrual from Purchase Invoices

**Workflow:**
When a Purchase Invoice is submitted with BOQ attribution:
1. Debit correct expense account (based on item type)
2. Credit Accounts Payable
3. Update BOQ Item's `quantity_executed` or `quantity_certified`

**Agent Task:**
Enhance `boq_transaction_validation.py`:

```python
def on_purchase_invoice_submit(doc, method):
    for row in doc.items:
        if row.boq_item:
            # Update executed quantity
            boq_item = frappe.get_doc("BOQ Item", row.boq_item)
            boq_item.quantity_executed += row.qty
            boq_item.save()

            # Log the cost event
            frappe.get_doc({
                "doctype": "BOQ Cost Event",
                "boq_item": row.boq_item,
                "transaction_type": "Purchase Invoice",
                "transaction_name": doc.name,
                "amount": row.amount,
                "quantity": row.qty,
                "posting_date": doc.posting_date,
            }).insert()
```

**Note:** Consider creating a new DocType `BOQ Cost Event` to track every financial touchpoint against a BOQ Item. This becomes your audit trail.

---

### 3.3 Subcontractor Management

**Concept:**
Subcontractors are a major cost in civil engineering. ERPNext handles this via:
- **Purchase Orders** to subcontractors (lump sum or measured)
- **Purchase Invoices** upon certification
- **Retention** (withholding 5-10% until defects period ends)

**Agent Task:**
Add to Construction Settings:
- Default retention percentage (e.g., 10%)
- Retention account (Liability: "Retention Payable")

When a Purchase Invoice for a subcontractor is submitted:
- Auto-create a second PI line for retention
- Or use ERPNext's native "Payment Terms Template" with retention

---

### Phase 3 Validation Checklist

- [ ] Clicking "Generate Progress Invoice" creates a valid Sales Invoice
- [ ] Sales Invoice pulls correct certified quantities and prices
- [ ] Purchase Invoices update BOQ progress fields
- [ ] Cost Events are logged for audit
- [ ] Retention is calculated and tracked

---

## Phase 4: Reporting & Analytics (Week 4)

> **Goal:** Build the reports that tell you if your projects are profitable.

### 4.1 Actual vs. Budget Report (The Most Important Report)

**Concept:**
For each BOQ Item, compare:
- **Budget:** `quantity` × `est_unit_cost` = `total_budgeted_cost`
- **Actual Cost:** Sum of all tagged Purchase Invoices, Stock Entries, Timesheets
- **Revenue:** Sum of all tagged Sales Invoices
- **Variance:** Budget - Actual
- **Profit:** Revenue - Actual Cost

**Agent Task:**
Create a custom **Script Report**:

```python
# Report: BOQ Actual vs Budget
# Filters: Project, BOQ Header, Date Range

def execute(filters=None):
    columns = [
        {"label": "BOQ Item", "fieldname": "boq_item", "fieldtype": "Link", "options": "BOQ Item", "width": 120},
        {"label": "Structure", "fieldname": "structure", "fieldtype": "Data", "width": 150},
        {"label": "Item Type", "fieldname": "item_type", "fieldtype": "Data", "width": 100},
        {"label": "Budget Qty", "fieldname": "budget_qty", "fieldtype": "Float", "width": 100},
        {"label": "Budget Cost", "fieldname": "budget_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Actual Cost", "fieldname": "actual_cost", "fieldtype": "Currency", "width": 120},
        {"label": "Revenue", "fieldname": "revenue", "fieldtype": "Currency", "width": 120},
        {"label": "Cost Variance", "fieldname": "cost_variance", "fieldtype": "Currency", "width": 120},
        {"label": "Profit", "fieldname": "profit", "fieldtype": "Currency", "width": 120},
        {"label": "Margin %", "fieldname": "margin_pct", "fieldtype": "Percent", "width": 100},
    ]

    data = []
    for item in get_boq_items(filters):
        actual_cost = get_actual_cost(item.name)
        revenue = get_revenue(item.name)
        budget_cost = item.est_line_total

        data.append({
            "boq_item": item.name,
            "structure": item.structure,
            "item_type": item.item_type,
            "budget_qty": item.quantity,
            "budget_cost": budget_cost,
            "actual_cost": actual_cost,
            "revenue": revenue,
            "cost_variance": budget_cost - actual_cost,
            "profit": revenue - actual_cost,
            "margin_pct": ((revenue - actual_cost) / revenue * 100) if revenue else 0,
        })

    return columns, data
```

---

### 4.2 Project Cash Flow Report

**Concept:**
Track cash in and out per project over time.

**Agent Task:**
Create a report or dashboard showing:
- Monthly: Invoiced, Received, Committed, Paid, Net
- Cumulative: Same metrics running total
- Forecast: Based on BOQ `total_contract_value` and planned execution schedule

---

### 4.3 WBS Cost Report

**Concept:**
Roll up costs by BOQ Structure (WBS) node.

**Agent Task:**
Leverage your existing `lft`/`rgt` tree structure with a SQL query that joins BOQ Structure with BOQ Items and transaction data, grouping by WBS node.

---

### Phase 4 Validation Checklist

- [ ] Actual vs. Budget report runs without errors
- [ ] Report shows correct variance and profit per BOQ line
- [ ] Project Cash Flow shows monthly trends
- [ ] WBS Cost Report aggregates correctly at group and leaf levels

---

## Phase 5: Cloud Deployment & Hardening (Week 5)

> **Goal:** Prepare for Frappe Cloud v16 production.

### 5.1 Theme System Audit

**Current Risk:** 16 CSS files + 20 JS files. Frappe Cloud v16 uses Tailwind CSS, not the legacy CSS variable system.

**Agent Task:**
1. Review each CSS file for v16 compatibility
2. Replace direct DOM manipulation with Frappe's `frappe.ui.form.on` patterns
3. Test all custom dropdowns, selects, and sidebar modifications in a clean v16 environment
4. Document which theme features are essential vs. cosmetic

**Your Priority:**
The accounting bridge is more critical than the theme. Deploy with a minimal theme first, then enhance.

---

### 5.2 Data Migration Plan

**From Local to Frappe Cloud:**
1. Export fixtures from local: `bench --site v16.localhost export-fixtures`
2. Push `construction` app to a private Git repository
3. On Frappe Cloud: `bench get-app` your repo
4. Migrate and install
5. Import fixtures

**Agent Task:**
Create a migration script that exports all custom fields, DocTypes, and fixtures, validates no hardcoded local paths exist, and generates a `migration_checklist.md`.

---

### 5.3 Arabic Localization Finalization

**Current State:** Multiple translation scripts and patches exist.

**Agent Task:**
1. Consolidate all Arabic translations into `construction/translations/ar.csv`
2. Remove ad-hoc translation scripts from `install.py` and `after_migrate`
3. Test all accounting DocType labels in Arabic
4. Ensure RTL layout works for financial reports

---

### 5.4 Backup & Disaster Recovery

**Agent Task:**
1. Configure automated backups on Frappe Cloud
2. Document recovery procedure
3. Test restore from backup to a staging site

---

### Phase 5 Validation Checklist

- [ ] App installs cleanly on a fresh v16 bench
- [ ] All accounting features work without theme conflicts
- [ ] Arabic UI is complete and RTL-safe
- [ ] Backup/restore tested
- [ ] Performance acceptable (reports load < 5 seconds for 1000 BOQ items)

---

## Appendix A: Quick Reference — ERPNext Accounting for Civil Engineers

| Civil Engineering Concept | ERPNext Equivalent | Where to Find It |
|--------------------------|-------------------|-----------------|
| Master Cost Breakdown | Chart of Accounts | Accounting > Chart of Accounts |
| Project Budget | Budget / Journal Entry | Accounting > Journal Entry |
| Client Invoice | Sales Invoice | Accounting > Sales Invoice |
| Supplier Invoice | Purchase Invoice | Accounting > Purchase Invoice |
| Cash Payment/Receipt | Payment Entry | Accounting > Payment Entry |
| Cost Allocation | Cost Center | Accounting > Cost Center |
| Work Breakdown Structure | Project + BOQ Structure | Projects > Project |
| Progress Measurement | BOQ Item Stage | Construction > BOQ Item Stage |
| Retention | Payment Terms Template | Buying > Payment Terms Template |
| Cost Variance | Custom Report | Construction > Reports |

---

## Appendix B: Agent-Ready Code Templates

### Template 1: Auto-Create Sales Invoice from BOQ
```python
@frappe.whitelist()
def create_sales_invoice_from_boq(boq_header, certified_only=True):
    boq = frappe.get_doc("BOQ Header", boq_header)
    # See Phase 3.1 for full implementation
    return si.name
```

### Template 2: Validate Accounting Account on Transaction
```python
def validate_expense_account_mapping(row, parent_doc):
    mapping = {
        "Measured Work": "5110 - Material Costs",
        "Daywork": "5120 - Labor Costs",
        "Provisional Sum": "5200 - Project Overhead",
    }
    expected = mapping.get(row.item_type)
    if expected and row.expense_account != expected:
        frappe.msgprint(f"Warning: Expected {expected} for {row.item_type}")
```

### Template 3: Update BOQ Progress from Transactions
```python
def sync_boq_progress(boq_item_name):
    # Sum all tagged transactions
    # Update quantity_executed / quantity_certified
    # Triggered via scheduler every hour or on transaction submit
```

---

## Appendix C: Learning Resources

| Resource | URL | Purpose |
|----------|-----|---------|
| ERPNext Accounting Docs | https://docs.erpnext.com/docs/v16/user/manual/en/accounts | Official reference |
| Frappe Framework Tutorial | https://frappeframework.com/docs/user/en/tutorial | Custom DocType development |
| ERPNext Projects | https://docs.erpnext.com/docs/v16/user/manual/en/projects | Project-based costing |
| Double Entry Accounting | https://www.accountingcoach.com/debits-and-credits/explanation | Conceptual foundation |
| Construction Accounting | https://www.cmja.com/construction-accounting-101/ | Industry context |

---

*End of Roadmap*
