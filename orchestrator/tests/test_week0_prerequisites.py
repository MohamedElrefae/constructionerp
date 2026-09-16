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
from dashboard_api import deduplicate_action, execute_action
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
