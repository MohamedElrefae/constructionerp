"""LangGraph workflow, SQLite jobs, and resumable native dispatch.

Callers hold the execution lock for every operation. Checkpoint replay never
relaunches a job with an uncertain launch intent. No commit/import executor exists.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import uuid
import re
from copy import deepcopy
from pathlib import Path
from typing import TypedDict

from adapters import WIRE_SCHEMA, classify_failure, parse_output
from candidates import allowed, changed, freeze, git, recheck, verify_owner_commit
from core import (
    DuplicateKeyConflict,
    GrantReconciliationRequired,
    PreconditionError,
    RecoveryError,
    ValidationError as CoreValidationError,
    WorkflowError,
    atomic_write,
    bytes_hash,
    canonical,
    digest,
    utc,
    within,
    write_json,
)
from jsonschema import ValidationError as JsonSchemaValidationError

SUPPORTED_STAGES = {"0", "1", "2", "3", "4"}
compute_scope_hash = digest


def extract_scope_proposal(plan_text: str) -> dict | None:
    match = re.search(r"```scope-proposal\s*\n(.*?)\n```", plan_text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except Exception as exc:
        raise WorkflowError(f"MALFORMED_RESULT: Invalid JSON in scope-proposal block: {exc}")

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from langsmith import tracing_context
from normalization import snapshot as finding_snapshot
from routing import apply_event, initial, pause
from schema_source import FAILURES
from store import Store
from validate import validate_document
from worker import process_identity


class GraphState(TypedDict):
    view: dict


def _ensure_quarantine_dir(private_root, job_id):
    """Ensures quarantine root and job directory exist, are owned by current user,
    are not symlinks, and are set to mode 0700.
    Returns Path(q_dir) on success, or None if verification fails.
    """
    if not private_root:
        return None
    try:
        p_root = Path(private_root)
        if not p_root.exists() or p_root.is_symlink():
            return None

        q_root = p_root / "quarantine"
        if q_root.is_symlink():
            return None
        q_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(q_root, 0o700)
        st_root = q_root.stat()
        if st_root.st_uid != os.getuid() or not q_root.is_dir() or (st_root.st_mode & 0o777) != 0o700:
            return None

        q_dir = q_root / job_id
        if q_dir.is_symlink():
            return None
        q_dir.mkdir(mode=0o700, exist_ok=True)
        os.chmod(q_dir, 0o700)
        st_dir = q_dir.stat()
        if st_dir.st_uid != os.getuid() or not q_dir.is_dir() or (st_dir.st_mode & 0o777) != 0o700:
            return None

        return q_dir
    except Exception:
        return None


def _quarantine_or_delete_file(path, fname, job_id, private_root=None):
    """Quarantines a raw artifact to protected private storage with restricted modes.

    - Quarantine root and job dir set to 0700.
    - Quarantined file set to 0600.
    - Verifies ownership (os.getuid()) and rejects symlink/non-regular targets.
    - Always ensures path does not remain in public destination.
    """
    path = Path(path)
    quarantined = False
    if private_root and (path.is_symlink() or path.exists()):
        try:
            # Reject symlinks and non-regular files for source
            if not path.is_symlink() and path.is_file():
                st_src = path.stat()
                if st_src.st_uid == os.getuid():
                    q_dir = _ensure_quarantine_dir(private_root, job_id)
                    if q_dir:
                        target = q_dir / fname
                        # Reject target if it already exists as symlink, directory, or wrong ownership
                        if target.is_symlink() or (target.exists() and (not target.is_file() or target.stat().st_uid != os.getuid())):
                            pass
                        else:
                            if target.exists():
                                target.unlink()
                            shutil.move(str(path), str(target))
                            os.chmod(target, 0o600)
                            st_tgt = target.stat()
                            if (
                                st_tgt.st_uid == os.getuid()
                                and target.is_file()
                                and not target.is_symlink()
                                and (st_tgt.st_mode & 0o777) == 0o600
                            ):
                                quarantined = True
        except Exception:
            quarantined = False

    if not quarantined:
        try:
            if path.is_symlink() or path.exists():
                path.unlink()
        except OSError:
            pass


def _quarantine_or_delete_runtime_artifacts(destination, job_id, private_root=None):
    for fname in ("stdout.jsonl", "stderr.txt"):
        fpath = destination / fname
        _quarantine_or_delete_file(fpath, fname, job_id, private_root)


def _sanitize_stage4_runtime_artifacts(destination, job_id, private_root, catalog_terms):
    """Sanitizes runtime artifacts on disk for stage4 jobs.

    If catalog_terms is None (terms could not be reliably loaded):
      Quarantines or deletes runtime artifacts; does NOT leave partially sanitized public files.
    If catalog_terms is a set:
      Sanitizes both stdout.jsonl and stderr.txt in-place using sanitize_public_text.
      If invalid UTF-8 is encountered, quarantines/deletes the affected artifact(s).
    """
    if catalog_terms is None:
        _quarantine_or_delete_runtime_artifacts(destination, job_id, private_root)
        return

    from stage4 import sanitize_public_text

    for fname in ("stdout.jsonl", "stderr.txt"):
        fpath = destination / fname
        if not fpath.exists() or fpath.is_symlink():
            continue
        try:
            raw_bytes = fpath.read_bytes()
            text = raw_bytes.decode("utf-8")
            sanitized = sanitize_public_text(text, catalog_terms=catalog_terms)
            fpath.write_text(sanitized, encoding="utf-8")
        except UnicodeDecodeError:
            # Invalid UTF-8: cannot safely sanitize without leaking bytes.
            # Quarantine or delete this specific artifact.
            _quarantine_or_delete_file(fpath, fname, job_id, private_root)
        except Exception:
            _quarantine_or_delete_file(fpath, fname, job_id, private_root)


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
        if self.config and self.config.get("roles"):
            if "roles_hash" not in self.config:
                self.config["roles_hash"] = digest(self.config["roles"])
                self.store.set_meta("config", self.config)
            self.sync_roles_mirror()
        watermark = self.runtime / "checkpoint-watermark.json"
        if watermark.exists():
            marker = json.loads(watermark.read_text())
            latest = max((e["seq"] for e in self.store.events()), default=0)
            if latest < marker["event_seq"]:
                self.store.set_meta("recovery_required", True)
        self.launcher = launcher
        self.graph = self._graph()
        self.graph_config = {"configurable": {"thread_id": "workflow"}, "recursion_limit": 100}

    def sync_roles_mirror(self):
        """Ensure the derived file mirror orchestrator/roles.json matches authoritative SQLite config."""
        if not self.config or not self.config.get("roles"):
            return
        roles_path = self.root / "orchestrator/roles.json"
        roles_data = self.config["roles"]
        expected_bytes = canonical(roles_data) + b"\n"
        if not roles_path.exists() or roles_path.read_bytes() != expected_bytes:
            write_json(roles_path, roles_data)

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

    def _recheck_candidate(self, candidate):
        if candidate.get("kind") == "stage4-proposal":
            if not candidate.get("export_sha256") or not candidate.get("proposal_sha256"):
                raise WorkflowError("Malformed stage4-proposal candidate binding")
            expected_id = digest({
                "kind": "stage4-proposal",
                "export_sha256": candidate["export_sha256"],
                "proposal_sha256": candidate["proposal_sha256"],
            })
            if candidate["candidate_id"] != expected_id:
                raise WorkflowError("Stage 4 proposal candidate identity mismatch")
        elif "manifest" in candidate:
            recheck(self.root, candidate["manifest"], self.config["generated"])

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
            "orchestrator/roles.json",
            "orchestrator/var/",
        ]
        config["generated"] = generated
        context_paths = config.get("read_only_context_paths", [])
        if context_paths:
            mandatory_files = ("AGENTS.md", "SESSION_MEMORY.md")
            for mf in mandatory_files:
                if mf not in context_paths:
                    raise CoreValidationError(f"Mandatory read-only context path missing from configuration: {mf}")
            for mf in mandatory_files:
                if not (self.root / mf).is_file():
                    raise CoreValidationError(f"Mandatory read-only context file does not exist on disk: {mf}")
            for cp in context_paths:
                for ap in config.get("scope", {}).get("allowed_paths", []):
                    ap_clean = ap.rstrip("/*")
                    if cp == ap or cp.startswith(ap_clean + "/"):
                        raise CoreValidationError(f"Read-only context path {cp} intersects with scope.allowed_paths {ap}")
                for gen in generated:
                    gen_clean = gen.rstrip("/")
                    if cp == gen or cp.startswith(gen_clean + "/"):
                        raise CoreValidationError(f"Read-only context path {cp} intersects with generated path {gen}")
        config["scope_hash"] = digest(config["scope"])
        config["roles_hash"] = digest(config.get("roles", {}))
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

    def adopt_historical(self, work_item, erp_descriptor=None):
        if self.config:
            raise WorkflowError("Worktree already initialized")
        if work_item != "erp-arabic-bilingual-data":
            raise WorkflowError(f"Unsupported historical adoption work-item: {work_item}")

        work = within(self.root, "docs/ai/work-items/" + work_item)
        for d in ("inbox", "outbox", "runs", "evidence"):
            (work / d).mkdir(parents=True, exist_ok=True)

        if not erp_descriptor:
            erp_descriptor = {
                "erp_checkout": "/home/mohamed/frappe-bench/apps/construction",
                "bench_root": "/home/mohamed/frappe-bench",
                "site": "v16.localhost",
                "site_classification": "non-production test",
                "private_root": "/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4",
            }
        erp_descriptor_hash = digest(erp_descriptor)

        # Directly revalidate all historical provenance from referenced files on disk (fail-closed)
        from stage4 import derive_stage4_candidate_id, is_hex64, verify_historical_provenance

        verified_prov = verify_historical_provenance(
            erp_descriptor["erp_checkout"], erp_descriptor["bench_root"]
        )

        manifest_meta = verified_prov["stage_4_foundation"]
        export_sha256 = manifest_meta["export_file_sha256"]

        historical_stages = {
            "0": {
                "sub_status": None,
                "historical": True,
                "evidence_refs": [
                    {
                        "artifact_id": verified_prov["stage_0"]["artifact_id"],
                        "sha256": verified_prov["stage_0"]["evidence_sha256"],
                        "visibility": "public",
                    }
                ],
            },
            "1": {
                "sub_status": None,
                "historical": True,
                "evidence_refs": [
                    {
                        "artifact_id": verified_prov["stage_1"]["artifact_id"],
                        "sha256": verified_prov["stage_1"]["evidence_sha256"],
                        "visibility": "public",
                    }
                ],
            },
            "2": {
                "sub_status": None,
                "historical": True,
                "evidence_refs": [
                    {
                        "artifact_id": verified_prov["stage_2"]["artifact_id"],
                        "sha256": verified_prov["stage_2"]["evidence_sha256"],
                        "visibility": "public",
                    }
                ],
            },
            "3": {
                "sub_status": None,
                "historical": True,
                "evidence_refs": [
                    {
                        "artifact_id": verified_prov["stage_3"]["artifact_id"],
                        "sha256": verified_prov["stage_3"]["evidence_sha256"],
                        "visibility": "public",
                    }
                ],
            },
            "4": {
                "sub_status": "PROPOSAL_PENDING",
                "historical": False,
                "evidence_refs": [],
            },
        }

        # Read expected identities from the private export catalog and store in content-addressed blobs
        export_file_path = Path(erp_descriptor["private_root"]) / "account_catalog_20260910_121018.json"
        if not export_file_path.exists():
            raise WorkflowError(f"Private export file missing: {export_file_path}")
        export_bytes = export_file_path.read_bytes()
        actual_exp_sha = hashlib.sha256(export_bytes).hexdigest()
        if actual_exp_sha != export_sha256:
            raise WorkflowError(f"Export file hash mismatch: got {actual_exp_sha}, expected {export_sha256}")
        from stage4 import store_private_blob
        store_private_blob(erp_descriptor["private_root"], export_bytes, expected_sha=export_sha256)
        export_catalog = json.loads(export_bytes)
        expected_identities = [r["identity"] for r in export_catalog.get("rows", [])]
        from stage4 import (
            derive_identities_digest,
            derive_stage4_candidate_id,
            is_hex64,
            verify_historical_provenance,
        )
        identities_digest = derive_identities_digest(expected_identities)

        initial_proposal_hash = digest(
            {"schema": "stage4-proposal/v1", "export_sha256": export_sha256, "rows": []}
        )
        stage4_candidate_id = derive_stage4_candidate_id(export_sha256, initial_proposal_hash)

        initial_candidate = {
            "kind": "stage4-proposal",
            "candidate_id": stage4_candidate_id,
            "export_sha256": export_sha256,
            "proposal_sha256": initial_proposal_hash,
            "manifest_hash": stage4_candidate_id,
            "identities_digest": identities_digest,
        }

        plan_path = "docs/translation/ERP_ARABIC_AND_BILINGUAL_DATA_END_TO_END_PLAN.md"
        plan_bytes = (self.root / plan_path).read_bytes()
        plan_hash = bytes_hash(plan_bytes)

        scope = {
            "allowed_paths": [
                "construction/data/localization/stage4_export_manifest.json",
                "construction/services/account_language_proposal.py",
                "construction/services/account_review_bundle.py",
                "construction/services/report_bilingual_extension.py",
                "construction/tests/test_stage4_review_bundle.py",
                "construction/tests/test_stage4_account_language.py",
            ],
            "requirements": [
                "CANONICAL_PLAN §11.1",
                "CANONICAL_PLAN §11.2",
                "CANONICAL_PLAN §11.3",
                "CANONICAL_PLAN §11.4",
            ],
            "validation_commands": [
                "python3 construction/tests/test_stage4_review_bundle.py"
            ],
        }
        scope_hash = digest(scope)

        generated = [
            str(work.relative_to(self.root)) + "/runs/",
            str(work.relative_to(self.root)) + "/inbox/",
            str(work.relative_to(self.root)) + "/outbox/",
            str(work.relative_to(self.root)) + "/STATE.json",
            "orchestrator/roles.json",
            "orchestrator/var/",
        ]

        roles_data = json.loads((self.root / "orchestrator/roles.json").read_text())
        roles_hash = digest(roles_data)

        config = dict(
            root=str(self.root),
            work_item=work_item,
            stages=["0", "1", "2", "3", "4"],
            stage="4",
            sub_status="PROPOSAL_PENDING",
            next_roles=[],
            historical_stages=historical_stages,
            plan_granted=False,
            branch=git(self.root, "branch", "--show-current").decode().strip(),
            base_commit=git(self.root, "rev-parse", "HEAD").decode().strip(),
            scope=scope,
            scope_hash=scope_hash,
            plan_path=plan_path,
            plan_revision_hash=plan_hash,
            candidate=initial_candidate,
            generated=generated,
            roles=roles_data,
            roles_hash=roles_hash,
            quorum=["ai-a1", "ai-a2", "ai-a3"],
            erp_target=erp_descriptor,
            erp_descriptor=erp_descriptor,
            erp_descriptor_hash=erp_descriptor_hash,
            export_sha256=export_sha256,
            identities_digest=identities_digest,
            adopt_historical=True,
            initialized_utc=utc(),
        )

        self.store.set_meta("config", config)
        self.config = config

        view_state = initial(config)
        self.graph.update_state(self.graph_config, {"view": view_state}, as_node="collect")
        self.export()
        return self.view()

    def view(self):
        snapshot = self.graph.get_state(self.graph_config)
        if not snapshot.values:
            raise WorkflowError("No workflow checkpoint; run init first")
        v = deepcopy(snapshot.values["view"])
        if not v.get("roles_hash") and self.config:
            v["roles_hash"] = self.config.get("roles_hash") or digest(self.config.get("roles", {}))
        return v

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

    def owner_decision(self, kind, payload, *, action_id=None, request_hash=None):
        if kind not in ("pause", "resume"):
            raise WorkflowError("Unsupported owner decision")
        payload = dict(payload)
        if action_id is not None:
            payload["action_id"] = action_id
        if request_hash is not None:
            payload["request_hash"] = request_hash
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
        if not v["plan_granted"] and ("builder" in v["next_roles"] or "proposer" in v["next_roles"]):
            raise WorkflowError("Builder or proposer dispatch requires standing PLAN grant")
        self._recheck_candidate(v["candidate"])
        plan = within(self.root, self.store.meta("plan_artifact", self.config["plan_path"]))
        if bytes_hash(plan.read_bytes()) != v["plan_revision_hash"]:
            raise WorkflowError("Approved plan artifact drift")
        if v["candidate"].get("kind") != "stage4-proposal" and any(
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
            expected_artifact_id = None
            expected_artifact_kind = None
            neutral_mounts = []
            private_root = None
            if v["candidate"].get("kind") == "stage4-proposal":
                private_root = (
                    self.config.get("erp_descriptor", {}).get("private_root")
                    or self.config.get("private_root")
                    or "/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4"
                )
                host_private_out = destination / "private_out"
                host_private_out.mkdir(mode=0o700, parents=True, exist_ok=True)
                try:
                    os.chmod(str(host_private_out), 0o700)
                except OSError:
                    pass
                neutral_mounts.append({
                    "host_path": str(host_private_out),
                    "sandbox_path": "/tmp/workspace/private_output",
                    "writable": True,
                })
                if role == "proposer":
                    expected_artifact_id = f"stage4-proposal-{job_id}"
                    expected_artifact_kind = "stage4-proposal"
                    exp_sha = v["candidate"]["export_sha256"]
                    catalog_blob = Path(private_root) / "blobs" / f"{exp_sha}.json"
                    if not catalog_blob.exists() or catalog_blob.is_symlink():
                        raise WorkflowError("Export catalog blob missing in private storage")
                    if hashlib.sha256(catalog_blob.read_bytes()).hexdigest() != exp_sha:
                        raise WorkflowError("Export catalog blob digest mismatch (TOCTOU prevented)")
                    neutral_mounts.append({
                        "host_path": str(catalog_blob),
                        "sandbox_path": "/tmp/workspace/private_inputs/account_catalog.json",
                        "writable": False,
                    })
                elif role in self.config.get("quorum", []):
                    expected_artifact_id = f"stage4-review-{role}-{job_id}"
                    expected_artifact_kind = "stage4-review"
                    proposal_sha = v["candidate"]["proposal_sha256"]
                    proposal_blob = Path(private_root) / "blobs" / f"{proposal_sha}.json"
                    if not proposal_blob.exists() or proposal_blob.is_symlink():
                        raise WorkflowError("Proposal blob missing in private storage")
                    if hashlib.sha256(proposal_blob.read_bytes()).hexdigest() != proposal_sha:
                        raise WorkflowError("Proposal blob digest mismatch")
                    neutral_mounts.append({
                        "host_path": str(proposal_blob),
                        "sandbox_path": "/tmp/workspace/private_inputs/proposal.json",
                        "writable": False,
                    })
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
                candidate_kind=v["candidate"].get("kind", "code"),
                candidate_id=v["candidate"]["candidate_id"],
                plan_revision_hash=v["plan_revision_hash"],
                prompt_version=prompt_version,
                status="COMPLETE",
                verdict="PROPOSED" if role in ("architect", "proposer") else "PASS",
                failure_class=None,
                findings=[],
                evidence_paths=[],
                started_utc=utc(),
                finished_utc=utc(),
            )
            if expected_artifact_id:
                placeholder_ref = {
                    "artifact_id": expected_artifact_id,
                    "sha256": "0" * 64,
                    "visibility": "private",
                }
                envelope["evidence_paths"] = [placeholder_ref]
                envelope["private_artifact_refs"] = [placeholder_ref]
                if role == "proposer":
                    envelope["export_sha256"] = v["candidate"]["export_sha256"]
                    envelope["proposal_sha256"] = "0" * 64
                else:
                    envelope["export_sha256"] = v["candidate"]["export_sha256"]
                    envelope["proposal_sha256"] = v["candidate"]["proposal_sha256"]
            dependencies = []
            if role in ["verifier", *self.config.get("quorum", [])]:
                dependencies = [
                    e["payload"]
                    for e in self.store.events()
                    if e["kind"] == "result" and e["payload"]["role"] == "builder"
                ][-1:]
            contract = within(self.root, self.config["plan_path"])
            read_artifacts = list(dict.fromkeys([str(contract), str(plan)]))
            for cp in self.config.get("read_only_context_paths", []):
                resolved_cp = self.root / cp
                if resolved_cp.is_file():
                    read_artifacts.append(str(resolved_cp))
            for dependency in dependencies:
                prior_job = self.store.job(dependency["job_id"])
                read_artifacts.append(str(Path(prior_job["runtime"]) / "stdout.jsonl"))
                validation = Path(prior_job["runtime"]) / "validation.json"
                if validation.exists():
                    read_artifacts.append(str(validation))
                    for log in Path(prior_job["runtime"]).glob("validation-*.*"):
                        if log.suffix in (".stdout", ".stderr"):
                            read_artifacts.append(str(log))
            validation_reports = {}
            report_refs = []
            if role in ("reviewer", "verifier"):
                # Reports are evidence, never verdicts or authorization. Discover only
                # this work item's validation reports in execution/control checkouts.
                evidence_roots = {
                    work / "evidence",
                    Path(__file__).resolve().parents[1] / "docs/ai/work-items" / v["work_item"] / "evidence",
                }
                for evidence_root in sorted(evidence_roots):
                    for source in sorted(evidence_root.glob("*validation.json")):
                        if source.is_symlink() or any(p.is_symlink() for p in source.parents):
                            continue
                        try:
                            text = source.read_text()
                            report = json.loads(text)
                        except (OSError, UnicodeError, ValueError):
                            continue
                        if not isinstance(report, dict):
                            continue
                        binding = report.get("candidate")
                        if not isinstance(binding, dict) or not isinstance(report.get("commands"), list):
                            continue
                        if (
                            binding.get("candidate_id") != v["candidate"]["candidate_id"]
                            or binding.get("manifest") != v["candidate"]["manifest"]
                            or binding.get("tree_oid") != v["candidate"]["tree_oid"]
                            or digest(binding["manifest"]) != binding["candidate_id"]
                        ):
                            continue
                        sha = bytes_hash(text.encode())
                        name = "candidate-validation-" + sha + ".json"
                        if name in validation_reports:
                            continue
                        validation_reports[name] = text
                        target = str(destination / name)
                        read_artifacts.append(target)
                        report_refs.append(dict(path=target, sha256=sha, source=str(source)))
            approval = None
            if role == "builder":
                grants = [
                    event["payload"]
                    for event in self.store.events()
                    if event["kind"] == "grant"
                    and event["payload"]["scope"] == "PLAN"
                    and event["payload"]["token_id"] in v["approval_refs"]
                    and event["payload"]["plan_revision_hash"] == v["plan_revision_hash"]
                    and event["payload"]["scope_hash"] == v["scope_hash"]
                    and v["stage"] in event["payload"]["stages"]
                ]
                if not grants:
                    raise WorkflowError("Standing PLAN grant evidence unavailable")
                approval = dict(
                    owner_plan_approved=True,
                    gate_id=grants[-1]["gate_id"],
                    plan_revision_hash=v["plan_revision_hash"],
                    scope_hash=v["scope_hash"],
                    stage=v["stage"],
                    repository_id=str(self.root),
                    authorization="Checkpoint-confirmed builder execution; non-consumable attestation only",
                )
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
                candidate_validation_reports=report_refs,
                owner_approval_attestation=approval,
                result_schema=str(within(self.root, "orchestrator/schemas/v1/result-envelope.json")),
                finding_schema=str(within(self.root, "orchestrator/schemas/v1/finding.json")),
                read_artifacts=read_artifacts,
                result_transport="stdout",
                explanation_transport="stdout",
                evidence_transport="runner-captured native events",
            )
            if expected_artifact_id:
                context["expected_artifact_id"] = expected_artifact_id
                context["expected_artifact_kind"] = expected_artifact_kind
                context["expected_output_alias"] = "output.json"
                context["expected_output_path"] = "/tmp/workspace/private_output/output.json"
                if role == "proposer" and v["candidate"].get("kind") == "stage4-proposal":
                    context["private_input_path"] = "/tmp/workspace/private_inputs/account_catalog.json"
            stage_instruction = ""
            if role == "architect" and v.get("stage") == "plan":
                stage_instruction = (
                    "\nPLANNING STAGE ARCHITECT INSTRUCTIONS:\n"
                    "1. Formulate the technical architectural plan for the requested work item.\n"
                    "2. In plan_text, you MUST embed a fenced code block with info-string 'scope-proposal' conforming to schema 'scope-proposal/v1'.\n"
                    "3. Format:\n"
                    "```scope-proposal\n"
                    "{\n"
                    '  "schema": "scope-proposal/v1",\n'
                    '  "implementation_stages": ["1"],\n'
                    '  "scope": {\n'
                    '    "allowed_paths": ["<path1>", ...],\n'
                    '    "requirements": ["<req1>", ...],\n'
                    '    "validation_commands": [["<cmd>", "<arg>", ...], ...]\n'
                    "  }\n"
                    "}\n"
                    "```\n"
                    "4. implementation_stages must be a non-empty unique list containing supported stages ('1', '2', '3', '4').\n"
                    "5. Set verdict to 'PROPOSED' (or 'BLOCKED' if requirements cannot be fulfilled).\n"
                )
            elif role == "proposer" and expected_artifact_id and v["candidate"].get("kind") == "stage4-proposal":
                stage_instruction = (
                    "\nSTAGE 4 PROPOSER INSTRUCTIONS:\n"
                    "1. Read private account catalog at /tmp/workspace/private_inputs/account_catalog.json.\n"
                    "2. Formulate Arabic accounting translation proposals for all 81 accounts.\n"
                    "3. Write the resulting JSON object to /tmp/workspace/private_output/output.json with format: "
                    '{"export_sha256": "' + v["candidate"]["export_sha256"] + '", "rows": [{"identity": ..., "english": ..., "is_group": ..., "proposal": {"arabic": ..., "confidence": "high"}}]}.\n'
                    "4. In result_json, return status: COMPLETE, verdict: PROPOSED, findings: [].\n"
                    "5. Scope requirement IDs are strictly: "
                    + json.dumps(self.config["scope"]["requirements"]) + ".\n"
                )
            prompt = (
                role_text
                + stage_instruction
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
                neutral_mounts=neutral_mounts,
                private_root=str(private_root) if private_root else None,
                expected_artifact_id=expected_artifact_id,
                expected_artifact_kind=expected_artifact_kind,
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
                    validation_reports=validation_reports,
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
        for name, text in job.get("validation_reports", {}).items():
            atomic_write(destination / name, text.encode(), immutable=True)
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
            self._recheck_candidate(v["candidate"])
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
                except (WorkflowError, ValueError, JsonSchemaValidationError, OSError, TypeError, KeyError) as exc:
                    # Only a known WorkflowError code may cross into durable state.
                    # Never persist its diagnostic suffix or classify arbitrary text.
                    code = str(exc).partition(":")[0] if isinstance(exc, WorkflowError) else None
                    failure = code if code in FAILURES else type(exc).__name__
                    self.store.update_job(job_id, "RECONCILIATION_REQUIRED", failure=failure)
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
        """Public entry point for result acceptance.

        Wraps _accept_inner() in error-path cleanup. Uses purely job-local state:
        - If catalog_terms can be loaded reliably, sanitizes artifacts.
        - If catalog_terms cannot be loaded reliably (missing/corrupt/symlink/schema),
          quarantines or deletes raw runtime artifacts; does not leave partially
          sanitized public files.
        - Invalid UTF-8 is quarantined/deleted without leaking bytes or replacing
          the original acceptance exception.
        """
        destination = Path(job["runtime"])
        job_id = job["job_id"]
        is_stage4 = view.get("candidate", {}).get("kind") == "stage4-proposal"
        private_root = None
        job_catalog_terms = None

        if is_stage4:
            private_root = (
                self.config.get("erp_descriptor", {}).get("private_root")
                or self.config.get("private_root")
                or "/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4"
            )
            export_sha = view.get("candidate", {}).get("export_sha256")
            if export_sha and isinstance(export_sha, str) and len(export_sha) == 64:
                try:
                    cat_blob = Path(private_root) / "blobs" / f"{export_sha}.json"
                    if cat_blob.is_file() and not cat_blob.is_symlink():
                        cat_doc = json.loads(cat_blob.read_bytes().decode("utf-8"))
                        if isinstance(cat_doc, dict) and isinstance(cat_doc.get("rows"), list):
                            expected_ids = [
                                r["identity"] for r in cat_doc["rows"] if isinstance(r, dict) and "identity" in r
                            ]
                            from stage4 import derive_identities_digest

                            if derive_identities_digest(expected_ids) == self.config.get("identities_digest"):
                                terms = set(expected_ids)
                                for r in cat_doc["rows"]:
                                    if isinstance(r, dict):
                                        if r.get("english"):
                                            terms.add(r["english"])
                                        if r.get("account_name"):
                                            terms.add(r["account_name"])
                                job_catalog_terms = terms
                except Exception:
                    job_catalog_terms = None

        try:
            return self._accept_inner(job, observation, view)
        except Exception:
            if is_stage4:
                try:
                    _sanitize_stage4_runtime_artifacts(
                        destination, job_id, private_root, catalog_terms=job_catalog_terms
                    )
                except Exception:
                    # Cleanup must NEVER replace the original acceptance exception
                    pass
            raise

    def _accept_inner(self, job, observation, view):
        destination = Path(job["runtime"])
        stdout = destination / "stdout.jsonl"
        if not stdout.is_file() or stdout.stat().st_size > 20_000_000:
            raise WorkflowError("EVIDENCE_UNAVAILABLE")
        raw = stdout.read_text(encoding="utf-8")
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

        verified_private_ref = None
        prop_meta = None
        rev_meta = None
        bundle_meta = None

        if view["candidate"].get("kind") == "stage4-proposal":
            private_root = (
                self.config.get("erp_descriptor", {}).get("private_root")
                or self.config.get("private_root")
                or "/home/mohamed/frappe-bench/sites/v16.localhost/private/stage4"
            )
            if body["status"] == "COMPLETE" and job["role"] in ("proposer", *self.config.get("quorum", [])):
                host_output = destination / "private_out" / "output.json"
                record_path = destination / "private-acceptance-record.json"
                expected_art_id = spec.get("expected_artifact_id")
                if not expected_art_id:
                    raise WorkflowError("Expected private artifact ID not configured")

                # Reject agent-selected artifact IDs or arbitrary paths returned in evidence_paths
                for ep in body.get("evidence_paths", []):
                    aid = ep.get("artifact_id")
                    if aid and aid != expected_art_id and aid != job["job_id"] + "-native-events":
                        raise WorkflowError("Agent-selected artifact ID rejected")

                catalog_blob = Path(private_root) / "blobs" / f"{view['candidate']['export_sha256']}.json"
                if not catalog_blob.exists() or catalog_blob.is_symlink():
                    raise WorkflowError("Export catalog blob missing in private storage")
                try:
                    cat_doc = json.loads(catalog_blob.read_text())
                except (ValueError, OSError) as exc:
                    raise WorkflowError(f"Export catalog blob corrupted: {exc}") from exc
                if not isinstance(cat_doc, dict) or "rows" not in cat_doc or not isinstance(cat_doc["rows"], list):
                    raise WorkflowError("Export catalog blob invalid schema")
                expected_identities = [r["identity"] for r in cat_doc["rows"]]
                from stage4 import derive_identities_digest
                if derive_identities_digest(expected_identities) != self.config["identities_digest"]:
                    raise WorkflowError("Export catalog identities digest mismatch")
                catalog_terms = set(expected_identities)
                for r in cat_doc["rows"]:
                    if r.get("english"):
                        catalog_terms.add(r["english"])
                    if r.get("account_name"):
                        catalog_terms.add(r["account_name"])

                if record_path.exists():
                    if not record_path.is_file() or record_path.is_symlink():
                        raise WorkflowError("Invalid acceptance record file")
                    try:
                        rec = json.loads(record_path.read_text())
                    except (ValueError, OSError) as exc:
                        raise WorkflowError(f"Corrupted acceptance record: {exc}") from exc
                    if not isinstance(rec, dict):
                        raise WorkflowError("Acceptance record must be a JSON object")
                    if rec.get("job_id") != job["job_id"] or rec.get("role") != job["role"]:
                        raise WorkflowError("Invalid acceptance record binding")
                    if rec.get("artifact_id") != expected_art_id:
                        raise WorkflowError("Acceptance record artifact_id mismatch")
                    blob_sha = rec.get("sha256")
                    if not blob_sha or not isinstance(blob_sha, str) or len(blob_sha) != 64:
                        raise WorkflowError("Invalid acceptance record sha256")

                    from stage4 import read_private_blob
                    blob_bytes = read_private_blob(private_root, blob_sha)
                    if hashlib.sha256(blob_bytes).hexdigest() != blob_sha:
                        raise WorkflowError("Recovered blob digest mismatch")
                    try:
                        blob_doc = json.loads(blob_bytes)
                    except (ValueError, OSError) as exc:
                        raise WorkflowError(f"Corrupted private blob in acceptance recovery: {exc}") from exc
                    if not isinstance(blob_doc, dict):
                        raise WorkflowError("Recovered private blob must be a JSON object")

                    if job["role"] == "proposer":
                        if blob_doc.get("schema") != "stage4-proposal/v1":
                            raise WorkflowError("Recovered proposal blob invalid schema")
                        if blob_doc.get("export_sha256") != view["candidate"]["export_sha256"]:
                            raise WorkflowError("Recovered proposal blob export_sha256 mismatch with current candidate")
                        prop_rows = blob_doc.get("rows")
                        if not isinstance(prop_rows, list) or len(prop_rows) != len(expected_identities):
                            raise WorkflowError("Recovered proposal blob rows count mismatch")
                        from stage4 import derive_proposal_hash
                        expected_prop_sha = derive_proposal_hash(prop_rows, view["candidate"]["export_sha256"])
                        if expected_prop_sha != blob_sha:
                            raise WorkflowError("Recovered proposal blob content hash mismatch")
                        if set(r.get("identity") for r in prop_rows) != set(expected_identities):
                            raise WorkflowError("Recovered proposal blob identities mismatch")
                        from stage4 import derive_identities_digest
                        if derive_identities_digest([r.get("identity") for r in prop_rows]) != self.config["identities_digest"]:
                            raise WorkflowError("Recovered proposal blob identities digest mismatch")
                        prop_meta = {
                            "proposal_sha256": blob_sha,
                            "artifact_sha256": blob_sha,
                            "rows_count": len(prop_rows),
                            "export_sha256": view["candidate"]["export_sha256"],
                        }
                    elif job["role"] in self.config.get("quorum", []):
                        if blob_doc.get("schema") != "stage4-panel-review/v1":
                            raise WorkflowError("Recovered review blob invalid schema")
                        if blob_doc.get("role") != job["role"]:
                            raise WorkflowError("Recovered review blob role mismatch")
                        if blob_doc.get("proposal_sha256") != view["candidate"]["proposal_sha256"]:
                            raise WorkflowError("Recovered review blob proposal_sha256 mismatch with current candidate")
                        session = body.get("session_id")
                        if not session or blob_doc.get("session_id") != session:
                            raise WorkflowError("Recovered review blob session_id mismatch with observed session")
                        row_decisions = blob_doc.get("row_decisions")
                        if not isinstance(row_decisions, list) or len(row_decisions) != len(expected_identities):
                            raise WorkflowError("Recovered review blob row decisions count mismatch")
                        if set(r.get("identity") for r in row_decisions) != set(expected_identities):
                            raise WorkflowError("Recovered review blob identities mismatch")
                        from stage4 import derive_identities_digest
                        if derive_identities_digest([r.get("identity") for r in row_decisions]) != self.config["identities_digest"]:
                            raise WorkflowError("Recovered review blob identities digest mismatch")
                        renewal_required = (
                            bool(blob_doc.get("renewal_required"))
                            or any(
                                r.get("suggested_arabic") and r.get("suggested_arabic") != r.get("proposed_arabic")
                                for r in row_decisions
                            )
                            or any(f.get("classification") == "arabic_value_change" for f in blob_doc.get("findings", []))
                        )
                        blocking = [f for f in blob_doc.get("findings", []) if f.get("blocking", True)]
                        for idx, r in enumerate(row_decisions):
                            if r.get("decision") == "rejected":
                                blocking.append({
                                    "finding_id": f"rejected-{job['role']}-{idx}",
                                    "role": job["role"],
                                    "blocking": True,
                                    "classification": "row_rejected",
                                    "summary": f"Reviewer {job['role']} rejected row at index {idx}",
                                })
                        sanitized_blocking = [
                            {
                                "finding_id": f.get("finding_id", f"finding-{i}"),
                                "role": job["role"],
                                "blocking": bool(f.get("blocking", True)),
                                "classification": f.get("classification", "generic"),
                                "summary": sanitize_public_text(f.get("summary", ""), catalog_terms=catalog_terms),
                            }
                            for i, f in enumerate(blocking)
                        ]
                        rev_meta = {
                            "review_sha256": blob_sha,
                            "role": job["role"],
                            "session_id": session,
                            "verdict": blob_doc.get("verdict", "PASS"),
                            "renewal_required": renewal_required,
                            "blocking_findings": sanitized_blocking,
                        }
                    else:
                        raise WorkflowError(f"Unsupported role for acceptance record recovery: {job['role']}")

                    verified_private_ref = {
                        "artifact_id": expected_art_id,
                        "sha256": blob_sha,
                        "visibility": "private",
                    }
                    body["export_sha256"] = view["candidate"]["export_sha256"]
                    body["proposal_sha256"] = (
                        prop_meta["proposal_sha256"] if job["role"] == "proposer" else view["candidate"]["proposal_sha256"]
                    )
                    body["private_artifact_refs"] = [verified_private_ref]
                else:
                    if not host_output.exists() or host_output.is_symlink():
                        raise WorkflowError("Private output file missing or invalid symlink")

                    if job["role"] == "proposer":
                        from stage4 import validate_and_store_proposal
                        prop_meta = validate_and_store_proposal(
                            private_root,
                            host_output,
                            expected_export_sha=view["candidate"]["export_sha256"],
                            expected_identities=expected_identities,
                            expected_identities_digest=self.config["identities_digest"],
                            export_catalog_path=catalog_blob if catalog_blob.exists() else None,
                        )
                        blob_sha = prop_meta["proposal_sha256"]
                        rec_meta = prop_meta
                    elif job["role"] in self.config.get("quorum", []):
                        from stage4 import validate_and_store_review
                        rev_meta = validate_and_store_review(
                            private_root,
                            host_output,
                            expected_role=job["role"],
                            expected_proposal_sha=view["candidate"]["proposal_sha256"],
                            expected_identities=expected_identities,
                            expected_session_id=body.get("session_id"),
                            catalog_terms=catalog_terms,
                        )
                        blob_sha = rev_meta["review_sha256"]
                        rec_meta = rev_meta

                    # Persist and fsync acceptance record before unlinking output.json
                    rec = {
                        "job_id": job["job_id"],
                        "role": job["role"],
                        "artifact_id": expected_art_id,
                        "sha256": blob_sha,
                        "meta": rec_meta,
                        "accepted_utc": utc(),
                    }
                    tmp_rec = destination / f".private-acceptance-{os.getpid()}.tmp"
                    with open(tmp_rec, "w") as f:
                        json.dump(rec, f, sort_keys=True)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(tmp_rec, record_path)
                    try:
                        dir_fd = os.open(str(destination), os.O_RDONLY)
                        try:
                            os.fsync(dir_fd)
                        finally:
                            os.close(dir_fd)
                    except OSError:
                        pass

                    try:
                        host_output.unlink()
                    except OSError:
                        pass

                    verified_private_ref = {
                        "artifact_id": expected_art_id,
                        "sha256": blob_sha,
                        "visibility": "private",
                    }
                    body["export_sha256"] = view["candidate"]["export_sha256"]
                    body["proposal_sha256"] = (
                        prop_meta["proposal_sha256"] if job["role"] == "proposer" else view["candidate"]["proposal_sha256"]
                    )
                    body["private_artifact_refs"] = [verified_private_ref]

                if job["role"] in self.config.get("quorum", []):
                    from stage4 import compose_and_store_bundle_and_payload
                    prior_quorum = {
                        e["payload"]["role"]: e["payload"]
                        for e in self.store.events()
                        if e["kind"] == "result" and e["payload"]["role"] in self.config.get("quorum", [])
                    }
                    all_quorum_roles = set(prior_quorum.keys()) | {job["role"]}
                    if all_quorum_roles == set(self.config.get("quorum", [])):
                        all_passed = (
                            rev_meta["verdict"] == "PASS"
                            and not rev_meta["renewal_required"]
                            and not rev_meta.get("blocking_findings")
                        )
                        for qrole, qpayload in prior_quorum.items():
                            qmeta = qpayload.get("review_meta", {})
                            if (
                                qpayload["result"]["verdict"] != "PASS"
                                or qmeta.get("verdict") != "PASS"
                                or qmeta.get("renewal_required")
                                or qmeta.get("blocking_findings")
                            ):
                                all_passed = False
                                break
                        if all_passed:
                            a2_sha = (
                                rev_meta["review_sha256"]
                                if job["role"] == "ai-a2"
                                else prior_quorum["ai-a2"]["review_meta"]["review_sha256"]
                            )
                            intent_path = destination / "bundle-composition-intent.json"
                            write_json(intent_path, {
                                "job_id": job["job_id"],
                                "candidate_id": view["candidate"]["candidate_id"],
                                "proposal_sha256": view["candidate"]["proposal_sha256"],
                                "started_utc": utc(),
                            })
                            panel_digests = {job["role"]: rev_meta["review_sha256"]}
                            for qrole, qpayload in prior_quorum.items():
                                panel_digests[qrole] = qpayload["review_meta"]["review_sha256"]

                            bundle_meta = compose_and_store_bundle_and_payload(
                                private_root,
                                view["candidate"]["proposal_sha256"],
                                a2_sha,
                                self.config.get("company", "Elrefae"),
                                view["candidate"]["candidate_id"],
                                view["candidate"]["export_sha256"],
                                self.config.get("erp_descriptor_hash", "0" * 64),
                                panel_digests,
                                required_roles=tuple(self.config["quorum"]),
                            )
                            write_json(destination / "bundle-composition-complete.json", bundle_meta)
            elif body["status"] == "COMPLETE":
                if view["candidate"].get("export_sha256"):
                    body["export_sha256"] = view["candidate"]["export_sha256"]
                if view["candidate"].get("proposal_sha256"):
                    body["proposal_sha256"] = view["candidate"]["proposal_sha256"]
                if view["candidate"].get("bundle_sha256"):
                    body["bundle_sha256"] = view["candidate"]["bundle_sha256"]
                if view["candidate"].get("payload_sha256"):
                    body["payload_sha256"] = view["candidate"]["payload_sha256"]
                if "private_artifact_refs" in view["candidate"]:
                    body["private_artifact_refs"] = deepcopy(view["candidate"]["private_artifact_refs"])
            else:
                if "export_sha256" in spec["envelope"]:
                    body["export_sha256"] = spec["envelope"]["export_sha256"]
                if "proposal_sha256" in spec["envelope"]:
                    body["proposal_sha256"] = spec["envelope"]["proposal_sha256"]
                if "private_artifact_refs" in spec["envelope"]:
                    body["private_artifact_refs"] = deepcopy(spec["envelope"]["private_artifact_refs"])

        # Collect catalog terms to sanitize public text (fail-closed)
        catalog_terms = set()
        if view["candidate"].get("kind") == "stage4-proposal":
            catalog_blob = Path(private_root) / "blobs" / f"{view['candidate']['export_sha256']}.json"
            if not catalog_blob.exists() or catalog_blob.is_symlink():
                raise WorkflowError("Export catalog blob missing for public sanitization")
            try:
                cat_doc = json.loads(catalog_blob.read_text())
            except (ValueError, OSError) as exc:
                raise WorkflowError(f"Export catalog blob unreadable for public sanitization: {exc}") from exc
            if not isinstance(cat_doc, dict) or "rows" not in cat_doc or not isinstance(cat_doc["rows"], list):
                raise WorkflowError("Export catalog blob invalid schema for public sanitization")
            for r in cat_doc["rows"]:
                if r.get("identity"):
                    catalog_terms.add(r["identity"])
                if r.get("english"):
                    catalog_terms.add(r["english"])
                if r.get("account_name"):
                    catalog_terms.add(r["account_name"])

        from stage4 import sanitize_public_text
        sanitized_explanation = sanitize_public_text(wire.get("explanation", ""), catalog_terms=catalog_terms)
        for f in body.get("findings", []):
            if "summary" in f:
                f["summary"] = sanitize_public_text(f["summary"], catalog_terms=catalog_terms)
            if "detail" in f:
                f["detail"] = sanitize_public_text(f["detail"], catalog_terms=catalog_terms)

        # Scrub runtime artifacts BEFORE computing evidence_paths so the
        # recorded digest matches the retained post-sanitization artifact.
        if view["candidate"].get("kind") == "stage4-proposal":
            _sanitize_stage4_runtime_artifacts(
                destination, job["job_id"], private_root, catalog_terms=catalog_terms
            )
            if stdout.exists() and not stdout.is_symlink():
                _native_events_bytes = stdout.read_bytes()
            else:
                _native_events_bytes = raw.encode("utf-8")
        else:
            _native_events_bytes = raw.encode("utf-8")

        # Captured native event log is a real artifact, not an agent-provided path.
        # Digest uses post-sanitization bytes so the hash matches the retained file.
        body["evidence_paths"] = [
            {
                "artifact_id": job["job_id"] + "-native-events",
                "sha256": bytes_hash(_native_events_bytes),
                "visibility": "public",
            }
        ]
        if verified_private_ref:
            body["evidence_paths"].append(verified_private_ref)

        validate_document("result-envelope", body)
        work = within(self.root, "docs/ai/work-items/" + view["work_item"])
        archive = work / "runs" / job["job_id"] / "results" / (job["job_id"] + ".json")
        write_json(archive, body, immutable=True)
        atomic_write(
            work / "runs" / job["job_id"] / "explanations" / (job["job_id"] + ".md"),
            sanitized_explanation.encode(),
            immutable=True,
        )
        event = dict(job_id=job["job_id"], role=job["role"], result=body)
        if verified_private_ref:
            event["verified_private_artifacts"] = [verified_private_ref]
        if prop_meta:
            from stage4 import derive_stage4_candidate_id
            event["proposal_sha256"] = prop_meta["proposal_sha256"]
            event["export_sha256"] = view["candidate"]["export_sha256"]
            event["candidate_id"] = derive_stage4_candidate_id(
                view["candidate"]["export_sha256"], prop_meta["proposal_sha256"]
            )
        if rev_meta:
            event["review_meta"] = rev_meta
        if bundle_meta:
            event["bundle_sha256"] = bundle_meta["bundle_sha256"]
            event["payload_sha256"] = bundle_meta["payload_sha256"]
            event["bundle_artifacts"] = [
                bundle_meta["bundle_artifact"],
                bundle_meta["payload_artifact"],
            ]
        if body.get("dry_run_evidence_digest"):
            event["dry_run_evidence_digest"] = body["dry_run_evidence_digest"]
        if body["status"] == "COMPLETE":
            if job["role"] == "architect" and body["verdict"] != "BLOCKED":
                if not wire["plan_text"].strip():
                    raise WorkflowError("Architect returned no plan")
                plan = work / "runs" / job["job_id"] / "results" / "plan.md"
                atomic_write(plan, wire["plan_text"].encode(), immutable=True)
                event["new_plan_hash"] = bytes_hash(wire["plan_text"].encode())
                self.store.set_meta("plan_artifact", str(plan.relative_to(self.root)))

                proposal = extract_scope_proposal(wire["plan_text"])
                if view.get("stage") == "plan" and proposal is None:
                    raise WorkflowError("MALFORMED_RESULT: Architect in planning stage must provide ```scope-proposal block")
                if proposal is not None:
                    schema_path = Path(__file__).parent / "schemas/v1/scope-proposal.json"
                    if schema_path.exists():
                        import jsonschema
                        try:
                            schema = json.loads(schema_path.read_text())
                            jsonschema.validate(instance=proposal, schema=schema)
                        except Exception as exc:
                            raise WorkflowError(f"MALFORMED_RESULT: Scope proposal schema validation failed: {exc}")
                    stages = proposal.get("implementation_stages", [])
                    if not stages or len(stages) != len(set(stages)) or any(s not in SUPPORTED_STAGES for s in stages):
                        raise WorkflowError(f"MALFORMED_RESULT: Invalid implementation_stages in scope proposal: {stages}")
                    outbox = work / "outbox"
                    outbox.mkdir(parents=True, exist_ok=True)
                    atomic_write(outbox / "scope-proposal.json", canonical(proposal) + b"\n", immutable=False)
                    event["scope_proposal"] = proposal

            elif job["role"] == "builder" and view["candidate"].get("kind") != "stage4-proposal":
                if not self.launcher:
                    validation = json.loads((destination / "validation.json").read_text())
                    if not validation.get("complete"):
                        raise WorkflowError("Required validation did not complete")
                    event["candidate"] = json.loads(
                        (destination / "tested-candidate/binding.json").read_text()
                    )
                    self._recheck_candidate(event["candidate"])
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
                self._recheck_candidate(view["candidate"])
                if (
                    job["role"] == "verifier"
                    and body["verdict"] == "PASS"
                    and view["candidate"].get("kind") != "stage4-proposal"
                ):
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
        row = self.store.conn.execute(
            "SELECT status FROM workflow_grants WHERE token_id=?", (token["token_id"],)
        ).fetchone()
        if row:
            raise WorkflowError("Token already used or recorded")
        view = self._synchronize_checkpoint()
        if (
            not view["gate"]
            or token["scope"] != view["gate"]["scope"]
            or token["gate_id"] != view["gate"]["gate_id"]
            or token["work_item"] != view["work_item"]
        ):
            raise WorkflowError("Approval does not match pending gate")
        from stage4 import is_hex64
        if token["scope"] == "PLAN":
            if token.get("schema_version") == 1:
                raise WorkflowError("Legacy schema_version 1 PLAN tokens cannot be reused for new approvals")
            if token.get("schema_version") != 2:
                raise WorkflowError("New PLAN approvals must declare schema_version 2 with roles_hash")
            if not token.get("roles_hash"):
                raise WorkflowError("PLAN token must declare roles_hash")
            expected_roles_hash = view.get("roles_hash") or digest(self.config.get("roles", {}))
            required = dict(
                plan_revision_hash=view["plan_revision_hash"],
                scope_hash=view["scope_hash"],
                roles_hash=expected_roles_hash,
                repository_id=str(self.root),
                branch=self.config["branch"],
            )
            if (
                any(token.get(k) != value for k, value in required.items())
                or view["stage"] not in token["stages"]
            ):
                raise WorkflowError("PLAN binding mismatch")
        elif token["scope"] == "COMMIT":
            self._recheck_candidate(view["candidate"])
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
        elif token["scope"] == "DRY_RUN":
            self._recheck_candidate(view["candidate"])
            if token.get("operation") != "set_account_name_ar":
                raise WorkflowError("DRY_RUN operation must be set_account_name_ar")
            for hkey in ("export_sha256", "proposal_sha256", "bundle_sha256", "payload_sha256", "erp_descriptor_hash"):
                if not token.get(hkey) or not is_hex64(token[hkey]):
                    raise WorkflowError(f"DRY_RUN {hkey} must be 64-character lowercase hex")

            # Unconditional check: active hashes must exist in state and match token
            exp_export = view["candidate"].get("export_sha256")
            if not exp_export or not is_hex64(exp_export):
                raise WorkflowError("DRY_RUN requires active export_sha256 in candidate")
            if token["export_sha256"] != exp_export:
                raise WorkflowError("DRY_RUN export_sha256 mismatch")

            exp_prop = view["candidate"].get("proposal_sha256") or view["candidate"].get("candidate_id")
            if not exp_prop or not is_hex64(exp_prop):
                raise WorkflowError("DRY_RUN requires active proposal_sha256 in candidate")
            token_prop = token.get("proposal_sha256") or token.get("candidate_id")
            if token_prop != exp_prop:
                raise WorkflowError("DRY_RUN proposal_sha256 mismatch")

            exp_bundle = view.get("bundle_sha256") or view["candidate"].get("bundle_sha256")
            if not exp_bundle or not is_hex64(exp_bundle):
                raise WorkflowError("DRY_RUN requires active bundle_sha256 in state")
            if token["bundle_sha256"] != exp_bundle:
                raise WorkflowError("DRY_RUN bundle_sha256 mismatch")

            exp_payload = view.get("payload_sha256") or view["candidate"].get("payload_sha256")
            if not exp_payload or not is_hex64(exp_payload):
                raise WorkflowError("DRY_RUN requires active payload_sha256 in state")
            if token["payload_sha256"] != exp_payload:
                raise WorkflowError("DRY_RUN payload_sha256 mismatch")

            exp_desc = self.config.get("erp_descriptor_hash") or view.get("erp_descriptor_hash")
            if not exp_desc or not is_hex64(exp_desc):
                raise WorkflowError("DRY_RUN requires active erp_descriptor_hash in config")
            if token["erp_descriptor_hash"] != exp_desc:
                raise WorkflowError("DRY_RUN erp_descriptor_hash mismatch")

        elif token["scope"] == "IMPORT":
            self._recheck_candidate(view["candidate"])
            if token.get("operation") != "set_account_name_ar":
                raise WorkflowError("IMPORT operation must be set_account_name_ar")
            for hkey in ("export_sha256", "proposal_sha256", "bundle_sha256", "payload_sha256", "erp_descriptor_hash"):
                if not token.get(hkey) or not is_hex64(token[hkey]):
                    raise WorkflowError(f"IMPORT {hkey} must be 64-character lowercase hex")
            if not token.get("dry_run_evidence_digest") or not is_hex64(token["dry_run_evidence_digest"]):
                raise WorkflowError("IMPORT dry_run_evidence_digest must be 64-character lowercase hex")

            exp_export = view["candidate"].get("export_sha256")
            if not exp_export or not is_hex64(exp_export):
                raise WorkflowError("IMPORT requires active export_sha256 in candidate")
            if token["export_sha256"] != exp_export:
                raise WorkflowError("IMPORT export_sha256 mismatch")

            exp_prop = view["candidate"].get("proposal_sha256") or view["candidate"].get("candidate_id")
            if not exp_prop or not is_hex64(exp_prop):
                raise WorkflowError("IMPORT requires active proposal_sha256 in candidate")
            token_prop = token.get("proposal_sha256") or token.get("candidate_id")
            if token_prop != exp_prop:
                raise WorkflowError("IMPORT proposal_sha256 mismatch")

            exp_bundle = view.get("bundle_sha256") or view["candidate"].get("bundle_sha256")
            if not exp_bundle or not is_hex64(exp_bundle):
                raise WorkflowError("IMPORT requires active bundle_sha256 in state")
            if token["bundle_sha256"] != exp_bundle:
                raise WorkflowError("IMPORT bundle_sha256 mismatch")

            exp_payload = view.get("payload_sha256") or view["candidate"].get("payload_sha256")
            if not exp_payload or not is_hex64(exp_payload):
                raise WorkflowError("IMPORT requires active payload_sha256 in state")
            if token["payload_sha256"] != exp_payload:
                raise WorkflowError("IMPORT payload_sha256 mismatch")

            exp_desc = self.config.get("erp_descriptor_hash") or view.get("erp_descriptor_hash")
            if not exp_desc or not is_hex64(exp_desc):
                raise WorkflowError("IMPORT requires active erp_descriptor_hash in config")
            if token["erp_descriptor_hash"] != exp_desc:
                raise WorkflowError("IMPORT erp_descriptor_hash mismatch")

            exp_dry = view.get("dry_run_evidence_digest")
            if not exp_dry or not is_hex64(exp_dry):
                raise WorkflowError("IMPORT requires recorded active dry_run_evidence_digest in state")
            if token["dry_run_evidence_digest"] != exp_dry:
                raise WorkflowError("IMPORT dry_run_evidence_digest mismatch against recorded evidence")
        else:
            raise WorkflowError("Unknown or unsupported approval scope")
        self.store.grant(token)
        self.store.event("grant-" + token["token_id"], "grant", token)
        if token["scope"] in ("COMMIT", "DRY_RUN", "IMPORT"):
            with self.store.conn:
                self.store.conn.execute(
                    "UPDATE workflow_grants SET status='RESERVED' WHERE token_id=?", (token["token_id"],)
                )
            write_json(self.runtime / "operations" / token["job_id"] / "intent.json", token, immutable=True)
        return self.run()

    def grant_and_synchronize(self, token: dict) -> dict:
        """Approval-only operation.
        
        Validates token against schema and pending gate, records grant row and event,
        and synchronizes LangGraph checkpoint WITHOUT calling run() or dispatching jobs.
        """
        if self.store.meta("recovery_required", False):
            raise WorkflowError("Recovery review required before approval creation")
        validate_document("approval-token", token)
        if token["status"] != "ISSUED":
            raise WorkflowError("Only a newly issued owner token can enter approval")
        row = self.store.conn.execute(
            "SELECT status FROM workflow_grants WHERE token_id=?", (token["token_id"],)
        ).fetchone()
        if row:
            raise WorkflowError("Token already used or recorded")
        view = self._synchronize_checkpoint()
        if (
            not view["gate"]
            or token["scope"] != view["gate"]["scope"]
            or token["gate_id"] != view["gate"]["gate_id"]
            or token["work_item"] != view["work_item"]
        ):
            raise WorkflowError("Approval does not match pending gate")
        if token["scope"] == "PLAN":
            if token.get("schema_version") == 1:
                raise WorkflowError("Legacy schema_version 1 PLAN tokens cannot be reused for new approvals")
            if token.get("schema_version") != 2:
                raise WorkflowError("New PLAN approvals must declare schema_version 2 with roles_hash")
            if not token.get("roles_hash"):
                raise WorkflowError("PLAN token must declare roles_hash")
            expected_roles_hash = view.get("roles_hash") or digest(self.config.get("roles", {}))
            required = dict(
                plan_revision_hash=view["plan_revision_hash"],
                scope_hash=view["scope_hash"],
                roles_hash=expected_roles_hash,
                repository_id=str(self.root),
                branch=self.config["branch"],
            )
            if (
                any(token.get(k) != value for k, value in required.items())
                or view["stage"] not in token["stages"]
            ):
                raise WorkflowError("PLAN binding mismatch")
        else:
            raise WorkflowError(f"Unsupported approval scope for grant_and_synchronize: {token['scope']}")

        self.store.grant(token)
        self.store.event("grant-" + token["token_id"], "grant", token)
        # Synchronize checkpoint without calling self.run()
        return self._synchronize_checkpoint()

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

    def _has_grant_events_for_current_stage(self):
        view = self.view()
        current_stage = view.get("stage")
        for event in self.store.events():
            if event["kind"] == "grant":
                payload = event["payload"]
                if payload.get("scope") == "PLAN":
                    token_stages = payload.get("stages", [])
                    gate_id_val = payload.get("gate_id", "")
                    if current_stage in token_stages or current_stage in gate_id_val:
                        return True
        return False

    def _load_scope_proposal(self):
        work_item = self.config.get("work_item")
        if not work_item:
            raise CoreValidationError("No work_item configured")
        proposal_file = self.root / f"docs/ai/work-items/{work_item}/outbox/scope-proposal.json"
        if not proposal_file.exists():
            raise CoreValidationError(f"Scope proposal file missing: {proposal_file}")
        try:
            return json.loads(proposal_file.read_text())
        except (ValueError, OSError) as e:
            raise CoreValidationError(f"Failed to read scope proposal: {e}")

    def adopt_scope(
        self,
        scope: dict,
        implementation_stages: list[str],
        action_id: str,
        request_hash: str,
    ):
        view = self.view()

        if not view.get("gate") or view["gate"].get("scope") != "PLAN":
            raise PreconditionError("adopt_scope requires a PLAN gate")
        if view.get("plan_granted"):
            raise PreconditionError("adopt_scope requires plan_granted == false")
        if view.get("active_jobs"):
            raise PreconditionError("adopt_scope requires active_jobs == []")
        if view.get("stage") != "plan":
            raise PreconditionError(
                f"adopt_scope only valid from the planning stage; current stage is {view.get('stage')!r}"
            )
        if self._has_grant_events_for_current_stage():
            raise PreconditionError(
                "adopt_scope prohibited after a PLAN grant for this stage"
            )

        if not implementation_stages:
            raise CoreValidationError("implementation_stages must not be empty")
        if len(implementation_stages) != len(set(implementation_stages)):
            raise CoreValidationError(
                f"implementation_stages contains duplicates: {implementation_stages}"
            )
        for stage in implementation_stages:
            if stage not in SUPPORTED_STAGES:
                raise CoreValidationError(f"unsupported stage: {stage!r}")
            if stage in self.config.get("stages", []):
                raise CoreValidationError(
                    f"stage {stage!r} already present; repeated adoption not allowed"
                )

        proposal = self._load_scope_proposal()
        if proposal.get("scope") != scope:
            raise CoreValidationError("scope does not match persisted scope-proposal.json")
        if proposal.get("implementation_stages") != implementation_stages:
            raise CoreValidationError(
                "implementation_stages do not match persisted scope-proposal.json"
            )

        new_scope_hash = compute_scope_hash(scope)
        new_config = deepcopy(self.config)
        new_config["scope"] = scope
        new_config["scope_hash"] = new_scope_hash
        new_config["stages"] = [*self.config.get("stages", []), *implementation_stages]

        candidate_meta = freeze(
            self.root,
            self.config["base_commit"],
            self.config["branch"],
            scope["allowed_paths"],
            self.runtime / "scope-adopted-candidate" / uuid.uuid4().hex,
            new_config.get("generated", []),
        )
        new_config["candidate"] = candidate_meta

        event_id, seq = self.store.adopt_scope_atomic(
            new_config=new_config,
            action_id=action_id,
            scope_hash=new_scope_hash,
            implementation_stages=implementation_stages,
            candidate_meta=candidate_meta,
            request_hash=request_hash,
        )

        self.config = self.store.meta("config")
        self._synchronize_checkpoint()
        return self.view()

    def recover_adopt_scope(self, stored_request_hash: str, submitted_request_hash: str):
        if not stored_request_hash:
            raise RecoveryError("scope_adopted event missing request_hash")
        if stored_request_hash != submitted_request_hash:
            raise DuplicateKeyConflict(
                "action_id reused with different request contents"
            )
        self.config = self.store.meta("config")
        self._synchronize_checkpoint()
        return self.view()

    def reconfigure_role(
        self,
        role,
        tool,
        model,
        effort=None,
        reason="Owner role reconfiguration",
        *,
        action_id=None,
        request_hash=None,
    ):
        view = self.view()
        if view["status"] != "PAUSED" or view.get("active_jobs"):
            raise WorkflowError("Role reconfiguration requires a paused workflow with all active jobs reconciled")

        known_roles = {"architect", "builder", "reviewer", "verifier", "proposer", "ai-a1", "ai-a2", "ai-a3"}
        if role not in known_roles:
            raise WorkflowError(f"Unknown role: {role}")

        if tool not in ("codex", "opencode"):
            raise WorkflowError(f"Unsupported tool: {tool}")

        if tool == "codex":
            binary = "/opt/codex-desktop/resources/codex"
            expected_ver = "0.153.0-alpha.5"
            valid_efforts = ("high", "medium", "low", None)
            if effort not in valid_efforts:
                raise WorkflowError(f"Invalid effort for codex: {effort}")
            if not model or not model.strip():
                raise WorkflowError("Model name cannot be empty")
        elif tool == "opencode":
            binary = "/usr/bin/opencode-cli"
            expected_ver = "1.14.33"
            effort = None
            if not model or not model.strip() or "/" not in model:
                raise WorkflowError("OpenCode model must follow '<provider>/<model>' format")

        binary_path = Path(binary)
        if not binary_path.exists() or not os.access(binary_path, os.X_OK):
            raise WorkflowError(f"Tool binary not found or not executable: {binary}")

        try:
            r = subprocess.run([str(binary_path), "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode != 0:
                raise WorkflowError(f"Failed to execute {binary} --version")
            binary_ver_output = r.stdout.strip()
            if expected_ver not in binary_ver_output:
                raise WorkflowError(f"Binary version mismatch: expected '{expected_ver}' in '{binary_ver_output}'")
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise WorkflowError(f"Error inspecting binary {binary}: {exc}")

        binary_sha = bytes_hash(binary_path.read_bytes())

        role_name = role if role in ("architect", "reviewer", "builder", "verifier") else "ai-reviewer"
        role_file = within(self.root, f"docs/ai/roles/{role_name}.md")
        if not role_file.exists():
            raise WorkflowError(f"Role prompt file missing: {role_file}")
        prompt_sha = bytes_hash(role_file.read_bytes())

        pin = {
            "tool": tool,
            "binary": str(binary_path),
            "model": model.strip(),
            "version": expected_ver,
            "effort": effort,
            "binary_sha256": binary_sha,
            "prompt_sha256": prompt_sha,
        }

        config = deepcopy(self.config)
        if "orchestrator/roles.json" not in config.get("generated", []):
            config.setdefault("generated", []).append("orchestrator/roles.json")
        old_pin = config.get("roles", {}).get(role)
        config.setdefault("roles", {})[role] = pin

        roles_hash = digest(config["roles"])
        config["roles_hash"] = roles_hash

        plan_revoked = bool(view.get("plan_granted") or config.get("plan_granted"))
        config["plan_granted"] = False
        new_gate = {"scope": "PLAN", "gate_id": "plan-" + uuid.uuid4().hex[:24]}
        config["gate"] = new_gate

        event_id = f"role-reconfigure-{uuid.uuid4().hex[:16]}"
        payload = {
            "role": role,
            "old_pin": old_pin,
            "new_pin": pin,
            "reason": reason,
            "roles_hash": roles_hash,
            "plan_grant_revoked": plan_revoked,
            "new_gate": new_gate,
        }
        if action_id is not None:
            payload["action_id"] = action_id
        if request_hash is not None:
            payload["request_hash"] = request_hash
        self.store.reconfigure(config, event_id, "role_reconfigured", payload, invalidate_grants=True)

        self.config = config
        self.sync_roles_mirror()
        return self.run()

    def role_catalog(self):
        tools = {}
        for tool_name, bin_path, exp_ver in (
            ("codex", "/opt/codex-desktop/resources/codex", "0.153.0-alpha.5"),
            ("opencode", "/usr/bin/opencode-cli", "1.14.33"),
        ):
            p = Path(bin_path)
            exists = p.exists() and os.access(p, os.X_OK)
            sha = bytes_hash(p.read_bytes()) if exists else None
            ver = None
            if exists:
                try:
                    r = subprocess.run([str(p), "--version"], capture_output=True, text=True, timeout=5)
                    ver = r.stdout.strip() if r.returncode == 0 else None
                except (OSError, subprocess.TimeoutExpired):
                    ver = None
            tools[tool_name] = {
                "binary": str(p),
                "exists": exists,
                "expected_version": exp_ver,
                "detected_version": ver,
                "binary_sha256": sha,
            }

        prompts = {}
        roles_dir = within(self.root, "docs/ai/roles")
        for r_file in sorted(roles_dir.glob("*.md")):
            prompts[r_file.stem] = {
                "path": str(r_file.relative_to(self.root)),
                "prompt_sha256": bytes_hash(r_file.read_bytes()),
            }

        current_roles = (
            self.config.get("roles", {})
            if self.config
            else json.loads((self.root / "orchestrator/roles.json").read_text())
        )
        return {
            "ok": True,
            "tools": tools,
            "prompts": prompts,
            "current_roles": current_roles,
        }

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
        self.sync_roles_mirror()
        self._export_view(self.view())

    def _export_view(self, v):
        work = within(self.root, "docs/ai/work-items/" + v["work_item"])
        latest_event = self.store.conn.execute(
            "SELECT created_utc FROM workflow_events WHERE seq <= ? ORDER BY seq DESC LIMIT 1",
            (v["cursor"],),
        ).fetchone()
        exported_utc = (
            latest_event["created_utc"]
            if latest_event
            else self.config.get("initialized_utc", v.get("initialized_utc", "2026-09-12T12:00:00Z"))
        )
        document = dict(
            schema_version=1,
            authority="sqlite-checkpoint-export-only",
            work_item=v["work_item"],
            stage=v["stage"],
            status=v["status"],
            revision=v["revision"],
            plan_revision_hash=v["plan_revision_hash"],
            roles_hash=v.get("roles_hash") or digest(self.config.get("roles", {})),
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
            exported_utc=exported_utc,
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
