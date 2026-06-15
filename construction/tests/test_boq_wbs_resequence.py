import frappe
from frappe.tests.utils import FrappeTestCase

from construction.tests.test_boq_helpers import get_or_create_test_project


def run_wbs_resequence_smoke() -> dict:
    cleanup_wbs_resequence_smoke_records()

    from construction.services.wbs_generator import resequence_wbs

    previous_flag = frappe.db.get_single_value("Construction Settings", "enable_boq_wbs_resequence")
    frappe.db.set_single_value("Construction Settings", "enable_boq_wbs_resequence", 1)

    draft_header = _make_header("Draft")
    non_draft_header = _make_header("Draft")

    try:
        root = _make_structure(draft_header.name, "Root", is_group=1)
        child_group = _make_structure(
            draft_header.name, "Child Group", parent_structure=root.name, is_group=1
        )
        child_leaf = _make_structure(draft_header.name, "Child Leaf", parent_structure=root.name, is_group=0)
        nested_leaf = _make_structure(
            draft_header.name,
            "Nested Leaf",
            parent_structure=child_group.name,
            is_group=0,
        )

        _force_wbs_codes(
            {
                root.name: "09",
                child_group.name: "09.09",
                child_leaf.name: "09.999",
                nested_leaf.name: "09.09.999",
            }
        )

        success = resequence_wbs(draft_header.name)
        final_codes = _get_wbs_map(draft_header.name)
        audit_exists = bool(frappe.db.exists("Comment", success["audit_comment"]))

        non_draft_header.status = "Pricing"
        non_draft_header.save(ignore_permissions=True)

        blocked = False
        blocked_message = None
        try:
            resequence_wbs(non_draft_header.name)
        except Exception as exc:
            blocked = True
            blocked_message = str(exc)

        return {
            "draft_header": draft_header.name,
            "success": {
                "changed_count": success["changed_count"],
                "structure_count": success["structure_count"],
                "audit_comment": success["audit_comment"],
                "audit_exists": audit_exists,
                "final_codes": final_codes,
            },
            "non_draft_block": {
                "header": non_draft_header.name,
                "status": frappe.db.get_value("BOQ Header", non_draft_header.name, "status"),
                "blocked": blocked,
                "message": blocked_message,
            },
        }
    finally:
        frappe.db.set_single_value("Construction Settings", "enable_boq_wbs_resequence", previous_flag or 0)
        cleanup_wbs_resequence_smoke_records()


def cleanup_wbs_resequence_smoke_records() -> dict:
    headers = frappe.get_all(
        "BOQ Header",
        filters={"title": "Test WBS Resequence"},
        pluck="name",
    )
    for header in headers:
        frappe.db.delete("Comment", {"reference_doctype": "BOQ Header", "reference_name": header})
        frappe.db.delete("BOQ Item Stage", {"boq_header": header})
        frappe.db.delete("BOQ Item", {"boq_header": header})
        frappe.db.delete("BOQ Structure", {"boq_header": header})
        frappe.db.delete("BOQ Header", {"name": header})
    frappe.db.commit()
    return {"deleted_headers": headers, "count": len(headers)}


class TestBOQWBSResequence(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_resequence_is_draft_only_and_audited(self):
        result = run_wbs_resequence_smoke()

        self.assertTrue(result["success"]["audit_exists"])
        self.assertEqual(result["success"]["final_codes"]["Root"], "01")
        self.assertEqual(result["success"]["final_codes"]["Child Group"], "01.01")
        self.assertEqual(result["success"]["final_codes"]["Child Leaf"], "01.002")
        self.assertEqual(result["success"]["final_codes"]["Nested Leaf"], "01.01.001")
        self.assertTrue(result["non_draft_block"]["blocked"])


def _make_header(status):
    return frappe.get_doc(
        {
            "doctype": "BOQ Header",
            "title": "Test WBS Resequence",
            "project": get_or_create_test_project(),
            "status": status,
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


def _force_wbs_codes(codes_by_name):
    for name, wbs_code in codes_by_name.items():
        frappe.db.set_value("BOQ Structure", name, "wbs_code", wbs_code, update_modified=False)


def _get_wbs_map(boq_header):
    rows = frappe.get_all(
        "BOQ Structure",
        filters={"boq_header": boq_header},
        fields=["title", "wbs_code"],
    )
    return {row.title: row.wbs_code for row in rows}
