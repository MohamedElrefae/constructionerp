"""Out-of-process supervisor + engine socket client (test-only).

All processes run inside the harness netns; the simulator, the supervisor and
the synthetic child are separate OS processes. No real T3/provider access.
"""

import json
import os
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

ORCH = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ORCH))
sys.path.insert(0, str(TESTS))

from t3_supervisor_client import (  # noqa: E402
    SupervisorClient,
    SupervisorLauncher,
    SupervisorRefusal,
    SupervisorUnavailable,
)


class SyntheticWorkflowLauncher(SupervisorLauncher):
    allow_builder_for_tests = True

MODEL = "opencode/deepseek-v4.1-flash-free"
BASE_FIXTURE = Path(os.environ.get("T3_SEAM_BASE_FIXTURE", "/opt/base-fixture"))
OLD_ROOT = os.environ.get("T3_SEAM_OLD_ROOT", "/var/tmp/guard-case-base-20261115")


def _wait_for(predicate, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="t3-sup-")
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.token = "synthetic-peer-token-0123456789"
        self.mcp_token = "synthetic-mcp-token-0123456789"
        (self.dir / "peer.token").write_text(self.token)
        (self.dir / "mcp.token").write_text(self.mcp_token)
        os.chmod(self.dir / "peer.token", 0o600)
        os.chmod(self.dir / "mcp.token", 0o600)
        self.events = self.dir / "launches.jsonl"
        self.procs = []
        self.sim = None
        self.sup = None
        self.url = None

    def tearDown(self):
        for proc in reversed(self.procs):
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    def _start_sim(self, fail=None, legacy_marker_mode=True):
        self.sim = subprocess.Popen(
            [sys.executable, str(TESTS / "_mcp_sim_server.py"),
             "--token", self.mcp_token, "--events", str(self.events)] +
            (["--fail", fail] if fail else []) +
            (["--legacy-marker-mode"] if legacy_marker_mode else []),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(ORCH),
        )
        self.procs.append(self.sim)
        line = self.sim.stdout.readline()
        self.assertTrue(line, "simulator did not start")
        self.url = json.loads(line)["url"]

    def _start_sup(self, state_name="state.json", peer_uid=None, socket_subdir=None, managed=False):
        self.sock_path = self.dir / (socket_subdir or "") / "sup.sock"
        if managed:
            os.chmod(self.dir, 0o2750)
        self.sup = subprocess.Popen(
            [sys.executable, str(TESTS / ("_synthetic_managed_supervisor_server.py" if managed else "_synthetic_supervisor_server.py")),
             "--socket", str(self.sock_path),
             "--state", str(self.dir / state_name),
             "--token-file", str(self.dir / "peer.token"),
             "--base-url", self.url,
             "--mcp-token-file", str(self.dir / "mcp.token"),
             "--model", MODEL, "--allowed-model", MODEL] +
            (["--peer-uid", str(peer_uid)] if peer_uid is not None else []),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(ORCH),
        )
        self.procs.append(self.sup)
        self.assertTrue(_wait_for(lambda: self.sock_path.exists()), "socket not created")
        line = self.sup.stdout.readline()
        self.assertTrue(line and json.loads(line).get("ready"), "supervisor did not start")

    def _client(self, token=None):
        return SupervisorClient(self.sock_path, token or self.token)

    def _launch_count(self, title_contains=None):
        if not self.events.exists():
            return 0
        lines = [json.loads(l) for l in self.events.read_text().splitlines() if l.strip()]
        if title_contains is not None:
            return len([l for l in lines if title_contains in (l.get("title") or "")])
        return len(lines)

    def _job(self, job_id="job-" + "a" * 24):
        return {"job_id": job_id, "client_request_id": "wp1-engine-job-" + "b" * 32,
                "model": MODEL, "brief": "Compute 6 * 7.", "role": "reviewer",
                "expect_marker": f"ENGINE-T3-RESULT {job_id}"}

    # ------------------------------------------------------------------ #
    def test_socket_mode_and_peer_auth(self):
        self._start_sim()
        self._start_sup()
        mode = (self.dir / "sup.sock").stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)
        with self.assertRaises(SupervisorRefusal) as ctx:
            self._client(token="wrong-token").call("health")
        self.assertIn("UNAUTHORIZED", str(ctx.exception))

    def test_framing_bounds_and_bad_json(self):
        self._start_sim()
        self._start_sup()

        def raw(payload_bytes):
            conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            conn.connect(str(self.dir / "sup.sock"))
            conn.sendall(payload_bytes)
            def recv_exact(n):
                buf = b""
                while len(buf) < n:
                    chunk = conn.recv(n - len(buf))
                    if not chunk:
                        raise AssertionError("short read")
                    buf += chunk
                return buf

            (length,) = struct.unpack(">I", recv_exact(4))
            body = recv_exact(length)
            conn.close()
            return json.loads(body)

        big = struct.pack(">I", 2 * 1024 * 1024) + b"{}"
        self.assertEqual(raw(big)["error"]["code"], "FRAME_TOO_LARGE")
        bad = json.dumps({"op": "health", "token": self.token}).encode()[:-2]
        self.assertEqual(raw(struct.pack(">I", len(bad)) + bad)["error"]["code"], "BAD_JSON")

    def test_dispatch_collect_no_duplicate(self):
        self._start_sim()
        self._start_sup()
        client = self._client()
        first = client.call("dispatch", {"job": self._job()})
        self.assertEqual(first["state"], "dispatched")
        second = client.call("dispatch", {"job": self._job()})
        self.assertEqual(second["task_id"], first["task_id"])
        self.assertEqual(self._launch_count("engine job " + self._job()["job_id"]), 1, "duplicate launch")
        collected = client.call("collect", {"job_id": self._job()["job_id"]})
        self.assertEqual(collected["state"], "completed")
        self.assertIn("ENGINE-T3-RESULT", collected["receipt"]["summary"])

    def test_restart_never_relaunches(self):
        self._start_sim()
        self._start_sup()
        first = self._client().call("dispatch", {"job": self._job()})
        self.sup.terminate()
        self.sup.wait(timeout=5)
        self._start_sup(state_name="state.json")
        second = self._client().call("dispatch", {"job": self._job()})
        self.assertEqual(second["task_id"], first["task_id"])
        self.assertEqual(self._launch_count("engine job " + self._job()["job_id"]), 1)

    def test_changed_retry_is_refused_without_relaunch(self):
        self._start_sim()
        self._start_sup()
        client = self._client()
        first = client.call("dispatch", {"job": self._job()})
        self.assertEqual(first["state"], "dispatched")
        changed = dict(self._job(), brief="Compute 7 * 7.")
        second = client.call("dispatch", {"job": changed})
        self.assertEqual(second["state"], "refused")
        self.assertIn("divergent", second["error"])
        self.assertEqual(self._launch_count("engine job " + self._job()["job_id"]), 1)

    def test_malformed_dispatch_does_not_stop_supervisor(self):
        self._start_sim()
        self._start_sup()
        client = self._client()
        for bad in (["not-an-object"], dict(self._job(), role=[]),
                    dict(self._job(), timeout_ms="invalid")):
            with self.subTest(job=bad):
                with self.assertRaises(SupervisorRefusal):
                    client.call("dispatch", {"job": bad})
        self.assertTrue(client.call("health")["pid"])

    def test_launcher_preflight_rejects_invalid_job_before_launch(self):
        self._start_sim()
        self._start_sup()
        launcher = SupervisorLauncher(self.dir, self.sock_path, self.token, allowed_models=[MODEL])
        job = {"job_id": "job-" + "a" * 24, "role": "reviewer",
               "spec": {"model": MODEL, "prompt": "Review this synthetic text.",
                        "hard_timeout": 3601}}
        with self.assertRaisesRegex(SupervisorRefusal, "timeout"):
            launcher.preflight(job)
        job["spec"]["hard_timeout"] = 60
        job["spec"]["prompt"] = "A synthetic password appears in this task."
        with self.assertRaisesRegex(SupervisorRefusal, "preflight refused"):
            launcher.preflight(job)
        self.assertEqual(self._launch_count(), 0)

    def test_lost_reply_is_uncertain_and_never_resent(self):
        self._start_sim(fail="lost_reply")
        self._start_sup()
        first = self._client().call("dispatch", {"job": self._job()})
        self.assertEqual(first["state"], "uncertain")
        self.sup.terminate()
        self.sup.wait(timeout=5)
        self._start_sup(state_name="state.json")
        second = self._client().call("dispatch", {"job": self._job()})
        self.assertEqual(second["state"], "uncertain")
        self.assertEqual(self._launch_count("engine job " + self._job()["job_id"]), 1, "lost reply must not be re-sent")

    def test_secret_redaction(self):
        self._start_sim(fail="echo_token")
        self._start_sup()
        result = self._client().call("dispatch", {"job": self._job()})
        self.assertEqual(result["state"], "prelaunch_failed")
        state_path = self.dir / "state.json"
        state_text = state_path.read_text() if state_path.exists() else ""
        self.assertNotIn(self.mcp_token, state_text)
        self.assertNotIn(self.mcp_token, json.dumps(result))
        self.assertNotIn("Bearer " + self.mcp_token, state_text)

    def test_disconnect_is_fail_closed(self):
        self._start_sim()
        self._start_sup()
        body = json.dumps({"op": "health", "token": self.token, "payload": {}}).encode()
        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.connect(str(self.dir / "sup.sock"))
        conn.sendall(struct.pack(">I", len(body)) + body)
        conn.close()                      # disconnect before reading
        time.sleep(0.2)
        self.assertEqual(self._client().call("health")["pid"], self.sup.pid)

    def test_kernel_observed_isolation_of_all_processes(self):
        self._start_sim()
        self._start_sup()
        test_inode = os.stat("/proc/self/ns/net").st_ino
        host_inode = os.environ.get("REHEARSAL_HOST_NETNS")
        if not host_inode:
            self.skipTest("host netns inode not provided (REHEARSAL_HOST_NETNS)")
        self.assertNotEqual(str(test_inode), host_inode, "not running in the isolated netns")
        # kernel-observed identities: read /proc directly, not a self-report
        self.assertEqual(os.stat(f"/proc/{self.sup.pid}/ns/net").st_ino, test_inode)
        self.assertEqual(os.stat(f"/proc/{self.sim.pid}/ns/net").st_ino, test_inode)
        child = subprocess.run([sys.executable, str(TESTS / "_synthetic_child.py")],
                               capture_output=True, text=True, timeout=30,
                               env={**os.environ, "REHEARSAL_HOST_HOME": str(Path.home())})
        info = json.loads(child.stdout.strip().splitlines()[-1])
        self.assertEqual(info["child_netns_inode"], test_inode)
        self.assertEqual(info["egress"], "DENIED")
        self.assertFalse(info["host_home_visible"])

    def test_bad_job_id_type_is_bad_request_and_daemon_survives(self):
        self._start_sim()
        self._start_sup()
        with self.assertRaises(SupervisorRefusal) as ctx:
            self._client().call("state", {"job_id": {}})
        self.assertIn("BAD_REQUEST", str(ctx.exception))
        self.assertEqual(self._client().call("health")["pid"], self.sup.pid)

    def test_cancel_reports_and_calls_interrupt(self):
        self._start_sim()
        self._start_sup()
        client = self._client()
        dispatched = client.call("dispatch", {"job": self._job()})
        result = client.call("cancel", {"job_id": self._job()["job_id"]})
        self.assertTrue(result.get("cancelled"))
        self.assertEqual(result.get("state"), "cancelled")
        events = [json.loads(l) for l in self.events.read_text().splitlines() if l.strip()]
        self.assertIn("interrupt", [e.get("event") for e in events])

    def test_socket_dir_is_created_0700(self):
        self._start_sim()
        self._start_sup(socket_subdir="fresh-sock-dir")
        mode = (self.dir / "fresh-sock-dir").stat().st_mode & 0o777
        self.assertEqual(mode, 0o700)

    def test_peer_uid_mismatch_is_rejected(self):
        self._start_sim()
        self._start_sup(peer_uid=1)     # current uid is not 1
        with self.assertRaises(SupervisorRefusal) as ctx:
            self._client().call("health")
        self.assertIn("PEER_REJECTED", str(ctx.exception))

    def test_engine_accepts_supervisor_result(self):
        self._engine_accepts_supervisor_result(managed=False)

    def test_engine_accepts_managed_bridge_result(self):
        self._engine_accepts_supervisor_result(managed=True)

    def _engine_accepts_supervisor_result(self, *, managed):
        if not BASE_FIXTURE.exists():
            self.skipTest(f"base fixture not available: {BASE_FIXTURE}")
        import shutil

        root = self.dir / "root"
        shutil.copytree(BASE_FIXTURE, root)
        db = root / "orchestrator/var/checkpoints.db"
        conn = sqlite3.connect(str(db))
        row = conn.execute("select value from workflow_meta where key='config'").fetchone()
        cfg = json.loads(row[0].replace(OLD_ROOT, str(root)))
        cfg["root"] = str(root)
        conn.execute("update workflow_meta set value=? where key='config'", (json.dumps(cfg),))
        conn.commit()
        conn.close()
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in (".json", ".md", ".txt") and p.stat().st_size < 2_000_000:
                try:
                    text = p.read_text()
                except (UnicodeDecodeError, OSError):
                    continue
                if OLD_ROOT in text:
                    p.write_text(text.replace(OLD_ROOT, str(root)))
        # prepare the job through the native gate (refusal leaves it CREATED)
        from cli import make_engine
        from core import WorkflowError
        with unittest.mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ENGINE_T3_BACKEND", None)
            os.environ.pop("ENGINE_NATIVE_DISPATCH", None)
            with self.assertRaises(WorkflowError):
                make_engine(root).run()
        job_id = conn = None
        conn = sqlite3.connect(str(root / "orchestrator/var/checkpoints.db"))
        job_id = conn.execute("select job_id from workflow_jobs").fetchone()[0]
        conn.close()
        self._start_sim(legacy_marker_mode=False)
        self._start_sup(managed=managed)
        launcher = SyntheticWorkflowLauncher(root, self.dir / "sup.sock", self.token,
                                             allowed_models=[MODEL])
        from engine import Engine
        engine = Engine(root, launcher=launcher)
        for _ in range(4):
            view = engine.run()
            conn = sqlite3.connect(str(root / "orchestrator/var/checkpoints.db"))
            status = conn.execute("select status from workflow_jobs where job_id=?", (job_id,)).fetchone()[0]
            conn.close()
            if status == "ACCEPTED":
                break
            engine = Engine(root, launcher=SyntheticWorkflowLauncher(
                root, self.dir / "sup.sock", self.token, allowed_models=[MODEL]))
        self.assertEqual(status, "ACCEPTED", view)
        self.assertEqual(self._launch_count("engine job " + job_id), 1)
        results = [entry["payload"] for entry in engine.store.events()
                   if entry["kind"] == "result" and entry["payload"]["job_id"] == job_id]
        self.assertEqual(results[-1]["model_evidence"], "executed")


if __name__ == "__main__":
    unittest.main()
