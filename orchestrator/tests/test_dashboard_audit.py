"""Regression: dashboard audit reads the real workflow_events schema.

The store creates `created_utc`; the audit export historically selected a
`timestamp` column that does not exist. This test builds the DB with the real
Store (no hand-written schema) and asserts the export returns the events.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

import dashboard_api
from store import Store


class DashboardAuditSchemaTests(unittest.TestCase):
    def _root_with_events(self, count=3):
        root = Path(tempfile.mkdtemp(prefix="audit-root-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        store = Store(root / "orchestrator/var/checkpoints.db")
        for i in range(count):
            store.event(f"evt-{i}", "test_kind", {"index": i, "text": "x" * 10})
        store.close()
        return root

    def test_audit_returns_events_from_real_schema(self):
        root = self._root_with_events(3)
        out = dashboard_api.get_sanitized_audit_events(root)
        self.assertEqual(out["metadata"]["total_available_events"], 3)
        self.assertEqual(len(out["events"]), 3)
        first = out["events"][0]
        self.assertEqual(first["seq"], 1)
        self.assertEqual(first["event_id"], "evt-0")
        self.assertEqual(first["kind"], "test_kind")
        self.assertIsInstance(first["timestamp"], str)
        self.assertTrue(first["timestamp"])
        self.assertEqual(first["payload"]["index"], 0)

    def test_audit_event_limit_is_enforced(self):
        root = self._root_with_events(5)
        out = dashboard_api.get_sanitized_audit_events(root, max_events=2)
        self.assertEqual(len(out["events"]), 2)
        self.assertTrue(out["metadata"]["truncated"])

    def test_audit_empty_database(self):
        root = Path(tempfile.mkdtemp(prefix="audit-empty-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        Store(root / "orchestrator/var/checkpoints.db").close()
        out = dashboard_api.get_sanitized_audit_events(root)
        self.assertEqual(out["events"], [])
        self.assertEqual(out["metadata"]["total_available_events"], 0)


if __name__ == "__main__":
    unittest.main()
