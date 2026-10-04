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

    def _build_test_excel(self, rate=3600):
        import openpyxl

        wb = openpyxl.Workbook()
        resources = wb.active
        resources.title = "Resources"
        resources.append(
            [
                "resource_code",
                "resource_type",
                "cost_stream",
                "name_en",
                "name_ar",
                "uom",
                "unit_price_egp",
                "currency",
                "exchange_rate",
                "company",
                "region",
                "price_date",
                "source_name",
            ]
        )
        resources.append(
            [
                "API-CEM-001",
                "Material",
                "M",
                "API Cement",
                "أسمنت API",
                "Ton",
                rate,
                "EGP",
                1.0,
                self.company,
                "Cairo",
                "2026-06-01",
                "Test Import",
            ]
        )

        templates = wb.create_sheet("BOQItemTemplates")
        templates.append(
            [
                "template_name",
                "description_en",
                "description_ar",
                "category",
                "uom",
                "overhead_pct",
                "profit_pct",
                "currency",
            ]
        )
        templates.append(
            [
                "API-CONC-PLN",
                "API Plain Concrete",
                "خرسانة عادية API",
                "Concrete Works",
                "m³",
                12,
                8,
                "EGP",
            ]
        )

        rate_sheet = wb.create_sheet("RateAnalysis")
        rate_sheet.append(
            [
                "template_name",
                "resource_code",
                "qty_per_boq_unit",
                "wastage_pct",
                "cost_stream",
                "cost_rate",
                "rate_source",
            ]
        )
        rate_sheet.append(["API-CONC-PLN", "API-CEM-001", 0.25, 3, "M", rate, "Import"])

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

    def test_import_rejects_file_over_byte_limit_before_service_call(self):
        from construction.api import cost_database_api

        class _BoundedStream:
            def __init__(self):
                self.requested = None

            def read(self, size=-1):
                self.requested = size
                return b"x" * size

        stream = _BoundedStream()

        class _FakeFile:
            filename = "too_large.xlsx"

            def __init__(self, upload_stream):
                self.stream = upload_stream

        old_limit = cost_database_api.COST_DATABASE_MAX_FILE_SIZE_BYTES
        try:
            cost_database_api.COST_DATABASE_MAX_FILE_SIZE_BYTES = 4
            frappe.request = frappe._dict(files={"file": _FakeFile(stream)})
            frappe.form_dict = frappe._dict(company=self.company)
            with self.assertRaises(frappe.ValidationError):
                cost_database_api.import_cost_database()
            self.assertEqual(stream.requested, 5)
        finally:
            cost_database_api.COST_DATABASE_MAX_FILE_SIZE_BYTES = old_limit

    def test_import_rejects_xlsx_resource_bounds_before_mutation(self):
        from construction.services import cost_database_service
        from construction.services.boq_import_service import BOQImportService

        content = self._build_test_excel()
        old_file_limit = cost_database_service.COST_DATABASE_MAX_FILE_SIZE_BYTES
        old_zip_limit = BOQImportService.MAX_ZIP_MEMBERS
        old_expanded_limit = BOQImportService.MAX_UNCOMPRESSED_SIZE
        old_worksheet_xml_limit = BOQImportService.MAX_WORKSHEET_XML_BYTES
        old_row_limit = BOQImportService.MAX_ROWS
        old_col_limit = BOQImportService.MAX_COLS
        old_import_rows = cost_database_service.COST_DATABASE_MAX_IMPORTED_ROWS
        try:
            cases = (
                ("COST_DATABASE_MAX_FILE_SIZE_BYTES", cost_database_service, 1),
                ("MAX_ZIP_MEMBERS", BOQImportService, 1),
                ("MAX_UNCOMPRESSED_SIZE", BOQImportService, 1),
                ("MAX_WORKSHEET_XML_BYTES", BOQImportService, 1),
                ("MAX_ROWS", BOQImportService, 1),
                ("MAX_COLS", BOQImportService, 1),
                ("COST_DATABASE_MAX_IMPORTED_ROWS", cost_database_service, 1),
            )
            for attr, owner, limit in cases:
                with self.subTest(bound=attr):
                    setattr(owner, attr, limit)
                    result = cost_database_service.import_cost_database_from_excel(
                        file_content=content,
                        file_name="bounded.xlsx",
                        company=self.company,
                    )
                    self.assertFalse(result["success"])
                    self.assertTrue(result["errors"])
                    self.assertEqual(result["records_created"]["items"], [])
                    if attr == "COST_DATABASE_MAX_FILE_SIZE_BYTES":
                        cost_database_service.COST_DATABASE_MAX_FILE_SIZE_BYTES = old_file_limit
                    elif attr == "MAX_ZIP_MEMBERS":
                        BOQImportService.MAX_ZIP_MEMBERS = old_zip_limit
                    elif attr == "MAX_UNCOMPRESSED_SIZE":
                        BOQImportService.MAX_UNCOMPRESSED_SIZE = old_expanded_limit
                    elif attr == "MAX_WORKSHEET_XML_BYTES":
                        BOQImportService.MAX_WORKSHEET_XML_BYTES = old_worksheet_xml_limit
                    elif attr == "MAX_ROWS":
                        BOQImportService.MAX_ROWS = old_row_limit
                    elif attr == "MAX_COLS":
                        BOQImportService.MAX_COLS = old_col_limit
                    elif attr == "COST_DATABASE_MAX_IMPORTED_ROWS":
                        cost_database_service.COST_DATABASE_MAX_IMPORTED_ROWS = old_import_rows
        finally:
            cost_database_service.COST_DATABASE_MAX_FILE_SIZE_BYTES = old_file_limit
            BOQImportService.MAX_ZIP_MEMBERS = old_zip_limit
            BOQImportService.MAX_UNCOMPRESSED_SIZE = old_expanded_limit
            BOQImportService.MAX_WORKSHEET_XML_BYTES = old_worksheet_xml_limit
            BOQImportService.MAX_ROWS = old_row_limit
            BOQImportService.MAX_COLS = old_col_limit
            cost_database_service.COST_DATABASE_MAX_IMPORTED_ROWS = old_import_rows

    def test_import_rejects_too_many_worksheets(self):
        import openpyxl

        from construction.services import cost_database_service

        wb = openpyxl.load_workbook(io.BytesIO(self._build_test_excel()))
        for index in range(8):
            wb.create_sheet(f"Extra{index}")
        buf = io.BytesIO()
        wb.save(buf)
        wb.close()

        result = cost_database_service.import_cost_database_from_excel(
            file_content=buf.getvalue(),
            file_name="many_sheets.xlsx",
            company=self.company,
            dry_run=True,
        )
        self.assertFalse(result["success"])
        self.assertIn("worksheets", result["errors"][0])

    def _rewrite_first_worksheet_part(self, content, declared_dimension):
        import zipfile

        output = io.BytesIO()
        dimension_rewritten = False
        relationship_rewritten = False
        content_type_rewritten = False
        with (
            zipfile.ZipFile(io.BytesIO(content), "r") as source,
            zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target,
        ):
            for info in source.infolist():
                name = info.filename
                data = source.read(name)
                if name == "xl/worksheets/sheet1.xml":
                    name = "xl/worksheets/custom-resource-data.xml"
                    self.assertEqual(data.count(b'ref="A1:M2"'), 1)
                    data = data.replace(b'ref="A1:M2"', f'ref="{declared_dimension}"'.encode())
                    dimension_rewritten = True
                elif name == "xl/_rels/workbook.xml.rels":
                    for old_target in (
                        b'Target="worksheets/sheet1.xml"',
                        b'Target="/xl/worksheets/sheet1.xml"',
                    ):
                        if old_target in data:
                            data = data.replace(
                                old_target,
                                old_target.replace(b"sheet1.xml", b"custom-resource-data.xml"),
                            )
                            relationship_rewritten = True
                elif name == "[Content_Types].xml":
                    old_part_name = b"/xl/worksheets/sheet1.xml"
                    content_type_rewritten = old_part_name in data
                    data = data.replace(old_part_name, b"/xl/worksheets/custom-resource-data.xml")
                target.writestr(name, data)
        self.assertTrue(dimension_rewritten, "fixture did not rewrite the worksheet dimension")
        self.assertTrue(relationship_rewritten, "fixture did not rewrite the worksheet relationship")
        self.assertTrue(content_type_rewritten, "fixture did not update the worksheet content type")
        return output.getvalue()

    def test_import_caps_actual_nonempty_rows_across_required_sheets(self):
        from construction.services import cost_database_service

        content = self._build_test_excel()
        wb = self._load_workbook(content)
        imported_nonempty_rows = sum(
            sum(
                any(value not in (None, "") for value in row)
                for row in wb[name].iter_rows(min_row=2, values_only=True)
            )
            for name in ("Resources", "BOQItemTemplates", "RateAnalysis")
        )
        wb.close()
        self.assertEqual(imported_nonempty_rows, 3)

        old_limit = cost_database_service.COST_DATABASE_MAX_IMPORTED_ROWS
        try:
            cost_database_service.COST_DATABASE_MAX_IMPORTED_ROWS = imported_nonempty_rows - 1
            rejected = cost_database_service.import_cost_database_from_excel(
                file_content=content,
                file_name="row_cap.xlsx",
                company=self.company,
                dry_run=True,
            )
            self.assertFalse(rejected["success"])
            self.assertIn("imported-row limit", " ".join(rejected["errors"]))

            cost_database_service.COST_DATABASE_MAX_IMPORTED_ROWS = imported_nonempty_rows
            accepted = cost_database_service.import_cost_database_from_excel(
                file_content=content,
                file_name="row_cap.xlsx",
                company=self.company,
                dry_run=True,
            )
            self.assertTrue(accepted["success"], msg=str(accepted["errors"]))
        finally:
            cost_database_service.COST_DATABASE_MAX_IMPORTED_ROWS = old_limit

    def test_import_resolves_custom_worksheet_part_and_checks_actual_coordinates(self):
        from construction.services import cost_database_service
        from construction.services.boq_import_service import BOQImportService

        content = self._rewrite_first_worksheet_part(self._build_test_excel(), "A1:L1")
        old_column_limit = BOQImportService.MAX_COLS
        try:
            BOQImportService.MAX_COLS = 12
            result = cost_database_service.import_cost_database_from_excel(
                file_content=content,
                file_name="custom_part.xlsx",
                company=self.company,
                dry_run=True,
            )
            self.assertFalse(result["success"])
            self.assertIn("cell coordinate", " ".join(result["errors"]).lower())
        finally:
            BOQImportService.MAX_COLS = old_column_limit

    def test_import_reads_rows_beyond_a_lying_small_dimension(self):
        from construction.services.cost_database_service import import_cost_database_from_excel

        content = self._rewrite_first_worksheet_part(self._build_test_excel(), "A1:M1")
        result = import_cost_database_from_excel(
            file_content=content,
            file_name="understated_dimension.xlsx",
            company=self.company,
            dry_run=True,
        )
        self.assertTrue(result["success"], msg=str(result["errors"]))

    def test_import_rejects_malformed_archive_without_records(self):
        from construction.services.cost_database_service import import_cost_database_from_excel

        result = import_cost_database_from_excel(
            file_content=b"PK\x03\x04small malformed fixture",
            file_name="malformed.xlsx",
            company=self.company,
        )
        self.assertFalse(result["success"])
        self.assertTrue(result["errors"])
        self.assertEqual(result["records_created"]["items"], [])

    def test_import_bounds_validation_error_response(self):
        import openpyxl

        from construction.services import cost_database_service

        wb = self._load_workbook(self._build_test_excel())
        resources = wb["Resources"]
        for index in range(105):
            resources.append(
                [
                    f"BAD-RESOURCE-{index}",
                    "Invalid Type",
                    "M",
                    "Invalid resource",
                    "",
                    "Ton",
                    10,
                    "EGP",
                    1,
                    self.company,
                    "Cairo",
                    "2026-06-01",
                    "Test",
                ]
            )
        buf = io.BytesIO()
        wb.save(buf)
        wb.close()

        content = buf.getvalue()
        old_limit = cost_database_service.COST_DATABASE_MAX_RESULT_MESSAGES
        try:
            cost_database_service.COST_DATABASE_MAX_RESULT_MESSAGES = 1000
            full = cost_database_service.import_cost_database_from_excel(
                file_content=content,
                file_name="many_validation_errors.xlsx",
                company=self.company,
                dry_run=True,
            )
            full_error_count = len(full["errors"])
            self.assertGreater(full_error_count, 100)

            cost_database_service.COST_DATABASE_MAX_RESULT_MESSAGES = 100
            bounded = cost_database_service.import_cost_database_from_excel(
                file_content=content,
                file_name="many_validation_errors.xlsx",
                company=self.company,
                dry_run=True,
            )
            omitted_count = full_error_count - 99
            self.assertFalse(bounded["success"])
            self.assertEqual(len(bounded["errors"]), 100)
            self.assertEqual(bounded["errors"][-1], f"{omitted_count} additional messages omitted")
            self.assertEqual(bounded["records_created"]["items"], [])
        finally:
            cost_database_service.COST_DATABASE_MAX_RESULT_MESSAGES = old_limit

    def _rewrite_archive_part(self, content, part_name, transform):
        import zipfile

        output = io.BytesIO()
        changed = False
        with (
            zipfile.ZipFile(io.BytesIO(content), "r") as source,
            zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target,
        ):
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == part_name:
                    data = transform(data)
                    changed = True
                target.writestr(info.filename, data)
        self.assertTrue(changed, f"fixture part {part_name!r} was not found")
        return output.getvalue()

    def test_import_enforces_compression_ratio_on_service_route(self):
        from construction.services import cost_database_service
        from construction.services.boq_import_service import BOQImportService

        old_limit = BOQImportService.MAX_MEMBER_COMPRESSION_RATIO
        try:
            BOQImportService.MAX_MEMBER_COMPRESSION_RATIO = 1
            result = cost_database_service.import_cost_database_from_excel(
                file_content=self._build_test_excel(),
                file_name="compression_ratio.xlsx",
                company=self.company,
                dry_run=True,
            )
            self.assertFalse(result["success"])
            self.assertIn("compression ratio", " ".join(result["errors"]).lower())
            self.assertEqual(result["records_created"]["items"], [])
        finally:
            BOQImportService.MAX_MEMBER_COMPRESSION_RATIO = old_limit

    def test_import_enforces_shared_strings_size_on_service_route(self):
        import zipfile

        from construction.services import cost_database_service
        from construction.services.boq_import_service import BOQImportService

        content = io.BytesIO()
        with (
            zipfile.ZipFile(io.BytesIO(self._build_test_excel()), "r") as source,
            zipfile.ZipFile(content, "w", zipfile.ZIP_DEFLATED) as target,
        ):
            for info in source.infolist():
                target.writestr(info.filename, source.read(info.filename))
            target.writestr("xl/sharedStrings.xml", b"<sst />")

        old_limit = BOQImportService.MAX_SHARED_STRINGS_BYTES
        try:
            BOQImportService.MAX_SHARED_STRINGS_BYTES = 1
            result = cost_database_service.import_cost_database_from_excel(
                file_content=content.getvalue(),
                file_name="shared_strings_size.xlsx",
                company=self.company,
                dry_run=True,
            )
            self.assertFalse(result["success"])
            self.assertIn("shared-string", " ".join(result["errors"]).lower())
            self.assertEqual(result["records_created"]["items"], [])
        finally:
            BOQImportService.MAX_SHARED_STRINGS_BYTES = old_limit

    def test_import_enforces_merged_area_on_service_route(self):
        from construction.services import cost_database_service
        from construction.services.boq_import_service import BOQImportService

        def add_small_merge(data):
            self.assertIn(b"</worksheet>", data)
            return data.replace(
                b"</worksheet>",
                b'<mergeCells count="1"><mergeCell ref="A1:B2"/></mergeCells></worksheet>',
                1,
            )

        content = self._rewrite_archive_part(
            self._build_test_excel(), "xl/worksheets/sheet1.xml", add_small_merge
        )
        old_limit = BOQImportService.MAX_TOTAL_MERGED_CELLS
        try:
            BOQImportService.MAX_TOTAL_MERGED_CELLS = 1
            result = cost_database_service.import_cost_database_from_excel(
                file_content=content,
                file_name="merged_area.xlsx",
                company=self.company,
                dry_run=True,
            )
            self.assertFalse(result["success"])
            self.assertIn("merged cell area", " ".join(result["errors"]).lower())
            self.assertEqual(result["records_created"]["items"], [])
        finally:
            BOQImportService.MAX_TOTAL_MERGED_CELLS = old_limit

    def test_import_cost_database_creates_records(self):
        """Real import creates Items, Resource Price History, and templates with schema fields persisted."""
        from construction.services.cost_database_service import import_cost_database_from_excel

        content = self._build_test_excel()
        result = import_cost_database_from_excel(
            file_content=content,
            file_name="test_import.xlsx",
            company=self.company,
        )
        self.assertTrue(result["success"], msg=str(result["errors"]))
        self.assertEqual(len(result["records_created"]["items"]), 1)
        self.assertEqual(len(result["records_created"]["resource_price_history"]), 1)
        self.assertEqual(len(result["records_created"]["boq_cost_analysis_templates"]), 1)

        # Item created with construction resource flags
        item = frappe.get_doc("Item", "API-CEM-001")
        self.assertTrue(item.is_construction_resource)
        self.assertEqual(item.construction_resource_type, "Material")
        self.assertEqual(item.default_cost_stream, "M")

        # Resource Price History created with region and source
        rph_name = result["records_created"]["resource_price_history"][0]
        rph = frappe.get_doc("Resource Price History", rph_name)
        self.assertEqual(rph.region, "Cairo")
        self.assertEqual(rph.source_doctype, "Import")
        self.assertEqual(rph.source_name, "Test Import")
        self.assertEqual(rph.status, "Active")

        # Template created with bilingual + category fields persisted
        tpl_name = result["records_created"]["boq_cost_analysis_templates"][0]
        tpl = frappe.get_doc("BOQ Cost Analysis", tpl_name)
        self.assertEqual(tpl.is_template, 1)
        self.assertEqual(tpl.template_name, "API-CONC-PLN")
        self.assertEqual(tpl.description_ar, "خرسانة عادية API")
        self.assertEqual(tpl.category, "Concrete Works")
        self.assertEqual(tpl.company, self.company)
        self.assertEqual(len(tpl.details), 1)
        self.assertEqual(tpl.details[0].item_code, "API-CEM-001")
        self.assertEqual(tpl.details[0].rate_source, "Import")

    def test_import_cost_database_idempotent(self):
        """Re-importing the same file creates no duplicate price history or templates."""
        from construction.services.cost_database_service import import_cost_database_from_excel

        content = self._build_test_excel()
        first = import_cost_database_from_excel(
            file_content=content,
            file_name="test_import.xlsx",
            company=self.company,
        )
        self.assertTrue(first["success"], msg=str(first["errors"]))

        second = import_cost_database_from_excel(
            file_content=content,
            file_name="test_import.xlsx",
            company=self.company,
        )
        self.assertTrue(second["success"], msg=str(second["errors"]))

        # No duplicate price history rows
        self.assertEqual(len(second["records_created"]["resource_price_history"]), 0)
        self.assertEqual(len(second["records_skipped"]["resource_price_history"]), 1)

        # No duplicate template — draft updated in place
        self.assertEqual(len(second["records_created"]["boq_cost_analysis_templates"]), 0)
        self.assertEqual(len(second["records_updated"]["boq_cost_analysis_templates"]), 1)

        # Exactly one price history row and one template exist
        self.assertEqual(frappe.db.count("Resource Price History", {"item_code": "API-CEM-001"}), 1)
        self.assertEqual(
            frappe.db.count("BOQ Cost Analysis", {"template_name": "API-CONC-PLN", "is_template": 1}),
            1,
        )

    def test_import_cost_database_updates_draft_template(self):
        """Re-import with a changed rate updates the draft template instead of duplicating it."""
        from construction.services.cost_database_service import import_cost_database_from_excel

        content = self._build_test_excel()
        first = import_cost_database_from_excel(
            file_content=content,
            file_name="test_import.xlsx",
            company=self.company,
        )
        self.assertTrue(first["success"], msg=str(first["errors"]))
        tpl_name = first["records_created"]["boq_cost_analysis_templates"][0]

        # New price for the same resource — history appends, template upserts
        content = self._build_test_excel(rate=4200)
        second = import_cost_database_from_excel(
            file_content=content,
            file_name="test_import.xlsx",
            company=self.company,
        )
        self.assertTrue(second["success"], msg=str(second["errors"]))

        # New price history row appended (rate differs)
        self.assertEqual(len(second["records_created"]["resource_price_history"]), 1)
        self.assertEqual(frappe.db.count("Resource Price History", {"item_code": "API-CEM-001"}), 2)

        # Template updated in place, not duplicated
        tpl = frappe.get_doc("BOQ Cost Analysis", tpl_name)
        self.assertEqual(tpl.details[0].cost_rate, 4200)
        self.assertEqual(
            frappe.db.count("BOQ Cost Analysis", {"template_name": "API-CONC-PLN", "is_template": 1}),
            1,
        )
