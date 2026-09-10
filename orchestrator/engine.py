"""LangGraph workflow, SQLite jobs, and resumable native dispatch.

Callers hold the execution lock for every operation. Checkpoint replay never
relaunches a job with an uncertain launch intent. No commit/import executor exists.
"""

import json
import os
import sqlite3
import subprocess
import sys
import uuid
from copy import deepcopy
from pathlib import Path
from typing import TypedDict

from adapters import WIRE_SCHEMA, classify_failure, parse_output
from candidates import allowed, changed, freeze, git, recheck, verify_owner_commit
from core import WorkflowError, atomic_write, bytes_hash, canonical, digest, utc, within, write_json
from jsonschema import ValidationError
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context
from normalization import snapshot as finding_snapshot
from routing import apply_event, initial, pause
from store import Store
from validate import validate_document
from worker import process_identity


class GraphState(TypedDict):
    view: dict


class Engine:
    def __init__(self, root, runtime=None, launcher=None):
        self.root = Path(root).resolve()
        self.runtime = Path(runtime or self.root / "orchestrator/var").resolve()
        self.store = Store(self.runtime / "checkpoints.db")
        self.checkpoint_conn = sqlite3.connect(
            self.runtime / "checkpoints.db", timeout=30, check_same_thread=False
        )
        self.checkpoint_conn.execute("PRAGMA synchronous=FULL")
        self.config = self.store.meta("config")
        watermark = self.runtime / "checkpoint-watermark.json"
        if watermark.exists():
            marker = json.loads(watermark.read_text())
            latest = max((e["seq"] for e in self.store.events()), default=0)
            if latest < marker["event_seq"]:
                self.store.set_meta("recovery_required", True)
        self.launcher = launcher
        self.graph = self._graph()
        self.graph_config = {"configurable": {"thread_id": "workflow"}, "recursion_limit": 100}

    def close(self):
        self.checkpoint_conn.close()
        self.store.close()

    def _graph(self):
        graph = StateGraph(GraphState)
        graph.add_node("synchronize", self._synchronize)
        graph.add_node("prepare", self._prepare)
        graph.add_node("dispatch", self._dispatch)
        graph.add_node("collect", self._collect)
        graph.add_node("owner_gate", self._owner_gate)
        graph.add_edge(START, "synchronize")
        graph.add_conditional_edges(
            "synchronize",
            self._route,
            {
                "prepare": "prepare",
                "dispatch": "dispatch",
                "collect": "collect",
                "gate": "owner_gate",
                "end": END,
            },
        )
        graph.add_edge("prepare", "dispatch")
        graph.add_edge("dispatch", "collect")
        graph.add_conditional_edges(
            "collect",
            lambda s: (
                "sync"
                if (
                    self.store.events(s["view"]["cursor"])
                    or s["view"]["next_roles"]
                    or s["view"]["gate"]
                    or s["view"]["status"] == "PAUSED"
                )
                else "end"
            ),
            {"sync": "synchronize", "end": END},
        )
        graph.add_edge("owner_gate", "synchronize")
        return graph.compile(checkpointer=SqliteSaver(self.checkpoint_conn))

    def initialize(self, config):
        if self.config:
            raise WorkflowError("Worktree already initialized")
        config = deepcopy(config)
        if str(self.root) != config["root"]:
            raise WorkflowError("Root identity mismatch")
        work = within(self.root, "docs/ai/work-items/" + config["work_item"])
        for d in ("inbox", "outbox", "runs"):
            (work / d).mkdir(parents=True, exist_ok=True)
        generated = [
            str(work.relative_to(self.root)) + "/runs/",
            str(work.relative_to(self.root)) + "/inbox/",
            str(work.relative_to(self.root)) + "/outbox/",
            str(work.relative_to(self.root)) + "/STATE.json",
            "orchestrator/var/",
        ]
        config["generated"] = generated
        config["scope_hash"] = digest(config["scope"])
        config["candidate"] = freeze(
            self.root,
            config["base_commit"],
            config["branch"],
            config["scope"]["allowed_paths"],
            self.runtime / "initial-candidate",
            generated,
        )
        self.store.set_meta("config", config)
        self.config = config
        # Init creates the checkpoint without starting a native engineering job.
        self.graph.update_state(self.graph_config, {"view": initial(config)}, as_node="collect")
        self.export()
        return self.view()

    def view(self):
        snapshot = self.graph.get_state(self.graph_config)
        if not snapshot.values:
            raise WorkflowError("No workflow checkpoint; run init first")
        return deepcopy(snapshot.values["view"])

    def _synchronize(self, state):
        view = deepcopy(state["view"])
        for event in self.store.events(view["cursor"]):
            view = apply_event(view, event, self.config)
            if event["kind"] == "grant" and event["payload"]["scope"] == "PLAN":
                self.store.consume(event["payload"]["gate_id"])
        return {"view": view}

    def _synchronize_checkpoint(self):
        """Fold durable decisions without preparing or launching any job."""
        view = self.view()
        if self.store.events(view["cursor"]):
            state = self._synchronize({"view": view})
            self.graph.update_state(self.graph_config, state, as_node="collect")
            self.export()
            return state["view"]
        return view

    def owner_decision(self, kind, payload):
        if kind not in ("pause", "resume"):
            raise WorkflowError("Unsupported owner decision")
        view = self._synchronize_checkpoint()
        # Reject invalid owner input before it can poison the durable event stream.
        apply_event(view, {"seq": view["cursor"] + 1, "kind": kind, "payload": payload}, self.config)
        self.store.event("owner-" + uuid.uuid4().hex, kind, payload)
        return self.run()

    def _route(self, state):
        v = state["view"]
        if v["status"] == "PAUSED":
            return "gate"
        if v["active_jobs"]:
            return (
                "dispatch"
                if any(self.store.job(j)["status"] == "CREATED" for j in v["active_jobs"])
                else "collect"
            )
        if v["gate"]:
            return "gate"
        if v["next_roles"]:
            return "prepare"
        return "end"

    def _owner_gate(self, state):
        v = state["view"]
        interrupt(
            {
                "gate": v["gate"],
                "status": v["status"],
                "pause_reason": v["pause_reason"],
                "plan_revision_hash": v["plan_revision_hash"],
                "scope_hash": v["scope_hash"],
                "candidate_id": v["candidate"]["candidate_id"],
            }
        )
        # Resumption carries no authorization. Only validated SQLite events can change state.
        if not self.store.events(v["cursor"]):
            raise WorkflowError("No recorded owner decision to resume")
        return state

    def _prepare(self, state):
        v = self._synchronize(state)["view"]
        if v["status"] == "PAUSED" or v["gate"]:
            return {"view": v}
        if not v["plan_granted"] and "builder" in v["next_roles"]:
            raise WorkflowError("Builder dispatch requires standing PLAN grant")
        recheck(self.root, v["candidate"]["manifest"], self.config["generated"])
        plan = within(self.root, self.store.meta("plan_artifact", self.config["plan_path"]))
        if bytes_hash(plan.read_bytes()) != v["plan_revision_hash"]:
            raise WorkflowError("Approved plan artifact drift")
        if any(
            not allowed(p, self.config["scope"]["allowed_paths"]) and not allowed(p, self.config["generated"])
            for p in changed(self.root, self.config["base_commit"])
        ):
            raise WorkflowError("Changed path outside approved contract")
        jobs = []
        work = within(self.root, "docs/ai/work-items/" + v["work_item"])
        for role in v["next_roles"]:
            pin = self.config["roles"][role]
            key = digest([v["work_item"], v["stage"], role, v["candidate"]["candidate_id"], v["attempt"]])
            job_id = "job-" + key[:24]
            existing = self.store.job(job_id)
            if existing:
                self._materialize_job(existing, work)
                jobs.append(job_id)
                continue
            destination = self.runtime / "jobs" / job_id
            destination.mkdir(parents=True, exist_ok=True)
            role_name = role if role in ("architect", "reviewer", "builder", "verifier") else "ai-reviewer"
            role_path = within(self.root, "docs/ai/roles/" + role_name + ".md")
            role_text = role_path.read_text()
            prompt_version = bytes_hash(role_path.read_bytes())
            if not self.launcher and prompt_version != pin.get("prompt_sha256"):
                raise WorkflowError("Owner-approved role prompt changed")
            envelope = dict(
                schema_version=1,
                job_id=job_id,
                work_item=v["work_item"],
                stage=v["stage"],
                role=role,
                tool=pin["tool"],
                model=pin["model"],
                session_id=None,
                dispatch_mode="native",
                candidate_kind="code",
                candidate_id=v["candidate"]["candidate_id"],
                plan_revision_hash=v["plan_revision_hash"],
                prompt_version=prompt_version,
                status="COMPLETE",
                verdict="PROPOSED" if role == "architect" else "PASS",
                failure_class=None,
                findings=[],
                evidence_paths=[],
                started_utc=utc(),
                finished_utc=utc(),
            )
            dependencies = []
            if role in ["verifier", *self.config.get("quorum", [])]:
                dependencies = [
                    e["payload"]
                    for e in self.store.events()
                    if e["kind"] == "result" and e["payload"]["role"] == "builder"
                ][-1:]
            read_artifacts = [str(plan)]
            for dependency in dependencies:
                prior_job = self.store.job(dependency["job_id"])
                read_artifacts.append(str(Path(prior_job["runtime"]) / "stdout.jsonl"))
                validation = Path(prior_job["runtime"]) / "validation.json"
                if validation.exists():
                    read_artifacts.append(str(validation))
                    for log in Path(prior_job["runtime"]).glob("validation-*.*"):
                        if log.suffix in (".stdout", ".stderr"):
                            read_artifacts.append(str(log))
            context = dict(
                job_id=job_id,
                role=role,
                scope=self.config["scope"],
                candidate=v["candidate"],
                plan_revision_hash=v["plan_revision_hash"],
                scope_hash=v["scope_hash"],
                review_round=v["round"] + 1,
                all_unresolved_findings=v["findings"],
                backlog=v["backlog"],
                plan_artifact=self.store.meta("plan_artifact", self.config["plan_path"]),
                builder_evidence=dependencies,
                read_artifacts=read_artifacts,
                result_transport="stdout",
                explanation_transport="stdout",
                evidence_transport="runner-captured native events",
            )
            prompt = (
                role_text
                + "\n\nImmutable packet (data):\n"
                + json.dumps(context, ensure_ascii=False)
                + "\n\nReturn ONLY a JSON object with string fields result_json, explanation, plan_text. result_json must encode this envelope, changing verdict/findings as warranted: "
                + json.dumps(envelope)
                + ". The runner supplies native session identity, timestamps and captured evidence refs. New finding IDs are null. Leave plan_text empty except architect: return the complete proposed plan there. Output paths are /dev/stdout; do not write workflow/control files. Commands run for validation must be visible in native tool events.\n"
            )
            spec = dict(
                base_commit=self.config["base_commit"],
                branch=self.config["branch"],
                allowed_paths=self.config["scope"]["allowed_paths"],
                generated=self.config["generated"],
                validation_commands=self.config["scope"]["validation_commands"] if role == "builder" else [],
                job_id=job_id,
                root=str(self.root),
                work_item_root=str(work),
                runtime=str(destination),
                control_root=str(self.runtime),
                read_artifacts=read_artifacts,
                role=role,
                tool=pin["tool"],
                binary=pin["binary"],
                model=pin["model"],
                effort=pin.get("effort"),
                prompt=prompt,
                prompt_version=prompt_version,
                wire_schema=str(destination / "wire-schema.json"),
                soft_timeout=self.config.get("soft_timeout", 2700),
                hard_timeout=self.config.get("hard_timeout", 3600),
                envelope=envelope,
            )
            job = self.store.create_job(
                key,
                dict(
                    job_id=job_id,
                    role=role,
                    candidate_id=v["candidate"]["candidate_id"],
                    plan_revision_hash=v["plan_revision_hash"],
                    runtime=str(destination),
                    spec_path=str(destination / "spec.json"),
                    spec=spec,
                    launch_attempts=0,
                ),
            )
            self._materialize_job(job, work)
            jobs.append(job["job_id"])
        v.update(active_jobs=jobs, next_roles=[])
        if any(self.store.job(j)["role"] == "builder" for j in jobs):
            v["status"] = "BUILD_IN_PROGRESS"
        return {"view": v}

    def _materialize_job(self, job, work):
        # SQLite records the exact timestamp-bearing inputs before any artifact write.
        # A crash at any file boundary re-exports the same durable inputs on replay.
        destination = Path(job["runtime"])
        prompt = job["spec"]["prompt"].encode()
        atomic_write(work / "runs" / job["job_id"] / "inputs" / "packet.md", prompt, immutable=True)
        atomic_write(work / "inbox" / (job["role"] + ".md"), prompt)
        write_json(destination / "wire-schema.json", WIRE_SCHEMA, immutable=True)
        write_json(job["spec_path"], job["spec"], immutable=True)

    def _dispatch(self, state):
        # A pending checkpoint can resume here directly: validate at the side effect.
        v = self._synchronize(state)["view"]
        if v["status"] == "PAUSED" or v["gate"]:
            return {"view": v}
        for job_id in v["active_jobs"]:
            job = self.store.job(job_id)
            if job["status"] != "CREATED":
                continue
            recheck(self.root, v["candidate"]["manifest"], self.config["generated"])
            plan = within(self.root, self.store.meta("plan_artifact", self.config["plan_path"]))
            if bytes_hash(plan.read_bytes()) != v["plan_revision_hash"]:
                raise WorkflowError("Approved plan artifact drift before dispatch")
            if (
                job["candidate_id"] != v["candidate"]["candidate_id"]
                or job["plan_revision_hash"] != v["plan_revision_hash"]
                or job["spec"]["envelope"]["stage"] != v["stage"]
            ):
                raise WorkflowError("Prepared job binding changed before dispatch")
            if job["role"] == "builder" and not v["plan_granted"]:
                raise WorkflowError("Builder dispatch requires standing PLAN grant")
            self.store.update_job(job_id, "LAUNCH_INTENT", launch_attempts=job["launch_attempts"] + 1)
            try:
                if self.launcher:
                    self.launcher(job)
                    self.store.update_job(job_id, "RUNNING")
                else:
                    with open(Path(job["runtime"]) / "worker-stderr.txt", "ab") as err:
                        process = subprocess.Popen(
                            [sys.executable, str(Path(__file__).parent / "worker.py"), job["spec_path"]],
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=err,
                            start_new_session=True,
                            cwd=self.root,
                        )
                    self.store.update_job(
                        job_id, "RUNNING", worker_pid=process.pid, worker_start=process_identity(process.pid)
                    )
            except OSError:
                # Popen failed before returning a process: one proven non-launch retry.
                if job["launch_attempts"] < 1:
                    self.store.update_job(job_id, "CREATED", no_child=True)
                else:
                    self.store.update_job(job_id, "LAUNCH_FAILED", no_child=True)
                    pause(v, "MISSING_BINARY")
        return {"view": v}

    def _collect(self, state):
        v = self._synchronize(state)["view"]
        if v["status"] == "PAUSED" or v["gate"]:
            return {"view": v}
        for job_id in v["active_jobs"]:
            job = self.store.job(job_id)
            destination = Path(job["runtime"])
            terminal = destination / "terminal.json"
            if job["status"] == "ACCEPTED":
                continue  # Its durable result event is replayed by synchronize.
            if terminal.exists():
                try:
                    observation = json.loads(terminal.read_text())
                    if not isinstance(observation, dict):
                        raise ValueError("terminal must be object")
                except (ValueError, OSError):
                    self.store.update_job(job_id, "RECONCILIATION_REQUIRED", failure="MALFORMED_RESULT")
                    pause(v, "RECONCILIATION_REQUIRED")
                    continue
                if observation.get("job_id") != job_id:
                    pause(v, "RECONCILIATION_REQUIRED")
                    continue
                if observation.get("phase") != "TERMINAL":
                    pause(v, "RECONCILIATION_REQUIRED")
                    continue
                try:
                    event = self.accept(job, observation, v)
                    self.store.event("result-" + job_id, "result", event)
                    self.store.update_job(job_id, "ACCEPTED")
                except (WorkflowError, ValueError, ValidationError, OSError, TypeError, KeyError) as exc:
                    self.store.update_job(job_id, "RECONCILIATION_REQUIRED", failure=type(exc).__name__)
                    pause(v, "RECONCILIATION_REQUIRED")
            elif job["status"] == "CREATED":
                # A proven failed launch remains eligible for the one retry on next run.
                continue
            elif (
                not self.launcher
                and job.get("worker_pid")
                and process_identity(job["worker_pid"]) == job.get("worker_start")
            ):
                continue
            elif self.launcher and job["status"] == "RUNNING":
                continue
            else:
                pause(v, "RECONCILIATION_REQUIRED")
        return {"view": v}

    def accept(self, job, observation, view):
        destination = Path(job["runtime"])
        stdout = destination / "stdout.jsonl"
        if not stdout.is_file() or stdout.stat().st_size > 20_000_000:
            raise WorkflowError("EVIDENCE_UNAVAILABLE")
        raw = stdout.read_text()
        spec = job["spec"]
        if observation["exit_code"] != 0 or observation.get("timeout"):
            body = deepcopy(spec["envelope"])
            stderr = (destination / "stderr.txt").read_text() if (destination / "stderr.txt").exists() else ""
            body.update(
                status="FAILED",
                verdict="FAILED",
                failure_class=classify_failure(raw + "\n" + stderr, observation.get("timeout", False)),
            )
            body["session_id"] = observation.get("session_id")
            wire = {
                "explanation": "Native process failed; inspect private local job observations.",
                "plan_text": "",
            }
        else:
            session, body, wire, _events = (
                parse_output(raw, spec["tool"]) if not self.launcher else self.launcher.parse(job, raw)
            )
            for field in (
                "job_id",
                "work_item",
                "stage",
                "role",
                "candidate_kind",
                "candidate_id",
                "plan_revision_hash",
                "prompt_version",
            ):
                if body.get(field) != spec["envelope"][field]:
                    raise WorkflowError("Stale or mismatched result binding")
            for old in self.store.events():
                if (
                    old["kind"] == "result"
                    and old["payload"]["job_id"] != job["job_id"]
                    and old["payload"]["result"].get("session_id") == session
                ):
                    raise WorkflowError("Native session reused across independent jobs")
            body.update(
                tool=spec["tool"],
                model=spec["model"],
                session_id=session,
                dispatch_mode="native" if not self.launcher else "manual",
            )
            body.update(started_utc=observation["started_utc"], finished_utc=observation["finished_utc"])
            body["evidence_paths"] = [
                {
                    "artifact_id": job["job_id"] + "-native-events",
                    "sha256": bytes_hash(raw.encode()),
                    "visibility": "public",
                }
            ]
            validate_document("result-envelope", body)
            known_ids = {f["finding_id"] for f in view["findings"] + view["backlog"]}
            incoming_ids = [f["finding_id"] for f in body["findings"] if f["finding_id"] is not None]
            if len(incoming_ids) != len(set(incoming_ids)) or not set(incoming_ids) <= known_ids:
                raise WorkflowError("Unknown or duplicate finding ID")
            # Normalization is not assumed from agent claims; total-cycle escalation stays active.
            for index, f in enumerate(body.get("findings", [])):
                if not set(f.get("affected_requirements", [])) <= set(self.config["scope"]["requirements"]):
                    raise WorkflowError("Finding references an unknown requirement")
                if not self.launcher:
                    f["snapshot"] = finding_snapshot(
                        f,
                        self.root,
                        self.config["scope"],
                        destination / ("normalization-" + str(index) + ".json"),
                        job["job_id"] + "-normalization-" + str(index),
                    )
        body.update(started_utc=observation["started_utc"], finished_utc=observation["finished_utc"])
        # Captured native event log is a real artifact, not an agent-provided path.
        body["evidence_paths"] = [
            {
                "artifact_id": job["job_id"] + "-native-events",
                "sha256": bytes_hash(raw.encode()),
                "visibility": "public",
            }
        ]
        validate_document("result-envelope", body)
        work = within(self.root, "docs/ai/work-items/" + view["work_item"])
        archive = work / "runs" / job["job_id"] / "results" / (job["job_id"] + ".json")
        write_json(archive, body, immutable=True)
        atomic_write(
            work / "runs" / job["job_id"] / "explanations" / (job["job_id"] + ".md"),
            wire["explanation"].encode(),
            immutable=True,
        )
        event = dict(job_id=job["job_id"], role=job["role"], result=body)
        if body["status"] == "COMPLETE":
            if job["role"] == "architect" and body["verdict"] != "BLOCKED":
                if not wire["plan_text"].strip():
                    raise WorkflowError("Architect returned no plan")
                plan = work / "runs" / job["job_id"] / "results" / "plan.md"
                atomic_write(plan, wire["plan_text"].encode(), immutable=True)
                event["new_plan_hash"] = bytes_hash(wire["plan_text"].encode())
                self.store.set_meta("plan_artifact", str(plan.relative_to(self.root)))
            elif job["role"] == "builder":
                if not self.launcher:
                    validation = json.loads((destination / "validation.json").read_text())
                    if not validation.get("complete"):
                        raise WorkflowError("Required validation did not complete")
                    event["candidate"] = json.loads(
                        (destination / "tested-candidate/binding.json").read_text()
                    )
                    recheck(self.root, event["candidate"]["manifest"], self.config["generated"])
                    event["validation"] = validation
                else:
                    event["candidate"] = freeze(
                        self.root,
                        self.config["base_commit"],
                        self.config["branch"],
                        self.config["scope"]["allowed_paths"],
                        destination / "candidate",
                        self.config["generated"],
                    )
                    event["validation"] = {"complete": True, "passed": True, "mode": "SYNTHETIC"}
            else:
                recheck(self.root, view["candidate"]["manifest"], self.config["generated"])
                if job["role"] == "verifier" and body["verdict"] == "PASS":
                    builds = [
                        e["payload"]
                        for e in self.store.events()
                        if e["kind"] == "result" and e["payload"]["role"] == "builder"
                    ]
                    if not builds or not builds[-1].get("validation", {}).get("passed"):
                        raise WorkflowError("Verifier PASS cannot override failing required tests")
        return event

    def _drive(self, graph_input):
        with tracing_context(enabled=False):
            for checkpoint in self.graph.stream(
                graph_input, self.graph_config, stream_mode="checkpoints", durability="sync"
            ):
                view = checkpoint.get("values", {}).get("view")
                if view:
                    self._export_view(view)

    def run(self):
        if self.store.meta("recovery_required", False):
            raise WorkflowError("Backup restore requires explicit external-operation reconciliation")
        snapshot = self.graph.get_state(self.graph_config)
        if not snapshot.values:
            raise WorkflowError("No initialized checkpoint")
        v = snapshot.values["view"]
        if any(t.interrupts for t in snapshot.tasks):
            if not self.store.events(v["cursor"]):
                self.export()
                return self.view()
            self._drive(Command(resume={"wake": True}))
        elif snapshot.next:
            self._drive(None)
        else:
            self._drive({"view": v})
        self.export()
        return self.view()

    def approve(self, token):
        if self.store.meta("recovery_required", False):
            raise WorkflowError("Recovery review required before approval creation")
        validate_document("approval-token", token)
        if token["status"] != "ISSUED":
            raise WorkflowError("Only a newly issued owner token can enter approval")
        view = self._synchronize_checkpoint()
        if (
            not view["gate"]
            or token["scope"] != view["gate"]["scope"]
            or token["gate_id"] != view["gate"]["gate_id"]
            or token["work_item"] != view["work_item"]
        ):
            raise WorkflowError("Approval does not match pending gate")
        if token["scope"] == "PLAN":
            required = dict(
                plan_revision_hash=view["plan_revision_hash"],
                scope_hash=view["scope_hash"],
                repository_id=str(self.root),
                branch=self.config["branch"],
            )
            if (
                any(token.get(k) != value for k, value in required.items())
                or view["stage"] not in token["stages"]
            ):
                raise WorkflowError("PLAN binding mismatch")
        elif token["scope"] == "COMMIT":
            recheck(self.root, view["candidate"]["manifest"], self.config["generated"])
            required = dict(
                candidate_id=view["candidate"]["candidate_id"],
                manifest_hash=view["candidate"]["manifest_hash"],
                repository_id=str(self.root),
                branch=self.config["branch"],
                expected_parent_sha=self.config["base_commit"],
                expected_tree_oid=view["candidate"]["tree_oid"],
            )
            if any(token.get(k) != value for k, value in required.items()):
                raise WorkflowError("COMMIT binding mismatch")
        else:
            raise WorkflowError("ERP approvals disabled until adoption gates pass")
        self.store.grant(token)
        self.store.event("grant-" + token["token_id"], "grant", token)
        if token["scope"] == "COMMIT":
            with self.store.conn:
                self.store.conn.execute(
                    "UPDATE workflow_grants SET status='RESERVED' WHERE token_id=?", (token["token_id"],)
                )
            write_json(self.runtime / "operations" / token["job_id"] / "intent.json", token, immutable=True)
        return self.run()

    def recover_backup(self, evidence, reset_budget):
        if not self.store.meta("recovery_required", False) or not reset_budget:
            raise WorkflowError("Recovery requires explicit owner evidence and budget-reset decision")
        evidence_hash = bytes_hash(Path(evidence).read_bytes())
        if git(self.root, "rev-parse", "HEAD").decode().strip() != self.config["base_commit"]:
            raise WorkflowError(
                "External Git operation postdates backup; reconcile from a newer backup or reviewed recovery plan"
            )
        observations = []
        for path in (self.runtime / "jobs").glob("*/progress.json"):
            data = json.loads(path.read_text())
            for pid_key, start_key in (("worker_pid", "worker_start"), ("native_pid", "native_start")):
                if data.get(pid_key) and process_identity(data[pid_key]) == data.get(start_key):
                    raise WorkflowError("Post-backup worker still alive; recovery remains paused")
            observations.append(
                {"job_id": path.parent.name, "progress_sha256": bytes_hash(path.read_bytes())}
            )
        candidate = freeze(
            self.root,
            self.config["base_commit"],
            self.config["branch"],
            self.config["scope"]["allowed_paths"],
            self.runtime / "recovery-candidates" / uuid.uuid4().hex,
            self.config["generated"],
        )
        payload = {
            "candidate": candidate,
            "owner_evidence_sha256": evidence_hash,
            "observations": observations,
            "attempt_offset": len(list((self.runtime / "jobs").glob("*"))) + 1,
            "explicit_budget_reset": True,
        }
        with self.store.conn:
            self.store.conn.execute("UPDATE workflow_grants SET status='INVALIDATED'")
            self.store.conn.execute(
                "UPDATE workflow_jobs SET status='OWNER_RECOVERY_REVIEWED' WHERE status!='ACCEPTED'"
            )
            self.store.conn.execute(
                "INSERT INTO workflow_events(event_id,kind,payload,created_utc) VALUES (?,?,?,?)",
                ("recovery-" + uuid.uuid4().hex, "recovery_reviewed", canonical(payload).decode(), utc()),
            )
            self.store.conn.execute(
                "INSERT INTO workflow_meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("recovery_required", "false"),
            )
        return self.run()

    def revise_scope(self, scope, reason):
        view = self.view()
        if view["status"] != "PAUSED" or view["active_jobs"]:
            raise WorkflowError("Scope revision requires all external jobs reconciled")
        candidate = freeze(
            self.root,
            self.config["base_commit"],
            self.config["branch"],
            scope["allowed_paths"],
            self.runtime / "owner-candidates" / uuid.uuid4().hex,
            self.config["generated"],
        )
        config = deepcopy(self.config)
        config.update(scope=scope, scope_hash=digest(scope))
        self.store.reconfigure(
            config,
            "scope-" + uuid.uuid4().hex,
            "scope_revised",
            {"scope_hash": config["scope_hash"], "candidate": candidate, "reason": reason},
        )
        self.config = config
        return self.run()

    def advance_stage(self):
        view = self.view()
        if not view["committed"] or view["status"] != "VERIFIED_FOR_RELEASE" or view["active_jobs"]:
            raise WorkflowError("Stage advancement requires the verified owner commit")
        index = self.config["stages"].index(view["stage"]) + 1
        if index >= len(self.config["stages"]):
            raise WorkflowError("All configured stages are complete")
        stage = self.config["stages"][index]
        commits = [e["payload"]["commit"] for e in self.store.events() if e["kind"] == "owner_commit"]
        base = git(self.root, "rev-parse", "HEAD").decode().strip()
        if not commits or base != commits[-1]:
            raise WorkflowError("HEAD differs from the reconciled owner commit")
        config = deepcopy(self.config)
        scope = config.get("stage_scopes", {}).get(stage, config["scope"])
        config.update(base_commit=base, scope=scope, scope_hash=digest(scope))
        candidate = freeze(
            self.root,
            base,
            config["branch"],
            scope["allowed_paths"],
            self.runtime / "stages" / stage / "initial-candidate",
            config["generated"],
        )
        refs = [
            {
                "artifact_id": e["payload"]["job_id"],
                "sha256": digest(e["payload"]["result"]),
                "visibility": "public",
            }
            for e in self.store.events()
            if e["kind"] == "result"
            and e["payload"]["role"] == "verifier"
            and e["payload"]["result"]["stage"] == view["stage"]
        ]
        self.store.reconfigure(
            config,
            "stage-" + stage,
            "stage_started",
            {
                "stage": stage,
                "scope_hash": config["scope_hash"],
                "candidate": candidate,
                "evidence_refs": refs,
            },
        )
        self.config = config
        return self.run()

    def reconcile_job(self, job_id, evidence):
        view = self.view()
        if view["status"] != "PAUSED" or job_id not in view["active_jobs"]:
            raise WorkflowError("Only paused active jobs can be owner-reconciled")
        job = self.store.job(job_id)
        progress = Path(job["runtime"]) / "progress.json"
        observation = json.loads(progress.read_text()) if progress.exists() else job
        for pid_key, start_key in (("worker_pid", "worker_start"), ("native_pid", "native_start")):
            if observation.get(pid_key) and process_identity(observation[pid_key]) == observation.get(
                start_key
            ):
                raise WorkflowError("Recorded worker/native process still alive")
        evidence = Path(evidence)
        evidence_hash = bytes_hash(evidence.read_bytes())
        self.store.event(
            "reconcile-" + job_id,
            "reconcile_job",
            {
                "job_id": job_id,
                "role": job["role"],
                "owner_evidence_sha256": evidence_hash,
                "decision": "ABANDONED_AFTER_OWNER_REVIEW",
            },
        )
        self.store.update_job(job_id, "OWNER_RECONCILED")
        return self.run()

    def refresh_candidate(self, reason):
        view = self.view()
        if view["status"] != "PAUSED" or view["active_jobs"]:
            raise WorkflowError("Reconcile all jobs before refreshing the source candidate")
        candidate = freeze(
            self.root,
            self.config["base_commit"],
            self.config["branch"],
            self.config["scope"]["allowed_paths"],
            self.runtime / "owner-candidates" / uuid.uuid4().hex,
            self.config["generated"],
        )
        self.store.event(
            "candidate-" + uuid.uuid4().hex, "refresh_candidate", {"candidate": candidate, "reason": reason}
        )
        with self.store.conn:
            self.store.conn.execute(
                "UPDATE workflow_grants SET status='INVALIDATED' WHERE status IN ('ISSUED','RESERVED')"
            )
        return self.run()

    def record_owner_commit(self):
        view = self.view()
        if not view["gate"] or view["gate"]["scope"] != "OWNER_COMMIT":
            raise WorkflowError("No authorized owner commit pending")
        grant = self.store.grant_for(view["gate"]["gate_id"])
        sha = verify_owner_commit(self.root, grant["token"])
        self.store.complete_grant(
            "commit-" + grant["token"]["job_id"],
            view["gate"]["gate_id"],
            {"commit": sha, "token_id": grant["token"]["token_id"]},
        )
        write_json(
            self.runtime / "operations" / grant["token"]["job_id"] / "complete.json",
            {"commit": sha, "token_id": grant["token"]["token_id"]},
            immutable=True,
        )
        return self.run()

    def export(self):
        self._export_view(self.view())

    def _export_view(self, v):
        work = within(self.root, "docs/ai/work-items/" + v["work_item"])
        document = dict(
            schema_version=1,
            authority="sqlite-checkpoint-export-only",
            work_item=v["work_item"],
            stage=v["stage"],
            status=v["status"],
            revision=v["revision"],
            plan_revision_hash=v["plan_revision_hash"],
            candidate_id=v["candidate"]["candidate_id"],
            active_jobs=v["active_jobs"],
            completed_dependencies=v["completed_dependencies"],
            approval_refs=v["approval_refs"],
            escalation={
                "unsuccessful_cycles": v["unsuccessful_cycles"],
                "unchanged_rounds": v["unchanged_rounds"],
                "last_snapshot_digest": digest(v["previous_snapshots"]) if v["previous_snapshots"] else None,
            },
            pause_reason=v["pause_reason"],
            resume_to=v["resume_to"],
            stages=v["stages"],
            exported_utc=utc(),
        )
        validate_document("state-export", document)
        write_json(work / "STATE.json", document)
        self.store.export_ledger(self.runtime / "ledger" / "events.jsonl")
        for event in self.store.events():
            if event["kind"] == "result" and event["seq"] <= v["cursor"]:
                payload = event["payload"]
                write_json(work / "outbox" / (payload["role"] + ".json"), payload["result"])
        if not self.store.meta("recovery_required", False):
            write_json(
                self.runtime / "checkpoint-watermark.json",
                {"event_seq": max((e["seq"] for e in self.store.events()), default=0)},
            )
