# Handover & Briefing Letter: Transactional Documents Bilingual Print Formats

**To:** OpenCode Autonomous Agent / Subagent Session (Session A)  
**From:** Antigravity Engineering Lane (Lead Verifier & Committer)  
**Date:** 2026-10-05  
**Subject:** Mission Briefing: Wave-2b Transactional Documents Bilingual Print Formats  
**Target Repository:** `/home/mohamed/frappe-bench/apps/construction`  
**Target Site:** `v16.localhost`  
**Base Commit:** `234c024` (`develop` branch)  
**Work Item Path:** `docs/ai/work-items/bilingual-transaction-print-formats/`  

---

## 1. Executive Summary & Objective

You are tasked with implementing and validating **Bilingual Jinja Print Formats** for the primary construction transactional documents.

With all master data now 100% Arabic-populated on `v16.localhost` (Company `شركة الرفاعي للمقاولات العامة`, 14 Departments, 5 Warehouses, 5 Projects, 3 Cost Centers, 8 Items, Customer `بريستيجا بيز`, and 45 active UOMs), standard business documents can now produce high-quality dual-language (English / العربية) PDF and print outputs.

Your mission is to:
1. Create 4 dedicated bilingual print formats in `apps/construction` for:
   - **`Purchase Order`** (`Construction Bilingual Purchase Order`)
   - **`Sales Invoice`** (`Construction Bilingual Sales Invoice`)
   - **`Stock Entry`** (`Construction Bilingual Stock Entry`)
   - **`Material Request`** (`Construction Bilingual Material Request`)
2. Implement robust bidirectional isolation using `<bdi>` tags and the registered `bdi_join` filter to prevent numeral and punctuation inversion.
3. Provide automated test coverage in `construction/tests/test_bilingual_transaction_print.py` verifying HTML rendering, field resolution, and fallback safety.
4. Prepare full evidence logs and manifest; leave git staging and commit to Antigravity as the independent verifier.

---

## 2. Invariants & Governance Rules

1. **Role Division:**
   - OpenCode implements, runs local checks, and compiles evidence.
   - Antigravity independently audits, verifies gates, checks manifest digests, and performs the local commit.
2. **Owner Confidentiality Policy (`docs/ai/OWNER_CONFIDENTIALITY_POLICY.md`):**
   - Strictly local execution. Never push to remote git repositories or trigger public CI.
3. **Zero Vendor Code Edits:**
   - Absolute prohibition against modifying `apps/frappe` or `apps/erpnext`. All print format definitions and templates live in `apps/construction`.
4. **Frozen Surfaces:**
   - `bilingual_service.py`, `searchable_dropdown/api/search.py`, `bilingual_registry.json`, and `uom.json` are byte-frozen.
5. **Bidi Isolation (`bdi_join`):**
   - Use `{{ [field_en, field_ar] | bdi_join(" / ") }}` for dual-language labels. Never concatenate raw strings without `<bdi>` wrapping.
6. **Graceful Fallbacks:**
   - If an entity lacks an Arabic translation (e.g. ad-hoc item or unpopulated vendor), render the English name cleanly without dangling separators (` / `).
7. **Ephemeral Redis Protocol:**
   - Redis ports 11000/13000 should only run during test execution and MUST be terminated immediately after. Never commit `dump.rdb`.

---

## 3. Specifications for the 4 Print Formats

All print formats reside in `construction/print_format/<format_slug>/<format_slug>.json` (or `.html` alongside):

### 1. `bilingual_purchase_order` (`Purchase Order`)
- **Header:**
  - Company: `{{ [doc.company, frappe.db.get_value("Company", doc.company, "company_name_ar")] | bdi_join(" / ") }}`
  - Supplier: `{{ [doc.supplier, doc.supplier_name_in_arabic or frappe.db.get_value("Supplier", doc.supplier, "supplier_name_ar")] | bdi_join(" / ") }}`
  - Project: `{{ [doc.project, frappe.db.get_value("Project", doc.project, "project_name_ar")] | bdi_join(" / ") }}`
  - Department: `{{ [doc.department, frappe.db.get_value("Department", doc.department, "department_name_ar")] | bdi_join(" / ") }}`
  - Order Number (`doc.name`), Transaction Date (`doc.transaction_date`), Required Date (`doc.schedule_date`).
- **Table Columns:**
  - `# / م`
  - `Item / الصنف` (`{{ [row.item_name, frappe.db.get_value("Item", row.item_code, "item_name_ar")] | bdi_join(" / ") }}`)
  - `Description / الوصف`
  - `Qty / الكمية`
  - `Unit / الوحدة` (`{{ [row.uom, frappe.db.get_value("UOM", row.uom, "uom_name_ar")] | bdi_join(" / ") }}`)
  - `Rate / السعر`
  - `Amount / الإجمالي`
- **Summary:** Net Total, Taxes / Charges, Grand Total, Currency.

### 2. `bilingual_sales_invoice` (`Sales Invoice`)
- **Header:**
  - Company: `{{ [doc.company, frappe.db.get_value("Company", doc.company, "company_name_ar")] | bdi_join(" / ") }}`
  - Customer: `{{ [doc.customer_name, doc.customer_name_in_arabic or frappe.db.get_value("Customer", doc.customer, "customer_name_ar")] | bdi_join(" / ") }}`
  - Invoice No (`doc.name`), Posting Date (`doc.posting_date`), Due Date (`doc.due_date`), Project.
- **Table Columns:**
  - `# / م`, Item, Description, Qty, Unit (`[row.uom, uom_name_ar]`), Rate, Net Amount.
- **Summary:** Net Total, VAT Amount, Grand Total (Tax Invoice layout).

### 3. `bilingual_stock_entry` (`Stock Entry`)
- **Header:**
  - Company, Purpose (`Material Issue` / `صرف مواد`, `Material Transfer` / `تحويل مواد`, `Material Receipt` / `استلام مواد`), Posting Date, Project.
  - Source Warehouse (`from_warehouse` + Arabic name) & Target Warehouse (`to_warehouse` + Arabic name).
- **Table Columns:**
  - Item, Source WH, Target WH, Qty, Unit (`[row.uom, uom_name_ar]`), Basic Rate, Amount.
- **Summary:** Total Qty, Total Valuation Amount.

### 4. `bilingual_material_request` (`Material Request`)
- **Header:**
  - Company, Request Type (`Purchase`, `Material Transfer`, etc.), Required Date (`schedule_date`), Department, Project.
- **Table Columns:**
  - Item, Required Qty, Unit (`[row.uom, uom_name_ar]`), Target Warehouse.

---

## 4. Required Deliverables for this Session

Inside `docs/ai/work-items/bilingual-transaction-print-formats/`:
1. `SCOPE.md` — scope descriptor and decision record.
2. `construction/print_format/bilingual_purchase_order/bilingual_purchase_order.json`
3. `construction/print_format/bilingual_sales_invoice/bilingual_sales_invoice.json`
4. `construction/print_format/bilingual_stock_entry/bilingual_stock_entry.json`
5. `construction/print_format/bilingual_material_request/bilingual_material_request.json`
6. `construction/tests/test_bilingual_transaction_print.py` — test suite asserting:
   - Rendering of all 4 formats with live Arabic masters (`Elrefae`, `Prestiga-Biz`, `M3`, etc.).
   - `<bdi>` tag presence and single-escaping.
   - Clean fallback when Arabic field is None.
7. `evidence/test-rendering.log` — execution log of print rendering tests.
8. `evidence/gates.log` — 6 lints + reconciler (19/19) execution log.
9. `evidence/MANIFEST.json` — manifest #32 pinning all artefacts.

---

## 5. Verification & Handover Instructions

Once you complete implementation and verify the tests:
- Do **NOT** push to remote.
- Ensure all ephemeral Redis processes are killed.
- Signal completion so Antigravity can run independent verification and commit.
