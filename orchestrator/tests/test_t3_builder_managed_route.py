import json

from t3_supervisor import Supervisor


class _Client:
    def __init__(self, model, marker):
        self.model = model
        self.marker = marker
        self.launches = []
        self.outcomes = []

    def delegate(self, **kwargs):
        self.launches.append(kwargs)
        return {"taskId": "thread-builder-1"}

    def status(self, task_id):
        assert task_id == "thread-builder-1"
        return self.outcomes.pop(0)


def _job():
    job_id = "job-" + "a" * 24
    marker = "ENGINE-T3-RESULT " + job_id
    return marker, {
        "job_id": job_id,
        "client_request_id": "wp1-engine-job-" + "b" * 32,
        "model": "opencode/synthetic-builder",
        "brief": "Return a bounded source packet as builder_bundle_json.",
        "role": "builder",
        "expect_marker": marker,
        "timeout_ms": 120_000,
    }


def _request(job):
    return {"op": "dispatch", "token": "protocol-token-1234567890", "payload": {"job": job}}


def test_builder_requires_explicit_managed_supervisor_capability(tmp_path):
    marker, job = _job()
    client = _Client(job["model"], marker)
    supervisor = Supervisor(
        socket_path=tmp_path / "sup.sock",
        state_path=tmp_path / "state.json",
        token="protocol-token-1234567890",
        base_url="http://127.0.0.1:8000",
        mcp_token="mcp-secret-token",
        model=job["model"],
        allowed_models=[job["model"]],
    )
    supervisor._client = lambda: client

    refused = supervisor.handle(_request(job))
    assert refused["ok"] is False
    assert refused["error"]["code"] == "REFUSED"
    assert client.launches == []


def test_managed_builder_refuses_oversized_candidate_packet_before_launch(tmp_path):
    marker, job = _job()
    job["brief"] = "x" * 80_001
    client = _Client(job["model"], marker)
    supervisor = Supervisor(
        socket_path=tmp_path / "sup.sock",
        state_path=tmp_path / "state.json",
        token="protocol-token-1234567890",
        base_url="http://127.0.0.1:8000",
        mcp_token="mcp-secret-token",
        model=job["model"],
        allowed_models=[job["model"]],
        builder_enabled=True,
    )
    supervisor._client = lambda: client
    refused = supervisor.handle(_request(job))
    assert refused["ok"] is False
    assert "brief size bound" in refused["error"]["message"]
    assert client.launches == []


def test_managed_builder_stays_single_launch_across_waiting_question_and_completion(tmp_path):
    marker, job = _job()
    client = _Client(job["model"], marker)
    source_packet = json.dumps({"files": [{"path": "src/app.py", "content": "print(1)"}]})
    job["brief"] += "\n" + source_packet
    supervisor = Supervisor(
        socket_path=tmp_path / "sup.sock",
        state_path=tmp_path / "state.json",
        token="protocol-token-1234567890",
        base_url="http://127.0.0.1:8000",
        mcp_token="mcp-secret-token",
        model=job["model"],
        allowed_models=[job["model"]],
        builder_enabled=True,
    )
    supervisor._client = lambda: client

    dispatched = supervisor.handle(_request(job))
    assert dispatched["ok"] is True
    assert dispatched["result"]["state"] == "dispatched"
    assert len(client.launches) == 1
    launch = client.launches[0]
    assert launch["role"] == "builder"
    assert "src/app.py" in launch["task"]
    assert "builder_bundle_json" in launch["task"]

    client.outcomes = [{"status": "waiting", "hasPendingQuestion": True}]
    waiting = supervisor.handle(
        {"op": "collect", "token": supervisor.token, "payload": {"job_id": job["job_id"]}}
    )
    assert waiting["result"]["state"] == "waiting"
    assert "receipt" not in waiting["result"]

    retry = supervisor.handle(_request(job))
    assert retry["result"]["state"] == "waiting"
    assert len(client.launches) == 1

    client.outcomes = [
        {
            "status": "completed",
            "hasPendingQuestion": False,
            "model": job["model"],
            "executedModel": job["model"],
            "summary": marker + "\nmodel completed",
        }
    ]
    # The supervisor's transport receipt requires only marker and model pin;
    # Engine-side decoding still rejects malformed/incomplete builder output.
    completed = supervisor.handle(
        {"op": "collect", "token": supervisor.token, "payload": {"job_id": job["job_id"]}}
    )
    assert completed["result"]["state"] == "completed"
    assert completed["result"]["receipt"]["model_evidence"] == "executed"
    assert len(client.launches) == 1


def test_builder_receipt_preserves_large_output_and_refuses_secret_redaction(tmp_path):
    marker, job = _job()
    client = _Client(job["model"], marker)
    supervisor = Supervisor(
        socket_path=tmp_path / "sup.sock",
        state_path=tmp_path / "state.json",
        token="protocol-token-1234567890",
        base_url="http://127.0.0.1:8000",
        mcp_token="mcp-secret-token",
        model=job["model"],
        allowed_models=[job["model"]],
        builder_enabled=True,
    )
    supervisor._client = lambda: client
    assert supervisor.handle(_request(job))["result"]["state"] == "dispatched"
    output = marker + "\n" + "x" * 12_000
    client.outcomes = [
        {"status": "completed", "model": job["model"], "executedModel": job["model"], "summary": output}
    ]
    result = supervisor.handle(
        {"op": "collect", "token": supervisor.token, "payload": {"job_id": job["job_id"]}}
    )
    assert result["result"]["receipt"]["summary"] == output

    _, second = _job()
    second["job_id"] = "job-" + "b" * 24
    second["expect_marker"] = "ENGINE-T3-RESULT " + second["job_id"]
    second["client_request_id"] += "-two"
    assert supervisor.handle(_request(second))["result"]["state"] == "dispatched"
    client.outcomes = [
        {
            "status": "completed",
            "model": second["model"],
            "executedModel": second["model"],
            "summary": second["expect_marker"] + "\nBearer sensitive",
        }
    ]
    result = supervisor.handle(
        {"op": "collect", "token": supervisor.token, "payload": {"job_id": second["job_id"]}}
    )
    assert result["result"]["state"] == "failed"
    assert "receipt" not in result["result"]
