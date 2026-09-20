"""Regression evidence for the independent native Phase 1 review's four P1s."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import engine as engine_module
import pytest
from core import WorkflowError, utc
from engine import Engine
from test_engine import Stub, plan_token


def test_commit_scope_cannot_authorize_plan_gate(configured):
    root, config = configured
    e = Engine(root, launcher=Stub())
    e.initialize(config)
    v = e.run()
    token = dict(
        schema_version=1,
        token_id="scope-confusion",
        gate_id=v["gate"]["gate_id"],
        work_item=v["work_item"],
        issuer="owner",
        issued_utc=utc(),
        status="ISSUED",
        scope="COMMIT",
        candidate_id=v["candidate"]["candidate_id"],
        manifest_hash=v["candidate"]["manifest_hash"],
        repository_id=str(root),
        branch=config["branch"],
        expected_parent_sha=config["base_commit"],
        expected_tree_oid=v["candidate"]["tree_oid"],
        job_id="owner-commit",
    )
    count = len(e.store.events())
    with pytest.raises(WorkflowError, match="pending gate"):
        e.approve(token)
    assert len(e.store.events()) == count
    assert e.store.grant_for(v["gate"]["gate_id"]) is None
    assert e.view()["gate"]["scope"] == "PLAN"
    e.close()


@pytest.mark.parametrize("artifact", ["packet.md", "spec.json", "wire-schema.json"])
def test_crash_during_preparation_recovers_original_inputs(configured, monkeypatch, artifact):
    root, config = configured
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    e.initialize(config)
    original_write = engine_module.atomic_write
    original_json = engine_module.write_json
    captured = []

    def fail_write(path, content, immutable=False):
        original_write(path, content, immutable)
        if Path(path).name == artifact:
            captured.append(Path(path).read_bytes())
            raise RuntimeError("simulated coordinator crash after artifact write")

    def fail_json(path, content, immutable=False):
        original_json(path, content, immutable)
        if Path(path).name == artifact:
            captured.append(Path(path).read_bytes())
            raise RuntimeError("simulated coordinator crash after artifact write")

    with monkeypatch.context() as patch:
        patch.setattr(engine_module, "atomic_write", fail_write)
        patch.setattr(engine_module, "write_json", fail_json)
        with pytest.raises(RuntimeError, match="simulated"):
            e.run()
    assert not stub.starts
    e.close()
    e = Engine(root, launcher=stub)
    v = e.run()
    job = e.store.job(v["active_jobs"][0])
    path = (
        root / "docs/ai/work-items/test-work/runs" / job["job_id"] / "inputs/packet.md"
        if artifact == "packet.md"
        else Path(job["runtime"]) / artifact
    )
    assert path.read_bytes() == captured[0]
    assert len(stub.starts) == 1
    e.close()


@pytest.mark.parametrize("change", ["pause", "candidate", "plan"])
def test_resume_pending_dispatch_revalidates_before_launch(configured, change):
    root, config = configured
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    e.initialize(config)
    prepared = e._prepare({"view": e.view()})
    e.graph.update_state(e.graph_config, prepared, as_node="prepare")
    assert e.graph.get_state(e.graph_config).next == ("dispatch",)
    e.close()
    e = Engine(root, launcher=stub)
    if change == "pause":
        e.store.event("owner-pause", "pause", {"reason": "OWNER:inspection"})
        assert e.run()["status"] == "PAUSED"
    else:
        (root / ("old" if change == "candidate" else "plan.md")).write_text("changed before resume")
        with pytest.raises(WorkflowError):
            e.run()
    assert not stub.starts
    assert all(e.store.job(j)["status"] == "CREATED" for j in prepared["view"]["active_jobs"])
    e.close()


def test_owner_pause_enters_during_normal_cli_monitor(configured, tmp_path):
    root, config = configured
    e = Engine(root, launcher=Stub(delayed=True))
    e.initialize(config)
    e.close()
    driver = tmp_path / "cli_fixture.py"
    driver.write_text("""import cli
from engine import Engine
from test_engine import Stub, plan_token
cli.Engine=lambda root:Engine(root,launcher=Stub(delayed=True))
cli.doctor=lambda root:{'ok':True}
raise SystemExit(cli.main())
""")
    env = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join(
            [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
        ),
    )
    argv = [sys.executable, str(driver), "--root", str(root)]
    monitor = subprocess.Popen(
        [*argv, "run"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        deadline = time.monotonic() + 10
        state_file = root / "docs/ai/work-items/test-work/STATE.json"
        while time.monotonic() < deadline:
            if monitor.poll() is not None:
                pytest.fail(monitor.communicate()[1])
            # Export schema does not expose active jobs; SQLite read gives the observation.
            e = Engine(root, launcher=Stub(delayed=True))
            active = e.view()["active_jobs"]
            e.close()
            if active:
                break
            time.sleep(0.05)
        assert active and state_file.exists()
        paused = subprocess.run(
            [*argv, "pause", "--reason", "inspection"], env=env, capture_output=True, text=True, timeout=10
        )
        assert paused.returncode == 0, paused.stdout + paused.stderr
        assert json.loads(paused.stdout)["status"] == "PAUSED"
        output, error = monitor.communicate(timeout=10)
        assert monitor.returncode == 0, error
        assert json.loads(output)["status"] == "PAUSED"
    finally:
        if monitor.poll() is None:
            monitor.kill()
            monitor.wait()


def test_approval_after_uncheckpointed_pause_does_not_poison_replay(configured):
    root, config = configured
    e = Engine(root, launcher=Stub())
    e.initialize(config)
    e.run()
    stale = plan_token(e)
    e.store.event("pause-before-crash", "pause", {"reason": "OWNER:inspection"})
    e.close()  # crash boundary: event durable, checkpoint still PLAN_SUBMITTED
    e = Engine(root, launcher=Stub())
    count = len(e.store.events())
    with pytest.raises(WorkflowError, match="pending gate"):
        e.approve(stale)
    assert len(e.store.events()) == count
    assert e.store.grant_for(stale["gate_id"]) is None
    assert e.view()["status"] == "PAUSED"
    e.close()
    e = Engine(root, launcher=Stub())
    assert e.run()["status"] == "PAUSED"
    assert e.owner_decision("resume", {"reason": "inspection complete"})["gate"]["scope"] == "PLAN"
    e.close()


def test_invalid_resume_is_rejected_before_event_storage(configured):
    root, config = configured
    e = Engine(root, launcher=Stub())
    e.initialize(config)
    with pytest.raises(WorkflowError, match="Cannot resume"):
        e.owner_decision("resume", {"reason": "invalid before pause"})
    assert e.store.events() == []
    assert e.run()["gate"]["scope"] == "PLAN"
    e.close()
