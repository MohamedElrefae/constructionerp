#!/usr/bin/env python3
"""Least-privilege clean-state supervisor for automatic dashboard startup.

It never renews credentials, restores old state, reconciles actions, or kills an
unknown owner.  Admission is clean-idle-only.  Unsafe admission exits 78 (no
automatic retry by systemd) and leaves a private status record plus an OnFailure
alert.  Only the newly spawned, identity-pinned child receives graceful
termination when the supervisor is asked to stop.

The supported state-owner fence remains the reviewed authority lease acquired by
``quiescent_handoff.launch.Prepared``.  This supervisor can therefore never create
a second state owner: a concurrent owner, a stale-but-alive owner, an occupied
port, a busy execution lock or a dirty crash database all refuse before spawn.
"""

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import signal
import socket
import stat
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

EXIT_BLOCKED = 78


class Refused(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def private(value):
    p = Path(value)
    if not p.is_absolute() or ".." in p.parts or any(x.is_symlink() for x in [p, *p.parents]):
        raise Refused("unsafe_path")
    parent = p.parent.stat()
    if parent.st_uid != os.getuid() or parent.st_mode & 0o077:
        raise Refused("metadata_not_private")
    return p


def pinned_file(value):
    """Code/helper file pin: owned, regular, not group/world writable.

    The parent need not be 0700 (release/tool trees are normally readable).
    """
    p = Path(value)
    if not p.is_absolute() or ".." in p.parts or any(x.is_symlink() for x in [p, *p.parents]):
        raise Refused("unsafe_path")
    st = p.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o022:
        raise Refused("source_not_private")
    return p


def document(value):
    p = private(value)
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as f:
        st = os.fstat(f.fileno())
        if (
            not stat.S_ISREG(st.st_mode)
            or st.st_uid != os.getuid()
            or st.st_nlink != 1
            or st.st_mode & 0o077
            or st.st_size > 16_000_000
        ):
            raise Refused("metadata_not_private")
        return json.load(f)


def atomic(value, doc):
    p = private(value)
    tmp = p.with_name("." + p.name + "." + uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(doc, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
        directory = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        tmp.unlink(missing_ok=True)


def boot_id():
    return Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _under(path, roots):
    try:
        target = Path(path)
        return any(target.is_relative_to(root) for root in roots)
    except (OSError, ValueError):
        return False


def _cgroup_related(pid, roots):
    """Best-effort: a same-UID process in a cgroup naming a canonical path.

    A generic unit-name match is intentionally not used: an unrelated live
    dashboard must not block a disposable/release candidate, and only paths that
    actually belong to the roots under review are evidence of a relation.
    """
    try:
        text = (Path("/proc") / str(pid) / "cgroup").read_text()
    except OSError:
        return False
    return any(str(root) in text for root in roots)


def writers(roots, exclude=()):
    """Observe same-filesystem-UID writers under the canonical roots.

    Returns ``busy`` (definite or plausibly related writer) and
    ``uninspectable_unrelated`` (standard non-dumpable desktop/system processes
    whose /proc entry cannot be read).  The latter is reported, not treated as a
    writer: systemd --user and the user session manager are always non-dumpable,
    so treating every one as fatal would make automatic startup impossible.  The
    documented limit is that a deliberately hostile same-UID process outside the
    dashboard cgroups is outside this user-service guarantee.
    """
    roots = [Path(root) for root in roots]
    matches = []
    unrelated = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) in {*exclude, os.getpid()}:
            continue
        pid = int(proc.name)
        try:
            status = (proc / "status").read_text()
            uids = next(line for line in status.splitlines() if line.startswith("Uid:")).split()[1:]
            if int(uids[3]) != os.getuid():
                continue
        except (OSError, StopIteration):
            continue
        comm = "?"
        try:
            comm = (proc / "comm").read_text().strip()
        except OSError:
            pass
        # Readable metadata that points at the roots is a definite relation.
        try:
            cmdline = (proc / "cmdline").read_bytes().decode("utf-8", "replace")
        except OSError:
            cmdline = ""
        # A command line that merely mentions a path (shells, editors, test
        # harnesses) is not a state writer.  Only known dashboard/launcher
        # programs that also name one of the protected paths are related.
        markers = ("quiescent_handoff", "dashboard.app", "incumbent_runtime", "catalog_front")
        related = any(str(root) in cmdline for root in roots) and any(marker in cmdline for marker in markers)
        cwd_target = None
        for link in ("cwd", "exe"):
            try:
                target = os.readlink(proc / link).removesuffix(" (deleted)")
                if link == "cwd":
                    cwd_target = target
                if _under(target, roots):
                    related = True
            except OSError:
                pass
        # A legacy unsealed launcher has no cooperative handler and no authority
        # lease of its own.  Its working directory/environment is the practical
        # identifier; a bare `dashboard.app` in an unrelated process is not enough.
        if "dashboard.app" in cmdline:
            if cwd_target and _under(cwd_target, roots):
                related = True
            else:
                try:
                    env_text = (proc / "environ").read_bytes().decode("utf-8", "replace")
                except OSError:
                    env_text = ""
                if any(str(root) in env_text for root in roots):
                    related = True
        if _cgroup_related(pid, roots):
            related = True
        try:
            for fd in (proc / "fd").iterdir():
                try:
                    name = os.readlink(fd).removesuffix(" (deleted)")
                    if not name.startswith("/") or not _under(name, roots):
                        continue
                    info = (proc / "fdinfo" / fd.name).read_text()
                    flags = int(
                        next(line for line in info.splitlines() if line.startswith("flags:")).split()[1], 8
                    )
                    if flags & os.O_ACCMODE != os.O_RDONLY:
                        matches.append({"pid": pid, "comm": comm, "kind": "write_capable_state_handle"})
                except FileNotFoundError:
                    continue
                except (PermissionError, StopIteration, OSError):
                    if related:
                        matches.append({"pid": pid, "comm": comm, "kind": "uninspectable_fd_table"})
                    else:
                        unrelated.append({"pid": pid, "comm": comm})
                    break
        except PermissionError:
            if related:
                matches.append({"pid": pid, "comm": comm, "kind": "uninspectable_related_process"})
            else:
                unrelated.append({"pid": pid, "comm": comm})
        except FileNotFoundError:
            continue
        except OSError:
            if related:
                matches.append({"pid": pid, "comm": comm, "kind": "uninspectable_related_process"})
        if related and not any(item["pid"] == pid for item in matches):
            matches.append({"pid": pid, "comm": comm, "kind": "related_process_metadata"})
    return {"busy": matches, "uninspectable_unrelated": unrelated}


def _catalogue_state(path):
    """Metadata-only credential/catalogue freshness; never reads a token."""
    p = Path(path)
    result = {"path": str(p), "present": p.exists(), "freshness": "unknown"}
    try:
        st = p.stat()
        result["private"] = st.st_uid == os.getuid() and not st.st_mode & 0o077
        result["size"] = st.st_size
    except OSError:
        result["private"] = False
    if not p.exists():
        result["freshness"] = "missing"
        return result
    try:
        doc = json.loads(p.read_text())
        fetched = doc.get("fetched_at")
        if fetched:
            from datetime import datetime as _dt

            then = _dt.fromisoformat(str(fetched).replace("Z", "+00:00"))
            if then.tzinfo is None:
                then = then.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - then).total_seconds()
            result["fetched_at"] = fetched
            result["freshness"] = "stale" if age > 3600 else "fresh"
    except (OSError, ValueError, TypeError):
        result["freshness"] = "unreadable"
    return result


def _credential_state(path):
    """Metadata-only expiry classification.  Expiry never blocks local startup."""
    if not path:
        return {"state": "not_configured"}
    p = Path(path)
    try:
        doc = json.loads(p.read_text())
        expires = doc.get("expiresAt")
        if not expires:
            return {"state": "unknown", "path": str(p)}
        from datetime import datetime as _dt

        then = _dt.fromisoformat(str(expires).replace("Z", "+00:00"))
        if then.tzinfo is None:
            then = then.replace(tzinfo=timezone.utc)
        seconds = (then - datetime.now(timezone.utc)).total_seconds()
        state = "expired" if seconds <= 0 else ("expiring" if seconds <= 7 * 86400 else "valid")
        return {"state": state, "expires_at": str(expires), "path": str(p)}
    except (OSError, ValueError, TypeError):
        return {"state": "unreadable", "path": str(p)}


@contextmanager
def _port_free(port):
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", int(port)))
        except OSError:
            raise Refused("configured_port_occupied") from None
    yield


class Controller:
    def __init__(self, policy_file):
        self.path = private(policy_file)
        self.policy = document(self.path)
        p = self.policy
        if (
            p.get("schema") != "automatic-dashboard/v1"
            or p.get("uid") != os.getuid()
            or p.get("admission") != "clean-idle-only"
        ):
            raise Refused("policy_contract")
        self.meta = self.path.parent
        self.status_path = self.meta / "automatic-status.json"
        self.owner_path = self.meta / "automatic-owner.json"
        if p["tool_sha256"] != digest(__file__):
            raise Refused("controller_source_changed")
        helper_path = pinned_file(p["helper"])
        if digest(helper_path) != p["helper_sha256"]:
            raise Refused("helper_source_changed")
        spec = importlib.util.spec_from_file_location("automatic_fresh_helper", helper_path)
        self.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.helper)
        self.release, self.reviewed, self.h = self.helper.runtime(p["release"])
        if digest(self.release / "HANDOFF_SOURCE.json") != p["release_contract_sha256"]:
            raise Refused("release_changed")
        (
            self.identity,
            self.listener,
            self.read_private,
            self.alive,
            self.seal,
            self.write_private,
            self.location,
            self.Unsafe,
        ) = self.h
        self.lock = None
        self.child = None
        self.stop_requested = False

    def status(self, phase, reason=None, **extra):
        record = {
            "schema": "automatic-dashboard-status/v1",
            "phase": phase,
            "reason": reason,
            "boot_id": boot_id(),
            "recorded_utc": datetime.now(timezone.utc).isoformat(),
            "unit": "t3-dashboard-auto.service",
            "operator_action": (
                "Inspect this status and the unit journal; preserve current state. "
                "No force kill, old-state restore, automatic reconciliation or auth reset."
            ),
            "alert": "OnFailure=t3-dashboard-auto-alert.service",
            **extra,
        }
        atomic(self.status_path, record)
        print(json.dumps({"phase": phase, "reason": reason}), flush=True)

    def acquire(self):
        fd = os.open(
            private(self.meta / "automatic-supervisor.lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise Refused("another_supervisor") from None
        self.lock = fd

    def _owner_record_ok(self, record):
        if record.get("lease_file") != self.policy["lease_file"]:
            raise Refused("owner_lease_mismatch")
        if record.get("release_root") != str(self.release):
            raise Refused("owner_release_mismatch")
        if record.get("release_contract_sha256") != self.policy["release_contract_sha256"]:
            raise Refused("owner_release_changed")
        plan_file = Path(record["source_plan"])
        if digest(plan_file) != record["source_plan_sha256"]:
            raise Refused("owner_plan_changed")
        plan = document(plan_file)
        if plan["lease_file"] != self.policy["lease_file"]:
            raise Refused("plan_lease_mismatch")
        owner_record = Path(record.get("owner_record", ""))
        if owner_record.exists():
            if document(owner_record) != record["owner"]:
                raise Refused("owner_readiness_mismatch")
        return plan

    def _owner_status(self, owner):
        """Classify a same-boot recorded owner without assuming /proc access.

        ``gone`` is safe (the PID/entry no longer exists, or was reused with a
        different identity).  An existing but unreadable entry is not proof of
        death and fails closed.
        """
        proc = Path("/proc") / str(owner["pid"])
        if not proc.exists():
            return "gone"
        try:
            fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
            if fields[0] == "Z":
                return "gone"
        except (OSError, IndexError):
            pass
        try:
            current = self.identity(owner["pid"])
        except Exception:
            raise Refused("previous_owner_unverifiable") from None
        return "alive" if current == owner else "gone"

    def previous(self):
        if self.owner_path.exists():
            record = document(self.owner_path)
        else:
            record = document(self.policy["initial_receipt"])
        plan = self._owner_record_ok(record)
        owner = record.get("owner")
        if (
            not isinstance(owner, dict)
            or not isinstance(owner.get("pid"), int)
            or not owner.get("start_ticks")
        ):
            raise Refused("owner_identity_malformed")
        same_boot = record.get("boot_id") == boot_id()
        if same_boot and self._owner_status(owner) == "alive":
            raise Refused("previous_owner_alive")
        return record, plan, same_boot

    def prepare(self, mode):
        record, old, same_boot = self.previous()
        anchor = old["anchor"]
        self.helper.clean_sidecars(anchor)
        from quiescent_handoff.state import registry_image

        tasks, _, _, _ = registry_image(anchor["state"]["registry"]["path"])
        roots = [
            anchor["source_root"],
            anchor["state"]["var_dir"]["path"],
            *[str(Path(t["worktree_path"]) / "orchestrator/var") for t in tasks],
            record["source_plan"],
            self.policy["lease_file"],
        ]
        observation = writers(roots)
        if observation["busy"]:
            raise Refused("busy_or_related_writer")
        self.location(self.path, [*old["metadata_exclusions"], str(self.release)])
        if Path(self.policy["lease_file"]).parent != self.meta:
            raise Refused("metadata_lease_directory")
        with _port_free(self.policy["port"]):
            plan = self.seal(
                anchor, self.policy["lease_file"], self.release, self.reviewed["files"], mode, record["owner"]
            )
        self.helper.clean_sidecars(anchor)
        # A peer appearing during private-copy/seal work must not be assumed away.
        observation = writers(roots)
        if observation["busy"]:
            raise Refused("writer_visibility_changed")
        target = self.meta / ("automatic-plan-" + uuid.uuid4().hex + ".json")
        self.write_private(target, plan)
        return target, plan, observation, same_boot

    def child_argv(self, plan):
        return [
            self.policy["python"],
            "-m",
            "quiescent_handoff",
            "--plan",
            str(plan),
            "--port",
            str(self.policy["port"]),
        ]

    def spawn(self, path):
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("DASHBOARD_", "ORCHESTRATOR_", "CANONICAL_"))
        }
        env.update(
            PYTHONPATH=str(self.release / "src"),
            PYTHONDONTWRITEBYTECODE="1",
            DASHBOARD_MODEL_CATALOG_FILE=self.policy["catalogue"],
        )
        env.pop("NOTIFY_SOCKET", None)
        # Same cgroup/UID. No process-group/scope signals and no parent-death kill.
        return subprocess.Popen(self.child_argv(path), cwd=self.release, env=env)

    def remember(self, owner, path):
        record = {
            "schema": "fresh-restart-receipt/v1",
            "boot_id": boot_id(),
            "owner": owner,
            "owner_record": str(path) + ".owner.json",
            "source_plan": str(path),
            "source_plan_sha256": digest(path),
            "release_root": str(self.release),
            "release_contract_sha256": self.policy["release_contract_sha256"],
            "lease_file": self.policy["lease_file"],
        }
        atomic(self.owner_path, record)

    def start_attempt(self, mode):
        if self.stop_requested:
            raise Refused("stop_requested_before_start")
        path, plan, observation, same_boot = self.prepare(mode)
        self.status(
            "starting",
            mode=mode,
            plan=str(path),
            cross_boot=not same_boot,
            uninspectable_unrelated=len(observation["uninspectable_unrelated"]),
            catalogue=_catalogue_state(self.policy["catalogue"]),
            credential=_credential_state(self.policy.get("credential_metadata")),
        )
        if self.stop_requested:
            raise Refused("stop_requested_before_start")
        self.child = self.spawn(path)
        deadline = time.monotonic() + int(self.policy.get("startup_timeout", 30))
        ready = Path(str(path) + ".owner.json")
        # Record a partial child even if import fails before readiness.  Future
        # attempts must prove it exited; a missing readiness record is not proof.
        for _ in range(20):
            try:
                owner = self.identity(self.child.pid)
                break
            except Exception:
                if self.child.poll() is not None:
                    return None
                time.sleep(0.01)
        else:
            raise Refused("partial_child_identity_unavailable")
        self.remember(owner, path)
        while self.child.poll() is None:
            if ready.exists():
                owner = document(ready)
                if self.identity(self.child.pid) != owner or not self.listener(
                    owner["pid"], f'http://127.0.0.1:{self.policy["port"]}'
                ):
                    raise Refused("ready_owner_mismatch")
                self.remember(owner, path)
                self.status(
                    "ready",
                    mode=mode,
                    pid=owner["pid"],
                    cross_boot=not same_boot,
                    session_policy="relogin-required",
                    catalogue=_catalogue_state(self.policy["catalogue"]),
                    credential=_credential_state(self.policy.get("credential_metadata")),
                )
                return owner
            if time.monotonic() > deadline:
                raise Refused("startup_still_alive_without_readiness")
            time.sleep(0.03)
        return None

    def terminate_own_child(self, *_):
        self.stop_requested = True
        if self.child is None or self.child.poll() is not None:
            return
        try:
            owner = self.identity(self.child.pid)
            fd = os.pidfd_open(self.child.pid)
            try:
                if self.identity(self.child.pid) == owner:
                    signal.pidfd_send_signal(fd, signal.SIGTERM, None, 0)
            finally:
                os.close(fd)
        except (ProcessLookupError, OSError):
            return

    def run(self):
        try:
            self.acquire()
            owner = self.start_attempt("guarded")
            if owner is None:
                self.status(
                    "guarded_start_failed",
                    "attempting_rollback_bridge"
                    if self.policy.get("allow_bridge_fallback")
                    else "refusing_without_bridge_opt_in",
                )
                if not self.policy.get("allow_bridge_fallback"):
                    raise Refused("guarded_start_failed")
                owner = self.start_attempt("rollback_bridge")
            if owner is None:
                raise Refused("guarded_and_bridge_start_failed")
            while self.child.poll() is None:
                time.sleep(0.2)
            if self.stop_requested:
                self.status("stopped", "requested_graceful_stop")
                return 0
            self.status(
                "owner_exited",
                "systemd_may_retry_only_after_fresh_admission",
                exit_code=self.child.returncode,
            )
            return 1
        except Exception as exc:
            if self.stop_requested and (self.child is None or self.child.poll() is not None):
                self.status("stopped", "requested_graceful_stop")
                return 0
            code = exc.code if isinstance(exc, Refused) else ("preflight_" + type(exc).__name__)
            self.status(
                "blocked", code, detail=str(exc) if type(exc).__name__ in ("Unsafe", "BindingError") else None
            )
            # Do not kill a partial/unknown owner.  OnFailure alerts, and exit 78
            # suppresses retries.  Any survivor retains its authority lease/port.
            return EXIT_BLOCKED
        finally:
            if self.lock is not None:
                os.close(self.lock)
                self.lock = None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--policy", required=True)
    a = p.parse_args()
    try:
        controller = Controller(a.policy)
        signal.signal(signal.SIGTERM, controller.terminate_own_child)
        signal.signal(signal.SIGINT, controller.terminate_own_child)
        return controller.run()
    except Exception:
        try:
            atomic(
                private(a.policy).parent / "automatic-status.json",
                {
                    "schema": "automatic-dashboard-status/v1",
                    "phase": "blocked",
                    "reason": "policy_or_source_preflight",
                    "recorded_utc": datetime.now(timezone.utc).isoformat(),
                    "unit": "t3-dashboard-auto.service",
                    "operator_action": (
                        "Inspect the unit journal and private policy/source pins. "
                        "No reset or state restore."
                    ),
                    "alert": "OnFailure=t3-dashboard-auto-alert.service",
                },
            )
        except Exception:
            pass
        print(json.dumps({"phase": "blocked", "reason": "policy_or_source_preflight"}), flush=True)
        return EXIT_BLOCKED


if __name__ == "__main__":
    raise SystemExit(main())
