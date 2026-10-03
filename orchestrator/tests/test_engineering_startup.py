"""Actual isolated startup commands with synthetic agents, never provider acceptance."""

import json
import runpy
import shutil
import sys
import time
from pathlib import Path

import engineering_startup as startup
import pytest
from candidates import freeze, git
from core import WorkflowError, bytes_hash
from engine import Engine
from test_engine import Stub, plan_token


@pytest.fixture
def engineering(configured):
    root, config = configured
    for name in startup.CONTEXT_PATHS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic engineering context: " + name)
    for name in startup.CHECKERS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("print('fixture check passed')\n")
    git(root, "add", ".")
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-m", "startup fixture")
    config["base_commit"] = git(root, "rev-parse", "HEAD").decode().strip()
    return root, config


def test_new_task_requires_guide_and_cannot_disable_policy(engineering):
    root, config = engineering
    (root / startup.CONTEXT_PATHS[2]).unlink()
    e = Engine(root, launcher=Stub())
    with pytest.raises(WorkflowError, match="Required engineering context missing"):
        e.initialize(config)
    config["engineering_startup_policy"] = False
    with pytest.raises(WorkflowError, match="Unsupported engineering_startup_policy"):
        e.initialize(config)
    assert e.store.meta("config") is None
    e.close()


def test_success_all_roles_receive_bound_context_and_owner_grant_still_required(engineering):
    root, config = engineering
    stub = Stub()
    e = Engine(root, launcher=stub)
    e.initialize(config)
    assert e.config["engineering_startup_policy"] == startup.POLICY
    assert e.run()["gate"]["scope"] == "PLAN"
    assert len(stub.starts) == 2
    assert e.run()["gate"]["scope"] == "PLAN"
    assert len(stub.starts) == 2
    assert e.approve(plan_token(e))["gate"]["scope"] == "COMMIT"
    assert len(stub.starts) == 4
    for job_id in stub.starts:
        spec = e.store.job(job_id)["spec"]
        assert set(startup.CONTEXT_PATHS) <= {r["source_relative_path"] for r in spec["read_artifact_refs"]}
        report = json.loads(Path(spec["engineering_startup"]["path"]).read_text())
        assert report["passed"]
        assert report["candidate_id"] == spec["envelope"]["candidate_id"]
        assert report["baseline"]["head"] == config["base_commit"]
        assert [r["argv"][1] for r in report["commands"]] == list(startup.CHECKERS)
        assert "Files Read" in spec["prompt"]
    e.close()


@pytest.mark.parametrize(
    "script",
    [
        "raise SystemExit(7)\n",
        "from pathlib import Path; Path('old').write_text('forbidden')\n",
        "from pathlib import Path; Path('orchestrator/var/checkpoints.db').write_text('forbidden')\n",
        "from pathlib import Path; Path('.git/config').write_text('forbidden')\n",
    ],
)
def test_failed_or_mutating_check_creates_failed_evidence_and_launches_nothing(engineering, script):
    root, config = engineering
    (root / startup.CHECKERS[0]).write_text(script)
    git(root, "add", ".")
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-m", "negative check fixture")
    config["base_commit"] = git(root, "rev-parse", "HEAD").decode().strip()
    stub = Stub()
    e = Engine(root, launcher=stub)
    e.initialize(config)
    with pytest.raises(WorkflowError, match="Engineering startup check failed"):
        e.run()
    assert not stub.starts
    reports = list((e.runtime / "startup").glob("*.json"))
    assert reports and not json.loads(reports[0].read_text())["passed"]
    for command in json.loads(reports[0].read_text())["commands"]:
        for stream in ("stdout", "stderr"):
            log = Path(command[stream + "_log"])
            assert log.stat().st_mode & 0o777 == 0o600
            assert bytes_hash(log.read_bytes()) == command[stream + "_sha256"]
    assert (root / "old").read_text() == "old"
    assert e.store.meta("config") is not None
    e.close()


def test_context_change_before_dispatch_fails_closed(engineering):
    root, config = engineering
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    e.initialize(config)
    state = e._prepare({"view": e.view()})
    (root / "AGENTS.md").write_text("Changed instructions")
    with pytest.raises(WorkflowError):
        e._dispatch(state)
    assert not stub.starts
    e.close()


def test_context_and_snapshot_change_during_job_invalidates_acceptance(engineering):
    root, config = engineering
    stub = Stub(delayed=True)
    e = Engine(root, launcher=stub)
    e.initialize(config)
    view = e.run()
    job = e.store.job(view["active_jobs"][0])
    stub.complete(job)
    observation = json.loads((Path(job["runtime"]) / "terminal.json").read_text())
    snapshot = Path(job["spec"]["read_artifact_refs"][0]["snapshot_path"])
    snapshot.write_text("Tampered snapshot")
    with pytest.raises(WorkflowError, match="snapshot digest mismatch"):
        e.accept(job, observation, view)
    snapshot.write_bytes((root / "AGENTS.md").read_bytes())
    (root / "AGENTS.md").write_text("New instructions during job")
    with pytest.raises(WorkflowError, match="Required engineering instructions changed"):
        e.accept(job, observation, view)
    e.close()


def test_baseline_and_checker_input_drift_rejected(engineering):
    root, config = engineering
    e = Engine(root, launcher=Stub(delayed=True))
    e.initialize(config)
    state = e._prepare({"view": e.view()})
    job = e.store.job(state["view"]["active_jobs"][0])
    (root / startup.CHECKERS[0]).write_text("print('different checker')")
    with pytest.raises(WorkflowError, match="checker inputs changed"):
        e._validate_engineering_job(job)
    (root / startup.CHECKERS[0]).write_text("print('fixture check passed')\n")
    git(root, "checkout", "-b", "different-branch")
    with pytest.raises(WorkflowError, match="Git baseline drift"):
        e._validate_engineering_job(job)
    e.close()


def test_concurrent_source_change_during_startup_blocks_dispatch(engineering, monkeypatch):
    root, config = engineering
    stub = Stub()
    e = Engine(root, launcher=stub)
    e.initialize(config)
    real_run = startup._bounded_run
    changed = False

    def concurrent_change(*args, **kwargs):
        nonlocal changed
        result = real_run(*args, **kwargs)
        if not changed:
            (root / "ADR.md").write_text("Concurrent source/context fact change")
            changed = True
        return result

    monkeypatch.setattr(startup, "_bounded_run", concurrent_change)
    with pytest.raises(WorkflowError, match=r"Candidate file set drift|inputs changed"):
        e.run()
    assert not stub.starts
    e.close()


def test_builder_changes_get_new_candidate_proof_and_completion_report_replays(engineering):
    root, config = engineering
    config["scope"]["allowed_paths"].append("construction/")
    stub = Stub()
    e = Engine(root, launcher=stub)
    e.initialize(config)
    e.run()
    stub.delayed = True
    view = e.approve(plan_token(e))
    job = e.store.job(view["active_jobs"][0])
    assert job["role"] == "builder"
    target = root / "construction/hooks.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Legitimate scoped builder source change\n")
    stub.complete(job)
    observation = json.loads((Path(job["runtime"]) / "terminal.json").read_text())
    first = e.accept(job, observation, view)
    second = startup.run(
        root,
        e.config,
        first["candidate"],
        e.runtime,
        root / "docs/ai/work-items/test-work",
        Path(first["engineering_startup"]["path"]),
    )
    assert first["engineering_startup"] == second
    assert first["candidate"]["candidate_id"] != job["candidate_id"]
    report = json.loads(Path(first["engineering_startup"]["path"]).read_text())
    assert report["passed"]
    assert report["candidate_id"] == first["candidate"]["candidate_id"]
    e.close()


def test_unreadable_sandbox_snapshot_blocks_dispatch(engineering, monkeypatch):
    root, config = engineering
    e = Engine(root, launcher=Stub())
    e.initialize(config)
    state = e._prepare({"view": e.view()})
    job = e.store.job(state["view"]["active_jobs"][0])
    # Simulate a mount accidentally omitted while retaining valid host bytes.
    from sandbox import command as real_command

    def omit_context(*args, **kwargs):
        kwargs["read_files"] = []
        return real_command(*args, **kwargs)

    monkeypatch.setattr(startup, "command", omit_context)
    with pytest.raises(WorkflowError, match="not readable/read-only"):
        e._validate_engineering_job(job)
    e.close()


def _copy_real_checker_inputs(root):
    source = Path(__file__).resolve().parents[2]
    for name in (
        *startup.CONTEXT_PATHS,
        *startup.CHECKERS,
        "ADR.md",
        "construction/hooks.py",
        "construction/api/theme_api.py",
    ):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    for name in ("construction/construction/doctype", "construction/patches"):
        shutil.copytree(source / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))


def test_actual_checkers_and_replay_safe_report(engineering):
    root, config = engineering
    _copy_real_checker_inputs(root)
    git(root, "add", ".")
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-m", "actual repository checker fixture")
    config["base_commit"] = git(root, "rev-parse", "HEAD").decode().strip()
    e = Engine(root, launcher=Stub())
    e.initialize(config)
    candidate = e.config["candidate"]
    report_path = e.runtime / "replay.json"
    ref = startup.run(
        root, e.config, candidate, e.runtime, root / "docs/ai/work-items/test-work", report_path
    )
    assert (
        startup.run(root, e.config, candidate, e.runtime, root / "docs/ai/work-items/test-work", report_path)
        == ref
    )
    assert json.loads(report_path.read_text())["passed"]
    e.close()


def test_real_schema_feature_scoped_facts_and_handover_reach_verifier(engineering):
    root, config = engineering
    _copy_real_checker_inputs(root)
    schema_name = "construction/construction/doctype/boq_item/boq_item.json"
    config["scope"]["allowed_paths"].extend([schema_name, "docs/ai/SCHEMA_FACTS.md", "SESSION_MEMORY.md"])
    git(root, "add", ".")
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-m", "actual schema feature baseline")
    config["base_commit"] = git(root, "rev-parse", "HEAD").decode().strip()
    stub = Stub()
    e = Engine(root, launcher=stub)
    e.initialize(config)
    e.run()
    stub.delayed = True
    view = e.approve(plan_token(e))
    job = e.store.job(view["active_jobs"][0])
    schema = json.loads((root / schema_name).read_text())
    schema["fields"].append(
        {"fieldname": "engineering_test_note", "fieldtype": "Data", "label": "Fixture note"}
    )
    (root / schema_name).write_text(json.dumps(schema))
    # This deliberate fixture schema change includes explicitly scoped facts regeneration;
    # the engine does not automatically regenerate facts to mask drift.
    namespace = runpy.run_path(str(root / startup.CHECKERS[0]))
    (root / "docs/ai/SCHEMA_FACTS.md").write_text(
        namespace["render_schema_facts"](namespace["load_schema_files"]())
    )
    with (root / "SESSION_MEMORY.md").open("a") as handle:
        handle.write("\nFixture schema feature handover\n")
    stub.complete(job)
    stub.delayed = False
    final = e.run()
    assert final["gate"]["scope"] == "COMMIT"
    verifier = e.store.job(stub.starts[-1])
    assert verifier["role"] == "verifier"
    refs = {r["source_relative_path"]: r for r in verifier["spec"]["read_artifact_refs"]}
    assert "engineering_test_note" in Path(refs["docs/ai/SCHEMA_FACTS.md"]["snapshot_path"]).read_text()
    assert "Fixture schema feature handover" in Path(refs["SESSION_MEMORY.md"]["snapshot_path"]).read_text()
    e.close()


def test_factual_updates_require_exact_scope_and_normative_context_stays_fixed(engineering):
    root, config = engineering
    config["scope"]["allowed_paths"].append("docs/ai/SCHEMA_FACTS.md")
    e = Engine(root, launcher=Stub())
    e.initialize(config)
    (root / "SESSION_MEMORY.md").write_text("Unapproved factual change")
    with pytest.raises(WorkflowError, match="Required engineering instructions changed"):
        startup.verify_required_context(root, e.config)
    e.close()
    assert startup.mutable_context_paths({"scope": {"allowed_paths": ["docs/ai/", "SESSION*"]}}) == set()


def test_instruction_write_scope_rejected_even_if_facts_are_explicitly_mutable(engineering):
    root, config = engineering
    config["scope"]["allowed_paths"].extend(["docs/ai/SCHEMA_FACTS.md", "AGENTS.md"])
    e = Engine(root, launcher=Stub())
    with pytest.raises(WorkflowError, match=r"intersects with scope.allowed_paths"):
        e.initialize(config)
    e.close()


@pytest.mark.parametrize("scope", ["*", "docs/ai/*.md", "docs/ai/SCHEMA*"])
def test_broad_scope_cannot_authorize_writing_mandatory_context(engineering, scope):
    root, config = engineering
    config["scope"]["allowed_paths"].append(scope)
    e = Engine(root, launcher=Stub())
    with pytest.raises(WorkflowError, match=r"intersects with scope.allowed_paths"):
        e.initialize(config)
    e.close()


def test_scope_adoption_cannot_add_instruction_write_paths(engineering):
    root, config = engineering
    config["stages"] = ["plan"]
    scope = {"allowed_paths": ["AGENTS.md"], "requirements": ["R1"], "validation_commands": []}

    class PlanningStub(Stub):
        def complete(self, job):
            super().complete(job)
            if job["role"] == "architect":
                output = Path(job["runtime"]) / "stdout.jsonl"
                payload = json.loads(output.read_text())
                payload["wire"]["plan_text"] = (
                    "```scope-proposal\n"
                    + json.dumps(
                        {
                            "schema": "scope-proposal/v1",
                            "implementation_stages": ["1"],
                            "scope": scope,
                        }
                    )
                    + "\n```"
                )
                output.write_text(json.dumps(payload))

    e = Engine(root, launcher=PlanningStub())
    e.initialize(config)
    e.run()
    before = dict(e.config)
    with pytest.raises(WorkflowError, match=r"intersects with scope.allowed_paths"):
        e.adopt_scope(scope, ["1"], "fixture-adoption", "fixture-hash")
    assert e.config == before
    assert not e.view()["plan_granted"]
    e.close()


def test_interpreter_cache_does_not_change_checker_input_binding(engineering):
    root, config = engineering
    startup.configure_new(root, config)
    before = startup.checker_inputs(root, config)
    cache = root / "construction/construction/doctype/__pycache__"
    cache.mkdir(parents=True)
    (cache / "module.pyc").write_bytes(b"cache")
    assert startup.checker_inputs(root, config) == before


def test_legacy_checkpoint_and_minimal_synthetic_repos_unchanged(configured):
    root, config = configured
    e = Engine(root, launcher=Stub())
    e.initialize(config)
    assert "engineering_startup_policy" not in e.config
    assert e.run()["gate"]["scope"] == "PLAN"
    e.close()
    e = Engine(root, launcher=Stub())
    assert "engineering_startup_policy" not in e.config
    assert e.run()["gate"]["scope"] == "PLAN"
    e.close()


def test_timeout_includes_child_that_closes_pipes_and_output_is_bounded(tmp_path):
    start = time.monotonic()
    result = startup._bounded_run(
        [sys.executable, "-c", "import os,time;os.close(1);os.close(2);time.sleep(60)"],
        tmp_path,
        timeout=0.2,
    )
    assert result["failure"] == "timeout"
    assert time.monotonic() - start < 3
    result = startup._bounded_run(
        [sys.executable, "-c", "import os;os.write(1,b'x'*1000000)"],
        tmp_path,
        limit=4096,
        output_dir=tmp_path / "private-logs",
    )
    assert result["failure"] == "output_limit"
    assert result["output_bytes"] <= 4096
    assert Path(result["stdout_log"]).stat().st_size <= 4096
    assert Path(result["stdout_log"]).stat().st_mode & 0o777 == 0o600
