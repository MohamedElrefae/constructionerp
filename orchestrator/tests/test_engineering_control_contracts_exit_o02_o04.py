"""Offline O02 recovery / O04 writer-boundary proof.

The tests use disposable Git/SQLite engine fixtures and real independent
processes. They do not open a live workflow database, start a listener, launch a
worker or expose a route.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from core import WorkflowError, execution_lock
from engine import Engine
from engineering_control_contracts.operation_store import (
    OperationConflict,
    OperationFenced,
    OperationStore,
    digest,
)
from test_engine import Stub, plan_token

REPO_ROOT = Path(__file__).resolve().parents[2]


def _prepare_plan_gate(configured):
    root, config = configured
    engine = Engine(root, launcher=Stub())
    try:
        engine.initialize(config)
        view = engine.run()
        assert view["gate"] and view["gate"]["scope"] == "PLAN"
        token = plan_token(engine)
        jobs = engine.store.conn.execute("SELECT COUNT(*) FROM workflow_jobs").fetchone()[0]
        events = engine.store.conn.execute(
            "SELECT COUNT(*) FROM workflow_events WHERE kind='grant'"
        ).fetchone()[0]
    finally:
        engine.close()
    return root, token, jobs, events


def _run_python(code: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


def _commit_script() -> str:
    return r"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("orchestrator").resolve()))
from core import execution_lock
from engine import Engine

root = Path(sys.argv[1])
token = json.loads(sys.argv[2])
with execution_lock(root / "orchestrator/var/execution.lock"):
    engine = Engine(root)
    try:
        engine.grant_and_synchronize(token)
    finally:
        engine.close()
print("COMMITTED")
"""


def _preflight_reject_script() -> str:
    return r"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path("orchestrator").resolve()))
from langgraph.checkpoint.sqlite import SqliteSaver

root = Path(sys.argv[1])
token = json.loads(sys.argv[2])
marker = Path(sys.argv[3])
db = root / "orchestrator/var/checkpoints.db"
conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
try:
    checkpoint = SqliteSaver(conn).get({"configurable": {"thread_id": "workflow"}})
    view = checkpoint["channel_values"]["view"]
finally:
    conn.close()
if token["gate_id"] != view["gate"]["gate_id"] or token["work_item"] != view["work_item"]:
    marker.write_text("PRE_EFFECT_REJECTED")
    print("PRE_EFFECT_REJECTED")
    raise SystemExit(1)
raise SystemExit("preflight unexpectedly accepted the token")
"""


def _evidence(root: Path, token_id: str) -> dict:
    db_path = root / "orchestrator/var/checkpoints.db"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        grant = conn.execute(
            "SELECT status, data FROM workflow_grants WHERE token_id=?", (token_id,)
        ).fetchone()
        events = conn.execute("SELECT payload FROM workflow_events WHERE kind='grant'").fetchall()
        matching = [row for row in events if json.loads(row[0]).get("token_id") == token_id]
        jobs = conn.execute("SELECT COUNT(*) FROM workflow_jobs").fetchone()[0]
    finally:
        conn.close()
    return {
        "grant": dict(status=grant[0], data=json.loads(grant[1])) if grant else None,
        "events": [json.loads(row[0]) for row in matching],
        "jobs": jobs,
    }


def _reconcile_from_evidence(
    store: OperationStore,
    operation_id: str,
    epoch: int,
    root: Path,
    expected_token: dict,
    *,
    expected_body: dict,
    writer_terminated: bool = True,
    pre_effect_failure: bool = False,
):
    """Reconcile only from fenced writer + full binding + durable effect evidence.

    ``writer_terminated`` and ``pre_effect_failure`` are caller-supplied test
    inputs, not verified production provenance. The proof only shows the
    fail-closed decision logic; it does not prove that a process is dead or that
    an effect was pre-effect in a real deployment.
    """
    operation = store.get(operation_id)
    if not writer_terminated:
        raise RuntimeError("Writer termination is not verified")
    if store.current_epoch() != epoch or epoch <= operation.writer_epoch:
        raise RuntimeError("Writer fencing is not verified")
    if operation.operation != "decisions" or operation.work_item_id != expected_token["work_item"]:
        raise RuntimeError("Journal operation/work-item binding mismatch")
    if operation.target_id != expected_token["work_item"]:
        raise RuntimeError("Journal target binding mismatch")
    if operation.request_hash != digest(expected_body):
        raise RuntimeError("Journal request hash does not bind the expected body")
    body_token = expected_body.get("token")
    if body_token != expected_token:
        raise RuntimeError("Journal body token does not match the expected token")
    if expected_body.get("action_id") != operation.operation_id:
        raise RuntimeError("Journal body action does not match the operation ID")

    token_id = expected_token["token_id"]
    evidence = _evidence(root, token_id)
    if evidence["grant"] is not None and evidence["events"]:
        if len(evidence["events"]) != 1:
            raise RuntimeError("Conflicting duplicate grant events")
        if evidence["grant"]["status"] != "CONSUMED":
            raise RuntimeError("Grant is not durably consumed")
        if evidence["grant"]["data"] != expected_token:
            raise RuntimeError("Grant data does not match the expected token")
        if evidence["events"][0] != expected_token:
            raise RuntimeError("Grant event does not match the expected token")
        return store.reconcile(
            operation_id,
            epoch=epoch,
            outcome="completed",
            receipt={
                "token_id": token_id,
                "gate_id": expected_token["gate_id"],
                "action_id": operation_id,
            },
            evidence_ref="grant-" + token_id,
        )
    if evidence["grant"] is None and not evidence["events"]:
        if not pre_effect_failure:
            raise RuntimeError("No durable effect and no verified pre-effect failure")
        return store.reconcile(
            operation_id,
            epoch=epoch,
            outcome="failed",
            evidence_ref="pre-effect-failure",
        )
    raise RuntimeError("Conflicting or partial durable effect evidence")


def _store(tmp_path: Path) -> OperationStore:
    return OperationStore(tmp_path / "o02.db")


def _begin(
    store: OperationStore,
    epoch: int,
    *,
    work_item: str = "test-work",
    operation_id: str = "op-o02",
    body: dict | None = None,
):
    return store.begin(
        epoch=epoch,
        subject="owner",
        project_id="project-o02",
        work_item_id=work_item,
        operation="decisions",
        target_id=work_item,
        idempotency_key="approve-plan-1",
        body=body if body is not None else {"decision": "approve_plan"},
        expected_revision=0,
        current_revision=0,
        operation_id=operation_id,
    )


def test_lost_response_after_commit_reconciles_from_durable_evidence(configured, tmp_path):
    root, token, baseline_jobs, baseline_grant_events = _prepare_plan_gate(configured)
    store = _store(tmp_path)
    epoch = store.claim_writer("writer-a")
    body = {"decision": "approve_plan", "token": token, "action_id": "op-o02"}
    _begin(store, epoch, body=body)

    proc = _run_python(_commit_script(), str(root), json.dumps(token))
    assert proc.returncode == 0, proc.stderr
    assert "COMMITTED" in proc.stdout

    # The writer's response was lost; no journal completion was recorded.
    recovered_store = _store(tmp_path)
    new_epoch = recovered_store.claim_writer("writer-b")
    recovered = recovered_store.recover(epoch=new_epoch)
    assert [op.state for op in recovered] == ["uncertain"]

    evidence = _evidence(root, token["token_id"])
    assert evidence["grant"] is not None
    assert len(evidence["events"]) == 1
    assert evidence["jobs"] == baseline_jobs
    assert baseline_grant_events == 0

    op = _reconcile_from_evidence(
        recovered_store,
        "op-o02",
        new_epoch,
        root,
        token,
        expected_body=body,
        writer_terminated=proc.returncode is not None,
    )
    assert op.state == "completed"
    assert op.effect_state == "completed"
    assert op.evidence_ref == "grant-" + token["token_id"]
    assert op.receipt["token_id"] == token["token_id"]

    # Reconciliation is one-shot and does not create a second grant or job.
    with pytest.raises(OperationConflict):
        recovered_store.reconcile(
            "op-o02",
            epoch=new_epoch,
            outcome="completed",
            receipt={"token_id": token["token_id"]},
            evidence_ref="grant-again",
        )
    assert _evidence(root, token["token_id"])["jobs"] == baseline_jobs
    assert len(_evidence(root, token["token_id"])["events"]) == 1


def test_no_effect_is_reconciled_only_from_absent_durable_evidence(configured, tmp_path):
    root, token, baseline_jobs, baseline_events = _prepare_plan_gate(configured)
    bad_token = dict(token)
    bad_token["gate_id"] = "gate-wrong"
    body = {"decision": "approve_plan", "token": bad_token, "action_id": "op-o02"}
    store = _store(tmp_path)
    epoch = store.claim_writer("writer-a")
    _begin(store, epoch, body=body)
    marker = tmp_path / "pre-effect-rejected"

    proc = _run_python(_preflight_reject_script(), str(root), json.dumps(bad_token), str(marker))
    assert proc.returncode != 0
    assert marker.read_text() == "PRE_EFFECT_REJECTED"

    recovered_store = _store(tmp_path)
    new_epoch = recovered_store.claim_writer("writer-b")
    recovered_store.recover(epoch=new_epoch)
    evidence = _evidence(root, token["token_id"])
    assert evidence["grant"] is None
    assert evidence["events"] == []
    assert evidence["jobs"] == baseline_jobs

    op = _reconcile_from_evidence(
        recovered_store,
        "op-o02",
        new_epoch,
        root,
        bad_token,
        expected_body=body,
        writer_terminated=proc.returncode is not None,
        pre_effect_failure=marker.exists(),
    )
    assert op.state == "failed"
    assert op.effect_state == "failed"
    assert op.receipt is None
    assert _evidence(root, token["token_id"])["jobs"] == baseline_jobs
    assert baseline_events == 0


def test_partial_effect_evidence_stays_uncertain(configured, tmp_path):
    root, token, baseline_jobs, _ = _prepare_plan_gate(configured)
    store = _store(tmp_path)
    epoch = store.claim_writer("writer-a")
    body = {"decision": "approve_plan", "token": token, "action_id": "op-o02"}
    _begin(store, epoch, body=body)

    proc = _run_python(_commit_script(), str(root), json.dumps(token))
    assert proc.returncode == 0, proc.stderr

    # Simulate a partial cross-store effect in the disposable fixture.
    db_path = root / "orchestrator/var/checkpoints.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM workflow_grants WHERE token_id=?", (token["token_id"],))
        conn.commit()
    finally:
        conn.close()

    recovered_store = _store(tmp_path)
    new_epoch = recovered_store.claim_writer("writer-b")
    recovered_store.recover(epoch=new_epoch)
    with pytest.raises(RuntimeError, match="Conflicting or partial"):
        _reconcile_from_evidence(
            recovered_store,
            "op-o02",
            new_epoch,
            root,
            token,
            expected_body=body,
            writer_terminated=proc.returncode is not None,
        )
    row = recovered_store.get("op-o02")
    assert row.state == "uncertain"
    assert row.evidence_ref is None
    assert _evidence(root, token["token_id"])["jobs"] == baseline_jobs


def test_operation_store_binds_work_item_and_rejects_stale_writer(tmp_path):
    store = _store(tmp_path)
    epoch = store.claim_writer("writer-a")
    first = _begin(store, epoch, work_item="work-a", operation_id="op-a")
    second = _begin(store, epoch, work_item="work-b", operation_id="op-b")
    assert first.work_item_id == "work-a"
    assert second.work_item_id == "work-b"
    with pytest.raises(OperationConflict):
        store.begin(
            epoch=epoch,
            subject="owner",
            project_id="project-o02",
            work_item_id="work-a",
            operation="decisions",
            target_id="work-a",
            idempotency_key="approve-plan-1",
            body={"decision": "different"},
            expected_revision=0,
            current_revision=0,
            operation_id="op-a2",
        )

    new_epoch = store.claim_writer("writer-b")
    assert new_epoch == epoch + 1
    with pytest.raises(OperationFenced):
        store.complete("op-a", epoch=epoch, receipt={"token_id": "owner-plan"})


def test_execution_lock_is_advisory_and_releases_after_process_exit(tmp_path):
    lock_path = tmp_path / "execution.lock"
    holder = r"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path("orchestrator").resolve()))
from core import execution_lock
with execution_lock(Path(sys.argv[1])):
    print("LOCKED", flush=True)
    time.sleep(30)
"""
    proc = subprocess.Popen(
        [sys.executable, "-c", holder, str(lock_path)],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout.readline().strip() == "LOCKED"
        with pytest.raises(WorkflowError, match="Another workflow writer"):
            with execution_lock(lock_path, timeout=0.2):
                pass
        proc.kill()
        proc.wait(timeout=5)
        with execution_lock(lock_path, timeout=2):
            pass
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_crashed_owner_process_leaves_uncertain_intent_and_new_epoch(tmp_path):
    store_path = tmp_path / "crash.db"
    script = r"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path("orchestrator").resolve()))
from engineering_control_contracts.operation_store import OperationStore

store = OperationStore(sys.argv[1])
epoch = store.claim_writer("crashed-writer")
store.begin(
    epoch=epoch,
    subject="owner",
    project_id="project-o02",
    work_item_id="test-work",
    operation="decisions",
    target_id="test-work",
    idempotency_key="crash-key",
    body={"decision": "approve_plan"},
    expected_revision=0,
    current_revision=0,
    operation_id="op-crash",
)
print("CLAIMED", flush=True)
os._exit(0)
"""
    proc = _run_python(script, str(store_path))
    assert proc.returncode == 0, proc.stderr
    assert "CLAIMED" in proc.stdout

    store = OperationStore(store_path)
    assert store.current_epoch() == 1
    new_epoch = store.claim_writer("recovery-writer")
    assert new_epoch == 2
    recovered = store.recover(epoch=new_epoch)
    assert [op.operation_id for op in recovered] == ["op-crash"]
    assert recovered[0].state == "uncertain"
    with pytest.raises(OperationFenced):
        store.complete("op-crash", epoch=1, receipt={"token_id": "owner-plan"})


def test_competing_process_writers_same_key_have_one_intent(tmp_path):
    store_path = tmp_path / "race.db"
    go_path = tmp_path / "go"
    store = OperationStore(store_path)
    epoch = store.claim_writer("writer-parent")
    script = r"""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path("orchestrator").resolve()))
from engineering_control_contracts.operation_store import (
    OperationConflict,
    OperationStore,
)

store = OperationStore(sys.argv[1])
go = Path(sys.argv[2])
while not go.exists():
    time.sleep(0.01)
try:
    op = store.begin(
        epoch=int(sys.argv[4]),
        subject="owner",
        project_id="project-o02",
        work_item_id="test-work",
        operation="decisions",
        target_id="test-work",
        idempotency_key="race-key",
        body={"decision": sys.argv[3]},
        expected_revision=0,
        current_revision=0,
        operation_id="op-race-" + sys.argv[3],
    )
except OperationConflict:
    print("CONFLICT", flush=True)
else:
    print("CREATED:" + op.operation_id, flush=True)
"""
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(store_path), str(go_path), body, str(epoch)],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for body in ("approve-a", "approve-b")
    ]
    try:
        go_path.write_text("go")
        outputs = [proc.communicate(timeout=10)[0].strip() for proc in procs]
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
    assert sum(output.startswith("CREATED:") for output in outputs) == 1
    assert sum(output == "CONFLICT" for output in outputs) == 1
    conn = sqlite3.connect(store_path)
    try:
        rows = conn.execute("SELECT COUNT(*) FROM operations").fetchone()[0]
    finally:
        conn.close()
    assert rows == 1


def _read_view(root: Path) -> dict:
    """Read the LangGraph view through a read-only SQLite connection (no Engine)."""
    db_path = root / "orchestrator/var/checkpoints.db"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        checkpoint = SqliteSaver(conn).get({"configurable": {"thread_id": "workflow"}})
        return dict(checkpoint["channel_values"]["view"])
    finally:
        conn.close()


def _read_config(root: Path) -> dict:
    db_path = root / "orchestrator/var/checkpoints.db"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM workflow_meta WHERE key='config'").fetchone()
        return json.loads(row[0])
    finally:
        conn.close()


def _role_cut_fixture(configured):
    root, config = configured
    engine = Engine(root, launcher=Stub())
    engine.initialize(config)
    engine.run()
    with execution_lock(engine.runtime / "execution.lock"):
        engine.grant_and_synchronize(plan_token(engine))
    engine.store.event("pause-role-cut", "pause", {"reason": "OWNER:role-cut"})
    view = engine.run()
    assert view["status"] == "PAUSED"
    engine.store.grant(
        {
            "token_id": "pending-role-cut",
            "gate_id": "pending-role-cut",
            "scope": "PLAN",
            "status": "ISSUED",
        }
    )
    return engine, root, _read_view(root), (root / "orchestrator/roles.json").read_bytes()


def _cut_role(engine, view: dict, action_id: str, *, request_hash: str):
    with execution_lock(engine.runtime / "execution.lock"):
        return engine.reconfigure_role_paused(
            role="reviewer",
            tool="opencode",
            model="opencode-go/deepseek-v4.1-flash",
            reason="Owner role cut",
            expected_revision=view["revision"],
            action_id=action_id,
            request_hash=request_hash,
        )


@pytest.mark.xfail(
    not hasattr(Engine, "reconfigure_role_paused"),
    strict=True,
    raises=AttributeError,
    reason="Legacy WP1 role-cut API absent; compatibility remains unresolved",
)
def test_reconfigure_cut_before_mirror_leaves_sqlite_atomic_effect_only(configured, monkeypatch):
    engine, root, before, roles_before = _role_cut_fixture(configured)
    try:

        def fail_mirror():
            raise WorkflowError("synthetic cut before roles mirror")

        monkeypatch.setattr(engine, "sync_roles_mirror", fail_mirror)
        with pytest.raises(WorkflowError, match="synthetic cut"):
            _cut_role(engine, before, "act-cut-mirror", request_hash="e" * 64)
    finally:
        engine.close()

    config = _read_config(root)
    assert config["roles"]["reviewer"]["model"] == "opencode-go/deepseek-v4.1-flash"
    conn = sqlite3.connect(root / "orchestrator/var/checkpoints.db")
    try:
        status = conn.execute(
            "SELECT status FROM workflow_grants WHERE token_id='pending-role-cut'"
        ).fetchone()[0]
        events = conn.execute("SELECT payload FROM workflow_events WHERE kind='role_reconfigured'").fetchall()
    finally:
        conn.close()
    assert status == "INVALIDATED"
    assert len(events) == 1
    assert json.loads(events[0][0])["action_id"] == "act-cut-mirror"
    assert (root / "orchestrator/roles.json").read_bytes() == roles_before
    assert _read_view(root)["plan_granted"] is True


@pytest.mark.xfail(
    not hasattr(Engine, "reconfigure_role_paused"),
    strict=True,
    raises=AttributeError,
    reason="Legacy WP1 role-cut API absent; compatibility remains unresolved",
)
def test_reconfigure_cut_after_mirror_before_checkpoint_leaves_checkpoint_old(configured, monkeypatch):
    engine, root, before, roles_before = _role_cut_fixture(configured)
    try:

        def fail_checkpoint():
            raise WorkflowError("synthetic cut before checkpoint")

        monkeypatch.setattr(engine, "_synchronize_checkpoint", fail_checkpoint)
        with pytest.raises(WorkflowError, match="synthetic cut"):
            _cut_role(engine, before, "act-cut-checkpoint", request_hash="f" * 64)
    finally:
        engine.close()

    assert _read_config(root)["roles"]["reviewer"]["model"] == "opencode-go/deepseek-v4.1-flash"
    assert (root / "orchestrator/roles.json").read_bytes() != roles_before
    assert _read_view(root)["plan_granted"] is True


@pytest.mark.xfail(
    not hasattr(Engine, "reconfigure_role_paused"),
    strict=True,
    raises=AttributeError,
    reason="Legacy WP1 role-cut API absent; compatibility remains unresolved",
)
def test_reconfigure_full_cut_updates_config_mirror_checkpoint_and_invalidates_grant(configured):
    engine, root, before, roles_before = _role_cut_fixture(configured)
    try:
        after = _cut_role(engine, before, "act-cut-full", request_hash="a" * 64)
        assert after["plan_granted"] is False
        assert after["prior"]["gate"]["scope"] == "PLAN"
    finally:
        engine.close()

    assert _read_config(root)["roles"]["reviewer"]["model"] == "opencode-go/deepseek-v4.1-flash"
    assert (root / "orchestrator/roles.json").read_bytes() != roles_before
    assert _read_view(root)["plan_granted"] is False
    conn = sqlite3.connect(root / "orchestrator/var/checkpoints.db")
    try:
        status = conn.execute(
            "SELECT status FROM workflow_grants WHERE token_id='pending-role-cut'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert status == "INVALIDATED"


def test_absent_evidence_without_pre_effect_failure_stays_uncertain(configured, tmp_path):
    root, token, _, _ = _prepare_plan_gate(configured)
    body = {"decision": "approve_plan", "token": token, "action_id": "op-o02"}
    store = _store(tmp_path)
    epoch = store.claim_writer("writer-a")
    _begin(store, epoch, body=body)

    recovered_store = _store(tmp_path)
    new_epoch = recovered_store.claim_writer("writer-b")
    recovered_store.recover(epoch=new_epoch)
    assert _evidence(root, token["token_id"])["grant"] is None
    with pytest.raises(RuntimeError, match="No durable effect"):
        _reconcile_from_evidence(
            recovered_store,
            "op-o02",
            new_epoch,
            root,
            token,
            expected_body=body,
            writer_terminated=True,
            pre_effect_failure=False,
        )
    row = recovered_store.get("op-o02")
    assert row.state == "uncertain"
    assert row.evidence_ref is None


def test_same_token_id_with_mismatched_grant_data_stays_uncertain(configured, tmp_path):
    root, token, baseline_jobs, _ = _prepare_plan_gate(configured)
    body = {"decision": "approve_plan", "token": token, "action_id": "op-o02"}
    store = _store(tmp_path)
    epoch = store.claim_writer("writer-a")
    _begin(store, epoch, body=body)

    proc = _run_python(_commit_script(), str(root), json.dumps(token))
    assert proc.returncode == 0, proc.stderr

    db_path = root / "orchestrator/var/checkpoints.db"
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT data FROM workflow_grants WHERE token_id=?", (token["token_id"],)
        ).fetchone()
        data = json.loads(row[0])
        data["gate_id"] = "different-gate"
        conn.execute(
            "UPDATE workflow_grants SET data=? WHERE token_id=?",
            (json.dumps(data), token["token_id"]),
        )
        conn.commit()
    finally:
        conn.close()

    recovered_store = _store(tmp_path)
    new_epoch = recovered_store.claim_writer("writer-b")
    recovered_store.recover(epoch=new_epoch)
    with pytest.raises(RuntimeError, match="Grant data does not match"):
        _reconcile_from_evidence(
            recovered_store,
            "op-o02",
            new_epoch,
            root,
            token,
            expected_body=body,
            writer_terminated=proc.returncode is not None,
        )
    row = recovered_store.get("op-o02")
    assert row.state == "uncertain"
    assert _evidence(root, token["token_id"])["jobs"] == baseline_jobs


def _uncertain_operation(tmp_path, body, *, operation_id="op-o02", work_item="test-work"):
    store = _store(tmp_path)
    epoch = store.claim_writer("writer-a")
    _begin(store, epoch, work_item=work_item, operation_id=operation_id, body=body)
    recovered = _store(tmp_path)
    new_epoch = recovered.claim_writer("writer-b")
    recovered.recover(epoch=new_epoch)
    return recovered, new_epoch


def test_journal_body_token_substitution_is_rejected(configured, tmp_path):
    _, token, _, _ = _prepare_plan_gate(configured)
    body = {"decision": "approve_plan", "token": token, "action_id": "op-o02"}
    store, epoch = _uncertain_operation(tmp_path, body)
    substituted = dict(token)
    substituted["gate_id"] = "gate-b"
    with pytest.raises(RuntimeError, match="body token"):
        _reconcile_from_evidence(
            store, "op-o02", epoch, tmp_path, substituted, expected_body=body, writer_terminated=True
        )
    assert store.get("op-o02").state == "uncertain"


def test_journal_snapshot_content_substitution_is_rejected(configured, tmp_path):
    _, token, _, _ = _prepare_plan_gate(configured)
    body = {
        "decision": "approve_plan",
        "token": token,
        "action_id": "op-o02",
        "review_snapshot_id": "review-a",
    }
    store, epoch = _uncertain_operation(tmp_path, body)
    changed = {**body, "review_snapshot_id": "review-b"}
    with pytest.raises(RuntimeError, match="request hash"):
        _reconcile_from_evidence(
            store, "op-o02", epoch, tmp_path, token, expected_body=changed, writer_terminated=True
        )
    assert store.get("op-o02").state == "uncertain"


def test_journal_action_binding_mismatch_is_rejected(configured, tmp_path):
    _, token, _, _ = _prepare_plan_gate(configured)
    body = {"decision": "approve_plan", "token": token, "action_id": "op-o02"}
    store, epoch = _uncertain_operation(tmp_path, body, operation_id="op-other")
    with pytest.raises(RuntimeError, match="body action"):
        _reconcile_from_evidence(
            store, "op-other", epoch, tmp_path, token, expected_body=body, writer_terminated=True
        )
    assert store.get("op-other").state == "uncertain"


def test_journal_work_item_substitution_is_rejected(configured, tmp_path):
    _, token, _, _ = _prepare_plan_gate(configured)
    substituted_token = dict(token)
    substituted_token["work_item"] = "work-b"
    body = {
        "decision": "approve_plan",
        "token": substituted_token,
        "action_id": "op-o02",
    }
    store, epoch = _uncertain_operation(tmp_path, body, work_item="work-a")
    with pytest.raises(RuntimeError, match="work-item"):
        _reconcile_from_evidence(
            store,
            "op-o02",
            epoch,
            tmp_path,
            substituted_token,
            expected_body=body,
            writer_terminated=True,
        )
    assert store.get("op-o02").state == "uncertain"


def test_absence_with_unterminated_writer_stays_uncertain(configured, tmp_path):
    _, token, _, _ = _prepare_plan_gate(configured)
    body = {"decision": "approve_plan", "token": token, "action_id": "op-o02"}
    store, epoch = _uncertain_operation(tmp_path, body)
    with pytest.raises(RuntimeError, match="Writer termination"):
        _reconcile_from_evidence(
            store,
            "op-o02",
            epoch,
            tmp_path,
            token,
            expected_body=body,
            writer_terminated=False,
            pre_effect_failure=True,
        )
    assert store.get("op-o02").state == "uncertain"
