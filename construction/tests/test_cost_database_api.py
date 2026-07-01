import io

import frappe
from frappe.tests.utils import FrappeTestCase


class TestCostDatabaseAPI(FrappeTestCase):
    """Tests for cost database API endpoints and template generation."""

    def setUp(self):
        self.company = frappe.db.get_value("Company", {}, "name") or "Test Quality Company"

    def tearDown(self):
        frappe.db.rollback()

    def _load_workbook(self, content):
        import openpyxl
        return openpyxl.load_workbook(io.BytesIO(content), data_only=True)

    def test_generate_blank_template_has_required_sheets(self):
        """Blank template contains Resources, BOQItemTemplates, RateAnalysis, PriceHistory, and _Metadata sheets."""
        from construction.services.cost_database_service import generate_cost_database_template

        content = generate_cost_database_template(mode="blank")
        wb = self._load_workbook(content)
        sheet_names = {s.title for s in wb.worksheets}
        self.assertIn("Resources", sheet_names)
        self.assertIn("BOQItemTemplates", sheet_names)
        self.assertIn("RateAnalysis", sheet_names)
        self.assertIn("PriceHistory", sheet_names)
        self.assertIn("_Metadata", sheet_names)

        # Metadata sheet is hidden
        self.assertEqual(wb["_Metadata"].sheet_state, "hidden")

    def test_generate_blank_template_headers(self):
        """Blank template sheets have the expected canonical headers."""
        from construction.services.cost_database_service import generate_cost_database_template

        content = generate_cost_database_template(mode="blank")
        wb = self._load_workbook(content)

        resources_headers = [c.value for c in wb["Resources"][1]]
        self.assertIn("resource_code", resources_headers)
        self.assertIn("resource_type", resources_headers)
        self.assertIn("cost_stream", resources_headers)
        self.assertIn("unit_price_egp", resources_headers)

        template_headers = [c.value for c in wb["BOQItemTemplates"][1]]
        self.assertIn("template_name", template_headers)
        self.assertIn("description_en", template_headers)
        self.assertIn("overhead_pct", template_headers)
        self.assertIn("profit_pct", template_headers)

        rate_headers = [c.value for c in wb["RateAnalysis"][1]]
        self.assertIn("template_name", rate_headers)
        self.assertIn("resource_code", rate_headers)
        self.assertIn("qty_per_boq_unit", rate_headers)
        self.assertIn("cost_rate", rate_headers)
        self.assertIn("rate_source", rate_headers)

    def test_generate_sample_template_contains_data(self):
        """Sample template is pre-filled with illustrative resources, templates, and rate analysis."""
        from construction.services.cost_database_service import generate_cost_database_template

        content = generate_cost_database_template(mode="sample")
        wb = self._load_workbook(content)

        resources_rows = list(wb["Resources"].iter_rows(min_row=2, values_only=True))
        self.assertGreater(len(resources_rows), 0)
        resource_codes = {r[0] for r in resources_rows if r[0]}
        self.assertIn("MAT-CEM-001", resource_codes)

        template_rows = list(wb["BOQItemTemplates"].iter_rows(min_row=2, values_only=True))
        self.assertGreater(len(template_rows), 0)
        template_names = {r[0] for r in template_rows if r[0]}
        self.assertIn("01-CONC-PLN", template_names)

        rate_rows = list(wb["RateAnalysis"].iter_rows(min_row=2, values_only=True))
        self.assertGreater(len(rate_rows), 0)
        rate_templates = {r[0] for r in rate_rows if r[0]}
        self.assertIn("01-CONC-PLN", rate_templates)

    def test_download_cost_database_template_api_blank(self):
        """API endpoint returns a binary .xlsx response for blank mode."""
        from construction.api.cost_database_api import download_cost_database_template

        download_cost_database_template(mode="blank")
        self.assertEqual(frappe.response["filename"], "cost_database_template_blank.xlsx")
        self.assertEqual(
            frappe.response["content_type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIsInstance(frappe.response["filecontent"], bytes)
        self.assertGreater(len(frappe.response["filecontent"]), 0)

    def test_download_cost_database_template_api_sample(self):
        """API endpoint returns a binary .xlsx response for sample mode."""
        from construction.api.cost_database_api import download_cost_database_template

        download_cost_database_template(mode="sample")
        self.assertEqual(frappe.response["filename"], "cost_database_template_sample.xlsx")
        self.assertIsInstance(frappe.response["filecontent"], bytes)

        wb = self._load_workbook(frappe.response["filecontent"])
        self.assertGreater(wb["Resources"].max_row, 1)

    def test_download_cost_database_template_api_invalid_mode(self):
        """API endpoint rejects invalid mode values."""
        from construction.api.cost_database_api import download_cost_database_template

        with self.assertRaises(frappe.ValidationError):
            download_cost_database_template(mode="invalid")

    def _build_test_excel(self):
        import openpyxl

        wb = openpyxl.Workbook()
        resources = wb.active
        resources.title = "Resources"
        resources.append([
            "resource_code", "resource_type", "cost_stream", "name_en", "name_ar",
            "uom", "unit_price_egp", "currency", "exchange_rate", "company",
            "region", "price_date", "source_name",
        ])
        resources.append([
            "API-CEM-001", "Material", "M", "API Cement", "أسمنت API",
            "Ton", 3600, "EGP", 1.0, self.company,
            "Cairo", "2026-06-01", "Test Import",
        ])

        templates = wb.create_sheet("BOQItemTemplates")
        templates.append([
            "template_name", "description_en", "description_ar", "uom",
            "overhead_pct", "profit_pct", "currency",
        ])
        templates.append([
            "API-CONC-PLN", "API Plain Concrete", "خرسانة عادية API",
            "m³", 12, 8, "EGP",
        ])

        rate = wb.create_sheet("RateAnalysis")
        rate.append([
            "template_name", "resource_code", "qty_per_boq_unit", "wastage_pct",
            "cost_stream", "cost_rate", "rate_source",
        ])
        rate.append(["API-CONC-PLN", "API-CEM-001", 0.25, 3, "M", 3600, "Import"])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.read()

    def test_import_cost_database_api_dry_run(self):
        """Import API endpoint validates a file in dry-run mode without creating records."""
        from construction.api.cost_database_api import import_cost_database

        content = self._build_test_excel()

        # Simulate a file upload in form_dict
        class _FakeFile:
            filename = "test_import.xlsx"
            stream = io.BytesIO(content)

        frappe.request = frappe._dict(files={"file": _FakeFile()})
        frappe.form_dict = frappe._dict(
            company=self.company,
            dry_run="1",
            auto_submit="0",
        )

        result = import_cost_database()
        self.assertTrue(result["success"])
        self.assertTrue(result["dry_run"])
        self.assertEqual(len(result["records_created"]["items"]), 0)
