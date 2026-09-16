"""Comprehensive acceptance tests for Week 0 orchestrator prerequisites.

Covers:
- Branch portability in doctor()
- Extracted preflight checks with action-specific sets
- Store.lookup_grant() and Store.adopt_scope_atomic()
- Planning stage routing and scope_adopted event
- Scope proposal JSON schema validation
- Engine.adopt_scope() and recovery
- Orchestrator-side deduplication (approvals & non-approvals)
- Role reconfiguration defaults preservation
- Architect scope proposal output contract
- Failure injection, crash recovery, and end-to-end workflow
"""

import json
import sqlite3
import subprocess
import sys
import uuid
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, patch

import jsonschema
import pytest
from candidates import freeze, git
from core import (
    DuplicateKeyConflict,
    GrantReconciliationRequired,
    PreconditionError,
    RecoveryError,
    WorkflowError,
    bytes_hash,
    canonical,
    digest,
    utc,
    write_json,
)
from core import ValidationError as CoreValidationError
from dashboard_api import (
    deduplicate_action,
    execute_action,
    get_plan_projection,
    get_state_projection,
    sanitize_error,
)
from engine import Engine, SUPPORTED_STAGES, extract_scope_proposal
from preflight import (
    CheckResult,
    check_approved_capabilities,
    check_binary,
    check_branch,
    check_configured_root,
    check_dependencies,
    check_recovery_cleared,
    check_roles_mirror_synced,
    check_sandbox_probe,
    check_sqlite_integrity,
    run_dispatch_preflight,
    run_display_checks,
    run_init_checks,
    run_owner_action_checks,
)
from routing import apply_event, gate_id
from store import Store
from test_engine import Stub, plan_token


def _sample_scope():
    return {
        "allowed_paths": ["old", "mode", "new"],
        "requirements": ["R1: sample requirement"],
        "validation_commands": [["python3", "-c", "print(1)"]],
    }


def _sample_proposal(stages=None):
    return {
        "schema": "scope-proposal/v1",
        "scope": _sample_scope(),
        "implementation_stages": stages or ["1"],
    }


class ProposalStub(Stub):
    def __init__(self, plan_text=None, outcomes=None, delayed=False):
        super().__init__(outcomes=outcomes, delayed=delayed)
        self.plan_text = plan_text

    def complete(self, job):
        body = deepcopy(job["spec"]["envelope"])
        role_outcome = deepcopy(self.outcomes.get(job["role"], {}))
        wire_override = role_outcome.pop("wire", None)
        body.update(role_outcome)
        body["session_id"] = "synthetic-" + job["job_id"]
        wire = {
            "plan_text": (wire_override.get("plan_text") if wire_override else None) or self.plan_text or "Synthetic plan",
            "explanation": (wire_override.get("explanation") if wire_override else None) or "SYNTHETIC fixture result",
        }
        payload = {
            "body": body,
            "wire": wire,
        }
        destination = Path(job["runtime"])
        (destination / "stdout.jsonl").write_text(json.dumps(payload))
        write_json(
            destination / "terminal.json",
            dict(
                job_id=job["job_id"],
                phase="TERMINAL",
                exit_code=0,
                timeout=False,
                started_utc=utc(),
                finished_utc=utc(),
                session_id=body["session_id"],
            ),
            immutable=True,
        )



# ==============================================================================
# 1. Host/Branch Portability
# ==============================================================================


def test_doctor_passes_on_configured_task_branch(configured):
    root, config = configured
    from cli import doctor

    git(root, "checkout", "-b", "task/work-item-123")
    res = doctor(root, expected_branch="task/work-item-123")
    assert res["checks"]["branch"] is True


def test_doctor_fails_on_unconfigured_branch(configured):
    root, config = configured
    from cli import doctor

    git(root, "checkout", "-b", "task/unconfigured-456")
    res = doctor(root, expected_branch="feature/scope-context-portability")
    assert res["checks"]["branch"] is False
    assert res["ok"] is False


# ==============================================================================
# 2. Extracted Preflight Checks with Action-Specific Sets
# ==============================================================================


def test_preflight_dispatch_includes_sandbox_and_capabilities(configured):
    root, config = configured
    runtime = root / "orchestrator/var"
    checks = run_dispatch_preflight(config, runtime, root)
    names = {c.name for c in checks}
    assert "sandbox_control_store_and_git_denial" in names
    assert "phase0_approved_capabilities" in names
    assert "sqlite_integrity" in names
    assert "recovery_cleared" in names


def test_preflight_owner_actions_skip_binary_check(configured):
    root, config = configured
    runtime = root / "orchestrator/var"
    checks = run_owner_action_checks(runtime, root, config)
    names = {c.name for c in checks}
    assert "sqlite_integrity" in names
    assert "recovery_cleared" in names
    assert "configured_root" in names
    assert not any(n.startswith("binary:") for n in names)


def test_binary_failure_does_not_block_pause(configured):
    root, config = configured
    stub = Stub()
    e = Engine(root, launcher=stub)
    try:
        e.initialize(config)
        e.run()
        # Even with a broken binary pin, owner pause check passes
        checks = run_owner_action_checks(e.runtime, root, e.config)
        assert all(c.ok for c in checks)
        v = e.owner_decision("pause", {"reason": "Routine operator pause"})
        assert v["status"] == "PAUSED"
    finally:
        e.close()


# ==============================================================================
# 3. Store.lookup_grant()
# ==============================================================================


def test_lookup_grant_returns_row_by_token_id(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    try:
        token = {
            "token_id": "tok-123",
            "gate_id": "gate-123",
            "status": "ISSUED",
            "scope": "PLAN",
        }
        store.grant(token)
        found = store.lookup_grant("tok-123")
        assert found is not None
        assert found["status"] == "ISSUED"
        assert found["data"]["token_id"] == "tok-123"
        assert found["data"]["gate_id"] == "gate-123"
    finally:
        store.close()


def test_lookup_grant_returns_none_when_absent(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    try:
        assert store.lookup_grant("nonexistent-token") is None
    finally:
        store.close()


# ==============================================================================
# 4. Store.adopt_scope_atomic()
# ==============================================================================


def test_adopt_scope_atomic_inserts_into_payload_column(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    try:
        new_config = {"root": str(tmp_path), "stages": ["1"]}
        event_id, seq = store.adopt_scope_atomic(
            new_config=new_config,
            action_id="act-001",
            scope_hash="h" * 64,
            implementation_stages=["1"],
            candidate_meta={"candidate_id": "cand-001"},
            request_hash="req-001",
        )
        row = store.conn.execute(
            "SELECT event_id, kind, payload, seq FROM workflow_events WHERE event_id=?",
            (event_id,),
        ).fetchone()
        assert row is not None
        assert row["kind"] == "scope_adopted"
        payload = json.loads(row["payload"])
        assert payload["action_id"] == "act-001"
        assert payload["request_hash"] == "req-001"
        assert payload["scope_hash"] == "h" * 64
        assert payload["implementation_stages"] == ["1"]
    finally:
        store.close()


def test_adopt_scope_atomic_seq_from_lastrowid(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    try:
        event_id, seq = store.adopt_scope_atomic(
            new_config={"stages": ["1"]},
            action_id="act-002",
            scope_hash="h" * 64,
            implementation_stages=["1"],
            candidate_meta={},
            request_hash="req-002",
        )
        assert seq == 1
    finally:
        store.close()


def test_adopt_scope_atomic_event_id_supplied_not_null(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    try:
        event_id, seq = store.adopt_scope_atomic(
            new_config={},
            action_id="act-003",
            scope_hash="h" * 64,
            implementation_stages=["1"],
            candidate_meta={},
            request_hash="req-003",
        )
        assert event_id is not None
        assert len(event_id) > 10
    finally:
        store.close()


def test_adopt_scope_atomic_invalidates_issued_and_reserved(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    try:
        store.grant({"token_id": "tok-1", "gate_id": "gate-1", "scope": "PLAN"})
        store.grant({"token_id": "tok-2", "gate_id": "gate-2", "scope": "PLAN"})
        store.conn.execute("UPDATE workflow_grants SET status='RESERVED' WHERE token_id='tok-2'")
        store.conn.commit()

        store.adopt_scope_atomic(
            new_config={},
            action_id="act-004",
            scope_hash="h" * 64,
            implementation_stages=["1"],
            candidate_meta={},
            request_hash="req-004",
        )

        row1 = store.conn.execute("SELECT status FROM workflow_grants WHERE token_id='tok-1'").fetchone()
        row2 = store.conn.execute("SELECT status FROM workflow_grants WHERE token_id='tok-2'").fetchone()
        assert row1[0] == "INVALIDATED"
        assert row2[0] == "INVALIDATED"
    finally:
        store.close()


def test_adopt_scope_atomic_request_hash_in_payload(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    try:
        event_id, seq = store.adopt_scope_atomic(
            new_config={},
            action_id="act-005",
            scope_hash="s" * 64,
            implementation_stages=["1"],
            candidate_meta={},
            request_hash="expected-request-hash",
        )
        events = store.events()
        assert events[0]["payload"]["request_hash"] == "expected-request-hash"
    finally:
        store.close()


def test_adopt_scope_atomic_all_three_in_one_transaction(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    try:
        store.grant({"token_id": "tok-active", "gate_id": "gate-act", "scope": "PLAN"})
        new_cfg = {"adopted": True}
        event_id, seq = store.adopt_scope_atomic(
            new_config=new_cfg,
            action_id="act-006",
            scope_hash="s" * 64,
            implementation_stages=["1"],
            candidate_meta={"id": "c1"},
            request_hash="req-006",
        )
        assert store.meta("config") == new_cfg
        assert store.lookup_grant("tok-active")["status"] == "INVALIDATED"
        assert store.events()[-1]["kind"] == "scope_adopted"
    finally:
        store.close()


# ==============================================================================
# 5. Planning Stage Routing & scope_adopted Event
# ==============================================================================


def test_scope_adopted_reads_payload_not_data():
    current = {
        "cursor": 0,
        "revision": 0,
        "work_item": "item",
        "stage": "plan",
        "stages": {},
        "plan_revision_hash": "p" * 64,
        "scope_hash": "old" * 16,
        "roles_hash": "r" * 64,
        "roles": {},
        "candidate": {},
        "plan_granted": False,
        "status": "PLAN_SUBMITTED",
        "next_roles": [],
        "gate": None,
    }
    event = {
        "seq": 1,
        "kind": "scope_adopted",
        "payload": {
            "implementation_stages": ["1"],
            "scope_hash": "new" * 16,
            "candidate_meta": {"candidate_id": "cand-new"},
            "action_id": "a1",
            "request_hash": "r1",
        },
    }
    new_state = apply_event(current, event, {})
    assert new_state["stage"] == "1"
    assert new_state["scope_hash"] == "new" * 16
    assert new_state["candidate"] == {"candidate_id": "cand-new"}


def test_scope_adopted_updates_candidate_in_routing():
    current = {
        "cursor": 0,
        "revision": 0,
        "work_item": "item",
        "stage": "plan",
        "stages": {},
        "plan_revision_hash": "p" * 64,
        "scope_hash": "old" * 16,
        "roles_hash": "r" * 64,
        "roles": {},
        "candidate": {"candidate_id": "old-cand"},
        "plan_granted": False,
        "status": "PLAN_SUBMITTED",
        "next_roles": [],
        "gate": None,
    }
    event = {
        "seq": 1,
        "kind": "scope_adopted",
        "payload": {
            "implementation_stages": ["1"],
            "scope_hash": "new" * 16,
            "candidate_meta": {"candidate_id": "new-cand-meta"},
        },
    }
    new_state = apply_event(current, event, {})
    assert new_state["candidate"]["candidate_id"] == "new-cand-meta"


def test_scope_adopted_routing_sets_implementation_stage():
    current = {
        "cursor": 0,
        "revision": 0,
        "work_item": "item",
        "stage": "plan",
        "stages": {},
        "plan_revision_hash": "p" * 64,
        "scope_hash": "s" * 64,
        "roles_hash": "r" * 64,
        "roles": {},
        "candidate": {},
        "plan_granted": False,
        "status": "PLAN_SUBMITTED",
        "next_roles": [],
        "gate": None,
    }
    event = {
        "seq": 1,
        "kind": "scope_adopted",
        "payload": {
            "implementation_stages": ["2", "3"],
            "scope_hash": "s2" * 32,
            "candidate_meta": {},
        },
    }
    new_state = apply_event(current, event, {})
    assert new_state["stage"] == "2"


def test_scope_adopted_routing_preserves_plan_history():
    current = {
        "cursor": 0,
        "revision": 0,
        "work_item": "item",
        "stage": "plan",
        "stages": {},
        "plan_revision_hash": "p" * 64,
        "scope_hash": "s" * 64,
        "roles_hash": "r" * 64,
        "roles": {},
        "candidate": {},
        "plan_granted": False,
        "status": "PLAN_SUBMITTED",
        "next_roles": [],
        "gate": None,
    }
    event = {
        "seq": 1,
        "kind": "scope_adopted",
        "payload": {
            "implementation_stages": ["1"],
            "scope_hash": "s_adopted" * 7 + "abcd",
            "candidate_meta": {},
        },
    }
    new_state = apply_event(current, event, {})
    assert "plan" in new_state["stages"]
    assert new_state["stages"]["plan"]["historical"] is False


def test_plan_approval_after_adoption_dispatches_builder():
    state = {
        "cursor": 0,
        "revision": 0,
        "work_item": "item",
        "stage": "1",
        "stages": {"plan": {"status": "SCOPE_ADOPTED"}},
        "plan_revision_hash": "p" * 64,
        "scope_hash": "s" * 64,
        "roles_hash": "r" * 64,
        "roles": {},
        "candidate": {},
        "plan_granted": False,
        "status": "PLAN_SUBMITTED",
        "next_roles": [],
        "gate": {"scope": "PLAN", "gate_id": "plan-123456789012345678901234"},
        "approval_refs": [],
    }
    state["gate"]["gate_id"] = gate_id(state, "PLAN")
    event = {
        "seq": 1,
        "kind": "grant",
        "payload": {
            "token_id": "tok-plan-approved",
            "scope": "PLAN",
            "schema_version": 2,
            "gate_id": state["gate"]["gate_id"],
            "plan_revision_hash": state["plan_revision_hash"],
            "scope_hash": state["scope_hash"],
            "roles_hash": state["roles_hash"],
            "stages": ["1"],
        },
    }
    new_state = apply_event(state, event, {})
    assert new_state["status"] == "APPROVED_FOR_BUILD"
    assert new_state["next_roles"] == ["builder"]
    assert new_state["plan_granted"] is True
    assert new_state["gate"] is None


def test_planning_stage_parks_at_plan_gate_after_reviewer(configured):
    root, config = configured
    config["stages"] = ["plan"]
    proposal = _sample_proposal()
    plan_with_proposal = f"# Proposed Architecture\n\n```scope-proposal\n{json.dumps(proposal)}\n```\n"

    stub = ProposalStub(outcomes={
        "architect": {
            "verdict": "PASS",
            "wire": {"plan_text": plan_with_proposal, "explanation": "OK"},
        },
        "reviewer": {
            "verdict": "PASS",
            "wire": {"explanation": "Reviewed plan"},
        },
    })
    e = Engine(root, launcher=stub)
    try:
        e.initialize(config)
        v = e.run()  # architect runs -> reviewer runs -> parks at PLAN gate
        assert v["stage"] == "plan"
        assert v["gate"] is not None
        assert v["gate"]["scope"] == "PLAN"
        assert v["plan_granted"] is False
        assert v["next_roles"] == []
    finally:
        e.close()


# ==============================================================================
# 6. Scope Proposal JSON Schema
# ==============================================================================


def _load_proposal_schema():
    schema_file = Path(__file__).resolve().parents[1] / "schemas/v1/scope-proposal.json"
    return json.loads(schema_file.read_text())


def test_scope_proposal_schema_accepts_valid_instance():
    schema = _load_proposal_schema()
    instance = _sample_proposal(["1", "2"])
    jsonschema.validate(instance=instance, schema=schema)


def test_scope_proposal_schema_rejects_duplicate_implementation_stages():
    schema = _load_proposal_schema()
    instance = _sample_proposal(["1", "1"])
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=schema)


def test_scope_proposal_schema_rejects_missing_required_fields():
    schema = _load_proposal_schema()
    instance = {"schema": "scope-proposal/v1", "scope": _sample_scope()}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=schema)


def test_scope_proposal_schema_rejects_additional_properties():
    schema = _load_proposal_schema()
    instance = _sample_proposal(["1"])
    instance["extra_field"] = "forbidden"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=schema)


# ==============================================================================
# 7. Engine.adopt_scope() and recovery
# ==============================================================================


def _setup_engine_at_plan_gate(root, config, proposal):
    plan_with_proposal = f"# Plan\n\n```scope-proposal\n{json.dumps(proposal)}\n```\n"
    stub = ProposalStub(outcomes={
        "architect": {
            "verdict": "PASS",
            "wire": {"plan_text": plan_with_proposal, "explanation": "OK"},
        },
        "reviewer": {
            "verdict": "PASS",
            "wire": {"explanation": "Reviewed"},
        },
    })
    e = Engine(root, launcher=stub)
    config["stages"] = ["plan"]
    e.initialize(config)
    e.run()
    return e


def test_adopt_scope_uses_view_not_self_state(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        assert not hasattr(e, "state")
        v = e.adopt_scope(
            scope=proposal["scope"],
            implementation_stages=proposal["implementation_stages"],
            action_id="act-adopt-1",
            request_hash="hash-adopt-1",
        )
        assert v["stage"] == "1"
        assert v["gate"]["scope"] == "PLAN"
    finally:
        e.close()


def test_adopt_scope_uses_synchronize_checkpoint(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        v = e.adopt_scope(
            scope=proposal["scope"],
            implementation_stages=proposal["implementation_stages"],
            action_id="act-sync-1",
            request_hash="hash-sync-1",
        )
        checkpoint_view = e._synchronize_checkpoint()
        assert checkpoint_view["stage"] == "1"
        assert checkpoint_view["scope_hash"] == digest(proposal["scope"])
    finally:
        e.close()


def test_adopt_scope_reloads_config_via_meta(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        e.adopt_scope(
            scope=proposal["scope"],
            implementation_stages=proposal["implementation_stages"],
            action_id="act-meta-1",
            request_hash="hash-meta-1",
        )
        assert e.config["stages"] == ["plan", "1"]
        assert e.config["scope"] == proposal["scope"]
    finally:
        e.close()


def test_adopt_scope_candidate_before_commit(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        v = e.adopt_scope(
            scope=proposal["scope"],
            implementation_stages=proposal["implementation_stages"],
            action_id="act-cand-1",
            request_hash="hash-cand-1",
        )
        assert "candidate" in v
        assert "candidate_id" in v["candidate"]
    finally:
        e.close()


def test_adopt_scope_no_stale_overwrite_after_restart(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        e.adopt_scope(
            scope=proposal["scope"],
            implementation_stages=proposal["implementation_stages"],
            action_id="act-restart-1",
            request_hash="hash-restart-1",
        )
    finally:
        e.close()

    e2 = Engine(root)
    try:
        v2 = e2.view()
        assert v2["stage"] == "1"
        assert e2.config["stages"] == ["plan", "1"]
        assert v2["scope_hash"] == digest(proposal["scope"])
    finally:
        e2.close()


def test_adopt_scope_recovery_reads_payload_not_data(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        e.adopt_scope(
            scope=proposal["scope"],
            implementation_stages=proposal["implementation_stages"],
            action_id="act-rec-1",
            request_hash="hash-rec-1",
        )
        # Deduplication under lock should recover using payload
        v = e.recover_adopt_scope(stored_request_hash="hash-rec-1", submitted_request_hash="hash-rec-1")
        assert v["stage"] == "1"
    finally:
        e.close()


def test_adopt_scope_recovery_rejects_missing_request_hash(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        with pytest.raises(RecoveryError):
            e.recover_adopt_scope(stored_request_hash="", submitted_request_hash="hash-1")
    finally:
        e.close()


def test_adopt_scope_rejected_if_not_plan_stage(configured):
    root, config = configured
    stub = Stub()
    e = Engine(root, launcher=stub)
    config["stages"] = ["1"]
    e.initialize(config)
    try:
        with pytest.raises(PreconditionError):
            e.adopt_scope(
                scope=_sample_scope(),
                implementation_stages=["2"],
                action_id="act-err-1",
                request_hash="req-err-1",
            )
    finally:
        e.close()


def test_adopt_scope_rejected_duplicate_within_implementation_stages(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        with pytest.raises(CoreValidationError):
            e.adopt_scope(
                scope=proposal["scope"],
                implementation_stages=["1", "1"],
                action_id="act-dup-1",
                request_hash="req-dup-1",
            )
    finally:
        e.close()


def test_adopt_scope_raises_validation_error_not_assert(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        with pytest.raises(CoreValidationError):
            e.adopt_scope(
                scope=proposal["scope"],
                implementation_stages=[],  # empty
                action_id="act-val-1",
                request_hash="req-val-1",
            )
    finally:
        e.close()


def test_adopt_scope_raises_precondition_error_not_assert(configured):
    root, config = configured
    stub = Stub()
    e = Engine(root, launcher=stub)
    config["stages"] = ["plan"]
    e.initialize(config)
    try:
        # Paused without a plan gate
        e.owner_decision("pause", {"reason": "Paused before review"})
        with pytest.raises(PreconditionError):
            e.adopt_scope(
                scope=_sample_scope(),
                implementation_stages=["1"],
                action_id="act-prec-1",
                request_hash="req-prec-1",
            )
    finally:
        e.close()


def test_adopt_scope_scope_must_match_proposal(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        different_scope = deepcopy(proposal["scope"])
        different_scope["requirements"] = ["R2: completely different"]
        with pytest.raises(CoreValidationError):
            e.adopt_scope(
                scope=different_scope,
                implementation_stages=["1"],
                action_id="act-diff-1",
                request_hash="req-diff-1",
            )
    finally:
        e.close()


# ==============================================================================
# 8. Deduplication Tests
# ==============================================================================


def _make_sample_token(token_id="tok-001", gate_id="gate-001", stage="1", scope="PLAN"):
    return {
        "token_id": token_id,
        "gate_id": gate_id,
        "schema_version": 2,
        "plan_revision_hash": "p" * 64,
        "scope_hash": "s" * 64,
        "roles_hash": "r" * 64,
        "scope": scope,
        "work_item": "test-work",
        "repository_id": "/repo",
        "branch": "test",
        "stages": [stage],
        "status": "ISSUED",
    }


def test_dedup_approval_neither_row_nor_event_returns_none(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    token = _make_sample_token("tok-new")
    try:
        result = deduplicate_action(
            action_id=None,
            request_hash="req-hash",
            token_id="tok-new",
            submitted_token=token,
            store=store,
            engine=engine,
        )
        assert result is None
    finally:
        store.close()


def test_dedup_approval_event_without_row_raises_reconciliation(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    token = _make_sample_token("tok-orphan-event")
    try:
        # Write event without grant row
        store.event("grant-orphan", "grant", token)
        with pytest.raises(GrantReconciliationRequired):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-orphan-event",
                submitted_token=token,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_row_without_event_raises_reconciliation(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    token = _make_sample_token("tok-orphan-row")
    try:
        # Write grant row without event
        store.grant(token)
        with pytest.raises(GrantReconciliationRequired):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-orphan-row",
                submitted_token=token,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_changed_token_id_raises_conflict(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored = _make_sample_token("tok-base")
    store.grant(stored)
    store.event("grant-base", "grant", stored)
    submitted = deepcopy(stored)
    submitted["token_id"] = "tok-diff"
    try:
        with pytest.raises(CoreValidationError):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-base",
                submitted_token=submitted,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_changed_gate_id_raises_conflict(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored = _make_sample_token("tok-base", gate_id="gate-old")
    store.grant(stored)
    store.event("grant-base", "grant", stored)
    submitted = deepcopy(stored)
    submitted["gate_id"] = "gate-new"
    try:
        with pytest.raises(DuplicateKeyConflict):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-base",
                submitted_token=submitted,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_changed_scope_hash_raises_conflict(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored = _make_sample_token("tok-base")
    store.grant(stored)
    store.event("grant-base", "grant", stored)
    submitted = deepcopy(stored)
    submitted["scope_hash"] = "changed" * 9 + "1"
    try:
        with pytest.raises(DuplicateKeyConflict):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-base",
                submitted_token=submitted,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_changed_plan_revision_hash_raises_conflict(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored = _make_sample_token("tok-base")
    store.grant(stored)
    store.event("grant-base", "grant", stored)
    submitted = deepcopy(stored)
    submitted["plan_revision_hash"] = "diff_plan" * 7 + "1"
    try:
        with pytest.raises(DuplicateKeyConflict):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-base",
                submitted_token=submitted,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_changed_roles_hash_raises_conflict(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored = _make_sample_token("tok-base")
    store.grant(stored)
    store.event("grant-base", "grant", stored)
    submitted = deepcopy(stored)
    submitted["roles_hash"] = "diff_roles" * 6 + "1234"
    try:
        with pytest.raises(DuplicateKeyConflict):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-base",
                submitted_token=submitted,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_changed_scope_string_raises_conflict(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored = _make_sample_token("tok-base", scope="PLAN")
    store.grant(stored)
    store.event("grant-base", "grant", stored)
    submitted = deepcopy(stored)
    submitted["scope"] = "COMMIT"
    try:
        with pytest.raises(DuplicateKeyConflict):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-base",
                submitted_token=submitted,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_changed_work_item_raises_conflict(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored = _make_sample_token("tok-base")
    store.grant(stored)
    store.event("grant-base", "grant", stored)
    submitted = deepcopy(stored)
    submitted["work_item"] = "diff-work-item"
    try:
        with pytest.raises(DuplicateKeyConflict):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-base",
                submitted_token=submitted,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_changed_repository_id_raises_conflict(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored = _make_sample_token("tok-base")
    store.grant(stored)
    store.event("grant-base", "grant", stored)
    submitted = deepcopy(stored)
    submitted["repository_id"] = "/different/repo"
    try:
        with pytest.raises(DuplicateKeyConflict):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-base",
                submitted_token=submitted,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_changed_branch_raises_conflict(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored = _make_sample_token("tok-base")
    store.grant(stored)
    store.event("grant-base", "grant", stored)
    submitted = deepcopy(stored)
    submitted["branch"] = "different-branch"
    try:
        with pytest.raises(DuplicateKeyConflict):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-base",
                submitted_token=submitted,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_changed_stages_raises_conflict(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored = _make_sample_token("tok-base", stage="1")
    store.grant(stored)
    store.event("grant-base", "grant", stored)
    submitted = deepcopy(stored)
    submitted["stages"] = ["1", "2"]
    try:
        with pytest.raises(DuplicateKeyConflict):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-base",
                submitted_token=submitted,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_inconsistent_row_event_raises_reconciliation(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored_row = _make_sample_token("tok-base")
    store.grant(stored_row)
    stored_event = deepcopy(stored_row)
    stored_event["scope_hash"] = "corrupted_event" * 4 + "1234"
    store.event("grant-base", "grant", stored_event)
    try:
        with pytest.raises(GrantReconciliationRequired):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-base",
                submitted_token=stored_row,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_both_consistent_calls_synchronize_checkpoint(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    token = _make_sample_token("tok-consistent")
    store.grant(token)
    store.event("grant-cons", "grant", token)
    try:
        res = deduplicate_action(
            action_id=None,
            request_hash="req-hash",
            token_id="tok-consistent",
            submitted_token=token,
            store=store,
            engine=engine,
        )
        assert res["status"] == "already_complete"
        assert res["source"] == "grant_event"
        engine._synchronize_checkpoint.assert_called_once()
    finally:
        store.close()


def test_dedup_reused_token_with_changed_inputs_rejected(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored = _make_sample_token("tok-reuse")
    store.grant(stored)
    store.event("grant-reuse", "grant", stored)
    submitted = deepcopy(stored)
    submitted["roles_hash"] = "changed_roles" * 4 + "12345678"
    try:
        with pytest.raises(DuplicateKeyConflict):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-reuse",
                submitted_token=submitted,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_mismatched_lookup_id_raises_validation_error(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    token = _make_sample_token("tok-real-id")
    try:
        with pytest.raises(CoreValidationError):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-wrong-lookup-id",
                submitted_token=token,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_approval_canonical_equality_catches_extra_fields(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    stored = _make_sample_token("tok-extra")
    store.grant(stored)
    store.event("grant-extra", "grant", stored)
    submitted = deepcopy(stored)
    submitted["unplanned_future_field"] = "value"
    try:
        with pytest.raises(DuplicateKeyConflict):
            deduplicate_action(
                action_id=None,
                request_hash="req-hash",
                token_id="tok-extra",
                submitted_token=submitted,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_non_approval_reads_payload_not_data(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    try:
        store.event(
            "owner-action-1",
            "pause",
            {"action_id": "act-non-app-1", "request_hash": "req-hash-1", "reason": "test"},
        )
        res = deduplicate_action(
            action_id="act-non-app-1",
            request_hash="req-hash-1",
            token_id=None,
            submitted_token=None,
            store=store,
            engine=engine,
        )
        assert res["status"] == "already_complete"
        assert res["event_id"] == "owner-action-1"
        engine._synchronize_checkpoint.assert_called_once()
    finally:
        store.close()


def test_dedup_non_approval_missing_request_hash_rejected(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    try:
        store.event(
            "owner-action-2",
            "pause",
            {"action_id": "act-missing-hash", "reason": "test"},
        )
        with pytest.raises(DuplicateKeyConflict):
            deduplicate_action(
                action_id="act-missing-hash",
                request_hash="submitted-hash",
                token_id=None,
                submitted_token=None,
                store=store,
                engine=engine,
            )
    finally:
        store.close()


def test_dedup_non_approval_calls_synchronize_checkpoint(tmp_path):
    store = Store(tmp_path / "checkpoints.db")
    engine = MagicMock()
    try:
        store.event(
            "owner-action-3",
            "pause",
            {"action_id": "act-sync-test", "request_hash": "hash-sync", "reason": "test"},
        )
        deduplicate_action(
            action_id="act-sync-test",
            request_hash="hash-sync",
            token_id=None,
            submitted_token=None,
            store=store,
            engine=engine,
        )
        engine._synchronize_checkpoint.assert_called_once()
    finally:
        store.close()


# ==============================================================================
# 9. Role Reconfiguration Defaults Preservation
# ==============================================================================


def test_reconfigure_role_preserves_effort_and_reason_defaults(configured):
    root, config = configured
    stub = Stub()
    e = Engine(root, launcher=stub)
    try:
        e.initialize(config)
        e.run()
        e.owner_decision("pause", {"reason": "Reconfiguring"})

        # Mock binary and prompt for codex
        bin_dir = root / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        fake_codex = bin_dir / "codex"
        fake_codex.write_text("#!/bin/sh\necho 'codex 0.153.0-alpha.5'\n")
        fake_codex.chmod(0o755)

        with patch("engine.bytes_hash", return_value="f" * 64):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="codex 0.153.0-alpha.5\n", stderr=""
                )
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("os.access", return_value=True):
                        e.reconfigure_role(
                            role="architect",
                            tool="codex",
                            model="gpt-5",
                            # effort and reason omitted -> defaults used
                        )
                        events = e.store.events()
                        reconfig_ev = [ev for ev in events if ev["kind"] == "role_reconfigured"][-1]
                        assert reconfig_ev["payload"]["reason"] == "Owner role reconfiguration"
                        assert reconfig_ev["payload"]["new_pin"]["effort"] is None
    finally:
        e.close()


def test_cli_callers_unaffected(configured):
    root, config = configured
    stub = Stub()
    e = Engine(root, launcher=stub)
    try:
        e.initialize(config)
        e.run()
        e.owner_decision("pause", {"reason": "CLI pause"})
        evs = e.store.events()
        pause_ev = [ev for ev in evs if ev["kind"] == "pause"][-1]
        assert "action_id" not in pause_ev["payload"]
    finally:
        e.close()


# ==============================================================================
# 10. Architect Scope-Proposal Output Contract
# ==============================================================================


def test_orchestrator_extracts_scope_proposal_at_collection(configured):
    root, config = configured
    config["stages"] = ["plan"]
    proposal = _sample_proposal(["1", "2"])
    plan_text = f"# Architect Plan\n\n```scope-proposal\n{json.dumps(proposal)}\n```\n"

    stub = ProposalStub(outcomes={
        "architect": {
            "verdict": "PASS",
            "wire": {"plan_text": plan_text, "explanation": "Architect complete"},
        },
    })
    e = Engine(root, launcher=stub)
    try:
        e.initialize(config)
        e.run()  # collects architect
        outbox_file = root / "docs/ai/work-items/test-work/outbox/scope-proposal.json"
        assert outbox_file.exists()
        extracted = json.loads(outbox_file.read_text())
        assert extracted["schema"] == "scope-proposal/v1"
        assert extracted["implementation_stages"] == ["1", "2"]
    finally:
        e.close()


def test_invalid_proposal_parks_with_error(configured):
    root, config = configured
    config["stages"] = ["plan"]
    # Invalid stages: duplicate stages
    invalid_proposal = _sample_proposal(["1", "1"])
    plan_text = f"# Plan\n\n```scope-proposal\n{json.dumps(invalid_proposal)}\n```\n"

    stub = ProposalStub(outcomes={
        "architect": {
            "verdict": "PASS",
            "wire": {"plan_text": plan_text, "explanation": "Invalid"},
        },
    })
    e = Engine(root, launcher=stub)
    try:
        e.initialize(config)
        v = e.run()
        assert v["status"] == "PAUSED"
        assert v["pause_reason"] == "RECONCILIATION_REQUIRED"
    finally:
        e.close()


def test_missing_proposal_blocks_adoption(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        proposal_file = (
            root / "docs/ai/work-items" / config["work_item"] / "outbox/scope-proposal.json"
        )
        if proposal_file.exists():
            proposal_file.unlink()
        with pytest.raises(CoreValidationError):
            e.adopt_scope(
                scope=_sample_scope(),
                implementation_stages=["1"],
                action_id="act-missing-outbox",
                request_hash="req-missing-outbox",
            )
    finally:
        e.close()


# ==============================================================================
# 11. End-to-End, Failure-Injection & Concurrency
# ==============================================================================


def test_adopt_scope_candidate_failure_rolls_back_all(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        with patch("engine.freeze", side_effect=OSError("Disk write failed")):
            with pytest.raises(OSError):
                e.adopt_scope(
                    scope=proposal["scope"],
                    implementation_stages=proposal["implementation_stages"],
                    action_id="act-fail-1",
                    request_hash="req-fail-1",
                )
        # Verify no scope_adopted event was inserted
        events = e.store.events()
        assert not any(ev["kind"] == "scope_adopted" for ev in events)
        # Verify config was not changed in SQLite
        meta_cfg = e.store.meta("config")
        assert meta_cfg["stages"] == ["plan"]
    finally:
        e.close()


def test_adopt_scope_crash_after_commit_recovery_restores_config_and_checkpoint(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        # Simulate normal atomic commit
        new_cfg = deepcopy(e.config)
        new_cfg["stages"] = ["plan", "1"]
        new_cfg["scope"] = proposal["scope"]
        new_cfg["scope_hash"] = digest(proposal["scope"])
        event_id, seq = e.store.adopt_scope_atomic(
            new_config=new_cfg,
            action_id="act-crash-test",
            scope_hash=new_cfg["scope_hash"],
            implementation_stages=["1"],
            candidate_meta={"candidate_id": "c" * 64},
            request_hash="req-crash",
        )
        # Process crashes here before e._synchronize_checkpoint() or e.config reload
    finally:
        e.close()

    # Recovery: new Engine starts up and deduplicate_action synchronizes checkpoint
    e_recovered = Engine(root)
    try:
        res = deduplicate_action(
            action_id="act-crash-test",
            request_hash="req-crash",
            token_id=None,
            submitted_token=None,
            engine=e_recovered,
        )
        assert res["status"] == "already_complete"
        v = e_recovered.view()
        assert v["stage"] == "1"
        assert e_recovered.config["stages"] == ["plan", "1"]
    finally:
        e_recovered.close()


def test_lost_subprocess_response_recovered_via_action_id(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        v = e.adopt_scope(
            scope=proposal["scope"],
            implementation_stages=proposal["implementation_stages"],
            action_id="act-lost-resp",
            request_hash="hash-lost-resp",
        )
        # Duplicate submission with same action_id and request_hash
        dedup = deduplicate_action(
            action_id="act-lost-resp",
            request_hash="hash-lost-resp",
            token_id=None,
            submitted_token=None,
            store=e.store,
            engine=e,
        )
        assert dedup["status"] == "already_complete"
    finally:
        e.close()


def test_idempotency_survives_restart(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        e.adopt_scope(
            scope=proposal["scope"],
            implementation_stages=proposal["implementation_stages"],
            action_id="act-persist-test",
            request_hash="hash-persist-test",
        )
    finally:
        e.close()

    e_restarted = Engine(root)
    try:
        dedup = deduplicate_action(
            action_id="act-persist-test",
            request_hash="hash-persist-test",
            token_id=None,
            submitted_token=None,
            store=e_restarted.store,
            engine=e_restarted,
        )
        assert dedup["status"] == "already_complete"
    finally:
        e_restarted.close()


def test_duplicate_submission_under_lock_one_executes(configured):
    root, config = configured
    proposal = _sample_proposal(["1"])
    e = _setup_engine_at_plan_gate(root, config, proposal)
    try:
        # First execution succeeds
        v1 = e.adopt_scope(
            scope=proposal["scope"],
            implementation_stages=proposal["implementation_stages"],
            action_id="act-under-lock",
            request_hash="hash-under-lock",
        )
        assert v1["stage"] == "1"

        # Concurrent/duplicate call checks dedup under lock and returns early
        dedup = deduplicate_action(
            action_id="act-under-lock",
            request_hash="hash-under-lock",
            token_id=None,
            submitted_token=None,
            store=e.store,
            engine=e,
        )
        assert dedup["status"] == "already_complete"
    finally:
        e.close()


def test_e2e_task_creation_through_plan_approval_to_builder_dispatch_and_collection(configured):
    """End-to-end acceptance test:
    1. Initialize with stages=["plan"]
    2. Architect runs, proposes scope with ```scope-proposal
    3. Reviewer runs, reviews plan
    4. Workflow parks at PLAN gate
    5. adopt_scope() transitions stage from "plan" to "1", invalidating existing grants
    6. Workflow re-parks at stage 1 PLAN gate
    7. Owner approves with schema_version=2 PLAN token
    8. Builder is dispatched and completes
    9. Verifier runs and verifies
    """
    root, config = configured
    config["stages"] = ["plan"]
    proposal = _sample_proposal(["1"])
    plan_with_proposal = f"# System Architecture\n\n```scope-proposal\n{json.dumps(proposal)}\n```\n"

    stub = ProposalStub(outcomes={
        "architect": {
            "verdict": "PASS",
            "wire": {"plan_text": plan_with_proposal, "explanation": "Architectural plan"},
        },
        "reviewer": {
            "verdict": "PASS",
            "wire": {"explanation": "Review approved"},
        },
        "builder": {
            "verdict": "PASS",
            "wire": {"explanation": "Build completed"},
        },
        "verifier": {
            "verdict": "PASS",
            "wire": {"explanation": "Verification passed"},
        },
    })
    e = Engine(root, launcher=stub)
    try:
        # Step 1-4: Initialize and park at planning stage PLAN gate
        e.initialize(config)
        v = e.run()
        assert v["stage"] == "plan"
        assert v["gate"]["scope"] == "PLAN"
        assert v["status"] == "PLAN_SUBMITTED"

        # Step 5-6: Adopt scope to stage "1"
        v = e.adopt_scope(
            scope=proposal["scope"],
            implementation_stages=proposal["implementation_stages"],
            action_id="act-e2e-adopt",
            request_hash="hash-e2e-adopt",
        )
        assert v["stage"] == "1"
        assert v["gate"]["scope"] == "PLAN"
        assert v["status"] == "PLAN_SUBMITTED"

        # Step 7: Owner approves plan for stage 1
        tok = plan_token(e, token_id="tok-e2e-approved")
        tok["stages"] = ["1"]
        v = e.approve(tok)

        # Step 8-9: Builder and verifier run and complete
        assert v["stage"] == "1"
        assert v["status"] == "VERIFIED_FOR_RELEASE"
        assert v["gate"]["scope"] == "COMMIT"
    finally:
        e.close()


# ==============================================================================
# 12. Subprocess Integration, Read-Only Privacy Projections & Concurrent Locking
# ==============================================================================


def test_subprocess_help_returns_zero():
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "-m", "orchestrator.dashboard_api", "--help"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Dashboard Subprocess API" in proc.stdout


def test_subprocess_state_read_only_allowlisted_projection(configured):
    root, config = configured
    repo_root = Path(__file__).resolve().parents[2]
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
    finally:
        e.close()

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.dashboard_api",
            "--root",
            str(root),
            "--action",
            "state",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    data = json.loads(proc.stdout)
    assert data["ok"] is True
    res = data["result"]
    assert "work_item" in res
    assert "stage" in res
    assert "status" in res
    # Ensure allowlisted projection hides host paths
    assert "root" not in res
    assert str(root) not in json.dumps(res)


def test_subprocess_plan_relative_and_sanitized(configured):
    root, config = configured
    repo_root = Path(__file__).resolve().parents[2]
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
    finally:
        e.close()

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.dashboard_api",
            "--root",
            str(root),
            "--action",
            "plan",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    data = json.loads(proc.stdout)
    assert data["ok"] is True
    res = data["result"]
    assert "plan_path" in res
    # Must be relative path, not absolute
    assert not Path(res["plan_path"]).is_absolute()
    # No host root leaked in plan text
    assert str(root) not in res["plan_text"]


def test_subprocess_bootstrap_task_branch(configured):
    root, config = configured
    repo_root = Path(__file__).resolve().parents[2]
    task_branch = "task/subproc-bootstrap-item"
    git(root, "checkout", "-b", task_branch)

    cfg = deepcopy(config)
    cfg["branch"] = task_branch
    cfg["base_commit"] = git(root, "rev-parse", "HEAD").decode().strip()

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.dashboard_api",
            "--root",
            str(root),
            "--action",
            "initialize",
            "--payload",
            json.dumps({"config": cfg}),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    data = json.loads(proc.stdout)
    assert data["ok"] is True
    assert data["result"]["stage"] == cfg.get("stage", cfg["stages"][0])


def test_subprocess_run_action_executes_without_type_error(configured):
    root, config = configured
    repo_root = Path(__file__).resolve().parents[2]
    git(root, "checkout", "-B", config["branch"])
    for r in config["roles"]:
        role_name = r if r in ("architect", "reviewer", "builder", "verifier") else "ai-reviewer"
        config["roles"][r]["prompt_sha256"] = bytes_hash((root / "docs/ai/roles" / f"{role_name}.md").read_bytes())
    evidence_dir = root / f"docs/ai/work-items/{config['work_item']}/evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "phase-0-capabilities.json").write_text(
        json.dumps({"phase_exit": "PASSED_WITH_OWNER_DIRECTIVE"})
    )
    git(root, "add", ".")
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-m", "add capability evidence")
    config["base_commit"] = git(root, "rev-parse", "HEAD").decode().strip()
    stub = Stub()
    e = Engine(root, launcher=stub)
    try:
        e.initialize(config)
    finally:
        e.close()

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.dashboard_api",
            "--root",
            str(root),
            "--action",
            "run",
            "--payload",
            json.dumps({}),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Stderr: {proc.stderr}\nStdout: {proc.stdout}"
    data = json.loads(proc.stdout)
    assert data["ok"] is True


def test_state_and_plan_projections_do_not_mutate_state_or_files(configured):
    root, config = configured
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
    finally:
        e.close()

    runtime_path = root / "orchestrator/var"
    db_path = runtime_path / "checkpoints.db"
    state_json = root / f"docs/ai/work-items/{config['work_item']}/STATE.json"
    roles_json = root / "orchestrator/roles.json"

    db_mtime_before = db_path.stat().st_mtime_ns
    state_mtime_before = state_json.stat().st_mtime_ns
    roles_mtime_before = roles_json.stat().st_mtime_ns
    db_hash_before = bytes_hash(db_path.read_bytes())

    # Invoke read-only projections
    st = get_state_projection(root)
    pl = get_plan_projection(root)

    assert st["status"] == "DRAFT"
    assert "plan_path" in pl

    assert db_path.stat().st_mtime_ns == db_mtime_before
    assert bytes_hash(db_path.read_bytes()) == db_hash_before
    assert state_json.stat().st_mtime_ns == state_mtime_before
    assert roles_json.stat().st_mtime_ns == roles_mtime_before


def test_plan_read_rejects_outside_root_paths(configured, tmp_path):
    root, config = configured
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
    finally:
        e.close()

    conn = sqlite3.connect(root / "orchestrator/var/checkpoints.db")
    try:
        conn.execute(
            "INSERT OR REPLACE INTO workflow_meta (key, value) VALUES ('plan_artifact', '\"/etc/hostname\"')"
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(PreconditionError, match="escapes worktree boundary"):
        get_plan_projection(root)


def test_plan_read_rejects_symlink_escapes(configured, tmp_path):
    root, config = configured
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
    finally:
        e.close()

    outside_file = tmp_path / "secret_outside.md"
    outside_file.write_text("TOP SECRET")
    symlink_file = root / "symlink_plan.md"
    symlink_file.symlink_to(outside_file)

    conn = sqlite3.connect(root / "orchestrator/var/checkpoints.db")
    try:
        conn.execute(
            "INSERT OR REPLACE INTO workflow_meta (key, value) VALUES ('plan_artifact', '\"symlink_plan.md\"')"
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(PreconditionError, match="escapes worktree boundary"):
        get_plan_projection(root)


def test_plan_endpoint_rejects_arbitrary_in_worktree_file_selection(configured, tmp_path):
    repo_root = Path(__file__).resolve().parents[2]

    # A) Uninitialized worktree: payload plan_path cannot read files
    uninitialized_root = tmp_path / "uninitialized_worktree"
    uninitialized_root.mkdir()
    (uninitialized_root / "core.py").write_text("SENSITIVE_UNINITIALIZED_SOURCE = 99999")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.dashboard_api",
            "--root",
            str(uninitialized_root),
            "--action",
            "plan",
            "--payload",
            json.dumps({"plan_path": "core.py"}),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["ok"] is True
    assert data["result"]["plan_text"] == ""
    assert data["result"]["plan_path"] == ""
    assert "SENSITIVE_UNINITIALIZED_SOURCE" not in proc.stdout

    # B) Initialized worktree: payload plan_path cannot override approved plan
    root, config = configured
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
    finally:
        e.close()

    (root / "private_source.py").write_text("PRIVATE_WORKTREE_CODE = 88888")

    proc2 = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.dashboard_api",
            "--root",
            str(root),
            "--action",
            "plan",
            "--payload",
            json.dumps({"plan_path": "private_source.py"}),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert proc2.returncode == 0
    data2 = json.loads(proc2.stdout)
    assert data2["ok"] is True
    assert data2["result"]["plan_path"] == config["plan_path"]
    assert "PRIVATE_WORKTREE_CODE" not in proc2.stdout


def test_html_parser_variants_and_encoded_urls_sanitization():
    from dashboard_api import sanitize_plan_text

    raw_html_variants = (
        "<img/src=x onerror=alert(1)>\n"
        "<a href=\"&#106;avascript:alert(1)\">click</a>\n"
        "<svg/onload=alert(1)>\n"
        "<iframe/src=\"evil.com\"></iframe>\n"
        "<body/onload=alert(1)>\n"
        "Normal math: x < 5 and y > 3"
    )
    clean = sanitize_plan_text(raw_html_variants)
    assert "<img" not in clean
    assert "&lt;img/src=x onerror=alert(1)&gt;" in clean
    assert "<a href=" not in clean
    assert '&lt;a href="&#106;avascript:alert(1)"&gt;' in clean
    assert "<svg" not in clean
    assert "&lt;svg/onload=alert(1)&gt;" in clean
    assert "<iframe" not in clean
    assert '&lt;iframe/src="evil.com"&gt;' in clean
    assert "<body" not in clean
    assert "&lt;body/onload=alert(1)&gt;" in clean
    assert "x < 5 and y > 3" in clean

    # Markdown links with encoded schemes
    md_encoded_links = (
        "[click1](javascript:alert(1))\n"
        "[click2](&#106;avascript:alert(1))\n"
        "[click3](javascript&#x3a;alert(1))\n"
        "[click4](<javascript:alert(1)>)\n"
        "[click5](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==)\n"
        "[click6](vbscript:alert(1))\n"
        "[safe1](https://example.com/guide?id=123)\n"
        "[safe2](/docs/guide.md)\n"
        "[safe3](#section-heading)\n"
        "[click_trailing](javascript:alert(1))next\n"
        "[click_ref][target]\n\n"
        "[target]: javascript:alert(1)\n"
        "[target_angle]: <javascript:alert(1)> \"Malicious Title\"\n"
        "[target_safe]: https://example.com/safe \"Safe Title\"\n"
        "<javascript:alert(1)>\n"
        "[![alt](javascript:alert(2))](https://example.com)\n"
        "[![alt](https://example.com/img.png)](javascript:alert(1))\n"
    )
    clean_md = sanitize_plan_text(md_encoded_links)
    assert "[click1](#blocked)" in clean_md
    assert "[click2](#blocked)" in clean_md
    assert "[click3](#blocked)" in clean_md
    assert "[click4](#blocked)" in clean_md
    assert "[click5](#blocked)" in clean_md
    assert "[click6](#blocked)" in clean_md
    assert "[safe1](https://example.com/guide?id=123)" in clean_md
    assert "[safe2](/docs/guide.md)" in clean_md
    assert "[safe3](#section-heading)" in clean_md
    assert "[click_trailing](#blocked)next" in clean_md
    assert "[click_ref][target]" in clean_md
    assert "[target]: #blocked" in clean_md
    assert "[target_angle]: #blocked \"Malicious Title\"" in clean_md
    assert "[target_safe]: https://example.com/safe \"Safe Title\"" in clean_md
    assert "&lt;javascript:alert(1)&gt;" in clean_md
    assert "[![alt](#blocked)](https://example.com)" in clean_md
    assert "[![alt](https://example.com/img.png)](#blocked)" in clean_md


def test_json_formatted_credentials_redaction():
    from dashboard_api import sanitize_plan_text

    text = (
        '# Configuration Guide\n\n'
        '```json\n'
        '{\n'
        '  "password": "demo-secret-123",\n'
        '  "api_key": "sk-test-live-key-456",\n'
        '  "client_secret": "my-client-secret-789",\n'
        '  "token": "token-xyz-000",\n'
        '  "token_id": "tok-grant-persisted-123"\n'
        '}\n'
        '```\n'
        'Inline settings: password = "demo-secret-123", secret_key: "demo-secret-123", Bearer tok-bearer-12345678.\n'
        'Quoted credentials with spaces: {"password": "alpha beta gamma"}\n'
        'Quoted credentials with punctuation: password: "alpha, beta; gamma"\n'
        'Quoted credentials with escaped quotes: {"secret": "alpha \\"beta\\" gamma"}\n'
        'Bilingual Arabic:\n'
        '# خطة العمل\n'
        'يرجى التأكد من حماية كلمة المرور وعدم نشرها علناً.'
    )
    clean = sanitize_plan_text(text)
    assert "demo-secret-123" not in clean
    assert "sk-test-live-key-456" not in clean
    assert "my-client-secret-789" not in clean
    assert "token-xyz-000" not in clean
    assert "tok-bearer-12345678" not in clean
    assert "alpha beta gamma" not in clean
    assert "beta gamma" not in clean
    assert "alpha, beta; gamma" not in clean
    assert "alpha \\\"beta\\\" gamma" not in clean
    assert '"password": "[REDACTED_CREDENTIAL]"' in clean
    assert '"api_key": "[REDACTED_CREDENTIAL]"' in clean
    assert '"client_secret": "[REDACTED_CREDENTIAL]"' in clean
    assert 'Bearer [REDACTED_CREDENTIAL]' in clean
    assert '{"password": "[REDACTED_CREDENTIAL]"}' in clean
    assert 'password: "[REDACTED_CREDENTIAL]"' in clean
    assert '{"secret": "[REDACTED_CREDENTIAL]"}' in clean
    assert '"token_id": "tok-grant-persisted-123"' in clean
    assert "خطة العمل" in clean
    assert "يرجى التأكد من حماية كلمة المرور" in clean
    assert "[REDACTED_ARABIC]" not in clean


def test_sensitive_pause_reasons_use_fixed_public_categories(configured):
    from dashboard_api import categorize_pause_reason

    # Test categorization helper directly
    assert categorize_pause_reason("OWNER: password=demo-secret-123") == "OPERATOR_PAUSED"
    assert categorize_pause_reason("operator paused with token=secret123") == "OPERATOR_PAUSED"
    assert categorize_pause_reason("Budget limit 50000 reached") == "BUDGET_EXHAUSTED"
    assert categorize_pause_reason("Approval gate pending: plan review") == "GATE_PENDING"
    assert categorize_pause_reason("Verification failed: lint error") == "VERIFICATION_FAILED"
    assert categorize_pause_reason("Fatal exception in /private/dir/file.py") == "EXECUTION_ERROR"
    assert categorize_pause_reason(None) is None

    # Test state projection excludes sensitive pause reasons
    root, config = configured
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
        view = e.view()
        state = e._prepare({"view": view})
        state["view"]["pause_reason"] = "OWNER: password=demo-secret-123"
        e.graph.update_state(e.graph_config, state, as_node="collect")
    finally:
        e.close()

    st = get_state_projection(root)
    assert st["pause_reason"] == "OPERATOR_PAUSED"
    serialized = json.dumps(st)
    assert "password" not in serialized
    assert "demo-secret-123" not in serialized


def test_missing_capability_evidence_fails_preflight_without_source_fallback(tmp_path):
    empty_worktree = tmp_path / "empty_worktree"
    empty_worktree.mkdir()
    res = check_approved_capabilities(None, worktree=empty_worktree)
    assert res.ok is False
    assert "Missing evidence" in res.message
    # Must NOT have fallen back to source repo
    assert str(empty_worktree) in res.message


def test_state_projection_hides_nested_private_state(configured):
    root, config = configured
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
        view = e.view()
        state = e._prepare({"view": view})
        state["view"]["gate"] = {
            "gate_id": "gate-secret-12345",
            "scope": "PLAN",
            "plan_hash": "a" * 64,
        }
        state["view"]["approval_refs"] = ["ref-secret-token-123"]
        state["view"]["stages"]["1"] = {
            "status": "RUNNING",
            "sub_status": "DISPATCHING",
            "evidence_refs": ["private/evidence.json"],
            "sha256": "b" * 64,
            "candidate_id": "cand-secret-999",
        }
        state["view"]["pause_reason"] = f"Halted at {root}/secret/path.py"
        e.graph.update_state(e.graph_config, state, as_node="collect")
    finally:
        e.close()

    st = get_state_projection(root)
    # Check internal hashes and metadata are omitted
    assert "plan_revision_hash" not in st
    assert "roles_hash" not in st
    assert "scope_hash" not in st
    assert "approval_refs" not in st
    assert "cursor" not in st
    assert "revision" not in st
    assert "completed_dependencies" not in st

    # Check gate_id is NOT exposed
    assert st["gate"] == {"scope": "PLAN"}
    assert "gate_id" not in (st["gate"] or {})

    # Check stages do not expose private details
    stg1 = st["stages"]["1"]
    assert stg1["status"] == "RUNNING"
    assert stg1["sub_status"] == "DISPATCHING"
    assert "evidence_refs" not in stg1
    assert "sha256" not in stg1
    assert "candidate_id" not in stg1

    # Check pause_reason is categorized into fixed public category
    assert st["pause_reason"] == "EXECUTION_ERROR"
    assert str(root) not in (st["pause_reason"] or "")


def test_sanitized_error_masks_external_paths(tmp_path):
    root = tmp_path / "worktree"
    root.mkdir()
    exc = WorkflowError("Failed reading /tmp/other-project/private.txt: access denied")
    res = sanitize_error(exc, root)

    assert "support_id" in res
    assert res["support_id"].startswith("ERR-")

    assert res["error"] == "Workflow execution error"
    assert res["error_type"] == "WorkflowError"

    serialized = json.dumps(res)
    assert "/tmp/other-project/private.txt" not in serialized
    assert "/tmp" not in serialized

    from dashboard_api import strip_paths
    raw = "Error logged in /tmp/other-project/private.txt during execution"
    stripped = strip_paths(raw, root=root)
    assert "/tmp/other-project/private.txt" not in stripped
    assert "[PATH]" in stripped


def test_plan_projection_preserves_legitimate_arabic(configured):
    root, config = configured
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
    finally:
        e.close()

    arabic_text = (
        "# خطة عمل المشروع\n\n"
        "## الأهداف والمتطلبات\n"
        "- دعم اللغة العربية بشكل كامل ودقيق.\n"
        "- التحقق من صحة البيانات المالية والمحاسبية.\n\n"
        "Bilingual requirement: Arabic and English support."
    )
    (root / config["plan_path"]).write_text(arabic_text, encoding="utf-8")

    proj = get_plan_projection(root)
    assert "خطة عمل المشروع" in proj["plan_text"]
    assert "الأهداف والمتطلبات" in proj["plan_text"]
    assert "دعم اللغة العربية" in proj["plan_text"]
    assert "Bilingual requirement" in proj["plan_text"]
    assert "[REDACTED_ARABIC]" not in proj["plan_text"]


def test_plan_projection_sanitizes_unsafe_html(configured):
    root, config = configured
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
    finally:
        e.close()

    unsafe_content = (
        "# Implementation Plan\n\n"
        "<script>alert('xss')</script>\n"
        "<iframe src=\"https://evil.example.com\"></iframe>\n"
        "<img src=\"valid.png\" onerror=\"alert('exploit')\">\n"
        "<img/src=x onerror=alert(1)>\n"
        "<a href=\"&#106;avascript:alert(1)\">click</a>\n"
        "<object data=\"payload.swf\"></object>\n"
        "Normal text with **bold** and *italic*.\n"
    )
    (root / config["plan_path"]).write_text(unsafe_content, encoding="utf-8")

    proj = get_plan_projection(root)
    text = proj["plan_text"]

    # Dangerous tags must be escaped
    assert "<script>" not in text
    assert "</script>" not in text
    assert "&lt;script&gt;" in text
    assert "&lt;/script&gt;" in text

    assert "<iframe" not in text
    assert "&lt;iframe" in text

    assert "<object" not in text
    assert "&lt;object" in text

    # Event handlers and javascript URIs neutralized
    assert '<img src="valid.png" onerror=' not in text
    assert '<img/src=x onerror=' not in text
    assert '&lt;img/src=x onerror=alert(1)&gt;' in text
    assert '<a href=' not in text
    assert '&lt;a href="&#106;avascript:alert(1)"&gt;' in text

    # Normal text preserved
    assert "Normal text with **bold** and *italic*." in text


def test_concurrent_subprocess_locking_serializes_mutations(configured):
    root, config = configured
    repo_root = Path(__file__).resolve().parents[2]
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
    finally:
        e.close()

    # Launch two subprocesses attempting to execute pause concurrently under the same lock
    payload1 = json.dumps({"action_id": "act-conc-1", "request_hash": "hash-conc-1", "reason": "pause 1"})
    payload2 = json.dumps({"action_id": "act-conc-2", "request_hash": "hash-conc-2", "reason": "pause 2"})

    p1 = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "orchestrator.dashboard_api",
            "--root",
            str(root),
            "--action",
            "pause",
            "--payload",
            payload1,
        ],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    p2 = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "orchestrator.dashboard_api",
            "--root",
            str(root),
            "--action",
            "pause",
            "--payload",
            payload2,
        ],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    out1, err1 = p1.communicate(timeout=20)
    out2, err2 = p2.communicate(timeout=20)

    # Both must complete without crashing or corrupting SQLite
    assert p1.returncode == 0, f"p1 failed: stderr={err1}, stdout={out1}"
    assert p2.returncode == 0, f"p2 failed: stderr={err2}, stdout={out2}"
    d1 = json.loads(out1)
    d2 = json.loads(out2)
    assert d1["ok"] is True
    assert d2["ok"] is True

    # Checkpoints DB remains completely sound
    e_verify = Engine(root)
    try:
        assert e_verify.store.integrity()
        assert e_verify.view()["status"] == "PAUSED"
    finally:
        e_verify.close()


def test_architect_role_prompt_sha256_matches_pinned_roles_json():
    root = Path(__file__).resolve().parents[2]
    role_file = root / "docs/ai/roles/architect.md"
    roles_json = json.loads((root / "orchestrator/roles.json").read_text())
    assert bytes_hash(role_file.read_bytes()) == roles_json["architect"]["prompt_sha256"]


def test_architect_dispatch_prompt_includes_scope_proposal_instructions(configured):
    root, config = configured
    config["stages"] = ["plan"]
    e = Engine(root, launcher=Stub())
    try:
        e.initialize(config)
        view = e.view()
        assert view["stage"] == "plan"
        state = e._prepare({"view": view})
        job_id = state["view"]["active_jobs"][0]
        job = e.store.job(job_id)
        spec = json.loads(Path(job["spec_path"]).read_text())
        assert "PLANNING STAGE ARCHITECT INSTRUCTIONS" in spec["prompt"]
        assert "scope-proposal" in spec["prompt"]
    finally:
        e.close()

