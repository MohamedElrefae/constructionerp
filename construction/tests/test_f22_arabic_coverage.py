"""F22: Arabic coverage regression for the ordinary-persona UI surfaces.

The F22 work found the Arabic session leaking English in exactly the places an ordinary
persona meets it: sidebar labels, workspace cards, validation errors, the K-01 import
dialog, the export menu and the print-settings dialog. Root causes were (a) strings never
passed through ``__()``, (b) framework ``ar.po`` entries left empty, and (c) sidebar /
workspace item labels with no translation entry at all.

This test keeps all three closed:

1. every ``__()`` string on the surfaces a persona loads has a non-empty Arabic entry;
2. the sidebar and workspace item labels used by the app's Sidebar fixture are translated;
3. the framework strings the app relies on (the mandatory-fields error prefix) are
   translated, because the framework ships them empty in ``ar.po``.

Run with: bench --site <site> run-tests --module construction.tests.test_f22_arabic_coverage
"""

import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase

APP_ROOT = frappe.get_app_path("construction")

SURFACE_FILES = (
    "construction/doctype/boq_header/boq_header.js",
    "construction/doctype/boq_item/boq_item.js",
    "construction/doctype/boq_item/boq_item_list.js",
    "construction/doctype/boq_item_stage/boq_item_stage.js",
    "construction/doctype/variation_order/variation_order.js",
    "public/js/construction_export_menu.js",
    "public/js/generic_export_menu.js",
    "public/js/print_settings_dialog.js",
    "construction/page/construction_report_viewer/construction_report_viewer.js",
    "construction/page/cost_database_workbench/cost_database_workbench.js",
)

# Sidebar Item labels the app's Sidebar fixture ships (module construction).
SIDEBAR_LABELS = (
    "Home",
    "Work areas",
    "Site execution",
    "Estimating and commercial",
    "Procurement and stores",
    "Finance",
    "Cost database",
    "BOQ management",
    "Change control",
    "Rates and prices",
    "Reports and views",
    "Themes and scope",
    "Variation Order",
    "User Scope Context",
    "Construction Report Viewer",
    "Cost Database Workbench",
)

# Workspace card labels rendered on the workspace page.
WORKSPACE_CARD_LABELS = (
    "BOQ Management",
    "Cost Estimation",
    "Variation Management",
    "Theme Settings",
    "Scope Management",
)

# Strings the framework leaves untranslated in its own ar.po but that our surfaces show.
FRAMEWORK_GAPS = (
    "Please fill the following mandatory fields before saving:",
    "Desk",
    "Column Widths",
    "Project",
)


class TestF22ArabicCoverage(FrappeTestCase):
    def _translated(self, source_text):
        rows = frappe.get_all(
            "Translation",
            filters={"language": "ar", "source_text": source_text},
            fields=["translated_text", "ct_is_catalog_entry"],
            limit_page_length=0,
        )
        if not rows:
            return False
        # A runtime override (ct_is_catalog_entry = 0) replaces the packaged catalog row,
        # which is often the empty one that made these strings untranslated in the first place.
        runtime = [r for r in rows if not r.ct_is_catalog_entry]
        chosen = runtime[-1] if runtime else rows[-1]
        return bool((chosen.translated_text or "").strip())

    def _js_strings(self, relative):
        path = os.path.join(APP_ROOT, relative)
        if not os.path.exists(path):
            self.skipTest(f"surface file absent: {relative}")
        src = open(path, encoding="utf-8").read()
        found = set()
        for match in re.finditer(r"""__\(\s*(["'])((?:(?!\1).){3,})\1\s*[,)]""", src):
            text = match.group(2)
            if "{" not in text and "%" not in text:
                found.add(text)
        return found

    def test_js_surface_strings_have_arabic(self):
        missing = {}
        for rel in SURFACE_FILES:
            for text in sorted(self._js_strings(rel)):
                if not self._translated(text):
                    missing.setdefault(rel, []).append(text)
        self.assertEqual(
            missing,
            {},
            "untranslated Arabic entries on ordinary-persona surfaces: "
            + "; ".join(f"{k}: {v}" for k, v in missing.items()),
        )

    def test_sidebar_and_workspace_labels_have_arabic(self):
        missing = [
            label
            for label in list(SIDEBAR_LABELS) + list(WORKSPACE_CARD_LABELS)
            if not self._translated(label)
        ]
        self.assertEqual(missing, [], f"sidebar/workspace labels without Arabic: {missing}")

    def test_framework_gap_strings_have_arabic(self):
        missing = [s for s in FRAMEWORK_GAPS if not self._translated(s)]
        self.assertEqual(
            missing,
            [],
            f"framework strings our surfaces rely on are untranslated in ar: {missing}",
        )

    def test_k01_dialog_strings_are_translatable(self):
        """The K-01 dialog strings must be wrapped in __(), not hardcoded (F22-D003)."""
        path = os.path.join(APP_ROOT, "construction/doctype/boq_header/boq_header.js")
        src = open(path, encoding="utf-8").read()
        for hardcoded in (
            'title: "Import BOQ from Excel"',
            'label: "Excel File"',
            'label: "Import Mode"',
            'primary_action_label: "Validate"',
            'd.set_primary_action("Confirm Import"',
        ):
            self.assertNotIn(
                hardcoded,
                src,
                f"K-01 dialog string is hardcoded and can never be Arabic: {hardcoded}",
            )

    def test_k01_dialog_preview_regression_guards(self):
        """F36-D003: the three preview-path fixes must stay in place.

        (1) `d.doc` initialised at dialog creation — without it the preview callback
        throws after the 200 response and the dialog sticks on "Validating…".
        (2) staged `file_url` and `import_mode` restored after `d.refresh()` — without
        them Confirm dies on mandatory validation / empty mode.
        (3) mode options stay English enum codes — translating them breaks the
        confirmed_import_mode round-trip against IMPORT_MODES.
        """
        path = os.path.join(APP_ROOT, "construction/doctype/boq_header/boq_header.js")
        src = open(path, encoding="utf-8").read()
        self.assertIn(
            "d.doc = d.doc || {}",
            src,
            "dialog backing object must be initialised (F36-D003-1)",
        )
        self.assertIn(
            'd.set_value("file_url", file_url)',
            src,
            "staged file_url must be restored after refresh (F36-D003-2)",
        )
        self.assertIn(
            'd.set_value("import_mode", msg.detected_import_mode)',
            src,
            "detected mode must be restored after refresh (F36-D003-2)",
        )
        self.assertIn(
            'options: ["Structured", "Semi-Structured", "Flat"]',
            src,
            "mode options must stay English enum codes (F36-D003-3)",
        )
