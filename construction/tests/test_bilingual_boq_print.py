"""BOQ Masters (BOQ Structure & BOQ Header) bilingual enablement and flag-gated print tests.

Run with:
PYTHONPATH=/home/mohamed/frappe-bench/worktrees/bilingual-boq-masters \\
  bench --site v16.localhost run-tests --app construction --module construction.tests.test_bilingual_boq_print

Covers:
- Patch v9_7 idempotency and reversibility for title_ar and title_ar_norm across BOQ Structure and BOQ Header.
- Registry mapping resolution including norm_field, tree.enabled, wbs_code code_field, and search fields.
- Fail-closed validation when declared fields are missing on active/schema_installed BOQ Structure and BOQ Header.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on title_ar for both doctypes.
- WBS Code Exclusivity & ASCII Invariant: wbs_code is strictly ASCII alphanumeric, has no _ar or _norm fields,
  and is untouched by bilingual normalization.
- Print Rendering Flag OFF: enable_bilingual_boq_print = 0 produces monolingual output identical to baseline.
- Print Rendering Flag ON: enable_bilingual_boq_print = 1 renders dual-language title / title_ar and project_name / project_name_ar.
- Mechanically enforced guard test: zero service edits (byte-identical to base commit ef36c95).
"""

import re
import subprocess
import unittest
from pathlib import Path
from uuid import uuid4

import frappe

from construction.patches.v9_7.add_boq_arabic_fields import execute as patch_execute
from construction.patches.v9_7.add_boq_arabic_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic
from construction.services.boq_export_service import BOQExportService
from construction.services.feature_flags import is_enabled, set_flag


def _get_project_and_company():
    proj = frappe.db.get_value("Project", {}, ["name", "company"], as_dict=True)
    if proj and proj.name:
        return proj.name, proj.company
    company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.get_all("Company", limit=1)[0].name
    doc = frappe.get_doc({
        "doctype": "Project",
        "project_name": f"Test Project {uuid4().hex[:6]}",
        "company": company,
    }).insert(ignore_permissions=True)
    return doc.name, company


def _make_header(title: str, title_ar: str = None, project: str = None, **kwargs):
    if not project:
        project, _ = _get_project_and_company()
    d = {
        "doctype": "BOQ Header",
        "project": project,
        "title": title,
        "status": "Draft",
        "boq_type": "Tender",
    }
    if title_ar:
        d["title_ar"] = title_ar
    d.update(kwargs)
    return frappe.get_doc(d).insert(ignore_permissions=True)


class TestBilingualBOQPrint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        patch_execute()

    def test_zero_service_edits_guard(self):
        """Primary invariant: bilingual_service.py and search.py must be byte-identical to base commit ef36c95."""
        repo_root = Path(__file__).resolve().parents[2]
        base_commit = "ef36c95"
        files_to_check = [
            "construction/services/bilingual_service.py",
            "construction/searchable_dropdown/api/search.py",
        ]
        for rel_path in files_to_check:
            expected = subprocess.check_output(
                ["git", "show", f"{base_commit}:{rel_path}"],
                cwd=str(repo_root),
            )
            actual = (repo_root / rel_path).read_bytes()
            self.assertEqual(
                actual,
                expected,
                f"Candidate violated zero-service-edits invariant for {rel_path}!",
            )

    def test_norm_field_patch_idempotent_and_reversible(self):
        """Idempotent execute and clean revert of patch v9_7 across BOQ Structure and BOQ Header."""
        patch_execute()
        targets = [
            ("BOQ Structure", "title_ar"),
            ("BOQ Structure", "title_ar_norm"),
            ("BOQ Header", "title_ar"),
            ("BOQ Header", "title_ar_norm"),
        ]
        for dt, fn in targets:
            self.assertTrue(frappe.get_meta(dt).has_field(fn), f"Field {fn} missing on {dt}")

        # Idempotency check: run again without error
        patch_execute()
        for dt, fn in targets:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        # Reversibility check: revert removes fields
        patch_revert()
        for dt, fn in targets:
            frappe.clear_cache(doctype=dt)
            self.assertFalse(frappe.get_meta(dt).has_field(fn), f"Field {fn} still present on {dt} after revert")

        # Re-execute to restore required schema for subsequent tests
        patch_execute()
        for dt, fn in targets:
            frappe.clear_cache(doctype=dt)
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

    def test_registry_loads_and_maps_resolved_boq_fields(self):
        """Ensure get_mapping resolves norm_field, tree.enabled, wbs_code, and search fields for both BOQ doctypes."""
        frappe.local.ct_bilingual_mapping_cache = None

        # 1. BOQ Structure
        m_struct = svc.get_mapping("BOQ Structure")
        self.assertIsNotNone(m_struct, "Mapping missing for BOQ Structure")
        self.assertEqual(m_struct["resolved"].get("english_field"), "title")
        self.assertEqual(m_struct["resolved"].get("arabic_field"), "title_ar")
        self.assertEqual(m_struct["resolved"].get("norm_field"), "title_ar_norm")
        self.assertEqual(m_struct["resolved"].get("code_field"), "wbs_code")
        self.assertTrue(bool((m_struct.get("tree") or {}).get("enabled")))
        self.assertIn("wbs_code", m_struct.get("search", {}).get("fields", []))
        self.assertIn("title_ar", m_struct.get("search", {}).get("fields", []))

        # 2. BOQ Header
        m_header = svc.get_mapping("BOQ Header")
        self.assertIsNotNone(m_header, "Mapping missing for BOQ Header")
        self.assertEqual(m_header["resolved"].get("english_field"), "title")
        self.assertEqual(m_header["resolved"].get("arabic_field"), "title_ar")
        self.assertEqual(m_header["resolved"].get("norm_field"), "title_ar_norm")
        self.assertIsNone(m_header["resolved"].get("code_field"))
        self.assertFalse(bool((m_header.get("tree") or {}).get("enabled")))
        self.assertIn("title_ar", m_header.get("search", {}).get("fields", []))

    def test_active_and_schema_installed_fail_closed_on_missing_field(self):
        """If norm_field is declared on schema_installed BOQ doctype but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        for target_dt in ("BOQ Structure", "BOQ Header"):
            fake_registry = {
                "schema": orig_registry.get("schema"),
                "display": orig_registry.get("display"),
                "unicode_policy": orig_registry.get("unicode_policy"),
                "doctypes": {
                    target_dt: {
                        "state": "schema_installed",
                        "english_field": "title",
                        "arabic_field": "title_ar",
                        "norm_field": f"nonexistent_{target_dt.lower().replace(' ', '_')}_norm",
                        "code_field": None,
                        "identity_field": "name",
                    }
                },
            }
            with unittest.mock.patch.object(svc, "get_registry", return_value=fake_registry):
                frappe.local.ct_bilingual_mapping_cache = None
                with self.assertRaises(frappe.ValidationError):
                    svc.get_mapping(target_dt)
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """Client-passed POISONED-KEY is overwritten with server-derived norm on save for BOQ Header and Structure."""
        header = None
        structure = None
        try:
            # 1. BOQ Header
            header = _make_header(
                f"Test BOQ Header {uuid4().hex[:6]}",
                title_ar="مشروع الأبراج السكنية والتجارية",
                title_ar_norm="POISONED-KEY-HEADER",
            )

            reloaded_header = frappe.get_doc("BOQ Header", header.name)
            expected_header_norm = normalize_arabic("مشروع الأبراج السكنية والتجارية")
            self.assertEqual(
                reloaded_header.title_ar_norm,
                expected_header_norm,
                "Poisoned key survived or norm not derived on BOQ Header!",
            )

            # 2. BOQ Structure
            structure = frappe.get_doc({
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Excavation Works",
                "title_ar": "أعمال الحفريات والأساسات العميقة",
                "title_ar_norm": "POISONED-KEY-STRUCT",
                "wbs_code": "01",
                "is_group": 1,
            })
            structure.flags.ignore_wbs_generation = True
            structure.insert(ignore_permissions=True)

            reloaded_struct = frappe.get_doc("BOQ Structure", structure.name)
            expected_struct_norm = normalize_arabic("أعمال الحفريات والأساسات العميقة")
            self.assertEqual(
                reloaded_struct.title_ar_norm,
                expected_struct_norm,
                "Poisoned key survived or norm not derived on BOQ Structure!",
            )
        finally:
            if structure and frappe.db.exists("BOQ Structure", structure.name):
                frappe.delete_doc("BOQ Structure", structure.name, force=True)
            if header and frappe.db.exists("BOQ Header", header.name):
                frappe.delete_doc("BOQ Header", header.name, force=True)
            frappe.db.commit()

    def test_arabic_edit_rejects_bidi_controls(self):
        """title_ar rejects bidi controls (C0, C1, DEL, overrides, isolates, LRM/RLM/ALM)."""
        forbidden_samples = [
            "أعمال\u202eالموقع",  # Right-to-Left Override
            "أعمال\u200eالموقع",  # LRM
            "أعمال\u202bالموقع",  # RLE
            "أعمال\x00الموقع",  # NUL
        ]
        header = None
        structure = None
        try:
            header = _make_header(f"Test BOQ Bidi {uuid4().hex[:6]}")

            structure = frappe.get_doc({
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Bidi Test Structure",
                "wbs_code": "99",
                "is_group": 1,
            })
            structure.flags.ignore_wbs_generation = True
            structure.insert(ignore_permissions=True)

            for bad_sample in forbidden_samples:
                # Test on BOQ Header
                header.title_ar = bad_sample
                with self.assertRaises(frappe.ValidationError):
                    header.save()

                # Test on BOQ Structure
                structure.title_ar = bad_sample
                with self.assertRaises(frappe.ValidationError):
                    structure.save()
        finally:
            if structure and frappe.db.exists("BOQ Structure", structure.name):
                frappe.delete_doc("BOQ Structure", structure.name, force=True)
            if header and frappe.db.exists("BOQ Header", header.name):
                frappe.delete_doc("BOQ Header", header.name, force=True)
            frappe.db.commit()

    def test_wbs_code_exclusivity_and_ascii_invariant(self):
        """wbs_code is strictly ASCII alphanumeric, has no _ar or _norm fields, and is untouched by Arabic normalization."""
        meta = frappe.get_meta("BOQ Structure")
        # Assert wbs_code field exists and has NO bilingual counterpart fields
        self.assertTrue(meta.has_field("wbs_code"))
        self.assertFalse(meta.has_field("wbs_code_ar"))
        self.assertFalse(meta.has_field("wbs_code_norm"))
        self.assertFalse(meta.has_field("wbs_code_ar_norm"))

        # Verify registry entry explicitly excludes wbs_code from being the identity or arabic field
        m = svc.get_mapping("BOQ Structure")
        self.assertEqual(m["resolved"]["code_field"], "wbs_code")
        self.assertEqual(m["resolved"]["arabic_field"], "title_ar")
        self.assertEqual(m["resolved"]["norm_field"], "title_ar_norm")

        # Create record with standard WBS code and Arabic title
        header = None
        structure = None
        try:
            header = _make_header(f"Test WBS Invariant {uuid4().hex[:6]}")

            wbs_test_val = "01.002.A-1"
            structure = frappe.get_doc({
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Substructure Concrete",
                "title_ar": "خرسانة الأساسات المسلحة",
                "wbs_code": wbs_test_val,
                "is_group": 0,
            })
            structure.flags.ignore_wbs_generation = True
            structure.insert(ignore_permissions=True)

            # Assert wbs_code matches ASCII alphanumeric pattern strictly
            self.assertTrue(bool(re.match(r"^[A-Za-z0-9._-]+$", structure.wbs_code)))
            self.assertEqual(structure.wbs_code, wbs_test_val)

            # Reload and verify wbs_code was untouched by any Arabic normalization hook
            reloaded = frappe.get_doc("BOQ Structure", structure.name)
            self.assertEqual(reloaded.wbs_code, wbs_test_val)
            self.assertTrue(bool(re.match(r"^[A-Za-z0-9._-]+$", reloaded.wbs_code)))
        finally:
            if structure and frappe.db.exists("BOQ Structure", structure.name):
                frappe.delete_doc("BOQ Structure", structure.name, force=True)
            if header and frappe.db.exists("BOQ Header", header.name):
                frappe.delete_doc("BOQ Header", header.name, force=True)
            frappe.db.commit()

    def test_print_rendering_flag_off_monolingual_baseline(self):
        """When enable_bilingual_boq_print = 0, print format outputs monolingual English without Arabic slash separator."""
        old_flag = is_enabled("enable_bilingual_boq_print")
        old_lang = getattr(frappe.local, "lang", None)
        header = None
        struct_root = None
        struct_leaf = None
        try:
            set_flag("enable_bilingual_boq_print", 0, commit=True)
            frappe.local.lang = "en"

            header = _make_header(
                f"Site Development Works {uuid4().hex[:6]}",
                title_ar="أعمال تطوير الموقع",
            )

            struct_root = frappe.get_doc({
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Earthworks",
                "title_ar": "الأعمال الترابية",
                "wbs_code": "01",
                "is_group": 1,
            })
            struct_root.flags.ignore_wbs_generation = True
            struct_root.insert(ignore_permissions=True)

            struct_leaf = frappe.get_doc({
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "parent_structure": struct_root.name,
                "title": "Site Clearing",
                "title_ar": "تنظيف الموقع",
                "wbs_code": "01.001",
                "is_group": 0,
            })
            struct_leaf.flags.ignore_wbs_generation = True
            struct_leaf.insert(ignore_permissions=True)

            context = {
                "header": BOQExportService.get_boq_header_data(header.name),
                "items": BOQExportService.get_tree_data(header.name),
                "grand_total": 0,
                "columns": [
                    {"key": "wbs_code", "label": "WBS Code", "width": 12},
                    {"key": "title", "label": "Title / Description", "width": 30},
                    {"key": "type", "label": "Type", "width": 6},
                ],
                "export_date": "2026-10-03 00:00",
                "company": "Company",
                **BOQExportService._print_context(),
            }

            self.assertFalse(context["is_bilingual_print"])

            # 1. Render boq_print_format.html
            html_full = BOQExportService._render_template("boq_print_format.html", context)
            self.assertIn(header.title, html_full)
            self.assertNotIn(f"{header.title} / {header.title_ar}", html_full)
            self.assertNotIn("Earthworks / الأعمال الترابية", html_full)
            self.assertIn("Earthworks", html_full)

            # 2. Render boq_header_print.html
            html_header = BOQExportService._render_template("boq_header_print.html", context)
            self.assertIn(header.title, html_header)
            self.assertNotIn(f"{header.title} / {header.title_ar}", html_header)
        finally:
            frappe.local.lang = old_lang
            set_flag("enable_bilingual_boq_print", old_flag, commit=True)
            if struct_leaf and frappe.db.exists("BOQ Structure", struct_leaf.name):
                frappe.delete_doc("BOQ Structure", struct_leaf.name, force=True)
            if struct_root and frappe.db.exists("BOQ Structure", struct_root.name):
                frappe.delete_doc("BOQ Structure", struct_root.name, force=True)
            if header and frappe.db.exists("BOQ Header", header.name):
                frappe.delete_doc("BOQ Header", header.name, force=True)
            frappe.db.commit()

    def test_print_rendering_flag_on_dual_language(self):
        """When enable_bilingual_boq_print = 1, print formats render dual-language title / title_ar in headers and lines."""
        old_flag = is_enabled("enable_bilingual_boq_print")
        old_lang = getattr(frappe.local, "lang", None)
        header = None
        struct_root = None
        struct_leaf = None
        test_project = None
        try:
            set_flag("enable_bilingual_boq_print", 1, commit=True)
            frappe.local.lang = "en"

            _, company = _get_project_and_company()
            proj_id = f"PROJ-BIL-{uuid4().hex[:6]}"
            test_project = frappe.get_doc({
                "doctype": "Project",
                "project_name": proj_id,
                "project_name_ar": "مشروع البرج التجاري الحديث",
                "company": company,
            }).insert(ignore_permissions=True)

            header = _make_header(
                "Main Commercial Center BOQ",
                title_ar="جدول كميات المركز التجاري الرئيسي",
                project=test_project.name,
            )

            struct_root = frappe.get_doc({
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Civil and Structural Package",
                "title_ar": "حزمة الأعمال المدنية والإنشائية",
                "wbs_code": "01",
                "is_group": 1,
            })
            struct_root.flags.ignore_wbs_generation = True
            struct_root.insert(ignore_permissions=True)

            struct_leaf = frappe.get_doc({
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "parent_structure": struct_root.name,
                "title": "Substructure Reinforced Concrete",
                "title_ar": "خرسانة الأساسات المسلحة",
                "wbs_code": "01.001",
                "is_group": 0,
            })
            struct_leaf.flags.ignore_wbs_generation = True
            struct_leaf.insert(ignore_permissions=True)

            context = {
                "header": BOQExportService.get_boq_header_data(header.name),
                "items": BOQExportService.get_tree_data(header.name),
                "grand_total": 0,
                "columns": [
                    {"key": "wbs_code", "label": "WBS Code", "width": 12},
                    {"key": "title", "label": "Title / Description", "width": 30},
                    {"key": "type", "label": "Type", "width": 6},
                ],
                "export_date": "2026-10-03 00:00",
                "company": "Company",
                **BOQExportService._print_context(),
            }

            self.assertTrue(context["is_bilingual_print"])

            header_context = {
                "header": BOQExportService.get_boq_header_data(header.name),
                "columns": [
                    {"key": "name", "label": "BOQ ID", "width": 15},
                    {"key": "title", "label": "Title", "width": 20},
                    {"key": "project_name", "label": "Project", "width": 20},
                ],
                "export_date": "2026-10-03 00:00",
                "company": "Company",
                **BOQExportService._print_context(),
            }

            # 1. Render boq_print_format.html
            html_full = BOQExportService._render_template("boq_print_format.html", context)
            expected_header_title = f"{header.title} / {header.title_ar}"
            self.assertIn(expected_header_title, html_full)
            expected_proj = f"{test_project.project_name} / {test_project.project_name_ar}"
            self.assertIn(expected_proj, html_full)
            self.assertIn("Civil and Structural Package / حزمة الأعمال المدنية والإنشائية", html_full)
            self.assertIn("Substructure Reinforced Concrete / خرسانة الأساسات المسلحة", html_full)
            self.assertIn("01.001", html_full)

            # 2. Render boq_header_print.html
            html_header = BOQExportService._render_template("boq_header_print.html", header_context)
            self.assertIn(expected_header_title, html_header)
            self.assertIn(expected_proj, html_header)
        finally:
            frappe.local.lang = old_lang
            set_flag("enable_bilingual_boq_print", old_flag, commit=True)
            if struct_leaf and frappe.db.exists("BOQ Structure", struct_leaf.name):
                frappe.delete_doc("BOQ Structure", struct_leaf.name, force=True)
            if struct_root and frappe.db.exists("BOQ Structure", struct_root.name):
                frappe.delete_doc("BOQ Structure", struct_root.name, force=True)
            if header and frappe.db.exists("BOQ Header", header.name):
                frappe.delete_doc("BOQ Header", header.name, force=True)
            if test_project and frappe.db.exists("Project", test_project.name):
                frappe.delete_doc("Project", test_project.name, force=True)
            frappe.db.commit()

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Search matches BOQ Structure and BOQ Header despite Alef variants, tatweel, and diacritics."""
        header = None
        structure = None
        try:
            h_ar = "مَشْرُوعُ الأَبْرَاجِ السَّكَنِيَّةِ"
            s_ar = "أَعْمَالُ الحَفْرِيَّاتِ العَمِيقَةِ"

            header = _make_header(
                f"Towers {uuid4().hex[:6]}",
                title_ar=h_ar,
            )

            structure = frappe.get_doc({
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Deep Excavation",
                "title_ar": s_ar,
                "wbs_code": "88",
                "is_group": 1,
            })
            structure.flags.ignore_wbs_generation = True
            structure.insert(ignore_permissions=True)
            frappe.db.commit()

            # 1. Search BOQ Header with bare Alef / no diacritics
            h_query = "مشروع الابراج"
            h_results = svc.search_bilingual("BOQ Header", txt=h_query)
            h_matched = [r["value"] for r in h_results]
            self.assertIn(header.name, h_matched, f"BOQ Header search failed for {h_query}")

            # 2. Search BOQ Structure with bare Alef / no diacritics
            s_query = "اعمال الحفريات"
            s_results = svc.search_bilingual("BOQ Structure", txt=s_query)
            s_matched = [r["value"] for r in s_results]
            self.assertIn(structure.name, s_matched, f"BOQ Structure search failed for {s_query}")

            # 3. Searchable dropdown search on BOQ Structure
            dropdown_res = searchable_link_search(doctype="BOQ Structure", txt=s_query)
            items = dropdown_res.get("results", []) if isinstance(dropdown_res, dict) else dropdown_res
            dropdown_names = [r["value"] for r in items]
            self.assertIn(structure.name, dropdown_names, f"Searchable dropdown failed for {s_query}")
        finally:
            if structure and frappe.db.exists("BOQ Structure", structure.name):
                frappe.delete_doc("BOQ Structure", structure.name, force=True)
            if header and frappe.db.exists("BOQ Header", header.name):
                frappe.delete_doc("BOQ Header", header.name, force=True)
            frappe.db.commit()
