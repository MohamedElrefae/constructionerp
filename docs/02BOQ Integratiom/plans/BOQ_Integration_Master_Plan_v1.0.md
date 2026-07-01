# Construction ERP — BOQ Integration Master Plan
**Single Source of Truth | Phase 1 Implementation | Approved for Development**

> **Version:** 1.0 (Unified)
> **Date:** May 25, 2026
> **Status:** APPROVED — Subject to Design Sign-off
> **Authority:** Head of Engineering | Construction ERP Core Team
> **Scope:** ERPNext v16 | App Namespace: `construction`

---

## Document Control

This document is the **single source of truth** for BOQ integration. It synthesizes:
- Original Requirements (`boq_integration_requirements.md`)
- Implementation Plan (`boq_integration_implementation.md`)
- Tasks/Tests/Verification (`boq_integration_tasks_tests_verification.md`)
- Enterprise Review (Review 1 — Cardinality & Architecture)
- Reconciliation Analysis (Review 2 — Conflict Resolution)
- Engineering Review (Review 3 — Final Authority & Decisions)

**Rule:** If any prior document conflicts with this plan, this plan wins.

---

## 1. Ground Truth Decisions (Non-Negotiable)

These decisions are approved by Engineering and bind all implementation work.

### 1.1 Local Codebase is the Authority

| Parameter | Ground Truth | Rejected Alternatives |
|-----------|--------------|----------------------|
| **App Namespace** | `construction` | `constructionerp` |
| **BOQ Header Lifecycle** | Draft → Pricing → Frozen → Locked | Draft → Active → Closed |
| **BOQ Structure Parent** | `parent_structure` | `parent_boq_structure` |
| **BOQ Item → Structure Link** | `structure` | `boq_structure` |
| **BOQ Item Pricing Fields** | `contract_unit_price`, `line_total`, `est_unit_cost`, `est_unit_price`, `est_line_total` | `rate`, `budget_amount`, `contract_rate` |
| **Wildcard Hook** | `construction.overrides.scope_enforcement.validate` on `*` | Must NOT be replaced or disabled |

### 1.2 Scope Boundaries

| What We Do | What We Do NOT Do |
|-------------|-------------------|
| Add `BOQ Item Stage` DocType | Auto-update stage quantities from Stock Entry/Timesheet |
| Add `has_stages` to `BOQ Item` | Rename existing BOQ fields |
| Create Accounting Dimension for `BOQ Item` | Make `BOQ Item Stage` a GL dimension |
| Add `boq_item_stage` to 8 transaction doctypes | Build IPC / billing / progress reports |
| Server-side validation for all BOQ links | Auto-derive physical progress |
| Idempotent install/migrate setup | Revision cloning with stage reset |
| Three-layer validation architecture | Raw SQL schema changes |

### 1.3 Approved Design Decisions

| Decision | Rule | Rationale |
|----------|------|-----------|
| **Stage code uniqueness** | Composite unique index on `(boq_item, stage_code)` | Prevents ambiguous cost objects (Procore/SAP standard) |
| **Quantity distribution** | Draft/Pricing: sum ≤ parent qty. Frozen/Locked: sum = parent qty (±0.001) | Flexible planning → strict baseline |
| **Lifecycle gating** | Draft/Pricing: NO transaction attribution. Frozen/Locked: YES | Prevents costs hitting unapproved BOQs |
| **Transaction coverage** | PO, PR, PI, Stock Entry, Timesheet, JE, Sales Invoice, **Material Request** | Full demand-to-payment traceability |
| **Expense category** | Optional Select field: Direct/Indirect/Overhead/Capital | Prepares schema for future cost control |
| **Concurrency** | `SELECT ... FOR UPDATE` on parent `BOQ Item` during stage validation | Prevents race conditions on concurrent stage creation |
| **Stage quantities** | Manual entry only. `measured_executed_qty` and `certified_qty` | No auto-write from operational documents |
| **Percent complete** | Auto-calculated from `measured_executed_qty / planned_qty`, with manual override | Controlled progress tracking |

---

## 2. Data Model

### 2.1 BOQ Item Stage (New DocType)

**Module:** `construction`
**Naming:** Auto-generated (`BOQ-STG-.#####`) or field-based after review

| Field | Type | Required | Options / Config | Description |
|-------|------|----------|-----------------|-------------|
| `boq_item` | Link | Yes | `BOQ Item` | Parent BOQ item |
| `boq_header` | Link | Yes | `BOQ Header` | Fetched from BOQ Item (read-only) |
| `project` | Link | Yes | `Project` | Fetched from BOQ Header (read-only) |
| `stage_code` | Data | Yes | — | Unique per BOQ Item. Composite unique index: `(boq_item, stage_code)` |
| `stage_name` | Data | Yes | — | Human-readable, e.g., 'Ground Floor' |
| `planned_qty` | Float | Yes | Non-negative | Quantity allocated to this stage |
| `measured_executed_qty` | Float | Yes | Non-negative | **Manual entry only.** Physical progress measured on site. |
| `certified_qty` | Float | Yes | Non-negative | Quantity certified by consultant. Must be ≤ `measured_executed_qty`. |
| `percent_complete` | Percent | Yes | 0–100 | Auto-calculated from `measured_executed_qty / planned_qty`. Manual override allowed. |
| `stage_status` | Select | Yes | `Not Started`, `In Progress`, `Completed`, `Certified`, `On Hold` | Execution state |
| `description` | Small Text | No | — | Optional notes |

**Controller Validation (`boq_item_stage.py`):**
```python
import frappe
from frappe import _
from construction.services.boq_lookups import get_stages_for_item
from construction.services.boq_operational import validate_stage_quantities

class BOQItemStage(Document):
    def validate(self):
        # Fetch parent relationships
        self.boq_header = frappe.db.get_value('BOQ Item', self.boq_item, 'boq_header')
        self.project = frappe.db.get_value('BOQ Header', self.boq_header, 'project')
        
        # Operational validation
        validate_stage_quantities(self)
        
    def before_insert(self):
        # Check stage_code uniqueness at controller level (database index is primary guard)
        if frappe.db.exists('BOQ Item Stage', {'boq_item': self.boq_item, 'stage_code': self.stage_code}):
            frappe.throw(_('Stage code {0} already exists for this BOQ Item').format(self.stage_code))
```

**Database Index (add via patch or DocType config):**
```sql
ALTER TABLE `tabBOQ Item Stage`
ADD UNIQUE INDEX `unique_stage_code_per_item` (`boq_item`, `stage_code`),
ADD INDEX `idx_boq_item` (`boq_item`),
ADD INDEX `idx_boq_item_stage_code` (`boq_item`, `stage_code`);
```

### 2.2 BOQ Item (Extended)

**Add exactly ONE field:**
- `has_stages` (Check, default 0)

**Preserve ALL existing fields unchanged:**
- `quantity`, `unit`, `factor`, `contract_unit_price`, `line_total`, `est_unit_cost`, `est_unit_price`, `est_line_total`

**Do NOT add:** `rate`, `budget_amount`, `contract_rate`, `is_old_version`.

**Controller Modification (`boq_item.py`):**
```python
def validate(self):
    # Existing validation continues unchanged
    # ...
    
    # New: if has_stages, validate aggregate planned qty
    if self.has_stages:
        total_planned = frappe.db.sql('''
            SELECT SUM(planned_qty) FROM `tabBOQ Item Stage`
            WHERE boq_item = %s AND status != 'Cancelled'
        ''', (self.name,))[0][0] or 0
        
        header_status = frappe.db.get_value('BOQ Header', self.boq_header, 'status')
        
        if header_status in ['Draft', 'Pricing']:
            if total_planned > self.quantity:
                frappe.throw(f'Stage planned qty ({total_planned}) exceeds BOQ Item qty ({self.quantity})')
        elif header_status in ['Frozen', 'Locked']:
            if abs(total_planned - self.quantity) > 0.001:
                frappe.throw(f'Frozen/Locked BOQ requires exact stage distribution')
```

### 2.3 Transaction Custom Fields

Add to these **8** child table DocTypes:

1. `Purchase Order Item`
2. `Purchase Receipt Item`
3. `Purchase Invoice Item`
4. `Stock Entry Detail`
5. `Timesheet Detail`
6. `Journal Entry Account`
7. `Sales Invoice Item`
8. `Material Request Item`

**Fields:**

```json
{
    'fieldname': 'boq_item',
    'fieldtype': 'Link',
    'options': 'BOQ Item',
    'label': 'BOQ Item',
    'insert_after': 'project',
    'depends_on': "eval:doc.expense_category == 'Direct'"
}
```

```json
{
    'fieldname': 'boq_item_stage',
    'fieldtype': 'Link',
    'options': 'BOQ Item Stage',
    'label': 'BOQ Item Stage',
    'insert_after': 'boq_item',
    'depends_on': "eval:doc.boq_item && doc.expense_category == 'Direct'"
}
```

```json
{
    'fieldname': 'expense_category',
    'fieldtype': 'Select',
    'options': '\nDirect\nIndirect\nOverhead\nCapital',
    'label': 'Expense Category',
    'insert_after': 'boq_item_stage',
    'default': 'Direct'
}
```

**Note:** For GL-generating documents (Purchase Invoice, Sales Invoice, Journal Entry, Payment Entry, Stock Entry), ERPNext v16 auto-injects `boq_item` via Accounting Dimension. The custom fields above are primarily for non-GL operational documents (PO, Material Request, Task, Timesheet) and for UI consistency on GL documents.

---

## 3. Architecture

### 3.1 Three-Layer Validation Service

All validation logic is separated into three layers to prevent duplication and enable future changes.

```
construction/services/
├── __init__.py
├── boq_lookups.py              # Stateless queries — NO business rules
├── boq_operational.py          # BOQ Item Stage controller rules
├── boq_accounting.py           # Transaction hook rules
└── boq_transaction_validation.py  # Orchestrator — called by hooks
```

#### Layer 1: boq_lookups.py
Pure query functions. No validation. No side effects.

```python
import frappe

def get_header_for_item(boq_item_name):
    return frappe.db.get_value('BOQ Item', boq_item_name, 'boq_header')

def get_project_for_header(boq_header_name):
    return frappe.db.get_value('BOQ Header', boq_header_name, 'project')

def get_status_for_header(boq_header_name):
    return frappe.db.get_value('BOQ Header', boq_header_name, 'status')

def get_stages_for_item(boq_item_name, exclude_name=None):
    filters = {'boq_item': boq_item_name}
    if exclude_name:
        filters['name'] = ['!=', exclude_name]
    return frappe.get_all('BOQ Item Stage', filters=filters, fields=['planned_qty'])
```

#### Layer 2: boq_operational.py
Invoked ONLY by the `BOQ Item Stage` controller.

```python
import frappe
from frappe import _
from construction.services.boq_lookups import get_stages_for_item

def validate_stage_quantities(doc):
    """Validate quantity bounds and aggregate totals for a BOQ Item Stage."""
    
    # 1. Non-negative quantities
    if doc.planned_qty < 0 or doc.measured_executed_qty < 0 or doc.certified_qty < 0:
        frappe.throw(_('Quantities must be non-negative'))
    
    # 2. Certified <= measured
    if doc.certified_qty > doc.measured_executed_qty:
        frappe.throw(_('Certified quantity cannot exceed measured executed quantity'))
    
    # 3. Percent complete bounds
    if doc.percent_complete < 0 or doc.percent_complete > 100:
        frappe.throw(_('Percent complete must be between 0 and 100'))
    
    # 4. Aggregate planned qty check with pessimistic locking
    parent_qty = frappe.db.get_value('BOQ Item', doc.boq_item, 'quantity')
    header_status = frappe.db.get_value('BOQ Header', doc.boq_header, 'status')
    
    # Lock parent BOQ Item row to prevent concurrent over-allocation
    frappe.db.sql(
        'SELECT name, quantity FROM `tabBOQ Item` WHERE name = %s FOR UPDATE',
        (doc.boq_item,)
    )
    
    stages = get_stages_for_item(doc.boq_item, exclude_name=doc.name)
    total_planned = sum(s['planned_qty'] for s in stages) + doc.planned_qty
    
    if header_status in ['Draft', 'Pricing']:
        if total_planned > parent_qty:
            frappe.throw(_('Total planned quantity ({0}) exceeds BOQ Item quantity ({1})').format(total_planned, parent_qty))
    elif header_status in ['Frozen', 'Locked']:
        if abs(total_planned - parent_qty) > 0.001:
            frappe.throw(_('Frozen/Locked BOQ requires exact quantity distribution. Total: {0}, Expected: {1}').format(total_planned, parent_qty))
```

#### Layer 3: boq_accounting.py
Invoked ONLY by ERPNext transaction hooks (Purchase Order, Stock Entry, etc.).

```python
import frappe
from frappe import _
from construction.services.boq_lookups import get_header_for_item, get_project_for_header, get_status_for_header

def validate_transaction_row(row, parent_doc):
    """Validate BOQ links on ERPNext transaction rows."""
    
    # Rule 1: Stage requires Item
    if row.get('boq_item_stage') and not row.get('boq_item'):
        frappe.throw(_('Row {0}: BOQ Item Stage requires BOQ Item').format(row.idx))
    
    if not row.get('boq_item'):
        return  # No BOQ attribution = skip validation
    
    # Rule 2: Item must exist
    if not frappe.db.exists('BOQ Item', row.boq_item):
        frappe.throw(_('Row {0}: BOQ Item does not exist').format(row.idx))
    
    # Rule 3: Header status must allow transactions
    boq_header = get_header_for_item(row.boq_item)
    header_status = get_status_for_header(boq_header)
    if header_status in ['Draft', 'Pricing']:
        frappe.throw(_('Row {0}: BOQ Header is {1}. Transaction attribution not allowed.').format(row.idx, header_status))
    
    # Rule 4: Project consistency
    boq_project = get_project_for_header(boq_header)
    row_project = getattr(parent_doc, 'project', None) or row.get('project')
    if row_project and boq_project and row_project != boq_project:
        frappe.throw(_('Row {0}: Project mismatch. Transaction: {1}, BOQ: {2}').format(row.idx, row_project, boq_project))
    
    # Rule 5: Stage must belong to Item
    if row.get('boq_item_stage'):
        stage_parent = frappe.db.get_value('BOQ Item Stage', row.boq_item_stage, 'boq_item')
        if stage_parent != row.boq_item:
            frappe.throw(_('Row {0}: Stage does not belong to selected BOQ Item').format(row.idx))
```

### 3.2 Orchestrator: boq_transaction_validation.py

```python
from construction.services.boq_accounting import validate_transaction_row

def validate_document(doc, method):
    """Central entry point called by all transaction hooks."""
    child_table = get_child_table(doc)
    if not child_table:
        return
    
    for row in child_table:
        validate_transaction_row(row, doc)

def get_child_table(doc):
    mapping = {
        'Purchase Order': 'items',
        'Purchase Receipt': 'items',
        'Purchase Invoice': 'items',
        'Sales Invoice': 'items',
        'Stock Entry': 'items',
        'Timesheet': 'time_logs',
        'Journal Entry': 'accounts',
        'Material Request': 'items'
    }
    return getattr(doc, mapping.get(doc.doctype), None)
```

### 3.3 Accounting Dimension Setup

**File:** `construction/install.py` or `construction/boq/dimension_setup.py`

```python
import frappe
from frappe import _

DIMENSION_NAME = 'BOQ Item'
REFERENCE_DOCTYPE = 'BOQ Item'

def setup_accounting_dimension():
    """Idempotent provisioning of BOQ Item Accounting Dimension."""
    if not frappe.db.exists('Accounting Dimension', DIMENSION_NAME):
        dimension = frappe.new_doc('Accounting Dimension')
        dimension.dimension_name = DIMENSION_NAME
        dimension.document_type = REFERENCE_DOCTYPE
        dimension.label = DIMENSION_NAME
        dimension.mandatory_for_bs = 0
        dimension.mandatory_for_pl = 0
        dimension.disabled = 0
        dimension.insert(ignore_permissions=True)
        
        # Trigger native field injection
        from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import make_dimension_in_accounting_doctypes
        make_dimension_in_accounting_doctypes(doc=dimension)
        
        frappe.logger().info(f'Created Accounting Dimension: {DIMENSION_NAME}')
    else:
        frappe.logger().info(f'Accounting Dimension {DIMENSION_NAME} already exists. Skipping.')
    
    # Verify field exists on GL Entry
    if not frappe.db.has_column('GL Entry', 'boq_item'):
        frappe.logger().warning('boq_item field missing on GL Entry. Attempting re-sync.')
        dimension = frappe.get_doc('Accounting Dimension', DIMENSION_NAME)
        make_dimension_in_accounting_doctypes(doc=dimension)
```

**Hook Registration:**
```python
# construction/hooks.py
after_install = 'construction.install.setup_accounting_dimension'
after_migrate = 'construction.install.setup_accounting_dimension'
```

### 3.4 Hooks Configuration

**File:** `construction/hooks.py` — ADD to existing `doc_events`, do NOT replace.

```python
doc_events = {
    # PRESERVE EXISTING WILDCARD HOOK
    '*': {
        'validate': 'construction.overrides.scope_enforcement.validate'
    },
    
    # NEW: Transaction-specific BOQ validation
    'Purchase Order': {
        'validate': 'construction.services.boq_transaction_validation.validate_document'
    },
    'Purchase Receipt': {
        'validate': 'construction.services.boq_transaction_validation.validate_document'
    },
    'Purchase Invoice': {
        'validate': 'construction.services.boq_transaction_validation.validate_document'
    },
    'Stock Entry': {
        'validate': 'construction.services.boq_transaction_validation.validate_document'
    },
    'Timesheet': {
        'validate': 'construction.services.boq_transaction_validation.validate_document'
    },
    'Journal Entry': {
        'validate': 'construction.services.boq_transaction_validation.validate_document'
    },
    'Sales Invoice': {
        'validate': 'construction.services.boq_transaction_validation.validate_document'
    },
    'Material Request': {
        'validate': 'construction.services.boq_transaction_validation.validate_document'
    },
    
    # NEW: BOQ Item Stage deletion guard
    'BOQ Item Stage': {
        'before_delete': 'construction.services.boq_lifecycle.before_delete_boq_item_stage'
    }
}
```

---

## 4. Implementation Steps (6-Week Phase 1)

### Week 1: Baseline + Metadata (Days 1-5)

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 1 | Re-read local codebase: hooks.py, BOQ Header/Structure/Item controllers and JSON | Dev | Baseline confirmed |
| 2 | Create `BOQ Item Stage` DocType JSON + Python controller | Dev | `boq_item_stage.json`, `boq_item_stage.py` |
| 3 | Add `has_stages` to `BOQ Item` JSON. Verify no existing fields modified. | Dev | `boq_item.json` updated |
| 4 | Add database indexes for BOQ Item Stage (unique + performance) | Dev | Patch or DocType config applied |
| 5 | Add permissions for BOQ Item Stage aligned with existing BOQ doctypes | Dev | Permission records created |

**Exit Criteria:**
- `bench --site [site] migrate` runs without error
- BOQ Item Stage appears in DocType list
- `has_stages` visible on BOQ Item form
- Existing BOQ tests still pass

### Week 2: Validation Layer (Days 6-10)

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 6 | Create `boq_lookups.py` with all query functions | Dev | Service module |
| 7 | Create `boq_operational.py` with stage quantity rules + locking | Dev | Service module |
| 8 | Create `boq_accounting.py` with transaction validation rules | Dev | Service module |
| 9 | Create `boq_transaction_validation.py` orchestrator | Dev | Service module |
| 10 | Wire `BOQ Item Stage` controller to `boq_operational.py` | Dev | Controller validates via service |

**Exit Criteria:**
- Valid stages save successfully
- Invalid quantities rejected with clear messages
- Concurrent stage creation blocked by `FOR UPDATE` lock
- Stage code duplicates rejected

### Week 3: Custom Fields + Dimension (Days 11-15)

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 11 | Write idempotent custom field deployment script | Dev | `fixtures/custom_fields.py` |
| 12 | Deploy `boq_item`, `boq_item_stage`, `expense_category` to 8 doctypes | Dev | Fields visible on all target forms |
| 13 | Write idempotent Accounting Dimension setup | Dev | `install.py` |
| 14 | Register `after_install` and `after_migrate` hooks | Dev | `hooks.py` updated |
| 15 | Test idempotency: run migrate twice, verify no duplicates | Dev | Clean migration confirmed |

**Exit Criteria:**
- `boq_item_stage` dropdown visible on Purchase Order Item, Stock Entry, Timesheet, Material Request
- Accounting Dimension `BOQ Item` exists
- `boq_item` field auto-injected on GL Entry, Purchase Invoice, Sales Invoice, Journal Entry, Payment Entry, Stock Entry
- Re-running setup does not duplicate anything

### Week 4: Hook Integration + Client Scripts (Days 16-20)

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 16 | Add transaction hooks to `hooks.py` (preserve wildcard) | Dev | `hooks.py` updated |
| 17 | Write client-side cascade query filters (Project -> BOQ Item -> Stage) | Dev | `public/js/boq_filters.js` |
| 18 | Add form visibility rules (hide stage when no item, show on Direct only) | Dev | JS applied |
| 19 | Test hook regression: verify wildcard scope validation still fires | Dev | Regression test passes |
| 20 | Test all 8 doctypes with valid/invalid BOQ combinations | Dev | Validation matrix complete |

**Exit Criteria:**
- Draft/Pricing BOQ blocks transaction attribution
- Frozen/Locked BOQ allows transaction attribution
- Project mismatch rejected
- Stage-from-wrong-item rejected
- Wildcard scope hook still runs

### Week 5: Tests + Regression (Days 21-25)

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 21 | Write `test_boq_item_stage.py` (creation, validation, uniqueness, aggregates) | Dev | Test file |
| 22 | Write `test_accounting_dimension.py` (creation, idempotency, field presence) | Dev | Test file |
| 23 | Write `test_transaction_validation.py` (all 8 doctypes, positive + negative) | Dev | Test file |
| 24 | Write `test_hook_regression.py` (wildcard still registered, still fires) | Dev | Test file |
| 25 | Run full test suite: `bench --site [site] run-tests --app construction` | Dev | All tests pass |

**Exit Criteria:**
- New tests fail before implementation (where appropriate)
- New tests pass after implementation
- Existing BOQ tests pass
- Existing scope tests pass
- No test regressions

### Week 6: UAT + Documentation (Days 26-30)

| Day | Task | Owner | Deliverable |
|-----|------|-------|-------------|
| 26 | Manual BOQ authoring verification (create project -> header -> structure -> item -> stages) | PM + Dev | Checklist signed |
| 27 | Manual transaction validation verification (PO, Stock Entry, Timesheet with stages) | PM + Dev | Checklist signed |
| 28 | Write ADR-001: Accounting Dimension Cardinality Risk and Phase 2 Migration Path | Dev | `docs/ADR-001.md` |
| 29 | Write user training notes for site engineers and project managers | PM | Training doc |
| 30 | Final sign-off from Engineering + GM | All | Approval recorded |

**Exit Criteria:**
- Manual verification checklist 100% complete
- ADR-001 documented
- GM approval obtained
- Ready for production deployment

---

## 5. Complete File Structure

```
construction/                                    # App root
├── construction/
│   ├── __init__.py
│   ├── hooks.py                                # MOD: preserve wildcard + add BOQ hooks + after_install/migrate
│   ├── install.py                              # NEW: idempotent Accounting Dimension setup
│   ├── modules.txt
│   ├── patches.txt
│   │
│   ├── doctype/
│   │   ├── boq_header/                         # EXISTING — DO NOT MODIFY
│   │   ├── boq_structure/                      # EXISTING — DO NOT MODIFY
│   │   ├── boq_item/                           # EXISTING — MOD: add has_stages only
│   │   │   ├── boq_item.json
│   │   │   └── boq_item.py                     # MOD: add aggregate validation
│   │   └── boq_item_stage/                     # NEW
│   │       ├── __init__.py
│   │       ├── boq_item_stage.json
│   │       └── boq_item_stage.py
│   │
│   ├── services/                               # NEW
│   │   ├── __init__.py
│   │   ├── boq_lookups.py                      # Stateless queries
│   │   ├── boq_operational.py                  # Stage controller rules
│   │   ├── boq_accounting.py                   # Transaction hook rules
│   │   ├── boq_transaction_validation.py       # Orchestrator
│   │   └── boq_lifecycle.py                    # Deletion guards
│   │
│   ├── fixtures/
│   │   └── custom_fields.py                    # MOD/NEW: idempotent field deployment
│   │
│   ├── overrides/
│   │   └── scope_enforcement.py                # EXISTING — DO NOT MODIFY
│   │
│   └── report/                                 # EMPTY in Phase 1 (reports deferred)
│
├── public/
│   └── js/
│       └── boq_filters.js                      # NEW: cascade query filters + visibility
│
├── tests/
│   ├── __init__.py
│   ├── test_boq_item_stage.py                  # NEW
│   ├── test_accounting_dimension.py              # NEW
│   ├── test_transaction_validation.py            # NEW
│   └── test_hook_regression.py                 # NEW
│
├── docs/
│   ├── boq_integration_requirements.md         # Source (archived)
│   ├── boq_integration_implementation.md         # Source (archived)
│   ├── boq_integration_tasks_tests_verification.md  # Source (archived)
│   └── ADR-001-accounting-dimension.md         # NEW: cardinality risk + migration path
│
└── setup.py
```

---

## 6. Test Plan

### 6.1 Existing Regression Tests (Must Pass)

Run before and after every change:
- BOQ Header lifecycle (Draft -> Pricing -> Frozen -> Locked)
- BOQ Structure tree creation and navigation
- Leaf-node BOQ Item auto-creation
- Header financial rollups
- Pricing locks
- Import/export service availability
- Wildcard scope validation (`construction.overrides.scope_enforcement.validate`)

### 6.2 BOQ Item Stage Tests

| # | Test Case | Expected Result |
|---|-----------|----------------|
| 1 | Valid stage creation | Saves successfully |
| 2 | Duplicate `stage_code` for same `boq_item` | Rejected with uniqueness error |
| 3 | Negative `planned_qty` | Rejected |
| 4 | Negative `measured_executed_qty` | Rejected |
| 5 | Negative `certified_qty` | Rejected |
| 6 | `certified_qty` > `measured_executed_qty` | Rejected |
| 7 | `percent_complete` < 0 | Rejected |
| 8 | `percent_complete` > 100 | Rejected |
| 9 | Sum of stage `planned_qty` > parent `quantity` (Draft/Pricing) | Rejected |
| 10 | Sum of stage `planned_qty` != parent `quantity` (Frozen/Locked) | Rejected |
| 11 | Stage `boq_header` matches parent BOQ Item's header | Auto-fetched correctly |
| 12 | Stage `project` matches parent BOQ Header's project | Auto-fetched correctly |
| 13 | Concurrent stage creation exceeding total qty | Blocked by `FOR UPDATE` lock |

### 6.3 Accounting Dimension Tests

| # | Test Case | Expected Result |
|---|-----------|----------------|
| 1 | Dimension creation on install | `BOQ Item` dimension exists |
| 2 | Idempotency — run setup twice | No duplicate dimension created |
| 3 | Field injection on GL Entry | `boq_item` column exists |
| 4 | Field injection on Purchase Invoice | `boq_item` column exists |
| 5 | No duplicate Custom Fields after re-run | Count matches expected |

### 6.4 Transaction Validation Tests

Test each of the 8 doctypes with these scenarios:

| Scenario | Expected |
|----------|----------|
| No BOQ fields set | Allowed (no validation) |
| Valid `boq_item` only | Allowed |
| Valid `boq_item` + matching `boq_item_stage` | Allowed |
| `boq_item_stage` without `boq_item` | **Rejected** |
| Stage belongs to different BOQ Item | **Rejected** |
| BOQ Item from different Project | **Rejected** |
| BOQ Header status = Draft | **Rejected** |
| BOQ Header status = Pricing | **Rejected** |
| BOQ Header status = Frozen | Allowed |
| BOQ Header status = Locked | Allowed |

### 6.5 Hook Regression Tests

| # | Test Case | Expected Result |
|---|-----------|----------------|
| 1 | Wildcard hook still registered | `construction.overrides.scope_enforcement.validate` in `doc_events['*']` |
| 2 | Wildcard hook still fires on save | Scope validation executes |
| 3 | BOQ hook fires alongside wildcard | Both validations execute |
| 4 | BOQ hooks do not replace wildcard | `doc_events['*']` unchanged |

---

## 7. Verification Checklist

### 7.1 Metadata Inspection

```bash
# Check DocTypes
bench --site [site] console
frappe.get_all('DocType', filters={'module': 'construction'})

# Check Accounting Dimension
frappe.get_doc('Accounting Dimension', 'BOQ Item')

# Check Custom Fields
frappe.get_all('Custom Field', filters={'fieldname': ['in', ['boq_item', 'boq_item_stage', 'expense_category']]})

# Check Hooks
import construction.hooks as h
print(h.doc_events)
```

### 7.2 Database Inspection

```sql
-- Verify BOQ Item Stage indexes
SHOW INDEX FROM `tabBOQ Item Stage`;

-- Verify GL Entry has boq_item
SELECT COLUMN_NAME FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tabGL Entry' AND COLUMN_NAME = 'boq_item';

-- Verify no duplicate custom fields
SELECT dt, fieldname, COUNT(*) as cnt FROM `tabCustom Field`
WHERE fieldname IN ('boq_item_stage', 'expense_category')
GROUP BY dt, fieldname HAVING cnt > 1;
```

### 7.3 Manual UAT Steps

**BOQ Authoring:**
1. Create a Project.
2. Create a BOQ Header for the Project.
3. Create a BOQ Structure group and leaf.
4. Confirm BOQ Item auto-created with existing fields intact.
5. Enter `contract_unit_price`, `quantity`, `factor` — confirm rollups work.
6. Enable `has_stages` on BOQ Item.
7. Create stages with `stage_code`, `stage_name`, `planned_qty`.
8. Confirm aggregate validation (Draft <= qty, Frozen = qty).

**Transaction Validation:**
1. Create a Purchase Order with a valid BOQ Item (Frozen status).
2. Add a matching BOQ Item Stage — confirm save allowed.
3. Change BOQ Header to Draft — confirm PO save blocked.
4. Try a stage from a different BOQ Item — confirm rejected.
5. Try a BOQ Item from a different Project — confirm rejected.
6. Create Stock Entry (Material Issue) with BOQ Item + Stage — confirm allowed.
7. Confirm Stock Entry does NOT auto-update `measured_executed_qty`.

---

## 8. Phase 2 Roadmap (Post-Phase 1)

These features are explicitly out of scope for Phase 1. They are documented here to prevent scope creep and guide future planning.

| Priority | Feature | Business Driver | Technical Dependency |
|----------|---------|-----------------|---------------------|
| 1 | **Site Measurement Entry** DocType | Source-of-truth for `measured_executed_qty` | Phase 1 stage schema must be stable |
| 2 | **Interim Payment Certificate (IPC)** | Client billing based on certified quantities | Site Measurement Entry must exist |
| 3 | **Progress Billing Reports** | GM dashboard, cost variance, earned value | IPC + GL actuals |
| 4 | **Two-Tier Cost Object Migration** | Performance if >5,000 BOQ Items cause GL lag | ADR-001 analysis + `Cost Code` DocType |
| 5 | **Subcontracting Order Coverage** | Link subcontractor claims to BOQ stages | IPC workflow |
| 6 | **Delivery Note / Landed Cost Voucher** | Full procurement traceability | Low priority — PO/PR/PI already covered |
| 7 | **Revision Cloning with Stage Reset** | BOQ version control | Stage data model proven stable |
| 8 | **Auto-calculation of `percent_complete`** from productivity norms | Reduce manual entry | Timesheet/Stock Entry integration approved |

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| Local agent codes v3 spec instead of this plan | High | Critical | **This document is the single source of truth.** Weekly code review against Section 1. | PM |
| Accounting Dimension cardinality causes GL slowdown | Medium | High | Monitor at 1K/5K/10K items. ADR-001 defines migration path. | Dev |
| Concurrent stage creation exceeds parent qty | Medium | Medium | `FOR UPDATE` lock + aggregate validation. Test in Week 5. | Dev |
| Wildcard scope hook accidentally disabled | Low | Critical | `test_hook_regression.py` runs on every commit. | Dev |
| Existing BOQ tests break during development | Medium | High | Run existing tests daily. No existing field renamed. | Dev |
| GM delays approval, stalling Sprint 1 | Low | High | Pre-approved decisions in Section 1. Proceed with non-controversial items. | PM |

---

## 10. Appendices

### Appendix A: ADR-001 Template (Accounting Dimension Cardinality)

**Title:** BOQ Item as Accounting Dimension — Cardinality Risk and Migration Path

**Context:** Requirements mandate `BOQ Item` as the Accounting Dimension for Phase 1. Enterprise review identifies this as high-cardinality (10,000+ items per mega-project), which may stress ERPNext's dimension system designed for moderate-cardinality objects (Cost Centers, Departments).

**Decision:** Proceed with `BOQ Item` as Accounting Dimension in Phase 1, with aggressive indexing and performance monitoring.

**Consequences:**
- Acceptable for small-to-medium projects (<5,000 BOQ Items).
- Risk of GL report slowdown on mega-projects.
- Requires future migration to two-tier model (see Phase 2 Roadmap).

**Migration Path (when needed):**
1. Create `Cost Code` DocType (low cardinality, mapped to BOQ Structure leaf nodes).
2. Make `Cost Code` the new Accounting Dimension.
3. Convert `boq_item` on GL Entry from dimension to custom Link field (analytical only).
4. Update all reports to join GL Entry -> Cost Code -> BOQ Item -> BOQ Item Stage.

### Appendix B: Competitor Benchmarks

| Platform | Cost Object Strategy | Stage/Phase Handling | Lifecycle Gating |
|----------|---------------------|---------------------|------------------|
| **SAP PS/S4HANA** | WBS Elements + Network Activities (low cardinality) | Activities broken by location/phase | Project status controls posting |
| **Procore** | Budget Codes (unique per line) | SOV organized by phase/location/trade | Budget approval required |
| **Tirzok ERP** | BOQ + Phase Entries | Phase Entries per BOQ line | Status-based workflow |
| **Our Target (Phase 1)** | BOQ Item as dimension (high cardinality) | BOQ Item Stage (operational) | Draft/Pricing block, Frozen/Locked allow |
| **Our Target (Phase 2)** | Cost Code as dimension (low cardinality) | BOQ Item Stage + Site Measurement Entry | Same + IPC workflow |

### Appendix C: Glossary

| Term | Definition |
|------|------------|
| **BOQ** | Bill of Quantities — contract document listing work items, quantities, and rates |
| **BOQ Item Stage** | Operational breakdown of a BOQ Item into execution slices (floor, phase, zone) |
| **Accounting Dimension** | ERPNext feature adding analytical fields to GL Entry for reporting |
| **IPC** | Interim Payment Certificate — monthly progress billing document |
| **WBS** | Work Breakdown Structure — hierarchical decomposition of project work |
| **ADR** | Architectural Decision Record — documented design decision with consequences |
| **Idempotent** | Operation that produces the same result whether run once or multiple times |
| **Cardinality** | Number of distinct values in a dataset — high cardinality = many unique values |

---

## Document Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Head of Engineering | | | |
| Project Manager | | | |
| General Manager | | | |
| Lead Developer | | | |

---

*End of Master Plan — Single Source of Truth*

*Version: 1.0 | Approved for Implementation | All prior documents superseded for development purposes*
