"""C02: test-only request -> actual Engine.initialize; no live creation adapter.

The fixture owns a pre-existing disposable Git repository and synthetic policy.
No request can select a path, scope, role, command, branch or native provider.
"""

import hashlib
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest
from candidates import git
from core import WorkflowError, bytes_hash, execution_lock
from engine import Engine
from engineering_control_contracts.contract import VERSION
from engineering_control_contracts.offline import Denied, TestIssuer, digest, validate
from store import Store


class CreationFixture:
    """Disposable proof harness only; not a second production workflow engine.

    Journals model recovery intent/receipts, not a production transaction protocol.
    Unknown partial initialization blocks. Completed checkpoint reconciliation is
    explicit and only rewrites derived exports after source/config revalidation.
    """

    def __init__(self, temporary_root, config, issuer):
        self.temporary_root = Path(temporary_root).resolve()
        self.config = deepcopy(config)
        self.root = Path(config["root"]).resolve()
        assert self.root.is_relative_to(self.temporary_root) and self.root != self.temporary_root
        assert (self.root / ".git").is_dir()  # Never a linked owner worktree.
        assert git(self.root, "config", "--local", "--get", "core.hooksPath").strip() == b"/dev/null"
        assert all(pin["tool"] == "synthetic" for pin in config["roles"].values())
        self.issuer = issuer
        self.journal = self.temporary_root / "creation-intent.json"
        self.lock = self.temporary_root / "creation.lock"
        self.launcher = Mock(side_effect=AssertionError("Creation dispatched a worker"))
        self.fail_after = None

    def save(self, record):
        temporary = self.journal.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, sort_keys=True))
        temporary.replace(self.journal)

    def authorize(self, principal, body, key):
        if not self.issuer.trusts(principal):
            raise Denied("unauthenticated")
        if (
            principal.actor != "human"
            or "create" not in principal.capabilities
            or principal.project != "project-1"
            or principal.work_item != self.config["work_item"]
        ):
            raise Denied("forbidden")
        validate("Create", body)
        # Reuse the same scalar ID contract for the real header boundary.
        from engineering_control_contracts.contract import ID
        from jsonschema import Draft202012Validator

        if not Draft202012Validator(ID).is_valid(key):
            raise Denied("invalid_request")
        if body["project_id"] != "project-1" or body["base_id"] != "base-1":
            raise Denied("not_found")

    def expected(self, body):
        config = deepcopy(self.config)
        # This is an unapproved request, not an owner PLAN grant. DRAFT still needs
        # architect/reviewer execution and the later plan gate.
        text = "# Synthetic request\n\n" + body["title"] + "\n\n" + body["brief"] + "\n"
        config["plan_path"] = "request.md"
        config["plan_revision_hash"] = hashlib.sha256(text.encode()).hexdigest()
        config["scope"]["allowed_paths"] = [*config["scope"]["allowed_paths"], "request.md"]
        return config, text

    def bound_record(self, principal, body, key):
        return dict(
            subject=principal.subject,
            project="project-1",
            work_item=self.config["work_item"],
            operation="create_work_item",
            policy_hash=digest(self.config),
            key=key,
            body_hash=digest(body),
        )

    def finish(self, engine, record, expected):
        # SQLite/checkpoint is authoritative. Exported STATE.json cannot prove init.
        if not engine.config or any(engine.config.get(k) != v for k, v in expected.items()):
            raise Denied("uncertain_outcome", "Partial or mismatched initialization requires review")
        view = engine.view()
        if (
            view["work_item"] != expected["work_item"]
            or view["status"] != "DRAFT"
            or view["active_jobs"]
            or view["plan_granted"]
            or view["candidate"] != engine.config["candidate"]
            or view["plan_revision_hash"] != expected["plan_revision_hash"]
            or view["scope_hash"] != digest(expected["scope"])
            or view["roles_hash"] != digest(expected["roles"])
            or view["next_roles"] != ["architect"]
        ):
            raise Denied("uncertain_outcome")
        for table in ("workflow_jobs", "workflow_grants", "workflow_events"):
            if engine.store.conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]:
                raise Denied("uncertain_outcome")
        engine._recheck_candidate(view["candidate"])
        engine.export()  # Explicit reconciliation of derived exports only.
        record["receipt"] = dict(
            schema_version=VERSION,
            operation_id="creation-1",
            receipt_id="creation-receipt-1",
            resource_id=expected["work_item"],
            revision=view["revision"],
            effect="initialization_only",
            effect_state="completed",
            runtime="native",
            job_ids=[],
            execution_complete=False,
        )
        validate("Receipt", record["receipt"])
        record["binding"] = dict(
            candidate_id=view["candidate"]["candidate_id"],
            manifest_sha256=view["candidate"]["manifest_hash"],
            base_commit=expected["base_commit"],
            plan_sha256=expected["plan_revision_hash"],
            scope_sha256=engine.config["scope_hash"],
            roles_sha256=engine.config["roles_hash"],
        )
        record["state"] = "completed"
        self.save(record)
        return deepcopy(record["receipt"])

    def request(self, principal, body, key="creation-key", reconcile=False):
        self.authorize(principal, body, key)
        with execution_lock(self.lock):
            binding = self.bound_record(principal, body, key)
            expected, text = self.expected(body)
            if self.journal.exists():
                record = json.loads(self.journal.read_text())
                if record["request"] != binding:
                    raise Denied("conflict")
                if record["state"] == "completed":
                    return deepcopy(record["receipt"])  # matching replay before stale
                if not reconcile:
                    raise Denied("uncertain_outcome", "Explicit fixture reconciliation required")
                # Never retry initialize after an uncertain outcome, including when
                # there is no config yet. Constructor writes are classified in docs.
                if not (self.root / "orchestrator/var/checkpoints.db").is_file():
                    raise Denied("uncertain_outcome", "No checkpoint; do not retry initialization")
                engine = Engine(self.root, launcher=self.launcher)
                try:
                    return self.finish(engine, record, expected)
                except WorkflowError as exc:
                    raise Denied("uncertain_outcome", "Initialization/source drift requires review") from exc
                finally:
                    engine.close()
            if reconcile:
                raise Denied("conflict")
            if body["expected_revision"] != 0:
                raise Denied("conflict")
            if (self.root / "orchestrator/var").exists() or (self.root / "request.md").exists():
                raise Denied("conflict", "Target must be fresh; never adopt existing workflow")
            if git(self.root, "rev-parse", "HEAD").decode().strip() != expected["base_commit"]:
                raise Denied("conflict")
            if git(self.root, "branch", "--show-current").decode().strip() != expected["branch"]:
                raise Denied("conflict")
            if git(self.root, "status", "--porcelain"):
                raise Denied("conflict", "Fixture target is dirty")
            record = dict(request=binding, state="intent")
            self.save(record)  # intent precedes request text, constructor and init
            if self.fail_after == "intent":
                raise RuntimeError("Synthetic crash after intent")
            (self.root / "request.md").write_text(text)
            engine = Engine(self.root, launcher=self.launcher)
            try:
                if self.fail_after == "constructor":
                    raise RuntimeError("Synthetic crash after constructor")
                engine.initialize(expected)
                if self.fail_after == "initialize":
                    raise RuntimeError("Synthetic lost initialization response")
                return self.finish(engine, record, expected)
            finally:
                engine.close()


@pytest.fixture
def creation(configured, tmp_path, monkeypatch):
    root, config = configured
    git(root, "config", "--local", "core.hooksPath", "/dev/null")
    issuer = TestIssuer()
    principal = issuer.issue(capabilities=("create",), work_item=config["work_item"])
    fixture = CreationFixture(tmp_path, config, issuer)
    probes = {}
    # Patch before Engine graph construction so bound graph nodes are probes too.
    for owner, names in (
        (Engine, ("run", "_drive", "_prepare", "_dispatch", "_collect", "approve", "grant_and_synchronize")),
        (Store, ("create_job", "grant", "event")),
    ):
        for name in names:
            probe = Mock(side_effect=AssertionError("No-dispatch boundary: " + name))
            monkeypatch.setattr(owner, name, probe)
            probes[name] = probe
    worker_probe = Mock(side_effect=AssertionError("Worker entry reached"))
    monkeypatch.setattr("worker.run", worker_probe)
    probes["worker.run"] = worker_probe
    original_initialize = Engine.initialize
    fixture.initializations = []

    def initialize_once(engine, selected):
        fixture.initializations.append(deepcopy(selected))
        return original_initialize(engine, selected)

    monkeypatch.setattr(Engine, "initialize", initialize_once)
    original_popen = subprocess.Popen
    fixture.commands = []

    def git_only_popen(argv, *args, **kwargs):
        # Git candidate capture is expected I/O, but no worker/native process or
        # commit/worktree creation may hide behind the initialization call.
        assert argv[0] == "git", "Non-Git subprocess during initialization"
        assert not {"commit", "push", "checkout", "switch"}.intersection(argv)
        assert "worktree" not in argv or "list" in argv
        fixture.commands.append(list(argv))
        return original_popen(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", git_only_popen)
    yield fixture, principal, probes
    fixture.launcher.assert_not_called()
    for probe in probes.values():
        probe.assert_not_called()


def request_body(**updates):
    return dict(
        expected_revision=0,
        project_id="project-1",
        base_id="base-1",
        title="Bounded synthetic task",
        brief="Describe a synthetic change to old; no execution authorized.",
        **updates,
    )


def inventory(root):
    return {str(p.relative_to(root)): bytes_hash(p.read_bytes()) for p in root.rglob("*") if p.is_file()}


def test_c02_request_maps_to_real_initialize_without_dispatch(creation):
    fixture, principal, _probes = creation
    before = inventory(fixture.root)
    head = git(fixture.root, "rev-parse", "HEAD")
    index = (fixture.root / ".git/index").read_bytes()
    worktrees = git(fixture.root, "worktree", "list", "--porcelain")
    receipt = fixture.request(principal, request_body())
    assert len(fixture.initializations) == 1
    assert receipt["effect"] == "initialization_only" and receipt["job_ids"] == []
    assert receipt["execution_complete"] is False
    after = inventory(fixture.root)
    # Existing files, HEAD, refs and real index remain byte-identical. Git freeze
    # may add objects through its isolated index; this is NOT zero Git I/O.
    assert all(after[path] == sha for path, sha in before.items())
    added = set(after) - set(before)
    allowed = ("orchestrator/var/", ".git/objects/", "docs/ai/work-items/test-work/")
    assert all(p == "request.md" or p == "orchestrator/roles.json" or p.startswith(allowed) for p in added)
    assert (fixture.root / "orchestrator/var/checkpoints.db").exists()
    assert "request.md" in {
        e["path"]
        for e in json.loads((fixture.root / "orchestrator/var/initial-candidate/binding.json").read_text())[
            "manifest"
        ]["entries"]
    }
    assert git(fixture.root, "rev-parse", "HEAD") == head
    assert (fixture.root / ".git/index").read_bytes() == index
    assert git(fixture.root, "worktree", "list", "--porcelain") == worktrees
    assert git(fixture.root, "config", "--local", "--get", "core.hooksPath").strip() == b"/dev/null"
    record = json.loads(fixture.journal.read_text())
    assert record["binding"]["plan_sha256"] == bytes_hash((fixture.root / "request.md").read_bytes())


def test_c02_replay_conflict_and_no_initialization_retry(creation, monkeypatch):
    fixture, principal, _probes = creation
    body = request_body()
    receipt = fixture.request(principal, body)
    snapshot = inventory(fixture.root)
    initialize = Mock(side_effect=AssertionError("Replay initialized again"))
    monkeypatch.setattr(Engine, "initialize", initialize)
    restarted = CreationFixture(fixture.temporary_root, fixture.config, fixture.issuer)
    assert restarted.request(principal, body) == receipt
    assert inventory(fixture.root) == snapshot
    for altered, key in (
        ({**body, "brief": "different"}, "creation-key"),
        (body, "fresh-key"),
        ({**body, "expected_revision": 1}, "creation-key"),
    ):
        with pytest.raises(Denied, match="conflict"):
            restarted.request(principal, altered, key)
    initialize.assert_not_called()


@pytest.mark.parametrize("phase", ["intent", "constructor", "initialize"])
def test_c02_lost_response_requires_explicit_reconciliation(creation, phase, monkeypatch):
    fixture, principal, _probes = creation
    fixture.fail_after = phase
    with pytest.raises(RuntimeError, match="Synthetic"):
        fixture.request(principal, request_body())
    restarted = CreationFixture(fixture.temporary_root, fixture.config, fixture.issuer)
    with pytest.raises(Denied, match="uncertain_outcome"):
        restarted.request(principal, request_body())
    initialize = Mock(side_effect=AssertionError("Uncertain initialization retried"))
    monkeypatch.setattr(Engine, "initialize", initialize)
    if phase == "initialize":
        receipt = restarted.request(principal, request_body(), reconcile=True)
        assert len(fixture.initializations) == 1
        assert receipt["effect"] == "initialization_only"
    else:
        with pytest.raises(Denied, match="uncertain_outcome"):
            restarted.request(principal, request_body(), reconcile=True)
        assert json.loads(fixture.journal.read_text())["state"] == "intent"
    initialize.assert_not_called()


@pytest.mark.parametrize("damage", ["source", "config", "checkpoint", "checkpoint_binding"])
def test_c02_reconciliation_rejects_drift_or_partial_checkpoint(creation, damage):
    fixture, principal, _probes = creation
    fixture.fail_after = "initialize"
    with pytest.raises(RuntimeError):
        fixture.request(principal, request_body())
    if damage == "source":
        (fixture.root / "request.md").write_text("changed after initialization")
    elif damage == "checkpoint_binding":
        engine = Engine(fixture.root, launcher=fixture.launcher)
        try:
            view = engine.view()
            view["scope_hash"] = "f" * 64
            engine.graph.update_state(engine.graph_config, {"view": view}, as_node="collect")
        finally:
            engine.close()
    else:
        # Synthetic SQLite only, never a live controller database.
        import sqlite3

        with sqlite3.connect(fixture.root / "orchestrator/var/checkpoints.db") as conn:
            if damage == "config":
                config = json.loads(
                    conn.execute("SELECT value FROM workflow_meta WHERE key='config'").fetchone()[0]
                )
                config["scope"]["allowed_paths"].append("outside-scope")
                conn.execute("UPDATE workflow_meta SET value=? WHERE key='config'", (json.dumps(config),))
            else:
                conn.execute("DELETE FROM checkpoints")
    with pytest.raises((Denied, WorkflowError)):
        fixture.request(principal, request_body(), reconcile=True)
    assert json.loads(fixture.journal.read_text())["state"] == "intent"


@pytest.mark.parametrize("damage", ["actor", "project", "base", "field", "oversize", "revision", "dirty"])
def test_c02_unauthorized_or_unbounded_request_has_no_writes(creation, damage):
    fixture, principal, _probes = creation
    body = request_body()
    if damage == "actor":
        principal = fixture.issuer.issue(
            actor="agent", capabilities=("create",), work_item=fixture.config["work_item"]
        )
    elif damage in ("project", "base"):
        body[damage + "_id"] = "unknown"
    elif damage == "field":
        body["root"] = "/caller-selected/path"
    elif damage == "oversize":
        body["brief"] = "x" * 2049
    elif damage == "revision":
        body["expected_revision"] = 1
    elif damage == "dirty":
        (fixture.root / "old").write_text("unexpected work")
    before = inventory(fixture.root)
    with pytest.raises(Denied):
        fixture.request(principal, body)
    assert inventory(fixture.root) == before and not fixture.journal.exists()


def test_c02_replay_revalidates_principal_and_frozen_server_policy(creation):
    fixture, principal, _probes = creation
    fixture.request(principal, request_body())
    changed_policy = deepcopy(fixture.config)
    changed_policy["scope"]["allowed_paths"].append("unexpected-policy-change")
    restarted = CreationFixture(fixture.temporary_root, changed_policy, fixture.issuer)
    with pytest.raises(Denied, match="conflict"):
        restarted.request(principal, request_body())
    fixture.issuer.issued.clear()
    with pytest.raises(Denied, match="unauthenticated"):
        fixture.request(principal, request_body())
    assert len(fixture.initializations) == 1


def test_c02_valid_maximum_request_is_bound_to_candidate(creation):
    fixture, principal, _probes = creation
    body = request_body()
    body.update(title="t" * 2048, brief="b" * 2048)
    fixture.request(principal, body)
    assert "t" * 2048 in (fixture.root / "request.md").read_text()
    assert len(fixture.initializations) == 1
