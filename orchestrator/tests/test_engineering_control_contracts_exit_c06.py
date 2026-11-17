"""Integrated synthetic decision boundary for WP1-C06/A2.

This test file is the only new executable artifact for the C06 boundary proof.
It connects:

- a verified synthetic human principal from the test-only O01 verifier;
- an immutable review snapshot and the real current gate/revision bindings;
- a content-scoped in-test idempotency receipt;
- the real ``Engine.grant_and_synchronize`` approval-only primitive;
- the real coordinator execution lock.

It uses a disposable Git/SQLite fixture and a synthetic launcher only to reach
the PLAN gate. It does not call ``Engine.run``/``approve``/``_drive``/``_prepare``/
``_dispatch``, admit a job, launch a worker or start a subprocess during the
decision or replay. It is not a production identity, transaction, isolation or
WP1 exit proof.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import candidates as candidates_module
import engine as engine_module
import pytest
from core import WorkflowError, bytes_hash, digest, execution_lock, utc
from engine import Engine
from engineering_control_contracts.contract import VERSION
from engineering_control_contracts.offline import Denied, validate
from engineering_control_contracts.provenance import (
    ProvenanceVerifier,
    TestAssertionIssuer,
)
from test_engine import Stub

NOW = datetime(2026, 11, 3, 10, 0, 0, tzinfo=timezone.utc)
TEST_KEY = b"c06-integrated-test-key"
KEY_ID = "c06-key-1"
PROJECT_ID = "project-c06"
SUBJECT = "synthetic-owner"


def _counts(engine: Engine) -> dict[str, int]:
    conn = engine.store.conn
    return {
        "grants": conn.execute("SELECT COUNT(*) FROM workflow_grants").fetchone()[0],
        "grant_events": conn.execute("SELECT COUNT(*) FROM workflow_events WHERE kind = 'grant'").fetchone()[
            0
        ],
        "events": conn.execute("SELECT COUNT(*) FROM workflow_events").fetchone()[0],
        "jobs": conn.execute("SELECT COUNT(*) FROM workflow_jobs").fetchone()[0],
    }


def _statuses(engine: Engine) -> set[str]:
    return {row[0] for row in engine.store.conn.execute("SELECT status FROM workflow_jobs").fetchall()}


class SyntheticDecisionBoundary:
    """Test-only decision boundary around the real approval-only primitive.

    The class deliberately lives in this test module. It is not a service,
    route, adapter or production boundary.
    """

    def __init__(self, engine: Engine, verifier: ProvenanceVerifier, snapshot: dict):
        self.engine = engine
        self.verifier = verifier
        self.snapshot = deepcopy(snapshot)
        self.receipts: dict[tuple, dict] = {}
        self.used_reviews: set[str] = set()
        self.lock_calls = 0
        self.last_principal = None
        self.last_token = None

    def _scope(self, principal, key: str) -> tuple:
        return (
            principal.subject,
            self.snapshot["project_id"],
            self.snapshot["work_item"],
            "decisions",
            self.snapshot["work_item"],
            key,
        )

    @staticmethod
    def _content_hash(request: dict) -> str:
        return digest({k: v for k, v in request.items() if k != "idempotency_key"})

    def _assert_snapshot_request(self, request: dict) -> None:
        if request.get("decision") != "approve_plan":
            raise Denied("unsupported_decision", "Only approve_plan is mapped")
        for field in ("review_snapshot_id", "gate_id", "expected_revision"):
            if request.get(field) != self.snapshot[field]:
                raise Denied("conflict", f"Stale or mismatched {field}")

    def _assert_current_view(self, view: dict) -> None:
        if view.get("plan_granted"):
            raise Denied("conflict", "Plan already granted")
        gate = view.get("gate")
        if not gate or gate.get("gate_id") != self.snapshot["gate_id"]:
            raise Denied("conflict", "Gate is no longer pending")
        checks = {
            "work_item": view.get("work_item"),
            "stage": view.get("stage"),
            "revision": view.get("revision"),
            "plan_revision_hash": view.get("plan_revision_hash"),
            "scope_hash": view.get("scope_hash"),
            "roles_hash": view.get("roles_hash"),
            "candidate_id": (view.get("candidate") or {}).get("candidate_id"),
        }
        for field, actual in checks.items():
            if actual != self.snapshot[field]:
                raise Denied("conflict", f"Stale or mismatched {field}")
        if str(self.engine.root) != self.snapshot["repository_id"]:
            raise Denied("conflict", "Repository binding mismatch")
        if self.engine.config["base_commit"] != self.snapshot["base_commit"]:
            raise Denied("conflict", "Source commit binding mismatch")

    def _assert_source_freshness(self, view: dict) -> None:
        """Git-only candidate/plan recheck, distinct from worker dispatch."""
        try:
            if (view.get("candidate") or {}).get("manifest"):
                self.engine._recheck_candidate(view["candidate"])
            plan_rel = self.engine.store.meta("plan_artifact", self.engine.config["plan_path"])
            plan_path = Path(self.engine.root) / plan_rel
            if bytes_hash(plan_path.read_bytes()) != view["plan_revision_hash"]:
                raise Denied("conflict", "Plan artifact drift")
        except Denied:
            raise
        except Exception as exc:
            raise Denied("conflict", f"Source freshness check failed: {exc}") from exc

    def _token(self) -> dict:
        return _plan_token(self.snapshot)

    def decide(self, envelope: dict, request: dict) -> tuple[dict, str]:
        principal = self.verifier.verify(
            envelope,
            expected_operation="decisions",
            expected_target=self.snapshot["work_item"],
            expected_request_hash=digest(request),
            expected_project=self.snapshot["project_id"],
            expected_work_item=self.snapshot["work_item"],
            now=NOW,
        )
        self.verifier.authorize(principal, "decide")
        self.last_principal = principal

        key = self._scope(principal, request["idempotency_key"])
        content = self._content_hash(request)
        prior = self.receipts.get(key)
        if prior is not None:
            if prior["content"] != content:
                raise Denied("conflict", "Idempotency key reused with different content")
            return deepcopy(prior["receipt"]), "replayed"

        self._assert_snapshot_request(request)
        if self.snapshot["review_snapshot_id"] in self.used_reviews:
            raise Denied("conflict", "Review snapshot already decided")

        with execution_lock(self.engine.runtime / "execution.lock"):
            self.lock_calls += 1
            current = self.engine.view()
            self._assert_current_view(current)
            self._assert_source_freshness(current)
            token = self._token()
            self.last_token = deepcopy(token)
            view_after = self.engine.grant_and_synchronize(token)

        receipt = {
            "schema_version": VERSION,
            "operation_id": "op-c06-integrated-1",
            "receipt_id": "rcpt-c06-integrated-1",
            "resource_id": self.snapshot["work_item"],
            "revision": view_after["revision"],
            "effect": "approval_only",
            "effect_state": "completed",
            "runtime": "native",
            "job_ids": [],
            "execution_complete": False,
        }
        validate("Receipt", receipt)
        self.receipts[key] = {"content": content, "receipt": deepcopy(receipt)}
        self.used_reviews.add(self.snapshot["review_snapshot_id"])
        return receipt, "granted"


@pytest.fixture
def c06_engine(configured):
    """Real engine in a disposable repo, parked at a synthetic PLAN gate."""
    root, config = configured
    engine = Engine(root, launcher=Stub())
    try:
        engine.initialize(config)
        view = engine.run()  # Synthetic setup only; no real agent.
        assert view["gate"] and view["gate"]["scope"] == "PLAN"
        assert not view["plan_granted"]
        yield engine, view
    finally:
        engine.close()


def _snapshot(engine: Engine, view: dict) -> dict:
    return {
        "review_snapshot_id": "review-c06-1",
        "gate_id": view["gate"]["gate_id"],
        "revision": view["revision"],
        "expected_revision": view["revision"],
        "work_item": view["work_item"],
        "stage": view["stage"],
        "plan_revision_hash": view["plan_revision_hash"],
        "scope_hash": view["scope_hash"],
        "roles_hash": view["roles_hash"],
        "candidate_id": view["candidate"]["candidate_id"],
        "base_commit": engine.config["base_commit"],
        "repository_id": str(engine.root),
        "branch": engine.config["branch"],
        "project_id": PROJECT_ID,
    }


def _request(snapshot: dict, key: str = "idem-c06-1") -> dict:
    return {
        "decision": "approve_plan",
        "review_snapshot_id": snapshot["review_snapshot_id"],
        "gate_id": snapshot["gate_id"],
        "expected_revision": snapshot["expected_revision"],
        "idempotency_key": key,
    }


def _plan_token(snapshot: dict) -> dict:
    return {
        "schema_version": 2,
        "token_id": "tok-c06-integrated-1",
        "gate_id": snapshot["gate_id"],
        "work_item": snapshot["work_item"],
        "scope": "PLAN",
        "stages": [snapshot["stage"]],
        "plan_revision_hash": snapshot["plan_revision_hash"],
        "scope_hash": snapshot["scope_hash"],
        "roles_hash": snapshot["roles_hash"],
        "repository_id": snapshot["repository_id"],
        "branch": snapshot["branch"],
        "status": "ISSUED",
        "issuer": SUBJECT,
        "issued_utc": utc(),
    }


def _envelope(issuer: TestAssertionIssuer, request: dict, **overrides) -> dict:
    settings = dict(
        key_id=KEY_ID,
        subject=SUBJECT,
        actor_class="human",
        project_id=PROJECT_ID,
        work_item_id=request.get("work_item_id", "test-work"),
        capabilities=("read", "decide"),
        assurance="multi_factor",
        operation="decisions",
        target_id=request.get("target_id", "test-work"),
        request_hash=digest(request),
        now=NOW,
    )
    settings.update(overrides)
    return issuer.issue(**settings)


def _issuer() -> TestAssertionIssuer:
    return TestAssertionIssuer(
        keys={KEY_ID: TEST_KEY},
        issuer="c06-test-issuer",
        audience="engineering-control",
    )


def _verifier() -> ProvenanceVerifier:
    return ProvenanceVerifier(
        keys_by_issuer={"c06-test-issuer": {KEY_ID: TEST_KEY}},
        trusted_issuers=("c06-test-issuer",),
    )


def _probes(engine: Engine, monkeypatch):
    probes = {}
    for name in ("run", "_prepare", "_dispatch", "_drive", "approve"):
        probe = Mock(side_effect=AssertionError(f"Unexpected dispatch boundary: {name}"))
        probes[name] = probe
        monkeypatch.setattr(engine, name, probe)
    admission = Mock(side_effect=AssertionError("Unexpected job admission"))
    launcher = Mock(side_effect=AssertionError("Unexpected launcher"))
    monkeypatch.setattr(engine.store, "create_job", admission)
    monkeypatch.setattr(engine, "launcher", launcher)

    # Git-only candidate recheck legitimately spawns `git`; a worker process is
    # not legitimate. Guard the command instead of failing every Popen.
    real_popen = engine_module.subprocess.Popen

    def guarded_popen(cmd, *args, **kwargs):
        executable = cmd[0] if isinstance(cmd, list | tuple) and cmd else cmd
        if Path(str(executable)).name != "git":
            raise AssertionError(f"Unexpected non-git subprocess: {cmd!r}")
        return real_popen(cmd, *args, **kwargs)

    monkeypatch.setattr(engine_module.subprocess, "Popen", guarded_popen)
    return [*probes.values(), admission, launcher]


def test_valid_synthetic_human_grants_once_and_replays(c06_engine, monkeypatch):
    engine, view = c06_engine
    snapshot = _snapshot(engine, view)
    boundary = SyntheticDecisionBoundary(engine, _verifier(), snapshot)
    issuer = _issuer()
    request = _request(snapshot)
    envelope = _envelope(issuer, request, work_item_id=snapshot["work_item"], target_id=snapshot["work_item"])
    before = _counts(engine)
    baseline_statuses = _statuses(engine)
    probes = _probes(engine, monkeypatch)
    recheck = Mock(wraps=engine._recheck_candidate)
    monkeypatch.setattr(engine, "_recheck_candidate", recheck)

    receipt, outcome = boundary.decide(envelope, request)

    assert outcome == "granted"
    assert receipt["effect"] == "approval_only"
    assert receipt["effect_state"] == "completed"
    assert receipt["job_ids"] == []
    assert receipt["execution_complete"] is False
    assert boundary.last_principal.actor_class == "human"
    assert boundary.last_principal.assurance == "multi_factor"
    assert boundary.lock_calls == 1
    assert recheck.call_count == 2  # boundary freshness check + engine guard
    assert snapshot["base_commit"] == engine.config["base_commit"]
    assert snapshot["candidate_id"] == view["candidate"]["candidate_id"]

    after = _counts(engine)
    assert after == {
        **before,
        "grants": before["grants"] + 1,
        "grant_events": before["grant_events"] + 1,
        "events": before["events"] + 1,
    }
    assert _statuses(engine) == baseline_statuses
    assert not set(baseline_statuses) & {"CREATED", "LAUNCH_INTENT", "RUNNING"}
    assert engine.view()["plan_granted"] is True
    assert engine.view()["active_jobs"] == []

    grant = engine.store.lookup_grant("tok-c06-integrated-1")
    assert grant is not None
    assert grant["data"]["issuer"] == SUBJECT
    assert grant["data"]["gate_id"] == snapshot["gate_id"]
    assert grant["data"]["plan_revision_hash"] == snapshot["plan_revision_hash"]
    assert grant["data"]["scope_hash"] == snapshot["scope_hash"]
    assert grant["data"]["roles_hash"] == snapshot["roles_hash"]
    assert grant["data"]["repository_id"] == snapshot["repository_id"]
    assert grant["data"]["branch"] == snapshot["branch"]

    replay, replay_outcome = boundary.decide(envelope, request)
    assert replay_outcome == "replayed"
    assert replay == receipt
    assert recheck.call_count == 2
    assert boundary.lock_calls == 1
    assert _counts(engine) == after
    for probe in probes:
        probe.assert_not_called()


def test_changed_content_same_key_conflicts_without_effect(c06_engine, monkeypatch):
    engine, view = c06_engine
    snapshot = _snapshot(engine, view)
    boundary = SyntheticDecisionBoundary(engine, _verifier(), snapshot)
    issuer = _issuer()
    request = _request(snapshot)
    envelope = _envelope(issuer, request, work_item_id=snapshot["work_item"], target_id=snapshot["work_item"])
    probes = _probes(engine, monkeypatch)
    boundary.decide(envelope, request)
    before = _counts(engine)

    changed = {**request, "request_note": "different content"}
    changed_env = _envelope(
        issuer,
        changed,
        jti="jti-c06-changed",
        work_item_id=snapshot["work_item"],
        target_id=snapshot["work_item"],
    )
    with pytest.raises(Denied) as error:
        boundary.decide(changed_env, changed)
    assert error.value.code == "conflict"
    assert _counts(engine) == before
    for probe in probes:
        probe.assert_not_called()


def test_changed_key_after_grant_is_rejected_without_second_grant(c06_engine, monkeypatch):
    engine, view = c06_engine
    snapshot = _snapshot(engine, view)
    boundary = SyntheticDecisionBoundary(engine, _verifier(), snapshot)
    issuer = _issuer()
    request = _request(snapshot)
    envelope = _envelope(issuer, request, work_item_id=snapshot["work_item"], target_id=snapshot["work_item"])
    probes = _probes(engine, monkeypatch)
    boundary.decide(envelope, request)
    before = _counts(engine)

    changed = {**request, "idempotency_key": "idem-c06-2"}
    changed_env = _envelope(
        issuer,
        changed,
        jti="jti-c06-key2",
        work_item_id=snapshot["work_item"],
        target_id=snapshot["work_item"],
    )
    with pytest.raises(Denied) as error:
        boundary.decide(changed_env, changed)
    assert error.value.code == "conflict"
    assert _counts(engine) == before
    for probe in probes:
        probe.assert_not_called()


@pytest.mark.parametrize("field", ["review_snapshot_id", "gate_id", "expected_revision"])
def test_stale_or_mismatched_review_binding_is_rejected(c06_engine, monkeypatch, field):
    engine, view = c06_engine
    snapshot = _snapshot(engine, view)
    boundary = SyntheticDecisionBoundary(engine, _verifier(), snapshot)
    request = _request(snapshot)
    request[field] = request[field] + 1 if field == "expected_revision" else "wrong-" + str(request[field])
    envelope = _envelope(
        _issuer(),
        request,
        work_item_id=snapshot["work_item"],
        target_id=snapshot["work_item"],
    )
    probes = _probes(engine, monkeypatch)
    before = _counts(engine)

    with pytest.raises(Denied) as error:
        boundary.decide(envelope, request)
    assert error.value.code == "conflict"
    assert _counts(engine) == before
    assert boundary.last_token is None
    for probe in probes:
        probe.assert_not_called()


def test_forged_principal_is_rejected_without_effect(c06_engine, monkeypatch):
    engine, view = c06_engine
    snapshot = _snapshot(engine, view)
    boundary = SyntheticDecisionBoundary(engine, _verifier(), snapshot)
    request = _request(snapshot)
    envelope = _envelope(
        _issuer(), request, work_item_id=snapshot["work_item"], target_id=snapshot["work_item"]
    )
    envelope["claims"]["subject"] = "forged-owner"
    probes = _probes(engine, monkeypatch)
    before = _counts(engine)

    with pytest.raises(Denied) as error:
        boundary.decide(envelope, request)
    assert error.value.code == "unauthenticated"
    assert _counts(engine) == before
    for probe in probes:
        probe.assert_not_called()


def test_agent_principal_cannot_decision(c06_engine, monkeypatch):
    engine, view = c06_engine
    snapshot = _snapshot(engine, view)
    boundary = SyntheticDecisionBoundary(engine, _verifier(), snapshot)
    request = _request(snapshot)
    envelope = _envelope(
        _issuer(),
        request,
        actor_class="agent",
        capabilities=("read", "decide"),
        work_item_id=snapshot["work_item"],
        target_id=snapshot["work_item"],
    )
    probes = _probes(engine, monkeypatch)
    before = _counts(engine)

    with pytest.raises(Denied) as error:
        boundary.decide(envelope, request)
    assert error.value.code == "forbidden"
    assert _counts(engine) == before
    for probe in probes:
        probe.assert_not_called()


def test_source_drift_after_snapshot_is_rejected_by_boundary(c06_engine, monkeypatch):
    """Git-only candidate recheck detects changed review-bound source."""
    engine, view = c06_engine
    snapshot = _snapshot(engine, view)
    boundary = SyntheticDecisionBoundary(engine, _verifier(), snapshot)
    request = _request(snapshot)
    envelope = _envelope(
        _issuer(), request, work_item_id=snapshot["work_item"], target_id=snapshot["work_item"]
    )
    probes = _probes(engine, monkeypatch)
    recheck = Mock(wraps=engine._recheck_candidate)
    monkeypatch.setattr(engine, "_recheck_candidate", recheck)
    before = _counts(engine)

    # Allowed source file changes after the review snapshot was taken.
    (engine.root / "old").write_text("drifted after review")

    with pytest.raises(Denied) as error:
        boundary.decide(envelope, request)
    assert error.value.code == "conflict"
    assert "Source freshness" in str(error.value.body.get("message", ""))
    assert boundary.last_token is None
    assert boundary.lock_calls == 1
    assert recheck.call_count == 1
    assert _counts(engine) == before
    for probe in probes:
        probe.assert_not_called()


def test_grant_and_synchronize_rejects_source_drift_before_grant(c06_engine, monkeypatch):
    """The real primitive now rechecks the reviewed candidate before grant."""
    engine, view = c06_engine
    snapshot = _snapshot(engine, view)
    token = _plan_token(snapshot)
    recheck = Mock(wraps=engine._recheck_candidate)
    monkeypatch.setattr(engine, "_recheck_candidate", recheck)
    probes = _probes(engine, monkeypatch)
    before = _counts(engine)

    (engine.root / "old").write_text("drifted after review")

    with pytest.raises(WorkflowError):
        with execution_lock(engine.runtime / "execution.lock"):
            engine.grant_and_synchronize(token)

    assert recheck.call_count == 1
    assert _counts(engine) == before
    for probe in probes:
        probe.assert_not_called()


def test_grant_and_synchronize_rejects_plan_artifact_drift_before_grant(c06_engine, monkeypatch):
    """Plan bytes are re-hashed through the authoritative stored plan path."""
    engine, view = c06_engine
    snapshot = _snapshot(engine, view)
    token = _plan_token(snapshot)

    # Put the plan under the generated runtime directory so the candidate recheck
    # passes, isolating the plan artifact/hash guard. This is test setup only;
    # the token still carries the original approved hash.
    source_plan = (engine.root / engine.config["plan_path"]).read_bytes()
    plan_copy = engine.runtime / "approval-plan.md"
    plan_copy.write_bytes(source_plan)
    engine.store.set_meta("plan_artifact", str(plan_copy.relative_to(engine.root)))
    plan_copy.write_text("drifted plan after review")

    recheck = Mock(wraps=engine._recheck_candidate)
    monkeypatch.setattr(engine, "_recheck_candidate", recheck)
    probes = _probes(engine, monkeypatch)
    before = _counts(engine)

    with pytest.raises(WorkflowError, match="Approved plan artifact drift before approval"):
        with execution_lock(engine.runtime / "execution.lock"):
            engine.grant_and_synchronize(token)

    assert recheck.call_count == 1
    assert _counts(engine) == before
    for probe in probes:
        probe.assert_not_called()


def _marker_script(path: Path, sentinel: Path) -> None:
    path.write_text(f'#!/bin/sh\necho ran >> "{sentinel}"\nexit 0\n')
    path.chmod(0o755)


def test_candidates_changed_ignores_git_external_process_settings(tmp_path, monkeypatch):
    repo = tmp_path / "git-config-repo"
    repo.mkdir()
    candidates_module.git(repo, "init", "-b", "main")
    candidates_module.git(repo, "config", "user.email", "test@example.invalid")
    candidates_module.git(repo, "config", "user.name", "Synthetic Test")
    (repo / "a.txt").write_text("original")
    (repo / ".gitattributes").write_text("*.txt diff=marker\n")
    candidates_module.git(repo, "add", ".")
    candidates_module.git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-m", "init")
    base = candidates_module.git(repo, "rev-parse", "HEAD").decode().strip()

    fs_sentinel = tmp_path / "fsmonitor.sentinel"
    ext_sentinel = tmp_path / "external.sentinel"
    text_sentinel = tmp_path / "textconv.sentinel"
    command_sentinel = tmp_path / "diff-command.sentinel"
    fs_hook = tmp_path / "fsmonitor.sh"
    ext_hook = tmp_path / "external.sh"
    text_hook = tmp_path / "textconv.sh"
    command_hook = tmp_path / "diff-command.sh"
    for hook, sentinel in (
        (fs_hook, fs_sentinel),
        (ext_hook, ext_sentinel),
        (text_hook, text_sentinel),
        (command_hook, command_sentinel),
    ):
        _marker_script(hook, sentinel)

    candidates_module.git(repo, "config", "core.fsmonitor", str(fs_hook))
    candidates_module.git(repo, "config", "diff.external", str(ext_hook))
    candidates_module.git(repo, "config", "diff.marker.textconv", str(text_hook))
    candidates_module.git(repo, "config", "diff.marker.command", str(command_hook))
    monkeypatch.setenv("GIT_EXTERNAL_DIFF", str(ext_hook))

    (repo / "a.txt").write_text("changed")

    real_run = candidates_module.subprocess.run
    calls = []

    def capture(cmd, *args, **kwargs):
        calls.append(list(cmd))
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(candidates_module.subprocess, "run", capture)
    result = candidates_module.changed(repo, base)

    assert result == ["a.txt"]
    for sentinel in (fs_sentinel, ext_sentinel, text_sentinel, command_sentinel):
        assert not sentinel.exists()

    assert calls
    for cmd in calls:
        assert cmd[:3] == ["git", "-C", str(repo)]
        assert cmd[3:5] == ["-c", "core.fsmonitor=false"]
    assert [cmd[5] for cmd in calls] == ["diff", "ls-files"]
    for cmd in calls:
        if cmd[5] == "diff":
            assert "--no-ext-diff" in cmd
            assert "--no-textconv" in cmd


def _install_fsmonitor(engine: Engine, tmp_path: Path) -> Path:
    sentinel = tmp_path / "fsmonitor-approval.sentinel"
    hook = tmp_path / "fsmonitor-approval.sh"
    _marker_script(hook, sentinel)
    candidates_module.git(engine.root, "config", "core.fsmonitor", str(hook))
    return sentinel


def test_approval_recheck_valid_path_does_not_run_fsmonitor(c06_engine, tmp_path):
    engine, view = c06_engine
    snapshot = _snapshot(engine, view)
    token = _plan_token(snapshot)
    sentinel = _install_fsmonitor(engine, tmp_path)

    with execution_lock(engine.runtime / "execution.lock"):
        after = engine.grant_and_synchronize(token)

    assert after["plan_granted"] is True
    assert not sentinel.exists()
    assert _counts(engine)["grants"] == 1


def test_approval_recheck_stale_path_does_not_run_fsmonitor(c06_engine, tmp_path):
    engine, view = c06_engine
    snapshot = _snapshot(engine, view)
    token = _plan_token(snapshot)
    sentinel = _install_fsmonitor(engine, tmp_path)
    before = _counts(engine)

    (engine.root / "old").write_text("drifted with fsmonitor configured")

    with pytest.raises(WorkflowError):
        with execution_lock(engine.runtime / "execution.lock"):
            engine.grant_and_synchronize(token)

    assert not sentinel.exists()
    assert _counts(engine) == before
