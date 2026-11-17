"""HttpT3Client + dispatcher against a deterministic local MCP simulator.

No real T3, no provider, no external network: the simulator listens on
loopback inside the kernel-enforced no-egress harness namespace.
"""

import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _mcp_sim import SimServer, SimState
from engine_t3_dispatch import L_COLLECTED, DispatchLedger, EngineT3Dispatcher
from t3_transport import (
    CorrelationStore,
    HttpT3Client,
    T3Transport,
    TransportReconciliationRequired,
    TransportRefusal,
    TransportUncertain,
)

MODEL = "opencode/deepseek-v4.1-flash-free"


def _job(root: Path, job_id: str = "job-" + "a" * 24) -> dict:
    return {
        "job_id": job_id,
        "idempotency_key": job_id,
        "work_item": "pilot-loop",
        "root": str(root),
        "model": MODEL,
        "role": "reviewer",
        "brief": "Compute 6 * 7 and report the result.",
        "expect_marker": f"ENGINE-T3-RESULT {job_id}",
        "access": "read-only",
    }


def _dispatcher(root: Path, transport) -> EngineT3Dispatcher:
    return EngineT3Dispatcher(
        work_item="pilot-loop",
        root=str(root),
        allowed_models=[MODEL],
        transport=transport,
        ledger=DispatchLedger(root / "ledger.json"),
        allow_dispatch=True,
    )


def _transport(root: Path, client) -> T3Transport:
    return T3Transport(
        CorrelationStore(root / "corr.json"),
        client,
        allowed_models=[MODEL],
        allow_send=True,
    )


class HttpContractTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="t3-http-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        # This suite exercises the low-level transport protocol, not Engine
        # result decoding; marker-only replies are an explicit legacy fixture.
        self.state = SimState(legacy_marker_mode=True)
        self.server = SimServer(self.state)
        self.server.__enter__()
        self.addCleanup(self.server.__exit__, None, None, None)
        self.client = HttpT3Client(self.server.url, self.state.token)

    def test_auth_is_required(self):
        with self.assertRaises(TransportRefusal) as ctx:
            HttpT3Client(self.server.url, "x" * 24).initialize()
        self.assertIn("401", str(ctx.exception))
        self.assertEqual(self.state.calls, [], "401 must be rejected before any method runs")

    def test_go_flash_model_reaches_the_opencode_provider(self):
        model = "opencode-go/deepseek-v4.1-flash"
        transport = T3Transport(
            CorrelationStore(self.root / "go-corr.json"),
            self.client,
            allowed_models=[model],
            allow_send=True,
        )
        job = _job(self.root)
        job["model"] = model
        result = transport.send(job)
        thread = self.state.threads[result["task_id"]]
        self.assertEqual(thread["provider"], "opencode")
        self.assertEqual(thread["model"], model)

    def test_initialize_and_tool_listing(self):
        out = self.client.initialize()
        self.assertEqual(out["result"]["protocolVersion"], "2025-03-26")
        tools = self.client.list_tools()
        self.assertIn("t3_thread_launch", tools)
        self.assertIn("t3_thread_read", tools)

    def test_codex_provider_instance_reaches_launch(self):
        client = HttpT3Client(self.server.url, self.state.token, provider="codex")
        result = client.delegate(
            task="[engine job job-" + "a" * 24 + "] Test",
            model="gpt-6-luna",
            role="reviewer",
            client_request_id="synthetic-request-12345",
            timeout_ms=1000,
            expect_marker="SYNTHETIC-MARKER",
        )
        thread = self.state.threads[result["taskId"]]
        self.assertEqual(thread["provider"], "codex")
        self.assertEqual(thread["model"], "gpt-6-luna")

    def test_delegate_and_status(self):
        job = _job(self.root)
        out = self.client.delegate(
            task=f"[engine job {job['job_id']}] Compute. Last line: {job['expect_marker']}",
            model=MODEL,
            role="research",
            client_request_id="wp1-engine-job-" + "b" * 32,
            timeout_ms=1000,
            expect_marker=job["expect_marker"],
        )
        self.assertTrue(out["taskId"].startswith("thr-"))
        status = self.client.status(out["taskId"])
        self.assertEqual(status["status"], "completed")
        self.assertIn(job["expect_marker"], status["summary"])
        self.assertEqual(status["executedModel"], MODEL)

    def test_session_header_is_sent_after_initialize(self):
        self.client.initialize()
        self.client._tool("t3_project_list", {"limit": 10})
        self.assertEqual(self.state.sessions_seen, ["sess-sim-1"])

    def test_missing_marker_is_refused(self):
        transport = _transport(self.root, self.client)
        dispatcher = _dispatcher(self.root, transport)
        job = _job(self.root)
        dispatcher.dispatch(job)
        self.state.fail = "no_marker"
        with self.assertRaises(TransportRefusal):
            dispatcher.collect(job["job_id"])

    def test_pagination(self):
        transport = _transport(self.root, self.client)
        projects = transport._list_all("t3_project_list", {"limit": 2}, "projects")
        self.assertEqual(len(projects), 3)
        self.assertEqual([p["projectId"] for p in projects], ["proj-a", "proj-b", "proj-c"])

    def test_http_failure_surfaces_as_refusal(self):
        self.state.fail = "http500"
        with self.assertRaises(TransportRefusal):
            self.client._tool("t3_project_list", {"limit": 10})

    def test_malformed_body_surfaces_as_refusal(self):
        self.state.fail = "malformed"
        with self.assertRaises(TransportRefusal):
            self.client._tool("t3_project_list", {"limit": 10})

    def test_dispatcher_success_over_http(self):
        transport = _transport(self.root, self.client)
        dispatcher = _dispatcher(self.root, transport)
        job = _job(self.root)
        rec = dispatcher.dispatch(job)
        self.assertEqual(rec["state"], "dispatched")
        self.assertTrue(rec["task_id"].startswith("thr-"))
        collected = dispatcher.collect(job["job_id"])
        self.assertEqual(collected["state"], L_COLLECTED)
        self.assertIn(job["expect_marker"], collected["receipt"]["summary"])

    def test_lost_reply_parks_without_resend(self):
        self.state.fail = "lost_reply"
        transport = _transport(self.root, self.client)
        dispatcher = _dispatcher(self.root, transport)
        job = _job(self.root)
        with self.assertRaises(TransportUncertain):
            dispatcher.dispatch(job)
        launches = [c for c in self.state.calls if c == ("tools/call", "t3_thread_launch")]
        self.assertEqual(len(launches), 1)
        with self.assertRaises(TransportReconciliationRequired):
            transport.reattach(job["job_id"])
        launches = [c for c in self.state.calls if c == ("tools/call", "t3_thread_launch")]
        self.assertEqual(len(launches), 1, "reattach must never re-send")

    def test_transport_redacts_token_from_persisted_errors(self):
        self.state.fail = "echo_token"
        transport = _transport(self.root, self.client)
        job = _job(self.root)
        with self.assertRaises(TransportUncertain):
            transport.send(job)
        rec = transport.store.get(job["job_id"]) or {}
        self.assertNotIn(self.state.token, json.dumps(rec))
        self.assertNotIn("Bearer " + self.state.token, json.dumps(rec))

    def test_egress_is_denied_while_loopback_works(self):
        with self.assertRaises(OSError):
            socket.create_connection(("203.0.113.1", 443), timeout=2)
        self.assertEqual(self.client.initialize()["result"]["protocolVersion"], "2025-03-26")


if __name__ == "__main__":
    unittest.main()


class HttpRestartTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="t3-http2-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.state = SimState(legacy_marker_mode=True)
        self.server = SimServer(self.state)
        self.server.__enter__()
        self.addCleanup(self.server.__exit__, None, None, None)

    def test_restart_does_not_resend_or_repoll(self):
        client = HttpT3Client(self.server.url, self.state.token)
        transport = _transport(self.root, client)
        dispatcher = _dispatcher(self.root, transport)
        job = _job(self.root)
        dispatcher.dispatch(job)
        dispatcher.collect(job["job_id"])
        calls_after = len(self.state.calls)
        # restart: new client/transport/dispatcher over the same durable stores
        client2 = HttpT3Client(self.server.url, self.state.token)
        transport2 = _transport(self.root, client2)
        dispatcher2 = _dispatcher(self.root, transport2)
        again = dispatcher2.collect(job["job_id"])
        self.assertEqual(again["state"], L_COLLECTED)
        self.assertEqual(len(self.state.calls), calls_after, "terminal collect must not repoll")
