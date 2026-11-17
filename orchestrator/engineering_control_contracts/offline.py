"""OFFLINE test doubles only. Never import this as a production workflow engine.

Caller must provide a TemporaryDirectory journal root. State is synthetic, not an
engine export. TrustedPrincipal instances are injected by a test-owned issuer;
there is deliberately no HTTP, login, token parser, real engine or native launcher.
"""

import hashlib
import json
import re
import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock

from jsonschema import Draft202012Validator, FormatChecker

from .contract import ID, OPERATIONS, VERSION, schemas

SCHEMAS = schemas()
OPS = {row[0]: row for row in OPERATIONS}
FORMATS = FormatChecker()


@FORMATS.checks("date-time")
def timestamp(value):
    # jsonschema's optional RFC3339 dependency is absent in this interpreter.
    # Fail closed instead of silently ignoring the required timestamp format.
    if not isinstance(value, str):
        return True  # the schema's type constraint handles non-strings
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})", value):
        return False
    try:
        datetime.fromisoformat(value.upper().replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


class Denied(Exception):
    def __init__(self, code, message="Request denied"):
        self.code = code
        self.body = dict(schema_version=VERSION, error=code, message=message, retryable=False)
        super().__init__(code)


def validate(name, value):
    schema = {"$ref": "#/$defs/" + name, "$defs": SCHEMAS["$defs"]}
    if list(Draft202012Validator(schema, format_checker=FORMATS).iter_errors(value)):
        raise Denied("invalid_request")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def identity():
    return "i-" + uuid.uuid4().hex


@dataclass(frozen=True)
class TrustedPrincipal:
    subject: str
    actor: str
    project: str
    work_item: str
    capabilities: frozenset
    job_id: str | None = None


class TestIssuer:
    """Object-identity trust for tests, not authentication and not serializable."""

    __test__ = False

    def __init__(self):
        self.issued = []

    def issue(
        self,
        subject="owner",
        actor="human",
        project="project-1",
        work_item="work-1",
        capabilities=("read", "decide", "execute", "lifecycle"),
        job_id=None,
    ):
        principal = TrustedPrincipal(subject, actor, project, work_item, frozenset(capabilities), job_id)
        self.issued.append(principal)
        return principal

    def trusts(self, principal):
        return any(principal is issued for issued in self.issued)


class FakeT3:
    """A separately retained runtime simulator survives a FakeBoundary restart."""

    def __init__(self):
        self.runs = {}
        self.launch_calls = 0
        self.cancel_calls = 0
        self.lose_next_response = False

    def launch(self, job):
        self.launch_calls += 1
        if job["job_id"] in self.runs:
            raise AssertionError("Duplicate logical launch")
        self.runs[job["job_id"]] = "running"
        if self.lose_next_response:
            self.lose_next_response = False
            raise TimeoutError("Synthetic lost launch response")

    def cancel(self, job_id):
        self.cancel_calls += 1  # Request only: does not imply termination.


class FakeEngine:
    """Predetermined synthetic gate/assignment fixture, not production routing."""

    def __init__(self):
        self.run_calls = 0
        self.worker_admissions = 0
        self.queued_effects = []
        self.grant_calls = 0
        self.event_calls = 0
        self.qualified_assignments = [initial_state()["assignment"]]

    def require_qualified(self, assignment):
        """Exact synthetic tuple intersection, not T3/provider qualification."""
        validate("Assignment", assignment)
        if assignment not in self.qualified_assignments:
            raise Denied("unsupported_assignment", "Assignment absent from qualified synthetic catalog")

    def record_plan(self, state):
        self.grant_calls += 1
        self.event_calls += 1
        state["approved"] = True
        state["grants"].append(deepcopy(state["review"]))

    def eligible(self, state):
        if not state["approved"] or state["paused"]:
            raise Denied("conflict", "Engine gate blocks admission")
        if state["jobs"]:
            raise Denied("conflict", "Existing logical owner must be reconciled")
        return "builder"


def initial_state():
    h = "a" * 64
    binding = dict(
        work_item_id="work-1",
        project_id="project-1",
        stage="stage-1",
        repository_id="repo-1",
        branch="synthetic",
        base_commit="b" * 40,
        candidate_id=h,
        manifest_sha256=h,
        context_sha256=h,
        plan_sha256=h,
        scope_sha256=h,
        roles_sha256=h,
    )
    assignment = dict(
        provider_instance="synthetic-provider",
        account_ref="synthetic-account",
        model="synthetic-model",
        runtime="native",
        binary_sha256=h,
        binary_version="synthetic-1",
        prompt_sha256=h,
        transport="native-cli",
        role="builder",
        options={"reasoning": "high"},
    )
    return dict(
        revision=1,
        binding=binding,
        assignment=assignment,
        approved=False,
        paused=False,
        review=dict(review_snapshot_id="review-1", gate_id="gate-1", revision=1, binding=deepcopy(binding)),
        grants=[],
        events=[],
        jobs={},
        artifacts={},
        receipts={},
    )


class FakeBoundary:
    """Serial synthetic command boundary with durable intent/receipts for restart tests.

    Atomic JSON rename models local publication, NOT fsync/crash-safe production
    storage. No cross-process guarantee. Unknown production mappings stay disabled.
    """

    def __init__(self, journal_root, issuer, runtime=None, engine=None):
        self.path = Path(journal_root) / "synthetic-control.json"
        if not self.path.parent.is_dir():
            raise ValueError("Test must supply an existing temporary directory")
        self.issuer = issuer
        self.runtime = runtime or FakeT3()
        self.engine = engine or FakeEngine()
        self.lock = RLock()
        self.state = json.loads(self.path.read_text()) if self.path.exists() else initial_state()
        # Lost responses/process exit must not admit a replacement worker.
        for job in self.state["jobs"].values():
            if job["state"] == "intent":
                job["state"] = "uncertain"
        self.save()

    def save(self):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, sort_keys=True))
        temporary.replace(self.path)

    def authorize(self, principal, op, resource):
        if not self.issuer.trusts(principal):
            raise Denied("unauthenticated")
        b = self.state["binding"]
        if principal.project != b["project_id"] or principal.work_item != b["work_item_id"]:
            raise Denied("forbidden")
        if op in ("decisions",):
            needed = "decide"
            if principal.actor != "human":
                raise Denied("forbidden")
        elif op == "execution_request":
            needed = "execute"
        elif op in ("pause", "resume", "cancel"):
            needed = "lifecycle"
            if principal.actor != "human":
                raise Denied("forbidden")
        elif op in ("observations", "results"):
            needed = "monitor"
            if principal.actor != "monitor" or principal.job_id != resource:
                raise Denied("forbidden")
        else:
            needed = "read"
        if needed not in principal.capabilities:
            raise Denied("forbidden")

    def request(self, principal, op, resource="work-1", body=None, key=None, version=VERSION):
        with self.lock:
            if op not in OPS:
                raise Denied("unsupported_operation")
            self.authorize(principal, op, resource)
            if version != VERSION:
                raise Denied("unsupported_version")
            if not Draft202012Validator(ID).is_valid(resource):
                raise Denied("invalid_request")
            row = OPS[op]
            validate(row[3], {} if body is None else body)
            if not row[5]:
                raise Denied("unsupported_operation")
            if row[1] == "get":
                result = self.read(op, resource, body or {})
                validate(row[4], result)
                return deepcopy(result)
            if not isinstance(key, str) or not Draft202012Validator(ID).is_valid(key):
                raise Denied("invalid_request")
            receipt_key = json.dumps(
                [principal.subject, principal.project, principal.work_item, op, resource, key]
            )
            request_hash = digest(body)
            prior = self.state["receipts"].get(receipt_key)
            # Authorization and strict validation first, matching replay BEFORE stale check.
            if prior:
                if prior["hash"] != request_hash:
                    raise Denied("conflict")
                return deepcopy(prior["receipt"])
            if body["expected_revision"] != self.state["revision"]:
                raise Denied("conflict", "Stale authoritative revision")
            if op in ("decisions", "execution_request", "pause", "resume") and resource != "work-1":
                raise Denied("not_found")
            before = deepcopy(self.state)
            try:
                effect, state, jobs = self.mutate(op, resource, body)
                self.state["revision"] += 1
                receipt = dict(
                    schema_version=VERSION,
                    operation_id=identity(),
                    receipt_id=identity(),
                    resource_id=resource,
                    revision=self.state["revision"],
                    effect=effect,
                    effect_state=state,
                    runtime="native",
                    job_ids=jobs,
                    execution_complete=False,
                )
                validate("Receipt", receipt)
                self.state["receipts"][receipt_key] = {"hash": request_hash, "receipt": receipt}
                # Intent AND receipt published before external I/O.
                self.save()
            except Exception:
                self.state = before
                raise
            if op == "execution_request":
                job = self.state["jobs"][jobs[0]]
                try:
                    self.engine.run_calls += 1
                    self.runtime.launch(job)
                    job["state"] = "running"
                except TimeoutError:
                    job["state"] = "uncertain"
                    receipt["effect_state"] = "uncertain"
                self.save()
            if op == "cancel":
                self.runtime.cancel(resource)
            return deepcopy(receipt)

    def event(self, kind, resource):
        self.state["events"].append(
            dict(sequence=len(self.state["events"]) + 1, kind=kind, resource_id=resource)
        )

    def mutate(self, op, resource, body):
        s = self.state
        if op == "decisions":
            if body["decision"] != "approve_plan":
                raise Denied("unsupported_decision")
            review = s["review"]
            if s["approved"] or review["revision"] != s["revision"] or review["binding"] != s["binding"]:
                raise Denied("conflict")
            if any(body[k] != review[k] for k in ("gate_id", "review_snapshot_id")):
                raise Denied("conflict")
            self.engine.record_plan(s)
            self.event("grant", resource)
            return "approval_only", "completed", []
        if op == "execution_request":
            if body["runtime_preference"] != "native":
                raise Denied("unsupported_runtime")
            role = self.engine.eligible(s)
            assignment = deepcopy(s["assignment"])
            self.engine.require_qualified(assignment)
            if assignment["runtime"] != "native" or assignment["role"] != role:
                raise Denied("unsupported_runtime")
            job_id = identity()
            s["jobs"][job_id] = dict(
                job_id=job_id,
                work_item_id="work-1",
                attempt=1,
                binding=deepcopy(s["binding"]),
                assignment=assignment,
                session_id=identity(),
                runtime_ref=identity(),
                state="intent",
                environment_id="synthetic-host",
                runtime_version="synthetic-runtime-1",
                result_accepted=False,
            )
            self.engine.worker_admissions += 1
            self.event("intent", job_id)
            return "execution_requested", "pending", [job_id]
        if op in ("pause", "resume"):
            s["paused"] = op == "pause"
            self.event(op, resource)
            return op + "_requested", "completed", []  # Resume never implies dispatch.
        if resource not in s["jobs"]:
            raise Denied("not_found")
        job = s["jobs"][resource]
        if op == "cancel":
            if job["state"] == "terminated":
                raise Denied("conflict")
            job["state"] = "cancel_pending"
            self.event("cancel", resource)
            return "cancellation_requested", "pending", [resource]
        if op == "observations":
            if any(body[k] != job[k] for k in ("job_id", "attempt", "runtime_ref")):
                raise Denied("conflict")
            if job["state"] == "terminated" and body["state"] != "terminated":
                raise Denied("conflict")
            if job["state"] != "cancel_pending" or body["state"] == "terminated":
                job["state"] = body["state"]
            self.event("observation", resource)
            return "observation_recorded", "completed", [resource]
        if op == "results":
            self.accept_result(job, body["evidence"])
            self.event("result", resource)
            return "result_proposed", "completed", [resource]
        raise Denied("unsupported_operation")

    def accept_result(self, job, evidence):
        if job["result_accepted"] or job["state"] != "terminated":
            raise Denied("conflict")
        for field in (
            "job_id",
            "attempt",
            "binding",
            "assignment",
            "session_id",
            "environment_id",
            "runtime_version",
        ):
            if evidence[field] != job[field]:
                raise Denied("invalid_evidence")
        if (
            evidence["role"] != job["assignment"]["role"]
            or evidence["status"] != "pass"
            or evidence["observer"] != "coordinator"
            or evidence["check_id"] != "required-check"
            or datetime.fromisoformat(evidence["finished_at"].upper().replace("Z", "+00:00"))
            < datetime.fromisoformat(evidence["started_at"].upper().replace("Z", "+00:00"))
        ):
            raise Denied("invalid_evidence")
        if job["assignment"]["role"] == "verifier" and any(
            other["assignment"]["role"] == "builder" and other["session_id"] == job["session_id"]
            for other in self.state["jobs"].values()
        ):
            raise Denied("invalid_evidence", "Verifier must have independent session lineage")
        for artifact in evidence["artifacts"]:
            registered = self.state["artifacts"].get(artifact["artifact_id"])
            if (
                not registered
                or registered["metadata"] != artifact
                or not artifact["complete"]
                or artifact["truncated"]
                or artifact["job_id"] != job["job_id"]
                or artifact["work_item_id"] != job["work_item_id"]
            ):
                raise Denied("invalid_evidence")
            raw = registered["text"].encode()
            if hashlib.sha256(raw).hexdigest() != artifact["sha256"] or len(raw) != artifact["size_bytes"]:
                raise Denied("invalid_evidence")
        # Validation outcome belongs to fake engine, not caller's PASS claim.
        if self.state.get("required_checks_failed", False):
            raise Denied("invalid_evidence")
        job["result_accepted"] = True

    def register_artifact(self, job_id, text, complete=True, truncated=False):
        """Coordinator test fixture method, intentionally absent from caller operations."""
        raw = text.encode()
        if len(raw) > 65536:
            raise Denied("resource_limit")
        metadata = dict(
            artifact_id=identity(),
            work_item_id="work-1",
            job_id=job_id,
            sha256=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw),
            media_type="text/plain",
            complete=complete,
            truncated=truncated,
            registered_by="coordinator",
        )
        validate("Artifact", metadata)
        self.state["artifacts"][metadata["artifact_id"]] = dict(metadata=metadata, text=text)
        self.save()
        return deepcopy(metadata)

    def read(self, op, resource, query):
        s = self.state
        work = dict(
            work_item_id="work-1",
            revision=s["revision"],
            binding=s["binding"],
            paused=s["paused"],
            approval_recorded=s["approved"],
        )
        if op == "capabilities":
            return dict(
                schema_version=VERSION,
                mode="offline_fake_only",
                production_enabled=False,
                t3_execution_enabled=False,
                qualified_assignments=deepcopy(self.engine.qualified_assignments),
                operations=[
                    dict(operation_id=r[0], live_enabled=False, fake_enabled=r[5]) for r in OPERATIONS
                ],
            )
        if op == "list_work_items":
            return dict(items=[work] if query.get("after", 0) == 0 else [], next_cursor=1)
        if op in ("get_work_item", "review_context", "events") and resource != "work-1":
            raise Denied("not_found")
        if op == "get_work_item":
            return work
        if op == "review_context":
            return s["review"]  # immutable snapshot; revision makes stale visible
        if op == "events":
            events = [e for e in s["events"] if e["sequence"] > query.get("after", 0)]
            chosen = events[: query.get("limit", 100)]
            return dict(
                events=chosen,
                next_cursor=chosen[-1]["sequence"] if chosen else query.get("after", 0),
                truncated=len(events) > len(chosen),
            )
        if op == "operation":
            for value in s["receipts"].values():
                if value["receipt"]["operation_id"] == resource:
                    return value["receipt"]
            raise Denied("not_found")
        if op == "job":
            if resource not in s["jobs"]:
                raise Denied("not_found")
            return s["jobs"][resource]
        if op in ("evidence", "evidence_content"):
            if resource not in s["artifacts"]:
                raise Denied("not_found")
            data = s["artifacts"][resource]
            if op == "evidence":
                return data["metadata"]
            return dict(artifact=data["metadata"], text=data["text"], preview_truncated=False)
        raise Denied("unsupported_operation")
