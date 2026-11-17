"""WP1-C01..C08 tests; fakes and a disposable real PLAN primitive probe only."""

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

import engine as engine_module
import pytest
from engineering_control_contracts.contract import OPERATIONS, VERSION, openapi, schemas
from engineering_control_contracts.offline import (
    Denied,
    FakeBoundary,
    FakeEngine,
    FakeT3,
    TestIssuer,
    TrustedPrincipal,
    validate,
)
from jsonschema import Draft202012Validator


@pytest.fixture
def rig(tmp_path):
    issuer = TestIssuer()
    owner = issuer.issue()
    boundary = FakeBoundary(tmp_path, issuer)
    return boundary, issuer, owner


def decision(b, **updates):
    return dict(
        expected_revision=b.state["revision"],
        decision="approve_plan",
        gate_id="gate-1",
        review_snapshot_id="review-1",
        **updates,
    )


def call(b, p, op, body, key="key-1", resource="work-1"):
    return b.request(p, op, resource, body, key)


def deny(code, fn):
    with pytest.raises(Denied) as error:
        fn()
    assert error.value.code == code
    validate("Error", error.value.body)


def start(rig):
    b, issuer, p = rig
    call(b, p, "decisions", decision(b))
    receipt = call(
        b, p, "execution_request", dict(expected_revision=b.state["revision"], runtime_preference="native")
    )
    job = b.state["jobs"][receipt["job_ids"][0]]
    monitor = issuer.issue(
        subject="monitor", actor="monitor", capabilities=("read", "monitor"), job_id=job["job_id"]
    )
    return b, p, monitor, job


def terminate(b, monitor, job):
    call(
        b,
        monitor,
        "observations",
        dict(
            expected_revision=b.state["revision"],
            job_id=job["job_id"],
            attempt=job["attempt"],
            runtime_ref=job["runtime_ref"],
            state="terminated",
            observed_at="2026-11-03T10:00:00Z",
        ),
        resource=job["job_id"],
    )


def evidence(b, job):
    artifact = b.register_artifact(job["job_id"], "synthetic complete test log")
    return dict(
        schema_version=VERSION,
        evidence_id="evidence-1",
        job_id=job["job_id"],
        attempt=job["attempt"],
        role=job["assignment"]["role"],
        binding=deepcopy(job["binding"]),
        assignment=deepcopy(job["assignment"]),
        environment_id=job["environment_id"],
        runtime_version=job["runtime_version"],
        session_id=job["session_id"],
        observer="coordinator",
        check_id="required-check",
        action_ref="action-1",
        started_at="2026-11-03T09:59:00Z",
        finished_at="2026-11-03T10:00:00Z",
        status="pass",
        artifacts=[artifact],
        limitations=["offline fake"],
    )


def test_machine_artifacts_and_all_references():
    root = Path(__file__).parents[1] / "engineering_control_contracts/v1"
    assert json.loads((root / "schemas.json").read_text()) == schemas()
    assert json.loads((root / "openapi.json").read_text()) == openapi()
    Draft202012Validator.check_schema(schemas())
    assert len(OPERATIONS) == 19
    operations = [operation for path in openapi()["paths"].values() for operation in path.values()]
    assert len(operations) == 19

    def visit(value):
        if isinstance(value, dict):
            if "$ref" in value:
                name = value["$ref"].split("/")[-1]
                assert name in schemas()["$defs"]
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schemas())
    visit(openapi())
    assert all(op["x-live-enabled"] is False for op in operations)


def test_c01_forged_principal_and_agent_cannot_grant(rig):
    b, issuer, owner = rig
    forged = TrustedPrincipal("owner", "human", "project-1", "work-1", frozenset(("decide",)))
    for p in (None, forged, {"actor": "human"}):
        deny("unauthenticated", lambda: call(b, p, "decisions", decision(b)))
    agent = issuer.issue(actor="agent", capabilities=("decide",))
    deny("forbidden", lambda: call(b, agent, "decisions", decision(b)))
    assert b.state["grants"] == [] and b.engine.grant_calls == 0
    for field in ("actor_type", "requested_by", "actor", "principal"):
        body = decision(b)
        body[field] = "owner"
        deny("invalid_request", lambda: call(b, owner, "decisions", body))


def test_c01_object_and_capability_scopes(rig):
    b, issuer, owner = rig
    for kwargs in ({"project": "another"}, {"work_item": "another"}, {"capabilities": ("read",)}):
        p = issuer.issue(**kwargs)
        deny("forbidden", lambda: call(b, p, "decisions", decision(b)))
    deny("not_found", lambda: call(b, owner, "decisions", decision(b), resource="other-work"))


def test_c02_safe_reads_and_disabled_mutations(rig):
    b, _issuer, p = rig
    before = deepcopy(b.state)
    for op in ("list_work_items", "get_work_item", "events", "review_context", "capabilities"):
        b.request(p, op)
    assert b.state == before
    assert b.engine.run_calls == b.runtime.launch_calls == 0
    for op, body in [
        (
            "create_work_item",
            dict(expected_revision=1, project_id="project-1", base_id="base-1", title="t", brief="b"),
        ),
        ("plan", dict(expected_revision=1, proposal_artifact_id="a-1")),
        ("assignments", dict(expected_revision=1, assignments=[b.state["assignment"]])),
    ]:
        deny("unsupported_operation", lambda: call(b, p, op, body))
    assert b.state == before


def test_c03_eligibility_and_no_silent_fallback(rig):
    b, _issuer, p = rig
    deny(
        "conflict",
        lambda: call(b, p, "execution_request", dict(expected_revision=1, runtime_preference="native")),
    )
    call(b, p, "decisions", decision(b))
    for runtime in ("t3",):
        deny(
            "unsupported_runtime",
            lambda: call(b, p, "execution_request", dict(expected_revision=2, runtime_preference=runtime)),
        )
    body = dict(expected_revision=2, runtime_preference="native", role="verifier")
    deny("invalid_request", lambda: call(b, p, "execution_request", body))
    assert b.runtime.launch_calls == 0 and b.engine.worker_admissions == 0
    receipt = call(b, p, "execution_request", dict(expected_revision=2, runtime_preference="native"))
    job = b.request(p, "job", receipt["job_ids"][0])
    assert job["assignment"] == b.state["assignment"]
    assert job["assignment"]["runtime"] == "native"
    assert b.runtime.launch_calls == b.engine.worker_admissions == 1
    assert receipt["execution_complete"] is False and receipt["effect_state"] == "pending"
    deny(
        "conflict",
        lambda: call(
            b, p, "execution_request", dict(expected_revision=3, runtime_preference="native"), key="new"
        ),
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_id", "wrong"),
        ("attempt", 2),
        ("role", "verifier"),
        ("session_id", "wrong"),
        ("environment_id", "wrong"),
        ("runtime_version", "wrong"),
        ("observer", "agent"),
        ("status", "skipped"),
        ("check_id", "wrong"),
    ],
)
def test_c04_wrong_result_bindings_rejected(rig, field, value):
    b, _p, monitor, job = start(rig)
    terminate(b, monitor, job)
    data = evidence(b, job)
    data[field] = value
    deny(
        "invalid_evidence",
        lambda: call(
            b,
            monitor,
            "results",
            dict(expected_revision=b.state["revision"], evidence=data),
            resource=job["job_id"],
        ),
    )
    assert not b.state["jobs"][job["job_id"]]["result_accepted"]


@pytest.mark.parametrize(
    "group,field",
    [
        ("binding", "candidate_id"),
        ("binding", "context_sha256"),
        ("binding", "manifest_sha256"),
        ("binding", "plan_sha256"),
        ("binding", "scope_sha256"),
        ("binding", "roles_sha256"),
        ("binding", "base_commit"),
        ("assignment", "account_ref"),
        ("assignment", "provider_instance"),
        ("assignment", "model"),
        ("assignment", "binary_sha256"),
        ("assignment", "prompt_sha256"),
        ("assignment", "binary_version"),
    ],
)
def test_c04_candidate_and_assignment_integrity(rig, group, field):
    b, _p, monitor, job = start(rig)
    terminate(b, monitor, job)
    data = evidence(b, job)
    data[group][field] = "c" * len(data[group][field])
    deny(
        "invalid_evidence",
        lambda: call(
            b,
            monitor,
            "results",
            dict(expected_revision=b.state["revision"], evidence=data),
            resource=job["job_id"],
        ),
    )


@pytest.mark.parametrize("damage", ["missing", "truncated", "incomplete", "tampered", "failed-check"])
def test_c04_missing_or_incomplete_required_artifacts(rig, damage):
    b, _p, monitor, job = start(rig)
    terminate(b, monitor, job)
    data = evidence(b, job)
    aid = data["artifacts"][0]["artifact_id"]
    if damage == "missing":
        b.state["artifacts"].pop(aid)
    elif damage in ("truncated", "incomplete"):
        flag = "truncated" if damage == "truncated" else "complete"
        value = damage == "truncated"
        data["artifacts"][0][flag] = value
        b.state["artifacts"][aid]["metadata"][flag] = value
    elif damage == "tampered":
        b.state["artifacts"][aid]["text"] += "changed"
    else:
        b.state["required_checks_failed"] = True
    deny(
        "invalid_evidence",
        lambda: call(
            b,
            monitor,
            "results",
            dict(expected_revision=b.state["revision"], evidence=data),
            resource=job["job_id"],
        ),
    )


def test_c04_result_acceptance_and_evidence_access(rig):
    b, p, monitor, job = start(rig)
    terminate(b, monitor, job)
    data = evidence(b, job)
    body = dict(expected_revision=b.state["revision"], evidence=data)
    receipt = call(b, monitor, "results", body, resource=job["job_id"])
    assert b.state["jobs"][job["job_id"]]["result_accepted"]
    assert call(b, monitor, "results", body, resource=job["job_id"]) == receipt
    aid = data["artifacts"][0]["artifact_id"]
    assert b.request(p, "evidence_content", aid)["text"] == "synthetic complete test log"
    deny("invalid_request", lambda: b.request(p, "evidence_content", "../../checkpoints.db"))
    deny("invalid_request", lambda: b.request(p, "evidence", aid, {"path": "/etc/passwd"}))
    deny("resource_limit", lambda: b.register_artifact(job["job_id"], "x" * 65537))
    data["artifacts"][0]["media_type"] = "application/x-sqlite3"
    deny("invalid_request", lambda: validate("Evidence", data))


def test_c05_separate_context_and_job_bound_monitors(rig):
    b, issuer, _owner = rig
    b, _p, monitor, builder = start(rig)
    # Explicit test-coordinator fixture for a second role, never caller-selected dispatch.
    verifier = deepcopy(builder)
    verifier.update(job_id="verifier-1", session_id="independent-session")
    verifier["assignment"]["role"] = "verifier"
    b.state["jobs"]["verifier-1"] = verifier
    terminate(b, monitor, builder)
    data = evidence(b, builder)
    foreign_monitor = issuer.issue(actor="monitor", capabilities=("monitor",), job_id="verifier-1")
    deny(
        "forbidden",
        lambda: call(
            b,
            foreign_monitor,
            "results",
            dict(expected_revision=b.state["revision"], evidence=data),
            resource=builder["job_id"],
        ),
    )
    # Builder evidence cannot pass as verifier evidence, even through its permitted monitor.
    data["job_id"] = "verifier-1"
    verifier["state"] = "terminated"
    deny(
        "invalid_evidence",
        lambda: call(
            b,
            foreign_monitor,
            "results",
            dict(expected_revision=b.state["revision"], evidence=data),
            resource="verifier-1",
        ),
    )
    assert builder["session_id"] != verifier["session_id"]


def test_c06_one_bound_grant_zero_dispatch_and_replay(rig):
    b, _issuer, p = rig
    body = decision(b)
    reviewed = deepcopy(b.state["review"])
    receipt = call(b, p, "decisions", body)
    assert receipt["effect"] == "approval_only" and receipt["effect_state"] == "completed"
    assert receipt["job_ids"] == [] and receipt["execution_complete"] is False
    assert b.state["grants"] == [reviewed]
    assert b.state["events"] == [dict(sequence=1, kind="grant", resource_id="work-1")]
    assert b.engine.grant_calls == b.engine.event_calls == 1
    assert b.engine.run_calls == b.runtime.launch_calls == b.engine.worker_admissions == 0
    assert b.engine.queued_effects == [] and b.state["jobs"] == {}
    assert call(b, p, "decisions", body) == receipt
    assert b.engine.grant_calls == b.engine.event_calls == 1
    assert b.engine.run_calls == b.runtime.launch_calls == b.engine.worker_admissions == 0


@pytest.mark.parametrize(
    "kind",
    [
        "reject_plan",
        "accept_business",
        "approve_commit",
        "approve_deployment",
        "approve_import",
        "approve_dry_run",
        "resolve_findings",
    ],
)
def test_c06_unsupported_decisions_do_not_fall_back(rig, kind):
    b, _issuer, p = rig
    body = decision(b)
    body["decision"] = kind
    before = deepcopy(b.state)
    deny("unsupported_decision", lambda: call(b, p, "decisions", body))
    assert b.state == before and b.engine.run_calls == b.runtime.launch_calls == b.engine.grant_calls == 0


def test_c07_replay_before_stale_and_conflicting_reuse(rig):
    b, issuer, p = rig
    body = decision(b)
    receipt = call(b, p, "decisions", body)
    assert call(b, p, "decisions", body) == receipt  # revision 1 is now stale, but replay is valid
    deny("conflict", lambda: call(b, p, "decisions", body, key="fresh-stale"))
    changed = {**body, "expected_revision": 2}
    deny("conflict", lambda: call(b, p, "decisions", changed))
    other_principal = issuer.issue(subject="second-owner")
    deny("conflict", lambda: call(b, other_principal, "decisions", body))
    revoked_agent = issuer.issue(actor="agent", capabilities=("read",))
    deny("forbidden", lambda: call(b, revoked_agent, "decisions", body))
    assert len(b.state["grants"]) == 1


def test_c07_concurrent_matching_requests_have_one_effect(rig):
    b, _issuer, p = rig
    body = decision(b)
    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(lambda _: call(b, p, "decisions", body), range(12)))
    assert all(r == receipts[0] for r in receipts)
    assert len(b.state["grants"]) == b.engine.grant_calls == 1


def test_c08_lost_response_restart_and_no_relaunch(rig, tmp_path):
    b, issuer, p = rig
    call(b, p, "decisions", decision(b))
    b.runtime.lose_next_response = True
    body = dict(expected_revision=2, runtime_preference="native")
    receipt = call(b, p, "execution_request", body)
    assert receipt["effect_state"] == "uncertain" and b.runtime.launch_calls == 1
    restarted = FakeBoundary(tmp_path, issuer, b.runtime, b.engine)
    assert call(restarted, p, "execution_request", body) == receipt
    deny(
        "conflict",
        lambda: call(
            restarted,
            p,
            "execution_request",
            dict(expected_revision=3, runtime_preference="native"),
            key="replacement",
        ),
    )
    assert b.runtime.launch_calls == 1
    job = restarted.state["jobs"][receipt["job_ids"][0]]
    monitor = issuer.issue(actor="monitor", capabilities=("monitor",), job_id=job["job_id"])
    call(
        restarted,
        monitor,
        "observations",
        dict(
            expected_revision=3,
            job_id=job["job_id"],
            attempt=1,
            runtime_ref=job["runtime_ref"],
            state="running",
            observed_at="2026-11-03T10:00:00Z",
        ),
        resource=job["job_id"],
    )
    assert job["state"] == "running"  # receipt remains the historical uncertain acknowledgement
    assert restarted.request(p, "job", job["job_id"])["state"] == "running"
    assert b.runtime.launch_calls == 1


def test_c08_pause_resume_cancel_and_termination(rig):
    b, issuer, p = rig
    call(b, p, "decisions", decision(b))
    call(b, p, "pause", dict(expected_revision=2, reason="stop admission"))
    deny(
        "conflict",
        lambda: call(b, p, "execution_request", dict(expected_revision=3, runtime_preference="native")),
    )
    call(b, p, "resume", dict(expected_revision=3, reason="resume admission"))
    assert b.runtime.launch_calls == 0
    receipt = call(b, p, "execution_request", dict(expected_revision=4, runtime_preference="native"))
    job = b.state["jobs"][receipt["job_ids"][0]]
    call(b, p, "pause", dict(expected_revision=5, reason="keep active work"), key="pause-2")
    assert job["state"] == "running" and b.runtime.cancel_calls == 0
    cancel = call(b, p, "cancel", dict(expected_revision=6, reason="explicit stop"), resource=job["job_id"])
    assert cancel["effect_state"] == "pending" and job["state"] == "cancel_pending"
    monitor = issuer.issue(actor="monitor", capabilities=("monitor",), job_id=job["job_id"])
    terminate(b, monitor, job)
    assert job["state"] == "terminated" and b.runtime.cancel_calls == 1
    # Viewer disconnection has no method/effect; host fixture state remains intact.
    assert len(b.state["jobs"]) == 1


@pytest.mark.parametrize(
    "field,value", [("expected_revision", True), ("expected_revision", -1), ("gate_id", "../escape")]
)
def test_strict_schema_bounds(rig, field, value):
    b, _issuer, p = rig
    body = decision(b)
    body[field] = value
    deny("invalid_request", lambda: call(b, p, "decisions", body))


def test_c06_real_plan_primitive_with_synthetic_checkpoint(configured, monkeypatch):
    """Actual Engine/Store/graph sync and exports, disposable repo, synthetic prior roles.

    This is source primitive evidence, not the fake HTTP facade or native isolation.
    No real Engine constructor ever receives the owner's checkout.
    """
    from unittest.mock import Mock

    from core import execution_lock
    from engine import Engine
    from test_engine import Stub, plan_token

    root, config = configured
    stub = Stub()
    engine = Engine(root, launcher=stub)
    try:
        engine.initialize(config)
        engine.run()  # Synthetic architect/reviewer fixture only; no native subprocess.
        token = plan_token(engine)
        baseline_jobs = engine.store.conn.execute("SELECT COUNT(*) FROM workflow_jobs").fetchone()[0]
        baseline_events = len(engine.store.events())
        grant = Mock(wraps=engine.store.grant)
        event = Mock(wraps=engine.store.event)
        monkeypatch.setattr(engine.store, "grant", grant)
        monkeypatch.setattr(engine.store, "event", event)
        probes = {}
        for name in ("run", "_prepare", "_dispatch", "_drive"):
            probes[name] = Mock(side_effect=AssertionError("Unexpected dispatch boundary: " + name))
            monkeypatch.setattr(engine, name, probes[name])
        admission = Mock(side_effect=AssertionError("Unexpected job admission"))
        launcher = Mock(side_effect=AssertionError("Unexpected launcher"))
        monkeypatch.setattr(engine.store, "create_job", admission)
        monkeypatch.setattr(engine, "launcher", launcher)

        # The approval guard legitimately runs git-only candidate/plan checks.
        # Permit only git subprocesses; reject any worker/native process.
        allowed_popen = []
        real_popen = engine_module.subprocess.Popen

        def guarded_popen(cmd, *args, **kwargs):
            executable = cmd[0] if isinstance(cmd, list | tuple) and cmd else cmd
            if Path(str(executable)).name != "git":
                raise AssertionError(f"Unexpected non-git subprocess: {cmd!r}")
            allowed_popen.append(cmd)
            return real_popen(cmd, *args, **kwargs)

        monkeypatch.setattr(engine_module.subprocess, "Popen", guarded_popen)
        # Real callers own this serialization boundary, not Engine itself.
        with execution_lock(engine.runtime / "execution.lock"):
            view = engine.grant_and_synchronize(token)
        assert grant.call_count == event.call_count == 1
        assert event.call_args.args[1] == "grant"
        assert view["plan_granted"] and view["active_jobs"] == []
        assert engine.store.lookup_grant(token["token_id"])["data"] == token
        assert len(engine.store.events()) == baseline_events + 1
        assert engine.store.conn.execute("SELECT COUNT(*) FROM workflow_jobs").fetchone()[0] == baseline_jobs
        for probe in [*probes.values(), admission, launcher]:
            probe.assert_not_called()
        assert allowed_popen
        assert {Path(str(cmd[0])).name for cmd in allowed_popen} == {"git"}
        # No admitted/queued worker rows; checkpoint eligibility alone is not dispatch.
        statuses = [row[0] for row in engine.store.conn.execute("SELECT status FROM workflow_jobs")]
        assert not set(statuses) & {"CREATED", "LAUNCH_INTENT", "RUNNING"}
    finally:
        engine.close()


def test_c08_restart_between_intent_and_external_response(rig, tmp_path):
    b, issuer, p = rig
    call(b, p, "decisions", decision(b))

    def crash(job):
        raise SystemExit("synthetic process exit after intent publication")

    b.runtime.launch = crash
    body = dict(expected_revision=2, runtime_preference="native")
    with pytest.raises(SystemExit):
        call(b, p, "execution_request", body)
    restarted = FakeBoundary(tmp_path, issuer, b.runtime, b.engine)
    prior = call(restarted, p, "execution_request", body)
    assert prior["effect_state"] == "pending"
    job = restarted.request(p, "job", prior["job_ids"][0])
    assert job["state"] == "uncertain"
    deny(
        "conflict",
        lambda: call(
            restarted,
            p,
            "execution_request",
            dict(expected_revision=3, runtime_preference="native"),
            key="replacement",
        ),
    )
    assert b.engine.worker_admissions == 1


def test_c07_revoked_principal_cannot_replay_receipt(rig):
    b, issuer, p = rig
    body = decision(b)
    call(b, p, "decisions", body)
    issuer.issued.clear()
    deny("unauthenticated", lambda: call(b, p, "decisions", body))


@pytest.mark.parametrize("damage", ["gate", "snapshot", "binding"])
def test_c06_stale_review_identity_has_no_effect(rig, damage):
    b, _issuer, p = rig
    body = decision(b)
    if damage == "gate":
        body["gate_id"] = "wrong"
    elif damage == "snapshot":
        body["review_snapshot_id"] = "wrong"
    else:
        b.state["binding"]["candidate_id"] = "f" * 64
    deny("conflict", lambda: call(b, p, "decisions", body))
    assert not b.state["grants"] and not b.state["events"] and not b.state["jobs"]
    assert b.engine.grant_calls == b.engine.run_calls == b.runtime.launch_calls == 0


def test_unsupported_version_and_invalid_observation(rig):
    b, _issuer, p = rig
    deny("unsupported_version", lambda: b.request(p, "capabilities", version="future-2"))
    b, p, monitor, job = start(rig)
    body = dict(
        expected_revision=b.state["revision"],
        job_id=job["job_id"],
        attempt=1,
        runtime_ref="wrong-runtime",
        state="terminated",
        observed_at="2026-11-03T10:00:00Z",
    )
    deny("conflict", lambda: call(b, monitor, "observations", body, resource=job["job_id"]))
    body["runtime_ref"] = job["runtime_ref"]
    body["observed_at"] = "not-a-timestamp"
    deny("invalid_request", lambda: call(b, monitor, "observations", body, resource=job["job_id"]))
    deny("forbidden", lambda: call(b, p, "observations", body, resource=job["job_id"]))


def test_c05_verifier_cannot_reuse_builder_session(rig):
    _b, issuer, _p = rig
    b, _p, _monitor, builder = start(rig)
    verifier = deepcopy(builder)
    verifier.update(job_id="verifier-1", state="terminated")
    verifier["assignment"]["role"] = "verifier"
    b.state["jobs"]["verifier-1"] = verifier
    vm = issuer.issue(actor="monitor", capabilities=("monitor",), job_id="verifier-1")
    data = evidence(b, verifier)
    deny(
        "invalid_evidence",
        lambda: call(
            b,
            vm,
            "results",
            dict(expected_revision=b.state["revision"], evidence=data),
            resource="verifier-1",
        ),
    )


def test_c04_option_and_time_binding(rig):
    b, _p, monitor, job = start(rig)
    terminate(b, monitor, job)
    data = evidence(b, job)
    data["assignment"]["options"]["reasoning"] = "low"
    deny(
        "invalid_evidence",
        lambda: call(
            b,
            monitor,
            "results",
            dict(expected_revision=b.state["revision"], evidence=data),
            resource=job["job_id"],
        ),
    )
    data["assignment"] = deepcopy(job["assignment"])
    data["finished_at"] = "2026-11-03T09:58:00Z"
    deny(
        "invalid_evidence",
        lambda: call(
            b,
            monitor,
            "results",
            dict(expected_revision=b.state["revision"], evidence=data),
            resource=job["job_id"],
        ),
    )


@pytest.mark.parametrize(
    "definition,field,valid",
    [
        ("Assignment", "provider_instance", "valid-id"),
        ("Assignment", "binary_sha256", "a" * 64),
        ("Binding", "base_commit", "a" * 40),
    ],
)
@pytest.mark.parametrize("suffix", ["\n", "\r\n", " ", "\t", "\x00", "\u2028", "\u2029"])
def test_r1_scalar_schema_rejects_final_disallowed_characters(definition, field, valid, suffix):
    scalar = schemas()["$defs"][definition]["properties"][field]
    assert not Draft202012Validator(scalar).is_valid(valid + suffix)


@pytest.mark.parametrize("value", ["a", "A0_" + "-" * 93])
def test_r1_identifier_valid_length_boundaries(value):
    from engineering_control_contracts.contract import ID

    assert Draft202012Validator(ID).is_valid(value)


@pytest.mark.parametrize(
    "value",
    ["", "a" * 97, "_start", "-start", "bad id", "bad\nid", "bad\rid", "bad\tid", "bad\x00id", "bad/id", "é"],
)
def test_r1_identifier_invalid_characters_and_lengths(value):
    from engineering_control_contracts.contract import ID

    assert not Draft202012Validator(ID).is_valid(value)


@pytest.mark.parametrize("field,size", [("binary_sha256", 64), ("prompt_sha256", 64)])
@pytest.mark.parametrize("damage", ["short", "long", "nonhex", "uppercase", "embedded_control"])
def test_r1_sha256_malformed(field, size, damage):
    scalar = schemas()["$defs"]["Assignment"]["properties"][field]
    values = {
        "short": "a" * (size - 1),
        "long": "a" * (size + 1),
        "nonhex": "g" * size,
        "uppercase": "A" * size,
        "embedded_control": "a" * (size - 1) + "\n",
    }
    assert Draft202012Validator(scalar).is_valid("0123456789abcdef" * 4)
    assert not Draft202012Validator(scalar).is_valid(values[damage])


@pytest.mark.parametrize("value", ["a" * 39, "a" * 41, "g" * 40, "A" * 40, "a" * 39 + "\t"])
def test_r1_git_sha_malformed(value):
    scalar = schemas()["$defs"]["Binding"]["properties"]["base_commit"]
    assert Draft202012Validator(scalar).is_valid("0123456789abcdef" * 2 + "01234567")
    assert not Draft202012Validator(scalar).is_valid(value)


@pytest.mark.parametrize("key", ["key\n", "key\r\n", "key ", "key\t", "key\x00", "k" * 97])
def test_r1_idempotency_header_denied_without_effect(rig, key):
    b, _issuer, p = rig
    before = deepcopy(b.state)
    deny("invalid_request", lambda: call(b, p, "decisions", decision(b), key=key))
    assert b.state == before and b.engine.grant_calls == 0


@pytest.mark.parametrize(
    "role", ["architect", "reviewer", "builder", "verifier", "proposer", "ai-a1", "ai-a2", "ai-a3"]
)
@pytest.mark.parametrize("reasoning", ["high", "xhigh", "max"])
def test_r2_existing_roles_and_extended_reasoning_are_schema_valid(rig, role, reasoning):
    b, _issuer, _p = rig
    assignment = deepcopy(b.state["assignment"])
    assignment.update(role=role, options={"reasoning": reasoning})
    validate("Assignment", assignment)
    # Evidence role must permit the same workflow vocabulary; runtime policy is separate.
    scalar = schemas()["$defs"]["Evidence"]["properties"]["role"]
    assert Draft202012Validator(scalar).is_valid(role)


@pytest.mark.parametrize(
    "reasoning", ["", "a" * 65, "xhigh\n", "max\r\n", " high", "high low", "bad\x00value", ["max"], 1]
)
def test_r2_malformed_reasoning_is_invalid_request(rig, reasoning):
    b, _issuer, _p = rig
    assignment = deepcopy(b.state["assignment"])
    assignment["options"]["reasoning"] = reasoning
    deny("invalid_request", lambda: validate("Assignment", assignment))


@pytest.mark.parametrize("role", ["owner", "admin", "architect\n", "unknown-role"])
def test_r2_unknown_or_malformed_role_denied(rig, role):
    b, _issuer, _p = rig
    assignment = deepcopy(b.state["assignment"])
    assignment["role"] = role
    deny("invalid_request", lambda: validate("Assignment", assignment))
    scalar = schemas()["$defs"]["Evidence"]["properties"]["role"]
    assert not Draft202012Validator(scalar).is_valid(role)


@pytest.mark.parametrize(
    "role,reasoning",
    [
        ("architect", "xhigh"),
        ("reviewer", "max"),
        ("builder", "xhigh"),
        ("builder", "max"),
        ("builder", "unadvertised-value"),
    ],
)
def test_r2_schema_valid_unqualified_tuple_cannot_dispatch(rig, role, reasoning):
    b, _issuer, p = rig
    capabilities = b.request(p, "capabilities")
    qualified = deepcopy(b.state["assignment"])
    assert capabilities["qualified_assignments"] == [qualified]
    assert capabilities["production_enabled"] is False
    assert capabilities["t3_execution_enabled"] is False
    call(b, p, "decisions", decision(b))
    # Test-coordinator fixture change, not a new assignments API. The fake must
    # still reject this unqualified tuple before worker admission or launch.
    b.state["assignment"].update(role=role, options={"reasoning": reasoning})
    validate("Assignment", b.state["assignment"])
    before = deepcopy(b.state)
    deny(
        "unsupported_assignment",
        lambda: call(
            b,
            p,
            "execution_request",
            dict(expected_revision=b.state["revision"], runtime_preference="native"),
        ),
    )
    assert b.state == before
    assert b.engine.worker_admissions == b.engine.run_calls == b.runtime.launch_calls == 0
    assert not b.engine.queued_effects
    assert b.request(p, "capabilities")["qualified_assignments"] == [qualified]
    # Syntactically supported role/option does not enable the disabled mutation API.
    deny(
        "unsupported_operation",
        lambda: call(
            b,
            p,
            "assignments",
            dict(expected_revision=b.state["revision"], assignments=[b.state["assignment"]]),
        ),
    )


@pytest.mark.parametrize("reasoning", ["a", "a" * 64])
def test_r2_reasoning_token_valid_boundaries(rig, reasoning):
    b, _issuer, _p = rig
    assignment = deepcopy(b.state["assignment"])
    assignment["options"]["reasoning"] = reasoning
    validate("Assignment", assignment)
