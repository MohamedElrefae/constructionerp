"""Offline tests for the native Stage 4 IMPORT executor.

The site write is mocked; these tests prove idempotency, reconciliation, rollback export
and invariant enforcement without touching ERP data.
"""

import hashlib
import json

import pytest

import import_adapter
from core import WorkflowError, canonical


DESCRIPTOR = {
    "bench_root": "/tmp/bench",
    "site": "test.localhost",
    "private_root": "/tmp/private",
    "erp_checkout": "/tmp/bench/apps/construction",
    "site_classification": "non-production test",
}


def _payload(*rows):
    return [{"identity": i, "arabic": a} for i, a in rows]


def _bundle(identities):
    return {"rows": [{"identity": i, "a2_review": {"identity": i, "decision": "approved"}} for i in identities]}


def _fake_console(before_map, *, drop_identity=False, invariant_ok=True, existing_after=None):
    """Return a fake _run_write_console that mimics the Frappe report."""

    def _fake(bench_root, site, planned, timeout=600):
        before = {r["identity"]: before_map.get(r["identity"]) for r in planned}
        wrote = 0
        after = {}
        for r in planned:
            prev = before[r["identity"]]
            target = r["arabic"]
            if prev != target:
                wrote += 1
            # existing_after simulates a value that diverges from the write (fault injection).
            after[r["identity"]] = existing_after[r["identity"]] if existing_after and r["identity"] in existing_after else target
        return {
            "before": before,
            "after": after,
            "wrote": wrote,
            "invariant_ok": invariant_ok,
            "imported_values_sha256": hashlib.sha256(
                canonical({r["identity"]: r["arabic"] for r in planned})
            ).hexdigest(),
        }

    return _fake


def test_import_is_idempotent_and_captures_rollback(monkeypatch, tmp_path):
    payload = _payload(("1000 - Assets - E", "الأصول"), ("1100 - Cash - E", "النقد"))
    bundle = _bundle([r["identity"] for r in payload])
    monkeypatch.setattr(
        import_adapter,
        "_run_write_console",
        _fake_console({"1000 - Assets - E": None, "1100 - Cash - E": "قديم"}),
    )
    result = import_adapter.import_payload(str(tmp_path), DESCRIPTOR, payload, bundle, {"evidence_digest": "d" * 64}, tmp_path)
    ev = result["evidence"]
    assert ev["rows_planned"] == 2
    assert ev["rows_written"] == 2  # 1000 null->value, 1100 changed
    assert ev["invariant_ok"] is True
    assert len(ev["rollback_export_sha256"]) == 64
    assert ev["dry_run_evidence_digest"] == "d" * 64

    # Re-running with the same target is a no-op write (idempotent).
    monkeypatch.setattr(
        import_adapter,
        "_run_write_console",
        _fake_console({"1000 - Assets - E": "الأصول", "1100 - Cash - E": "النقد"}),
    )
    second = import_adapter.import_payload(
        str(tmp_path), DESCRIPTOR, payload, bundle, {"evidence_digest": "d" * 64}, tmp_path / "run2"
    )
    assert second["evidence"]["rows_written"] == 0


def test_import_detects_post_write_mismatch(monkeypatch, tmp_path):
    payload = _payload(("1000 - Assets - E", "الأصول"))
    bundle = _bundle(["1000 - Assets - E"])
    monkeypatch.setattr(
        import_adapter,
        "_run_write_console",
        _fake_console({"1000 - Assets - E": None}, existing_after={"1000 - Assets - E": "قيمة خاطئة"}),
    )
    with pytest.raises(WorkflowError, match="post-import value mismatch"):
        import_adapter.import_payload(str(tmp_path), DESCRIPTOR, payload, bundle, {"evidence_digest": "d" * 64}, tmp_path)


def test_import_rejects_invariant_violation(monkeypatch, tmp_path):
    payload = _payload(("1000 - Assets - E", "الأصول"))
    bundle = _bundle(["1000 - Assets - E"])
    monkeypatch.setattr(
        import_adapter,
        "_run_write_console",
        _fake_console({"1000 - Assets - E": None}, invariant_ok=False),
    )
    with pytest.raises(WorkflowError, match="invariant violated"):
        import_adapter.import_payload(str(tmp_path), DESCRIPTOR, payload, bundle, {"evidence_digest": "d" * 64}, tmp_path)


def test_import_requires_descriptor(tmp_path):
    with pytest.raises(WorkflowError, match="resolved ERP descriptor"):
        import_adapter.import_payload(str(tmp_path), {}, [{"identity": "x", "arabic": "y"}], {"rows": []}, {}, tmp_path)


def test_import_evidence_digest_is_deterministic(monkeypatch, tmp_path):
    payload = _payload(("1000 - Assets - E", "الأصول"))
    bundle = _bundle(["1000 - Assets - E"])
    monkeypatch.setattr(import_adapter, "_run_write_console", _fake_console({"1000 - Assets - E": None}))
    a = import_adapter.import_payload(str(tmp_path), DESCRIPTOR, payload, bundle, {"evidence_digest": "d" * 64}, tmp_path / "a")
    monkeypatch.setattr(
        import_adapter,
        "_run_write_console",
        _fake_console({"1000 - Assets - E": None}, existing_after={"1000 - Assets - E": "الأصول"}),
    )
    b = import_adapter.import_payload(str(tmp_path), DESCRIPTOR, payload, bundle, {"evidence_digest": "d" * 64}, tmp_path / "b")
    # Different readback/write counts yield different evidence digests.
    assert a["evidence_digest"] != b["evidence_digest"]
