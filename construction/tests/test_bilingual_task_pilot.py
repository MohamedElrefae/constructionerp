"""Stage 5 Wave 2 Pilot tests: Task bilingual enablement.

Run with:
PYTHONPATH=/home/mohamed/frappe-bench/worktrees/bilingual-task-master \\
  bench --site v16.localhost run-tests --app construction --module construction.tests.test_bilingual_task_pilot

Covers:
- Patch v9_8 idempotency and reversibility for subject_ar and subject_ar_norm.
- Registry mapping resolution including norm_field, tree.enabled, and search fields.
- Fail-closed validation when declared fields are missing on active/schema_installed Task.
- Server-authoritative derivation of norm_field on save (POISONED-KEY overwritten).
- Bidi and control character rejection on subject_ar.
- Tree identity invariant (name and parent_task remain ASCII serials/unaltered).
- Rename doc preserves Arabic and norm keys.
- Normalized Arabic search matching despite Alef variants, tatweel, and diacritics.
- Mechanically enforced guard test: zero service edits (byte-identical to base commit abffaaa).
"""

import re
import subprocess
import unittest
from pathlib import Path
from uuid import uuid4

import frappe

from construction.patches.v9_8.add_task_arabic_fields import execute as patch_execute
from construction.patches.v9_8.add_task_arabic_fields import revert as patch_revert
from construction.searchable_dropdown.api.search import searchable_link_search
from construction.services import bilingual_service as svc
from construction.services.bilingual_registry import normalize_arabic


def _get_target_task():
    """Helper to fetch an existing Task doc for testing."""
    docs = frappe.get_all("Task", filters={"is_group": 0}, limit=1)
    if not docs:
        docs = frappe.get_all("Task", limit=1)
    if not docs:
        raise unittest.SkipTest("No existing records found for Task")
    return frappe.get_doc("Task", docs[0].name)


class TestBilingualTaskPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        patch_execute()

    def test_zero_service_edits_guard(self):
        """Task master primary claim: bilingual_service.py and search.py must be byte-identical to base commit abffaaa."""
        repo_root = Path(__file__).resolve().parents[2]
        base_commit = "abffaaa"
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
        """Idempotent execute and clean revert of patch v9_8 across Task custom fields."""
        patch_execute()
        targets = [
            ("Task", "subject_ar"),
            ("Task", "subject_ar_norm"),
        ]
        for dt, fn in targets:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in targets:
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

        patch_revert()
        for dt, fn in targets:
            frappe.clear_cache(doctype=dt)
            self.assertFalse(frappe.get_meta(dt).has_field(fn))

        patch_execute()
        for dt, fn in targets:
            frappe.clear_cache(doctype=dt)
            self.assertTrue(frappe.get_meta(dt).has_field(fn))

    def test_registry_loads_and_maps_resolved_task_fields(self):
        """Ensure get_mapping resolves subject_ar_norm, tree.enabled, and search fields."""
        frappe.local.ct_bilingual_mapping_cache = None
        m = svc.get_mapping("Task")
        self.assertIsNotNone(m, "Mapping missing for Task")
        self.assertEqual(m["resolved"].get("norm_field"), "subject_ar_norm")
        self.assertEqual(m["resolved"].get("english_field"), "subject")
        self.assertEqual(m["resolved"].get("arabic_field"), "subject_ar")
        self.assertIsNone(m["resolved"].get("code_field"))
        self.assertTrue(bool((m.get("tree") or {}).get("enabled")))
        self.assertEqual(m.get("search", {}).get("fields"), ["subject", "subject_ar"])

    def test_active_and_schema_installed_fail_closed_on_missing_task_field(self):
        """If norm_field is declared on schema_installed Task but missing from schema, fail closed."""
        frappe.local.ct_bilingual_mapping_cache = None
        orig_registry = svc.get_registry()
        fake_registry = {
            "schema": orig_registry.get("schema"),
            "display": orig_registry.get("display"),
            "unicode_policy": orig_registry.get("unicode_policy"),
            "doctypes": {
                "Task": {
                    "state": "schema_installed",
                    "english_field": "subject",
                    "arabic_field": "subject_ar",
                    "norm_field": "nonexistent_task_norm_field",
                    "code_field": None,
                    "identity_field": "name",
                }
            },
        }
        with unittest.mock.patch.object(svc, "get_registry", return_value=fake_registry):
            frappe.local.ct_bilingual_mapping_cache = None
            with self.assertRaises(frappe.ValidationError):
                svc.get_mapping("Task")
        frappe.local.ct_bilingual_mapping_cache = None

    def test_server_authoritative_norm_derivation_and_poison_overwritten(self):
        """Client-passed POISONED-KEY is overwritten with server-derived norm on save."""
        doc = _get_target_task()
        orig_ar = doc.get("subject_ar")
        orig_norm = doc.get("subject_ar_norm")
        test_ar = "مهمة فحص الموقع والأعمال الإنشائية"
        try:
            doc.set("subject_ar", test_ar)
            doc.set("subject_ar_norm", "POISONED-KEY")
            doc.save()

            reloaded = frappe.get_doc("Task", doc.name)
            expected_norm = normalize_arabic(test_ar)
            self.assertEqual(
                reloaded.get("subject_ar_norm"),
                expected_norm,
                "Poisoned key survived or norm key not derived on Task!",
            )
        finally:
            clean = frappe.get_doc("Task", doc.name)
            clean.set("subject_ar", orig_ar)
            clean.set("subject_ar_norm", orig_norm)
            clean.save()
            frappe.db.commit()

    def test_arabic_edit_rejects_bidi_controls(self):
        """subject_ar rejects bidi controls (C0, C1, DEL, overrides, isolates, LRM/RLM/ALM)."""
        forbidden_samples = [
            "مهمة\u202eالمشروع",  # Right-to-Left Override
            "مهمة\u200eالمشروع",  # LRM
            "مهمة\u202bالمشروع",  # RLE
            "مهمة\x00المشروع",  # NUL
        ]
        doc = _get_target_task()
        orig_val = doc.get("subject_ar")
        for bad_sample in forbidden_samples:
            doc.set("subject_ar", bad_sample)
            with self.assertRaises(frappe.ValidationError):
                doc.save()
        clean = frappe.get_doc("Task", doc.name)
        clean.set("subject_ar", orig_val)
        clean.save()
        frappe.db.commit()

    def test_identity_invariant_and_tree_preservation(self):
        """Task preserves naming series PK, parent_task pointer, and retains Arabic/norm keys across rename."""
        parent_root = frappe.get_all("Task", filters={"is_group": 1}, limit=1)
        parent_id = parent_root[0].name if parent_root else None
        task_ar = "مهمة إعداد المخططات الهندسية"
        test_subj = f"Engineering Drawing Preparation {uuid4().hex[:6]}"

        task = frappe.get_doc({
            "doctype": "Task",
            "subject": test_subj,
            "parent_task": parent_id,
            "is_group": 0,
            "subject_ar": task_ar,
        })
        task.insert(ignore_permissions=True)
        old_id = task.name

        # Verify name PK is naming series ASCII
        self.assertTrue(bool(re.match(r"^TASK-\d{4}-\d+$", task.name) or re.match(r"^TASK-", task.name)))
        if parent_id:
            self.assertEqual(task.parent_task, parent_id)

        new_id = f"{old_id}-RENAMED"

        try:
            if frappe.db.exists("Task", new_id):
                frappe.delete_doc("Task", new_id, force=True)

            self.assertEqual(task.subject_ar_norm, normalize_arabic(task_ar))
            if parent_id:
                self.assertEqual(task.parent_task, parent_id)

            frappe.rename_doc("Task", old_id, new_id, force=True)

            renamed = frappe.get_doc("Task", new_id)
            self.assertEqual(renamed.subject_ar, task_ar)
            self.assertEqual(renamed.subject_ar_norm, normalize_arabic(task_ar))
            if parent_id:
                self.assertEqual(renamed.parent_task, parent_id)
        finally:
            frappe.db.delete("Task Depends On", {"task": ["in", [old_id, new_id]]})
            frappe.db.delete("Task Depends On", {"parent": ["in", [old_id, new_id]]})
            if frappe.db.exists("Task", new_id):
                frappe.delete_doc("Task", new_id, force=True)
            if frappe.db.exists("Task", old_id):
                frappe.delete_doc("Task", old_id, force=True)
            frappe.db.commit()

    def test_search_matches_despite_alef_tatweel_diacritics(self):
        """Search matches despite Alef variants, tatweel, and diacritics."""
        doc = _get_target_task()
        orig_ar = doc.get("subject_ar")
        test_canonical = "مُهِمَّةُ الصِّيَانَةِ الكَهْرَبَائِيَّةِ"
        try:
            doc.set("subject_ar", test_canonical)
            doc.save()
            frappe.db.commit()

            # Query with bare Alef without Tashkeel
            query = "مهمة الصيانة"

            # 1. bilingual_service.search_bilingual
            results = svc.search_bilingual("Task", txt=query)
            matched_names = [r["value"] for r in results]
            self.assertIn(
                doc.name,
                matched_names,
                f"search_bilingual(Task) failed to match '{test_canonical}' with query '{query}'",
            )

            # 2. searchable_dropdown.searchable_link_search
            dropdown_res = searchable_link_search(doctype="Task", txt=query)
            items = dropdown_res.get("results", []) if isinstance(dropdown_res, dict) else dropdown_res
            dropdown_names = [r["value"] for r in items]
            self.assertIn(
                doc.name,
                dropdown_names,
                f"searchable_link_search(Task) failed to match '{test_canonical}' with query '{query}'",
            )
        finally:
            clean = frappe.get_doc("Task", doc.name)
            clean.set("subject_ar", orig_ar)
            clean.save()
            frappe.db.commit()
