"""Coordinator-owned engineering startup evidence; never an agent approval."""

import fnmatch
import json
import os
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path

from candidates import allowed, git, recheck
from core import WorkflowError, atomic_write, bytes_hash, digest, utc, within, write_json
from sandbox import command
from validation_runner import can_unshare_net

POLICY = "engineering-startup/v1"
CONTEXT_PATHS = (
    "AGENTS.md",
    "SESSION_MEMORY.md",
    "docs/ai/PROFESSIONAL_ENGINEERING_STANDARD.md",
    "docs/ai/CONTEXT_INDEX.md",
    "docs/ai/SCHEMA_FACTS.md",
    "AGENT_WORKFLOW.md",
)
CHECKERS = ("scripts/schema_drift_checker.py", "scripts/ai_context_check.py")
FACTUAL_CONTEXT_PATHS = {"SESSION_MEMORY.md", "docs/ai/SCHEMA_FACTS.md", "docs/ai/CONTEXT_INDEX.md"}
TIMEOUT_SECONDS = 30
OUTPUT_LIMIT = 262144


def enabled(config):
    policy = config.get("engineering_startup_policy")
    if policy is None:
        return False  # Existing persisted checkpoints are deliberately not migrated.
    if policy != POLICY:
        raise WorkflowError("Unsupported engineering_startup_policy; required version is " + POLICY)
    return True


def context_manifest(root, config):
    root = Path(root).resolve()
    entries = []
    paths = list(dict.fromkeys([*CONTEXT_PATHS, *config.get("read_only_context_paths", [])]))
    for name in paths:
        path = within(root, name)
        if not path.is_file():
            if name in CONTEXT_PATHS:
                raise WorkflowError("Required engineering context missing: " + name)
            continue
        entries.append({"path": name, "sha256": bytes_hash(path.read_bytes())})
    return entries


def configure_new(root, config):
    """Fresh Construction/native tasks cannot silently omit or disable the policy."""
    root = Path(root).resolve()
    required = (
        (root / "construction").exists()
        or any((root / p).exists() for p in CHECKERS)
        or (root / CONTEXT_PATHS[2]).exists()
        or any(p.get("tool") != "synthetic" for p in config.get("roles", {}).values())
    )
    if required and "engineering_startup_policy" not in config:
        config["engineering_startup_policy"] = POLICY
    if required and not enabled(config):
        raise WorkflowError("New engineering tasks require " + POLICY)
    if not enabled(config):
        return
    config["read_only_context_paths"] = list(
        dict.fromkeys([*CONTEXT_PATHS, *config.get("read_only_context_paths", [])])
    )
    validate_scope(config)
    manifest = context_manifest(root, config)
    config["engineering_required_context"] = [e for e in manifest if e["path"] in CONTEXT_PATHS]
    for checker in CHECKERS:
        if not within(root, checker).is_file():
            raise WorkflowError("Required engineering startup checker missing: " + checker)


def verify_required_context(root, config):
    current = context_manifest(root, config)
    required = [e for e in current if e["path"] in CONTEXT_PATHS]
    mutable = mutable_context_paths(config)
    if [e for e in required if e["path"] not in mutable] != [
        e for e in config.get("engineering_required_context", []) if e["path"] not in mutable
    ]:
        raise WorkflowError("Required engineering instructions changed; reconcile in a new reviewed task")
    return current


def mutable_context_paths(config):
    """Only explicitly scoped factual files may change; directory/glob scope is insufficient."""
    return FACTUAL_CONTEXT_PATHS.intersection(config.get("scope", {}).get("allowed_paths", []))


def validate_scope(config):
    if not enabled(config):
        return
    mutable = mutable_context_paths(config)
    for name in config.get("read_only_context_paths", []):
        if name in mutable:
            continue
        for pattern in config.get("scope", {}).get("allowed_paths", []):
            # Shared candidate semantics plus conservative rejection of apparent glob
            # write scope (the legacy candidate matcher accepts exact/prefix paths).
            if allowed(name, [pattern]) or fnmatch.fnmatchcase(name, pattern):
                raise WorkflowError(
                    "Read-only engineering context intersects with scope.allowed_paths: " + name
                )


def checker_inputs(root, config):
    """Bind every source/schema input read by the two repository checkers."""
    root = Path(root).resolve()
    names = {*CHECKERS, "ADR.md", "construction/hooks.py", "construction/api/theme_api.py"}
    entries = []
    for base, pattern in (
        ("construction/construction/doctype", "**/*"),
        ("construction/patches", "**/*"),
    ):
        directory = within(root, base)
        if directory.exists():
            names.update(str(p.relative_to(root)) for p in directory.glob(pattern))
    for name in sorted(names):
        path = within(root, name)
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_dir():
            entries.append({"path": name, "kind": "directory"})
        elif path.is_file():
            entries.append({"path": name, "kind": "file", "sha256": bytes_hash(path.read_bytes())})
        else:
            entries.append({"path": name, "kind": "missing"})
    return {"context": verify_required_context(root, config), "checker_inputs": entries}


def git_baseline(root):
    return {
        "root": git(root, "rev-parse", "--show-toplevel").decode().strip(),
        "branch": git(root, "rev-parse", "--abbrev-ref", "HEAD").decode().strip(),
        "head": git(root, "rev-parse", "HEAD").decode().strip(),
        "short_head": git(root, "rev-parse", "--short", "HEAD").decode().strip(),
        "status": git(root, "status", "--short").decode(),
    }


def _bounded_run(argv, root, timeout=TIMEOUT_SECONDS, limit=OUTPUT_LIMIT, output_dir=None):
    """Bound output in memory and kill the complete isolated process group on failure."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for key in list(env):
        if key.startswith(("WORKFLOW_", "LANGSMITH_", "LANGCHAIN_")):
            env.pop(key)
    process = subprocess.Popen(
        argv,
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        env=env,
    )
    chunks = {"stdout": bytearray(), "stderr": bytearray()}
    failure = None
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    failure = "timeout"
                    break
                for key, _ in selector.select(min(remaining, 0.1)):
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    available = limit - sum(len(v) for v in chunks.values())
                    chunks[key.data].extend(data[:available])
                    if len(data) > available:
                        failure = "output_limit"
                        break
                if failure:
                    break
        if failure:
            os.killpg(process.pid, signal.SIGKILL)
        try:
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            failure = "timeout"
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        process.stdout.close()
        process.stderr.close()
    result = {
        "exit_code": process.returncode,
        "failure": failure,
        # Do not distribute arbitrary checker output (potentially private values).
        "stdout_sha256": bytes_hash(bytes(chunks["stdout"])),
        "stderr_sha256": bytes_hash(bytes(chunks["stderr"])),
        "output_bytes": sum(len(v) for v in chunks.values()),
    }
    if output_dir:
        directory = Path(output_dir)
        if directory.is_symlink():
            raise WorkflowError("Symlink startup diagnostic directory refused")
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory.chmod(0o700)
        for name, data in chunks.items():
            path = directory / (name + ".log")
            atomic_write(path, bytes(data), immutable=True)
            path.chmod(0o600)
            result[name + "_log"] = str(path)
    return result


def check_snapshot_visibility(root, work, runtime, refs, report_path):
    """Exercise the exact mounts hiding control state and restoring selected artifacts."""
    files = [r["snapshot_path"] for r in refs] + [str(report_path)]
    code = (
        "import hashlib,json,os,sys; from pathlib import Path; "
        "refs=json.loads(sys.argv[1]); "
        "assert all(hashlib.sha256(Path(r['snapshot_path']).read_bytes()).hexdigest()==r['sha256'] "
        "for r in refs); "
        "assert all(not os.access(p, os.W_OK) for p in json.loads(sys.argv[2]))"
    )
    wrapped = _offline_command(
        [sys.executable, "-c", code, json.dumps(refs), json.dumps(files)],
        root,
        work,
        runtime,
        read_files=files,
    )
    result = _bounded_run(wrapped, root, timeout=10)
    if result["exit_code"] or result["failure"]:
        raise WorkflowError("Engineering context snapshots are not readable/read-only in dispatch sandbox")


def _offline_command(argv, root, work, runtime, read_files=()):
    wrapped = command(
        argv,
        root,
        work,
        hidden_roots=[runtime, work],
        read_files=read_files,
        writable_source=False,
    )
    wrapped.insert(1, "--unshare-net")
    # Generic native isolation hides control contents in writable empty tmpfs.
    # Startup commands additionally cannot manufacture files at those hidden paths.
    index = wrapped.index("--chdir")
    for hidden in (runtime, work):
        if Path(hidden).exists():
            wrapped[index:index] = ["--remount-ro", str(Path(hidden).resolve())]
            index += 2
    return wrapped


def run(root, config, candidate, runtime, work, report_path):
    """Run actual trusted-coordinator startup checks; persist success or failure."""
    root, report_path = Path(root).resolve(), Path(report_path)
    if report_path.exists():
        # Completion acceptance can replay after evidence persistence but before the
        # durable result event. Reuse only exact, still-valid successful evidence.
        ref = {"path": str(report_path), "sha256": bytes_hash(report_path.read_bytes())}
        _, previous = verify_report(root, config, candidate["candidate_id"], ref)
        recheck(root, candidate["manifest"], config["generated"])
        return {**ref, "inputs_digest": previous["inputs_digest"]}
    report = {
        "schema": POLICY,
        "candidate_id": candidate["candidate_id"],
        "started_utc": utc(),
        "interpreter": sys.executable,
        "commands": [],
        "passed": False,
    }
    try:
        if not can_unshare_net():
            raise WorkflowError("Engineering startup requires network-isolated offline sandbox")
        recheck(root, candidate["manifest"], config["generated"])
        before = checker_inputs(root, config)
        report.update(baseline=git_baseline(root), inputs=before, inputs_digest=digest(before))
        for index, checker in enumerate(CHECKERS):
            argv = [sys.executable, checker]
            wrapped = _offline_command(argv, root, work, runtime)
            record = {
                "argv": argv,
                "cwd": str(root),
                **_bounded_run(
                    wrapped,
                    root,
                    output_dir=(Path(runtime) / "startup-private" / report_path.stem / str(index)),
                ),
            }
            report["commands"].append(record)
            if record["exit_code"] or record["failure"]:
                raise WorkflowError(
                    "Engineering startup check failed: "
                    + checker
                    + " ("
                    + str(record["failure"] or f"exit {record['exit_code']}")
                    + "); bounded owner-only diagnostics: "
                    + record["stdout_log"]
                    + " / "
                    + record["stderr_log"]
                )
        recheck(root, candidate["manifest"], config["generated"])
        if checker_inputs(root, config) != before:
            raise WorkflowError("Engineering startup inputs changed during checks")
        report["passed"] = True
    except (OSError, WorkflowError) as exc:
        report["failure"] = str(exc)
        raise
    finally:
        report["finished_utc"] = utc()
        write_json(report_path, report, immutable=True)
    return {
        "path": str(report_path),
        "sha256": bytes_hash(report_path.read_bytes()),
        "inputs_digest": report["inputs_digest"],
    }


def verify_report(root, config, candidate_id, ref, *, allow_builder_changes=False):
    path = Path(ref["path"])
    if path.is_symlink() or bytes_hash(path.read_bytes()) != ref["sha256"]:
        raise WorkflowError("Engineering startup evidence digest mismatch")
    report = json.loads(path.read_text())
    if (
        not report.get("passed")
        or report.get("schema") != POLICY
        or report.get("candidate_id") != candidate_id
    ):
        raise WorkflowError("Engineering startup evidence binding mismatch")
    baseline = report.get("baseline", {})
    for name, args in (
        ("root", ("rev-parse", "--show-toplevel")),
        ("branch", ("rev-parse", "--abbrev-ref", "HEAD")),
        ("head", ("rev-parse", "HEAD")),
    ):
        if git(root, *args).decode().strip() != baseline.get(name):
            raise WorkflowError("Engineering startup Git baseline drift: " + name)
    current = checker_inputs(root, config)
    mutable = mutable_context_paths(config) if allow_builder_changes else set()
    if [e for e in current["context"] if e["path"] not in mutable] != [
        e for e in report["inputs"]["context"] if e["path"] not in mutable
    ]:
        raise WorkflowError("Engineering context changed after startup")
    if not allow_builder_changes and digest(current) != report["inputs_digest"]:
        raise WorkflowError("Engineering checker inputs changed after startup")
    return current, report
