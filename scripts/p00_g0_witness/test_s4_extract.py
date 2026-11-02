"""Unit tests for the S4 extraction/redaction component (synthetic inputs only).

No database, no target, no configuration. Run:
    python3 -m unittest discover -s apps/construction/scripts/p00_g0_witness -v
"""

from __future__ import annotations

import json
import re
import unittest

from s4_extract import (
    C1,
    C2,
    C3,
    C4,
    C5,
    C6,
    CODES,
    INCOMPLETE,
    STATUSES,
    UNKNOWN,
    S4Extractor,
    classify,
)


class ClassifyTests(unittest.TestCase):
    def test_absent_row_is_unknown(self):
        out = classify(None, innodb_read_only=False)
        self.assertEqual((out.code, out.status, out.reason), (C4, UNKNOWN, "absence_not_evidence"))

    def test_declared_readonly(self):
        out = classify({"trx_is_read_only": 1, "trx_autocommit_non_locking": 0}, innodb_read_only=False)
        self.assertEqual((out.code, out.status), (C1, UNKNOWN))
        self.assertEqual(out.reason, "declared_readonly")

    def test_declared_readwrite(self):
        out = classify({"trx_is_read_only": 0, "trx_autocommit_non_locking": 0}, innodb_read_only=False)
        self.assertEqual((out.code, out.status, out.reason), (C2, UNKNOWN, "declared_readwrite"))

    def test_autocommit_is_indeterminate(self):
        out = classify({"trx_is_read_only": 1, "trx_autocommit_non_locking": 1}, innodb_read_only=False)
        self.assertEqual((out.code, out.reason), (C3, "autocommit_non_locking"))

    def test_global_mode_confound(self):
        out = classify({"trx_is_read_only": 1, "trx_autocommit_non_locking": 0}, innodb_read_only=True)
        self.assertEqual((out.code, out.reason), (C3, "global_mode_confound"))

    def test_unexpected_column_withheld(self):
        out = classify(
            {"trx_is_read_only": 1, "trx_autocommit_non_locking": 0, "trx_query": "x"},
            innodb_read_only=False,
        )
        self.assertEqual((out.code, out.status, out.reason), (C5, INCOMPLETE, "unexpected_column"))

    def test_unexpected_value_indeterminate(self):
        out = classify({"trx_is_read_only": 7, "trx_autocommit_non_locking": 0}, innodb_read_only=False)
        self.assertEqual((out.code, out.reason), (C3, "unexpected_value"))

    def test_ambiguity_is_incomplete(self):
        out = classify({"trx_autocommit_non_locking": 0}, innodb_read_only=False)
        self.assertEqual((out.code, out.status, out.reason), (None, INCOMPLETE, "evaluation_ambiguous"))

    def test_multiple_rows_indeterminate(self):
        out = classify(None, innodb_read_only=False, multiple=True)
        self.assertEqual((out.code, out.reason), (C3, "multiple_rows"))

    def test_vocabulary_closed(self):
        from s4_extract import Outcome

        with self.assertRaises(ValueError):
            Outcome("X9", UNKNOWN, "declared_readonly")
        with self.assertRaises(ValueError):
            Outcome(C1, "OK", "declared_readonly")
        with self.assertRaises(ValueError):
            Outcome(C1, UNKNOWN, "not_a_reason")


class ExtractorTests(unittest.TestCase):
    def _runner(self, rows):
        calls = []

        def run(q):
            calls.append(q)
            return rows

        return run, calls

    def test_single_observation_shape(self):
        run, calls = self._runner([{"trx_is_read_only": 1, "trx_autocommit_non_locking": 0}])
        ex = S4Extractor(run, clock=lambda: 10.0, sleeper=lambda s: None)
        rec = ex.extract(case_id="Q7-P1-04")
        self.assertEqual(rec["surface"], "S4")
        self.assertEqual(rec["class_outcome"]["code"], C1)
        self.assertEqual(rec["redaction_decision"], "emitted_label")
        self.assertEqual(len(calls), 1)
        self.assertIn("CONNECTION_ID()", calls[0])
        # no forbidden projection in the query
        self.assertNotIn("trx_query", calls[0])
        self.assertNotIn("trx_mysql_thread_id,", calls[0])

    def test_absent_row_unknown(self):
        run, _ = self._runner([])
        ex = S4Extractor(run, clock=lambda: 10.0, sleeper=lambda s: None)
        rec = ex.extract()
        self.assertEqual((rec["class_outcome"]["code"], rec["class_outcome"]["status"]), (C4, UNKNOWN))

    def test_freshness_gap_enforced(self):
        run, _ = self._runner([{"trx_is_read_only": 1, "trx_autocommit_non_locking": 0}])
        times = iter([10.0, 10.02, 10.2])
        slept = []
        ex = S4Extractor(run, clock=lambda: next(times), sleeper=lambda s: slept.append(s))
        ex.extract()
        rec = ex.extract()
        self.assertTrue(slept, "expected a sleep to enforce the >=150ms idle gap")
        self.assertEqual(rec["freshness"]["cache_class"], "fresh")

    def test_integrity_chain_links(self):
        run, _ = self._runner([{"trx_is_read_only": 0, "trx_autocommit_non_locking": 0}])
        ex = S4Extractor(run, clock=lambda: 10.0, sleeper=lambda s: None)
        a = ex.extract()
        b = ex.extract()
        self.assertEqual(b["integrity"]["prev_digest"], a["integrity"]["this_digest"])
        self.assertEqual(len(a["integrity"]["this_digest"]), 64)

    def test_no_connection_id_or_forbidden_keys_in_record(self):
        run, _ = self._runner([{"trx_is_read_only": 1, "trx_autocommit_non_locking": 0}])
        ex = S4Extractor(run, clock=lambda: 10.0, sleeper=lambda s: None)
        rec = ex.extract()
        blob = json.dumps(rec)
        for forbidden in ("trx_query", "trx_mysql_thread_id", "trx_id", "trx_started"):
            self.assertNotIn(forbidden, blob)
        # handle is a random 32-hex token; no long digit-only runs (no ids)
        self.assertRegex(rec["correlation"]["handle"], r"^[0-9a-f]{32}$")

    def test_query_error_maps_to_incomplete(self):
        def boom(q):
            raise RuntimeError("synthetic failure")

        ex = S4Extractor(boom, clock=lambda: 10.0, sleeper=lambda s: None)
        rec = ex.extract()
        self.assertEqual(
            (rec["class_outcome"]["code"], rec["class_outcome"]["status"], rec["class_outcome"]["reason"]),
            (None, INCOMPLETE, "evaluation_aborted"),
        )
        self.assertEqual(rec["redaction_decision"], "withheld")

    def test_integrity_failure_maps_to_fail(self):
        ex = S4Extractor(
            lambda q: [{"trx_is_read_only": 1, "trx_autocommit_non_locking": 0}],
            clock=lambda: 10.0, sleeper=lambda s: None,
        )
        rec = ex.extract(integrity_failed=True)
        self.assertEqual(
            (rec["class_outcome"]["code"], rec["class_outcome"]["status"], rec["class_outcome"]["reason"]),
            (None, "FAIL", "integrity_failure"),
        )
        self.assertEqual(rec["redaction_decision"], "withheld")

    def test_assess_conflicting_evidence_incomplete(self):
        seq = iter([
            {"trx_is_read_only": 1, "trx_autocommit_non_locking": 0},
            {"trx_is_read_only": 0, "trx_autocommit_non_locking": 0},
        ])
        times = iter([10.0, 10.0, 10.2])
        ex = S4Extractor(lambda q: [next(seq)], clock=lambda: next(times), sleeper=lambda s: None)
        rec = ex.assess(case_id="Q7-P1-03")
        self.assertEqual(
            (rec["class_outcome"]["code"], rec["class_outcome"]["status"], rec["class_outcome"]["reason"]),
            (None, INCOMPLETE, "conflicting_evidence"),
        )
        self.assertEqual(rec["redaction_decision"], "withheld")

    def test_assess_agreeing_observations(self):
        row = {"trx_is_read_only": 1, "trx_autocommit_non_locking": 0}
        seq = iter([row, row])
        times = iter([10.0, 10.0, 10.2])
        ex = S4Extractor(lambda q: [next(seq)], clock=lambda: next(times), sleeper=lambda s: None)
        rec = ex.assess(case_id="control")
        self.assertEqual((rec["class_outcome"]["code"], rec["class_outcome"]["status"]), (C1, UNKNOWN))
        self.assertEqual(rec["redaction_decision"], "emitted_label")

    def test_vocabulary_in_record(self):
        run, _ = self._runner([{"trx_is_read_only": 1, "trx_autocommit_non_locking": 0}])
        ex = S4Extractor(run, clock=lambda: 10.0, sleeper=lambda s: None)
        rec = ex.extract()
        self.assertIn(rec["class_outcome"]["status"], STATUSES)
        self.assertIn(rec["class_outcome"]["code"], CODES)


if __name__ == "__main__":
    unittest.main()
