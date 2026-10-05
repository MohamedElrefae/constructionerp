"""Bilingual print formats for transactional documents (Wave-2b).

Run with:
  bench --site v16.localhost run-tests --app construction \\
      --module construction.tests.test_bilingual_transaction_print

Covers:
- The four shipped Print Format JSON definitions (Purchase Order, Sales Invoice,
  Stock Entry, Material Request) parse, are self-consistent, and use the
  registered ``bdi_join`` filter rather than raw string concatenation.
- Registration of those formats on the live site via
  ``construction.install.setup_transaction_print_formats`` (idempotent).
- End-to-end rendering through ``frappe.get_print`` against live Arabic master
  data (Company ``Elrefae`` / شركة الرفاعي للمقاولات العامة, Customer
  ``Prestiga-Biz`` / بريستيجا بيز, Item ``SUBCONCRETE-001``, UOM ``M3``).
- Graceful monolingual fallback with no dangling `` / `` separator when an
  entity has no Arabic value.
- Single HTML escaping of values containing ``&`` (no double escaping).
- Zero-edit guard for the byte-frozen surfaces named in the briefing.
"""

import json
import subprocess
import unittest
from pathlib import Path
from uuid import uuid4

import frappe
from frappe.utils import add_days, today

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "234c02446deb3dd10567bfcbc995732ccd8cc19e"

PRINT_FORMAT_SLUGS = (
    "bilingual_purchase_order",
    "bilingual_sales_invoice",
    "bilingual_stock_entry",
    "bilingual_material_request",
)

PRINT_FORMATS = {
    "bilingual_purchase_order": ("Construction Bilingual Purchase Order", "Purchase Order"),
    "bilingual_sales_invoice": ("Construction Bilingual Sales Invoice", "Sales Invoice"),
    "bilingual_stock_entry": ("Construction Bilingual Stock Entry", "Stock Entry"),
    "bilingual_material_request": ("Construction Bilingual Material Request", "Material Request"),
}

FROZEN_SURFACES = (
    "construction/services/bilingual_service.py",
    "construction/searchable_dropdown/api/search.py",
    "construction/data/bilingual/bilingual_registry.json",
    "construction/fixtures/uom.json",
)

COMPANY = "Elrefae"
COMPANY_AR = "شركة الرفاعي للمقاولات العامة"
CUSTOMER = "Prestiga-Biz"
CUSTOMER_AR = "بريستيجا بيز"
STOCK_ITEM = "SUBCONCRETE-001"
UOM = "M3"
UOM_AR = "متر مكعب"
WAREHOUSE = "Stores - E"
DEPARTMENT = "Accounts - E"
DEPARTMENT_AR = "الحسابات"


def _render(doctype, name, print_format):
    """Render a document through the real printview path."""
    return frappe.get_print(doctype, name, print_format=print_format)


def _bdi(value):
    return f"<bdi>{value}</bdi>"


def _pair(english, arabic):
    return f"{_bdi(english)} / {_bdi(arabic)}"


class TestBilingualTransactionPrint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._project = None
        cls._supplier = None
        cls._created = []

        cls._project = frappe.get_doc(
            {
                "doctype": "Project",
                "project_name": f"CT Print & Test {uuid4().hex[:6]}",
                "company": COMPANY,
                "project_name_ar": "مشروع تجربة الطباعة",
            }
        ).insert(ignore_permissions=True)

        cls._supplier = frappe.get_doc(
            {
                "doctype": "Supplier",
                "supplier_name": f"CT Print Supplier {uuid4().hex[:6]}",
                "supplier_group": "All Supplier Groups",
                "supplier_type": "Company",
                "supplier_name_in_arabic": "مورد تجربة الطباعة",
            }
        ).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        for doctype, name in reversed(cls._created):
            if frappe.db.exists(doctype, name):
                try:
                    frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
                except Exception:
                    frappe.db.rollback()
        cls._created = []
        for doctype, name in (("Supplier", getattr(cls._supplier, "name", None)),
                              ("Project", getattr(cls._project, "name", None))):
            if name and frappe.db.exists(doctype, name):
                try:
                    frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
                except Exception:
                    frappe.db.rollback()
        frappe.db.commit()

    def _track(self, doctype, doc):
        type(self)._created.append((doctype, doc.name))
        return doc

    def _make(self, payload):
        doc = frappe.get_doc(payload)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return self._track(doc.doctype, doc)

    # ------------------------------------------------------------------
    # Shipped artefacts
    # ------------------------------------------------------------------

    def test_print_format_json_files_are_well_formed(self):
        for slug in PRINT_FORMAT_SLUGS:
            path = REPO_ROOT / "construction" / "print_format" / slug / f"{slug}.json"
            self.assertTrue(path.is_file(), f"Missing print format definition: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
            expected_name, expected_doc_type = PRINT_FORMATS[slug]
            self.assertEqual(data["doctype"], "Print Format")
            self.assertEqual(data["name"], expected_name)
            self.assertEqual(data["doc_type"], expected_doc_type)
            self.assertEqual(data["print_format_type"], "Jinja")
            self.assertEqual(data["custom_format"], 1)
            self.assertEqual(data["disabled"], 0)
            self.assertIn("| bdi_join(", data["html"])
            self.assertIn('<div class="ct-doc">', data["html"])

    def test_print_formats_registered_and_idempotent(self):
        from construction.install import setup_transaction_print_formats

        for slug, (name, doc_type) in PRINT_FORMATS.items():
            self.assertTrue(frappe.db.exists("Print Format", name), f"{name} not installed")
            stored = frappe.get_doc("Print Format", name)
            self.assertEqual(stored.doc_type, doc_type)
            self.assertEqual(stored.custom_format, 1)
            self.assertEqual(stored.print_format_type, "Jinja")
            self.assertEqual(stored.disabled, 0)
            path = REPO_ROOT / "construction" / "print_format" / slug / f"{slug}.json"
            self.assertEqual(stored.html, json.loads(path.read_text(encoding="utf-8"))["html"])

        before = frappe.db.count("Print Format")
        setup_transaction_print_formats()
        frappe.db.commit()
        setup_transaction_print_formats()
        frappe.db.commit()
        self.assertEqual(frappe.db.count("Print Format"), before)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def test_render_purchase_order_bilingual(self):
        po = self._make(
            {
                "doctype": "Purchase Order",
                "supplier": self._supplier.name,
                "company": COMPANY,
                "transaction_date": today(),
                "schedule_date": add_days(today(), 7),
                "project": self._project.name,
                "department": DEPARTMENT,
                "items": [
                    {
                        "item_code": STOCK_ITEM,
                        "qty": 10,
                        "uom": UOM,
                        "rate": 100,
                        "warehouse": WAREHOUSE,
                    }
                ],
            }
        )
        html = _render("Purchase Order", po.name, PRINT_FORMATS["bilingual_purchase_order"][0])

        self.assertIn(_pair(COMPANY, COMPANY_AR), html)
        self.assertIn(_pair(self._supplier.name, "مورد تجربة الطباعة"), html)
        self.assertIn(_pair(self._project.name, "مشروع تجربة الطباعة"), html)
        self.assertIn(_pair(DEPARTMENT, DEPARTMENT_AR), html)
        self.assertIn(_pair(STOCK_ITEM, "مقاولة باطن لأعمال الخرسانة"), html)
        self.assertIn(_pair(UOM, UOM_AR), html)
        self.assertIn(_pair("Purchase Order", "أمر شراء"), html)
        self.assertIn(_pair("Item", "الصنف"), html)
        self.assertIn("<bdi>", html)
        self.assertGreaterEqual(html.count("<bdi>"), 12)

    def test_render_sales_invoice_bilingual(self):
        si = self._make(
            {
                "doctype": "Sales Invoice",
                "customer": CUSTOMER,
                "company": COMPANY,
                "posting_date": today(),
                "due_date": add_days(today(), 30),
                "items": [{"item_code": "Consulting", "qty": 1, "rate": 100}],
            }
        )
        html = _render("Sales Invoice", si.name, PRINT_FORMATS["bilingual_sales_invoice"][0])

        self.assertIn(_pair(COMPANY, COMPANY_AR), html)
        self.assertIn(_pair(CUSTOMER, CUSTOMER_AR), html)
        self.assertIn(_pair("Consulting", "استشارات"), html)
        self.assertIn(_pair("Tax Invoice", "فاتورة ضريبية"), html)

    def test_render_stock_entry_bilingual(self):
        se = self._make(
            {
                "doctype": "Stock Entry",
                "stock_entry_type": "Material Issue",
                "company": COMPANY,
                "posting_date": today(),
                "items": [
                    {
                        "item_code": STOCK_ITEM,
                        "qty": 2,
                        "uom": UOM,
                        "s_warehouse": WAREHOUSE,
                        "basic_rate": 25,
                        "allow_zero_valuation_rate": 1,
                    }
                ],
            }
        )
        html = _render("Stock Entry", se.name, PRINT_FORMATS["bilingual_stock_entry"][0])

        self.assertIn(_pair(COMPANY, COMPANY_AR), html)
        self.assertIn(_pair("Material Issue", "صرف مواد"), html)
        self.assertIn(_pair(STOCK_ITEM, "مقاولة باطن لأعمال الخرسانة"), html)
        self.assertIn(_pair(UOM, UOM_AR), html)
        self.assertIn(_pair("Purpose", "الغرض"), html)

    def test_render_material_request_bilingual(self):
        mr = self._make(
            {
                "doctype": "Material Request",
                "material_request_type": "Purchase",
                "company": COMPANY,
                "transaction_date": today(),
                "schedule_date": add_days(today(), 7),
                "items": [
                    {"item_code": STOCK_ITEM, "qty": 5, "uom": UOM, "warehouse": WAREHOUSE}
                ],
            }
        )
        html = _render("Material Request", mr.name, PRINT_FORMATS["bilingual_material_request"][0])

        self.assertIn(_pair(COMPANY, COMPANY_AR), html)
        self.assertIn(_pair("Purchase", "شراء"), html)
        self.assertIn(_pair(STOCK_ITEM, "مقاولة باطن لأعمال الخرسانة"), html)
        self.assertIn(_pair(UOM, UOM_AR), html)
        self.assertIn(_pair("Material Request", "طلب مواد"), html)

    def test_fallback_has_no_dangling_separator(self):
        """An entity with no Arabic value renders monolingually, never with a stray ' / '."""
        plain_supplier = frappe.get_doc(
            {
                "doctype": "Supplier",
                "supplier_name": f"CT Plain Supplier {uuid4().hex[:6]}",
                "supplier_group": "All Supplier Groups",
                "supplier_type": "Company",
            }
        ).insert(ignore_permissions=True)
        self._track("Supplier", plain_supplier)
        plain_project = frappe.get_doc(
            {
                "doctype": "Project",
                "project_name": f"CT Plain Project {uuid4().hex[:6]}",
                "company": COMPANY,
            }
        ).insert(ignore_permissions=True)
        self._track("Project", plain_project)

        po = self._make(
            {
                "doctype": "Purchase Order",
                "supplier": plain_supplier.name,
                "company": COMPANY,
                "transaction_date": today(),
                "schedule_date": add_days(today(), 7),
                "project": plain_project.name,
                "items": [
                    {
                        "item_code": STOCK_ITEM,
                        "qty": 1,
                        "uom": UOM,
                        "rate": 10,
                        "warehouse": WAREHOUSE,
                    }
                ],
            }
        )
        html = _render("Purchase Order", po.name, PRINT_FORMATS["bilingual_purchase_order"][0])

        self.assertIn(_bdi(plain_supplier.name), html)
        self.assertNotIn(f"{_bdi(plain_supplier.name)} / ", html)
        self.assertNotIn(f"{_bdi(plain_project.name)} / ", html)
        self.assertNotIn("/ </bdi>", html)
        self.assertNotIn("<bdi></bdi>", html)
        self.assertNotIn("None / ", html)

        # The company still has an Arabic value, so that pair must remain bilingual.
        self.assertIn(_pair(COMPANY, COMPANY_AR), html)

    def test_single_escaping_of_ampersand_values(self):
        """Values containing '&' and '<' are escaped exactly once in the rendered output."""
        amp_supplier = frappe.get_doc(
            {
                "doctype": "Supplier",
                "supplier_name": f"CT Print & Supplier {uuid4().hex[:6]}",
                "supplier_group": "All Supplier Groups",
                "supplier_type": "Company",
            }
        ).insert(ignore_permissions=True)
        self._track("Supplier", amp_supplier)

        po = self._make(
            {
                "doctype": "Purchase Order",
                "supplier": amp_supplier.name,
                "company": COMPANY,
                "transaction_date": today(),
                "schedule_date": add_days(today(), 7),
                "items": [
                    {
                        "item_code": STOCK_ITEM,
                        "qty": 1,
                        "uom": UOM,
                        "rate": 10,
                        "warehouse": WAREHOUSE,
                        "description": "Sand & Gravel <Fine>",
                    }
                ],
            }
        )
        html = _render("Purchase Order", po.name, PRINT_FORMATS["bilingual_purchase_order"][0])

        # bdi_join escapes the '&' once inside <bdi>
        self.assertIn("<bdi>CT Print &amp; Supplier", html)
        # a raw template expression escapes '&' once, and never re-emits a raw tag
        self.assertIn("Sand &amp; Gravel", html)
        self.assertNotIn("<Fine>", html)
        self.assertNotIn("&amp;amp;", html)
        self.assertNotIn("&amp;lt;", html)
        self.assertNotIn("&lt;bdi&gt;", html)

    def test_no_raw_bilingual_concatenation_without_bdi_join(self):
        for slug in PRINT_FORMAT_SLUGS:
            path = REPO_ROOT / "construction" / "print_format" / slug / f"{slug}.json"
            html = json.loads(path.read_text(encoding="utf-8"))["html"]
            self.assertGreaterEqual(
                html.count("| bdi_join("),
                8,
                f"{slug} uses too few bdi_join calls",
            )
            self.assertNotIn('"{{"', html)
            self.assertNotIn("doc.company +", html)

    # ------------------------------------------------------------------
    # Frozen surfaces
    # ------------------------------------------------------------------

    def test_frozen_surfaces_byte_identical_to_base_commit(self):
        for rel_path in FROZEN_SURFACES:
            expected = subprocess.check_output(
                ["git", "show", f"{BASE_COMMIT}:{rel_path}"],
                cwd=str(REPO_ROOT),
            )
            actual = (REPO_ROOT / rel_path).read_bytes()
            self.assertEqual(
                actual,
                expected,
                f"Frozen surface {rel_path} was modified by this work item!",
            )


if __name__ == "__main__":
    unittest.main()
