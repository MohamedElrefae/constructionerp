"""SYNTHETIC graph qualification: no providers, sites, or real pilot changes."""

import json
import shutil
from pathlib import Path

import pytest
from adapters import parse_output
from candidates import git
from core import WorkflowError, utc, write_json
from engine import Engine
from normalization import snapshot as normalize_snapshot
from test_engine import Stub, plan_token


def finding(kind="implementation_defect", summary="SYNTHETIC defect", identity=None, snapshot=None):
    return dict(
        schema_version=1,
        finding_id=identity,
        classification=kind,
        blocking=kind != "optional_improvement",
        summary=summary,
        affected_requirements=["R1"],
        evidence_refs=[],
        snapshot=snapshot,
    )


def job(e, role):
    matches = [e.store.job(j) for j in e.view()["active_jobs"] if e.store.job(j)["role"] == role]
    assert len(matches) == 1, e.view()
    return matches[0]


def complete(e, stub, role, plan=None, **outcome):
    j = job(e, role)
    stub.outcomes[role] = outcome
    stub.complete(j)
    if plan is not None:
        path = Path(j["runtime"]) / "stdout.jsonl"
        data = json.loads(path.read_text())
        data["wire"]["plan_text"] = plan
        path.write_text(json.dumps(data))
    return e.run()


def ready(configured, quorum=False):
    root, config = configured
    if quorum:
        config["quorum"] = ["ai-a1", "ai-a2", "ai-a3"]
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    e.initialize(config)
    e.run()
    complete(e, stub, "architect")
    complete(e, stub, "reviewer")
    e.approve(plan_token(e))
    return e, stub


def commit_token(e):
    v = e.view()
    c = v["candidate"]
    return dict(
        schema_version=1,
        token_id="SYNTHETIC-commit",
        work_item=v["work_item"],
        gate_id=v["gate"]["gate_id"],
        scope="COMMIT",
        issuer="SYNTHETIC-owner",
        issued_utc=utc(),
        status="ISSUED",
        candidate_id=c["candidate_id"],
        manifest_hash=c["manifest_hash"],
        repository_id=str(e.root),
        branch=e.config["branch"],
        expected_parent_sha=e.config["base_commit"],
        expected_tree_oid=c["tree_oid"],
        job_id="SYNTHETIC-commit-job",
    )


def test_repair_packet_all_findings_and_plan_grant_retention(configured):
    e, s = ready(configured)
    complete(e, s, "builder")
    v = complete(
        e,
        s,
        "verifier",
        verdict="BLOCKED",
        findings=[finding(summary="SYNTHETIC first"), finding(summary="SYNTHETIC second")],
    )
    ids = {f["finding_id"] for f in v["findings"]}
    packet = job(e, "builder")["spec"]["prompt"]
    assert len(ids) == 2 and all(i in packet for i in ids)
    assert v["plan_granted"] and len(e.store.conn.execute("SELECT * FROM workflow_grants").fetchall()) == 1
    (e.root / "old").write_text("SYNTHETIC code repair")
    old = v["candidate"]["candidate_id"]
    complete(e, s, "builder")
    assert e.view()["candidate"]["candidate_id"] != old
    v = complete(e, s, "verifier", verdict="PASS")
    assert v["status"] == "VERIFIED_FOR_RELEASE" and v["plan_granted"] and not v["findings"]
    assert len(e.store.conn.execute("SELECT * FROM workflow_grants").fetchall()) == 1
    e.close()


def test_design_returns_to_architecture_and_independent_plan_review(configured):
    e, s = ready(configured)
    complete(e, s, "builder")
    complete(e, s, "verifier", verdict="BLOCKED", findings=[finding("design_defect")])
    assert job(e, "architect")
    complete(e, s, "architect", plan="SYNTHETIC revised plan fixes the design")
    assert job(e, "reviewer")
    v = complete(e, s, "reviewer", verdict="PASS")
    assert v["gate"]["scope"] == "PLAN" and not v["plan_granted"]
    e.close()


@pytest.mark.parametrize(
    "kind,expected", [("optional_improvement", "VERIFIED_FOR_RELEASE"), ("owner_decision", "PAUSED")]
)
def test_optional_backlog_and_disagreement(configured, kind, expected):
    e, s = ready(configured)
    complete(e, s, "builder")
    v = complete(
        e,
        s,
        "verifier",
        verdict="PASS" if kind == "optional_improvement" else "BLOCKED",
        findings=[finding(kind)],
    )
    assert v["status"] == expected
    if kind == "optional_improvement":
        assert len(v["backlog"]) == 1 and not v["findings"]
    else:
        assert v["pause_reason"] == "OWNER_DECISION" and not v["active_jobs"]
    e.close()


@pytest.mark.parametrize("last_verdict", ["PASS", "BLOCKED"])
def test_quorum_incomplete_then_pass_or_fail(configured, last_verdict):
    e, s = ready(configured, quorum=True)
    complete(e, s, "builder")
    original = {r: job(e, r) for r in ["ai-a1", "ai-a2", "ai-a3"]}
    for r in ["ai-a1", "ai-a2"]:
        v = complete(e, s, r)
        assert v["gate"] is None and v["status"] != "VERIFIED_FOR_RELEASE"
        assert all(
            other["job_id"] not in original[r]["spec"]["prompt"] for rr, other in original.items() if rr != r
        )
    v = complete(
        e, s, "ai-a3", verdict=last_verdict, findings=[finding()] if last_verdict == "BLOCKED" else []
    )
    if last_verdict == "PASS":
        assert job(e, "verifier") and v["gate"] is None
        assert complete(e, s, "verifier")["status"] == "VERIFIED_FOR_RELEASE"
    else:
        assert job(e, "builder") and len(v["findings"]) == 1
    e.close()


@pytest.mark.parametrize("cycles", [2, 3])
def test_graph_escalation_survives_restart(configured, cycles):
    e, s = ready(configured)
    snapshot = (
        normalize_snapshot(
            finding(summary="SYNTHETIC stable"),
            e.root,
            {"requirement_paths": {"R1": ["old"]}},
            e.runtime / "synthetic-snapshot.json",
            "SYNTHETIC-snapshot",
        )
        if cycles == 2
        else None
    )
    for n in range(cycles):
        complete(e, s, "builder")
        v = complete(
            e,
            s,
            "verifier",
            verdict="BLOCKED",
            findings=[
                finding(
                    summary="SYNTHETIC stable" if cycles == 2 else f"SYNTHETIC round {n}", snapshot=snapshot
                )
            ],
        )
        if n < cycles - 1:
            assert v["status"] != "PAUSED"
            root = e.root
            e.close()
            e = Engine(root, launcher=s)
            assert e.view()["unsuccessful_cycles"] == n + 1
    assert v["status"] == "PAUSED" and v["pause_reason"] == "ESCALATED"
    assert v["unsuccessful_cycles"] == cycles
    e.close()


def test_commit_token_rejects_candidate_content_drift(configured):
    e, s = ready(configured)
    complete(e, s, "builder")
    complete(e, s, "verifier")
    token = commit_token(e)
    (e.root / "old").write_text("SYNTHETIC post-review drift")
    with pytest.raises(WorkflowError):
        e.approve(token)
    assert e.store.grant_for(token["gate_id"]) is None
    e.close()


def test_post_commit_pre_record_crash_reconciles_once(configured):
    e, s = ready(configured)
    complete(e, s, "builder")
    complete(e, s, "verifier")
    token = commit_token(e)
    e.approve(token)
    root = e.root
    # Sole operation in a disposable repository, never the project branch.
    git(
        root,
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "--allow-empty",
        "-m",
        "SYNTHETIC owner operation\n\nWorkflow-Job: SYNTHETIC-commit-job",
    )
    sha = git(root, "rev-parse", "HEAD")
    e.close()  # crash boundary after external commit, before completion event
    e = Engine(root, launcher=s)
    assert e.view()["gate"]["scope"] == "OWNER_COMMIT"
    v = e.record_owner_commit()
    assert v["committed"] and e.store.grant_for(token["gate_id"])["status"] == "CONSUMED"
    count = len(e.store.events())
    e.close()
    e = Engine(root, launcher=s)
    e.run()
    assert len(e.store.events()) == count and git(root, "rev-parse", "HEAD") == sha
    e.close()


def test_vacuum_into_restore_requires_owner_reconciliation(configured, tmp_path):
    e, s = ready(configured)
    snapshot = tmp_path / "vacuum-snapshot.db"
    e.store.conn.execute("VACUUM INTO ?", (str(snapshot),))
    complete(e, s, "builder")
    complete(e, s, "verifier")
    root = e.root
    e.close()
    shutil.copyfile(snapshot, root / "orchestrator/var/checkpoints.db")
    e = Engine(root, launcher=s)
    with pytest.raises(WorkflowError, match="Backup restore"):
        e.run()
    evidence = tmp_path / "owner-inspection.md"
    evidence.write_text(
        "SYNTHETIC reconciliation: no process or Git operation after snapshot; source inspected"
    )
    v = e.recover_backup(evidence, True)
    assert not e.store.meta("recovery_required") and not v["plan_granted"]
    assert job(e, "architect")
    assert all(r[0] == "INVALIDATED" for r in e.store.conn.execute("SELECT status FROM workflow_grants"))
    e.close()


@pytest.mark.parametrize(
    "failure", ["AUTH_FAILURE", "DENIED_ACTION", "TIMEOUT", "MALFORMED_RESULT", "EVIDENCE_UNAVAILABLE"]
)
def test_failure_classes_block_and_record_named_class(configured, failure):
    class NativeParserStub(Stub):
        def parse(self, job, raw):
            try:
                return parse_output(raw, "codex")
            except WorkflowError as exc:
                raise WorkflowError(str(exc) + ": SYNTHETIC_PRIVATE_EXCEPTION_BODY") from exc

    root, config = configured
    s = NativeParserStub(delayed=True)
    e = Engine(root, launcher=s)
    e.initialize(config)
    e.run()
    j = job(e, "architect")
    d = Path(j["runtime"])
    text = {
        "AUTH_FAILURE": "SYNTHETIC authentication failed 401",
        "DENIED_ACTION": "SYNTHETIC permission denied",
        "TIMEOUT": "SYNTHETIC timeout",
        "MALFORMED_RESULT": "SYNTHETIC not json",
    }
    if failure != "EVIDENCE_UNAVAILABLE":
        (d / "stdout.jsonl").write_text(text[failure])
    write_json(
        d / "terminal.json",
        dict(
            job_id=j["job_id"],
            phase="TERMINAL",
            exit_code=0 if failure in ("MALFORMED_RESULT", "EVIDENCE_UNAVAILABLE") else 1,
            timeout=failure == "TIMEOUT",
            started_utc=utc(),
            finished_utc=utc(),
            session_id="SYNTHETIC-failed-session",
        ),
    )
    v = e.run()
    assert v["status"] == "PAUSED" and len(s.starts) == 1
    event_classes = [
        r["payload"]["result"]["failure_class"] for r in e.store.events() if r["kind"] == "result"
    ]
    recorded = [e.store.job(j["job_id"]).get("failure"), v["pause_reason"], *event_classes]
    assert failure in recorded, f"Expected durable class {failure}, observed {recorded}"
    assert "SYNTHETIC_PRIVATE_EXCEPTION_BODY" not in "\n".join(e.store.conn.iterdump())
    assert "SYNTHETIC_PRIVATE_EXCEPTION_BODY" not in json.dumps(v)
    assert len(s.starts) == 1
    e.close()


def test_missing_binary_retries_only_one_proven_nonlaunch(configured):
    root, config = configured
    attempts = []

    def no_child(j):
        attempts.append(j["job_id"])
        raise FileNotFoundError("SYNTHETIC missing binary before child creation")

    e = Engine(root, launcher=no_child)
    e.initialize(config)
    e.run()
    v = e.run()
    assert attempts == [attempts[0]] * 2 and v["pause_reason"] == "MISSING_BINARY"
    e.run()
    assert len(attempts) == 2
    e.close()
