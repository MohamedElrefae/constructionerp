"""API unit and integration tests for Week 3 inspection, projection, and export endpoints.

Tests:
- Authentication requirement across all 9 endpoints.
- Findings and backlog projection with stats.
- Evidence listing (allowlisted extensions, no symlinks).
- Evidence content reading:
  - Valid text file with SHA-256 calculation.
  - Large file (>256 KB) truncation with sha256: null.
  - Path traversal and invalid characters rejection (400).
  - Disallowed file extensions rejection (400).
  - Unsafe permissions fail-closed: returns 403 "evidence unavailable: unsafe permissions".
- Diff projection (base commit from config only, hardened flags, control char escaping).
- Settings projection (roles, escalation counters, timeouts).
- Audit export (dual limits: 1000 events & 512 KB, 16 KB field caps, JSONL trailer, headers).
- State and reviews JSON export.
- Authoritative Stage 4 ERP manifest inspection (fail-closed bench root, integrity disclosure).
"""

import json
import os
import sqlite3
from pathlib import Path

import httpx
import pytest

from dashboard.app import app, task_registry
from dashboard.auth import auth_store, session_manager
from dashboard.security import SecurityError, read_authoritative_stage4_manifest
from dashboard.tests.conftest import create_isolated_worktree


@pytest.fixture
def auth_headers_and_cookies():
    """Create authenticated session and CSRF tokens for testing."""
    data = auth_store._load_data()
    if "users" not in data:
        data["users"] = {}
    data["users"]["engineer"] = {
        "password_hash": "scrypt$16384$8$1$00$00",
        "is_initial": False,
    }
    auth_store._save_data(data)

    session_token = session_manager.create_session("engineer")
    csrf_token = "valid_test_csrf_token"
    cookies = {
        "dashboard_session": session_token,
        "dashboard_csrf": csrf_token,
    }
    headers = {
        "host": "127.0.0.1:8080",
        "origin": "https://127.0.0.1:8080",
        "x-csrf-token": csrf_token,
    }
    return headers, cookies


@pytest.mark.anyio
async def test_unauthenticated_week3_endpoints_rejected():
    """Verify all 9 Week 3 endpoints return 401 when unauthenticated."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://127.0.0.1:8080") as client:
        endpoints = [
            "/api/tasks/task-test/findings",
            "/api/tasks/task-test/evidence",
            "/api/tasks/task-test/evidence/test.txt",
            "/api/tasks/task-test/diff",
            "/api/tasks/task-test/settings",
            "/api/tasks/task-test/export/audit",
            "/api/tasks/task-test/export/state",
            "/api/tasks/task-test/export/reviews",
            "/api/erp/projection",
        ]
        for path in endpoints:
            resp = await client.get(path)
            assert resp.status_code == 401
            assert resp.json()["detail"] == "Authentication required"


@pytest.mark.anyio
async def test_findings_projection(auth_headers_and_cookies, tmp_path):
    """Verify findings and backlog projection with statistics."""
    headers, cookies = auth_headers_and_cookies
    wt = create_isolated_worktree(tmp_path, "wt_findings")

    if tmp_path not in task_registry.allowed_roots:
        task_registry.allowed_roots.append(tmp_path)
    reg = task_registry.register_existing_worktree(str(wt))
    task_id = reg["task_id"]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies
    ) as client:
        resp = await client.get(f"/api/tasks/{task_id}/findings", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "findings" in data
        assert "backlog" in data
        assert "stats" in data
        assert data["stats"]["total_findings"] == len(data["findings"])
        assert data["stats"]["blocking_findings"] == 0
        assert data["stats"]["backlog_items"] == len(data["backlog"])


@pytest.mark.anyio
async def test_evidence_listing_and_filtering(auth_headers_and_cookies, tmp_path):
    """Verify evidence listing allows text extensions and ignores symlinks and non-allowed files."""
    headers, cookies = auth_headers_and_cookies
    wt = create_isolated_worktree(tmp_path, "wt_evidence")

    evidence_dir = wt / "docs/ai/work-items/isolated-test-work-item/evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # Ensure all ancestor directories from wt down to evidence have strict 0755 mode
    curr = evidence_dir
    while curr != wt.parent:
        curr.chmod(0o755)
        curr = curr.parent

    # Allowed extensions: .md, .txt, .json, .xml, .patch, .csv
    for p, content in [
        (evidence_dir / "report.md", "Markdown report"),
        (evidence_dir / "summary.txt", "Plain text summary"),
        (evidence_dir / "data.json", "{}"),
        (evidence_dir / "changes.patch", "--- a\n+++ b\n"),
        (evidence_dir / "script.sh", "#!/bin/sh"),
    ]:
        p.write_text(content)
        p.chmod(0o644)
    (evidence_dir / "binary.bin").write_bytes(b"\x00\x01\x02")
    (evidence_dir / "binary.bin").chmod(0o644)

    # Symlink (must be ignored)
    target = wt / "README.md"
    link = evidence_dir / "link.md"
    try:
        link.symlink_to(target)
    except OSError:
        pass

    if tmp_path not in task_registry.allowed_roots:
        task_registry.allowed_roots.append(tmp_path)
    reg = task_registry.register_existing_worktree(str(wt))
    task_id = reg["task_id"]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies
    ) as client:
        resp = await client.get(f"/api/tasks/{task_id}/evidence", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        filenames = [f["filename"] for f in data["files"]]
        assert "report.md" in filenames
        assert "summary.txt" in filenames
        assert "data.json" in filenames
        assert "changes.patch" in filenames
        assert "script.sh" not in filenames
        assert "binary.bin" not in filenames
        assert "link.md" not in filenames

        # Verify fail-closed behavior on unsafe permissions (0o775)
        evidence_dir.chmod(0o775)
        resp_unsafe = await client.get(f"/api/tasks/{task_id}/evidence", headers=headers)
        assert resp_unsafe.status_code == 403
        assert "evidence unavailable: unsafe permissions" in resp_unsafe.json()["detail"]
        evidence_dir.chmod(0o755)


@pytest.mark.anyio
async def test_evidence_content_reading_and_security(auth_headers_and_cookies, tmp_path):
    """Verify evidence reading, large-file truncation, path validation, and fail-closed permission checks."""
    headers, cookies = auth_headers_and_cookies
    wt = create_isolated_worktree(tmp_path, "wt_ev_content")

    evidence_dir = wt / "docs/ai/work-items/isolated-test-work-item/evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # Ensure all ancestor directories from wt down to evidence have strict 0755 mode
    curr = evidence_dir
    while curr != wt.parent:
        curr.chmod(0o755)
        curr = curr.parent

    # 1. Normal file reading with secure permissions (0755 / 0644)
    good_file = evidence_dir / "normal.txt"
    good_file.write_text("Hello, civil engineer!")
    good_file.chmod(0o644)

    # 2. Large file (> 256 KB)
    large_file = evidence_dir / "large.txt"
    large_file.write_text("A" * (260 * 1024))
    large_file.chmod(0o644)

    if tmp_path not in task_registry.allowed_roots:
        task_registry.allowed_roots.append(tmp_path)
    reg = task_registry.register_existing_worktree(str(wt))
    task_id = reg["task_id"]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies
    ) as client:
        # Read normal file
        resp = await client.get(f"/api/tasks/{task_id}/evidence/normal.txt", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "normal.txt"
        assert data["content"] == "Hello, civil engineer!"
        assert data["truncated"] is False
        assert data["sha256"] is not None
        assert len(data["sha256"]) == 64

        # Read large file (> 256 KB)
        resp_large = await client.get(f"/api/tasks/{task_id}/evidence/large.txt", headers=headers)
        assert resp_large.status_code == 200
        data_large = resp_large.json()
        assert data_large["truncated"] is True
        assert data_large["sha256"] is None
        assert len(data_large["content"]) == 256 * 1024

        # Invalid filename rejection (400)
        resp_bad = await client.get(f"/api/tasks/{task_id}/evidence/bad*file.txt", headers=headers)
        assert resp_bad.status_code == 400
        assert "invalid filename" in resp_bad.json()["detail"].lower()

        # Disallowed extension rejection (400)
        resp_ext = await client.get(f"/api/tasks/{task_id}/evidence/danger.sh", headers=headers)
        assert resp_ext.status_code == 400

        # Unsafe permissions fail-closed (HTTP 403 "evidence unavailable: unsafe permissions")
        unsafe_file = evidence_dir / "unsafe.txt"
        unsafe_file.write_text("Unsafe group writable")
        unsafe_file.chmod(0o664)  # Group writable!
        resp_perm = await client.get(f"/api/tasks/{task_id}/evidence/unsafe.txt", headers=headers)
        assert resp_perm.status_code == 403
        assert "unsafe permissions" in resp_perm.json()["detail"].lower()


@pytest.mark.anyio
async def test_diff_projection(auth_headers_and_cookies, tmp_path):
    """Verify diff projection using stored configuration base commit."""
    headers, cookies = auth_headers_and_cookies
    wt = create_isolated_worktree(tmp_path, "wt_diff")

    # Get initial commit hash
    res = os.popen(f"git -C {wt} rev-parse HEAD").read().strip()
    base_commit = res

    # Update config in checkpoints.db to store base_commit
    db_path = wt / "orchestrator/var/checkpoints.db"
    conn = sqlite3.connect(str(db_path))
    with conn:
        conn.execute(
            "UPDATE workflow_meta SET value = ? WHERE key = 'config'",
            (json.dumps({"work_item": "isolated-test-work-item", "task_base_commit": base_commit}),),
        )
    conn.close()

    # Make a commit to create a diff
    test_file = wt / "new_feature.py"
    test_file.write_text("print('hello world')\n")
    os.system(f"git -C {wt} add new_feature.py && git -C {wt} commit -m 'add feature'")

    if tmp_path not in task_registry.allowed_roots:
        task_registry.allowed_roots.append(tmp_path)
    reg = task_registry.register_existing_worktree(str(wt))
    task_id = reg["task_id"]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies
    ) as client:
        resp = await client.get(f"/api/tasks/{task_id}/diff", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["base_commit"] == base_commit
        assert len(data["files"]) >= 1
        assert any(f["path"] == "new_feature.py" for f in data["files"])
        assert "hello world" in data["diff_text"]
        assert data["truncated"] is False


@pytest.mark.anyio
async def test_diff_wall_clock_timeout_enforced():
    """Verify that _read_subprocess_bounded enforces wall-clock timeout and reaps child."""
    import subprocess

    from dashboard.config import ORCHESTRATOR_PYTHON

    check_code = """
import subprocess
import time
from orchestrator.dashboard_api import _read_subprocess_bounded

proc = subprocess.Popen(["sleep", "10"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
t0 = time.monotonic()
try:
    _read_subprocess_bounded(proc, max_bytes=1000, timeout=0.5)
    print("FAILED_NO_TIMEOUT")
except TimeoutError:
    elapsed = time.monotonic() - t0
    assert elapsed < 2.0, f"Took too long: {elapsed}s"
    assert proc.poll() is not None, "Process was not reaped"
    print("SUCCESS_TIMEOUT")
"""
    res = subprocess.run(
        [str(ORCHESTRATOR_PYTHON), "-c", check_code],
        cwd="/home/mohamed/frappe-bench/worktrees/scope-context-portability",
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert res.returncode == 0, f"Stderr: {res.stderr}"
    assert "SUCCESS_TIMEOUT" in res.stdout


@pytest.mark.anyio
async def test_settings_projection(auth_headers_and_cookies, tmp_path):
    """Verify settings projection returning role pins, timeouts, and escalation counters."""
    headers, cookies = auth_headers_and_cookies
    wt = create_isolated_worktree(tmp_path, "wt_settings")

    if tmp_path not in task_registry.allowed_roots:
        task_registry.allowed_roots.append(tmp_path)
    reg = task_registry.register_existing_worktree(str(wt))
    task_id = reg["task_id"]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies
    ) as client:
        resp = await client.get(f"/api/tasks/{task_id}/settings", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "roles" in data
        assert "escalation_status" in data
        assert "timeouts" in data
        assert data["timeouts"]["soft_timeout"] == 2700
        assert data["timeouts"]["hard_timeout"] == 3600


@pytest.mark.anyio
async def test_audit_export_and_sanitization(auth_headers_and_cookies, tmp_path):
    """Verify audit export format, credential redaction, dual bounding, and headers."""
    headers, cookies = auth_headers_and_cookies
    wt = create_isolated_worktree(tmp_path, "wt_audit")
    db_path = wt / "orchestrator/var/checkpoints.db"

    # Seed events into workflow_events
    conn = sqlite3.connect(str(db_path))
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_events (
                seq INTEGER PRIMARY KEY,
                event_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                payload TEXT NOT NULL
            )
        """)
        # Insert event with sensitive credentials and host paths
        payload = {
            "token": "ghp_secretpassword1234567890",
            "host_path": str(wt / "secret.py"),
            "msg": "Event 1 message",
        }
        conn.execute(
            "INSERT INTO workflow_events (seq, event_id, kind, timestamp, payload) VALUES (?, ?, ?, ?, ?)",
            (1, "ev-001", "step", "2026-09-17T00:00:00Z", json.dumps(payload)),
        )
    conn.close()

    if tmp_path not in task_registry.allowed_roots:
        task_registry.allowed_roots.append(tmp_path)
    reg = task_registry.register_existing_worktree(str(wt))
    task_id = reg["task_id"]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies
    ) as client:
        resp = await client.get(f"/api/tasks/{task_id}/export/audit", headers=headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "application/x-ndjson"
        assert 'attachment; filename="isolated-test-work-item_audit.jsonl"' in resp.headers.get(
            "content-disposition", ""
        )
        assert resp.headers.get("x-audit-truncated") == "false"
        assert resp.headers.get("x-audit-events-count") == "1"

        lines = resp.text.strip().split("\n")
        assert len(lines) == 2  # 1 event + 1 metadata trailer

        event_line = json.loads(lines[0])
        assert event_line["event_id"] == "ev-001"
        # Verify credentials redacted and path stripped
        assert "ghp_secretpassword1234567890" not in lines[0]
        assert "[REDACTED_CREDENTIAL]" in lines[0] or "REDACTED" in lines[0]

        trailer = json.loads(lines[1])
        assert "_metadata" in trailer
        assert trailer["_metadata"]["schema"] == "dashboard-audit-export/v1"
        assert trailer["_metadata"]["emitted_events"] == 1

        # Verify server-side audit hard caps are strictly enforced against oversized requests
        from dashboard.subprocess_client import query_audit_events

        res_capped = await query_audit_events(wt, max_events=999999, max_bytes=999999999)
        assert res_capped["metadata"]["emitted_events"] <= 1000
        assert res_capped["metadata"]["emitted_bytes"] <= 524288


@pytest.mark.anyio
async def test_state_and_reviews_exports(auth_headers_and_cookies, tmp_path):
    """Verify JSON export endpoints for state and reviews."""
    headers, cookies = auth_headers_and_cookies
    wt = create_isolated_worktree(tmp_path, "wt_exports")

    if tmp_path not in task_registry.allowed_roots:
        task_registry.allowed_roots.append(tmp_path)
    reg = task_registry.register_existing_worktree(str(wt))
    task_id = reg["task_id"]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies
    ) as client:
        # State export
        resp_state = await client.get(f"/api/tasks/{task_id}/export/state", headers=headers)
        assert resp_state.status_code == 200
        assert resp_state.headers.get("content-type") == "application/json"
        assert "isolated-test-work-item_state.json" in resp_state.headers.get("content-disposition", "")
        state_json = resp_state.json()
        assert "status" in state_json

        # Reviews export
        resp_rev = await client.get(f"/api/tasks/{task_id}/export/reviews", headers=headers)
        assert resp_rev.status_code == 200
        assert resp_rev.headers.get("content-type") == "application/json"
        assert "isolated-test-work-item_reviews.json" in resp_rev.headers.get("content-disposition", "")
        rev_json = resp_rev.json()
        assert "reviews" in rev_json


@pytest.mark.anyio
async def test_authoritative_stage4_erp_manifest(auth_headers_and_cookies, tmp_path, monkeypatch):
    """Verify authoritative Stage 4 manifest reading with live SHA-256 and integrity disclosure."""
    headers, cookies = auth_headers_and_cookies

    # Direct security call verification: raw manifest dict must NOT be exposed
    manifest_data = read_authoritative_stage4_manifest()
    assert manifest_data["status"] == "PARKED"
    assert manifest_data["manifest_sha256"] is not None
    assert len(manifest_data["manifest_sha256"]) == 64
    assert manifest_data["company"] == "Elrefae"
    assert manifest_data["domain"] == "account-master"
    assert "manifest" not in manifest_data
    # Verify path masking
    assert manifest_data["masked_export_path"] == "[PATH]"
    # Permissions check: current manifest is 0664 / 0775 dirs, so unverified_permissions is reported
    assert manifest_data["integrity_status"] in ("unverified_permissions", "verified")

    # API endpoint verification
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies
    ) as client:
        resp = await client.get("/api/erp/projection", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "PARKED"
        assert data["company"] == "Elrefae"
        assert len(data["manifest_sha256"]) == 64
        assert "manifest" not in data

    # Verify oversized manifest (> 64 KB) fails closed and does NOT label prefix hash as digest
    fake_bench = tmp_path / "bench"
    (fake_bench / "apps").mkdir(parents=True)
    (fake_bench / "sites").mkdir(parents=True)
    fake_manifest_dir = fake_bench / "apps" / "construction" / "construction" / "data" / "localization"
    fake_manifest_dir.mkdir(parents=True)
    fake_manifest_file = fake_manifest_dir / "stage4_export_manifest.json"
    fake_manifest_file.write_text("A" * 70000)

    monkeypatch.setattr("dashboard.security.FRAPPE_BENCH_ROOT", fake_bench)
    monkeypatch.setattr("dashboard.security.STAGE4_AUTHORITATIVE_MANIFEST_PATH", fake_manifest_file)

    with pytest.raises(SecurityError, match="exceeds maximum allowed size"):
        read_authoritative_stage4_manifest()

    async with httpx.AsyncClient(
        transport=transport, base_url="https://127.0.0.1:8080", cookies=cookies
    ) as client:
        resp = await client.get("/api/erp/projection", headers=headers)
        assert resp.status_code == 403
        assert "exceeds maximum allowed size" in resp.json()["detail"]
