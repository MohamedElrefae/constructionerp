"""TEST-ONLY synthetic T3 transport. No network, no T3, no provider.

This module exists so tests can exercise the real engine/dashboard entry points
with a deterministic in-process double. It is injected explicitly by tests via
``cli.make_engine(..., transport_factory=...)`` or
``dashboard_api.execute_action(..., engine_factory=...)``. Production code never
constructs it: the production T3 backend is refused unconditionally.
"""

from pathlib import Path

from t3_transport import CorrelationStore, T3Transport


class SyntheticT3Client:
    """In-memory T3 double: deterministic task ids, canned terminal outcomes."""

    def __init__(self, *, mode: str = "ok"):
        if mode not in ("ok", "lost_reply"):
            raise ValueError(f"unknown synthetic mode: {mode!r}")
        self.mode = mode
        self.calls: list[tuple[str, str]] = []
        self.tasks: dict[str, dict] = {}
        self._next = 0

    def delegate(self, *, task, model, role, client_request_id, timeout_ms,
                 expect_marker, project_id=None):
        self.calls.append(("delegate", client_request_id))
        self._next += 1
        task_id = f"task-synthetic-{self._next:04d}"
        self.tasks[task_id] = {
            "model": model,
            "expect_marker": expect_marker,
            "client_request_id": client_request_id,
            "envelope": getattr(self, "envelope", None),
        }
        if self.mode == "lost_reply":
            # The task exists at the (synthetic) T3 side, but the reply is lost.
            raise TimeoutError("synthetic lost reply: task created, reply lost")
        return {"taskId": task_id, "raw": {"projectId": "synthetic-project"}}

    def status(self, task_id):
        task = self.tasks.get(task_id)
        if task is None:
            raise KeyError(task_id)
        return {
            "taskId": task_id,
            "status": "completed",
            "latestTerminalStatus": "completed",
            "executedModel": task["model"],
            # The engine's transport contract requires the expect_marker in the
            # summary and a wire envelope (result_json/explanation/plan_text) in
            # stdout; the marker line precedes the JSON envelope.
            "summary": f"{task['expect_marker']}\n" + _wire(task),
            "hasPendingQuestion": False,
            "pendingApproval": False,
        }

    def cancel(self, task_id, reason):
        return {"taskId": task_id, "status": "cancelled", "reason": reason}

    def _tool(self, name, arguments):
        # Read-only enumeration used by reconciliation lookups.
        if name == "t3_project_list":
            return {"projects": [], "nextCursor": None}
        if name == "t3_thread_list":
            return {"threads": [], "nextCursor": None}
        raise RuntimeError(f"synthetic client: unsupported tool {name!r}")


class SyntheticTransportFactory:
    """Factory matching T3DispatchLauncher's transport_factory contract."""

    def __init__(self, client: SyntheticT3Client):
        self.client = client

    def __call__(self, *, root, allowed_models, allow_send=True, **_):
        store = CorrelationStore(Path(root) / "orchestrator/var/t3-correlation.json")
        return T3Transport(
            store,
            self.client,
            allowed_models=list(allowed_models),
            allow_send=bool(allow_send),
        )


def make_synthetic_factory(mode: str = "ok") -> tuple[SyntheticTransportFactory, SyntheticT3Client]:
    client = SyntheticT3Client(mode=mode)
    return SyntheticTransportFactory(client), client

def _wire(task: dict) -> str:
    """Schema-valid wire envelope for the synthetic result."""
    import json as _json

    body = dict(task["envelope"]) if task.get("envelope") else {}
    body.update(
        schema_version=body.get("schema_version", 1),
        status="COMPLETE",
        verdict=body.get("verdict", "PROPOSED"),
        failure_class=None,
        findings=[],
        evidence_paths=[],
        session_id=task.get("client_request_id", "synthetic"),
    )
    return _json.dumps({
        "result_json": _json.dumps(body),
        "explanation": "synthetic seam result",
        # The architect result must carry a plan; the engine adopts it as the
        # plan artifact. Synthetic, no-op content for the seam test only.
        "plan_text": "# Synthetic plan\n\nSeam test plan; no project content.\n",
    })
