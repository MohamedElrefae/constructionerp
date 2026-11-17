"""Engine may retry only when its launcher proves no task was started."""
from pathlib import Path
from unittest import mock
import pytest

from core import ProvenNoLaunch, WorkflowError, bytes_hash
from engine import Engine
from t3_supervisor_client import SupervisorUnavailable


def test_proven_prelaunch_failure_restores_created_job(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text("synthetic plan")
    revision = bytes_hash(plan.read_bytes())
    candidate = {"candidate_id": "synthetic"}
    job = {"status": "CREATED", "role": "reviewer", "candidate_id": "synthetic",
           "plan_revision_hash": revision, "launch_attempts": 0,
           "spec": {"envelope": {"stage": "1"}}}
    view = {"status": "ACTIVE", "gate": None, "active_jobs": ["job-1"],
            "candidate": candidate, "plan_revision_hash": revision, "stage": "1"}

    class NoLaunch:
        def __call__(self, _job):
            raise ProvenNoLaunch("synthetic session setup failure")

    engine = object.__new__(Engine)
    engine.root = Path(tmp_path)
    engine.config = {"plan_path": "plan.md"}
    engine.launcher = NoLaunch()
    engine.store = mock.Mock()
    engine.store.job.return_value = job
    engine.store.meta.return_value = "plan.md"
    engine._synchronize = lambda _state: {"view": view}
    engine._recheck_candidate = lambda _candidate: None
    engine._validate_engineering_job = lambda _job: None
    engine._enforce_native_dispatch_gate = lambda: None
    engine._dispatch({})
    assert engine.store.update_job.call_args_list == [
        mock.call("job-1", "LAUNCH_INTENT", launch_attempts=1),
        mock.call("job-1", "CREATED", no_child=True),
    ]

    class UnknownLaunch:
        def __call__(self, _job):
            raise SupervisorUnavailable("synthetic lost reply")

    engine.store.update_job.reset_mock()
    engine.launcher = UnknownLaunch()
    with pytest.raises(SupervisorUnavailable):
        engine._dispatch({})
    assert engine.store.update_job.call_args_list == [
        mock.call("job-1", "LAUNCH_INTENT", launch_attempts=1),
    ]

    class UnknownOsError:
        def __call__(self, _job):
            raise OSError("synthetic I/O failure after possible launch")

    engine.store.update_job.reset_mock()
    engine.launcher = UnknownOsError()
    with pytest.raises(WorkflowError, match="RECONCILIATION_REQUIRED"):
        engine._dispatch({})
    assert engine.store.update_job.call_args_list == [
        mock.call("job-1", "LAUNCH_INTENT", launch_attempts=1),
    ]
