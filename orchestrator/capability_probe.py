"""Phase 0 probes. Inventory is not a native pass; never dispatch engineering work."""

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]


def utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def capture(argv, cwd, timeout=20):
    start = utc()
    before = time.monotonic()
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    expired = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        expired = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    return {
        "command": argv,
        "cwd": str(cwd),
        "started_utc": start,
        "finished_utc": utc(),
        "elapsed_seconds": round(time.monotonic() - before, 3),
        "exit_code": process.returncode,
        "timeout": expired,
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
    }


def codex_probe(binary, private_dir):
    config_path = Path.home() / ".codex" / "config.toml"
    config = tomllib.loads(config_path.read_text()) if config_path.exists() else {}
    # Read only these non-secret settings. Auth remains owned by the native CLI.
    model = config.get("model")
    effort = config.get("model_reasoning_effort")
    if not model:
        return {"status": "BLOCKED", "reason": "No configured model to pin; no model chosen implicitly"}
    probe_root = private_dir / "workspace"
    probe_root.mkdir()
    schema = private_dir / "probe-schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {"probe": {"type": "string", "enum": ["ok"]}},
                "required": ["probe"],
                "additionalProperties": False,
            }
        )
    )
    result_path = private_dir / "last-message.json"
    prompt = 'Capability probe only. Do not read project files, use tools, or modify anything. Return exactly {"probe":"ok"}.'
    argv = [
        binary,
        "exec",
        "--ignore-user-config",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "--cd",
        str(probe_root),
        "--model",
        model,
        "--json",
        "--output-schema",
        str(schema),
        "--output-last-message",
        str(result_path),
    ]
    if effort:
        argv.extend(["-c", 'model_reasoning_effort="' + effort + '"'])
    argv.append(prompt)
    observed = capture(argv, probe_root, timeout=90)
    # Raw native output is private and is never included in the report.
    for stream in ("stdout", "stderr"):
        (private_dir / (stream + ".txt")).write_text(observed[stream])
    events = []
    for line in observed["stdout"].splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    session = next((e.get("thread_id") for e in events if e.get("type") == "thread.started"), None)
    valid = False
    if result_path.exists():
        try:
            valid = json.loads(result_path.read_text()) == {"probe": "ok"}
        except json.JSONDecodeError:
            pass
    passed = observed["exit_code"] == 0 and valid and bool(session)
    return {
        "status": "HEADLESS_PASS" if passed else "BLOCKED",
        "configured_model": model,
        "configured_effort": effort,
        "model_identity": "requested; backend identity requires Phase 1 observation",
        "session_id": session,
        "structured_output_valid": valid,
        "exit_code": observed["exit_code"],
        "timeout": observed["timeout"],
        "started_utc": observed["started_utc"],
        "finished_utc": observed["finished_utc"],
        "event_types": sorted({str(e.get("type")) for e in events}),
        "raw_output_sha256": hashlib.sha256(observed["stdout"].encode()).hexdigest(),
        "permission_boundary": "NOT_PROVEN: read-only requested; write-enabled builder control-store denial needs separate enforcement probe",
        "invocation": [part.replace(str(private_dir), "<private-probe-dir>") for part in argv],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-codex",
        action="store_true",
        help="Harmless network probe using the existing configured model/auth",
    )
    parser.add_argument(
        "--codex-binary", help="Explicit native executable; does not modify PATH or install anything"
    )
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = {"schema_version": 1, "phase": 0, "created_utc": utc(), "phase_exit": "BLOCKED", "tools": {}}
    private_base = ROOT / "orchestrator" / "var" / "probes"
    private_base.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_dir = Path(tempfile.mkdtemp(prefix="probe-", dir=private_base))
    for tool, command in (("codex", "codex"), ("antigravity", "agy"), ("opencode", "opencode")):
        if tool == "codex":
            bundled = "/opt/codex-desktop/resources/codex"
            binary = shutil.which(args.codex_binary or (bundled if Path(bundled).exists() else command))
        elif tool == "opencode":
            binary = shutil.which("opencode") or shutil.which("opencode-cli")
        else:
            binary = shutil.which(command)
        item = {"binary": binary, "status": "MISSING_BINARY" if not binary else "UNPROVEN"}
        if binary:
            try:
                check = capture([binary, "--version"], private_dir)
                item.update(version=check["stdout"].strip()[:200], version_exit_code=check["exit_code"])
            except OSError as exc:
                item.update(status="BLOCKED", reason=type(exc).__name__)
        report["tools"][tool] = item
    codex = report["tools"]["codex"]
    if args.run_codex and codex["binary"]:
        codex["headless_probe"] = codex_probe(codex["binary"], private_dir)
    report["required_remaining_gates"] = [
        "Owner review of versioned role prompts",
        "All native tools have accepted headless probes",
        "Control-store/approval-command permissions proven or owner-executed operation boundary recorded",
        "Models pinned from observed native configuration for all roles",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"phase_exit": report["phase_exit"], "report": str(args.report.resolve())}))
    return 1  # Inventory or one tool's success can never pass the full native gate.


if __name__ == "__main__":
    raise SystemExit(main())
