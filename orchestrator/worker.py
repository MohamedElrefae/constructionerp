"""Detached job monitor. Only captures external observations; never grants approvals."""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from adapters import invocation, session_from
from core import atomic_write, utc, write_json
from validation_runner import run as run_validations


def process_identity(pid):
    try:
        raw = Path("/proc/" + str(pid) + "/stat").read_text()
        tail = raw[raw.rfind(")") + 2 :].split()
        if tail[0] == "Z":
            return None
        return tail[19]  # starttime, field 22 (tail begins at field 3)
    except (OSError, IndexError):
        return None


def run(spec_path):
    spec = json.loads(Path(spec_path).read_text())
    destination = Path(spec["runtime"])
    progress = dict(
        job_id=spec["job_id"],
        worker_pid=os.getpid(),
        worker_start=process_identity(os.getpid()),
        phase="WORKER_STARTED",
        session_id=None,
        started_utc=utc(),
    )
    write_json(destination / "progress.json", progress)
    stdout_path, stderr_path = destination / "stdout.jsonl", destination / "stderr.txt"
    native_started = False
    try:
        argv, env = invocation(spec)
        progress["phase"] = "NATIVE_LAUNCH_INTENT"
        write_json(destination / "progress.json", progress)
        with stdout_path.open("wb") as out, stderr_path.open("wb") as err:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                cwd=spec["root"],
                env=env,
                start_new_session=True,
            )
            native_started = True
            progress.update(
                phase="RUNNING", native_pid=process.pid, native_start=process_identity(process.pid)
            )
            write_json(destination / "progress.json", progress)
            started = time.monotonic()
            warned, timeout = False, False
            with stdout_path.open("r") as stream:
                while process.poll() is None:
                    if stdout_path.stat().st_size + stderr_path.stat().st_size > 20_000_000:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                        progress["output_limit_exceeded"] = True
                        break
                    if time.monotonic() - started >= spec.get("soft_timeout", 2700) and not warned:
                        warned = True
                        progress["soft_timeout_warning"] = True
                        write_json(destination / "progress.json", progress)
                    if time.monotonic() - started >= spec.get("hard_timeout", 3600):
                        timeout = True
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                        break
                    offset = stream.tell()
                    line = stream.readline()
                    if line and line.endswith("\n"):
                        try:
                            event = json.loads(line)
                            session = session_from(event, spec["tool"]) if isinstance(event, dict) else None
                            if session and not progress["session_id"]:
                                progress["session_id"] = session
                                write_json(destination / "progress.json", progress)
                        except ValueError:
                            pass
                    else:
                        stream.seek(offset)
                        time.sleep(0.1)
            code = process.wait()
        if code == 0 and spec.get("validation_commands"):
            progress["phase"] = "VALIDATION"
            write_json(destination / "progress.json", progress)
            run_validations(spec, destination, started + spec.get("hard_timeout", 3600))
        terminal = dict(
            progress,
            phase="TERMINAL",
            exit_code=code,
            timeout=timeout,
            finished_utc=utc(),
            stdout=str(stdout_path),
            stderr=str(stderr_path),
        )
    except OSError as exc:
        terminal = dict(
            progress,
            phase="UNCERTAIN" if native_started else "LAUNCH_FAILED",
            no_native_child=not native_started,
            error_type=type(exc).__name__,
            finished_utc=utc(),
        )
    except Exception as exc:
        terminal = dict(progress, phase="UNCERTAIN", error_type=type(exc).__name__, finished_utc=utc())
    write_json(destination / "terminal.json", terminal, immutable=True)


if __name__ == "__main__":
    run(sys.argv[1])
