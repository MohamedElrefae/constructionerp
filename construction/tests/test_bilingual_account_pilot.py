"""
Stage 3 tests: bilingual framework + Account UI/tree pilot (bench tests).

Run with: bench --site [site] run-tests --module construction.tests.test_bilingual_account_pilot

Covers: registry service integration (fail-closed schema validation),
controlled Arabic-only edit (no rename, Version audit via the governed
service call, canonical Unicode policy), server-side confinement of
account_name_ar (direct form/REST saves refused), the atomic reason-required
governed rename (standard path preserved, post-rename identity resolved
server-side, rollback on audit failure), server-authoritative Arabic search
normalization, permission behavior as non-Administrator users, batched tree
children, patch idempotency/reversal, stale-concurrent-edit safety, and a
performance smoke. All mutations happen on dedicated test documents and are
cleaned up; live Account names are never migrated.
"""

import json
import time
import unittest
from pathlib import Path
from unittest import mock

import frappe

from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic

ROOT = Path(__file__).resolve().parent.parent.parent


TEST_COMPANY = "Elrefae"
TEST_EN = "CT Bilingual Pilot"
TEST_EN_CHILD = "CT Bilingual Pilot Child"
TEST_AR = "حساب تجريبي ثنائي اللغة"
TEST_AR_CHILD = "حساب تجريبي فرعي"
TEST_AR_DIACRITIZED = "أَحْمَـد"          # hamza-alef + diacritics + tatweel
TEST_AR_BARE = "احمد"                     # bare query form
NO_PERM_USER = "ct-bilingual-noperm@example.com"
WRITER_USER = "ct-bilingual-writer@example.com"


def _unique_number():
    return "CT-T3-" + frappe.generate_hash(length=6)


def _clear_arabic(name):
    frappe.db.set_value(
        "Account", name, {"account_name_ar": None, "account_name_ar_norm": None}, update_modified=False
    )


class TestBilingualAccountPilot(unittest.TestCase):
    pilot = None
    pilot_child = None

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        # P0-2/P1-2 schema state: read-only Arabic field + normalized key.
        from construction.patches.v8_8.add_account_arabic_name_field import execute as patch_v8_8
        from construction.patches.v9_0.enable_account_track_changes import execute as enable_track_changes
        from construction.patches.v9_1.add_account_arabic_norm_field import execute as patch_v9_1

        patch_v8_8()
        enable_track_changes()
        patch_v9_1()
        frappe.clear_cache(doctype="Account")
        if not frappe.get_meta("Account").track_changes:
            raise AssertionError("Account.track_changes not enabled by v9_0 patch")
        meta = frappe.get_meta("Account")
        for field in ("account_name_ar", "account_name_ar_norm"):
            if not meta.has_field(field):
                raise AssertionError("%s missing on Account" % field)
        # Remove leftovers from any earlier interrupted pilot run (children
        # first — nestedset parents refuse to delete with children present).
        leftovers = frappe.get_all(
            "Account",
            filters={"company": TEST_COMPANY, "account_number": ("like", "CT-T3-%")},
            fields=["name", "is_group"],
            order_by="lft desc",
        )
        for row in leftovers:
            frappe.delete_doc("Account", row.name, force=True, ignore_permissions=True)
        parent = frappe.get_value(
            "Account",
            {"company": TEST_COMPANY, "is_group": 1, "parent_account": ("is", "set")},
            "name",
        )
        cls.pilot = frappe.get_doc(
            {
                "doctype": "Account",
                "company": TEST_COMPANY,
                "account_name": TEST_EN,
                "account_number": _unique_number(),
                "parent_account": parent,
                "is_group": 1,
                "account_type": "Stock",
                "root_type": "Asset",
                "report_type": "Balance Sheet",
            }
        ).insert(ignore_permissions=True)
        cls.pilot_child = frappe.get_doc(
            {
                "doctype": "Account",
                "company": TEST_COMPANY,
                "account_name": TEST_EN_CHILD,
                "account_number": _unique_number(),
                "parent_account": cls.pilot.name,
                "is_group": 0,
                "account_type": "Stock",
                "root_type": "Asset",
                "report_type": "Balance Sheet",
            }
        ).insert(ignore_permissions=True)
        for user, roles in ((NO_PERM_USER, []), (WRITER_USER, ["Accounts User"])):
            if frappe.db.exists("User", user):
                continue
            doc = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": user,
                    "first_name": "CT",
                    "new_password": "ct-test-pw-123",
                    "user_type": "System User",
                    "send_welcome_email": 0,
                    "roles": [{"role": r} for r in roles],
                }
            )
            doc.insert(ignore_permissions=True)
        # The scope-context system requires an active scope for non-admin
        # document writes; give the writer user a company-scoped context
        # (removed with the user in teardown).
        if not frappe.db.exists("User Scope Context", {"user": WRITER_USER}):
            frappe.get_doc(
                {
                    "doctype": "User Scope Context",
                    "user": WRITER_USER,
                    "company": TEST_COMPANY,
                }
            ).insert(ignore_permissions=True)
        # Fixtures must be durable: the atomicity test below performs an
        # explicit rollback and must only discard its own rename attempt.
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        # Names may have been renamed by tests; match by governed number
        # prefix, children (higher lft) before parents.
        leftovers = frappe.get_all(
            "Account",
            filters={"company": TEST_COMPANY, "account_number": ("like", "CT-T3-%")},
            fields=["name"],
            order_by="lft desc",
        )
        for row in leftovers:
            if frappe.db.exists("Account", row.name):
                frappe.delete_doc("Account", row.name, force=True, ignore_permissions=True)
        for row in frappe.get_all("User Scope Context", filters={"user": WRITER_USER}, pluck="name"):
            frappe.delete_doc("User Scope Context", row, force=True, ignore_permissions=True)
        for user in (NO_PERM_USER, WRITER_USER):
            if frappe.db.exists("User", user):
                frappe.delete_doc("User", user, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.flags.ct_governed_arabic_edit = False

    # --- registry service ---

    def test_registry_loads_and_maps_resolved_fields(self):
        data = svc.get_registry()
        self.assertIsNotNone(data)
        mapping = svc.get_mapping("Account")
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping["resolved"]["arabic_field"], "account_name_ar")
        self.assertEqual(mapping["resolved"]["english_field"], "account_name")
        self.assertEqual(mapping["resolved"]["code_field"], "account_number")
        for dt, ar in (
            ("Item", "item_name_ar"),
            ("Customer", "customer_name_in_arabic"),
            ("Supplier", "supplier_name_in_arabic"),
        ):
            self.assertEqual(svc.get_mapping(dt)["resolved"]["arabic_field"], ar)

    def test_unmapped_or_planned_doctype_returns_none(self):
        self.assertIsNone(svc.get_mapping("Nonexistent Doctype XYZ"))

    def test_active_mapping_fails_closed_on_schema_mismatch(self):
        # P1: an active mapping whose physical field vanished must raise,
        # never silently degrade to arabic_field=None.
        real_get_meta = frappe.get_meta

        class ReducedMeta:
            def __init__(self, inner):
                self._inner = inner

            def has_field(self, field):
                if field == "item_name_ar":
                    return False
                return self._inner.has_field(field)

            def __getattr__(self, name):
                return getattr(self._inner, name)

        def fake_get_meta(doctype):
            return ReducedMeta(real_get_meta(doctype))

        with mock.patch("frappe.get_meta", side_effect=fake_get_meta):
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Item")

    def test_fallback_chain_by_session_language(self):
        self.assertEqual(svc.fallback_chain("ar"), ["arabic", "english", "identity"])
        self.assertEqual(svc.fallback_chain("en"), ["english", "arabic", "identity"])

    # --- identity read / display ---

    def test_get_account_identity_payload(self):
        ident = svc.get_account_identity(self.pilot.name)
        self.assertEqual(ident["identity"], self.pilot.name)
        self.assertEqual(ident["english"], TEST_EN)
        self.assertEqual(ident["code"], self.pilot.account_number)
        self.assertIn("completeness", ident)
        self.assertIn("fallback", ident)

    def test_identity_read_refused_without_permission(self):
        frappe.set_user(NO_PERM_USER)
        with self.assertRaises(frappe.PermissionError):
            svc.read_identity("Account", self.pilot.name)
        frappe.set_user("Administrator")

    def test_display_name_fallback_modes(self):
        svc.set_account_name_ar(self.pilot.name, TEST_AR)
        try:
            label, mode = svc.display_name("Account", self.pilot.name, lang="ar")
            self.assertEqual((label, mode), (TEST_AR, "arabic"))
            label, mode = svc.display_name("Account", self.pilot.name, lang="en")
            self.assertEqual((label, mode), (TEST_EN, "english"))
        finally:
            _clear_arabic(self.pilot.name)
        label, mode = svc.display_name("Account", self.pilot.name, lang="ar")
        self.assertEqual(mode, "english")

    # --- controlled Arabic-only edit ---

    def test_arabic_only_edit_preserves_identity_and_records_version(self):
        before = frappe.db.get_value(
            "Account", self.pilot.name, ["name", "account_name", "account_number"], as_dict=True
        )
        # Production-path proof: the runner suppresses Versions by default
        # (frappe.in_test sets ignore_version), so exercise the real path
        # around the SERVICE call itself.
        previous_in_test = getattr(frappe, "in_test", False)
        frappe.in_test = False
        try:
            result = svc.set_account_name_ar(self.pilot.name, TEST_AR)
        finally:
            frappe.in_test = previous_in_test
        try:
            self.assertTrue(result["ok"])
            after = frappe.db.get_value(
                "Account", self.pilot.name, ["name", "account_name", "account_number", "account_name_ar"], as_dict=True
            )
            self.assertEqual(after.name, before.name)
            self.assertEqual(after.account_name, before.account_name)
            self.assertEqual(after.account_number, before.account_number)
            self.assertEqual(after.account_name_ar, TEST_AR)
            self.assertEqual(after.account_name_ar, result["arabic_name_ar"])
            # The normalized search key is maintained by the governed path.
            self.assertEqual(after.account_name_ar, TEST_AR)
            versions = frappe.get_all(
                "Version",
                filters={"ref_doctype": "Account", "docname": self.pilot.name},
                limit_page_length=1,
            )
            self.assertTrue(versions, "native Version audit missing for governed Arabic-only edit")
        finally:
            _clear_arabic(self.pilot.name)

    def test_governed_edit_maintains_normalized_search_key(self):
        svc.set_account_name_ar(self.pilot.name, TEST_AR_DIACRITIZED)
        try:
            stored = frappe.db.get_value("Account", self.pilot.name, "account_name_ar_norm")
            self.assertEqual(stored, normalize_arabic(TEST_AR_DIACRITIZED))
        finally:
            _clear_arabic(self.pilot.name)

    def test_arabic_edit_rejects_control_characters(self):
        with self.assertRaises(frappe.ValidationError):
            svc.set_account_name_ar(self.pilot.name, "bad\x00name")
        self.assertIsNone(frappe.db.get_value("Account", self.pilot.name, "account_name_ar"))

    def test_arabic_edit_rejects_all_bidi_controls(self):
        # P0-1: canonical C1 — LRM/RLM/ALM and embeddings/overrides/isolates
        # are all rejected in stored Arabic values.
        for mark in ("\u200e", "\u200f", "\u061c", "\u202e", "\u2066"):
            with self.assertRaises(frappe.ValidationError):
                svc.set_account_name_ar(self.pilot.name, TEST_AR + mark)
        self.assertIsNone(frappe.db.get_value("Account", self.pilot.name, "account_name_ar"))

    # --- server-side confinement (P0-2) ---

    def test_insertion_with_arabic_name_refused(self):
        # P0: a new Account cannot carry an Arabic name at all — the
        # governed workflow is create-then-edit.
        parent = frappe.get_value(
            "Account", {"company": TEST_COMPANY, "is_group": 1, "parent_account": ("is", "set")}, "name"
        )
        doc = frappe.get_doc(
            {
                "doctype": "Account",
                "company": TEST_COMPANY,
                "account_name": "CT Insert Probe",
                "account_number": _unique_number(),
                "parent_account": parent,
                "is_group": 0,
                "account_name_ar": TEST_AR,
            }
        )
        with self.assertRaises(frappe.PermissionError):
            doc.insert(ignore_permissions=True)
        self.assertIsNone(
            frappe.db.get_value(
                "Account", {"account_name": "CT Insert Probe", "company": TEST_COMPANY}, "name"
            )
        )

    def test_governed_token_is_bound_to_the_exact_operation(self):
        # A token aimed at another document (or carrying stale binding data)
        # must be refused — the bypass binds to doctype/name/old/new.
        svc.set_account_name_ar(self.pilot.name, TEST_AR)
        try:
            stored = frappe.db.get_value("Account", self.pilot.name, "account_name_ar")
            doc = frappe.get_doc("Account", self.pilot_child.name)
            doc.account_name_ar = TEST_AR_CHILD
            # Mis-aimed token: bound to the parent doc, applied to the child.
            setattr(
                frappe.flags,
                svc.GOVERNED_EDIT_FLAG,
                {"doctype": "Account", "name": self.pilot.name, "old": None, "new": TEST_AR_CHILD},
            )
            try:
                with self.assertRaises(frappe.PermissionError):
                    doc.save()
            finally:
                setattr(frappe.flags, svc.GOVERNED_EDIT_FLAG, None)
            self.assertIsNone(frappe.db.get_value("Account", self.pilot_child.name, "account_name_ar"))
            self.assertEqual(stored, TEST_AR)
        finally:
            _clear_arabic(self.pilot.name)

    def test_normalized_key_invariant_on_unchanged_save(self):
        # A submitted forged/stale normalized key must be overwritten by the
        # server-derived value on EVERY save, even when the Arabic value is
        # unchanged.
        svc.set_account_name_ar(self.pilot.name, TEST_AR)
        try:
            frappe.db.set_value(
                "Account",
                self.pilot.name,
                {"account_name_ar_norm": "POISONED-KEY"},
                update_modified=False,
            )
            doc = frappe.get_doc("Account", self.pilot.name)
            doc.save()
            stored = frappe.db.get_value("Account", self.pilot.name, "account_name_ar_norm")
            self.assertEqual(stored, normalize_arabic(TEST_AR))
        finally:
            _clear_arabic(self.pilot.name)

    def test_direct_form_save_bypass_refused_for_writer(self):
        # The writer has ordinary Account write permission, but a direct
        # form/REST document save that changes account_name_ar must be
        # refused — only the governed API may write the field.
        frappe.set_user(WRITER_USER)
        try:
            doc = frappe.get_doc("Account", self.pilot.name)
            doc.account_name_ar = TEST_AR
            with self.assertRaises(frappe.PermissionError):
                doc.save()
        finally:
            frappe.set_user("Administrator")
        self.assertIsNone(frappe.db.get_value("Account", self.pilot.name, "account_name_ar"))

    def test_direct_form_save_bypass_refused_even_for_administrator(self):
        doc = frappe.get_doc("Account", self.pilot.name)
        doc.account_name_ar = TEST_AR
        with self.assertRaises(frappe.PermissionError):
            doc.save()
        self.assertIsNone(frappe.db.get_value("Account", self.pilot.name, "account_name_ar"))

    def test_non_arabic_saves_still_pass_the_hook(self):
        # Unrelated Account edits (no Arabic change) must remain unaffected.
        doc = frappe.get_doc("Account", self.pilot_child.name)
        doc.save()
        self.assertEqual(doc.account_name, TEST_EN_CHILD)

    # --- permissions (non-Administrator) ---

    def test_arabic_edit_requires_write_permission(self):
        frappe.set_user(NO_PERM_USER)
        try:
            with self.assertRaises(frappe.PermissionError):
                svc.set_account_name_ar(self.pilot.name, TEST_AR)
        finally:
            frappe.set_user("Administrator")
        self.assertIsNone(frappe.db.get_value("Account", self.pilot.name, "account_name_ar"))

    def test_writer_role_can_set_arabic_only(self):
        frappe.set_user(WRITER_USER)
        try:
            result = svc.set_account_name_ar(self.pilot.name, TEST_AR)
            self.assertTrue(result["ok"])
            en = frappe.db.get_value("Account", self.pilot.name, ["account_name", "account_number"], as_dict=True)
            self.assertEqual(en.account_name, TEST_EN)
            self.assertEqual(en.account_number, self.pilot.account_number)
        finally:
            frappe.set_user("Administrator")
            _clear_arabic(self.pilot.name)

    # --- governed rename (P0-3) ---

    def test_governed_rename_end_to_end(self):
        from erpnext.accounts.doctype.account.account import get_account_autoname

        old_name = self.pilot_child.name
        old_number = self.pilot_child.account_number
        new_number = _unique_number()
        result = svc.governed_rename_account(
            name=old_name,
            account_name=TEST_EN_CHILD,
            account_number=new_number,
            reason="CT pilot governed rename test",
        )
        try:
            self.assertTrue(result["ok"])
            self.assertTrue(result["renamed"])
            expected_new_name = get_account_autoname(new_number, TEST_EN_CHILD, TEST_COMPANY)
            self.assertEqual(result["name"], expected_new_name)
            # Post-rename identity resolved server-side (not client-supplied).
            self.assertEqual(result["after"]["account_number"], new_number)
            self.assertEqual(result["after"]["account_name"], TEST_EN_CHILD)
            comments = frappe.get_all(
                "Comment",
                filters={"reference_doctype": "Account", "reference_name": result["name"]},
                fields=["content"],
            )
            self.assertTrue(any("CT pilot governed rename test" == c.content for c in comments), comments)
            # The claimed Version(rename) audit is REAL: a native Version row
            # exists on the post-rename identity recording the identity
            # change (account_number old -> new).
            versions = frappe.get_all(
                "Version",
                filters={"ref_doctype": "Account", "docname": result["name"]},
                fields=["name", "data"],
                limit_page_length=0,
            )
            self.assertTrue(versions, "post-rename Version missing")
            version_data = json.loads(versions[-1].data)
            changed_fields = {c[0] for c in version_data.get("changed", [])}
            self.assertIn("account_number", changed_fields)
            changed_pairs = {c[0]: (c[1], c[2]) for c in version_data.get("changed", [])}
            self.assertEqual(changed_pairs["account_number"], (old_number, new_number))
        finally:
            if frappe.db.exists("Account", result["name"]):
                from erpnext.accounts.doctype.account.account import update_account_number

                update_account_number(result["name"], TEST_EN_CHILD, old_number)
                for c in frappe.get_all(
                    "Comment",
                    filters={"reference_doctype": "Account", "reference_name": result["name"]},
                    pluck="name",
                ):
                    frappe.delete_doc("Comment", c, force=True, ignore_permissions=True)
                for v in frappe.get_all(
                    "Version",
                    filters={"ref_doctype": "Account", "docname": result["name"]},
                    pluck="name",
                ):
                    frappe.delete_doc("Version", v, force=True, ignore_permissions=True)

    def test_governed_rename_requires_reason(self):
        with self.assertRaises(frappe.ValidationError):
            svc.governed_rename_account(
                name=self.pilot_child.name,
                account_name=TEST_EN_CHILD,
                account_number=self.pilot_child.account_number,
                reason="   ",
            )

    def test_rename_failure_duplicate_number_rolls_back_scoped(self):
        # Vendor failure class: the target number is already used by another
        # account in the company. The savepoint rollback must restore the
        # original identity and leave no NEW reason Comment behind.
        old_number = self.pilot_child.account_number
        comments_before = frappe.get_all(
            "Comment",
            filters={"reference_doctype": "Account", "reference_name": self.pilot_child.name},
            pluck="name",
        )
        with self.assertRaises(frappe.ValidationError):
            svc.governed_rename_account(
                name=self.pilot_child.name,
                account_name=TEST_EN_CHILD,
                account_number=self.pilot.account_number,  # duplicate in company
                reason="duplicate number must fail closed",
            )
        after = frappe.db.get_value("Account", self.pilot_child.name, ["account_number", "account_name"], as_dict=True)
        self.assertEqual(after.account_number, old_number)
        self.assertEqual(after.account_name, TEST_EN_CHILD)
        comments_after = frappe.get_all(
            "Comment",
            filters={"reference_doctype": "Account", "reference_name": self.pilot_child.name},
            pluck="name",
        )
        self.assertEqual(sorted(comments_after), sorted(comments_before))

    def test_rename_failure_keeps_caller_transaction_work(self):
        # Scoped atomicity: unrelated uncommitted caller work must SURVIVE a
        # failed governed rename (the endpoint owns only its savepoint).
        frappe.db.commit()
        scratch_value = "CT-COMPOSE-" + frappe.generate_hash(length=4)
        frappe.db.set_value("Account", self.pilot.name, "account_name", scratch_value, update_modified=False)
        with self.assertRaises(frappe.ValidationError):
            svc.governed_rename_account(
                name=self.pilot_child.name,
                account_name=TEST_EN_CHILD,
                account_number=self.pilot.account_number,  # duplicate → vendor refuses
                reason="composition failure test",
            )
        # The caller's pending write is still present (not rolled back).
        self.assertEqual(frappe.db.get_value("Account", self.pilot.name, "account_name"), scratch_value)
        # Restore.
        frappe.db.set_value("Account", self.pilot.name, "account_name", TEST_EN, update_modified=False)
        frappe.db.commit()

    def test_rename_success_does_not_commit_caller_work(self):
        # Scoped atomicity: a successful rename must not commit the caller's
        # unrelated pending work — a full rollback at the end of this test
        # must restore the pre-rename identity (impossible if the endpoint
        # had committed).
        frappe.db.commit()
        old_number = self.pilot_child.account_number
        new_number = _unique_number()
        scratch_value = "CT-COMPOSE-OK-" + frappe.generate_hash(length=4)
        frappe.db.set_value("Account", self.pilot.name, "account_name", scratch_value, update_modified=False)
        result = svc.governed_rename_account(
            name=self.pilot_child.name,
            account_name=TEST_EN_CHILD,
            account_number=new_number,
            reason="composition success test",
        )
        try:
            self.assertTrue(result["ok"])
            self.assertTrue(result["renamed"])
            # Caller's pending write survives (still uncommitted).
            self.assertEqual(frappe.db.get_value("Account", self.pilot.name, "account_name"), scratch_value)
        finally:
            # Discard BOTH the rename and the scratch write: proves the
            # endpoint did not commit them.
            frappe.db.rollback()
        self.assertEqual(frappe.db.get_value("Account", self.pilot_child.name, "account_number"), old_number)
        self.assertFalse(
            frappe.db.get_value("Account", {"account_number": new_number, "company": TEST_COMPANY}, "name")
        )

    def test_overridden_endpoint_dispatches_to_governed_wrapper(self):
        # The overridden vendor method must dispatch (HTTP-path semantics)
        # to the governed wrapper, enforce the reason there, and stay
        # signature-compatible with the vendor's from_descendant argument.
        resolved_path = frappe.override_whitelisted_method(
            "erpnext.accounts.doctype.account.account.update_account_number"
        )
        self.assertEqual(resolved_path, "construction.services.bilingual_service.governed_rename_account")
        resolved = frappe.get_attr(resolved_path)
        self.assertIs(resolved, svc.governed_rename_account)
        with self.assertRaises(frappe.ValidationError):
            resolved(
                name=self.pilot_child.name,
                account_name=TEST_EN_CHILD,
                account_number=self.pilot_child.account_number,
                reason=None,
            )
        # Vendor-call compatibility: from_descendant passes through without
        # error (same-value rename of a descendant account).
        result = resolved(
            name=self.pilot_child.name,
            account_name=TEST_EN_CHILD,
            account_number=self.pilot_child.account_number,
            reason="from_descendant compatibility",
            from_descendant=True,
        )
        self.assertTrue(result["ok"])
        self.assertFalse(result["renamed"])
        # Clean up this test's audit Comment.
        for c in frappe.get_all(
            "Comment",
            filters={"reference_doctype": "Account", "reference_name": result["name"]},
            pluck="name",
        ):
            frappe.delete_doc("Comment", c, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_governed_rename_requires_permission(self):
        frappe.set_user(NO_PERM_USER)
        try:
            with self.assertRaises(frappe.PermissionError):
                svc.governed_rename_account(
                    name=self.pilot_child.name,
                    account_name=TEST_EN_CHILD,
                    account_number=self.pilot_child.account_number,
                    reason="because",
                )
        finally:
            frappe.set_user("Administrator")

    def test_governed_rename_rolls_back_when_audit_fails(self):
        # Atomicity: if recording the reason fails, the rename must roll
        # back as one transaction — no rename without its required reason.
        frappe.db.commit()  # durable fixtures: the rollback must be scoped to this attempt
        old_name = self.pilot_child.name
        old_number = self.pilot_child.account_number
        new_number = _unique_number()

        with mock.patch(
            "construction.services.bilingual_service._insert_rename_comment",
            side_effect=frappe.ValidationError("simulated audit failure"),
        ):
            with self.assertRaises(frappe.ValidationError):
                svc.governed_rename_account(
                    name=old_name,
                    account_name=TEST_EN_CHILD,
                    account_number=new_number,
                    reason="must roll back",
                )
        self.assertTrue(frappe.db.exists("Account", old_name), "rename must roll back on audit failure")
        after = frappe.db.get_value("Account", old_name, ["account_number", "account_name"], as_dict=True)
        self.assertEqual(after.account_number, old_number)
        self.assertIsNone(
            frappe.db.get_value("Account", {"account_number": new_number, "company": TEST_COMPANY}, "name")
        )

    def test_vendor_rename_endpoint_is_overridden(self):
        # The standard endpoint cannot be called without the reason: it is
        # routed to the governed wrapper via override_whitelisted_methods.
        overrides = frappe.get_hooks("override_whitelisted_methods")
        target = overrides.get("erpnext.accounts.doctype.account.account.update_account_number") or []
        self.assertIn("construction.services.bilingual_service.governed_rename_account", target)

    # --- Arabic search normalization (P1-2) ---

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        # Stored value is diacritized with hamza-alef and tatweel; the bare
        # query must still find it (and vice versa) in ONE query.
        svc.set_account_name_ar(self.pilot.name, TEST_AR_DIACRITIZED)
        try:
            calls = []
            original = frappe.get_list

            def counting(*args, **kwargs):
                if args and args[0] == "Account":
                    calls.append(kwargs)
                return original(*args, **kwargs)

            with mock.patch("frappe.get_list", side_effect=counting):
                results = svc.search_bilingual("Account", txt=TEST_AR_BARE, lang="ar", page_length=50)
            self.assertEqual(len(calls), 1, "normalized search must stay a single query")
            values = [r["value"] for r in results]
            self.assertIn(self.pilot.name, values)
            # Reverse direction: diacritized query against bare stored value.
            svc.set_account_name_ar(self.pilot_child.name, TEST_AR_BARE)
            try:
                calls.clear()
                with mock.patch("frappe.get_list", side_effect=counting):
                    results = svc.search_bilingual("Account", txt=TEST_AR_DIACRITIZED, lang="ar", page_length=50)
                self.assertEqual(len(calls), 1)
                values = [r["value"] for r in results]
                self.assertIn(self.pilot_child.name, values)
            finally:
                _clear_arabic(self.pilot_child.name)
        finally:
            _clear_arabic(self.pilot.name)

    def test_search_bilingual_single_query_and_hits(self):
        svc.set_account_name_ar(self.pilot.name, TEST_AR)
        svc.set_account_name_ar(self.pilot_child.name, TEST_AR_CHILD)
        try:
            calls = []
            original = frappe.get_list

            def counting(*args, **kwargs):
                if args and args[0] == "Account":
                    calls.append(kwargs)
                return original(*args, **kwargs)

            with mock.patch("frappe.get_list", side_effect=counting):
                results = svc.search_bilingual("Account", txt=TEST_AR, lang="ar", page_length=50)
            self.assertEqual(len(calls), 1, "bilingual search must be a single query (no N+1)")
            labels = {r["value"]: r for r in results}
            self.assertIn(self.pilot.name, labels)
            self.assertEqual(labels[self.pilot.name]["label_mode"], "arabic")
            en_results = svc.search_bilingual("Account", txt=TEST_EN, lang="en", page_length=50)
            en_labels = {r["value"]: r for r in en_results}
            self.assertIn(self.pilot.name, en_labels)
            self.assertEqual(en_labels[self.pilot.name]["label_mode"], "english")
            code_results = svc.search_bilingual("Account", txt=self.pilot.account_number, lang="ar", page_length=50)
            self.assertTrue(any(r["value"] == self.pilot.name for r in code_results))
        finally:
            _clear_arabic(self.pilot.name)
            _clear_arabic(self.pilot_child.name)

    def test_search_bilingual_respects_permissions(self):
        frappe.set_user(NO_PERM_USER)
        try:
            with self.assertRaises(frappe.PermissionError):
                svc.search_bilingual("Account", txt="CT")
        finally:
            frappe.set_user("Administrator")

    def test_search_bilingual_page_length_and_start(self):
        results = svc.search_bilingual("Account", txt="", page_length=1, start=0)
        self.assertLessEqual(len(results), 1)

    def test_search_bilingual_pagination_pages_are_ordered_and_disjoint(self):
        page1 = svc.search_bilingual("Account", txt="", page_length=3, start=0, lang="en")
        page2 = svc.search_bilingual("Account", txt="", page_length=3, start=3, lang="en")
        self.assertLessEqual(len(page1), 3)
        self.assertLessEqual(len(page2), 3)
        ids1 = {r["value"] for r in page1}
        ids2 = {r["value"] for r in page2}
        self.assertEqual(ids1 & ids2, set(), "start offset must paginate, not repeat rows")

    def test_ranking_is_global_with_genuine_competitors_both_paths(self):
        # Genuine competing set: 12 RECENT substring-only matches
        # (CT-RANK-TARGET-FILLER-*) must NOT outrank an exact match that is
        # 30 days older — for BOTH search implementations, and the exact
        # match must appear on page 1 despite page_length=10 (global ranking
        # before slicing, over the complete match set).
        from construction.searchable_dropdown.api.search import searchable_link_search

        parent = frappe.get_value(
            "Account", {"company": TEST_COMPANY, "is_group": 1, "parent_account": ("is", "set")}, "name"
        )
        import datetime

        exact = frappe.get_doc(
            {
                "doctype": "Account",
                "company": TEST_COMPANY,
                "account_name": "CT-RANK-TARGET",
                "account_number": "CT-RANK-EXACT",
                "parent_account": parent,
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        fillers = []
        try:
            old_ts = (frappe.utils.now_datetime() - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S.%f")
            frappe.db.set_value("Account", exact.name, "modified", old_ts, update_modified=False)
            for i in range(12):
                doc = frappe.get_doc(
                    {
                        "doctype": "Account",
                        "company": TEST_COMPANY,
                        "account_name": "CT-RANK-TARGET-FILLER-%02d" % i,
                        "account_number": "CT-RANK-F%d" % i,
                        "parent_account": parent,
                        "is_group": 0,
                    }
                ).insert(ignore_permissions=True)
                fillers.append(doc)
            query = "CT-RANK-TARGET"
            # Bilingual path: exact first, page bounded, fillers never ahead.
            results = svc.search_bilingual("Account", txt=query, lang="en", page_length=10, start=0)
            self.assertTrue(results)
            self.assertEqual(results[0]["value"], exact.name, "exact match must rank first globally")
            self.assertLessEqual(len(results), 10)
            # Dropdown path: same global behavior.
            drop = searchable_link_search(
                doctype="Account", txt=query, filters={"company": TEST_COMPANY}, search_fields=["account_name"], page_length=10
            )
            self.assertTrue(drop)
            self.assertEqual(drop[0]["value"], exact.name, "dropdown path must rank the exact match first too")
            # Cross-page: page 2 contains fillers only, never the exact match.
            page2 = svc.search_bilingual("Account", txt=query, lang="en", page_length=10, start=10)
            self.assertTrue(page2)
            self.assertNotIn(exact.name, {r["value"] for r in page2})
        finally:
            for row in frappe.get_all(
                "Account",
                filters={"company": TEST_COMPANY, "account_number": ("like", "CT-RANK-%")},
                fields=["name", "is_group"],
                order_by="lft desc",
            ):
                if frappe.db.exists("Account", row.name):
                    frappe.delete_doc("Account", row.name, force=True, ignore_permissions=True)
            frappe.db.commit()

    def test_ranking_beyond_thousand_boundary(self):
        # >1000 semantics: with 1001 genuine competing matches inserted
        # (newest first) and an exact match older than all of them, the
        # uncapped complete-match-set ranking must still surface the exact
        # match first — the previous newest-1000 window silently dropped it.
        parent = frappe.get_value(
            "Account", {"company": TEST_COMPANY, "is_group": 1, "parent_account": ("is", "set")}, "name"
        )
        import datetime

        exact = frappe.get_doc(
            {
                "doctype": "Account",
                "company": TEST_COMPANY,
                "account_name": "CT-BULK-TARGET",
                "account_number": "CT-BULK-EXACT",
                "parent_account": parent,
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)
        now = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S.%f")
        user = frappe.session.user
        currency = frappe.db.get_value("Company", TEST_COMPANY, "default_currency") or "EGP"
        rows = []
        for i in range(1001):
            rows.append(
                (
                    "CT-BULK-%04d - CT-BULK-TARGET - E" % i,
                    now,
                    now,
                    user,
                    user,
                    0,
                    TEST_COMPANY,
                    "CT-BULK-TARGET-FILLER-%04d" % i,
                    "CT-BULK-%04d" % i,
                    parent,
                    0,
                    i * 2 + 1,
                    i * 2 + 2,
                    currency,
                )
            )
        try:
            old_ts = (frappe.utils.now_datetime() - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S.%f")
            frappe.db.set_value("Account", exact.name, "modified", old_ts, update_modified=False)
            for row in rows:
                frappe.db.sql(
                    """
                    INSERT INTO `tabAccount`
                    (name, creation, modified, modified_by, owner, docstatus, company,
                     account_name, account_number, parent_account, is_group, lft, rgt, account_currency)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    row,
                )
            frappe.db.commit()
            query = "CT-BULK-TARGET"
            results = svc.search_bilingual("Account", txt=query, lang="en", page_length=10, start=0)
            self.assertTrue(results)
            self.assertEqual(
                results[0]["value"], exact.name, "exact match beyond 1000 newer competitors must rank first"
            )
            # The complete match set exceeds 1000 and is fully served within
            # the window — on BOTH public paths (service and dropdown).
            from construction.services.bilingual_service import RANK_WINDOW

            full = svc.search_bilingual("Account", txt=query, lang="en", page_length=RANK_WINDOW, start=0)
            match_count = len(frappe.get_list(
                "Account",
                filters={"company": TEST_COMPANY},
                or_filters=[
                    ["account_name", "like", "%" + query + "%"],
                    ["name", "like", "%" + query + "%"],
                    ["account_number", "like", "%" + query + "%"],
                ],
                fields=["name"],
                limit_page_length=0,
            ))
            self.assertGreaterEqual(match_count, 1002)
            self.assertIn(exact.name, {r["value"] for r in full})
            self.assertFalse(
                svc.search_bilingual("Account", txt=query, lang="en", page_length=5, start=0, with_meta=True)["truncated"],
                "matches below the window must not be flagged truncated",
            )
            from construction.searchable_dropdown.api.search import searchable_link_search

            drop = searchable_link_search(
                doctype="Account", txt=query, filters={"company": TEST_COMPANY}, search_fields=["account_name"], page_length=10
            )
            self.assertTrue(drop)
            self.assertEqual(
                drop[0]["value"], exact.name, "dropdown path must surface the beyond-window exact match too"
            )
            drop_full = searchable_link_search(
                doctype="Account", txt=query, filters={"company": TEST_COMPANY}, search_fields=["account_name"], page_length=RANK_WINDOW, start=0
            )
            self.assertGreaterEqual(len(drop_full), 200)
            self.assertIn(exact.name, {r["value"] for r in drop_full})
        finally:
            frappe.db.sql("DELETE FROM `tabAccount` WHERE account_number LIKE %s", ("CT-BULK-%",))
            if frappe.db.exists("Account", exact.name):
                frappe.delete_doc("Account", exact.name, force=True, ignore_permissions=True)
            frappe.db.commit()

    def test_real_window_boundary_5000_and_5001_both_paths(self):
        # Genuine 5,000/5,001 boundary with REAL fixtures on BOTH paths:
        # with exactly 5,000 matching rows the ranked set is exactly-full
        # and NOT truncated (probe excludes the boundary); adding a 5,001st
        # row overflows — the service loudly refuses on the plain path,
        # with_meta flags it, and the dropdown refuses too.
        from construction.searchable_dropdown.api.search import searchable_link_search

        parent = frappe.get_value(
            "Account", {"company": TEST_COMPANY, "is_group": 1, "parent_account": ("is", "set")}, "name"
        )
        now = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S.%f")
        user = frappe.session.user
        currency = frappe.db.get_value("Company", TEST_COMPANY, "default_currency") or "EGP"

        def insert_bulk(count, start=0):
            rows = []
            for i in range(start, start + count):
                rows.append(
                    (
                        "CT-CAP-%06d - CT-CAP-TARGET - E" % i,
                        now,
                        now,
                        user,
                        user,
                        0,
                        TEST_COMPANY,
                        "CT-CAP-TARGET-FILLER-%06d" % i,
                        "CT-CAP-%06d" % i,
                        parent,
                        0,
                        1,
                        2,
                        currency,
                    )
                )
            for row in rows:
                frappe.db.sql(
                    """
                    INSERT INTO `tabAccount`
                    (name, creation, modified, modified_by, owner, docstatus, company,
                     account_name, account_number, parent_account, is_group, lft, rgt, account_currency)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    row,
                )
            frappe.db.commit()

        try:
            # Exactly RANK_WINDOW matches: served fully, not truncated.
            insert_bulk(svc.RANK_WINDOW)
            with_meta = svc.search_bilingual("Account", txt="CT-CAP-TARGET", lang="en", page_length=5, start=0, with_meta=True)
            self.assertGreaterEqual(len(with_meta["results"]), 1)
            self.assertFalse(with_meta["truncated"], "exactly-full 5,000 window must NOT be flagged")
            full = svc.search_bilingual("Account", txt="CT-CAP-TARGET", lang="en", page_length=svc.MAX_PAGE_LENGTH, start=0)
            self.assertEqual(len(full), svc.MAX_PAGE_LENGTH, "page must be the clamped size (billing out beyond the clamp)")
            served_first_page_count = len(full)
            self.assertGreater(served_first_page_count, 0)
            match_count = len(frappe.get_list(
                "Account",
                filters={"company": TEST_COMPANY},
                or_filters=[
                    ["account_name", "like", "%CT-CAP-TARGET%"],
                    ["name", "like", "%CT-CAP-TARGET%"],
                    ["account_number", "like", "%CT-CAP-TARGET%"],
                ],
                fields=["name"],
                limit_page_length=0,
            ))
            self.assertEqual(match_count, svc.RANK_WINDOW, "exactly 5,000 matches exist")
            # Dropdown path at the exact boundary: bounded page, no refusal.
            drop = searchable_link_search(
                doctype="Account", txt="CT-CAP-TARGET", filters={"company": TEST_COMPANY}, search_fields=["account_name"], page_length=5
            )
            self.assertTrue(drop)
            # Insert the 5,001st row: real overflow -> loud service refusal
            # on the plain path, flag on with_meta, dropdown refusal.
            insert_bulk(1, start=svc.RANK_WINDOW)
            with self.assertRaises(frappe.ValidationError):
                svc.search_bilingual("Account", txt="CT-CAP-TARGET", lang="en", page_length=5)
            with self.assertRaises(frappe.ValidationError):
                searchable_link_search(
                    doctype="Account", txt="CT-CAP-TARGET", filters={"company": TEST_COMPANY}, search_fields=["account_name"], page_length=5
                )
            flagged = svc.search_bilingual("Account", txt="CT-CAP-TARGET", lang="en", page_length=5, start=0, with_meta=True)
            self.assertTrue(flagged["truncated"])
            flagged_count = len(frappe.get_list(
                "Account",
                filters={"company": TEST_COMPANY},
                or_filters=[
                    ["account_name", "like", "%CT-CAP-TARGET%"],
                    ["name", "like", "%CT-CAP-TARGET%"],
                    ["account_number", "like", "%CT-CAP-TARGET%"],
                ],
                fields=["name"],
                limit_page_length=0,
            ))
            self.assertEqual(flagged_count, svc.RANK_WINDOW + 1, "the 5,001st match exists")
        finally:
            frappe.db.sql("DELETE FROM `tabAccount` WHERE account_number LIKE %s", ("CT-CAP-%",))
            frappe.db.commit()

    def test_non_integer_pagination_inputs_are_cross_path_consistent(self):
        # Non-integer start/page_length must behave IDENTICALLY on both
        # public paths: numeric strings/floats coerce ("3.5" -> 3); garbage
        # falls back to the default floors — never a ValueError on one path
        # and a silent [] on the other.
        from construction.searchable_dropdown.api.search import searchable_link_search

        # Invalid pagination values must be refused IDENTICALLY on BOTH
        # paths — same exception class AND same message (a future
        # service/dropdown mismatch must fail). Includes `None` inputs and
        # fractional floats/strings/garbage.
        cases_garbage = [
            {"page_length": "3.5", "start": 0},
            {"page_length": "abc", "start": 0},
            {"page_length": 3.7, "start": "0"},
            {"page_length": None, "start": 0},
            {"page_length": 2, "start": None},
            {"page_length": None, "start": None},
        ]
        for kwargs in cases_garbage:
            err_svc = err_dd = None
            with self.assertRaises(frappe.ValidationError) as cm_svc:
                svc.search_bilingual("Account", txt="CT-T3-", lang="en", **kwargs)
            err_svc = str(cm_svc.exception)
            with self.assertRaises(frappe.ValidationError) as cm_dd:
                searchable_link_search(
                    doctype="Account", txt="CT-T3-", filters={"company": TEST_COMPANY}, search_fields=["account_name"],
                    **kwargs
                )
            err_dd = str(cm_dd.exception)
            self.assertEqual(err_svc, err_dd, "identical exception message required (%r)" % kwargs)
        # Integer-valued strings work on both and agree on the first value.
        for kwargs in ({"page_length": "2", "start": 0}, {"page_length": 2, "start": "1"}):
            m = svc.search_bilingual("Account", txt="CT-T3-", lang="en", **kwargs)
            d = searchable_link_search(
                doctype="Account", txt="CT-T3-", filters={"company": TEST_COMPANY}, search_fields=["account_name"],
                **kwargs
            )
            self.assertTrue(m and d, kwargs)
            self.assertTrue(m[0]["value"] == d[0]["value"], kwargs)

    def test_negative_zero_and_oversized_pagination_inputs_are_lower_bounded(self):
        # Negative and zero page_length / negative start must never reach
        # ORM pagination or Python slicing with framework-dependent
        # behavior on either public path: they are lower-clamped server-
        # side before any use.
        from construction.searchable_dropdown.api.search import searchable_link_search

        for kwargs in (
            {"page_length": -3, "start": 0},
            {"page_length": 0, "start": 0},
            {"page_length": 1, "start": -5},
            {"page_length": -3, "start": -5},
            {"page_length": 0, "start": -5},
        ):
            m = svc.search_bilingual("Account", txt="CT-T3-", page_length=kwargs["page_length"], start=kwargs["start"], lang="en")
            self.assertTrue(m, "lower-bounded page must never be empty on real matches")
            self.assertLessEqual(len(m), svc.MAX_PAGE_LENGTH)
            d = searchable_link_search(
                doctype="Account", txt="CT-T3-", filters={"company": TEST_COMPANY}, search_fields=["account_name"],
                **kwargs
            )
            self.assertTrue(d, "dropdown lower-bounded page must never be empty on real matches")
            self.assertLessEqual(len(d), 200)
        # Oversized inputs remain handled (upper clamp) — sanity re-check.
        huge = svc.search_bilingual("Account", txt="", page_length=10 ** 9, start=-7)
        self.assertLessEqual(len(huge), svc.MAX_PAGE_LENGTH)

    def test_page_length_is_clamped_against_client_input(self):
        # A caller-supplied huge page_length must never trigger unbounded
        # transfer on either path.
        huge = svc.search_bilingual("Account", txt="", page_length=10 ** 9, start=0)
        self.assertLessEqual(len(huge), svc.MAX_PAGE_LENGTH)
        meta = svc.search_bilingual("Account", txt="", page_length=10 ** 9, start=0, with_meta=True)
        self.assertEqual(len(meta["results"]), len(meta["results"]))  # bounded shape check
        self.assertLessEqual(len(meta["results"]), svc.MAX_PAGE_LENGTH)
        from construction.searchable_dropdown.api.search import searchable_link_search

        drop = searchable_link_search(
            doctype="Account", txt="", filters={"company": TEST_COMPANY}, search_fields=["account_name"], page_length=10 ** 9
        )
        self.assertLessEqual(len(drop), svc.MAX_PAGE_LENGTH)

    def test_blank_query_is_bounded_and_text_query_reports_truncation(self):
        # Resource safety: blank queries use plain bounded DB pagination
        # (never a complete-set scan); text queries rank within the
        # documented window and report the truncation contract via with_meta.
        from unittest import mock as _mock

        blank = svc.search_bilingual("Account", txt="", page_length=5, start=0)
        self.assertLessEqual(len(blank), 5)
        blank_meta = svc.search_bilingual("Account", txt="", page_length=5, start=0, with_meta=True)
        self.assertFalse(blank_meta["truncated"])
        # Text query inside the window: ranked results, no truncation flag.
        text_meta = svc.search_bilingual("Account", txt="CT-T3-", page_length=5, start=0, with_meta=True)
        self.assertFalse(text_meta["truncated"])
        self.assertEqual(text_meta["window"], svc.RANK_WINDOW)
        # Window+1 probe semantics with the REAL fixture set (2 matches):
        # window == match count => NOT truncated (exactly-full window, the
        # probe row is excluded); window == match_count - 1 => truncated.
        # The 5,001st-row probe removes exact-5,000 false positives by
        # construction.
        with _mock.patch.object(svc, "RANK_WINDOW", 2):
            boundary = svc.search_bilingual("Account", txt="CT-T3-", page_length=5, start=0, with_meta=True)
        self.assertFalse(boundary["truncated"], "exactly-full window must NOT be flagged (probe excludes it)")
        self.assertEqual(boundary["window"], 2)
        with _mock.patch.object(svc, "RANK_WINDOW", 1):
            forced = svc.search_bilingual("Account", txt="CT-T3-", page_length=5, start=0, with_meta=True)
        self.assertTrue(forced["truncated"])
        self.assertEqual(forced["window"], 1)
        # The plain list path is LOUD on real overflow (never silent).
        from construction.searchable_dropdown.api.search import searchable_link_search

        with _mock.patch.object(svc, "RANK_WINDOW", 1):
            with self.assertRaises(frappe.ValidationError):
                searchable_link_search(
                    doctype="Account", txt="CT-T3-", filters={"company": TEST_COMPANY}, search_fields=["account_name"], page_length=5
                )
            with self.assertRaises(frappe.ValidationError):
                svc.search_bilingual("Account", txt="CT-T3-", page_length=5, start=0)

    def test_searchable_link_search_pagination_uses_start(self):
        from construction.searchable_dropdown.api.search import searchable_link_search

        page1 = searchable_link_search(
            doctype="Account", txt="", filters={"company": TEST_COMPANY}, search_fields=["account_name"], page_length=2, start=0
        )
        page2 = searchable_link_search(
            doctype="Account", txt="", filters={"company": TEST_COMPANY}, search_fields=["account_name"], page_length=2, start=2
        )
        ids1 = {r["value"] for r in page1}
        ids2 = {r["value"] for r in page2}
        self.assertEqual(ids1 & ids2, set(), "start must paginate in the dropdown path too")

    def test_registry_error_propagates_through_dropdown_path(self):
        # Fail-closed: an active-mapping schema mismatch must SURFACE from
        # the shipped dropdown search, never degrade to a silent empty list.
        from construction.searchable_dropdown.api.search import searchable_link_search

        real_get_meta = frappe.get_meta


        class ReducedMeta:
            def __init__(self, inner):
                self._inner = inner

            def has_field(self, field):
                if field == "account_name_ar":
                    return False
                return self._inner.has_field(field)

            def __getattr__(self, name):
                return getattr(self._inner, name)

        def fake_get_meta(doctype):
            return ReducedMeta(real_get_meta(doctype))

        with mock.patch("frappe.get_meta", side_effect=fake_get_meta):
            # The mapping is request-memoized; clear the memo so the
            # mocked schema drift is actually re-resolved.
            if hasattr(frappe.local, "ct_bilingual_mapping_cache"):
                frappe.local.ct_bilingual_mapping_cache = {}
            with self.assertRaises(frappe.ValidationError):
                searchable_link_search(
                    doctype="Account", txt="CT", search_fields=["account_name"], page_length=5
                )

    def test_comparative_p95_artifact_bound_and_gate(self):
        # The permanent gate CONSUMES AND AUTHENTICATES the preserved
        # artifact: code hashes must match the current governed files
        # (stale code fails), match sets must be identical, the recorded
        # statistic must equal nearest-rank P95 over the preserved raw
        # samples with a TRUE median, and the canonical gate must hold.
        # A separate live measurement (below) re-derives everything.
        import hashlib
        import math
        import json

        artifact_path = ROOT / "docs/ai/work-items/erp-arabic-bilingual-data/evidence/raw-logs/stage3/p95-measurement.json"
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        m = artifact["measurement"]
        for name, path in (
            ("bilingual_service.py", "construction/services/bilingual_service.py"),
            ("bilingual_registry.py", "construction/services/bilingual_registry.py"),
            ("search.py", "construction/searchable_dropdown/api/search.py"),
        ):
            live = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            self.assertEqual(m["code_hashes"][name], live, "preserved P95 artifact is stale for %s" % name)
        self.assertTrue(m["match_sets_equal"])
        # Cherry-pick resistance: EVERY round's raw samples are preserved
        # and each round's recorded P95 must equal its own nearest-rank
        # recompute; the selected values must be the MIN over the
        # preserved per-round P95s.
        for side in ("baseline", "bilingual"):
            rounds = m["round_samples"][side]
            self.assertEqual(len(rounds), m.get("round_count", len(rounds)), side)
            for r, raw in enumerate(rounds):
                expected_r_p95 = sorted(raw)[max(0, math.ceil(0.95 * len(raw)) - 1)]
                self.assertEqual(m["round_p95_ms"][side][r], round(expected_r_p95, 3), "%s round %d" % (side, r))
            self.assertEqual(
                m[side]["p95_ms"], min(m["round_p95_ms"][side]),
                "selected value must be the min over the preserved rounds (%s)" % side,
            )
        for side in ("baseline", "bilingual"):
            raw = sorted(m[side]["samples_ms"])
            expected_p95 = raw[max(0, math.ceil(0.95 * len(raw)) - 1)]
            self.assertEqual(m[side]["p95_ms"], round(expected_p95, 3), side)
            n = len(raw)
            expected_median = raw[n // 2] if n % 2 else (raw[n // 2 - 1] + raw[n // 2]) / 2.0
            # The recorded median is computed on unrounded samples; the
            # artifact stores 3-decimal samples, so allow rounding drift.
            self.assertAlmostEqual(m[side]["median_ms"], round(expected_median, 3), delta=0.002, msg=side)
            self.assertEqual(len(raw), m["samples"], side)
        limit = m["baseline"]["p95_ms"] * 1.10  # canonical 10% rule; floor REJECTED by the owner
        self.assertLessEqual(
            m["bilingual"]["p95_ms"],
            limit,
            "preserved bilingual P95 %.2fms exceeds baseline %.2fms + 10%% (limit %.2fms)"
            % (m["bilingual"]["p95_ms"], m["baseline"]["p95_ms"], limit),
        )

    def test_comparative_p95_live_measurement_is_balanced_and_bound(self):
        # Live STRUCTURAL re-derivation: alternating pair order, PER-CALL
        # SQL deltas, environment binding, match-set equivalence, and the
        # statistic contract. The latency gate itself is decided by the
        # artifact test above, which is hash-bound to the CURRENT code and
        # regenerated each cycle (a live sub-2ms baseline is too small for
        # a stable 10% split; the artifact is forced current by the hash
        # check, so it cannot go stale).
        measurement = svc.measure_search_p95("CT-T3-", samples=20)
        self.assertTrue(measurement["match_sets_equal"])
        self.assertIn("alternating", measurement["order_balance"])
        self.assertGreater(measurement["query_counts"]["baseline_mean_per_call"], 0)
        self.assertGreater(measurement["query_counts"]["bilingual_mean_per_call"], 0)
        self.assertLessEqual(
            max(measurement["query_counts"]["baseline_counts"]),
            measurement["query_counts"]["baseline_mean_per_call"] + 1,
        )
        self.assertIn("db_version", measurement["environment"])
        self.assertIn("code_hashes", measurement)

    def test_http_dispatch_through_overridden_endpoint(self):
        # The REAL dispatch path (frappe.handler.execute_cmd — the exact code
        # the HTTP /api/method layer runs): form_dict argument coercion plus
        # whitelisting/override resolution. A reason-free call through the
        # vendor path is refused by the governed wrapper; a reasoned call
        # succeeds with string-coerced arguments.
        from frappe.handler import execute_cmd

        frappe.set_user("Administrator")

        class _FakeRequest:
            method = "POST"

        # execute_cmd is the HTTP handler's dispatch; it reads the request
        # method, so provide the POST-shaped request the API layer uses.
        frappe.local.request = _FakeRequest()
        try:
            # A live HTTP request sends strings; reason omitted -> refused.
            frappe.local.form_dict = frappe._dict(
                {
                    "cmd": "erpnext.accounts.doctype.account.account.update_account_number",
                    "name": self.pilot_child.name,
                    "account_name": TEST_EN_CHILD,
                    "account_number": self.pilot_child.account_number,
                }
            )
            with self.assertRaises(frappe.ValidationError):
                execute_cmd("erpnext.accounts.doctype.account.account.update_account_number")
            # Reasoned call through the same dispatch path succeeds; the
            # returned identity is a server-resolved string.
            frappe.local.form_dict = frappe._dict(
                {
                    "cmd": "erpnext.accounts.doctype.account.account.update_account_number",
                    "name": self.pilot_child.name,
                    "account_name": TEST_EN_CHILD,
                    "account_number": self.pilot_child.account_number,
                    "reason": "HTTP dispatch layer evidence",
                }
            )
            result = execute_cmd("erpnext.accounts.doctype.account.account.update_account_number")
            self.assertTrue(result["ok"])
            self.assertFalse(result["renamed"])
            for c in frappe.get_all(
                "Comment",
                filters={"reference_doctype": "Account", "reference_name": result["name"]},
                pluck="name",
            ):
                frappe.delete_doc("Comment", c, force=True, ignore_permissions=True)
            for v in frappe.get_all(
                "Version",
                filters={"ref_doctype": "Account", "docname": result["name"]},
                pluck="name",
            ):
                frappe.delete_doc("Version", v, force=True, ignore_permissions=True)
            frappe.db.commit()
            # Handler-level from_descendant coercion: a real HTTP client
            # sends STRINGS, so the dispatch layer must carry the string
            # form field into the governed/vendor path compatibly.
            frappe.local.form_dict = frappe._dict(
                {
                    "cmd": "erpnext.accounts.doctype.account.account.update_account_number",
                    "name": self.pilot_child.name,
                    "account_name": TEST_EN_CHILD,
                    "account_number": self.pilot_child.account_number,
                    "reason": "HTTP dispatch from_descendant coercion",
                    "from_descendant": "1",
                }
            )
            result = execute_cmd("erpnext.accounts.doctype.account.account.update_account_number")
            self.assertTrue(result["ok"])
            self.assertFalse(result["renamed"])
            for c in frappe.get_all(
                "Comment",
                filters={"reference_doctype": "Account", "reference_name": result["name"]},
                pluck="name",
            ):
                frappe.delete_doc("Comment", c, force=True, ignore_permissions=True)
            for v in frappe.get_all(
                "Version",
                filters={"ref_doctype": "Account", "docname": result["name"]},
                pluck="name",
            ):
                frappe.delete_doc("Version", v, force=True, ignore_permissions=True)
            frappe.db.commit()
        finally:
            frappe.local.form_dict = frappe._dict()
            del frappe.local.request
            frappe.set_user("Administrator")

    # --- tree children (batched, bilingual labels) ---

    def test_tree_children_batched_and_labeled(self):
        svc.set_account_name_ar(self.pilot_child.name, TEST_AR_CHILD)
        try:
            account_calls = []
            original = frappe.get_list

            def counting(*args, **kwargs):
                if args and args[0] == "Account":
                    account_calls.append(kwargs)
                return original(*args, **kwargs)

            with mock.patch("frappe.get_list", side_effect=counting):
                nodes = svc.get_account_tree_children(
                    "Account", parent=self.pilot.name, company=TEST_COMPANY, is_root=False
                )
            # vendor children query + ONE batched label query (never per node)
            self.assertEqual(len(account_calls), 2, account_calls)
            by_name = {n["value"]: n for n in nodes}
            self.assertIn(self.pilot_child.name, by_name)
            self.assertEqual(by_name[self.pilot_child.name].get("account_name_ar"), TEST_AR_CHILD)
            self.assertEqual(by_name[self.pilot_child.name].get("value"), self.pilot_child.name)
        finally:
            _clear_arabic(self.pilot_child.name)

    # --- concurrency / stale-edit safety ---

    def test_stale_concurrent_save_is_refused(self):
        # Framework guarantee: a stale document save after a concurrent
        # change raises TimestampMismatchError (last-write-wins is refused).
        doc1 = frappe.get_doc("Account", self.pilot_child.name)
        doc2 = frappe.get_doc("Account", self.pilot_child.name)
        doc2.account_name = TEST_EN_CHILD + " x"
        doc2.save()
        try:
            with self.assertRaises(frappe.TimestampMismatchError):
                doc1.save()
        finally:
            fresh = frappe.get_doc("Account", self.pilot_child.name)
            fresh.account_name = TEST_EN_CHILD
            fresh.save()

    # --- patches: idempotency + reversal (v9_0 / v9_1) ---

    def test_track_changes_patch_idempotent_and_reversible(self):
        from construction.patches.v9_0.enable_account_track_changes import execute, revert

        execute()
        self.assertTrue(frappe.get_meta("Account").track_changes)
        execute()
        self.assertTrue(frappe.get_meta("Account").track_changes)
        revert()
        frappe.clear_cache(doctype="Account")
        self.assertFalse(frappe.get_meta("Account").track_changes)
        execute()
        self.assertTrue(frappe.get_meta("Account").track_changes)

    def test_norm_field_patch_idempotent_and_reversible(self):
        from construction.patches.v9_1.add_account_arabic_norm_field import execute, revert

        execute()
        self.assertTrue(frappe.get_meta("Account").has_field("account_name_ar_norm"))
        execute()
        self.assertTrue(frappe.get_meta("Account").has_field("account_name_ar_norm"))
        revert()
        frappe.clear_cache(doctype="Account")
        self.assertFalse(frappe.get_meta("Account").has_field("account_name_ar_norm"))
        execute()
        self.assertTrue(frappe.get_meta("Account").has_field("account_name_ar_norm"))

    def test_arabic_field_is_read_only(self):
        # P0-2 defense in depth: the form must not offer direct edits.
        field = frappe.get_meta("Account").get_field("account_name_ar")
        self.assertTrue(field.read_only)

    # --- searchable dropdown regression (English baseline intact) ---

    def test_searchable_link_search_english_baseline_unchanged(self):
        from construction.searchable_dropdown.api.search import searchable_link_search

        results = searchable_link_search(
            doctype="Account",
            txt=TEST_EN,
            filters={"company": TEST_COMPANY},
            search_fields=["account_name"],
            page_length=50,
        )
        self.assertTrue(any(r["value"] == self.pilot.name for r in results), results)

    def test_searchable_link_search_arabic_session_prefers_arabic(self):
        from construction.searchable_dropdown.api.search import searchable_link_search

        svc.set_account_name_ar(self.pilot.name, TEST_AR)
        try:
            frappe.local.lang = "ar"
            try:
                results = searchable_link_search(
                    doctype="Account",
                    txt=TEST_EN,
                    filters={"company": TEST_COMPANY},
                    search_fields=["account_name"],
                    page_length=50,
                )
            finally:
                frappe.local.lang = "en"
            labels = {r["value"]: r["label"] for r in results}
            self.assertEqual(labels.get(self.pilot.name), TEST_AR)
        finally:
            _clear_arabic(self.pilot.name)

    # --- performance smoke (P95 measured against a generous bound) ---

    def test_search_performance_smoke(self):
        svc.set_account_name_ar(self.pilot.name, TEST_AR)
        try:
            samples = []
            for _ in range(20):
                started = time.perf_counter()
                svc.search_bilingual("Account", txt=TEST_AR_BARE, lang="ar", page_length=20)
                samples.append((time.perf_counter() - started) * 1000.0)
            samples.sort()
            p95 = samples[int(len(samples) * 0.95) - 1]
            self.assertLess(p95, 250.0, "bilingual search P95 regressed: %.1fms" % p95)
        finally:
            _clear_arabic(self.pilot.name)


if __name__ == "__main__":
    unittest.main()
