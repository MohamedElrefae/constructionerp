"""Offline tests for the native Stage 4 DRY_RUN executor.

The live site read is mocked; these tests prove the read-only checks, the blocking
classification and the deterministic evidence digest without touching ERP data.
"""

import json

import pytest

import dry_run
from core import canonical, digest


DESCRIPTOR = {
    "bench_root": "/tmp/bench",
    "site": "test.localhost",
    "private_root": "/tmp/private",
    "erp_checkout": "/tmp/bench/apps/construction",
    "site_classification": "non-production test",
}


def _payload(*rows):
    return [{"identity": i, "arabic": a} for i, a in rows]


def _bundle(identities, decision="approved"):
    return {
        "schema": "construction-stage4-account-review-bundle/v1",
        "rows": [
            {
                "identity": i,
                "english": i.split(" - ", 1)[1] if " - " in i else i,
                "is_group": False,
                "proposal": {"arabic": "x"},
                "a2_review": {"identity": i, "decision": decision},
            }
            for i in identities
        ],
    }


def _live(entries):
    """entries: {identity: row-or-None}"""
    return {"accounts": entries, "total_accounts": len([v for v in entries.values() if v])}


def test_dry_run_clean_payload_is_not_blocking(monkeypatch, tmp_path):
    payload = _payload(("1000 - Assets - E", "الأصول"), ("1100 - Cash - E", "النقد"))
    bundle = _bundle([r["identity"] for r in payload])
    live = _live({
        "1000 - Assets - E": {"name": "1000 - Assets - E", "account_name_ar": None, "parent_account": None},
        "1100 - Cash - E": {"name": "1100 - Cash - E", "account_name_ar": None, "parent_account": "1000 - Assets - E"},
    })
    monkeypatch.setattr(dry_run, "_run_read_console", lambda *a, **k: live)

    result = dry_run.dry_run(str(tmp_path), DESCRIPTOR, payload, bundle, tmp_path)
    s = result["summary"]
    assert s["blocking"] is False
    assert s["live_accounts_present"] == 2
    assert s["stale_rows"] == []
    assert len(result["evidence_digest"]) == 64


def test_dry_run_reports_stale_missing_and_blank(monkeypatch, tmp_path):
    payload = _payload(
        ("1000 - Assets - E", "الأصول"),
        ("1100 - Cash - E", "النقد"),
        ("1200 - Bank - E", "   "),
    )
    bundle = _bundle([r["identity"] for r in payload])
    live = _live({
        "1000 - Assets - E": {"name": "1000 - Assets - E"},
        "1100 - Cash - E": None,  # stale row: governed identity absent from live
        "1200 - Bank - E": {"name": "1200 - Bank - E"},
    })
    monkeypatch.setattr(dry_run, "_run_read_console", lambda *a, **k: live)

    result = dry_run.dry_run(str(tmp_path), DESCRIPTOR, payload, bundle, tmp_path)
    s = result["summary"]
    assert s["blocking"] is True
    assert "1100 - Cash - E" in s["stale_rows"]
    assert "1200 - Bank - E" in s["blank_names"]


def test_dry_run_reports_unexpected_current_and_duplicate(monkeypatch, tmp_path):
    payload = _payload(("1000 - Assets - E", "الأصول"), ("1000 - Assets Dup - E", "الأصول ٢"))
    bundle = _bundle([r["identity"] for r in payload])
    live = _live({
        "1000 - Assets - E": {"name": "1000 - Assets - E", "account_name_ar": "قيمة مختلفة"},
        "1000 - Assets Dup - E": {"name": "1000 - Assets Dup - E", "account_name_ar": None},
    })
    monkeypatch.setattr(dry_run, "_run_read_console", lambda *a, **k: live)

    result = dry_run.dry_run(str(tmp_path), DESCRIPTOR, payload, bundle, tmp_path)
    s = result["summary"]
    assert "1000 - Assets - E" in s["unexpected_current_values"]
    assert "1000" in s["duplicate_codes"]
    assert s["blocking"] is True


def test_dry_run_reports_approval_gap(monkeypatch, tmp_path):
    payload = _payload(("1000 - Assets - E", "الأصول"))
    bundle = _bundle(["1000 - Assets - E"], decision="rejected")
    live = _live({"1000 - Assets - E": {"name": "1000 - Assets - E", "account_name_ar": None}})
    monkeypatch.setattr(dry_run, "_run_read_console", lambda *a, **k: live)

    result = dry_run.dry_run(str(tmp_path), DESCRIPTOR, payload, bundle, tmp_path)
    assert result["summary"]["approval_gaps"] == ["1000 - Assets - E"]
    assert result["summary"]["blocking"] is True


def test_dry_run_digest_is_deterministic_and_binds_payload(monkeypatch, tmp_path):
    payload = _payload(("1000 - Assets - E", "الأصول"))
    bundle = _bundle(["1000 - Assets - E"])
    live = _live({"1000 - Assets - E": {"name": "1000 - Assets - E", "account_name_ar": None}})
    monkeypatch.setattr(dry_run, "_run_read_console", lambda *a, **k: live)

    first = dry_run.dry_run(str(tmp_path), DESCRIPTOR, payload, bundle, tmp_path / "run1")
    # Changing the planned Arabic changes the bound digest.
    payload2 = _payload(("1000 - Assets - E", "إجمالي الأصول"))
    second = dry_run.dry_run(str(tmp_path), DESCRIPTOR, payload2, bundle, tmp_path / "run2")
    assert first["evidence_digest"] != second["evidence_digest"]

    # Re-running identical inputs is deterministic apart from the recorded timestamp.
    expected = first["summary"]["planned_values_sha256"]
    assert expected == digest_expectation(payload)


def digest_expectation(payload):
    planned = {r["identity"]: r["arabic"] for r in payload}
    import hashlib

    return hashlib.sha256(canonical(planned)).hexdigest()


def test_dry_run_requires_descriptor(tmp_path):
    from core import WorkflowError

    with pytest.raises(WorkflowError, match="resolved ERP descriptor"):
        dry_run.dry_run(str(tmp_path), {}, [], {"rows": []}, tmp_path)
