"""Native Stage 1 acceptance for the Project Execution Tree.

These tests require a separately authorized disposable site. They are not part
of the offline validation command.
"""

from __future__ import annotations

import threading
from uuid import uuid4

import frappe
from frappe.tests.utils import FrappeTestCase

from construction.services import execution_tree as service
from construction.services import execution_tree_access as access
from construction.services import execution_tree_rules as rules


def _require_approved_disposable_site():
    # A verified host/bench/site/database/socket allowlist is not implemented.
    # Never replace this with a caller-supplied boolean or site-name check.
    raise RuntimeError("WBS P1 native suite disabled until an approved disposable-site binding is verified.")


class ExecutionTreeTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        _require_approved_disposable_site()
        super().setUpClass()
        cls.company = cls._ensure_company("WBS Tree Company", "WBST1")
        cls.other_company = cls._ensure_company("WBS Tree Other Company", "WBST2")
        cls.project = cls._ensure_project("WBS-TREE-P1", cls.company)
        cls.other_project = cls._ensure_project("WBS-TREE-P2", cls.company)
        cls.manager = cls._ensure_user("wbs.manager@example.test", ["Project Manager", "Projects Manager"])
        cls.system_manager = cls._ensure_user(
            "wbs.system.manager@example.test", ["System Manager", "Projects Manager"]
        )
        cls.engineer = cls._ensure_user("wbs.engineer@example.test", ["Site Engineer", "Projects User"])
        cls.outsider = cls._ensure_user("wbs.outsider@example.test", ["Site Engineer", "Projects User"])
        cls.administrator = "Administrator"
        # Fresh authorization and worker connections cannot see uncommitted fixtures.
        frappe.db.commit()

    @classmethod
    def _ensure_company(cls, name, abbreviation):
        if not frappe.db.exists("Company", name):
            frappe.get_doc({"doctype": "Company", "company_name": name, "abbr": abbreviation}).insert(
                ignore_permissions=True
            )
        return name

    @classmethod
    def _ensure_project(cls, name, company):
        if not frappe.db.exists("Project", name):
            frappe.get_doc(
                {
                    "doctype": "Project",
                    "project_name": name,
                    "name": name,
                    "company": company,
                }
            ).insert(ignore_permissions=True, set_name=name)
        return name

    @classmethod
    def _ensure_user(cls, email, roles):
        if not frappe.db.exists("User", email):
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": email.split("@")[0],
                    "send_welcome_email": 0,
                }
            )
            user.insert(ignore_permissions=True)
            for role in roles:
                user.append("roles", {"role": role})
            user.save(ignore_permissions=True)
        user = frappe.get_doc("User", email)
        actual_roles = {row.role for row in user.roles}
        if not user.enabled or not set(roles).issubset(actual_roles):
            raise RuntimeError(f"Synthetic fixture user {email} has incompatible roles or is disabled.")
        return email

    def setUp(self):
        super().setUp()
        # A separate committed synthetic Project prevents counter and tree
        # state from leaking between tests and into reruns. The disposable
        # lab teardown owns cleanup of committed test fixtures.
        frappe.set_user("Administrator")
        self.project = self._ensure_project(f"WBS-P1-{uuid4().hex[:12]}", self.company)
        frappe.db.commit()
        frappe.set_user(self.manager)

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def _node(self, title, parent=None, group=False):
        expected = None
        if parent:
            expected = frappe.db.get_value(rules.NODE_DOCTYPE, parent, "modified")
        return service.create_node(
            project=self.project,
            title=title,
            is_group=group,
            parent_node=parent,
            expected_parent_modified=str(expected) if expected else None,
        )

    def test_create_derives_company_and_allocates_widening_codes(self):
        first = self._node("Root", group=True)
        second = self._node("Level 1", parent=first["name"])
        assert first["company"] == self.company
        assert first["ebs_code"] == rules.format_execution_code(1)
        assert second["ebs_code"] == rules.format_execution_code(2)

    def test_tree_read_returns_bounded_deterministic_summaries(self):
        root = self._node("Root", group=True)
        self._node("B", parent=root["name"])
        self._node("A", parent=root["name"])
        # get_tree uses an independent authority snapshot and cannot see
        # this connection's uncommitted node inserts.
        frappe.db.commit()
        tree = service.get_tree(self.project)
        assert tree["project"] == self.project
        assert tree["actions"]["read"] is True
        codes = [node["ebs_code"] for node in tree["nodes"]]
        # Children are ordered by numeric execution code, not alphabetically.
        assert codes == sorted(codes)
        names = [node["title"] for node in tree["nodes"]]
        assert names.index("B") < names.index("A")

    def test_cross_project_parent_is_rejected(self):
        other_root = service.create_node(self.other_project, "Other root", True, None, None)
        with self.assertRaises(Exception):
            self._node("Bad", parent=other_root["name"])

    def test_stale_version_is_rejected(self):
        node = self._node("Root", group=True)
        service.update_node(self.project, node["name"], node["modified"], title="Renamed")
        with self.assertRaises(Exception):
            service.update_node(self.project, node["name"], node["modified"], title="Again")

    def test_delete_with_children_is_rejected(self):
        root = self._node("Root", group=True)
        child = self._node("Child", parent=root["name"])
        frappe.set_user(self.system_manager)
        with self.assertRaises(Exception):
            service.delete_node(self.project, root["name"], root["modified"])
        # A manager without System Manager is denied; System Manager may delete.
        frappe.set_user(self.manager)
        with self.assertRaises(Exception):
            service.delete_node(self.project, child["name"], child["modified"])
        frappe.set_user(self.system_manager)
        service.delete_node(self.project, child["name"], child["modified"])

    def test_company_lock_blocks_change_after_first_issue(self):
        self._node("Root", group=True)
        project = frappe.get_doc("Project", self.project)
        project.company = self.other_company
        with self.assertRaises(frappe.ValidationError):
            project.save(ignore_permissions=True)

    def test_counter_is_retained_after_last_node_is_deleted(self):
        node = self._node("Root")
        frappe.set_user(self.system_manager)
        service.delete_node(self.project, node["name"], node["modified"])
        frappe.set_user(self.manager)
        assert frappe.db.exists(rules.COUNTER_DOCTYPE, self.project)
        next_node = self._node("Root again")
        assert rules.parse_execution_code(next_node["ebs_code"]) > 1

    def test_ordinary_generic_routes_are_closed(self):
        frappe.set_user(self.engineer)
        node = None
        frappe.set_user(self.manager)
        node = self._node("Root")
        frappe.set_user(self.engineer)
        assert not _has_permission(rules.NODE_DOCTYPE, "read", self.engineer)
        assert not _has_permission(rules.NODE_DOCTYPE, "write", self.engineer)
        frappe.set_user(self.manager)
        assert node

    def test_concurrent_first_allocation_is_unique(self):
        barrier = threading.Barrier(2)
        results = []
        errors = []
        site, sites_path = frappe.local.site, frappe.local.sites_path

        def worker(index):
            connected = False
            try:
                frappe.init(site=site, sites_path=sites_path)
                frappe.connect()
                connected = True
                frappe.set_user(self.manager)
                barrier.wait(timeout=10)
                results.append(
                    service.create_node(
                        project=self.project,
                        title=f"Race {index}",
                        is_group=False,
                        parent_node=None,
                        expected_parent_modified=None,
                    )["ebs_code"]
                )
                frappe.db.commit()
            except Exception as error:
                if connected:
                    frappe.db.rollback()
                errors.append(error)
            finally:
                frappe.destroy()

        threads = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert all(not thread.is_alive() for thread in threads)
        assert not errors
        assert len(set(results)) == 2
        assert len(frappe.get_all(rules.NODE_DOCTYPE, filters={"project": self.project})) >= 2

    # ------------------------------------------------------------------
    # W02/W03 lifecycle, B1 commit orders, retained history
    # ------------------------------------------------------------------

    def test_project_rename_merge_delete_blocked_with_retained_history(self):
        project = self._ensure_project(f"{self.project}-HIST", self.company)
        frappe.db.commit()
        node = service.create_node(project, "History root", True, None, None)
        frappe.set_user(self.system_manager)
        service.delete_node(project, node["name"], node["modified"])
        frappe.set_user(self.manager)
        with self.assertRaises(frappe.ValidationError):
            frappe.rename_doc("Project", project, f"{project}-RENAMED")
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("Project", project)
        other = self._ensure_project(f"{self.project}-MERGE", self.company)
        with self.assertRaises(frappe.ValidationError):
            frappe.rename_doc("Project", project, other, merge=True)
        # A Project without execution history keeps ordinary lifecycle rights.
        clean = self._ensure_project(f"{self.project}-CLEAN", self.company)
        frappe.rename_doc("Project", clean, f"{clean}-RENAMED")
        frappe.delete_doc("Project", f"{clean}-RENAMED")

    def test_b1_company_correction_before_first_issue_and_lock_after(self):
        project = self._ensure_project(f"{self.project}-B1", self.company)
        doc = frappe.get_doc("Project", project)
        doc.company = self.other_company
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        node = service.create_node(project, "First issue", False, None, None)
        assert node["company"] == self.other_company
        empty = frappe.get_doc("Project", project)
        frappe.set_user(self.system_manager)
        service.delete_node(project, node["name"], node["modified"])
        frappe.set_user(self.manager)
        locked = frappe.get_doc("Project", project)
        locked.company = self.company
        with self.assertRaises(frappe.ValidationError):
            locked.save(ignore_permissions=True)

    def _race_worker(self, fn, results, key, site, sites_path, committed=None):
        connected = False
        try:
            frappe.init(site=site, sites_path=sites_path)
            frappe.connect()
            connected = True
            frappe.set_user(self.manager)
            results[key] = fn()
            frappe.db.commit()
            if committed is not None:
                committed.set()
        except Exception as error:
            if connected:
                frappe.db.rollback()
            results[key] = error
        finally:
            frappe.destroy()

    def test_b1_allocation_commits_first_then_company_edit_refused(self):
        project = self._ensure_project(f"{self.project}-RACE-A", self.company)
        frappe.db.commit()
        allocated = threading.Event()
        results = {}
        site, sites_path = frappe.local.site, frappe.local.sites_path

        def allocate():
            return service.create_node(project, "Race root", True, None, None)

        def edit():
            if not allocated.wait(timeout=10):
                raise TimeoutError("Allocation did not commit before the Company edit.")
            doc = frappe.get_doc("Project", project)
            doc.company = self.other_company
            doc.save(ignore_permissions=True)
            return "committed"

        threads = [
            threading.Thread(
                target=self._race_worker, args=(allocate, results, "alloc", site, sites_path, allocated)
            ),
            threading.Thread(target=self._race_worker, args=(edit, results, "edit", site, sites_path)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert all(not thread.is_alive() for thread in threads)
        assert isinstance(results["alloc"], dict)
        assert results["alloc"]["company"] == self.company
        assert isinstance(results["edit"], frappe.ValidationError)
        assert frappe.db.get_value("Project", project, "company") == self.company

    def test_b1_company_edit_commits_first_then_allocation_derives_new_company(self):
        project = self._ensure_project(f"{self.project}-RACE-B", self.company)
        frappe.db.commit()
        edited = threading.Event()
        results = {}
        site, sites_path = frappe.local.site, frappe.local.sites_path

        def edit():
            doc = frappe.get_doc("Project", project)
            doc.company = self.other_company
            doc.save(ignore_permissions=True)
            return "committed"

        def allocate():
            if not edited.wait(timeout=10):
                raise TimeoutError("Company edit did not commit before allocation.")
            return service.create_node(project, "Race root", True, None, None)

        threads = [
            threading.Thread(
                target=self._race_worker, args=(edit, results, "edit", site, sites_path, edited)
            ),
            threading.Thread(target=self._race_worker, args=(allocate, results, "alloc", site, sites_path)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert all(not thread.is_alive() for thread in threads)
        assert results["edit"] == "committed"
        assert isinstance(results["alloc"], dict)
        assert results["alloc"]["company"] == self.other_company
        assert frappe.db.get_value("Project", project, "company") == self.other_company

    def test_counter_overflow_and_widening_on_retained_state(self):
        project = self._ensure_project(f"{self.project}-OVERFLOW", self.company)
        frappe.db.commit()
        service.create_node(project, "Seed", False, None, None)
        frappe.db.set_value(rules.COUNTER_DOCTYPE, project, "last_issued", rules.MAX_COUNTER_VALUE)
        frappe.db.commit()
        with self.assertRaises(frappe.ValidationError):
            service.create_node(project, "Overflow", False, None, None)
        assert frappe.db.get_value(rules.COUNTER_DOCTYPE, project, "last_issued") == rules.MAX_COUNTER_VALUE
        wide = self._ensure_project(f"{self.project}-WIDE", self.company)
        frappe.db.commit()
        service.create_node(wide, "Seed", False, None, None)
        frappe.db.set_value(rules.COUNTER_DOCTYPE, wide, "last_issued", 9999)
        frappe.db.commit()
        node = service.create_node(wide, "Widened", False, None, None)
        assert node["ebs_code"] == "EBS-10000"

    # ------------------------------------------------------------------
    # W04 freshness, revocation, generic/share closure, guard cleanup
    # ------------------------------------------------------------------

    def test_committed_revocation_from_second_connection_denies_new_requests(self):
        frappe.set_user(self.engineer)
        assert service.get_tree(self.project)["project"] == self.project
        barrier = threading.Barrier(2)
        errors = []
        restore_errors = []
        site, sites_path = frappe.local.site, frappe.local.sites_path

        def revoke():
            connected = False
            try:
                frappe.init(site=site, sites_path=sites_path)
                frappe.connect()
                connected = True
                frappe.db.delete("Has Role", {"parent": self.engineer, "role": "Site Engineer"})
                frappe.db.commit()
                barrier.wait(timeout=10)
            except Exception as error:
                if connected:
                    frappe.db.rollback()
                errors.append(error)
            finally:
                frappe.destroy()

        def restore():
            connected = False
            try:
                frappe.init(site=site, sites_path=sites_path)
                frappe.connect()
                connected = True
                if not frappe.db.exists("Has Role", {"parent": self.engineer, "role": "Site Engineer"}):
                    frappe.get_doc(
                        {
                            "doctype": "Has Role",
                            "parent": self.engineer,
                            "parenttype": "User",
                            "parentfield": "roles",
                            "role": "Site Engineer",
                        }
                    ).insert(ignore_permissions=True)
                frappe.db.commit()
            except Exception as error:
                if connected:
                    frappe.db.rollback()
                restore_errors.append(error)
            finally:
                frappe.destroy()

        thread = threading.Thread(target=revoke)

        def ensure_restored():
            thread.join(timeout=30)
            if thread.is_alive():
                raise RuntimeError("Revocation worker did not exit; restoration cannot safely start.")
            restore_thread = threading.Thread(target=restore)
            restore_thread.start()
            restore_thread.join(timeout=30)
            if restore_thread.is_alive() or restore_errors:
                raise RuntimeError("Role restoration failed or timed out.") from (
                    restore_errors[0] if restore_errors else None
                )

        thread.start()
        self.addCleanup(ensure_restored)
        barrier.wait(timeout=10)
        thread.join(timeout=30)
        assert not thread.is_alive() and not errors
        with self.assertRaises(frappe.PermissionError):
            service.get_tree(self.project)
        with self.assertRaises(frappe.PermissionError):
            service.create_node(self.project, "Revoked", False, None, None)
        ensure_restored()
        assert service.get_tree(self.project)["project"] == self.project

    def test_measurement_only_user_is_denied_despite_native_read(self):
        user = self._ensure_user("wbs.measurement@example.test", ["Projects User"])
        frappe.db.commit()
        # Prove the independent authority reader sees the enabled principal and
        # intended roles; otherwise a missing user could masquerade as denial.
        with access.FreshAuthorityReader() as reader:
            user_row = access._read_user(reader, user)
            roles = set(access._read_roles(reader, user, user_row.get("user_type")))
            assert "Projects User" in roles
            assert not roles.intersection({"Site Engineer", "Project Manager", "System Manager"})
        frappe.set_user(user)
        assert frappe.has_permission("Project", ptype="read", doc=self.project)
        with self.assertRaises(frappe.PermissionError):
            service.get_tree(self.project)

    def test_guard_is_cleared_after_exception_and_generic_access_stays_closed(self):
        with self.assertRaises(Exception):
            service.create_node(self.project, "Bad parent", False, "EBN-99999", "2026-11-18 00:00:00.000000")
        assert access.current_guard() is None
        assert not frappe.has_permission(rules.NODE_DOCTYPE, ptype="read", user=self.manager)
        assert not frappe.has_permission(rules.COUNTER_DOCTYPE, ptype="read", user=self.manager)

    def test_generic_set_value_and_list_routes_are_closed(self):
        node = self._node("Generic target")
        with self.assertRaises(frappe.PermissionError):
            frappe.client.set_value(rules.NODE_DOCTYPE, node["name"], "title", "Hijacked")
        rows = frappe.client.get_list(rules.NODE_DOCTYPE, filters={"project": self.project}, fields=["name"])
        assert not rows
        with self.assertRaises(frappe.PermissionError):
            frappe.client.set_value(rules.COUNTER_DOCTYPE, self.project, "last_issued", 0)

    def test_protected_share_is_rejected_and_not_persisted(self):
        node = self._node("Share target")
        with self.assertRaises(frappe.PermissionError):
            frappe.share.add(rules.NODE_DOCTYPE, node["name"], self.engineer, read=1)
        assert not frappe.db.count(
            "DocShare", {"share_doctype": rules.NODE_DOCTYPE, "share_name": node["name"]}
        )
        with self.assertRaises(frappe.PermissionError):
            frappe.share.add(rules.COUNTER_DOCTYPE, self.project, self.engineer, read=1)

    def test_stale_parent_version_is_rejected(self):
        root = self._node("Root", group=True)
        service.update_node(self.project, root["name"], root["modified"], title="Root renamed")
        with self.assertRaises(Exception):
            service.create_node(
                self.project,
                "Child",
                False,
                root["name"],
                root["modified"],
            )

    def test_move_to_root_and_disabled_marker_semantics(self):
        root = self._node("Root", group=True)
        child = self._node("Child", parent=root["name"])
        moved = service.move_node(self.project, child["name"], child["modified"], None, None)
        assert moved["parent_node"] is None
        disabled = service.set_disabled(self.project, child["name"], moved["modified"], True)
        assert disabled["disabled"] == 1
        assert disabled["title"] == child["title"]
        frappe.db.commit()
        tree = service.get_tree(self.project)
        listed = next(item for item in tree["nodes"] if item["name"] == child["name"])
        assert listed["disabled"] == 1
        enabled = service.set_disabled(self.project, child["name"], disabled["modified"], False)
        assert enabled["disabled"] == 0


def _has_permission(doctype, ptype, user):
    return frappe.has_permission(doctype, ptype=ptype, user=user)
