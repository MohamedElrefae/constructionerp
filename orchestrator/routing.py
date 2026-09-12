"""Deterministic routing over accepted events; no process or filesystem side effects."""

import hashlib
import json
from copy import deepcopy

from core import WorkflowError, digest
from stage4 import derive_stage4_candidate_id, is_hex64


def initial(config):
    sub_status = config.get("sub_status")
    plan_granted = config.get("plan_granted", False)

    # In Stage 4 PROPOSAL_PENDING, fail-closed owner-controlled proposal-dispatch gate
    if sub_status == "PROPOSAL_PENDING" and not plan_granted:
        gate = {"scope": "PLAN", "gate_id": gate_id(config, "PLAN")}
        next_roles = []
    else:
        gate = None
        next_roles = config.get("next_roles", ["architect"])

    return dict(
        work_item=config["work_item"],
        stage=config.get("stage") or config["stages"][0],
        sub_status=sub_status,
        status="DRAFT",
        next_roles=next_roles,
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
        gate=gate,
        pause_reason=None,
        resume_to=None,
        prior=None,
        completed_dependencies=[],
        approval_refs=[],
        review_results={},
        stages=deepcopy(config.get("historical_stages", {})),
        plan_granted=plan_granted,
        committed=False,
        dry_run_evidence_digest=None,
    )


def gate_id(state, scope):
    bindings = [state["work_item"], state["stage"], scope, state["plan_revision_hash"], state["scope_hash"]]
    if scope != "PLAN" and state.get("candidate"):
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
        if state.get("sub_status") == "PANEL_REVIEW":
            state.update(
                sub_status="BUNDLE_VALIDATED",
                status="BUILD_COMPLETE",
                next_roles=["verifier"],
                gate=None,
            )
        else:
            state.update(status="BUILD_COMPLETE", next_roles=["verifier"], gate=None)
    else:
        if state.get("sub_status") == "BUNDLE_VALIDATED":
            state.update(
                sub_status="OWNER_PAYLOAD_AUTHORIZATION",
                status="VERIFIED_FOR_RELEASE",
                next_roles=[],
                gate={"scope": "DRY_RUN", "gate_id": gate_id(state, "DRY_RUN")},
            )
        elif state.get("sub_status") == "POST_IMPORT_EVIDENCE":
            state.update(
                sub_status="STAGE_4_VERIFIED",
                status="VERIFIED_FOR_RELEASE",
                next_roles=[],
                gate=None,
            )
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
        elif role == "proposer":
            if output["verdict"] == "PROPOSED":
                verified_arts = body.get("verified_private_artifacts", [])
                proposal_sha = body.get("proposal_sha256")
                export_sha = body.get("export_sha256") or state["candidate"].get("export_sha256")
                if not verified_arts or not proposal_sha or not export_sha:
                    state["attempt"] += 1
                    pause(state, "MALFORMED_RESULT")
                else:
                    candidate_id = body.get("candidate_id") or derive_stage4_candidate_id(export_sha, proposal_sha)
                    cand = deepcopy(state["candidate"])
                    cand["export_sha256"] = export_sha
                    cand["proposal_sha256"] = proposal_sha
                    cand["candidate_id"] = candidate_id
                    cand["manifest_hash"] = candidate_id
                    cand["private_artifact_refs"] = deepcopy(verified_arts)
                    state["candidate"] = cand
                    state.update(
                        sub_status="PROPOSAL_FROZEN",
                        status="BUILD_COMPLETE",
                        next_roles=config.get("quorum", ["ai-a1", "ai-a2", "ai-a3"]),
                        review_results={},
                    )
            elif output["verdict"] == "BLOCKED":
                pause(state, "OWNER_DECISION")
            else:
                state["attempt"] += 1
                pause(state, output.get("failure_class", "MALFORMED_RESULT"))
        elif role == "builder":
            if state.get("sub_status") == "DRY_RUN":
                digest_val = body.get("dry_run_evidence_digest") or output.get("dry_run_evidence_digest")
                if not digest_val or not is_hex64(digest_val):
                    pause(state, "MALFORMED_RESULT")
                    state["attempt"] += 1
                elif output["verdict"] == "PASS":
                    state.update(
                        sub_status="IMPORT_AUTHORIZATION",
                        status="VERIFIED_FOR_RELEASE",
                        next_roles=[],
                        gate={"scope": "IMPORT", "gate_id": gate_id(state, "IMPORT")},
                        dry_run_evidence_digest=digest_val,
                    )
                else:
                    pause(state, "DRY_RUN_FAILED")
            elif state.get("sub_status") == "IMPORT":
                if output["verdict"] == "PASS":
                    state.update(
                        sub_status="POST_IMPORT_EVIDENCE",
                        status="BUILD_COMPLETE",
                        next_roles=["verifier"],
                        gate=None,
                    )
                else:
                    pause(state, "IMPORT_FAILED")
            else:
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
            entry = dict(output)
            entry["verified_artifacts"] = body.get("verified_private_artifacts", [])
            entry["review_meta"] = body.get("review_meta", {})
            state["review_results"][role] = entry
            if set(state["review_results"]) == set(config["quorum"]):
                if state.get("sub_status") in ("PROPOSAL_FROZEN", "PANEL_REVIEW"):
                    state["sub_status"] = "PANEL_REVIEW"
                    all_blocking = []
                    renewal_required = False
                    sessions = []
                    for qrole in config["quorum"]:
                        qinfo = state["review_results"][qrole]
                        qmeta = qinfo.get("review_meta", {})
                        if qmeta.get("blocking_findings"):
                            all_blocking.extend(qmeta["blocking_findings"])
                        if qmeta.get("renewal_required"):
                            renewal_required = True
                        if qinfo.get("session_id"):
                            sessions.append(qinfo["session_id"])

                    if len(set(sessions)) != len(sessions):
                        pause(state, "MALFORMED_RESULT")
                    elif all_blocking:
                        incoming = findings(state, all_blocking)
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
                            state.update(status="NEEDS_REVISION", next_roles=["proposer"], gate=None)
                            state["attempt"] += 1
                    elif renewal_required:
                        state.update(
                            sub_status="PANEL_RENEWAL",
                            status="NEEDS_REVISION",
                            next_roles=["proposer"],
                            review_results={},
                            round=state["round"] + 1,
                        )
                    elif all(q["verdict"] == "PASS" for q in state["review_results"].values()):
                        bundle_sha = body.get("bundle_sha256") or (body.get("bundle_composed") or {}).get("bundle_sha256")
                        payload_sha = body.get("payload_sha256") or (body.get("bundle_composed") or {}).get("payload_sha256")
                        bundle_arts = body.get("bundle_artifacts") or (body.get("bundle_composed") or {}).get("verified_private_artifacts", [])
                        if not bundle_sha or not payload_sha or not is_hex64(bundle_sha) or not is_hex64(payload_sha):
                            state["attempt"] += 1
                            pause(state, "MALFORMED_RESULT")
                        else:
                            state["candidate"]["bundle_sha256"] = bundle_sha
                            state["candidate"]["payload_sha256"] = payload_sha
                            state["bundle_sha256"] = bundle_sha
                            state["payload_sha256"] = payload_sha
                            if "private_artifact_refs" in state["candidate"] and bundle_arts:
                                state["candidate"]["private_artifact_refs"].extend(bundle_arts)
                            state.update(
                                sub_status="BUNDLE_VALIDATED",
                                status="BUILD_COMPLETE",
                                next_roles=["verifier"],
                                review_results={},
                                round=state["round"] + 1,
                            )
                    else:
                        review_outcome(state, [state["review_results"][r] for r in config["quorum"]], "quorum", config["quorum"])
                else:
                    review_outcome(state, [state["review_results"][r] for r in config["quorum"]], "quorum", config["quorum"])
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
            if state.get("sub_status") == "PROPOSAL_PENDING":
                state.update(plan_granted=True, status="APPROVED_FOR_BUILD", next_roles=["proposer"], gate=None)
            else:
                state.update(plan_granted=True, status="APPROVED_FOR_BUILD", next_roles=["builder"], gate=None)
        elif token["scope"] == "COMMIT":
            if token["candidate_id"] != state["candidate"]["candidate_id"]:
                raise WorkflowError("Stale commit grant")
            state["gate"] = {"scope": "OWNER_COMMIT", "gate_id": token["gate_id"]}
        elif token["scope"] == "DRY_RUN":
            if token["candidate_id"] != state["candidate"]["candidate_id"]:
                raise WorkflowError("Stale dry-run grant candidate")
            if token.get("operation") != "set_account_name_ar":
                raise WorkflowError("Unsupported operation in dry-run grant")
            for hkey in ("export_sha256", "proposal_sha256", "bundle_sha256", "payload_sha256", "erp_descriptor_hash"):
                if not token.get(hkey) or not is_hex64(token[hkey]):
                    raise WorkflowError(f"Dry-run grant {hkey} must be 64-character lowercase hex")

            # Unconditional check: active hashes must exist in state and match token
            exp_export = state["candidate"].get("export_sha256")
            if not exp_export or not is_hex64(exp_export):
                raise WorkflowError("Dry-run requires active export_sha256 in state")
            if token["export_sha256"] != exp_export:
                raise WorkflowError("Dry-run grant export_sha256 mismatch")

            exp_prop = state["candidate"].get("proposal_sha256") or state["candidate"].get("candidate_id")
            if not exp_prop or not is_hex64(exp_prop):
                raise WorkflowError("Dry-run requires active proposal_sha256 in state")
            token_prop = token.get("proposal_sha256") or token.get("candidate_id")
            if token_prop != exp_prop:
                raise WorkflowError("Dry-run grant proposal_sha256 mismatch")

            exp_bundle = state.get("bundle_sha256") or state["candidate"].get("bundle_sha256")
            if not exp_bundle or not is_hex64(exp_bundle):
                raise WorkflowError("Dry-run requires active bundle_sha256 in state")
            if token["bundle_sha256"] != exp_bundle:
                raise WorkflowError("Dry-run grant bundle_sha256 mismatch")

            exp_payload = state.get("payload_sha256") or state["candidate"].get("payload_sha256")
            if not exp_payload or not is_hex64(exp_payload):
                raise WorkflowError("Dry-run requires active payload_sha256 in state")
            if token["payload_sha256"] != exp_payload:
                raise WorkflowError("Dry-run grant payload_sha256 mismatch")

            exp_desc = config.get("erp_descriptor_hash") or state.get("erp_descriptor_hash")
            if not exp_desc or not is_hex64(exp_desc):
                raise WorkflowError("Dry-run requires active erp_descriptor_hash in config")
            if token["erp_descriptor_hash"] != exp_desc:
                raise WorkflowError("Dry-run grant erp_descriptor_hash mismatch")

            state.update(
                sub_status="DRY_RUN",
                status="APPROVED_FOR_BUILD",
                next_roles=["builder"],
                gate=None,
            )
        elif token["scope"] == "IMPORT":
            if token["candidate_id"] != state["candidate"]["candidate_id"]:
                raise WorkflowError("Stale import grant candidate")
            if token.get("operation") != "set_account_name_ar":
                raise WorkflowError("Unsupported operation in import grant")
            for hkey in ("export_sha256", "proposal_sha256", "bundle_sha256", "payload_sha256", "erp_descriptor_hash"):
                if not token.get(hkey) or not is_hex64(token[hkey]):
                    raise WorkflowError(f"Import grant {hkey} must be 64-character lowercase hex")
            if not token.get("dry_run_evidence_digest") or not is_hex64(token["dry_run_evidence_digest"]):
                raise WorkflowError("Import grant dry_run_evidence_digest must be 64-character lowercase hex")

            exp_export = state["candidate"].get("export_sha256")
            if not exp_export or not is_hex64(exp_export):
                raise WorkflowError("Import requires active export_sha256 in state")
            if token["export_sha256"] != exp_export:
                raise WorkflowError("Import grant export_sha256 mismatch")

            exp_prop = state["candidate"].get("proposal_sha256") or state["candidate"].get("candidate_id")
            if not exp_prop or not is_hex64(exp_prop):
                raise WorkflowError("Import requires active proposal_sha256 in state")
            token_prop = token.get("proposal_sha256") or token.get("candidate_id")
            if token_prop != exp_prop:
                raise WorkflowError("Import grant proposal_sha256 mismatch")

            exp_bundle = state.get("bundle_sha256") or state["candidate"].get("bundle_sha256")
            if not exp_bundle or not is_hex64(exp_bundle):
                raise WorkflowError("Import requires active bundle_sha256 in state")
            if token["bundle_sha256"] != exp_bundle:
                raise WorkflowError("Import grant bundle_sha256 mismatch")

            exp_payload = state.get("payload_sha256") or state["candidate"].get("payload_sha256")
            if not exp_payload or not is_hex64(exp_payload):
                raise WorkflowError("Import requires active payload_sha256 in state")
            if token["payload_sha256"] != exp_payload:
                raise WorkflowError("Import grant payload_sha256 mismatch")

            exp_desc = config.get("erp_descriptor_hash") or state.get("erp_descriptor_hash")
            if not exp_desc or not is_hex64(exp_desc):
                raise WorkflowError("Import requires active erp_descriptor_hash in config")
            if token["erp_descriptor_hash"] != exp_desc:
                raise WorkflowError("Import grant erp_descriptor_hash mismatch")

            exp_dry = state.get("dry_run_evidence_digest")
            if not exp_dry or not is_hex64(exp_dry):
                raise WorkflowError("Import requires recorded active dry_run_evidence_digest in state")
            if token["dry_run_evidence_digest"] != exp_dry:
                raise WorkflowError("Import grant dry_run_evidence_digest does not match recorded evidence")

            state.update(
                sub_status="IMPORT",
                status="APPROVED_FOR_BUILD",
                next_roles=["builder"],
                gate=None,
            )
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
    if state.get("sub_status") and state.get("stage") in state.get("stages", {}):
        state["stages"][state["stage"]]["sub_status"] = state["sub_status"]
    state.update(cursor=event["seq"], revision=state["revision"] + 1)
    return state
