"""Offline acceptance tests for the O01/O02 design prototypes.

These tests exercise ``engineering_control_contracts.provenance`` and
``engineering_control_contracts.operation_store`` only. Both modules are
test-only: a shared HMAC key and a single-host SQLite file prove stated
semantics, not production authentication, key custody, durability or
multi-writer consensus.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from engineering_control_contracts.contract import VERSION
from engineering_control_contracts.offline import Denied
from engineering_control_contracts.operation_store import (
    OperationConflict,
    OperationFenced,
    OperationNotFound,
    OperationStore,
    digest,
)
from engineering_control_contracts.provenance import (
    ProvenanceVerifier,
    TestAssertionIssuer,
    VerifiedPrincipal,
    sign,
)

NOW = datetime(2026, 11, 3, 10, 0, 0, tzinfo=timezone.utc)
KEY = b"offline-test-key"
KEY_ID = "k1"


# ---------------------------------------------------------------------------
# O01: provenance assertion semantics
# ---------------------------------------------------------------------------


def verifier(**kwargs):
    settings = dict(
        keys_by_issuer={"test-issuer": {KEY_ID: KEY}},
        trusted_issuers=("test-issuer",),
    )
    settings.update(kwargs)
    return ProvenanceVerifier(**settings)


def signer(**kwargs):
    settings = dict(keys={KEY_ID: KEY}, issuer="test-issuer", audience="engineering-control")
    settings.update(kwargs)
    return TestAssertionIssuer(**settings)


def verify(verifier_instance, envelope, **kwargs):
    expected = dict(
        expected_operation="decisions",
        expected_target="work-1",
        expected_request_hash="a" * 64,
    )
    expected.update(kwargs)
    return verifier_instance.verify(envelope, **expected)


def denied(code):
    return pytest.raises(Denied, match=f"^{code}$")


def test_human_decision_verifies_and_authorizes():
    envelope = signer().issue(now=NOW)
    principal = verify(verifier(), envelope, now=NOW)

    assert isinstance(principal, VerifiedPrincipal)
    assert principal.subject == "owner"
    assert principal.actor_class == "human"
    assert principal.capabilities == frozenset({"read", "decide", "lifecycle"})
    assert principal.job_id is None
    verify(verifier(), envelope, now=NOW)  # same envelope/request is a safe replay
    verifier().authorize(principal, "decide")


def test_verifier_does_not_accept_caller_built_principal_as_authentication():
    # VerifiedPrincipal is a value object; constructing one must not bypass the
    # verifier. This documents that only verify() produces accepted state.
    principal = VerifiedPrincipal(
        issuer="test-issuer",
        subject="owner",
        actor_class="human",
        project_id="project-1",
        work_item_id="work-1",
        capabilities=frozenset({"decide"}),
        auth_method="t3_sso",
        assurance="multi_factor",
        session_id="session-1",
        job_id=None,
        operation="decisions",
        target_id="work-1",
        request_hash="a" * 64,
        jti="jti-1",
        expires_at=NOW,
    )
    verifier().authorize(principal, "decide")  # authorization is a policy check, not identity proof


@pytest.mark.parametrize(
    "code,mutate",
    [
        ("unauthenticated", lambda claims: claims.update(subject="intruder")),
        ("unauthenticated", lambda claims: claims.update(capabilities=["read", "decide"])),
        ("unauthenticated", lambda claims: claims.update(request_hash="b" * 64)),
    ],
)
def test_tampered_claims_fail_signature(code, mutate):
    envelope = signer().issue(now=NOW)
    mutate(envelope["claims"])
    with denied(code):
        verify(verifier(), envelope, now=NOW)


def test_forged_signature_fails_signature():
    envelope = signer().issue(now=NOW)
    envelope["signature"] = sign(envelope["claims"], b"wrong-key")
    with denied("unauthenticated"):
        verify(verifier(), envelope, now=NOW)


def test_unknown_key_id_is_rejected():
    rogue = signer(keys={KEY_ID: KEY, "k9": b"other"})
    envelope = rogue.issue(now=NOW, key_id="k9")
    with denied("unauthenticated"):
        verify(verifier(), envelope, now=NOW)


def test_untrusted_issuer_is_rejected():
    envelope = signer(issuer="rogue-issuer").issue(now=NOW)
    with denied("unauthenticated"):
        verify(verifier(), envelope, now=NOW)


def test_audience_mismatch_is_rejected():
    envelope = signer(audience="some-other-service").issue(now=NOW)
    with denied("unauthenticated"):
        verify(verifier(), envelope, now=NOW)


def test_expired_assertion_is_rejected():
    envelope = signer().issue(now=NOW - timedelta(seconds=120), lifetime_seconds=30)
    with denied("unauthenticated"):
        verify(verifier(), envelope, now=NOW)


def test_assertion_lifetime_cap_is_enforced():
    envelope = signer().issue(now=NOW, lifetime_seconds=301)
    with denied("unauthenticated"):
        verify(verifier(), envelope, now=NOW)


def test_future_assertion_is_rejected_beyond_clock_skew():
    envelope = signer().issue(now=NOW + timedelta(seconds=120))
    with denied("unauthenticated"):
        verify(verifier(), envelope, now=NOW)


def test_clock_skew_tolerates_recent_expiry():
    envelope = signer().issue(now=NOW - timedelta(seconds=60), lifetime_seconds=30)
    principal = verify(verifier(clock_skew_seconds=60), envelope, now=NOW)
    assert principal.expires_at == NOW - timedelta(seconds=30)


def test_assertion_must_be_bound_to_operation_target_and_request():
    envelope = signer().issue(now=NOW)
    for expected in (
        dict(expected_operation="execution_request"),
        dict(expected_target="work-2"),
        dict(expected_request_hash="b" * 64),
    ):
        with denied("conflict"):
            verify(verifier(), envelope, now=NOW, **expected)


def test_assertion_scope_must_match_project_and_work_item():
    envelope = signer().issue(now=NOW)
    with denied("forbidden"):
        verify(verifier(), envelope, now=NOW, expected_project="project-2")
    with denied("forbidden"):
        verify(verifier(), envelope, now=NOW, expected_work_item="work-2")


def test_replay_with_different_request_is_conflict():
    first = signer().issue(now=NOW)
    second = signer().issue(now=NOW, request_hash="b" * 64)
    assert first["claims"]["jti"] == second["claims"]["jti"]

    instance = verifier()
    verify(instance, first, now=NOW)
    with denied("conflict"):
        verify(instance, second, now=NOW, expected_request_hash="b" * 64)


@pytest.mark.parametrize(
    "label,overrides",
    [
        ("project", {"project_id": "project-2"}),
        ("work_item", {"work_item_id": "work-2"}),
        ("actor", {"actor_class": "agent", "auth_method": "t3_session"}),
        ("capability", {"capabilities": ["read", "decide"]}),
        ("assurance", {"assurance": "single_factor"}),
        ("session", {"session_id": "session-2"}),
        (
            "job",
            {
                "actor_class": "monitor",
                "capabilities": ["observe", "result"],
                "job_id": "job-1",
                "auth_method": "t3_session",
            },
        ),
    ],
)
def test_signed_replay_with_changed_authorization_claims_conflicts(label, overrides):
    first = signer().issue(now=NOW)
    second = signer().issue(now=NOW, **overrides)
    assert first["claims"]["jti"] == second["claims"]["jti"]
    assert first["claims"] != second["claims"]

    instance = verifier()
    verify(instance, first, now=NOW)
    # Request context matches the second assertion; only the signed claim set
    # differs, so replay identity (not request binding) must reject it.
    with denied("conflict"):
        verify(instance, second, now=NOW)


def test_identical_full_assertion_replays_idempotently():
    envelope = signer().issue(now=NOW)
    instance = verifier()
    first = verify(instance, envelope, now=NOW)
    second = verify(instance, envelope, now=NOW)
    assert first == second


def test_revoked_subject_or_session_is_rejected():
    instance = verifier()
    envelope = signer().issue(now=NOW)
    instance.revoke_subject("test-issuer", "owner")
    with denied("unauthenticated"):
        verify(instance, envelope, now=NOW)

    instance = verifier()
    envelope = signer().issue(now=NOW)
    instance.revoke_session("test-issuer", "session-1")
    with denied("unauthenticated"):
        verify(instance, envelope, now=NOW)


def test_agent_cannot_decide_or_lifecycle():
    envelope = signer().issue(
        now=NOW,
        actor_class="agent",
        capabilities=("read", "decide", "lifecycle"),
        auth_method="t3_session",
    )
    principal = verify(verifier(), envelope, now=NOW)

    for capability in ("decide", "lifecycle"):
        with denied("forbidden"):
            verifier().authorize(principal, capability)


def test_monitor_is_limited_to_its_job_and_observation_capabilities():
    envelope = signer().issue(
        now=NOW,
        subject="monitor",
        actor_class="monitor",
        capabilities=("observe", "result"),
        job_id="job-1",
    )
    principal = verify(verifier(), envelope, now=NOW)
    verifier().authorize(principal, "observe", job_id="job-1")

    with denied("forbidden"):
        verifier().authorize(principal, "observe", job_id="job-2")
    with denied("forbidden"):
        verifier().authorize(principal, "decide")


def test_monitor_requires_job_binding_and_others_forbid_it():
    with denied("forbidden"):
        verify(verifier(), signer().issue(now=NOW, actor_class="monitor", job_id=None), now=NOW)
    with denied("forbidden"):
        verify(verifier(), signer().issue(now=NOW, job_id="job-1"), now=NOW)


def test_observation_requires_monitor_principal_not_human_or_agent():
    human = signer().issue(now=NOW, capabilities=("read", "observe"))
    with denied("forbidden"):
        verifier().authorize(verify(verifier(), human, now=NOW), "observe", job_id="job-1")

    agent = signer().issue(
        now=NOW,
        actor_class="agent",
        capabilities=("read", "observe"),
        auth_method="t3_session",
    )
    agent_principal = verify(verifier(), agent, now=NOW)
    with denied("forbidden"):
        verifier().authorize(agent_principal, "observe", job_id="job-1")


def test_decision_requires_strong_authentication_assurance():
    envelope = signer().issue(now=NOW, assurance="single_factor")
    principal = verify(verifier(), envelope, now=NOW)
    with denied("forbidden"):
        verifier().authorize(principal, "decide")


def test_authorize_rejects_unknown_or_unheld_capabilities():
    principal = verify(verifier(), signer().issue(now=NOW), now=NOW)
    with denied("invalid_request"):
        verifier().authorize(principal, "delete_everything")
    with denied("forbidden"):
        verifier().authorize(principal, "execute")


@pytest.mark.parametrize(
    "overrides,code",
    [
        ({"schema_version": "0.0.0"}, "unsupported_version"),
        ({"actor_class": "robot"}, "forbidden"),
        ({"auth_method": "magic"}, "forbidden"),
        ({"assurance": "none"}, "forbidden"),
        ({"capabilities": []}, "forbidden"),
        ({"capabilities": ["read", "read"]}, "forbidden"),
        ({"operation": "not a valid id"}, "invalid_request"),
        ({"target_id": "", "operation": "decisions"}, "invalid_request"),
        ({"request_hash": "not-a-hash"}, "invalid_request"),
        ({"lifetime_seconds": 0}, "invalid_request"),
    ],
)
def test_malformed_claim_values_are_rejected(overrides, code):
    with denied(code):
        verify(verifier(), signer().issue(now=NOW, **overrides), now=NOW)


def test_unknown_claim_or_envelope_fields_are_rejected():
    envelope = signer().issue(now=NOW)
    envelope["claims"]["extra"] = "value"
    with denied("unauthenticated"):
        verify(verifier(), envelope, now=NOW)

    envelope = signer().issue(now=NOW)
    envelope["extra"] = "value"
    with denied("unauthenticated"):
        verify(verifier(), envelope, now=NOW)

    with denied("unauthenticated"):
        verify(verifier(), {"claims": {}, "signature": "a" * 64}, now=NOW)
    with denied("unauthenticated"):
        verify(verifier(), "not-an-envelope", now=NOW)


def test_non_hex_signature_is_invalid_request():
    envelope = signer().issue(now=NOW)
    envelope["signature"] = "not a signature"
    with denied("invalid_request"):
        verify(verifier(), envelope, now=NOW)


def test_version_matches_contract_version():
    assert signer().issue(now=NOW)["claims"]["schema_version"] == VERSION


# ---------------------------------------------------------------------------
# O02: durable operation journal semantics
# ---------------------------------------------------------------------------


def store(tmp_path, name="operations.db"):
    return OperationStore(tmp_path / name)


def begin(instance, epoch, key="idem-1", body=None, operation_id="op-1", **updates):
    request = dict(
        epoch=epoch,
        subject="owner",
        project_id="project-1",
        work_item_id="work-1",
        operation="decisions",
        target_id="work-1",
        idempotency_key=key,
        body={"decision": "approve_plan"} if body is None else body,
        expected_revision=1,
        current_revision=1,
        operation_id=operation_id,
    )
    request.update(updates)
    return instance.begin(**request)


def test_intent_is_persisted_before_effects(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    operation = begin(instance, epoch)

    assert operation.state == "intent"
    assert operation.effect_state == "pending"
    assert operation.revision == 1
    assert operation.request_hash == digest({"decision": "approve_plan"})
    assert operation.writer_epoch == epoch
    assert instance.get("op-1") == operation


def test_matching_replay_is_idempotent_and_precedes_revision_check(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    first = begin(instance, epoch)
    replay = begin(instance, epoch, current_revision=99)

    assert replay == first
    assert len(instance.uncertain()) == 0
    with pytest.raises(OperationNotFound):
        instance.get("op-2")


def test_expected_revision_is_part_of_replay_identity(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    first = begin(instance, epoch, expected_revision=1, current_revision=1)

    with pytest.raises(OperationConflict):
        # Same key/body, but the request's revision precondition changed.
        begin(instance, epoch, expected_revision=2, current_revision=2)

    # The identical request still replays after the current revision advances.
    replay = begin(instance, epoch, expected_revision=1, current_revision=2)
    assert replay == first
    assert instance.get("op-1") == first


def test_identical_replay_after_revision_advance_returns_existing(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    first = begin(instance, epoch, expected_revision=1, current_revision=1)
    replay = begin(instance, epoch, expected_revision=1, current_revision=2)

    assert replay == first
    assert instance.get("op-1").state == "intent"


def test_fresh_stale_intent_fails_without_row(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    with pytest.raises(OperationConflict):
        begin(instance, epoch, expected_revision=1, current_revision=2)

    with pytest.raises(OperationNotFound):
        instance.get("op-1")

    accepted = begin(instance, epoch, expected_revision=2, current_revision=2)
    assert accepted.revision == 2
    assert instance.get("op-1") == accepted


def test_idempotency_key_reuse_with_different_content_conflicts(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    begin(instance, epoch)
    with pytest.raises(OperationConflict):
        begin(instance, epoch, body={"decision": "reject"}, operation_id="op-2")


def test_completion_records_receipt_and_observed_job(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    begin(instance, epoch)
    receipt = {"effect": "approval_only", "revision": 2}
    done = instance.complete("op-1", epoch=epoch, receipt=receipt, job_id="job-1", attempt=1)

    assert done.state == "completed"
    assert done.effect_state == "completed"
    assert done.receipt == receipt
    assert done.job_id == "job-1"
    assert done.attempt == 1


def test_completion_is_idempotent_for_same_receipt_only(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    begin(instance, epoch)
    instance.complete("op-1", epoch=epoch, receipt={"effect": "approval_only"})
    same = instance.complete("op-1", epoch=epoch, receipt={"effect": "approval_only"})
    assert same.state == "completed"
    with pytest.raises(OperationConflict):
        instance.complete("op-1", epoch=epoch, receipt={"effect": "different"})


def test_completion_replay_accepts_identical_correlation(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    begin(instance, epoch)
    receipt = {"effect": "approval_only"}
    instance.complete(
        "op-1", epoch=epoch, receipt=receipt, job_id="job-1", attempt=1, runtime_ref="runtime-1"
    )
    replay = instance.complete(
        "op-1", epoch=epoch, receipt=receipt, job_id="job-1", attempt=1, runtime_ref="runtime-1"
    )
    assert replay.job_id == "job-1"
    assert replay.attempt == 1
    assert replay.runtime_ref == "runtime-1"


@pytest.mark.parametrize(
    "field,value",
    [("job_id", "job-2"), ("attempt", 2), ("runtime_ref", "runtime-2")],
)
def test_completion_replay_rejects_changed_correlation(tmp_path, field, value):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    begin(instance, epoch)
    receipt = {"effect": "approval_only"}
    instance.complete(
        "op-1", epoch=epoch, receipt=receipt, job_id="job-1", attempt=1, runtime_ref="runtime-1"
    )
    with pytest.raises(OperationConflict):
        instance.complete("op-1", epoch=epoch, receipt=receipt, **{field: value})


def test_unknown_operation_lookups_and_completion_fail_closed(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    with pytest.raises(OperationNotFound):
        instance.get("missing")
    with pytest.raises(OperationNotFound):
        instance.complete("missing", epoch=epoch, receipt={})
    with pytest.raises(OperationNotFound):
        instance.mark_uncertain("missing", epoch=epoch, reason="lost")
    with pytest.raises(OperationNotFound):
        instance.reconcile("missing", epoch=epoch, outcome="failed")


def test_stale_writer_epoch_is_fenced_for_every_mutation(tmp_path):
    instance = store(tmp_path)
    old = instance.claim_writer("writer-a")
    begin(instance, old)
    new = instance.claim_writer("writer-b")
    assert new == old + 1

    with pytest.raises(OperationFenced):
        begin(instance, old, key="idem-2", operation_id="op-2")
    with pytest.raises(OperationFenced):
        instance.complete("op-1", epoch=old, receipt={})
    with pytest.raises(OperationFenced):
        instance.mark_uncertain("op-1", epoch=old, reason="stale")
    with pytest.raises(OperationFenced):
        instance.recover(epoch=old)


def test_restart_turns_unfinished_intent_into_uncertain_without_relaunch(tmp_path):
    path = tmp_path / "operations.db"
    first = OperationStore(path)
    epoch = first.claim_writer("writer-a")
    begin(first, epoch)

    second = OperationStore(path)
    assert second.current_epoch() == epoch
    assert [o.operation_id for o in second.uncertain()] == []

    new_epoch = second.claim_writer("writer-b")
    recovered = second.recover(epoch=new_epoch)
    assert [o.state for o in recovered] == ["uncertain"]
    assert recovered[0].uncertain_reason == "writer restart before completion"
    assert second.get("op-1").effect_state == "uncertain"
    # Recovery records uncertainty; there is no method that creates or relaunches work.
    assert not hasattr(second, "launch")
    assert not hasattr(second, "dispatch")


def test_reconciliation_requires_new_epoch_and_uncertain_state(tmp_path):
    path = tmp_path / "operations.db"
    first = OperationStore(path)
    epoch = first.claim_writer("writer-a")
    begin(first, epoch)

    second = OperationStore(path)
    second.recover(epoch=epoch)  # the current writer may record uncertainty
    with pytest.raises(OperationConflict):
        # reconciliation must be owned by a later writer epoch
        second.reconcile("op-1", epoch=epoch, outcome="failed")

    new_epoch = second.claim_writer("writer-b")
    with pytest.raises(ValueError):
        second.reconcile("op-1", epoch=new_epoch, outcome="completed")
    with pytest.raises(ValueError):
        second.reconcile("op-1", epoch=new_epoch, outcome="failed", receipt={})

    reconciled = second.reconcile(
        "op-1",
        epoch=new_epoch,
        outcome="completed",
        receipt={"revision": 2},
        job_id="job-1",
        evidence_ref="evidence-1",
    )
    assert reconciled.state == "completed"
    assert reconciled.receipt == {"revision": 2}
    assert reconciled.evidence_ref == "evidence-1"
    assert reconciled.writer_epoch == new_epoch


def test_failed_reconciliation_records_no_receipt(tmp_path):
    path = tmp_path / "operations.db"
    first = OperationStore(path)
    epoch = first.claim_writer("writer-a")
    begin(first, epoch)
    second = OperationStore(path)
    second.claim_writer("writer-b")
    second.recover(epoch=second.current_epoch())
    third = OperationStore(path)
    final_epoch = third.claim_writer("writer-c")

    failed = third.reconcile("op-1", epoch=final_epoch, outcome="failed", evidence_ref="evidence-1")
    assert failed.state == "failed"
    assert failed.effect_state == "failed"
    assert failed.receipt is None


def test_reconciliation_cannot_repeat_with_changed_correlation(tmp_path):
    path = tmp_path / "operations.db"
    first = OperationStore(path)
    epoch = first.claim_writer("writer-a")
    begin(first, epoch)
    second = OperationStore(path)
    second.claim_writer("writer-b")
    second.recover(epoch=second.current_epoch())
    third = OperationStore(path)
    final_epoch = third.claim_writer("writer-c")
    third.reconcile(
        "op-1",
        epoch=final_epoch,
        outcome="completed",
        receipt={"revision": 2},
        job_id="job-1",
        evidence_ref="evidence-1",
    )

    with pytest.raises(OperationConflict):
        third.reconcile(
            "op-1",
            epoch=final_epoch,
            outcome="completed",
            receipt={"revision": 2},
            job_id="job-2",
            evidence_ref="evidence-1",
        )
    row = third.get("op-1")
    assert row.job_id == "job-1"
    assert row.state == "completed"


def test_cannot_complete_or_mark_uncertain_a_finished_operation(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    begin(instance, epoch)
    instance.mark_uncertain("op-1", epoch=epoch, reason="synthetic loss")
    with pytest.raises(OperationConflict):
        instance.mark_uncertain("op-1", epoch=epoch, reason="again")
    with pytest.raises(OperationConflict):
        instance.complete("op-1", epoch=epoch, receipt={})


def test_concurrent_identical_requests_produce_one_operation(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")

    def attempt(_):
        return begin(instance, epoch)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))

    assert {result.operation_id for result in results} == {"op-1"}
    assert {result.state for result in results} == {"intent"}


def test_concurrent_conflicting_requests_with_same_key_one_wins(tmp_path):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")

    def attempt(index):
        body = {"decision": "approve_plan", "index": index}
        try:
            return begin(instance, epoch, body=body, operation_id=f"op-{index}")
        except OperationConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))

    assert len([r for r in results if r != "conflict"]) == 1
    assert len([r for r in results if r == "conflict"]) == 7


@pytest.mark.parametrize(
    "updates",
    [
        {"subject": "bad subject"},
        {"idempotency_key": ""},
        {"operation_id": "x" * 97},
        {"body": "not a dict"},
        {"expected_revision": -1},
        {"expected_revision": "1"},
        {"current_revision": -1},
        {"current_revision": "1"},
    ],
)
def test_invalid_begin_inputs_are_rejected(tmp_path, updates):
    instance = store(tmp_path)
    epoch = instance.claim_writer("writer-a")
    with pytest.raises(ValueError):
        begin(instance, epoch, **updates)


def test_invalid_store_path_requires_database_suffix(tmp_path):
    with pytest.raises(ValueError):
        OperationStore(tmp_path / "operations.json")


def test_store_never_points_at_existing_workflow_state(tmp_path):
    instance = store(tmp_path)
    assert instance.path == (tmp_path / "operations.db").resolve()
    assert instance.path.suffix == ".db"
