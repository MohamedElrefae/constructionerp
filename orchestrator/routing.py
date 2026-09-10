"""Deterministic routing over accepted events; no process or filesystem side effects."""

from copy import deepcopy

from core import WorkflowError, digest


def initial(config):
    return dict(
        work_item=config["work_item"],
        stage=config["stages"][0],
        status="DRAFT",
        next_roles=["architect"],
        active_jobs=[],
        candidate=config["candidate"],
        plan_revision_hash=config["plan_revision_hash"],
        scope_hash=config["scope_hash"],
        round=0,
        attempt=1,
        cursor=0,
        revision=0,
        findings=[],
        backlog=[],
        next_finding=1,
        unsuccessful_cycles=0,
        unchanged_rounds=0,
        previous_snapshots=[],
        gate=None,
        pause_reason=None,
        resume_to=None,
        prior=None,
        completed_dependencies=[],
        approval_refs=[],
        review_results={},
        stages={},
        plan_granted=False,
        committed=False,
    )


def gate_id(state, scope):
    bindings = [state["work_item"], state["stage"], scope, state["plan_revision_hash"], state["scope_hash"]]
    if scope != "PLAN":
        bindings += [state["candidate"]["candidate_id"]]
    return scope.lower() + "-" + digest(bindings)[:24]


def pause(state, reason):
    if state["status"] != "PAUSED":
        state["prior"] = dict(status=state["status"], next_roles=state["next_roles"], gate=state["gate"])
        state["resume_to"] = state["status"]
    state.update(
        status="PAUSED",
        pause_reason=reason,
        next_roles=[],
        gate={"scope": "DECISION", "gate_id": "decision-" + str(state["revision"])},
    )


def finding_identity(f):
    reproduction = (f.get("snapshot") or {}).get("reproduction_digest") or f.get("summary", "").strip()
    if not reproduction:
        return None
    return f["classification"], tuple(sorted(f.get("affected_requirements", []))), reproduction


def findings(state, incoming, pending=()):
    result = []
    known = {f["finding_id"]: f for f in state["findings"] + state["backlog"] + list(pending)}
    for f in deepcopy(incoming):
        if f["finding_id"] is None:
            identity = finding_identity(f)
            existing = next(
                (
                    key
                    for key, old in known.items()
                    if identity is not None and finding_identity(old) == identity
                ),
                None,
            )
            if existing:
                f["finding_id"] = existing
            else:
                f["finding_id"] = "SCP-" + str(state["next_finding"]).zfill(3)
                state["next_finding"] += 1
        elif f["finding_id"] not in known:
            raise WorkflowError("Reviewer supplied an unallocated finding ID")
        known[f["finding_id"]] = f
        result.append(f)
    return result


def review_outcome(state, outputs, source, quorum):
    accepted = []
    for output in outputs:
        accepted += findings(state, output["findings"], accepted)
    state["backlog"] += [f for f in accepted if not f["blocking"]]
    # Reviews must explicitly cover all old unresolved IDs; never silently drop one.
    old = {f["finding_id"]: f for f in state["findings"]}
    updates = {f["finding_id"]: f for f in accepted}
    if all(o["verdict"] == "PASS" for o in outputs):
        # A PASS is an explicit assertion that the entire repair packet was rechecked.
        old = {
            k: f
            for k, f in old.items()
            if source == "reviewer" and f["classification"] == "implementation_defect"
        }
    old.update(updates)
    state["findings"] = [f for f in old.values() if f["blocking"]]
    blocked = any(o["verdict"] == "BLOCKED" for o in outputs) or any(
        source != "reviewer" or f["classification"] != "implementation_defect" for f in state["findings"]
    )
    state["round"] += 1
    if blocked:
        state["unsuccessful_cycles"] += 1
        snapshots = sorted(
            digest(
                [
                    f["finding_id"],
                    f["classification"],
                    f["snapshot"]["reproduction_digest"],
                    f["snapshot"]["relevant_evidence_digest"],
                ]
            )
            for f in state["findings"]
            if f.get("snapshot")
        )
        overlap = set(snapshots) & set(state["previous_snapshots"])
        state["unchanged_rounds"] = state["unchanged_rounds"] + 1 if overlap else (1 if snapshots else 0)
        state["previous_snapshots"] = snapshots
        if state["unsuccessful_cycles"] >= 3 or state["unchanged_rounds"] >= 2:
            pause(state, "ESCALATED")
        elif any(f["classification"] == "owner_decision" for f in state["findings"]):
            pause(state, "OWNER_DECISION")
        elif any(f["classification"] == "design_defect" for f in state["findings"]):
            state.update(status="NEEDS_REVISION", next_roles=["architect"], gate=None)
        else:
            state.update(status="CHANGES_REQUESTED", next_roles=["builder"], gate=None)
        state["attempt"] += 1
        return
    if source == "reviewer" and state["plan_granted"]:
        state.update(status="APPROVED_FOR_BUILD", next_roles=["builder"], gate=None)
    elif source == "reviewer":
        state.update(
            status="PLAN_SUBMITTED", next_roles=[], gate={"scope": "PLAN", "gate_id": gate_id(state, "PLAN")}
        )
    elif source == "quorum":
        state.update(status="BUILD_COMPLETE", next_roles=["verifier"], gate=None)
    else:
        state.update(
            status="VERIFIED_FOR_RELEASE",
            next_roles=[],
            gate={"scope": "COMMIT", "gate_id": gate_id(state, "COMMIT")},
        )


def apply_event(current, event, config):
    state = deepcopy(current)
    if event["seq"] <= state["cursor"]:
        return state
    kind, body = event["kind"], event["payload"]
    if kind == "result":
        role, output = body["role"], body["result"]
        if body["job_id"] not in state["active_jobs"]:
            raise WorkflowError("Result does not belong to active jobs")
        state["active_jobs"].remove(body["job_id"])
        state["completed_dependencies"].append(body["job_id"])
        if output["status"] == "FAILED":
            state["next_roles"] = [role]
            state["attempt"] += 1
            pause(state, output["failure_class"])
        elif role == "architect":
            if output["verdict"] == "BLOCKED":
                state["findings"] += findings(state, output["findings"])
                state["next_roles"] = ["architect"]
                state["attempt"] += 1
                pause(state, "OWNER_DECISION")
            else:
                state.update(
                    plan_revision_hash=body["new_plan_hash"],
                    plan_granted=state["plan_granted"]
                    and body["new_plan_hash"] == state["plan_revision_hash"],
                    status="PLAN_SUBMITTED",
                    next_roles=["reviewer"],
                    gate=None,
                )
        elif role == "builder":
            state["candidate"] = body["candidate"]
            if output["verdict"] == "BLOCKED":
                incoming = findings(state, output["findings"])
                state["findings"] += [
                    f
                    for f in incoming
                    if f["blocking"]
                    and f["finding_id"] not in {old["finding_id"] for old in state["findings"]}
                ]
                state["backlog"] += [f for f in incoming if not f["blocking"]]
                if any(f["classification"] == "owner_decision" for f in incoming):
                    pause(state, "OWNER_DECISION")
                elif any(f["classification"] == "design_defect" for f in incoming):
                    state.update(status="NEEDS_REVISION", next_roles=["architect"], gate=None)
                    state["attempt"] += 1
                else:
                    state.update(status="BUILD_COMPLETE", next_roles=["verifier"], gate=None)
            else:
                state.update(
                    candidate=body["candidate"],
                    status="BUILD_COMPLETE",
                    next_roles=config.get("quorum", []) or ["verifier"],
                    review_results={},
                )
        elif role in config.get("quorum", []):
            state["review_results"][role] = output
            if set(state["review_results"]) == set(config["quorum"]):
                sessions = [o["session_id"] for o in state["review_results"].values()]
                if len(set(sessions)) != len(sessions):
                    raise WorkflowError("Quorum sessions are not independent")
                review_outcome(state, list(state["review_results"].values()), "quorum", config["quorum"])
            else:
                state["next_roles"] = []
        else:
            review_outcome(state, [output], role, config.get("quorum", []))
    elif kind == "grant":
        token = body
        if (
            not state["gate"]
            or token["gate_id"] != state["gate"]["gate_id"]
            or token["scope"] != state["gate"]["scope"]
        ):
            raise WorkflowError("Stale gate authorization")
        state["approval_refs"].append(token["token_id"])
        if token["scope"] == "PLAN":
            if (
                token["plan_revision_hash"] != state["plan_revision_hash"]
                or token["scope_hash"] != state["scope_hash"]
            ):
                raise WorkflowError("Stale plan grant")
            state.update(plan_granted=True, status="APPROVED_FOR_BUILD", next_roles=["builder"], gate=None)
        elif token["scope"] == "COMMIT":
            if token["candidate_id"] != state["candidate"]["candidate_id"]:
                raise WorkflowError("Stale commit grant")
            state["gate"] = {"scope": "OWNER_COMMIT", "gate_id": token["gate_id"]}
        else:
            raise WorkflowError("ERP operation execution is gated beyond this phase")
    elif kind == "pause":
        pause(state, body["reason"])
    elif kind == "resume":
        if state["status"] != "PAUSED" or (
            state["active_jobs"] and not state["pause_reason"].startswith("OWNER:")
        ):
            raise WorkflowError("Cannot resume unresolved active/uncertain jobs")
        if state["pause_reason"] == "ESCALATED" and not body.get("reset_budget"):
            raise WorkflowError("Escalation needs an explicit owner budget-reset decision")
        if body.get("reset_budget"):
            state.update(unsuccessful_cycles=0, unchanged_rounds=0, previous_snapshots=[])
        prior = state["prior"]
        state.update(prior)
        state.update(pause_reason=None, resume_to=None, prior=None)
        if not state["next_roles"] and not state["gate"] and not state["active_jobs"]:
            state["next_roles"] = [
                "architect"
                if any(f["classification"] == "design_defect" for f in state["findings"])
                else "builder"
            ]
    elif kind == "reconcile_job":
        if state["status"] != "PAUSED" or body["job_id"] not in state["active_jobs"]:
            raise WorkflowError("Reconciliation does not match a paused active job")
        state["active_jobs"].remove(body["job_id"])
        state["attempt"] += 1
        state["prior"]["next_roles"] = list(dict.fromkeys(state["prior"]["next_roles"] + [body["role"]]))
    elif kind == "refresh_candidate":
        if state["status"] != "PAUSED" or state["active_jobs"]:
            raise WorkflowError("Candidate refresh requires all external jobs reconciled")
        state["candidate"] = body["candidate"]
        state["review_results"] = {}
        state["attempt"] += 1
        state["prior"].update(gate=None, next_roles=["builder" if state["plan_granted"] else "architect"])
    elif kind == "stage_started":
        state["stages"][state["stage"]] = {
            "sub_status": None,
            "historical": False,
            "evidence_refs": body["evidence_refs"],
        }
        state.update(
            stage=body["stage"],
            scope_hash=body["scope_hash"],
            candidate=body["candidate"],
            status="DRAFT",
            next_roles=["architect"],
            active_jobs=[],
            round=0,
            attempt=1,
            findings=[],
            review_results={},
            unsuccessful_cycles=0,
            unchanged_rounds=0,
            previous_snapshots=[],
            gate=None,
            pause_reason=None,
            resume_to=None,
            prior=None,
            plan_granted=False,
            committed=False,
        )
    elif kind == "scope_revised":
        if state["status"] != "PAUSED" or state["active_jobs"]:
            raise WorkflowError("Scope revision requires a paused reconciled stage")
        state.update(
            scope_hash=body["scope_hash"], plan_granted=False, review_results={}, candidate=body["candidate"]
        )
        state["prior"].update(status="NEEDS_REVISION", next_roles=["architect"], gate=None)
        state["attempt"] += 1
    elif kind == "recovery_reviewed":
        state.update(
            candidate=body["candidate"],
            active_jobs=[],
            next_roles=["architect"],
            status="DRAFT",
            gate=None,
            pause_reason=None,
            resume_to=None,
            prior=None,
            plan_granted=False,
            committed=False,
            review_results={},
            attempt=state["attempt"] + body["attempt_offset"],
            unsuccessful_cycles=0,
            unchanged_rounds=0,
            previous_snapshots=[],
        )
    elif kind == "owner_commit":
        state.update(committed=True, gate=None)
    else:
        raise WorkflowError("Unknown authoritative event")
    state.update(cursor=event["seq"], revision=state["revision"] + 1)
    return state
