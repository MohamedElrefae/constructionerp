"""Out-of-process T3 supervisor (test-only synthetic transport).

Owns the MCP client, the per-job durable state and the credentials. The engine
talks to it over an authenticated Unix socket. In this build the supervisor is
started by tests with a synthetic token and a local MCP simulator; it is not a
production service and does not make the T3 backend selectable.

Protocol: 4-byte big-endian length + JSON. Requests:
  {"op": "health"|"dispatch"|"collect"|"cancel"|"state", "token": ..., "payload": {...}}
Responses: {"ok": true, "result": {...}} | {"ok": false, "error": {"code", "message"}}

Durability: state file written atomically; a job marked "launching" before the
MCP call is treated as uncertain on restart and never relaunched.
"""

import hashlib
import json
import os
import socket
import stat
import struct
import sys
import tempfile
import time
from pathlib import Path

MAX_FRAME = 1024 * 1024
MAX_BUILDER_BRIEF_CHARS = 80_000
ENGINE_T3_ROLES = frozenset({
    "architect", "reviewer", "verifier", "proposer", "ai-a1", "ai-a2", "ai-a3",
})


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _redact(text: str, token: str) -> str:
    out = str(text).replace(token, "<redacted>")
    return out.replace("Bearer ", "Bearer <redacted> ")


def _request_digest(job: dict) -> str:
    """Bind idempotency to all values used to select and launch a task."""
    request = {key: job.get(key) for key in (
        "job_id", "client_request_id", "model", "role", "brief",
        "expect_marker", "project_id", "timeout_ms", "spec")}
    wire = json.dumps(request, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(wire).hexdigest()


class SupervisorState:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.doc = {"jobs": {}, "started_utc": _now()}
        try:
            fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        except FileNotFoundError:
            fd = None
        except OSError:
            raise SystemExit("supervisor state cannot be opened safely; refusing to start") from None
        if fd is not None:
            try:
                meta = os.fstat(fd)
                if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.geteuid()
                        or meta.st_mode & 0o077 or meta.st_size > 16 * 1024 * 1024):
                    raise SystemExit("supervisor state ownership, permissions, or size invalid")
                with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as fh:
                    raw = fh.read(16 * 1024 * 1024 + 1)
                if len(raw) > 16 * 1024 * 1024:
                    raise SystemExit("supervisor state exceeds size limit")
                doc = json.loads(raw)
            except (ValueError, UnicodeDecodeError, OSError):
                raise SystemExit("supervisor state unreadable; refusing to start") from None
            finally:
                os.close(fd)
            if not isinstance(doc, dict) or not isinstance(doc.get("jobs"), dict):
                raise SystemExit("supervisor state has an invalid schema; refusing to start")
            for rec in doc["jobs"].values():
                if not isinstance(rec, dict) or "state" not in rec:
                    raise SystemExit("supervisor state record invalid; refusing to start")
            self.doc = doc

    def save(self) -> None:
        fd, name = tempfile.mkstemp(prefix=self.path.name + ".tmp.", dir=self.path.parent)
        tmp = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(self.doc, indent=1, sort_keys=True))
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
            # Persist the rename as well as the file before a provider launch.
            directory_fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass

    def get(self, job_id: str):
        return self.doc["jobs"].get(job_id)

    def put(self, job_id: str, record: dict) -> None:
        self.doc["jobs"][job_id] = record
        self.save()


class Supervisor:
    # The standalone supervisor is test-only. Builder dispatch stays disabled
    # unless an explicitly test-owned subclass enables its synthetic workflow.
    allow_builder_for_tests = False

    def __init__(self, *, socket_path: Path, state_path: Path, token: str,
                 base_url: str, mcp_token: str, model: str,
                 allowed_models, peer_uid=None, provider="opencode",
                 builder_enabled=False):
        self.socket_path = Path(socket_path)
        self.state = SupervisorState(Path(state_path))
        self.token = token
        self.base_url = base_url
        self.mcp_token = mcp_token
        self.model = model
        if provider not in ("opencode", "codex"):
            raise ValueError("unsupported T3 provider")
        self.provider = provider
        self.allowed_models = list(allowed_models)
        if not isinstance(builder_enabled, bool):
            raise ValueError("builder_enabled must be boolean")
        self.builder_enabled = builder_enabled
        self.uid = os.geteuid()
        self.peer_uid = int(peer_uid) if peer_uid is not None else self.uid
        self.started = _now()

    # -- MCP client (reuses the reviewed transport client) ----------------- #
    def _client(self):
        from t3_transport import HttpT3Client
        client = HttpT3Client(self.base_url, self.mcp_token, provider=self.provider)
        client.initialize()
        return client

    def _dispatch(self, job: dict) -> dict:
        job_id = job["job_id"]
        request_digest = _request_digest(job)
        rec = self.state.get(job_id)
        if rec is not None:
            if rec.get("client_request_id") != job.get("client_request_id"):
                return {"state": "refused", "error": "job_id reused with a divergent request id"}
            if not rec.get("request_digest"):
                return {"state": "uncertain", "task_id": rec.get("task_id"),
                        "error": "legacy job cannot verify retry contents; reconcile"}
            if rec["request_digest"] != request_digest:
                return {"state": "refused", "error": "job_id reused with divergent task contents"}
            # never relaunch: known task, in-flight marker, or terminal.
            # "launching" means the crash window: outcome unknown.
            state = "uncertain" if rec["state"] == "launching" else rec["state"]
            return {"state": state, "task_id": rec.get("task_id")}
        try:
            # MCP session setup sends no task. If it fails, the supervisor can
            # prove that no launch was attempted and need not park the job as
            # uncertain. Only delegate() follows the durable launch marker.
            client = self._client()
        except Exception as exc:
            return {"state": "prelaunch_failed", "error": _redact(
                f"T3 session unavailable: {type(exc).__name__}: {exc}", self.mcp_token)}
        rec = {"job_id": job_id, "client_request_id": job["client_request_id"],
               "request_digest": request_digest,
               "model": job["model"], "role": job["role"],
               "expect_marker": job.get("spec", {}).get("expect_marker") or job["expect_marker"],
               "state": "launching", "task_id": None,
               "history": [{"state": "launching", "utc": _now()}]}
        self.state.put(job_id, rec)          # durable BEFORE the MCP call
        try:
            spec = job.get("spec") or {}
            task = spec.get("task") or (f"[engine job {job_id}] {job['brief']} "
                                        f"The LAST line must contain: {job['expect_marker']}")
            out = client.delegate(
                task=task,
                model=job["model"], role=job["role"],
                client_request_id=job["client_request_id"],
                timeout_ms=int(job.get("timeout_ms", 120000)),
                expect_marker=spec.get("expect_marker") or job["expect_marker"],
                project_id=job.get("project_id"),
            )
            task_id = out.get("taskId")
            if not task_id:
                raise RuntimeError("delegate returned no taskId")
        except Exception as exc:             # outcome unknown: never re-send
            rec.update(state="uncertain", error=_redact(f"{type(exc).__name__}: {exc}", self.mcp_token))
            rec["history"].append({"state": "uncertain", "utc": _now()})
            self.state.put(job_id, rec)
            return {"state": "uncertain", "error": rec["error"]}
        rec.update(state="dispatched", task_id=task_id)
        rec["history"].append({"state": "dispatched", "utc": _now()})
        self.state.put(job_id, rec)
        return {"state": "dispatched", "task_id": task_id}

    def _collect(self, job_id: str) -> dict:
        rec = self.state.get(job_id)
        if rec is None:
            return {"state": "refused", "error": "unknown job_id"}
        if rec["state"] in ("completed", "failed", "uncertain", "cancelled"):
            return {"state": rec["state"], "receipt": rec.get("receipt")}
        if not rec.get("task_id"):
            return {"state": "uncertain", "error": "no task identity; reconcile"}
        try:
            outcome = self._client().status(rec["task_id"])
        except Exception as exc:
            return {"state": "uncertain", "error": _redact(f"{type(exc).__name__}: {exc}", self.mcp_token)}
        if outcome.get("hasPendingQuestion") or outcome.get("pendingApproval"):
            if rec.get("state") != "waiting":
                rec.update(state="waiting", wait_reason="pending_owner_action")
                rec["history"].append({"state": "waiting", "utc": _now()})
                self.state.put(job_id, rec)
            return {"state": "waiting", "reason": "pending_owner_action"}
        status = outcome.get("status")
        if status in ("preparing", "queued", "starting", "running", "waiting", "idle"):
            if rec.get("state") == "waiting":
                rec.update(state="dispatched")
                rec.pop("wait_reason", None)
                rec["history"].append({"state": "dispatched", "utc": _now()})
                self.state.put(job_id, rec)
            return {"state": "dispatched"}
        marker = rec.get("expect_marker") or ""
        summary = outcome.get("summary") or ""
        executed = outcome.get("executedModel") or outcome.get("model")
        if status != "completed":
            rec.update(state="failed", error=f"task status {status!r}")
            rec.pop("wait_reason", None)
            self.state.put(job_id, rec)
            return {"state": "failed", "error": rec["error"]}
        if executed != rec.get("model"):
            rec.update(state="failed", error="model pin mismatch")
            rec.pop("wait_reason", None)
            self.state.put(job_id, rec)
            return {"state": "failed", "error": rec["error"]}
        if outcome.get("model") and outcome["model"] != rec.get("model"):
            rec.update(state="failed", error="configured model pin mismatch")
            rec.pop("wait_reason", None)
            self.state.put(job_id, rec)
            return {"state": "failed", "error": rec["error"]}
        if not marker or marker not in summary:
            rec.update(state="failed", error="result marker missing")
            rec.pop("wait_reason", None)
            self.state.put(job_id, rec)
            return {"state": "failed", "error": rec["error"]}
        limit = 50_000 if rec.get("role") == "builder" else 8_000
        redacted_summary = _redact(summary, self.mcp_token)
        if len(summary) > limit or (rec.get("role") == "builder" and redacted_summary != summary):
            # Never silently truncate or rewrite source bytes in an artifact.
            rec.update(state="failed", error="result exceeds bounds or requires secret redaction")
            rec.pop("wait_reason", None)
            self.state.put(job_id, rec)
            return {"state": "failed", "error": rec["error"]}
        receipt = {"job_id": job_id, "task_id": rec["task_id"], "state": "completed",
                   "summary": redacted_summary,
                   "configured_model": outcome.get("model"),
                   "executed_model": outcome.get("executedModel"),
                   "model_evidence": "executed" if outcome.get("executedModel") else "configured_only",
                   "validated_utc": _now()}
        rec.update(state="completed", receipt=receipt)
        rec.pop("wait_reason", None)
        rec["history"].append({"state": "completed", "utc": _now()})
        self.state.put(job_id, rec)
        return {"state": "completed", "receipt": receipt}

    def handle(self, request) -> dict:
        if not isinstance(request, dict):
            return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "request must be an object"}}
        import hmac as _hmac
        candidate = request.get("token")
        if (not isinstance(self.token, str) or not self.token.isascii() or not self.token
                or not isinstance(candidate, str) or not candidate.isascii()
                or not _hmac.compare_digest(candidate, self.token)):
            return {"ok": False, "error": {"code": "UNAUTHORIZED", "message": "peer token mismatch"}}
        op = request.get("op")
        payload = request.get("payload") or {}
        if not isinstance(payload, dict):
            return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "payload must be an object"}}
        if op == "health":
            return {"ok": True, "result": {"pid": os.getpid(), "uid": self.uid,
                                           "netns_inode": os.stat("/proc/self/ns/net").st_ino,
                                           "started_utc": self.started}}
        if op == "cancel":
            job_id = payload.get("job_id", "")
            if not isinstance(job_id, str) or not job_id:
                return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "job_id must be a string"}}
            rec = self.state.get(job_id)
            if rec is None:
                return {"ok": False, "error": {"code": "REFUSED", "message": "unknown job_id"}}
            if rec.get("state") in ("completed", "failed", "cancelled"):
                return {"ok": True, "result": {"state": rec["state"], "cancelled": False,
                                               "error": "job is already terminal"}}
            if not rec.get("task_id"):
                return {"ok": True, "result": {"state": rec["state"], "cancelled": False}}
            try:
                outcome = self._client().cancel(rec["task_id"], "engine cancel")
            except Exception as exc:
                return {"ok": True, "result": {"state": rec["state"], "cancelled": False,
                                               "error": _redact(f"{type(exc).__name__}: {exc}", self.mcp_token)}}
            if (not isinstance(outcome, dict)
                    or outcome.get("threadId") != rec["task_id"]
                    or outcome.get("status") != "cancelled"):
                return {"ok": True, "result": {"state": rec["state"], "cancelled": False,
                                               "error": "T3 did not confirm cancellation"}}
            rec.update(state="cancelled")
            self.state.put(job_id, rec)
            return {"ok": True, "result": {"state": "cancelled", "cancelled": True}}
        if op == "state":
            job_id = payload.get("job_id", "")
            if not isinstance(job_id, str) or not job_id:
                return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "job_id must be a string"}}
            rec = self.state.get(job_id)
            return {"ok": True, "result": {"record": rec}}
        if op == "dispatch":
            job = payload.get("job") or {}
            if not isinstance(job, dict):
                return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "job must be an object"}}
            missing = [k for k in ("job_id", "client_request_id", "model", "brief", "expect_marker", "role") if not job.get(k)]
            if missing:
                return {"ok": False, "error": {"code": "BAD_REQUEST", "message": f"missing {missing}"}}
            if any(not isinstance(job[k], str) for k in
                   ("job_id", "client_request_id", "model", "brief", "expect_marker", "role")):
                return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "job fields must be strings"}}
            if (job.get("project_id") is not None and not isinstance(job["project_id"], str)):
                return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "project_id must be a string"}}
            if (job.get("timeout_ms") is not None and
                    (isinstance(job["timeout_ms"], bool) or not isinstance(job["timeout_ms"], int)
                     or not 1 <= job["timeout_ms"] <= 3600000)):
                return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "invalid timeout_ms"}}
            if (job.get("role") == "builder"
                    and len(job.get("brief", "")) > MAX_BUILDER_BRIEF_CHARS):
                return {"ok": False, "error": {"code": "REFUSED",
                                               "message": "builder source packet exceeds brief size bound"}}
            if (job.get("idempotency_key") is not None and not isinstance(job["idempotency_key"], str)):
                return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "idempotency_key must be a string"}}
            if job["role"] not in ENGINE_T3_ROLES | {"builder"}:
                return {"ok": False, "error": {"code": "REFUSED", "message": "unsupported Engine role"}}
            if (job["role"] == "builder" and not self.builder_enabled
                    and getattr(type(self), "allow_builder_for_tests", False) is not True):
                return {"ok": False, "error": {"code": "REFUSED", "message": "builder dispatch is disabled"}}
            if job["model"] not in self.allowed_models:
                return {"ok": False, "error": {"code": "REFUSED", "message": "model not allowed"}}
            from t3_transport import TransportRefusal, build_task_spec
            try:
                spec = build_task_spec(
                    {"job_id": job["job_id"],
                     "idempotency_key": job.get("idempotency_key") or job["client_request_id"],
                     "model": job["model"], "brief": job["brief"],
                     "expect_marker": job["expect_marker"], "access": "read-only",
                     "role": job["role"]},
                    allowed_models=self.allowed_models)
            except TransportRefusal as exc:
                return {"ok": False, "error": {"code": "REFUSED",
                                               "message": _redact(str(exc), self.mcp_token)}}
            return {"ok": True, "result": self._dispatch({**job, "spec": spec})}
        if op == "collect":
            job_id = payload.get("job_id", "")
            if not isinstance(job_id, str) or not job_id:
                return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "job_id must be a string"}}
            return {"ok": True, "result": self._collect(job_id)}
        return {"ok": False, "error": {"code": "UNKNOWN_OP", "message": str(op)}}


def _recv_exact(conn, n):
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def serve(supervisor: Supervisor):
    path = supervisor.socket_path
    if not path.parent.exists():
        path.parent.mkdir(parents=True, mode=0o700)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    lock_path = path.with_name(path.name + ".lock")
    lock_fh = open(lock_path, "a+")
    import fcntl
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit("another supervisor owns this socket")
    try:
        if path.exists() or path.is_symlink():
            path.unlink()
    except OSError:
        pass
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    os.chmod(path, 0o600)
    server.listen(8)
    pidfile = path.with_name(path.name + ".pid")
    pidfile.write_text(str(os.getpid()))
    os.chmod(pidfile, 0o600)
    print(json.dumps({"ready": True, "socket": str(path), "pid": os.getpid()}), flush=True)
    while True:
        conn, _ = server.accept()
        conn.settimeout(30.0)
        try:
            creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
            pid, uid, gid = struct.unpack("3i", creds)
            if uid != supervisor.peer_uid:
                conn.sendall(_frame({"ok": False, "error": {"code": "PEER_REJECTED",
                                                           "message": "peer uid mismatch"}}))
                try:
                    conn.shutdown(socket.SHUT_WR)
                    conn.settimeout(0.5)
                    while conn.recv(65536):
                        pass
                except OSError:
                    pass
                continue
            header = _recv_exact(conn, 4)
            if header is None:
                continue
            (length,) = struct.unpack(">I", header)
            if length <= 0:
                conn.sendall(_frame({"ok": False, "error": {"code": "BAD_FRAME",
                                                           "message": str(length)}}))
                continue
            if length > MAX_FRAME:
                conn.sendall(_frame({"ok": False, "error": {"code": "FRAME_TOO_LARGE",
                                                           "message": str(length)}}))
                continue
            body = _recv_exact(conn, length)
            if body is None:
                continue
            try:
                request = json.loads(body.decode())
            except ValueError:
                conn.sendall(_frame({"ok": False, "error": {"code": "BAD_JSON",
                                                           "message": "invalid json"}}))
                continue
            response = supervisor.handle(request)
            framed = _frame(response)
            if len(framed) - 4 > MAX_FRAME:
                framed = _frame({"ok": False, "error": {"code": "RESPONSE_TOO_LARGE",
                                                        "message": "response bound"}})
            conn.sendall(framed)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            conn.close()


def _frame(payload: dict) -> bytes:
    body = json.dumps(payload).encode()
    return struct.pack(">I", len(body)) + body


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--mcp-token-file", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", choices=("opencode", "codex"), default="opencode")
    parser.add_argument("--allowed-model", action="append", default=[])
    parser.add_argument("--peer-uid", type=int, default=None)
    args = parser.parse_args()
    token = Path(args.token_file).read_text().strip()
    mcp_token = Path(args.mcp_token_file).read_text().strip()
    sup = Supervisor(socket_path=Path(args.socket), state_path=Path(args.state),
                     token=token, base_url=args.base_url, mcp_token=mcp_token,
                     model=args.model, allowed_models=args.allowed_model or [args.model],
                     peer_uid=args.peer_uid, provider=args.provider)
    serve(sup)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
