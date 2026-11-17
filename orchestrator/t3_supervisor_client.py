"""Engine-side client for the out-of-process T3 supervisor (test-only path).

The client speaks the length-prefixed JSON protocol, verifies the supervisor's
health (pid + netns identity) before dispatch, and maps transport failures to
fail-closed errors: EOF/timeout means "outcome unknown" and the caller must not
retry. Secrets are never included in errors.
"""

import json
import math
import os
import socket
import stat
import struct
import time
from pathlib import Path

MAX_FRAME = 1024 * 1024


class SupervisorUnavailable(RuntimeError):
    """Socket/peer failure: outcome unknown, never retry blindly."""


class SupervisorRefusal(RuntimeError):
    """Supervisor refused the operation before any T3 contact."""


def load_private_supervisor_token(path):
    """Read a narrowly permissioned token file for the opt-in dashboard route.

    This checks the file descriptor actually opened (including no-follow), so
    replacing the path with a symlink between a path check and read cannot
    redirect the credential read.  It is a local file-hygiene check only: a
    same-UID process can still access the token and this does not authenticate
    a supervisor process by itself.
    """
    token_path = Path(path)
    if not token_path.is_absolute():
        raise SupervisorRefusal("supervisor token path must be absolute")
    if not hasattr(os, "O_NOFOLLOW"):
        raise SupervisorRefusal("platform cannot open supervisor token without following symlinks")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    try:
        fd = os.open(str(token_path), flags)
    except OSError as exc:
        raise SupervisorRefusal(
            f"supervisor token file cannot be opened: {type(exc).__name__}") from None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise SupervisorRefusal("supervisor token must be a regular file")
        if st.st_uid != os.geteuid():
            raise SupervisorRefusal("supervisor token file owner mismatch")
        if st.st_mode & 0o077:
            raise SupervisorRefusal("supervisor token file permissions must exclude group and others")
        with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as fh:
            token = fh.read(4097).strip()
        if not token:
            raise SupervisorRefusal("supervisor token file is empty")
        if len(token) > 4096:
            raise SupervisorRefusal("supervisor token exceeds size bound")
        if not token.isascii():
            raise SupervisorRefusal("supervisor token must be ASCII")
        return token
    except UnicodeDecodeError:
        raise SupervisorRefusal("supervisor token file is not UTF-8 text") from None
    finally:
        os.close(fd)


def _recv_exact(conn, n):
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise SupervisorUnavailable("supervisor closed the connection")
        buf += chunk
    return buf


class SupervisorClient:
    def __init__(self, socket_path, token, *, timeout=60.0, expected_uid=None,
                 peer_verifier=None):
        self.socket_path = str(socket_path)
        self.token = token
        self.timeout = float(timeout)
        if peer_verifier is not None and not callable(peer_verifier):
            raise ValueError("peer_verifier must be callable")
        self.peer_verifier = peer_verifier
        self.expected_uid = expected_uid if expected_uid is not None else os.geteuid()
        if (isinstance(self.expected_uid, bool)
                or not isinstance(self.expected_uid, int)
                or self.expected_uid < 0):
            raise ValueError("expected_uid must be a nonnegative integer")

    def call(self, op, payload=None):
        body = json.dumps({"op": op, "token": self.token, "payload": payload or {}}).encode()
        if len(body) > MAX_FRAME:
            raise SupervisorRefusal("request exceeds frame bound")
        frame = struct.pack(">I", len(body)) + body
        try:
            conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            conn.settimeout(self.timeout)
            conn.connect(self.socket_path)
        except OSError as exc:
            raise SupervisorUnavailable(f"supervisor unreachable: {type(exc).__name__}") from None
        try:
            # Verify the peer BEFORE disclosing the token.
            creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
            peer_pid, uid, _gid = struct.unpack("3i", creds)
            if uid != self.expected_uid:
                raise SupervisorRefusal("supervisor peer uid mismatch")
            if self.peer_verifier is not None:
                # A deployment-specific verifier can inspect this very socket
                # before the protocol token or any task data is disclosed.
                verdict = self.peer_verifier(conn)
                if not isinstance(verdict, dict) or verdict.get("identity_observed") is not True:
                    raise SupervisorRefusal("supervisor peer verification did not confirm identity")
            conn.sendall(frame)
            header = _recv_exact(conn, 4)
            (length,) = struct.unpack(">I", header)
            if length <= 0 or length > MAX_FRAME:
                raise SupervisorUnavailable("response frame out of bounds")
            try:
                response = json.loads(_recv_exact(conn, length).decode())
            except (ValueError, UnicodeDecodeError):
                raise SupervisorUnavailable("malformed supervisor response") from None
        except OSError as exc:
            raise SupervisorUnavailable(f"supervisor I/O failure: {type(exc).__name__}") from None
        finally:
            conn.close()
        if not isinstance(response, dict):
            raise SupervisorUnavailable("malformed supervisor response")
        if not response.get("ok"):
            err = response.get("error") or {}
            code = err.get("code", "ERROR")
            message = str(err.get("message", ""))[:300]
            if code in ("UNAUTHORIZED", "PEER_REJECTED", "REFUSED", "BAD_REQUEST"):
                raise SupervisorRefusal(f"{code}: {message}")
            raise SupervisorUnavailable(f"{code}: {message}")
        result = response.get("result") or {}
        if op == "health":
            if (not isinstance(result, dict) or peer_pid <= 0
                    or type(result.get("pid")) is not int or result["pid"] != peer_pid
                    or type(result.get("uid")) is not int or result["uid"] != uid):
                raise SupervisorRefusal("supervisor health identity does not match socket peer")
        return result


def cancel(client, job_id):
    """Cancel a supervised task; returns the supervisor result."""
    return client.call("cancel", {"job_id": job_id})


class SupervisorLauncher:
    """Engine launcher slot backed by the supervisor socket (test-only)."""

    allow_builder_for_tests = False
    builder_enabled = False

    def __init__(self, root, socket_path, token, *, allowed_models, timeout=10.0,
                 min_poll_interval_s=0.0, expected_uid=None):
        self.root = str(Path(root).resolve())
        self.client = SupervisorClient(socket_path, token, timeout=timeout,
                                       expected_uid=expected_uid)
        self.allowed_models = list(allowed_models)
        self.min_poll_interval_s = float(min_poll_interval_s)
        self.calls = []

    def preflight(self, job):
        health = self.client.call("health")
        pid = health.get("pid")
        if not pid:
            raise SupervisorRefusal("supervisor health check failed")
        # Kernel-observed identity: the supervisor's /proc netns must match ours.
        try:
            sup_inode = os.stat(f"/proc/{pid}/ns/net").st_ino
            self_inode = os.stat("/proc/self/ns/net").st_ino
        except OSError as exc:
            raise SupervisorUnavailable(f"supervisor process not observable: {exc}") from None
        if sup_inode != self_inode:
            raise SupervisorRefusal("supervisor is not in the engine's network namespace")
        self._validate_job(job)

    def _validate_job(self, job):
        spec = job.get("spec") or {}
        role = job.get("role") or spec.get("role")
        if role not in {"architect", "reviewer", "builder", "verifier", "proposer", "ai-a1", "ai-a2", "ai-a3"}:
            raise SupervisorRefusal("T3 supervisor does not support this Engine role")
        if (role == "builder" and not self.builder_enabled
                and getattr(type(self), "allow_builder_for_tests", None) is not True):
            raise SupervisorRefusal("T3 supervisor transport is read-only; builder dispatch is refused")
        model = spec.get("model")
        if model not in self.allowed_models:
            raise SupervisorRefusal(f"model {model!r} not allowed by the supervisor launcher")
        timeout = spec.get("hard_timeout", 3600)
        if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout) or not 0 < timeout <= 3600
                or int(timeout * 1000) < 1):
            raise SupervisorRefusal("T3 hard timeout must be between 1 millisecond and 1 hour")
        # Match the supervisor's task validation before Engine persists a
        # launch intent; an invalid brief should never strand a prepared job.
        from t3_transport import TransportRefusal, build_task_spec
        job_id = job.get("job_id")
        if not isinstance(job_id, str):
            raise SupervisorRefusal("T3 job id must be a string")
        try:
            build_task_spec({
                "job_id": job_id,
                "idempotency_key": "wp1-engine-job-" + job_id.replace("job-", ""),
                "model": model,
                "brief": spec.get("prompt"),
                "expect_marker": f"ENGINE-T3-RESULT {job_id}",
                "access": "read-only", "role": role,
            }, allowed_models=self.allowed_models)
        except (TransportRefusal, TypeError, ValueError) as exc:
            raise SupervisorRefusal(f"T3 task preflight refused: {exc}") from None

    def __call__(self, job):
        spec = job["spec"]
        self.calls.append(job["job_id"])
        result = self.client.call("dispatch", {"job": {
            "job_id": job["job_id"],
            "role": job.get("role") or spec.get("role"),
            "client_request_id": "wp1-engine-job-" + job["job_id"].replace("job-", ""),
            "model": spec["model"],
            "brief": spec["prompt"],
            "expect_marker": f"ENGINE-T3-RESULT {job['job_id']}",
            "timeout_ms": int(spec.get("hard_timeout", 3600) * 1000),
        }})
        if result.get("state") == "prelaunch_failed":
            from core import ProvenNoLaunch
            raise ProvenNoLaunch(result.get("error") or "T3 session setup failed before launch")
        if result.get("state") in ("refused",):
            raise SupervisorRefusal(result.get("error") or "dispatch refused")
        # dispatched/uncertain/terminal: leave the job RUNNING; poll resolves.

    def _write(self, job, text, exit_code, started_utc, timeout=False, model_evidence=None,
               supervisor_receipt=None):
        runtime = Path(job["runtime"])
        runtime.mkdir(parents=True, exist_ok=True)
        (runtime / "stdout.jsonl").write_text(text)
        observation = {"job_id": job["job_id"], "phase": "TERMINAL",
                       "exit_code": int(exit_code),
                       "started_utc": started_utc,
                       "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if timeout:
            observation["timeout"] = True
        if model_evidence is not None:
            observation["model_evidence"] = model_evidence
        if supervisor_receipt is not None:
            # Keep the independently returned receipt intact for Engine intake.
            # Bound it before persistence; never reconstruct it from model text.
            if not isinstance(supervisor_receipt, dict) or len(json.dumps(supervisor_receipt).encode("utf-8")) > 2_000_000:
                raise SupervisorRefusal("supervisor receipt exceeds observation bounds")
            observation["supervisor_receipt"] = supervisor_receipt
        (runtime / "terminal.json").write_text(json.dumps(observation))

    def _recorded_start(self, record):
        from datetime import datetime
        history = record.get("history")
        if not isinstance(history, list):
            raise SupervisorRefusal("supervisor has no recorded launch time")
        for entry in history:
            if isinstance(entry, dict) and entry.get("state") == "launching":
                started = entry.get("utc")
                try:
                    if not isinstance(started, str) or not started.endswith("Z"):
                        raise ValueError
                    datetime.fromisoformat(started.replace("Z", "+00:00"))
                except ValueError:
                    break
                return started
        raise SupervisorRefusal("supervisor has no valid recorded launch time")

    def poll(self, job):
        try:
            result = self.client.call("collect", {"job_id": job["job_id"]})
        except SupervisorUnavailable as exc:
            from core import WorkflowError
            raise WorkflowError(f"RECONCILIATION_REQUIRED: {exc}") from None
        state = result.get("state")
        if state == "completed":
            receipt = result.get("receipt") or {}
            task_id = receipt.get("task_id")
            if receipt.get("job_id") != job.get("job_id") or not task_id:
                raise SupervisorRefusal("supervisor receipt does not match prepared job")
            evidence = receipt.get("model_evidence")
            if evidence == "executed":
                selected_model = receipt.get("executed_model")
            elif evidence == "configured_only" and receipt.get("executed_model") is None:
                selected_model = receipt.get("configured_model")
            else:
                raise SupervisorRefusal("supervisor receipt model evidence is missing or inconsistent")
            if selected_model != job.get("spec", {}).get("model"):
                raise SupervisorRefusal("supervisor receipt model does not match prepared job")
            record = self.client.call("state", {"job_id": job["job_id"]}).get("record") or {}
            if (record.get("job_id") != job.get("job_id")
                    or record.get("task_id") != task_id
                    or record.get("model") != selected_model):
                raise SupervisorRefusal("supervisor task correlation does not match receipt")
            from t3_result import decode_t3_result, T3ResultError
            try:
                session, body, wire, _events = decode_t3_result(
                    assistant_text=receipt.get("summary"), job=job,
                    task_id=task_id, executed_model=selected_model)
            except T3ResultError as exc:
                raise SupervisorRefusal(f"invalid T3 result: {exc}") from None
            body["session_id"] = session
            text = f"ENGINE-T3-RESULT {job['job_id']}\n{json.dumps(wire)}"
            self._write(job, text, 0, self._recorded_start(record), model_evidence=evidence,
                        supervisor_receipt=receipt)
        elif state == "failed":
            record = self.client.call("state", {"job_id": job["job_id"]}).get("record") or {}
            if record.get("job_id") != job.get("job_id"):
                raise SupervisorRefusal("supervisor state does not match failed job")
            self._write(job, f"T3 task failed: {result.get('error', '')}\n", 1,
                        self._recorded_start(record))
        elif state == "uncertain":
            # No terminal.json: the engine keeps the job RUNNING until the
            # supervisor can prove an outcome; never re-send here.
            return
        elif state == "waiting":
            # A T3 human question/approval is not a completed assistant
            # result. Keep the job live so a later collect can observe the
            # owner's response; never write terminal.json for this state.
            return
        elif state == "refused":
            raise SupervisorRefusal(result.get("error") or "collect refused")

    def receipt_for(self, job):
        """Re-fetch and validate the supervisor receipt at artifact intake time."""
        result = self.client.call("collect", {"job_id": job["job_id"]})
        if result.get("state") != "completed":
            raise SupervisorRefusal("supervisor no longer reports a completed builder result")
        receipt = result.get("receipt")
        if not isinstance(receipt, dict):
            raise SupervisorRefusal("completed supervisor result has no receipt")
        task_id = receipt.get("task_id")
        evidence = receipt.get("model_evidence")
        configured = receipt.get("configured_model")
        executed = receipt.get("executed_model")
        if (receipt.get("job_id") != job.get("job_id") or not task_id
                or configured != job.get("spec", {}).get("model")
                or (evidence == "executed" and executed != configured)
                or (evidence == "configured_only" and executed is not None)
                or evidence not in ("executed", "configured_only")):
            raise SupervisorRefusal("supervisor receipt identity or model evidence is inconsistent")
        record = self.client.call("state", {"job_id": job["job_id"]}).get("record") or {}
        selected = executed if evidence == "executed" else configured
        if (record.get("job_id") != job.get("job_id") or record.get("task_id") != task_id
                or record.get("model") != selected):
            raise SupervisorRefusal("supervisor receipt no longer matches durable task state")
        from t3_result import decode_t3_result, T3ResultError
        try:
            decode_t3_result(assistant_text=receipt.get("summary"), job=job,
                             task_id=task_id, executed_model=selected)
        except T3ResultError as exc:
            raise SupervisorRefusal(f"invalid T3 result receipt: {exc}") from None
        return receipt

    def parse(self, job, raw):
        from t3_dispatch import _extract_wire
        wire = _extract_wire(raw, allow_builder_bundle=job.get("role") == "builder")
        body = json.loads(wire["result_json"])
        rec = self.client.call("state", {"job_id": job["job_id"]}).get("record") or {}
        task_id = rec.get("task_id")
        if not task_id:
            raise SupervisorRefusal("supervisor state has no correlated T3 thread")
        return task_id, body, wire, []


class ManagedSupervisorLauncher(SupervisorLauncher):
    """Candidate for an externally managed supervisor, not wired to production.

    The caller must provide an independent verifier for every connected socket.
    The verifier must establish process and service confinement; the callable
    itself is not a security boundary. The health response only identifies the
    protocol and is not evidence that systemd or the network enforces isolation.
    """

    def __init__(self, root, socket_path, token, *, allowed_models,
                 expected_uid, peer_verifier, builder_enabled=False,
                 timeout=10.0, min_poll_interval_s=0.0):
        if peer_verifier is None or not callable(peer_verifier):
            raise SupervisorRefusal("managed supervisor requires an independent peer verifier")
        if isinstance(expected_uid, bool) or not isinstance(expected_uid, int) or expected_uid <= 0:
            raise SupervisorRefusal("managed supervisor requires an explicit non-root UID")
        if expected_uid == os.geteuid():
            raise SupervisorRefusal("managed supervisor UID must differ from dashboard UID")
        if not isinstance(builder_enabled, bool):
            raise SupervisorRefusal("managed builder authorization must be boolean")
        super().__init__(root, socket_path, token, allowed_models=allowed_models,
                         timeout=timeout, min_poll_interval_s=min_poll_interval_s,
                         expected_uid=expected_uid)
        self.client.peer_verifier = peer_verifier
        self.builder_enabled = builder_enabled

    def preflight(self, job):
        health = self.client.call("health")
        if (health.get("ready") is not True or health.get("read_only") is not False
                or health.get("protocol") != "experimental-managed-supervisor/v1"
                or health.get("builder_enabled") is not self.builder_enabled):
            raise SupervisorRefusal("managed supervisor dispatch health is not ready")
        self._validate_job(job)
