"""Offline tests for the standalone read-only projection."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from engineering_control_contracts.readonly_projection import (
    ProjectionDenied,
    ProjectionInvalid,
    ProjectionUnsupported,
    ReadPrincipal,
    project_work_item,
    project_work_item_snapshot,
)


def _config(**updates):
    config = {
        "work_item": "work-a",
        "project_id": "project-a",
        "branch": "test",
        "stages": ["1"],
        "stage": "1",
        "base_commit": "b" * 40,
        "plan_revision_hash": "a" * 64,
        "scope_hash": "c" * 64,
        "roles_hash": "d" * 64,
        "scope": {"allowed_paths": ["docs/ai/work-items/work-a/**"]},
        "roles": {"builder": {"tool": "codex", "binary": "/secret/path"}},
        "candidate": {"candidate_id": "e" * 64},
    }
    config.update(updates)
    return config


def _make_db(root: Path, *, events=3, config=None):
    var = root / "orchestrator" / "var"
    var.mkdir(parents=True)
    db = var / "checkpoints.db"
    conn = sqlite3.connect(db)
    try:
        conn.executescript(
            """
            CREATE TABLE workflow_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE workflow_events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                kind TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_utc TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO workflow_meta VALUES ('config', ?)",
            (json.dumps(config if config is not None else _config()),),
        )
        for index in range(events):
            conn.execute(
                "INSERT INTO workflow_events(event_id, kind, payload, created_utc) VALUES (?,?,?,?)",
                (
                    f"ev-{index}",
                    "grant" if index == 0 else "observation",
                    json.dumps({"token_id": "secret-token", "safe": f"value-{index}"}),
                    f"2026-11-03T10:00:0{index}Z",
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return db


def _principal(**updates):
    values = dict(
        subject="synthetic-owner",
        project_id="project-a",
        work_item_id="work-a",
        capabilities=frozenset({"read"}),
    )
    values.update(updates)
    return ReadPrincipal(**values)


def _snapshot_meta(root: Path):
    return {
        str(p.relative_to(root)): (
            p.read_bytes(),
            p.stat().st_mode & 0o777,
            p.stat().st_size,
            p.stat().st_mtime_ns,
        )
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _snapshot(root: Path):
    return {
        str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mode & 0o777)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_supported_projection_is_bounded_sanitized_and_read_only(tmp_path):
    db = _make_db(tmp_path)
    stale = tmp_path / "orchestrator/var/events.jsonl"
    stale.write_text("this exported ledger is intentionally stale\n")
    before = _snapshot(tmp_path)

    result = project_work_item(tmp_path, _principal(), after=0, limit=2)

    assert result["work_item"]["work_item"] == "work-a"
    assert result["work_item"]["role_names"] == ["builder"]
    assert "binary" not in json.dumps(result["work_item"])
    assert len(result["events"]) == 2
    assert result["truncated"] is True
    assert result["next_cursor"] == 2
    assert result["source"] == "sqlite_workflow_meta_and_events"
    assert "secret-token" not in json.dumps(result)
    assert all(event["payload_key_count"] == 2 for event in result["events"])
    assert _snapshot(tmp_path) == before
    assert stale.read_text() == "this exported ledger is intentionally stale\n"


def test_cursor_and_limit_bounds(tmp_path):
    _make_db(tmp_path, events=4)
    first = project_work_item(tmp_path, _principal(), after=0, limit=2)
    second = project_work_item(tmp_path, _principal(), after=first["next_cursor"], limit=2)
    assert [e["seq"] for e in first["events"]] == [1, 2]
    assert [e["seq"] for e in second["events"]] == [3, 4]
    assert second["truncated"] is False
    for kwargs in ({"limit": 0}, {"limit": 101}, {"after": -1}, {"after": True}, {"limit": True}):
        with pytest.raises(ProjectionInvalid):
            project_work_item(tmp_path, _principal(), **kwargs)


def test_authorization_and_object_scope_are_enforced(tmp_path):
    _make_db(tmp_path)
    with pytest.raises(ProjectionDenied):
        project_work_item(tmp_path, _principal(work_item_id="work-b"))
    with pytest.raises(ProjectionDenied):
        project_work_item(tmp_path, _principal(project_id="project-b"))
    with pytest.raises(ProjectionDenied):
        ReadPrincipal(
            subject="synthetic-owner",
            project_id="project-a",
            work_item_id="work-a",
            capabilities=frozenset({"observe"}),
        )


def test_absent_corrupt_and_malformed_databases_fail_closed(tmp_path):
    with pytest.raises(ProjectionUnsupported):
        project_work_item(tmp_path, _principal())

    corrupt_root = tmp_path / "corrupt"
    var = corrupt_root / "orchestrator" / "var"
    var.mkdir(parents=True)
    (var / "checkpoints.db").write_bytes(b"not a sqlite database")
    with pytest.raises(ProjectionUnsupported):
        project_work_item(corrupt_root, _principal())

    bad_root = tmp_path / "bad-config"
    _make_db(bad_root, config={"work_item": "work-a", "project_id": "project-a"})
    db = bad_root / "orchestrator/var/checkpoints.db"
    conn = sqlite3.connect(db)
    try:
        conn.execute("UPDATE workflow_meta SET value='{' WHERE key='config'")
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(ProjectionUnsupported):
        project_work_item(bad_root, _principal())


def test_symlink_paths_and_relative_root_are_rejected(tmp_path):
    db = _make_db(tmp_path)
    with pytest.raises(ProjectionInvalid):
        project_work_item(Path("relative"), _principal())

    alias = tmp_path / "db-link"
    alias.symlink_to(db)
    original = db.with_name("checkpoints.real")
    db.rename(original)
    alias.unlink()
    alias.symlink_to(original)
    # Restore the canonical path as a symlink to the real file.
    alias.unlink()
    db.symlink_to(original)
    with pytest.raises(ProjectionInvalid):
        project_work_item(tmp_path, _principal())


def test_live_wal_or_sidecars_are_unsupported_and_untouched(tmp_path):
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "INSERT INTO workflow_events(event_id, kind, payload, created_utc) VALUES (?,?,?,?)",
            ("live-ev", "grant", json.dumps({"token_id": "live"}), "2026-11-03T11:00:00Z"),
        )
        conn.commit()
        before = _snapshot(tmp_path)
        with pytest.raises(ProjectionUnsupported):
            project_work_item(tmp_path, _principal())
        assert _snapshot(tmp_path) == before
    finally:
        conn.close()


def test_oversized_payload_and_config_are_unsupported(tmp_path):
    big_root = tmp_path / "big"
    _make_db(big_root)
    db = big_root / "orchestrator/var/checkpoints.db"
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "INSERT INTO workflow_events(event_id, kind, payload, created_utc) VALUES (?,?,?,?)",
            ("big", "observation", json.dumps({"blob": "x" * 70000}), "2026-11-03T12:00:00Z"),
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(ProjectionUnsupported):
        project_work_item(big_root, _principal())


def test_wal_present_shm_absent_crash_state_fails_before_connect(tmp_path):
    db = _make_db(tmp_path)
    script = r"""
import os
import sqlite3
import sys
conn = sqlite3.connect(sys.argv[1])
conn.execute("PRAGMA journal_mode=WAL")
conn.execute(
    "INSERT INTO workflow_events(event_id, kind, payload, created_utc) VALUES (?,?,?,?)",
    ("crash-wal", "grant", '{"token_id": "crash"}', "2026-11-03T13:00:00Z"),
)
conn.commit()
os._exit(0)
"""
    proc = subprocess.run([sys.executable, "-c", script, str(db)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    wal = Path(str(db) + "-wal")
    shm = Path(str(db) + "-shm")
    assert wal.exists()
    if shm.exists():
        shm.unlink()
    assert not shm.exists()
    before = _snapshot(tmp_path)

    with pytest.raises(ProjectionUnsupported):
        project_work_item(tmp_path, _principal())

    assert not shm.exists()
    assert _snapshot(tmp_path) == before


def test_uri_special_path_is_read_without_side_effects(tmp_path):
    root = tmp_path / "root ?#% unicode"
    _make_db(root)
    before = _snapshot(root)
    result = project_work_item(root, _principal())
    assert result["work_item"]["work_item"] == "work-a"
    assert _snapshot(root) == before


def test_symlinked_root_is_rejected(tmp_path):
    root = tmp_path / "real-root"
    _make_db(root)
    alias = tmp_path / "alias-root"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ProjectionInvalid):
        project_work_item(alias, _principal())


def test_project_binding_is_required_and_exact(tmp_path):
    root = tmp_path / "no-project"
    _make_db(root, config={"work_item": "work-a", "stage": "1"})
    with pytest.raises(ProjectionUnsupported):
        project_work_item(root, _principal())


def test_untrusted_config_and_event_values_fail_closed(tmp_path):
    bad_role = tmp_path / "bad-role"
    config = _config()
    config["roles"] = {"not-a-role": {}}
    _make_db(bad_role, config=config)
    with pytest.raises(ProjectionUnsupported):
        project_work_item(bad_role, _principal())

    bad_stage = tmp_path / "bad-stage"
    config = _config()
    config["stage"] = "unbounded-stage-name"
    _make_db(bad_stage, config=config)
    with pytest.raises(ProjectionUnsupported):
        project_work_item(bad_stage, _principal())

    bad_event = tmp_path / "bad-event"
    _make_db(bad_event, events=1)
    conn = sqlite3.connect(bad_event / "orchestrator/var/checkpoints.db")
    try:
        conn.execute("UPDATE workflow_events SET kind='untrusted'")
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(ProjectionUnsupported):
        project_work_item(bad_event, _principal())


def test_idle_wal_configured_database_without_sidecars_fails_before_connect(tmp_path):
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        conn.execute(
            "INSERT INTO workflow_events(event_id, kind, payload, created_utc) VALUES (?,?,?,?)",
            ("idle-wal", "observation", '{"safe": "idle"}', "2026-11-03T14:00:00Z"),
        )
        conn.commit()
    finally:
        conn.close()
    assert not Path(str(db) + "-wal").exists()
    assert not Path(str(db) + "-shm").exists()
    before = _snapshot(tmp_path)

    with pytest.raises(ProjectionUnsupported, match="persistently WAL-configured"):
        project_work_item(tmp_path, _principal())

    assert not Path(str(db) + "-wal").exists()
    assert not Path(str(db) + "-shm").exists()
    assert _snapshot(tmp_path) == before


def _real_engine_checkpoint(configured):
    from engine import Engine
    from test_engine import Stub

    root, config = configured
    engine = Engine(root, launcher=Stub())
    try:
        engine.initialize(config)
        engine.run()
    finally:
        engine.close()
    return root


def test_real_engine_checkpoint_without_project_binding_fails_closed(configured):
    root = _real_engine_checkpoint(configured)
    db = root / "orchestrator/var/checkpoints.db"
    # Setup-only normalization: make the real engine DB a quiescent rollback DB
    # so the missing project binding, not WAL, is the observed failure.
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"
    finally:
        conn.close()
    before = _snapshot(root)
    with pytest.raises(ProjectionUnsupported, match="project binding"):
        project_work_item(root, _principal(work_item_id="test-work"))
    assert _snapshot(root) == before


def test_real_engine_idle_wal_checkpoint_fails_before_connect(configured):
    root = _real_engine_checkpoint(configured)
    db = root / "orchestrator/var/checkpoints.db"
    header = db.read_bytes()[:100]
    assert header[18] == 2 or header[19] == 2
    # Engine close should leave a quiescent WAL-configured DB; if a sidecar
    # remains, checkpoint it as setup before the no-write projection check.
    if Path(str(db) + "-wal").exists():
        conn = sqlite3.connect(db)
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            conn.close()
    assert not Path(str(db) + "-wal").exists()
    assert not Path(str(db) + "-shm").exists()
    before = _snapshot(root)
    with pytest.raises(ProjectionUnsupported, match="persistently WAL-configured"):
        project_work_item(root, _principal(work_item_id="test-work"))
    assert not Path(str(db) + "-wal").exists()
    assert not Path(str(db) + "-shm").exists()
    assert _snapshot(root) == before


def test_project_and_cursor_bounds_are_enforced(tmp_path):
    _make_db(tmp_path)
    with pytest.raises(ProjectionInvalid):
        _principal(project_id="p" * 129)
    with pytest.raises(ProjectionInvalid):
        project_work_item(tmp_path, _principal(), after=2**63)


def test_concurrent_journal_mode_race_is_not_zero_write(tmp_path, monkeypatch):
    """Deliberate regression demonstrating the unresolved non-cooperating-writer race.

    The precheck sees a clean DELETE-mode DB. A test hook switches it to WAL
    before the read-only connection. The projection detects sidecars after open
    and returns unsupported, but SQLite has already created -wal/-shm. This test
    asserts the limitation rather than claiming zero-write safety.
    """
    import engineering_control_contracts.readonly_projection as projection

    db = _make_db(tmp_path)
    before = _snapshot(tmp_path)
    real_connect = projection._connect

    def race_connect(path):
        writer = sqlite3.connect(path)
        try:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute(
                "INSERT INTO workflow_events(event_id, kind, payload, created_utc) VALUES (?,?,?,?)",
                ("race", "observation", json.dumps({"safe": "race"}), "2026-11-03T15:00:00Z"),
            )
            writer.commit()
        finally:
            writer.close()
        return real_connect(path)

    monkeypatch.setattr(projection, "_connect", race_connect)
    with pytest.raises(ProjectionUnsupported, match="sidecars appeared"):
        project_work_item(tmp_path, _principal())
    assert Path(str(db) + "-wal").exists()
    assert Path(str(db) + "-shm").exists()
    assert _snapshot(tmp_path) != before


def test_snapshot_copy_reads_only_private_copy_and_leaves_source_unchanged(tmp_path):
    _make_db(tmp_path)
    before = _snapshot_meta(tmp_path)
    result = project_work_item_snapshot(tmp_path, _principal())
    assert result["work_item"]["work_item"] == "work-a"
    assert _snapshot_meta(tmp_path) == before


def test_snapshot_copy_does_not_run_sqlite_on_source(tmp_path, monkeypatch):
    _make_db(tmp_path)
    import engineering_control_contracts.readonly_projection as projection

    source = (tmp_path / "orchestrator/var/checkpoints.db").resolve()
    real_connect = sqlite3.connect
    paths = []

    def record(path, *args, **kwargs):
        paths.append(str(path))
        return real_connect(path, *args, **kwargs)

    monkeypatch.setattr(projection.sqlite3, "connect", record)
    project_work_item_snapshot(tmp_path, _principal())
    assert paths
    assert str(source) not in "\n".join(paths)
    assert all("control-projection-" in path for path in paths)


def test_snapshot_copy_fails_closed_without_project_and_preserves_source(tmp_path):
    _make_db(tmp_path, config={"work_item": "work-a", "stage": "1"})
    before = _snapshot_meta(tmp_path)
    with pytest.raises(ProjectionUnsupported, match="project binding"):
        project_work_item_snapshot(tmp_path, _principal())
    assert _snapshot_meta(tmp_path) == before


def test_snapshot_copy_rejects_idle_wal_before_copy_without_sidecars(tmp_path):
    db = _make_db(tmp_path)
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "INSERT INTO workflow_events(event_id, kind, payload, created_utc) VALUES (?,?,?,?)",
            ("idle-wal-copy", "observation", '{"safe": "idle"}', "2026-11-03T16:00:00Z"),
        )
        conn.commit()
    finally:
        conn.close()
    assert not Path(str(db) + "-wal").exists()
    assert not Path(str(db) + "-shm").exists()
    before = _snapshot_meta(tmp_path)
    with pytest.raises(ProjectionUnsupported, match="persistently WAL-configured"):
        project_work_item_snapshot(tmp_path, _principal())
    assert _snapshot_meta(tmp_path) == before
    assert not Path(str(db) + "-wal").exists()
    assert not Path(str(db) + "-shm").exists()


def test_snapshot_copy_real_engine_idle_wal_fails_without_source_sidecars(configured):
    from engine import Engine
    from test_engine import Stub

    root, config = configured
    engine = Engine(root, launcher=Stub())
    try:
        engine.initialize(config)
        engine.run()
    finally:
        engine.close()
    db = root / "orchestrator/var/checkpoints.db"
    if Path(str(db) + "-wal").exists():
        conn = sqlite3.connect(db)
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            conn.close()
    assert not Path(str(db) + "-wal").exists()
    assert not Path(str(db) + "-shm").exists()
    before = _snapshot_meta(root)
    with pytest.raises(ProjectionUnsupported, match="persistently WAL-configured"):
        project_work_item_snapshot(root, _principal(work_item_id="test-work"))
    assert _snapshot_meta(root) == before
    assert not Path(str(db) + "-wal").exists()
    assert not Path(str(db) + "-shm").exists()


def test_snapshot_copy_enforces_incremental_budget_and_cleans_temp(tmp_path, monkeypatch):
    import engineering_control_contracts.readonly_projection as projection

    db = _make_db(tmp_path)
    source = db.resolve()
    monkeypatch.setattr(projection, "MAX_SNAPSHOT_BYTES", 65536)
    real_read = projection.os.read
    grew = False

    def growing_read(fd, size):
        nonlocal grew
        chunk = real_read(fd, size)
        if not grew:
            grew = True
            with source.open("ab") as writer:
                writer.write(b"x" * 70000)
        return chunk

    real_tmp = projection.tempfile.TemporaryDirectory
    created = []

    def tracked_tmp(*args, **kwargs):
        manager = real_tmp(*args, **kwargs)
        created.append(Path(manager.name))
        return manager

    monkeypatch.setattr(projection.os, "read", growing_read)
    monkeypatch.setattr(projection.tempfile, "TemporaryDirectory", tracked_tmp)
    with pytest.raises(ProjectionUnsupported, match="grew beyond"):
        project_work_item_snapshot(tmp_path, _principal())
    assert created
    assert all(not path.exists() for path in created)
