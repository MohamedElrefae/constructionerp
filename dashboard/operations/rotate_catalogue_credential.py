#!/usr/bin/env python3
"""Operator-invoked, supported 30-day read-only session rotation. No automatic renewal.
Never display tokens or raw auth/CLI errors; no dashboard restart or model calls.
"""

import fcntl
import hashlib
import json
import os
import stat
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

APP_ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path(os.environ.get("T3_DASHBOARD_RUNTIME", str(APP_ROOT.parents[1] / "runtime/dashboard")))
META = RUNTIME / "state"
STATE = Path.home() / ".local/state/t3-dashboard-picker-catalog-rc2"
TOKEN = STATE / "read-only-token"
RELEASE = Path(__file__).resolve().parent
CLI = str(Path.home() / ".t3/bin/t3")
PYTHON = str(RUNTIME / "base/runtime/dashboard/bin/python")
ORIGIN = "http://127.0.0.1:3773"
SCOPE = ["orchestration:read"]
TTL = "30d"
TTL_SECONDS = 30 * 24 * 60 * 60


def check(ok):
    if not ok:
        raise RuntimeError("Rotation refused")


def private_file(p):
    check(p.is_absolute() and not any(x.is_symlink() for x in [p, *p.parents]))
    st = p.stat()
    parent = p.parent.stat()
    check(
        st.st_uid == os.getuid() and stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and not st.st_mode & 0o077
    )
    check(parent.st_uid == os.getuid() and not parent.st_mode & 0o077)
    return p.read_bytes()


def atomic(p, data):
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".rotation-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, p)
        directory = os.open(p.parent, os.O_DIRECTORY | os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(tmp).unlink(missing_ok=True)


def run(args):
    return subprocess.run(
        args,
        capture_output=True,
        timeout=40,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def auth(*args):
    return run([CLI, "auth", "session", *args, "--base-dir", str(Path.home() / ".t3")])


def session(token):
    try:
        with urlopen(
            Request(ORIGIN + "/api/auth/session", headers={"Authorization": "Bearer " + token}), timeout=8
        ) as response:
            return json.load(response)
    except HTTPError as exc:
        if exc.code in (401, 403):
            return {"authenticated": False}
        raise


def exact_grant(state):
    return (
        state.get("authenticated") is True
        and state.get("sessionMethod") == "bearer-access-token"
        and state.get("scopes") == SCOPE
        and state.get("permissions") == SCOPE
    )


def properties(unit):
    result = run(
        [
            "systemctl",
            "--user",
            "show",
            unit,
            "-p",
            "ActiveState",
            "-p",
            "MainPID",
            "-p",
            "Result",
            "-p",
            "ExecMainStatus",
            "-p",
            "ExecMainStartTimestampMonotonic",
        ]
    )
    check(result.returncode == 0)
    return dict(line.split("=", 1) for line in result.stdout.decode().splitlines() if "=" in line)


def main():
    check(META.stat().st_uid == os.getuid() and not META.stat().st_mode & 0o077)
    check(STATE.stat().st_uid == os.getuid() and not STATE.stat().st_mode & 0o077)
    lockfd = os.open(META / "catalogue-rotation.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(lockfd)
        print(json.dumps({"status": "Rotation already running"}))
        return 2
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = META / ("rotation-" + stamp + ".json")
    report = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "preflight",
        "scope": SCOPE,
        "ttl_seconds": TTL_SECONDS,
        "automatic_renewal": False,
        "models_called": False,
        "dashboard_restarted": False,
        "token_disclosed": False,
    }

    def save():
        atomic(report_path, (json.dumps(report, indent=2) + "\n").encode())

    issued = None
    old_raw = None
    installed = False
    verified = False
    temporary = []
    try:
        current_path = META / "credential-state.json"
        current = json.loads(private_file(current_path))
        old_raw = private_file(TOKEN)
        old_token = old_raw.decode().strip()
        check(old_token and not any(x.isspace() for x in old_token))
        old = session(old_token)
        if old.get("authenticated"):
            check(exact_grant(old) and old.get("expiresAt") == current["expiresAt"])
        else:
            check(
                datetime.fromisoformat(current["expiresAt"].replace("Z", "+00:00"))
                <= datetime.now(timezone.utc)
            )
        listed = auth("list", "--json")
        check(listed.returncode == 0)
        previous = next(
            (s for s in json.loads(listed.stdout) if s["sessionId"] == current["sessionId"]), None
        )
        if previous:
            check(previous["method"] == "bearer-access-token" and previous["scopes"] == SCOPE)
            check(previous["expiresAt"] == current["expiresAt"])
        check(properties("t3-dashboard-auto.service")["ActiveState"] == "active")
        check(properties("t3-dashboard-picker-catalog-rc2.timer")["ActiveState"] == "active")
        original_pid = properties("t3-dashboard-auto.service")["MainPID"]
        report["old_session"] = {k: current[k] for k in ("sessionId", "expiresAt", "scopes")}
        report["stage"] = "issuance"
        save()
        result = auth(
            "issue",
            "--scope",
            "orchestration:read",
            "--ttl",
            TTL,
            "--label",
            "dashboard-picker-rc2-refresh-rotate-" + stamp,
            "--subject",
            "dashboard-readonly-catalogue-refresh",
            "--json",
        )
        check(result.returncode == 0)
        issued = json.loads(result.stdout)
        check(issued["method"] == "bearer-access-token" and issued["scopes"] == SCOPE)
        remaining = (
            datetime.fromisoformat(issued["expiresAt"].replace("Z", "+00:00")) - datetime.now(timezone.utc)
        ).total_seconds()
        check(TTL_SECONDS - 60 < remaining <= TTL_SECONDS + 1)
        check(exact_grant(session(issued["token"])))
        report["replacement"] = {k: issued[k] for k in ("sessionId", "method", "scopes", "expiresAt")}
        report["stage"] = "isolated_producer_check"
        save()
        fd, name = tempfile.mkstemp(dir=STATE, prefix=".rotation-token-")
        temporary.append(Path(name))
        with os.fdopen(fd, "w") as stream:
            stream.write(issued["token"])
            stream.flush()
            os.fsync(stream.fileno())
        probe = STATE / (".rotation-probe-" + stamp + ".json")
        temporary.append(probe)
        result = run(
            [
                "/usr/local/bin/node",
                str(RELEASE / "tools/refresh_catalog.mjs"),
                "--origin",
                ORIGIN,
                "--token-file",
                name,
                "--output",
                str(probe),
                "--python",
                PYTHON,
                "--once",
            ]
        )
        check(result.returncode == 0)
        doc = json.loads(private_file(probe))
        check(doc["source"] == "t3.server.getConfig" and doc["complete"] is True)
        check(issued["token"].encode() not in probe.read_bytes())
        report["isolated_producer_success"] = True
        atomic(TOKEN, issued["token"].encode())
        installed = True
        switched = time.monotonic() * 1_000_000
        report["switched_utc"] = datetime.now(timezone.utc).isoformat()
        report["stage"] = "await_scheduled_refresh"
        save()
        deadline = time.monotonic() + 150
        while True:
            props = properties("t3-dashboard-picker-catalog-rc2.service")
            if (
                int(props.get("ExecMainStartTimestampMonotonic", "0")) > switched
                and props.get("Result") == "success"
                and props.get("ExecMainStatus") == "0"
                and props.get("ActiveState") == "inactive"
            ):
                doc = json.loads(private_file(STATE / "catalog.json"))
                check(doc["source"] == "t3.server.getConfig" and doc["complete"] is True)
                check(
                    datetime.fromisoformat(doc["fetched_at"].replace("Z", "+00:00"))
                    > datetime.fromisoformat(report["switched_utc"])
                )
                break
            check(time.monotonic() < deadline)
            time.sleep(2)
        verified = True
        state = {k: issued[k] for k in ("sessionId", "method", "scopes", "expiresAt")}
        state["last_rotation_report"] = str(report_path)
        state["superseded_session_pending_revocation"] = current["sessionId"]
        atomic(current_path, (json.dumps(state, indent=2) + "\n").encode())
        report["scheduled_refresh"] = {
            "verified": True,
            "fetched_at": doc["fetched_at"],
            "models": sum(len(p["models"]) for p in doc["providers"]),
            "provider_instances": len(doc["providers"]),
        }
        report["stage"] = "revoke_superseded_after_success"
        save()
        if previous:
            result = auth("revoke", current["sessionId"])
            check(result.returncode == 0)
        check(session(old_token).get("authenticated") is not True)
        check(exact_grant(session(issued["token"])))
        check(properties("t3-dashboard-auto.service")["MainPID"] == original_pid)
        state.pop("superseded_session_pending_revocation")
        atomic(current_path, (json.dumps(state, indent=2) + "\n").encode())
        report.update(
            {
                "status": "SUCCESS",
                "superseded_revoked_or_expired": True,
                "superseded_bearer_rejected": True,
                "replacement_authenticated": True,
                "dashboard_pid_preserved": original_pid,
                "token_mode": "0600",
                "directory_mode": "0700",
                "ongoing_rotation": "Manual operator invocation only; no credential-management authority added to refresh unit",
            }
        )
    except Exception:
        report["status"] = "FAILED" if not verified else "REPLACEMENT_WORKS_REQUIRES_OPERATOR_FOLLOWUP"
        report["failure"] = "Stopped at recorded stage; secret-bearing outputs suppressed"
        if not verified:
            if installed and old_raw is not None:
                atomic(TOKEN, old_raw)
                report["old_token_restored"] = True
            if issued:
                report["failed_replacement_revoked"] = auth("revoke", issued["sessionId"]).returncode == 0
    finally:
        for p in temporary:
            p.unlink(missing_ok=True)
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save()
        os.close(lockfd)
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(report_path),
                "replacement_expires_at": report.get("replacement", {}).get("expiresAt"),
                "superseded_revoked_or_expired": report.get("superseded_revoked_or_expired", False),
            }
        )
    )
    return 0 if report["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({"status": "Preflight refused; no secret output"}))
        raise SystemExit(2)
