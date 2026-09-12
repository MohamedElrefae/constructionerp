"""Required native-process write isolation; no token authority rests on prompts."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from core import WorkflowError


def command(
    argv,
    root,
    work_item,
    writable_native=(),
    hidden_roots=(),
    read_files=(),
    writable_source=True,
    neutral_mounts=(),
):
    binary = shutil.which("bwrap")
    if not binary:
        raise WorkflowError("Bubblewrap unavailable: native dispatch disabled")
    root = Path(root).resolve()
    cmd = [
        binary,
        "--die-with-parent",
        "--new-session",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--ro-bind",
        "/",
        "/",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--tmpfs",
        "/run",
    ]
    if root.is_relative_to("/tmp"):
        cmd += ["--dir", str(root)]
    cmd += [
        "--bind" if writable_source else "--ro-bind",
        str(root),
        str(root),
    ]
    # Preserve resolver data when /etc/resolv.conf points into the hidden /run tree.
    resolver = Path("/etc/resolv.conf").resolve()
    if resolver.is_file() and resolver.is_relative_to("/run"):
        cmd += ["--ro-bind", str(resolver), str(resolver)]
    for directory in writable_native:
        p = Path(directory).expanduser().resolve()
        if p.exists():
            cmd += ["--bind", str(p), str(p)]
    protected = [
        root / "orchestrator",
        root / ".git",
        root / "docs/ai/roles",
        root / "docs/ai/templates",
        Path(work_item),
    ]
    # Role files and job instructions are read-only. Native output returns on stdout.
    for p in protected:
        if p.exists():
            if p.is_relative_to("/tmp"):
                if p.is_dir():
                    cmd += ["--dir", str(p)]
                else:
                    cmd += ["--dir", str(p.parent)]
            cmd += ["--ro-bind", str(p), str(p)]
    for p in hidden_roots:
        p = Path(p).resolve()
        if p.exists() and p not in (Path("/tmp"), Path("/run")):
            if p.is_relative_to("/tmp"):
                cmd += ["--dir", str(p)]
            cmd += ["--tmpfs", str(p)]
    for p in read_files:
        p = Path(p).resolve()
        if p.is_file():
            if p.is_relative_to("/tmp"):
                cmd += ["--dir", str(p.parent)]
            cmd += ["--ro-bind", str(p), str(p)]
    for m in neutral_mounts:
        host_path = Path(m["host_path"]).resolve()
        sandbox_path = m["sandbox_path"]
        if not sandbox_path.startswith("/tmp/"):
            raise WorkflowError(
                f"Neutral mount sandbox_path must reside within writable sandbox mount (/tmp): {sandbox_path}"
            )
        parent = str(Path(sandbox_path).parent)
        cmd += ["--dir", parent]
        if host_path.is_dir():
            cmd += ["--dir", sandbox_path]
        if m.get("writable", False):
            cmd += ["--bind", str(host_path), sandbox_path]
        else:
            cmd += ["--ro-bind", str(host_path), sandbox_path]
    cmd += ["--chdir", str(root), "--", *argv]
    return cmd


def probe():
    """Both positive writable-root and negative control-store checks are necessary."""
    with tempfile.TemporaryDirectory(prefix="workflow-boundary-") as temp:
        root = Path(temp)
        (root / "orchestrator").mkdir()
        (root / ".git").write_text("test git metadata")
        (root / "work-item").mkdir()
        sentinel = root / "orchestrator" / "sentinel"
        sentinel.write_text("unchanged")
        code = """from pathlib import Path
import errno
Path("allowed").write_text("ok")
try:
    Path("orchestrator/sentinel").write_text("forbidden")
except OSError as e:
    assert e.errno in (errno.EROFS, errno.EACCES)
else:
    raise SystemExit(2)
try:
    Path(".git").write_text("forbidden")
except OSError as e:
    assert e.errno in (errno.EROFS, errno.EACCES)
else:
    raise SystemExit(3)
"""
        r = subprocess.run(
            command(["/usr/bin/python3", "-c", code], root, root / "work-item"),
            capture_output=True,
            timeout=10,
        )
        return (
            r.returncode == 0
            and sentinel.read_text() == "unchanged"
            and (root / "allowed").read_text() == "ok"
        )
