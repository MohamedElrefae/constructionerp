import sys
import time
from pathlib import Path

import pytest
import validation_runner
from candidates import git
from core import WorkflowError
from validation_runner import run


def test_offline_validations_capture_real_exit_and_protect_source(repo, tmp_path):
    (repo / "new").write_text("candidate")
    work = repo / "work-item"
    work.mkdir()
    runtime = tmp_path / "control"
    runtime.mkdir()
    base = git(repo, "rev-parse", "HEAD").decode().strip()
    spec = dict(
        root=str(repo),
        base_commit=base,
        branch="test",
        allowed_paths=["new"],
        generated=[],
        work_item_root=str(work),
        control_root=str(runtime),
        validation_commands=[
            [sys.executable, "-c", 'from pathlib import Path; assert Path("new").read_text()=="candidate"'],
            [sys.executable, "-c", 'from pathlib import Path; Path("new").write_text("bad")'],
            [
                sys.executable,
                "-c",
                'import socket; s=socket.socket(); s.settimeout(1); s.connect(("1.1.1.1", 80))',
            ],
        ],
    )
    if not validation_runner.can_unshare_net():
        with pytest.raises(WorkflowError, match="Network isolation unavailable"):
            run(spec, runtime, time.monotonic() + 30)
        assert (repo / "new").read_text() == "candidate"
        return

    result = run(spec, runtime, time.monotonic() + 30)
    assert result["complete"] and not result["passed"]
    assert result["records"][0]["exit_code"] == 0
    assert result["records"][1]["exit_code"] != 0
    # Network egress is denied:
    assert result["records"][2]["exit_code"] != 0
    assert (repo / "new").read_text() == "candidate"


def test_offline_validation_fails_closed_when_network_isolation_unavailable(repo, tmp_path, monkeypatch):
    (repo / "new").write_text("candidate")
    work = repo / "work-item"
    work.mkdir()
    runtime = tmp_path / "control"
    runtime.mkdir()
    base = git(repo, "rev-parse", "HEAD").decode().strip()
    spec = dict(
        root=str(repo),
        base_commit=base,
        branch="test",
        allowed_paths=["new"],
        generated=[],
        work_item_root=str(work),
        control_root=str(runtime),
        validation_commands=[
            [sys.executable, "-c", "import sys; sys.exit(0)"],
        ],
    )
    monkeypatch.setattr(validation_runner, "can_unshare_net", lambda: False)
    with pytest.raises(WorkflowError, match="Network isolation unavailable"):
        run(spec, runtime, time.monotonic() + 30)
    # Ensure no child validation command was launched or output created
    assert not (runtime / "validation-0.stdout").exists()
