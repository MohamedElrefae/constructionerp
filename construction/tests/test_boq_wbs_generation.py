from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import frappe
from frappe.tests.utils import FrappeTestCase

from construction.services.boq_wbs_health import run_wbs_health_check
from construction.tests.test_boq_helpers import get_or_create_test_project


def run_concurrent_wbs_insert_smoke(child_count: int = 4) -> dict:
    """Evidence helper: insert siblings concurrently and report generated WBS codes."""
    site = frappe.local.site
    header = _make_header()
    parent = _make_structure(header.name, "Concurrent Parent", is_group=1)
    frappe.db.commit()

    errors = []
    results = []
    try:
        with ThreadPoolExecutor(max_workers=child_count) as executor:
            futures = [
                executor.submit(
                    _insert_child_in_new_connection,
                    site,
                    header.name,
                    parent.name,
                    f"Concurrent Leaf {idx + 1}",
                )
                for idx in range(child_count)
            ]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    errors.append(str(exc))

        rows = frappe.get_all(
            "BOQ Structure",
            filters={"boq_header": header.name, "parent_structure": parent.name},
            fields=["name", "wbs_code"],
            order_by="wbs_code",
        )
        wbs_codes = [row.wbs_code for row in rows]
        health = run_wbs_health_check(header.name)

        return {
            "boq_header": header.name,
            "parent_structure": parent.name,
            "requested_inserts": child_count,
            "successful_inserts": len(results),
            "errors": errors,
            "wbs_codes": wbs_codes,
            "distinct_wbs_codes": len(wbs_codes) == len(set(wbs_codes)),
            "health": health["summary"],
        }
    finally:
        _cleanup_header(header.name)
        frappe.db.commit()


def cleanup_wbs_generation_smoke_records() -> dict:
    headers = frappe.get_all(
        "BOQ Header",
        filters={"title": "Test WBS Generation"},
        pluck="name",
    )
    for header in headers:
        _cleanup_header(header)
    frappe.db.commit()
    return {"deleted_headers": headers, "count": len(headers)}


class TestBOQWBSGeneration(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_sequential_generation_uses_max_existing_sibling_segment(self):
        header = _make_header()
        root = _make_structure(header.name, "Root", is_group=1)
        first = _make_structure(header.name, "First Leaf", parent_structure=root.name, is_group=0)
        second = _make_structure(header.name, "Second Leaf", parent_structure=root.name, is_group=0)

        self.assertEqual(root.wbs_code, "01")
        self.assertEqual(first.wbs_code, "01.001")
        self.assertEqual(second.wbs_code, "01.002")

    def test_concurrent_insert_smoke(self):
        result = run_concurrent_wbs_insert_smoke(child_count=3)

        self.assertEqual(result["errors"], [])
        self.assertEqual(result["successful_inserts"], 3)
        self.assertTrue(result["distinct_wbs_codes"])
        self.assertEqual(result["health"]["issue_count"], 0)


def _make_header():
    return frappe.get_doc(
        {
            "doctype": "BOQ Header",
            "title": "Test WBS Generation",
            "project": get_or_create_test_project(),
            "status": "Draft",
            "boq_type": "Tender",
        }
    ).insert(ignore_permissions=True)


def _make_structure(header, title, parent_structure=None, is_group=0):
    return frappe.get_doc(
        {
            "doctype": "BOQ Structure",
            "boq_header": header,
            "title": title,
            "parent_structure": parent_structure,
            "is_group": is_group,
        }
    ).insert(ignore_permissions=True)


def _insert_child_in_new_connection(site, header, parent, title):
    frappe.init(site=site)
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        doc = _make_structure(header, title, parent_structure=parent, is_group=0)
        frappe.db.commit()
        return {"name": doc.name, "wbs_code": doc.wbs_code}
    finally:
        frappe.destroy()


def _cleanup_header(header):
    frappe.db.delete("BOQ Item Stage", {"boq_header": header})
    frappe.db.delete("BOQ Item", {"boq_header": header})
    frappe.db.delete("BOQ Structure", {"boq_header": header})
    frappe.db.delete("BOQ Header", {"name": header})
