import subprocess
from pathlib import Path

from sandbox import command, probe


def test_control_store_and_git_are_not_writable():
    assert probe()


def test_peer_results_hidden_but_explicit_plan_readable(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    control = root / "orchestrator/var"
    control.mkdir(parents=True)
    (control / "peer-transcript").write_text("PEER")
    work = root / "work-item"
    work.mkdir()
    plan = work / "plan.md"
    plan.write_text("APPROVED")
    (work / "peer-result.json").write_text("PEER")
    code = """from pathlib import Path
assert Path('work-item/plan.md').read_text()=='APPROVED'
assert not Path('work-item/peer-result.json').exists()
assert not Path('orchestrator/var/peer-transcript').exists()
try:Path('source').write_text('forbidden')
except OSError:pass
else:raise SystemExit(3)
"""
    r = subprocess.run(
        command(
            ["/usr/bin/python3", "-c", code],
            root,
            work,
            hidden_roots=[control, work],
            read_files=[plan],
            writable_source=False,
        ),
        capture_output=True,
    )
    assert r.returncode == 0, r.stderr.decode()
    assert not (root / "source").exists()
