import sys
import time
from pathlib import Path

from candidates import git
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
        ],
    )
    result = run(spec, runtime, time.monotonic() + 30)
    assert result["complete"] and not result["passed"]
    assert result["records"][0]["exit_code"] == 0 and result["records"][1]["exit_code"] != 0
    assert (repo / "new").read_text() == "candidate"
