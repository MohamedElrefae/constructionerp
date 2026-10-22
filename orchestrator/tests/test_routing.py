from copy import deepcopy

import pytest
from core import WorkflowError
from routing import review_outcome


def state():
    return dict(
        work_item="w",
        stage="1",
        plan_revision_hash="a" * 64,
        scope_hash="b" * 64,
        candidate={"candidate_id": "c" * 64},
        revision=1,
        round=0,
        attempt=1,
        status="BUILD_COMPLETE",
        next_roles=[],
        gate=None,
        findings=[],
        backlog=[],
        next_finding=1,
        unsuccessful_cycles=0,
        unchanged_rounds=0,
        previous_snapshots=[],
        plan_granted=True,
    )


def finding(kind, identity=None, snapshot=None):
    return {
        "finding_id": identity,
        "classification": kind,
        "blocking": kind != "optional_improvement",
        "snapshot": snapshot,
    }


@pytest.mark.parametrize(
    "classification,route", [("implementation_defect", "builder"), ("design_defect", "architect")]
)
def test_distinct_return_routes(classification, route):
    v = state()
    review_outcome(v, [{"verdict": "BLOCKED", "findings": [finding(classification)]}], "verifier", [])
    assert v["next_roles"] == [route]
    assert v["unsuccessful_cycles"] == 1


def test_optional_backlog_does_not_block():
    v = state()
    review_outcome(v, [{"verdict": "PASS", "findings": [finding("optional_improvement")]}], "verifier", [])
    assert len(v["backlog"]) == 1 and v["status"] == "VERIFIED_FOR_RELEASE"


def test_three_failed_cycles_persist_across_architecture_route():
    v = state()
    for i, kind in enumerate(["implementation_defect", "design_defect", "implementation_defect"]):
        review_outcome(
            v, [{"verdict": "BLOCKED", "findings": [finding(kind)]}], "reviewer" if i == 1 else "verifier", []
        )
    assert v["status"] == "PAUSED" and v["pause_reason"] == "ESCALATED"
    assert v["unsuccessful_cycles"] == 3


def test_same_normalized_blocker_escalates_after_two_rounds():
    v = state()
    f = finding(
        "implementation_defect",
        snapshot={
            "reproduction_digest": "a",
            "relevant_evidence_digest": "b",
            "normalized_material_ref": "stable",
        },
    )
    review_outcome(v, [{"verdict": "BLOCKED", "findings": [f]}], "verifier", [])
    f["finding_id"] = v["findings"][0]["finding_id"]
    review_outcome(v, [{"verdict": "BLOCKED", "findings": [f]}], "verifier", [])
    assert v["pause_reason"] == "ESCALATED" and v["unsuccessful_cycles"] == 2


def test_architecture_pass_preserves_unfixed_implementation_findings():
    v = state()
    v["findings"] = [finding("implementation_defect", "SCP-001")]
    review_outcome(v, [{"verdict": "PASS", "findings": []}], "reviewer", [])
    assert v["next_roles"] == ["builder"] and len(v["findings"]) == 1


def test_new_artifact_reference_does_not_reset_same_blocker():
    v = state()
    first = {
        "reproduction_digest": "a",
        "relevant_evidence_digest": "b",
        "normalized_material_ref": "job-one",
    }
    second = {**first, "normalized_material_ref": "job-two"}
    review_outcome(
        v,
        [{"verdict": "BLOCKED", "findings": [finding("implementation_defect", snapshot=first)]}],
        "verifier",
        [],
    )
    review_outcome(
        v,
        [
            {
                "verdict": "BLOCKED",
                "findings": [finding("implementation_defect", v["findings"][0]["finding_id"], second)],
            }
        ],
        "verifier",
        [],
    )
    assert v["pause_reason"] == "ESCALATED"


def test_duplicate_finding_reuses_orchestrator_id():
    v = state()
    f = {**finding("implementation_defect"), "summary": "Same reproduction", "affected_requirements": ["R1"]}
    review_outcome(
        v, [{"verdict": "BLOCKED", "findings": [f]}, {"verdict": "BLOCKED", "findings": [f]}], "quorum", []
    )
    assert len(v["findings"]) == 1 and v["next_finding"] == 2
