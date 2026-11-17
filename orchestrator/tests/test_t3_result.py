import json
import tempfile
import unittest
from pathlib import Path

from t3_result import T3ResultError, decode_t3_result
from t3_supervisor import Supervisor
from t3_supervisor_client import SupervisorLauncher, SupervisorRefusal
from t3_transport import TransportRefusal, build_task_spec

MODEL = "codex/test-model"
TASK_ID = "thr-0123456789"
JOB_ID = "job-a1b2"
MARKER = f"ENGINE-T3-RESULT {JOB_ID}"


def _job():
    envelope = {
        "schema_version": 1,
        "job_id": JOB_ID,
        "work_item": "work-item-1",
        "stage": "1",
        "role": "reviewer",
        "tool": "codex",
        "model": MODEL,
        "session_id": "model-session",
        "dispatch_mode": "manual",
        "candidate_kind": "code",
        "candidate_id": "a" * 64,
        "plan_revision_hash": "b" * 64,
        "prompt_version": "c" * 64,
        "status": "COMPLETE",
        "verdict": "PASS",
        "failure_class": None,
        "findings": [],
        "evidence_paths": [
            {
                "artifact_id": "review-evidence-1",
                "sha256": "d" * 64,
                "visibility": "public",
            }
        ],
        "started_utc": "2026-11-15T10:00:00Z",
        "finished_utc": "2026-11-15T10:00:01Z",
    }
    return {
        "job_id": JOB_ID,
        "role": "reviewer",
        "spec": {
            "model": MODEL,
            "tool": "codex",
            "envelope": envelope,
        },
    }


def _response(body=None):
    body = body or _job()["spec"]["envelope"]
    wire = {"result_json": json.dumps(body), "explanation": "Reviewed.", "plan_text": ""}
    return f"Review complete.\n{json.dumps(wire)}\nENGINE-T3-RESULT {JOB_ID}"


class T3ResultTests(unittest.TestCase):
    def test_task_spec_preserves_and_requires_engine_role(self):
        job = {
            "job_id": JOB_ID,
            "idempotency_key": "request-0123456789",
            "model": MODEL,
            "brief": "Read-only review.",
            "expect_marker": f"ENGINE-T3-RESULT {JOB_ID}",
            "access": "read-only",
            "role": "verifier",
        }
        spec = build_task_spec(job, allowed_models=[MODEL])
        self.assertEqual(spec["role"], "verifier")
        missing = dict(job)
        missing.pop("role")
        with self.assertRaisesRegex(TransportRefusal, "role"):
            build_task_spec(missing, allowed_models=[MODEL])

    def test_decodes_received_schema_valid_envelope_and_binds_thread(self):
        session, body, wire, events = decode_t3_result(
            assistant_text=_response(), job=_job(), task_id=TASK_ID, executed_model=MODEL
        )
        self.assertEqual(session, TASK_ID)
        self.assertEqual(body["verdict"], "PASS")
        self.assertEqual(json.loads(wire["result_json"])["job_id"], JOB_ID)
        self.assertEqual(events, [])

    def test_decodes_schema_valid_blocked_builder_result(self):
        builder = _job()
        builder["role"] = "builder"
        envelope = dict(builder["spec"]["envelope"], role="builder", verdict="BLOCKED")
        envelope["findings"] = [
            {
                "schema_version": 1,
                "finding_id": None,
                "classification": "owner_decision",
                "blocking": True,
                "summary": "Required contract artifacts are unavailable.",
                "affected_requirements": ["R1"],
                "evidence_refs": [],
                "snapshot": None,
            }
        ]
        builder["spec"]["envelope"] = envelope
        wire = {
            "result_json": json.dumps(envelope),
            "explanation": "Blocked safely.",
            "plan_text": "",
            "builder_bundle_json": '{"files":[]}',
        }
        session, body, _, _ = decode_t3_result(
            assistant_text=f"{json.dumps(wire)}\nENGINE-T3-RESULT {JOB_ID}",
            job=builder,
            task_id=TASK_ID,
            executed_model=MODEL,
        )
        self.assertEqual(session, TASK_ID)
        self.assertEqual(body["status"], "COMPLETE")
        self.assertEqual(body["verdict"], "BLOCKED")

    def test_rejects_malformed_blocked_result_instead_of_accepting_it(self):
        builder = _job()
        builder["role"] = "builder"
        builder["spec"]["envelope"]["role"] = "builder"
        envelope = dict(
            builder["spec"]["envelope"],
            role="builder",
            status="BLOCKED",
            verdict="BLOCKED",
            failure_class="MISSING_REQUIRED_ARTIFACTS",
        )
        wire = {
            "result_json": json.dumps(envelope),
            "explanation": "Blocked.",
            "plan_text": "",
            "builder_bundle_json": '{"files":[]}',
        }
        with self.assertRaisesRegex(T3ResultError, "schema validation"):
            decode_t3_result(
                assistant_text=f"{json.dumps(wire)}\nENGINE-T3-RESULT {JOB_ID}",
                job=builder,
                task_id=TASK_ID,
                executed_model=MODEL,
            )

    def test_builder_response_limit_is_raised_only_for_builder_role(self):
        builder = _job()
        builder["role"] = "builder"
        body = dict(builder["spec"]["envelope"], role="builder")
        builder["spec"]["envelope"] = body
        wire = {
            "result_json": json.dumps(body),
            "explanation": "x" * 9_000,
            "plan_text": "",
            "builder_bundle_json": "{}",
        }
        response = f"ENGINE-T3-RESULT {JOB_ID}\n{json.dumps(wire)}"
        session, _, _, _ = decode_t3_result(
            assistant_text=response, job=builder, task_id=TASK_ID, executed_model=MODEL
        )
        self.assertEqual(session, TASK_ID)
        with self.assertRaisesRegex(T3ResultError, "8000 characters"):
            decode_t3_result(assistant_text=response, job=_job(), task_id=TASK_ID, executed_model=MODEL)

        oversized = "ENGINE-T3-RESULT " + JOB_ID + "\n" + ("x" * 50_000)
        with self.assertRaisesRegex(T3ResultError, "50000 characters"):
            decode_t3_result(assistant_text=oversized, job=builder, task_id=TASK_ID, executed_model=MODEL)

    def test_rejects_marker_only_without_fabricating_pass(self):
        with self.assertRaisesRegex(T3ResultError, "no complete result wire"):
            decode_t3_result(
                assistant_text=f"ENGINE-T3-RESULT {JOB_ID}", job=_job(), task_id=TASK_ID, executed_model=MODEL
            )

    def test_rejects_missing_marker_and_malformed_json(self):
        with self.assertRaisesRegex(T3ResultError, "marker"):
            decode_t3_result(assistant_text="{}", job=_job(), task_id=TASK_ID, executed_model=MODEL)
        text = f'ENGINE-T3-RESULT {JOB_ID}\n{{"result_json":'
        with self.assertRaises(T3ResultError):
            decode_t3_result(assistant_text=text, job=_job(), task_id=TASK_ID, executed_model=MODEL)

    def test_rejects_job_and_role_mismatch(self):
        body = dict(_job()["spec"]["envelope"], job_id="job-deadbeef")
        with self.assertRaisesRegex(T3ResultError, "job_id"):
            decode_t3_result(
                assistant_text=_response(body), job=_job(), task_id=TASK_ID, executed_model=MODEL
            )
        body = dict(_job()["spec"]["envelope"], role="builder")
        with self.assertRaisesRegex(T3ResultError, "role"):
            decode_t3_result(
                assistant_text=_response(body), job=_job(), task_id=TASK_ID, executed_model=MODEL
            )

    def test_rejects_model_mismatch_and_missing_thread_identity(self):
        body = dict(_job()["spec"]["envelope"], model="other/model")
        with self.assertRaisesRegex(T3ResultError, "result model"):
            decode_t3_result(
                assistant_text=_response(body), job=_job(), task_id=TASK_ID, executed_model=MODEL
            )
        with self.assertRaisesRegex(T3ResultError, "thread identity"):
            decode_t3_result(assistant_text=_response(), job=_job(), task_id="", executed_model=MODEL)
        with self.assertRaisesRegex(T3ResultError, "executed model"):
            decode_t3_result(
                assistant_text=_response(), job=_job(), task_id=TASK_ID, executed_model="other/model"
            )

    def test_rejects_schema_invalid_result(self):
        body = dict(_job()["spec"]["envelope"])
        body["unexpected"] = True
        with self.assertRaisesRegex(T3ResultError, "schema validation"):
            decode_t3_result(
                assistant_text=_response(body), job=_job(), task_id=TASK_ID, executed_model=MODEL
            )

    def test_supervisor_rejects_receipt_task_id_mismatch(self):
        class StubClient:
            def call(self, op, payload):
                if op == "collect":
                    return {
                        "state": "completed",
                        "receipt": {
                            "job_id": JOB_ID,
                            "task_id": "thr-impostor",
                            "executed_model": MODEL,
                            "model_evidence": "executed",
                            "summary": _response(),
                        },
                    }
                if op == "state":
                    return {"record": {"job_id": JOB_ID, "task_id": TASK_ID, "model": MODEL}}
                raise AssertionError(op)

        with tempfile.TemporaryDirectory() as temp:
            job = _job()
            job["runtime"] = str(Path(temp) / "runtime")
            launcher = SupervisorLauncher(temp, "unused", "unused", allowed_models=[MODEL])
            launcher.client = StubClient()
            with self.assertRaisesRegex(SupervisorRefusal, "correlation"):
                launcher.poll(job)

    def test_supervisor_preserves_engine_role_without_fallback(self):
        class CapturingClient:
            role = None

            def delegate(self, **kwargs):
                self.role = kwargs["role"]
                return {"taskId": TASK_ID}

        with tempfile.TemporaryDirectory() as temp:
            supervisor = Supervisor(
                socket_path=Path(temp) / "sup.sock",
                state_path=Path(temp) / "state.json",
                token="test-token",
                base_url="http://127.0.0.1:1",
                mcp_token="no-network",
                model=MODEL,
                allowed_models=[MODEL],
            )
            client = CapturingClient()
            supervisor._client = lambda: client
            job = {
                "job_id": JOB_ID,
                "client_request_id": "request-0123456789",
                "model": MODEL,
                "brief": "Read-only review.",
                "expect_marker": f"ENGINE-T3-RESULT {JOB_ID}",
                "role": "verifier",
                "candidate_kind": "code",
            }
            response = supervisor.handle({"op": "dispatch", "token": "test-token", "payload": {"job": job}})
            self.assertEqual(response["result"]["state"], "dispatched")
            self.assertEqual(client.role, "verifier")
            missing_role = dict(job)
            missing_role.pop("role")
            refused = supervisor.handle(
                {"op": "dispatch", "token": "test-token", "payload": {"job": missing_role}}
            )
            self.assertEqual(refused["error"]["code"], "BAD_REQUEST")

            unsupported = dict(job, role="builder")
            refused = supervisor.handle(
                {"op": "dispatch", "token": "test-token", "payload": {"job": unsupported}}
            )
            self.assertEqual(refused["error"]["code"], "REFUSED")

    def test_supervisor_requires_confirmed_interrupt_and_skips_terminal_jobs(self):
        class CapturingClient:
            calls = 0

            def cancel(self, task_id, reason):
                self.calls += 1
                return {"threadId": "thr-some-other-task", "status": "cancelled"}

        with tempfile.TemporaryDirectory() as temp:
            supervisor = Supervisor(
                socket_path=Path(temp) / "sup.sock",
                state_path=Path(temp) / "state.json",
                token="test-token",
                base_url="http://127.0.0.1:1",
                mcp_token="no-network",
                model=MODEL,
                allowed_models=[MODEL],
            )
            client = CapturingClient()
            supervisor._client = lambda: client
            supervisor.state.put(
                JOB_ID,
                {
                    "job_id": JOB_ID,
                    "task_id": TASK_ID,
                    "model": MODEL,
                    "state": "dispatched",
                    "client_request_id": "request-0123456789",
                },
            )
            response = supervisor.handle(
                {"op": "cancel", "token": "test-token", "payload": {"job_id": JOB_ID}}
            )
            self.assertFalse(response["result"]["cancelled"])
            self.assertEqual(response["result"]["state"], "dispatched")
            self.assertEqual(supervisor.state.get(JOB_ID)["state"], "dispatched")

            supervisor.state.put(
                JOB_ID,
                {
                    "job_id": JOB_ID,
                    "task_id": TASK_ID,
                    "model": MODEL,
                    "state": "completed",
                    "client_request_id": "request-0123456789",
                },
            )
            response = supervisor.handle(
                {"op": "cancel", "token": "test-token", "payload": {"job_id": JOB_ID}}
            )
            self.assertFalse(response["result"]["cancelled"])
            self.assertEqual(response["result"]["state"], "completed")
            self.assertEqual(client.calls, 1)

    def test_supervisor_parks_completed_outcome_with_pending_owner_action(self):
        class CapturingClient:
            def __init__(self, first_outcome):
                self.outcomes = [
                    first_outcome,
                    {
                        "status": "completed",
                        "summary": MARKER,
                        "executedModel": MODEL,
                        "hasPendingQuestion": False,
                        "pendingApproval": None,
                    },
                ]

            def status(self, _task_id):
                return self.outcomes.pop(0)

        for pending in ({"hasPendingQuestion": True}, {"pendingApproval": {"kind": "command"}}):
            with self.subTest(pending=pending), tempfile.TemporaryDirectory() as temp:
                supervisor = Supervisor(
                    socket_path=Path(temp) / "sup.sock",
                    state_path=Path(temp) / "state.json",
                    token="test-token",
                    base_url="http://127.0.0.1:1",
                    mcp_token="no-network",
                    model=MODEL,
                    allowed_models=[MODEL],
                )
                client = CapturingClient(
                    {
                        "status": "completed",
                        "summary": MARKER,
                        "executedModel": MODEL,
                        "hasPendingQuestion": False,
                        "pendingApproval": None,
                        **pending,
                    }
                )
                supervisor._client = lambda: client
                supervisor.state.put(
                    JOB_ID,
                    {
                        "job_id": JOB_ID,
                        "task_id": TASK_ID,
                        "model": MODEL,
                        "expect_marker": MARKER,
                        "state": "dispatched",
                        "client_request_id": "request-0123456789",
                        "history": [{"state": "dispatched", "utc": "2026-01-01T00:00:00Z"}],
                    },
                )

                waiting = supervisor._collect(JOB_ID)
                self.assertEqual(waiting["state"], "waiting")
                self.assertEqual(supervisor.state.get(JOB_ID)["wait_reason"], "pending_owner_action")
                self.assertNotIn("receipt", supervisor.state.get(JOB_ID))

                launcher = SupervisorLauncher(temp, "unused", "unused", allowed_models=[MODEL])
                launcher.client = type(
                    "WaitingClient", (), {"call": lambda self, *_args, **_kwargs: {"state": "waiting"}}
                )()
                runtime = Path(temp) / "runtime"
                launcher.poll({"job_id": JOB_ID, "runtime": str(runtime), "spec": {"model": MODEL}})
                self.assertFalse((runtime / "terminal.json").exists())

                completed = supervisor._collect(JOB_ID)
                self.assertEqual(completed["state"], "completed")
                self.assertIn("receipt", supervisor.state.get(JOB_ID))

    def test_receipt_marks_configured_only_model_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            supervisor = Supervisor(
                socket_path=Path(temp) / "sup.sock",
                state_path=Path(temp) / "state.json",
                token="test-token",
                base_url="http://127.0.0.1:1",
                mcp_token="no-network",
                model=MODEL,
                allowed_models=[MODEL],
            )
            supervisor._client = lambda: type(
                "Client",
                (),
                {
                    "status": lambda self, _task_id: {
                        "status": "completed",
                        "summary": MARKER,
                        "model": MODEL,
                        "executedModel": None,
                        "modelEvidence": "configured_only",
                    }
                },
            )()
            supervisor.state.put(
                JOB_ID,
                {
                    "job_id": JOB_ID,
                    "task_id": TASK_ID,
                    "model": MODEL,
                    "expect_marker": MARKER,
                    "state": "dispatched",
                    "history": [],
                },
            )
            receipt = supervisor._collect(JOB_ID)["receipt"]
            self.assertEqual(receipt["model_evidence"], "configured_only")
            self.assertIsNone(receipt["executed_model"])
            self.assertEqual(receipt["configured_model"], MODEL)


if __name__ == "__main__":
    unittest.main()
