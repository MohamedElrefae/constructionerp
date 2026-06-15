from concurrent.futures import ThreadPoolExecutor, as_completed

import frappe
from frappe.tests.utils import FrappeTestCase


def run_stage_policy_smoke() -> dict:
    header = None
    certified_header = None
    try:
        header, item = _make_stage_policy_item("WP3 Stage Policy Smoke")
        stage = _make_stage(item, planned_qty=10, measured_executed_qty=0, certified_qty=0).insert(
            ignore_permissions=True
        )

        _move_header_to_status(header.name, "Frozen")
        stage.reload()
        stage.measured_executed_qty = 4
        stage.percent_complete = 40
        stage.save(ignore_permissions=True)
        frappe.db.commit()

        stage.reload()
        frozen_planned_block = _try_save_stage(stage.name, {"planned_qty": 9})
        frozen_name_block = _try_save_stage(stage.name, {"stage_name": "Changed After Frozen"})

        _move_header_to_status(header.name, "Locked")
        stage.reload()
        stage.measured_executed_qty = 6
        stage.percent_complete = 60
        stage.save(ignore_permissions=True)
        frappe.db.commit()

        certified_header, certified_item = _make_stage_policy_item("WP3 Certified Stage Smoke")
        certified = _make_stage(
            certified_item,
            stage_code="CERT-001",
            planned_qty=10,
            measured_executed_qty=10,
            certified_qty=0,
            stage_status="In Progress",
        ).insert(ignore_permissions=True)
        certified.certified_qty = 10
        certified.stage_status = "Certified"
        certified.percent_complete = 100
        certified.save(ignore_permissions=True)
        frappe.db.commit()

        certified_edit_block = _try_save_stage(certified.name, {"description": "Changed after certification"})
        certified_delete_block = _try_delete_stage(certified.name)

        return {
            "success": True,
            "frozen_measurement_allowed": True,
            "locked_measurement_allowed": True,
            "frozen_planned_blocked": not frozen_planned_block["success"],
            "frozen_name_blocked": not frozen_name_block["success"],
            "certified_edit_blocked": not certified_edit_block["success"],
            "certified_delete_blocked": not certified_delete_block["success"],
            "errors": {
                "frozen_planned": frozen_planned_block.get("error"),
                "frozen_name": frozen_name_block.get("error"),
                "certified_edit": certified_edit_block.get("error"),
                "certified_delete": certified_delete_block.get("error"),
            },
        }
    finally:
        if header:
            _cleanup_stage_policy_header(header.name)
        if certified_header:
            _cleanup_stage_policy_header(certified_header.name)
        frappe.db.commit()


def run_stage_certification_role_smoke() -> dict:
    header = None
    original_user = frappe.session.user
    try:
        header, item = _make_stage_policy_item("WP3 Certification Role Smoke")
        stage = _make_stage(item, planned_qty=10, measured_executed_qty=10, certified_qty=0).insert(
            ignore_permissions=True
        )
        frappe.db.commit()

        blocked = None
        frappe.set_user("Guest")
        try:
            guest_stage = frappe.get_doc("BOQ Item Stage", stage.name)
            guest_stage.certified_qty = 10
            guest_stage.stage_status = "Certified"
            guest_stage.save(ignore_permissions=True)
            blocked = {"success": True}
        except Exception as exc:
            frappe.db.rollback()
            blocked = {"success": False, "error": str(exc)}
        finally:
            frappe.set_user(original_user)

        if blocked.get("success") or "can certify" not in (blocked.get("error") or ""):
            frappe.throw(f"Expected non-certifier certification block, got {blocked}")

        admin_stage = frappe.get_doc("BOQ Item Stage", stage.name)
        admin_stage.certified_qty = 10
        admin_stage.stage_status = "Certified"
        admin_stage.percent_complete = 100
        admin_stage.save(ignore_permissions=True)

        return {
            "success": True,
            "guest_certification_blocked": True,
            "guest_error": blocked.get("error"),
            "admin_certification_allowed": True,
        }
    finally:
        frappe.set_user(original_user)
        if header:
            _cleanup_stage_policy_header(header.name)
        frappe.db.commit()


def run_stage_bulk_update_smoke() -> dict:
    from construction.api.boq_api import bulk_update_boq_item_stages
    from construction.services.feature_flags import get_flags

    header = None
    old_flag = frappe.db.get_single_value("Construction Settings", "enable_stage_measurement_ui")
    original_user = frappe.session.user
    try:
        header, item = _make_stage_policy_item("WP3 Bulk Stage Smoke")
        stage_1 = _make_stage(item, stage_code="BULK-1", planned_qty=5).insert(ignore_permissions=True)
        stage_2 = _make_stage(item, stage_code="BULK-2", planned_qty=5).insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.db.set_single_value("Construction Settings", "enable_stage_measurement_ui", 0)
        disabled = bulk_update_boq_item_stages([{"name": stage_1.name, "measured_executed_qty": 1}])
        if disabled.get("success") or "disabled" not in (disabled.get("error") or ""):
            frappe.throw(f"Expected disabled bulk update block, got {disabled}")

        frappe.db.set_single_value("Construction Settings", "enable_stage_measurement_ui", 1)
        measurement = bulk_update_boq_item_stages(
            [
                {
                    "name": stage_1.name,
                    "measured_executed_qty": 2,
                    "percent_complete": 40,
                    "stage_status": "In Progress",
                },
                {
                    "name": stage_2.name,
                    "measured_executed_qty": 3,
                    "percent_complete": 60,
                    "stage_status": "In Progress",
                },
            ]
        )
        if not measurement.get("success"):
            frappe.throw(f"Expected bulk measurement success, got {measurement}")

        frappe.set_user("Guest")
        guest_cert = bulk_update_boq_item_stages(
            [{"name": stage_1.name, "certified_qty": 1, "stage_status": "Certified"}]
        )
        frappe.set_user(original_user)
        if guest_cert.get("success") or "can certify" not in (guest_cert.get("error") or ""):
            frappe.throw(f"Expected guest bulk certification block, got {guest_cert}")

        admin_cert = bulk_update_boq_item_stages(
            [
                {
                    "name": stage_1.name,
                    "measured_executed_qty": 2,
                    "certified_qty": 2,
                    "stage_status": "Certified",
                }
            ]
        )
        if not admin_cert.get("success"):
            frappe.throw(f"Expected admin bulk certification success, got {admin_cert}")

        rows = frappe.get_all(
            "BOQ Item Stage",
            filters={"boq_header": header.name},
            fields=[
                "stage_code",
                "measured_executed_qty",
                "certified_qty",
                "percent_complete",
                "stage_status",
            ],
            order_by="stage_code",
        )
        return {
            "success": True,
            "disabled_blocked": True,
            "measurement_success": True,
            "guest_certification_blocked": True,
            "admin_certification_success": True,
            "rows": [dict(row) for row in rows],
            "flags_after_smoke": get_flags(),
        }
    finally:
        frappe.set_user(original_user)
        if old_flag is not None:
            frappe.db.set_single_value("Construction Settings", "enable_stage_measurement_ui", old_flag)
        if header:
            _cleanup_stage_policy_header(header.name)
        frappe.db.commit()


def run_stage_concurrent_distribution_smoke() -> dict:
    site = frappe.local.site
    header = None
    try:
        header, item = _make_stage_policy_item("WP3 Concurrent Stage Smoke")
        frappe.db.commit()

        results = []
        errors = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    _insert_stage_in_new_connection,
                    site,
                    item.name,
                    f"CONC-{idx + 1}",
                    6,
                )
                for idx in range(2)
            ]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    errors.append(str(exc))

        stage_rows = frappe.get_all(
            "BOQ Item Stage",
            filters={"boq_item": item.name},
            fields=["name", "stage_code", "planned_qty"],
            order_by="stage_code",
        )
        total_planned = sum(row.planned_qty for row in stage_rows)
        if len(stage_rows) != 1 or total_planned != 6:
            frappe.throw(
                f"Expected one successful stage with total planned 6, got {stage_rows}; "
                f"worker results={results}; worker errors={errors}"
            )
        if not errors or not any("exceeds BOQ Item quantity" in error for error in errors):
            frappe.throw(f"Expected one concurrent over-allocation error, got {errors}")

        return {
            "success": True,
            "requested_inserts": 2,
            "successful_inserts": len(results),
            "blocked_inserts": len(errors),
            "errors": errors,
            "stage_rows": [dict(row) for row in stage_rows],
            "total_planned": total_planned,
        }
    finally:
        if header:
            _cleanup_stage_policy_header(header.name)
        frappe.db.commit()


def setup_stage_concurrent_process_smoke() -> dict:
    header, item = _make_stage_policy_item("WP3 Concurrent Process Stage Smoke")
    frappe.db.commit()
    return {"success": True, "header": header.name, "boq_item": item.name}


def insert_stage_for_item_smoke(boq_item: str, stage_code: str, planned_qty: float) -> dict:
    stage = frappe.get_doc(
        {
            "doctype": "BOQ Item Stage",
            "boq_item": boq_item,
            "stage_code": stage_code,
            "stage_name": f"Concurrent Process {stage_code}",
            "planned_qty": planned_qty,
            "measured_executed_qty": 0,
            "certified_qty": 0,
            "percent_complete": 0,
            "stage_status": "Not Started",
        }
    ).insert(ignore_permissions=True)
    frappe.db.commit()
    return {
        "success": True,
        "name": stage.name,
        "stage_code": stage.stage_code,
        "planned_qty": stage.planned_qty,
    }


def inspect_stage_concurrent_process_smoke(header: str) -> dict:
    rows = frappe.get_all(
        "BOQ Item Stage",
        filters={"boq_header": header},
        fields=["name", "stage_code", "planned_qty"],
        order_by="stage_code",
    )
    result = {
        "success": len(rows) == 1 and sum(row.planned_qty for row in rows) == 6,
        "header": header,
        "stage_rows": [dict(row) for row in rows],
        "total_planned": sum(row.planned_qty for row in rows),
    }
    _cleanup_stage_policy_header(header)
    frappe.db.commit()
    return result


class TestBOQItemStage(FrappeTestCase):
    def setUp(self):
        self._clear_scope_defaults()
        self.project = self._make_project()
        self.header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "project": self.project,
                "title": "Test BOQ Item Stage",
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)

        self.structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": self.header.name,
                "title": "Stage Test Item",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)

        self.item = frappe.get_doc(
            "BOQ Item",
            frappe.db.get_value("BOQ Item", {"structure": self.structure.name}, "name"),
        )
        self.item.quantity = 10
        self.item.has_stages = 1
        self.item.save(ignore_permissions=True)

    def _clear_scope_defaults(self):
        for key in ("branch", "company", "cost_center", "project", "department"):
            frappe.defaults.clear_user_default(key, "Administrator")

    def _make_project(self):
        company = frappe.db.get_value("Company", {}, "name")
        if not company:
            company = (
                frappe.get_doc(
                    {
                        "doctype": "Company",
                        "company_name": "_Test BOQ Company",
                        "default_currency": "USD",
                        "country": "United States",
                    }
                )
                .insert(ignore_permissions=True)
                .name
            )

        project_name = "_Test BOQ Project"
        project = frappe.db.get_value("Project", {"project_name": project_name}, "name")
        if project:
            return project

        return (
            frappe.get_doc(
                {
                    "doctype": "Project",
                    "project_name": project_name,
                    "company": company,
                    "naming_series": "PROJ-.####",
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

    def _stage(self, **overrides):
        doc = frappe.get_doc(
            {
                "doctype": "BOQ Item Stage",
                "boq_item": self.item.name,
                "stage_code": "S001",
                "stage_name": "Ground Floor",
                "planned_qty": 5,
                "measured_executed_qty": 2,
                "certified_qty": 1,
                "percent_complete": 40,
                "stage_status": "In Progress",
            }
        )
        doc.update(overrides)
        return doc

    def test_valid_stage_fetches_parent_context(self):
        stage = self._stage().insert(ignore_permissions=True)

        self.assertEqual(stage.boq_header, self.header.name)
        self.assertEqual(stage.project, self.project)

    def test_pricing_allows_has_stages_when_quantity_posts_as_zero(self):
        header = frappe.get_doc(
            {
                "doctype": "BOQ Header",
                "project": self.project,
                "title": "Pricing Has Stages",
                "status": "Draft",
                "boq_type": "Tender",
            }
        ).insert(ignore_permissions=True)
        structure = frappe.get_doc(
            {
                "doctype": "BOQ Structure",
                "boq_header": header.name,
                "title": "Pricing Has Stages Item",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        item = frappe.get_doc(
            "BOQ Item",
            frappe.db.get_value("BOQ Item", {"structure": structure.name}, "name"),
        )

        header.status = "Pricing"
        header.save(ignore_permissions=True)

        item.reload()
        item.quantity = 0
        item.has_stages = 1
        item.save(ignore_permissions=True)

        self.assertEqual(item.has_stages, 1)

    def test_duplicate_stage_code_rejected(self):
        self._stage().insert(ignore_permissions=True)

        with self.assertRaises(frappe.ValidationError):
            self._stage(stage_name="Duplicate").insert(ignore_permissions=True)

    def test_quantity_guards(self):
        for fieldname in ("planned_qty", "measured_executed_qty", "certified_qty"):
            with self.assertRaises(frappe.ValidationError):
                self._stage(stage_code=f"NEG-{fieldname}", **{fieldname: -1}).insert(ignore_permissions=True)

        with self.assertRaises(frappe.ValidationError):
            self._stage(stage_code="CERT", measured_executed_qty=2, certified_qty=3).insert(
                ignore_permissions=True
            )

    def test_percent_complete_bounds(self):
        with self.assertRaises(frappe.ValidationError):
            self._stage(stage_code="LOW", percent_complete=-1).insert(ignore_permissions=True)

        with self.assertRaises(frappe.ValidationError):
            self._stage(stage_code="HIGH", percent_complete=101).insert(ignore_permissions=True)

    def test_draft_total_planned_cannot_exceed_parent_quantity(self):
        self._stage(stage_code="S001", planned_qty=6).insert(ignore_permissions=True)

        with self.assertRaises(frappe.ValidationError):
            self._stage(stage_code="S002", planned_qty=5).insert(ignore_permissions=True)

    def test_frozen_requires_exact_distribution(self):
        self.header.status = "Pricing"
        self.header.save(ignore_permissions=True)
        self.header.status = "Frozen"
        self.header.save(ignore_permissions=True)

        with self.assertRaises(frappe.ValidationError):
            self._stage(stage_code="F001", planned_qty=5).insert(ignore_permissions=True)


def _make_stage_policy_item(title: str):
    project = frappe.db.get_value("Project", {}, "name")
    if not project:
        frappe.throw("Stage policy smoke requires at least one Project record.")
    header = frappe.get_doc(
        {
            "doctype": "BOQ Header",
            "project": project,
            "title": title,
            "status": "Draft",
            "boq_type": "Tender",
        }
    ).insert(ignore_permissions=True)
    structure = frappe.get_doc(
        {
            "doctype": "BOQ Structure",
            "boq_header": header.name,
            "title": f"{title} Item",
            "is_group": 0,
        }
    ).insert(ignore_permissions=True)
    item = frappe.get_doc("BOQ Item", frappe.db.get_value("BOQ Item", {"structure": structure.name}, "name"))
    item.quantity = 10
    item.has_stages = 1
    item.save(ignore_permissions=True)
    return header, item


def _make_stage(item, **overrides):
    doc = frappe.get_doc(
        {
            "doctype": "BOQ Item Stage",
            "boq_item": item.name,
            "stage_code": "STG-POL-001",
            "stage_name": "Stage Policy",
            "planned_qty": 10,
            "measured_executed_qty": 0,
            "certified_qty": 0,
            "percent_complete": 0,
            "stage_status": "Not Started",
        }
    )
    doc.update(overrides)
    return doc


def _move_header_to_status(header_name: str, status: str):
    header = frappe.get_doc("BOQ Header", header_name)
    transitions = {"Draft": "Pricing", "Pricing": "Frozen", "Frozen": "Locked"}
    while header.status != status:
        header.status = transitions[header.status]
        header.save(ignore_permissions=True)
        header.reload()


def _try_save_stage(stage_name: str, updates: dict) -> dict:
    try:
        stage = frappe.get_doc("BOQ Item Stage", stage_name)
        stage.update(updates)
        stage.save(ignore_permissions=True)
        return {"success": True}
    except Exception as exc:
        frappe.db.rollback()
        return {"success": False, "error": str(exc)}


def _try_delete_stage(stage_name: str) -> dict:
    try:
        frappe.delete_doc("BOQ Item Stage", stage_name, ignore_permissions=True)
        return {"success": True}
    except Exception as exc:
        frappe.db.rollback()
        return {"success": False, "error": str(exc)}


def _cleanup_stage_policy_header(header_name: str):
    frappe.db.delete("BOQ Item Stage", {"boq_header": header_name})
    frappe.db.delete("BOQ Item", {"boq_header": header_name})
    frappe.db.delete("BOQ Structure", {"boq_header": header_name})
    frappe.db.delete("BOQ Header", {"name": header_name})


def _insert_stage_in_new_connection(site: str, boq_item: str, stage_code: str, planned_qty: float):
    frappe.init(site=site)
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        frappe.db.begin()
        stage = frappe.get_doc(
            {
                "doctype": "BOQ Item Stage",
                "boq_item": boq_item,
                "stage_code": stage_code,
                "stage_name": f"Concurrent {stage_code}",
                "planned_qty": planned_qty,
                "measured_executed_qty": 0,
                "certified_qty": 0,
                "percent_complete": 0,
                "stage_status": "Not Started",
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()
        return {"name": stage.name, "stage_code": stage.stage_code, "planned_qty": stage.planned_qty}
    except Exception:
        frappe.db.rollback()
        raise
    finally:
        frappe.destroy()
